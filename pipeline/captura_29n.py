"""Captura de la noche electoral (y del simulacro): pregunta a la API de Interior si hay envío nuevo,
lo guarda tal cual con su hora, actualiza el fichero que lee la web y calcula la proyección.

    python -m pipeline.captura_29n --simulacro                 # bucle, cada 60 s (Ctrl+C para parar)
    python -m pipeline.captura_29n --una-vez                   # un solo envío y termina
    python -m pipeline.captura_29n --repetir CARPETA_DE_ENVIO  # rehace un envío ya guardado (sin red)
    python -m pipeline.captura_29n --publicar                  # además, git commit + push del fichero de la web
    python -m pipeline.captura_29n --mesas                     # baja los ficheros por mesa (al acabar cada fase) y termina

Variables de entorno: ELECCIONES_API_URL, ELECCIONES_API_USER, ELECCIONES_API_PASS (y ELECCIONES_API_AUTH).
Las credenciales NO se escriben en ningún fichero ni se suben a la repo.

Qué guarda, en --carpeta (por defecto ../datos/29n_envios, fuera de la repo):
    envio_<número>_<AAAAMMDD-HHMMSS>/totales.csv.gz, avances.csv.gz, municipios_NN.csv.gz   ficheros de Interior,
                                                                                   comprimidos (gzip), sin modificar
    envio_<...>/proyeccion.json                                                    estimación propia (no se publica)
    registro.csv                                                                   una línea por envío capturado
    senado/envio_<número>_<AAAAMMDD-HHMMSS>_totales.csv.gz                         totales del Senado, tal cual (no se leen)
    mesas_<AAAAMMDD-HHMMSS>/avances_NN, escrutinio_congreso_NN, escrutinio_senado_NN (.csv.gz)   solo con --mesas
Y en la repo: web/data/vivo_29n.json (lo que pinta la página).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
import time
import urllib.error
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
             simulacro: bool = False, salida_web: Path = E.VIVO, guardar_bruto: bool = True,
             hoy: datetime | None = None) -> dict:
    """Descarga (o relee) un envío, lo guarda y devuelve un resumen. No lanza si falla una provincia."""
    ahora = datetime.now()
    destino = carpeta / f"envio_{envio}_{ahora:%Y%m%d-%H%M%S}" if guardar_bruto else Path(cliente.carpeta)
    destino.mkdir(parents=True, exist_ok=True)
    fallos = []
    rechazos = [0]                                   # 401/403 seguidos en este envío

    def traer(nombre: str, pedir) -> bytes | None:
        if rechazos[0] >= RECHAZOS:                  # el manual pide no insistir tras un 401/403
            return None
        try:
            datos = pedir()
        except Exception as e:                       # una provincia que falla no debe parar la noche
            fallos.append(f"{nombre}: {e}")
            rechazos[0] = rechazos[0] + 1 if _rechazo(e) else 0
            if rechazos[0] == RECHAZOS:
                fallos.append(f"{RECHAZOS} respuestas 401/403 seguidas: no se pide el resto de este envío")
            return None
        rechazos[0] = 0
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
        dias = _antiguedad(E.leer_totales(E.texto(tot))[0]["fecha"], hoy)
        if dias is not None and dias > 1:
            # Antes de empezar, el servicio puede seguir sirviendo el último envío de una prueba anterior (casi al
            # 100 %). Publicarlo dejaría la página con datos viejos y, además, bloquearía el recuento nuevo por «retroceso».
            fallos.append(f"totales.csv: datos de hace {dias} días (de una prueba anterior); no se publica")
            resumen["antiguo"] = True
        elif n["escrutado"] < previo and _RETROCESOS.get(salida_web, 0) < 1:
            _RETROCESOS[salida_web] = _RETROCESOS.get(salida_web, 0) + 1
            fallos.append(f"totales.csv: el recuento retrocede ({previo} % -> {n['escrutado']} %); no se publica")
        else:
            # Un retroceso aislado es un envío defectuoso; si el siguiente también va por debajo, es que Interior ha
            # reiniciado el recuento (empieza otra prueba, o la jornada real): se acepta.
            _RETROCESOS[salida_web] = 0
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
        proy = P.proyectar_registros(registros, base) | {"envio": envio, "capturado": resumen["capturado"],
                                                         "hora": resumen.get("hora_interior", ""), "simulacro": simulacro}
        if tot:      # recuento del mismo envío, por espacio, para poder compararlo con la proyección
            suma = lambda a: {f: sum(p["e"] for p in a["partidos"] if p["f"] == f) for f in {p["f"] for p in a["partidos"] if p["e"]}}
            proy["recuento"] = {"nacional": suma(web["nacional"]), "provincias": {k: suma(a) for k, a in web["provincias"].items()}}
            proy["nombres"] = {k: a["nombre"] for k, a in web["provincias"].items()}
        (destino / "proyeccion.json").write_text(json.dumps(proy, ensure_ascii=False, indent=1), encoding="utf-8")
        # Copia para la página oculta web/proyeccion.html (se publica junto al recuento; no está enlazada desde la web).
        if not any("no se publica" in f for f in fallos):
            E.guardar(proy, salida_web.with_name("proyeccion_29n.json"))
        resumen |= {"proyeccion": proy["nacional"]["escanos"], "margen": proy["margen"]["escanos_media"],
                    "escrutado_municipios": proy["escrutado"]}
    resumen["fallos"] = fallos
    return resumen


RECHAZOS = 3
_RETROCESOS: dict[Path, int] = {}                    # retrocesos seguidos sin publicar, por fichero de salida


def _antiguedad(fecha: str, hoy: datetime | None) -> int | None:
    """Días entre la fecha de totalización de Interior (YYMMddHHmm) y hoy. None si no se comprueba o no se entiende."""
    if hoy is None:
        return None
    try:
        return abs((hoy.date() - datetime.strptime(fecha[:6], "%y%m%d").date()).days)
    except ValueError:
        return None


def _rechazo(e: Exception) -> bool:
    return isinstance(e, urllib.error.HTTPError) and e.code in (401, 403)


def capturar_senado(cliente, envio: str, carpeta: Path) -> Path:
    """Guarda tal cual los totales del Senado de un envío. No se leen ni se publican: quedan para después."""
    destino = carpeta / "senado"
    destino.mkdir(parents=True, exist_ok=True)
    f = destino / f"envio_{envio}_{datetime.now():%Y%m%d-%H%M%S}_totales.csv.gz"
    f.write_bytes(gzip.compress(cliente.totales(envio, 3), 6))
    return f


MESAS = {"avances": "getAvances/2", "escrutinio_congreso": "getEscrutinio/2", "escrutinio_senado": "getEscrutinio/3"}


def capturar_mesas(cliente, carpeta: Path, provincias: list[str], pausa: float = 0.5) -> dict:
    """Baja los ficheros por mesa (participación, Congreso y Senado) de cada provincia. Interior los deja al
    terminar cada fase, así que antes de eso fallan: tras tres fallos seguidos se deja ese tipo de fichero."""
    destino = carpeta / f"mesas_{datetime.now():%Y%m%d-%H%M%S}"
    destino.mkdir(parents=True, exist_ok=True)
    resumen = {"carpeta": str(destino)}
    for nombre, ruta in MESAS.items():
        hechos, seguidos, error = 0, 0, ""
        for p in provincias:
            try:
                datos = cliente.mesas(ruta, p)
            except Exception as e:
                seguidos, error = seguidos + 1, f"{p}: {e}"
                if seguidos == 3:
                    break
                continue
            seguidos = 0
            hechos += 1
            (destino / f"{nombre}_{p}.csv.gz").write_bytes(gzip.compress(datos, 6))
            time.sleep(pausa)
        resumen[nombre] = {"provincias": hechos, "ultimo_error": error}
    return resumen


def _escrutado_publicado(fichero: Path, simulacro: bool) -> float:
    """% escrutado del fichero que ya lee la web (0 si no existe, está vacío o es de otro tipo de sesión)."""
    try:
        d = json.loads(fichero.read_text(encoding="utf-8"))
        return float(d["nacional"]["escrutado"]) if bool(d.get("simulacro")) == simulacro else 0.0
    except (OSError, ValueError, KeyError):
        return 0.0


def _es_simulacro(fichero: Path) -> bool:
    try:
        return bool(json.loads(fichero.read_text(encoding="utf-8")).get("simulacro"))
    except (OSError, ValueError):
        return False


def publicar(fichero: Path, mensaje: str, subir: bool = True) -> str:
    """git add + commit (+ push si `subir`) del fichero de la web, el resumen para pantallas y la proyección.
    Devuelve el error, o cadena vacía. Con `subir=False` el envío queda confirmado en local y sube con el siguiente push."""
    ficheros = [str(fichero)] + [str(f) for f in (fichero.with_name("pantallas_29n.json"), fichero.with_name("pantallas_29n.csv"),
                                                  fichero.with_name("proyeccion_29n.json")) if f.exists()]
    for orden in (["git", "add", *ficheros], ["git", "commit", "-q", "-m", mensaje], ["git", "push", "-q"])[:3 if subir else 2]:
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
    ap.add_argument("--cada", type=float, default=0, metavar="MIN",
                    help="con --publicar: sube a GitHub como mucho una vez cada MIN minutos (cada subida es un despliegue "
                         "de Netlify). Los envíos intermedios se confirman en local y suben juntos. Por defecto, todos.")
    ap.add_argument("--sin-proyeccion", action="store_true")
    ap.add_argument("--repetir", type=Path, help="carpeta de un envío ya guardado: lo reprocesa sin conectarse")
    ap.add_argument("--mesas", action="store_true", help="baja los ficheros por mesa de las 52 provincias y termina")
    ap.add_argument("--sin-senado", action="store_true", help="no guarda los totales del Senado")
    a = ap.parse_args()
    base = None if a.sin_proyeccion else P.base_municipal()
    provincias = base["provincias"] if base else [f"{i:02d}" for i in range(1, 53)]
    if a.repetir:
        r = capturar(Guardado(a.repetir), Guardado(a.repetir).envio(), a.carpeta, provincias, base, a.simulacro, guardar_bruto=False)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    cliente = E.Cliente()
    a.carpeta.mkdir(parents=True, exist_ok=True)
    if a.mesas:
        print(json.dumps(capturar_mesas(cliente, a.carpeta, provincias), ensure_ascii=False, indent=1))
        return
    if not a.simulacro and _es_simulacro(E.VIVO):
        E.vaciar()                                   # no empezar la jornada real con restos de una prueba en la página
        print("La página tenía datos de un simulacro: se ha vaciado.")
        if a.publicar:
            print("   " + (publicar(E.VIVO, "29N: página vacía") or "publicada vacía"))
    ultimo = ultimo_senado = None
    subido, pendientes = 0.0, 0                      # hora de la última subida y envíos confirmados sin subir
    error_senado = ""
    rechazos = 0
    print(f"Capturando en {a.carpeta} cada {a.intervalo} s. Ctrl+C para parar.")
    while True:
        try:
            envio = cliente.envio()
            if envio != ultimo:
                r = capturar(cliente, envio, a.carpeta, provincias, base, a.simulacro, hoy=datetime.now())
                _anotar(a.carpeta, r)
                linea = f"{r['capturado']}  envío {envio}  escrutado {r.get('escrutado', '?')} %  {r.get('escanos', {})}"
                if "proyeccion" in r:
                    linea += f"  | proyección {r['proyeccion']} (±{r['margen']})"
                print(linea + (f"  | {len(r['fallos'])} fallos: {r['fallos'][:2]}" if r["fallos"] else ""))
                if a.publicar and "escrutado" in r and not r.get("antiguo"):
                    subir = time.time() - subido >= a.cada * 60
                    error = publicar(E.VIVO, f"29N: envío {envio} ({r['escrutado']} % escrutado)", subir)
                    if error:
                        print("   no se pudo publicar ->", error)
                    elif subir:
                        subido, pendientes = time.time(), 0
                    else:
                        pendientes += 1
                        print(f"   confirmado en local; sube con el siguiente (como mucho una subida cada {a.cada:g} min)")
                ultimo = envio
            rechazos = 0
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"{datetime.now():%H:%M:%S}  error: {e}")
            if _rechazo(e):
                # Manual, apartado 4: ante un 401/403 no reintentar de continuo. Se espacia: 5, 10 y 15 minutos.
                rechazos += 1
                espera = min(15, 5 * rechazos)
                print(f"   Interior rechaza la petición ({e.code}). 401: revisar usuario y clave. 403: puede ser un bloqueo;"
                      f" avisar a soporte (IP pública, hora, URL y código). Nuevo intento en {espera} min.")
                if not a.una_vez:
                    time.sleep(espera * 60 - a.intervalo)
        if not a.sin_senado and not rechazos:
            try:
                es = cliente.envio(3)
                if es != ultimo_senado:
                    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}  Senado, envío {es}: guardado en {capturar_senado(cliente, es, a.carpeta).name}")
                    ultimo_senado, error_senado = es, ""
            except KeyboardInterrupt:
                raise
            except Exception as e:                   # antes de su escrutinio puede no haber nada: se avisa una sola vez
                if str(e) != error_senado:
                    error_senado = str(e)
                    print(f"{datetime.now():%H:%M:%S}  Senado: {e}")
        if a.una_vez:
            break
        time.sleep(a.intervalo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Con --cada pueden quedar envíos confirmados sin subir: se suben al parar (si no hay nada, no hace nada).
        r = subprocess.run(["git", "push", "-q"], cwd=C.REPO, capture_output=True, text=True)
        print("\nCaptura detenida." + ("" if r.returncode == 0 else " OJO: no se pudo subir lo pendiente; lanza «git push»."))
