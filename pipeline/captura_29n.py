"""Captura de la noche electoral (y del simulacro): pregunta a la API de Interior si hay envío nuevo,
lo guarda tal cual con su hora, actualiza el fichero que lee la web y calcula la proyección.

    python -m pipeline.captura_29n --simulacro                 # bucle, cada 60 s (Ctrl+C para parar)
    python -m pipeline.captura_29n --una-vez                   # un solo envío y termina
    python -m pipeline.captura_29n --repetir CARPETA_DE_ENVIO  # rehace un envío ya guardado (sin red)
    python -m pipeline.captura_29n --publicar                  # además, git commit + push del fichero de la web

Variables de entorno: ELECCIONES_API_URL, ELECCIONES_API_USER, ELECCIONES_API_PASS (y ELECCIONES_API_AUTH).
Las credenciales NO se escriben en ningún fichero ni se suben a la repo.

Qué guarda, en --carpeta (por defecto ../datos/29n_envios, fuera de la repo):
    envio_<número>_<AAAAMMDD-HHMMSS>/totales.csv.gz, avances.csv.gz, municipios_NN.csv.gz   ficheros de Interior,
                                                                                   comprimidos (gzip), sin modificar
    envio_<...>/proyeccion.json                                                    estimación propia (no se publica)
    registro.csv                                                                   una línea por envío capturado
Y en la repo: web/data/vivo_29n.json (lo que pinta la página).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import config as C
from . import escrutinio_29n as E
from . import proyeccion_29n as P

CARPETA = C.REPO.parent / "datos" / "29n_envios"


class Guardado:
    """Lee un envío ya guardado en disco con la misma interfaz que `escrutinio_29n.Cliente`."""

    def __init__(self, carpeta: Path):
        self.carpeta = Path(carpeta)

    def envio(self) -> str:
        return self.carpeta.name.split("_")[1] if "_" in self.carpeta.name else "0"

    def _leer(self, nombre: str) -> bytes:
        f = self.carpeta / nombre
        return f.read_bytes() if f.exists() else gzip.decompress((self.carpeta / (nombre + ".gz")).read_bytes())

    def totales(self, envio: str) -> bytes:
        return self._leer("totales.csv")

    def municipios(self, prov: str, envio: str) -> bytes:
        return self._leer(f"municipios_{prov}.csv")

    def avances(self, envio: str) -> bytes:
        return self._leer("avances.csv")


def capturar(cliente, envio: str, carpeta: Path, provincias: list[str], base: dict | None,
             simulacro: bool = False, salida_web: Path = E.VIVO, guardar_bruto: bool = True) -> dict:
    """Descarga (o relee) un envío, lo guarda y devuelve un resumen. No lanza si falla una provincia."""
    ahora = datetime.now()
    destino = carpeta / f"envio_{envio}_{ahora:%Y%m%d-%H%M%S}" if guardar_bruto else Path(cliente.carpeta)
    destino.mkdir(parents=True, exist_ok=True)
    fallos = []

    def traer(nombre: str, pedir) -> bytes | None:
        try:
            datos = pedir()
        except Exception as e:                       # una provincia que falla no debe parar la noche
            fallos.append(f"{nombre}: {e}")
            return None
        if guardar_bruto:
            # Comprimido: los 52 ficheros de municipios ocupan unos 50 MB por envío sin comprimir.
            (destino / (nombre + ".gz")).write_bytes(gzip.compress(datos, 6))
        return datos

    resumen = {"envio": envio, "capturado": f"{ahora:%Y-%m-%d %H:%M:%S}", "carpeta": str(destino)}
    tot = traer("totales.csv", lambda: cliente.totales(envio))
    av = traer("avances.csv", lambda: cliente.avances(envio))
    if tot:
        web = E.a_web(E.leer_totales(E.texto(tot)), simulacro=simulacro, avances=E.leer_avances(E.texto(av)) if av else None)
        n = web["nacional"]
        # En el simulacro del 18-N un envío de totales llegó a cero con el recuento al 85 %. Si el recuento
        # retrocede respecto a lo ya publicado, no se pisa la página: se anota y se espera al siguiente.
        previo = _escrutado_publicado(salida_web, simulacro)
        if n["escrutado"] < previo:
            fallos.append(f"totales.csv: el recuento retrocede ({previo} % -> {n['escrutado']} %); no se publica")
        else:
            E.guardar(web, salida_web)
            # Resumen para terceros (pantallas en la calle), junto al fichero de la web y con los mismos datos.
            E.guardar_pantallas(web, envio, salida_web.with_name("pantallas_29n.json"))
        resumen |= {"hora_interior": web["hora"], "escrutado": n["escrutado"],
                    "escanos": {p["s"]: p["e"] for p in n["partidos"] if p["e"]}, "avisos": web["avisos"]}
    registros = []
    for p in provincias:
        datos = traer(f"municipios_{p}.csv", lambda p=p: cliente.municipios(p, envio))
        if datos:
            try:
                registros += E.leer_municipios(E.texto(datos))
            except ValueError as e:
                fallos.append(f"municipios_{p}.csv: {e}")
    # Sin nada escrutado no hay nada que proyectar (saldría la base de 2023 tal cual, que no es una estimación).
    if base is not None and any(r["censo_escrutado"] > 0 for r in registros):
        proy = P.proyectar_registros(registros, base) | {"envio": envio, "capturado": resumen["capturado"]}
        (destino / "proyeccion.json").write_text(json.dumps(proy, ensure_ascii=False, indent=1), encoding="utf-8")
        resumen |= {"proyeccion": proy["nacional"]["escanos"], "margen": proy["margen"]["escanos_media"],
                    "escrutado_municipios": proy["escrutado"]}
    resumen["fallos"] = fallos
    return resumen


def _escrutado_publicado(fichero: Path, simulacro: bool) -> float:
    """% escrutado del fichero que ya lee la web (0 si no existe, está vacío o es de otro tipo de sesión)."""
    try:
        d = json.loads(fichero.read_text(encoding="utf-8"))
        return float(d["nacional"]["escrutado"]) if bool(d.get("simulacro")) == simulacro else 0.0
    except (OSError, ValueError, KeyError):
        return 0.0


def publicar(fichero: Path, mensaje: str) -> str:
    """git add + commit + push del fichero de la web y del resumen para pantallas. Devuelve el error, o cadena vacía."""
    ficheros = [str(fichero)] + [str(f) for f in (fichero.with_name("pantallas_29n.json"), fichero.with_name("pantallas_29n.csv"))
                                 if f.exists()]
    for orden in (["git", "add", *ficheros], ["git", "commit", "-q", "-m", mensaje], ["git", "push", "-q"]):
        r = subprocess.run(orden, cwd=C.REPO, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
            return f"{' '.join(orden[:2])}: {(r.stderr or r.stdout).strip()[:200]}"
    return ""


def _anotar(carpeta: Path, r: dict) -> None:
    f = carpeta / "registro.csv"
    nuevo = not f.exists()
    with open(f, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if nuevo:
            w.writerow(["capturado", "envio", "hora_interior", "escrutado", "escanos", "proyeccion", "fallos"])
        w.writerow([r["capturado"], r["envio"], r.get("hora_interior", ""), r.get("escrutado", ""),
                    json.dumps(r.get("escanos", {}), ensure_ascii=False), json.dumps(r.get("proyeccion", {}), ensure_ascii=False),
                    len(r["fallos"])])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--carpeta", type=Path, default=CARPETA)
    ap.add_argument("--intervalo", type=int, default=60, help="segundos entre consultas (por defecto, 60)")
    ap.add_argument("--simulacro", action="store_true", help="rotula la página como SIMULACRO")
    ap.add_argument("--una-vez", action="store_true")
    ap.add_argument("--publicar", action="store_true", help="git commit + push de web/data/vivo_29n.json en cada envío")
    ap.add_argument("--sin-proyeccion", action="store_true")
    ap.add_argument("--repetir", type=Path, help="carpeta de un envío ya guardado: lo reprocesa sin conectarse")
    a = ap.parse_args()
    base = None if a.sin_proyeccion else P.base_municipal()
    provincias = base["provincias"] if base else [f"{i:02d}" for i in range(1, 53)]
    if a.repetir:
        r = capturar(Guardado(a.repetir), Guardado(a.repetir).envio(), a.carpeta, provincias, base, a.simulacro, guardar_bruto=False)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    cliente = E.Cliente()
    a.carpeta.mkdir(parents=True, exist_ok=True)
    ultimo = None
    print(f"Capturando en {a.carpeta} cada {a.intervalo} s. Ctrl+C para parar.")
    while True:
        try:
            envio = cliente.envio()
            if envio != ultimo:
                r = capturar(cliente, envio, a.carpeta, provincias, base, a.simulacro)
                _anotar(a.carpeta, r)
                linea = f"{r['capturado']}  envío {envio}  escrutado {r.get('escrutado', '?')} %  {r.get('escanos', {})}"
                if "proyeccion" in r:
                    linea += f"  | proyección {r['proyeccion']} (±{r['margen']})"
                print(linea + (f"  | {len(r['fallos'])} fallos: {r['fallos'][:2]}" if r["fallos"] else ""))
                if a.publicar and "escrutado" in r:
                    error = publicar(E.VIVO, f"29N: envío {envio} ({r['escrutado']} % escrutado)")
                    if error:
                        print("   no se pudo publicar ->", error)
                ultimo = envio
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"{datetime.now():%H:%M:%S}  error: {e}")
        if a.una_vez:
            break
        time.sleep(a.intervalo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCaptura detenida.")
