"""Escrutinio provisional del 29N: lee los ficheros de la API de descargas de Interior para medios.

Diseño de registro: «Manual API de descargas · Elecciones Generales, 29 de noviembre de 2026»
(Ministerio del Interior), apartado 3.2. Los ficheros son CSV con separador «;», campos de longitud
fija y, en los porcentajes, las dos últimas posiciones son decimales.

    python -m pipeline.escrutinio_29n --vacio      # web/data/vivo_29n.json sin escrutinio (antes de las 20:00)
    python -m pipeline.escrutinio_29n --demo       # web/data/demo_29n.json con DATOS DE PRUEBA (ver abajo)
    python -m pipeline.escrutinio_29n fichero.csv  # convierte un getEscrutinioTotales ya descargado
    python -m pipeline.escrutinio_29n --descargar  # pide el último envío a la API y lo convierte

Para --descargar hacen falta ELECCIONES_API_URL (dominio del repositorio), ELECCIONES_API_USER y
ELECCIONES_API_PASS. Autenticación HTTP básica (probada en el simulacro del 18 de noviembre).

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
PANTALLAS = WEB / "pantallas_29n.json"          # resumen mínimo para terceros (pantallas en la calle); también .csv
PANTALLAS_EJEMPLO = WEB / "pantallas_ejemplo.json"   # el mismo formato, con el último envío del simulacro
SIMULACRO = WEB / "simulacro_29n.json"          # último envío del simulacro de Interior (18-N-2026); se ve con ?simulacro
DATOS_SIMULACRO = C.REPO / "tests" / "datos" / "simulacro"
CONV = C.REPO / "data" / "web" / "29n"
FECHA = "29 de noviembre de 2026"
N_CAND = 80

# Campos fijos de getEscrutinioTotales (nombre, longitud), en orden. Después, 80 × CAND.
CAMPOS = [("fecha", 10), ("tipo", 2), ("ccaa", 2), ("prov", 2), ("fijo", 1), ("nombre", 50), ("mesas", 5),
          ("censo", 8), ("censo_escrutado", 8), ("pct_escrutado", 5), ("votantes", 8), ("pct_votantes", 5),
          ("abstencion", 8), ("pct_abstencion", 5), ("blancos", 8), ("pct_blancos", 5), ("nulos", 8),
          ("pct_nulos", 5), ("diputados", 3), ("cod_ultima", 4), ("cod_proxima", 4), ("votos_faltan", 8)]
CAND = [("c", 4), ("s", 55), ("v", 8), ("pct", 5), ("e", 3)]
# Campos fijos de getEscrutinioMunicipios. Después, 80 × (código, siglas, votos, porcentaje): sin diputados.
CAMPOS_MUN = [("fecha", 10), ("ccaa", 2), ("prov", 2), ("fijo", 1), ("mun", 3), ("distrito", 2), ("nombre", 50),
              ("fijo2", 2), ("fijo3", 2), ("mesas", 5), ("censo", 8), ("censo_escrutado", 8), ("pct_escrutado", 5),
              ("votantes", 8), ("pct_votantes", 5), ("abstencion", 8), ("pct_abstencion", 5), ("blancos", 8),
              ("pct_blancos", 5), ("nulos", 8), ("pct_nulos", 5)]
CAND_MUN = 4
# Campos fijos de /mesas/getEscrutinio/2/{codPrv}.csv (manual final, apartado 3.2). Después, 80 × (código, siglas,
# votos, porcentaje). Interior los publica al terminar el recuento provisional, no durante la noche.
CAMPOS_MESA = [("fecha", 10), ("ccaa", 2), ("prov", 2), ("circ", 1), ("mun", 3), ("distrito", 2), ("seccion", 3),
               ("mesa", 1), ("nombre", 50), ("fijo2", 2), ("fijo3", 2), ("mesas", 5), ("censo", 8),
               ("censo_escrutado", 8), ("pct_escrutado", 5), ("votantes", 8), ("pct_votantes", 5), ("abstencion", 8),
               ("pct_abstencion", 5), ("blancos", 8), ("pct_blancos", 5), ("nulos", 8), ("pct_nulos", 5)]


# Código de agrupación de la API de Interior (fichero getCandidaturas/2) -> espacio. Lo que no está, OTROS.
AGRUPACION = {"0001": "PSOE", "0007": "PP", "0067": "PP", "0006": "VOX", "0003": "SALF", "0012": "PODEMOS", "0013": "FA",
              "0004": "ADELANTE", "0005": "PACMA", "0042": "JUNTS", "0043": "ERC", "0133": "EH_BILDU", "0063": "EH_BILDU",
              "0070": "PNV", "0109": "BNG", "0028": "CC", "0030": "NC", "0077": "COMPROMIS", "0021": "TERUEL_EXISTE",
              "0066": "GBAI"}
# Código principal de cada espacio en la API (para fabricar ficheros de prueba coherentes con los reales).
CODIGO = {"PSOE": "0001", "PP": "0007", "VOX": "0006", "SALF": "0003", "PODEMOS": "0012", "FA": "0013", "ADELANTE": "0004",
          "JUNTS": "0042", "ERC": "0043", "EH_BILDU": "0133", "PNV": "0070", "BNG": "0109", "CC": "0028", "NC": "0030",
          "COMPROMIS": "0077", "TERUEL_EXISTE": "0021", "GBAI": "0066"}
_COD: dict[str, str] = {}


def espacio_api(codigo: str, siglas: str) -> str:
    """Espacio de una candidatura de la API: por su código (vía agrupación) y, si no se conoce, por las siglas."""
    if not _COD:
        f = CONV / "candidaturas_api_2026.csv"
        if f.exists():
            with open(f, encoding="utf-8", newline="") as fh:
                _COD.update({r["codigo"]: AGRUPACION.get(r["agrupacion"], "OTROS") for r in csv.DictReader(fh)})
        _COD.setdefault("", "OTROS")
    return _COD.get(codigo.strip().rjust(4, "0")) or espacio("", siglas)


CAMPOS_AV = ["fecha", "tipo", "ccaa", "prov", "fijo", "nombre", "mesas", "mesas_constituidas", "mesas_suspendidas", "censo",
             "censo_constituidas", "censo_suspendidas"]


def leer_avances(texto: str) -> list[dict]:
    """Registros de getAvancesTotales: constitución de mesas y los dos avances de participación (14:00 y 18:00)."""
    out = []
    for linea in texto.splitlines():
        f = linea.split(";")
        if len(f) < len(CAMPOS_AV) + 6:
            continue
        r = {n: f[i].strip() for i, n in enumerate(CAMPOS_AV)}
        for n in CAMPOS_AV[6:]:
            r[n] = _entero(r[n])
        r["avances"] = [{"mesas": _entero(f[12 + 3 * k]), "censo": _entero(f[13 + 3 * k]), "pct": _entero(f[14 + 3 * k]) / 100}
                        for k in range(2)]
        out.append(r)
    return out


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


def _leer_sin_escanos(texto: str, campos: list, que: str) -> list[dict]:
    """Registros con campos fijos y 80 × (código, siglas, votos, porcentaje): municipios y mesas."""
    out = []
    n_fijos = len(campos)
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        f = linea.split(";")
        if len(f) < n_fijos + N_CAND * CAND_MUN:
            raise ValueError(f"Registro {que} con {len(f)} campos; se esperaban {n_fijos + N_CAND * CAND_MUN}")
        r = {n: f[i].strip() for i, (n, _) in enumerate(campos)}
        for n in ("mesas", "censo", "censo_escrutado", "votantes", "abstencion", "blancos", "nulos"):
            r[n] = _entero(r[n])
        for n in ("pct_escrutado", "pct_votantes", "pct_abstencion", "pct_blancos", "pct_nulos"):
            r[n] = _entero(r[n]) / 100
        r["id"] = r["prov"] + r["mun"]
        r["partidos"] = []
        for k in range(N_CAND):
            c, s, v, _ = f[n_fijos + k * CAND_MUN: n_fijos + (k + 1) * CAND_MUN]
            if s.strip() and _entero(c):
                r["partidos"].append({"c": c.strip(), "s": s.strip(), "v": _entero(v)})
        out.append(r)
    return out


def leer_municipios(texto: str) -> list[dict]:
    """Registros de getEscrutinioMunicipios de una provincia: municipios (distrito «99») y distritos de las
    siete grandes ciudades (distrito distinto de «99»; sus votos ya están incluidos en el registro del municipio)."""
    return _leer_sin_escanos(texto, CAMPOS_MUN, "municipal")


def leer_mesas(texto: str) -> list[dict]:
    """Registros de /mesas/getEscrutinio/2/{codPrv}.csv: una mesa por registro. Añade `seccion_id` con el formato
    de la base histórica (provincia + municipio + distrito + sección, 10 dígitos). Escrito a partir del manual:
    SIN PROBAR con un fichero real hasta la prueba de medios del 25 de noviembre."""
    out = _leer_sin_escanos(texto, CAMPOS_MESA, "de mesa")
    for r in out:
        r["seccion_id"] = r["id"] + r["distrito"] + r["seccion"]
    return out


def escribir_municipios(registros: list[dict]) -> str:
    """Inverso de `leer_municipios` y, si los registros llevan `seccion`, de `leer_mesas` (para pruebas)."""
    lineas = []
    for r in registros:
        f = []
        for n, lon in (CAMPOS_MESA if "seccion" in r else CAMPOS_MUN):
            v = r.get(n, "9" if n == "fijo" else "99" if n in ("fijo2", "fijo3", "distrito") else "")
            if n.startswith("pct_"):
                v = round(float(v or 0) * 100)
            f.append(str(v).ljust(lon) if n in ("nombre", "mesa") else str(v).rjust(lon, "0"))
        for k in range(N_CAND):
            p = r["partidos"][k] if k < len(r["partidos"]) else None
            f += [p["c"].rjust(4, "0"), p["s"].ljust(55), str(p["v"]).rjust(8, "0"), "0" * 5] if p \
                else ["0000", " " * 55, "0" * 8, "0" * 5]
        lineas.append(";".join(f))
    return "\r\n".join(lineas) + "\r\n"


def _hora(fecha: str) -> str:
    """'2611292114' (YYMMddHHmm) -> '21:14'."""
    return f"{fecha[6:8]}:{fecha[8:10]}" if len(fecha) == 10 and fecha.isdigit() else ""


def _ambito(r: dict, nombre: str | None = None) -> dict:
    cand = sum(p["v"] for p in r["partidos"])
    # Las candidaturas de un mismo espacio se suman en una fila (PP + UPN-PP, EH BILDU + EH BILDU-ERC, PSOE + PSC…):
    # Interior las da separadas en el total nacional. Las de OTROS no se mezclan entre sí. La fila conserva las
    # siglas y el código de la candidatura con más votos, y en `incluye` las siglas de las demás.
    filas: dict[str, dict] = {}
    for p in sorted(r["partidos"], key=lambda p: -p["v"]):
        if not (p["v"] > 0 or p["e"] > 0):
            continue
        f = espacio_api(p["c"], p["s"])
        clave = f if f != "OTROS" else "OTROS:" + p["c"]
        if clave in filas:
            filas[clave]["v"] += p["v"]; filas[clave]["e"] += p["e"]
            filas[clave].setdefault("incluye", []).append(p["s"])
        else:
            filas[clave] = {"c": p["c"], "s": p["s"], "f": f, "v": p["v"], "e": p["e"]}
    partidos = sorted(filas.values(), key=lambda p: (-p["e"], -p["v"]))
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


def a_web(registros: list[dict], prueba: bool = False, simulacro: bool = False, avances: list[dict] | None = None) -> dict:
    """Elección «2026» con la forma de resultados.json. Avisa si los escaños no cuadran con el BOE.
    `avances` (de `leer_avances`) añade a cada ámbito las mesas constituidas y los avances de participación."""
    ref = _nombres()
    nacional = next(r for r in registros if r["tipo"] == "TO")
    av = {(a["tipo"], a["prov"]): a for a in avances or []}

    def _con_avances(r, nombre):
        a = _ambito(r, nombre)
        x = av.get((r["tipo"], r["prov"]))
        if x:
            a["mesas"] = {"total": x["mesas"], "constituidas": x["mesas_constituidas"], "suspendidas": x["mesas_suspendidas"]}
            a["avances"] = [k["pct"] for k in x["avances"]]
        return a

    provincias = {r["prov"]: _con_avances(r, ref[r["prov"]][0]) for r in registros if r["tipo"] == "PR"}
    avisos = [f"{p}: {a['escanos_total']} diputados en el fichero, {ref[p][1]} en el BOE"
              for p, a in provincias.items() if a["escanos_total"] != ref[p][1]]
    return {"id": "2026", "fecha": FECHA, "hora": _hora(nacional["fecha"]), "prueba": prueba, "simulacro": simulacro,
            "avisos": avisos,
            "nacional": _con_avances(nacional, "España"), "provincias": dict(sorted(provincias.items()))}


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
    cods = CODIGO
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


class Cliente:
    """Peticiones GET a la API de descargas. Dominio y credenciales, por variables de entorno:
    ELECCIONES_API_URL, ELECCIONES_API_USER, ELECCIONES_API_PASS. Autenticación HTTP básica (probada en el
    simulacro del 18-N); con ELECCIONES_API_AUTH=ninguna no se envía cabecera. El manual pide que la cabecera
    User-Agent no vaya vacía: se manda una fija (ELECCIONES_API_UA la cambia). `eleccion`: 2 = Congreso, 3 = Senado."""

    def __init__(self, base: str | None = None, usuario: str | None = None, clave: str | None = None):
        self.base = (base or os.environ["ELECCIONES_API_URL"]).rstrip("/")
        usuario = usuario or os.environ.get("ELECCIONES_API_USER", "")
        clave = clave or os.environ.get("ELECCIONES_API_PASS", "")
        self.cabeceras = {"User-Agent": os.environ.get("ELECCIONES_API_UA", "captura-29n/1.0 (python-urllib)")}
        if usuario and os.environ.get("ELECCIONES_API_AUTH", "basic") == "basic":
            self.cabeceras["Authorization"] = "Basic " + base64.b64encode(f"{usuario}:{clave}".encode()).decode()

    def pedir(self, ruta: str, espera: int = 60) -> bytes:
        req = urllib.request.Request(self.base + ruta, headers=self.cabeceras)
        with urllib.request.urlopen(req, timeout=espera) as r:
            return r.read()

    def envio(self, eleccion: int = 2) -> str:
        """Número del último envío (se toma el primer número de la respuesta)."""
        import re
        m = re.search(r"\d+", self.pedir(f"/descargas/csv/data/getEnvio/{eleccion}").decode("utf-8", errors="replace"))
        if not m:
            raise ValueError(f"getEnvio/{eleccion} no ha devuelto ningún número de envío")
        return m.group(0)

    def totales(self, envio: str, eleccion: int = 2) -> bytes:
        return self.pedir(f"/descargas/csv/data/getEscrutinioTotales/{eleccion}/{envio}")

    def municipios(self, prov: str, envio: str) -> bytes:
        return self.pedir(f"/descargas/csv/data/getEscrutinioMunicipios/2/{prov}/{envio}")

    def avances(self, envio: str) -> bytes:
        return self.pedir(f"/descargas/csv/data/getAvancesTotales/2/{envio}")

    def mesas(self, que: str, prov: str) -> bytes:
        """Ficheros por mesa de una provincia (sin número de envío; son grandes): `que` = «getAvances/2»,
        «getEscrutinio/2» (Congreso) o «getEscrutinio/3» (Senado)."""
        return self.pedir(f"/mesas/{que}/{prov}.csv", espera=600)


def texto(datos: bytes) -> str:
    """Los ficheros no declaran codificación: se intenta UTF-8 y, si no, Latin-1 (la de los ficheros de Interior)."""
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        return datos.decode("latin-1")


def descargar() -> str:
    """Último envío del Congreso: getEnvio/2 y getEscrutinioTotales/2/{numEnv}."""
    c = Cliente()
    return texto(c.totales(c.envio()))


def simulacro_web() -> dict:
    """Último envío del simulacro del 18 de noviembre (ficheros reales de Interior, datos ficticios)."""
    return a_web(leer_totales(texto((DATOS_SIMULACRO / "totales.csv").read_bytes())), simulacro=True,
                 avances=leer_avances(texto((DATOS_SIMULACRO / "avances.csv").read_bytes())))


NOMBRES = {"PP": "PP", "PSOE": "PSOE", "VOX": "Vox", "FA": "Frente Amplio", "PODEMOS": "Podemos", "SALF": "Se Acabó la Fiesta",
           "ERC": "ERC", "JUNTS": "Junts", "EH_BILDU": "EH Bildu", "PNV": "PNV", "BNG": "BNG", "CC": "Coalición Canaria",
           "COMPROMIS": "Compromís", "NC": "Nueva Canarias-Podemos-IU-Sumar", "ADELANTE": "Adelante Andalucía",
           "TERUEL_EXISTE": "Teruel Existe", "GBAI": "Geroa Bai", "PACMA": "PACMA"}
COLORES = {"PP": "#1D84CE", "PSOE": "#E30713", "VOX": "#5BA82B", "FA": "#E51C55", "PODEMOS": "#6B2E7A", "SALF": "#7A5230",
           "ERC": "#E0A020", "JUNTS": "#00A99D", "EH_BILDU": "#7BA21A", "PNV": "#0F6B3C", "BNG": "#5F93C0", "CC": "#C9A400",
           "COMPROMIS": "#D96A2B", "NC": "#3C8D5A", "ADELANTE": "#2AA198", "TERUEL_EXISTE": "#4B6B4F", "GBAI": "#B0333A",
           "PACMA": "#9BB52B"}
# Escaños de 2023 (oficiales) con los que se compara cada espacio; None = sin comparación directa (Sumar tuvo 31).
ESCANOS_2023 = {"PP": 138, "PSOE": 121, "VOX": 33, "ERC": 7, "JUNTS": 7, "EH_BILDU": 6, "PNV": 5, "BNG": 1, "CC": 1}
HORAS_AVANCE = ("14:00", "18:00")
# Avances nacionales de las dos generales anteriores, para comparar. Fuente: Ministerio del Interior, tomados de la
# tabla de Wikipedia que aportó Nacho (2026-11-19); por comunidades, en data/web/29n/participacion_avances_previos.csv.
# NO contrastados aquí con los ficheros de Interior (están en el PC; infoelectoral no responde desde la nube).
AVANCES_PREVIOS = {"14:00": {"2023": 40.48, "2019": 37.92}, "18:00": {"2023": 53.12, "2019": 56.86}}


def pantallas(web: dict, envio: str = "") -> dict:
    """Resumen mínimo del estado nacional para un proveedor externo (pantallas): pocas cifras y nombres legibles.
    Sale de la misma salida que pinta la web, así que ambas enseñan siempre lo mismo."""
    n = web["nacional"]
    partidos = [{"id": p["f"] if p["f"] != "OTROS" else p["s"], "nombre": NOMBRES.get(p["f"], p["s"]), "siglas": p["s"],
                 "escanos": p["e"], "votos": p["v"], "porcentaje": round(100 * p["v"] / n["validos"], 2) if n["validos"] else 0.0,
                 "escanos_2023": ESCANOS_2023.get(p["f"]), "color": COLORES.get(p["f"], "#8D98A6")}
                for p in n["partidos"] if p["e"] > 0 or (n["validos"] and p["v"] >= 0.01 * n["validos"])]
    av = n.get("avances") or []
    return {"eleccion": "Elecciones generales · " + web["fecha"], "simulacro": bool(web.get("simulacro")), "envio": envio,
            "actualizado": web["hora"], "fase": "escrutinio" if n["escrutado"] > 0 else "participacion" if any(av) else "previa",
            "escanos_total": n["escanos_total"], "mayoria_absoluta": n["escanos_total"] // 2 + 1,
            "escrutado_pct": n["escrutado"], "participacion_pct": n["participacion_residentes"] if n["escrutado"] > 0 else None,
            "electores": n["censo"], "votantes": n["votantes"], "votos_blancos": n["blancos"], "votos_nulos": n["nulos"],
            "mesas": n.get("mesas"),
            "avances": [{"hora": h, "participacion_pct": v, "participacion_2023_pct": AVANCES_PREVIOS[h]["2023"],
                         "participacion_nov2019_pct": AVANCES_PREVIOS[h]["2019"]} for h, v in zip(HORAS_AVANCE, av) if v > 0],
            "partidos": partidos,
            "nota": "Recuento provisional del Ministerio del Interior. Porcentajes sobre votos válidos. Sin voto exterior (CERA)."}


def pantallas_csv(d: dict) -> str:
    """El mismo resumen en CSV (separador «;», decimales con punto): una fila por dato general y una por partido."""
    # En las filas «avance», la última columna es la participación a esa hora en julio de 2023.
    filas = [["tipo", "id", "nombre", "escanos", "votos", "porcentaje", "escanos_2023"],
             ["general", "actualizado", d["actualizado"], "", "", "", ""],
             ["general", "escrutado_pct", "", "", "", d["escrutado_pct"], ""],
             ["general", "participacion_pct", "", "", "", "" if d["participacion_pct"] is None else d["participacion_pct"], ""]]
    filas += [["avance", a["hora"], "", "", "", a["participacion_pct"], a["participacion_2023_pct"]] for a in d["avances"]]
    filas += [["partido", p["id"], p["nombre"], p["escanos"], p["votos"], p["porcentaje"],
               "" if p["escanos_2023"] is None else p["escanos_2023"]] for p in d["partidos"]]
    return "\r\n".join(";".join(str(c) for c in f) for f in filas) + "\r\n"


def guardar_pantallas(web: dict, envio: str = "", salida: Path = PANTALLAS) -> Path:
    d = pantallas(web, envio)
    guardar(d, salida)
    salida.with_suffix(".csv").write_text(pantallas_csv(d), encoding="utf-8", newline="")
    return salida


def guardar(datos: dict, salida: Path) -> Path:
    salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return salida


def vaciar(salida: Path = VIVO) -> list[Path]:
    """Deja sin escrutinio los ficheros que lee la web: recuento, resumen para pantallas y proyección."""
    return [guardar(vacio(), salida), guardar_pantallas(vacio(), salida=salida.with_name("pantallas_29n.json")),
            guardar({"escrutado": 0, "nacional": {"escanos": {}, "pct": {}}, "provincias": {}},
                    salida.with_name("proyeccion_29n.json"))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fichero", nargs="?")
    ap.add_argument("--vacio", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--simulacro-web", action="store_true", help="regenera web/data/simulacro_29n.json")
    ap.add_argument("--descargar", action="store_true")
    a = ap.parse_args()
    if a.simulacro_web:
        print(guardar(simulacro_web(), SIMULACRO), guardar_pantallas(simulacro_web(), "130", PANTALLAS_EJEMPLO))
    elif a.demo:
        print(guardar(a_web(leer_totales(demo()), prueba=True), DEMO))
    elif a.vacio:
        print(*vaciar())
    else:
        texto = descargar() if a.descargar else Path(a.fichero).read_text(encoding="utf-8", errors="replace")
        web = a_web(leer_totales(texto))
        print(guardar(web, VIVO), f"escrutado {web['nacional']['escrutado']} %", *web["avisos"])
