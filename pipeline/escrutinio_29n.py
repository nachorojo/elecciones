"""Escrutinio provisional del 29N: lee los ficheros de la API de descargas de Interior para medios.

Diseño de registro: «Manual API de descargas · Elecciones Generales, 29 de noviembre de 2026»
(Ministerio del Interior), apartado 3.2. Los ficheros son CSV con separador «;», campos de longitud
fija y, en los porcentajes, las dos últimas posiciones son decimales.

    python -m pipeline.escrutinio_29n --vacio      # web/data/vivo_29n.json sin escrutinio (antes de las 20:00)
    python -m pipeline.escrutinio_29n --demo       # web/data/demo_29n.json con DATOS DE PRUEBA (ver abajo)
    python -m pipeline.escrutinio_29n fichero.csv  # convierte un getEscrutinioTotales ya descargado
    python -m pipeline.escrutinio_29n --descargar  # pide el último envío a la API y lo convierte

Para --descargar hacen falta ELECCIONES_API_URL (dominio del repositorio), ELECCIONES_API_USER y
ELECCIONES_API_PASS. El manual no dice el dominio ni cómo se autentica: aquí se supone
autenticación HTTP básica. SIN PROBAR contra el servicio real (simulacro: 18 de noviembre, 15:00).

La salida tiene la misma forma que una elección de web/data/resultados.json, más `escrutado`
(% de censo escrutado) y `hora`, para que la web la pinte igual que las demás convocatorias.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import urllib.request
from pathlib import Path

from . import config as C
from .convocatoria_29n import espacio

WEB = C.REPO / "web" / "data"
VIVO = WEB / "vivo_29n.json"
DEMO = WEB / "demo_29n.json"
CONV = C.REPO / "data" / "web" / "29n"
FECHA = "29 de noviembre de 2026"
N_CAND = 80

# Campos fijos de getEscrutinioTotales (nombre, longitud), en orden. Después, 80 × CAND.
CAMPOS = [("fecha", 10), ("tipo", 2), ("ccaa", 2), ("prov", 2), ("fijo", 1), ("nombre", 50), ("mesas", 5),
          ("censo", 8), ("censo_escrutado", 8), ("pct_escrutado", 5), ("votantes", 8), ("pct_votantes", 5),
          ("abstencion", 8), ("pct_abstencion", 5), ("blancos", 8), ("pct_blancos", 5), ("nulos", 8),
          ("pct_nulos", 5), ("diputados", 3), ("cod_ultima", 4), ("cod_proxima", 4), ("votos_faltan", 8)]
CAND = [("c", 4), ("s", 55), ("v", 8), ("pct", 5), ("e", 3)]


def _entero(x: str) -> int:
    x = x.strip()
    return int(x) if x else 0


def leer_totales(texto: str) -> list[dict]:
    """Registros de getEscrutinioTotales: total estatal (TO), comunidades (CM) y provincias (PR)."""
    out = []
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        f = linea.split(";")
        if len(f) < len(CAMPOS) + N_CAND * len(CAND):
            raise ValueError(f"Registro con {len(f)} campos; se esperaban {len(CAMPOS) + N_CAND * len(CAND)}")
        r = {n: f[i].strip() for i, (n, _) in enumerate(CAMPOS)}
        for n in ("mesas", "censo", "censo_escrutado", "votantes", "abstencion", "blancos", "nulos", "diputados",
                  "votos_faltan"):
            r[n] = _entero(r[n])
        for n in ("pct_escrutado", "pct_votantes", "pct_abstencion", "pct_blancos", "pct_nulos"):
            r[n] = _entero(r[n]) / 100
        r["partidos"] = []
        for k in range(N_CAND):
            c, s, v, _, e = f[len(CAMPOS) + k * len(CAND): len(CAMPOS) + (k + 1) * len(CAND)]
            if s.strip() and _entero(c):
                r["partidos"].append({"c": c.strip(), "s": s.strip(), "v": _entero(v), "e": _entero(e)})
        out.append(r)
    return out


def escribir_totales(registros: list[dict]) -> str:
    """Inverso de `leer_totales` (para pruebas y para el fichero de demostración)."""
    lineas = []
    for r in registros:
        f = []
        for n, lon in CAMPOS:
            v = r.get(n, "")
            if n.startswith("pct_"):
                v = round(float(v or 0) * 100)
            f.append(str(v).ljust(lon) if n in ("nombre", "tipo") else str(v).rjust(lon, "0"))
        for k in range(N_CAND):
            p = r["partidos"][k] if k < len(r["partidos"]) else None
            if p:
                f += [p["c"].rjust(4, "0"), p["s"].ljust(55), str(p["v"]).rjust(8, "0"),
                      str(round(10000 * p["v"] / max(1, r["votantes"] - r["nulos"]))).rjust(5, "0"), str(p["e"]).rjust(3, "0")]
            else:
                f += ["0000", " " * 55, "0" * 8, "0" * 5, "000"]
        lineas.append(";".join(f))
    return "\r\n".join(lineas) + "\r\n"


def _hora(fecha: str) -> str:
    """'2611292114' (YYMMddHHmm) -> '21:14'."""
    return f"{fecha[6:8]}:{fecha[8:10]}" if len(fecha) == 10 and fecha.isdigit() else ""


def _ambito(r: dict, nombre: str | None = None) -> dict:
    cand = sum(p["v"] for p in r["partidos"])
    partidos = sorted(({"c": p["c"], "s": p["s"], "f": espacio("", p["s"]), "v": p["v"], "e": p["e"]}
                       for p in r["partidos"] if p["v"] > 0 or p["e"] > 0), key=lambda p: (-p["e"], -p["v"]))
    return {"nombre": nombre or r["nombre"], "censo": r["censo"], "censo_escrutado": r["censo_escrutado"],
            "escrutado": r["pct_escrutado"], "votantes": r["votantes"], "blancos": r["blancos"], "nulos": r["nulos"],
            "candidaturas": cand, "validos": cand + r["blancos"], "escanos_total": r["diputados"],
            "cera": {"censo": 0, "votantes": 0, "votos": 0},
            "participacion_residentes": round(100 * r["votantes"] / r["censo_escrutado"], 2) if r["censo_escrutado"] else 0,
            "ultimo": {"ultima": r["cod_ultima"], "proxima": r["cod_proxima"], "faltan": r["votos_faltan"]},
            "partidos": partidos, "otros": 0}


def _nombres() -> dict[str, tuple[str, int]]:
    with open(CONV / "escanos.csv", encoding="utf-8", newline="") as fh:
        return {r["provincia"]: (r["nombre"], int(r["escanos_29n"])) for r in csv.DictReader(fh)}


def a_web(registros: list[dict], prueba: bool = False) -> dict:
    """Elección «2026» con la forma de resultados.json. Avisa si los escaños no cuadran con el BOE."""
    ref = _nombres()
    nacional = next(r for r in registros if r["tipo"] == "TO")
    provincias = {r["prov"]: _ambito(r, ref[r["prov"]][0]) for r in registros if r["tipo"] == "PR"}
    avisos = [f"{p}: {a['escanos_total']} diputados en el fichero, {ref[p][1]} en el BOE"
              for p, a in provincias.items() if a["escanos_total"] != ref[p][1]]
    return {"id": "2026", "fecha": FECHA, "hora": _hora(nacional["fecha"]), "prueba": prueba, "avisos": avisos,
            "nacional": _ambito(nacional, "España"), "provincias": dict(sorted(provincias.items()))}


def vacio() -> dict:
    """Antes del escrutinio: las 52 circunscripciones con sus escaños y nada contado."""
    def reg(tipo, prov, nombre, dip):
        return {"fecha": "", "tipo": tipo, "ccaa": "99", "prov": prov, "nombre": nombre, "mesas": 0, "censo": 0,
                "censo_escrutado": 0, "pct_escrutado": 0, "votantes": 0, "pct_votantes": 0, "abstencion": 0,
                "blancos": 0, "nulos": 0, "diputados": dip, "cod_ultima": "", "cod_proxima": "", "votos_faltan": 0,
                "partidos": []}
    ref = _nombres()
    return a_web([reg("TO", "99", "España", 350)] + [reg("PR", p, n, e) for p, (n, e) in ref.items()])


def demo(escrutado: float = 0.62) -> str:
    """Fichero de PRUEBA con el formato de la API: voto de 2023 trasladado a las listas de 2026 con el
    simulador, como si se hubiera contado el `escrutado` del censo. No es una estimación de nada: sirve
    para probar el lector y la página."""
    from . import simulador as S
    d = S.base_29n()
    pct = {e["id"]: e["inicio"] for e in d["espacios"]} | {"FA": 6.3, "PODEMOS": 4.0, "SALF": 0.0}
    r = S.simular(d, pct)
    cods = {e: str(i + 1).rjust(4, "0") for i, e in enumerate(S.ORDEN)}
    siglas = {"PP": "PP", "PSOE": "PSOE", "VOX": "VOX", "FA": "FA", "PODEMOS": "PODEMOS", "SALF": "SALF", "ERC": "ERC",
              "JUNTS": "JxCat", "EH_BILDU": "EH BILDU", "PNV": "EAJ-PNV", "BNG": "BNG", "CC": "CCa-1.ºCAN",
              "COMPROMIS": "COMPROMIS-EUPV-PODEM-ERPV", "NC": "NC-BC, PODEMOS, IU, SUMAR",
              "ADELANTE": "ADELANTE ANDALUCÍA", "TERUEL_EXISTE": "TERUEL EXISTE", "GBAI": "GBAI"}
    regs, tot = [], {"censo": 0, "ce": 0, "vot": 0, "bl": 0, "nu": 0, "v": {}, "e": {}}
    for p, pr in d["provincias"].items():
        censo = round(pr["validos"] / 0.66)
        ce = round(censo * escrutado)
        partidos = [{"c": cods[e], "s": siglas[e], "v": round(v * escrutado), "e": r["escanos"][p].get(e, 0)}
                    for e, v in r["votos"][p].items() if e != S.RESTO]
        bl = round(r["votos"][p].get(S.RESTO, 0) * escrutado)
        nu = round(0.011 * pr["validos"] * escrutado)
        vot = sum(x["v"] for x in partidos) + bl + nu
        regs.append({"fecha": "2611292114", "tipo": "PR", "ccaa": "99", "prov": p, "fijo": "9", "nombre": pr["nombre"],
                     "mesas": 0, "censo": censo, "censo_escrutado": ce, "pct_escrutado": 100 * escrutado,
                     "votantes": vot, "pct_votantes": 100 * vot / ce, "abstencion": ce - vot,
                     "pct_abstencion": 100 * (ce - vot) / ce, "blancos": bl, "pct_blancos": 0, "nulos": nu,
                     "pct_nulos": 0, "diputados": pr["escanos"], "cod_ultima": "0", "cod_proxima": "0",
                     "votos_faltan": 0, "partidos": partidos})
        tot["censo"] += censo; tot["ce"] += ce; tot["vot"] += vot; tot["bl"] += bl; tot["nu"] += nu
        for x in partidos:
            tot["v"][x["c"]] = tot["v"].get(x["c"], 0) + x["v"]
            tot["e"][x["c"]] = tot["e"].get(x["c"], 0) + x["e"]
    inv = {c: e for e, c in cods.items()}
    nac = dict(regs[0], tipo="TO", prov="99", nombre="Total nacional", censo=tot["censo"], censo_escrutado=tot["ce"],
               votantes=tot["vot"], pct_votantes=100 * tot["vot"] / tot["ce"], abstencion=tot["ce"] - tot["vot"],
               pct_abstencion=100 * (tot["ce"] - tot["vot"]) / tot["ce"], blancos=tot["bl"], nulos=tot["nu"],
               diputados=350, partidos=[{"c": c, "s": siglas[inv[c]], "v": v, "e": tot["e"][c]} for c, v in tot["v"].items()])
    return escribir_totales([nac] + regs)


def descargar() -> str:
    """Último envío del Congreso: getEnvio/2 y getEscrutinioTotales/2/{numEnv}. Sin probar (ver cabecera)."""
    base = os.environ["ELECCIONES_API_URL"].rstrip("/")
    cred = base64.b64encode(f"{os.environ['ELECCIONES_API_USER']}:{os.environ['ELECCIONES_API_PASS']}".encode()).decode()

    def pedir(ruta: str) -> str:
        req = urllib.request.Request(base + ruta, headers={"Authorization": "Basic " + cred})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", errors="replace")

    envio = pedir("/descargas/csv/data/getEnvio/2").strip()
    return pedir(f"/descargas/csv/data/getEscrutinioTotales/2/{envio}")


def guardar(datos: dict, salida: Path) -> Path:
    salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fichero", nargs="?")
    ap.add_argument("--vacio", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--descargar", action="store_true")
    a = ap.parse_args()
    if a.demo:
        print(guardar(a_web(leer_totales(demo()), prueba=True), DEMO))
    elif a.vacio:
        print(guardar(vacio(), VIVO))
    else:
        texto = descargar() if a.descargar else Path(a.fichero).read_text(encoding="utf-8", errors="replace")
        web = a_web(leer_totales(texto))
        print(guardar(web, VIVO), f"escrutado {web['nacional']['escrutado']} %", *web["avisos"])
