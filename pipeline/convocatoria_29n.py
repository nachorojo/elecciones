"""Convocatoria del 29 de noviembre de 2026: escaños por circunscripción y candidaturas al Congreso.

    python -m pipeline.convocatoria_29n            # usa la copia local del BOE si existe; si no, la descarga

Fuentes (BOE, públicas, sin credenciales):
  - Real Decreto 806/2026, de 5 de octubre (BOE-A-2026-20742): el anexo da los diputados de cada
    circunscripción.
  - Candidaturas proclamadas (BOE-A-2026-23103, BOE de 3 de noviembre) y su corrección de errores
    (BOE-A-2026-23383, BOE de 7 de noviembre).

Salidas (pequeñas, van a la repo):
  data/web/29n/escanos.csv                 provincia, nombre, escaños 29N, escaños 2023
  data/web/29n/candidaturas_congreso.csv   provincia, orden, denominación, siglas, espacio
  web/data/29n.json                        lo mismo, para la web

`espacio` es la agrupación que usa el simulador (PP, PSOE, VOX, FA, PODEMOS, SALF…). Es una
clasificación PROVISIONAL hecha por reglas sobre las siglas: hay que validarla con la Redacción.
"""
from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

from . import config as C

BOE = "https://www.boe.es/diario_boe/xml.php?id="
DOCS = {"decreto": "BOE-A-2026-20742", "proclamadas": "BOE-A-2026-23103", "correccion": "BOE-A-2026-23383"}
CACHE = C.REPO.parent / "datos" / "boe"
OUT_CSV = C.REPO / "data" / "web" / "29n"
OUT_JSON = C.REPO / "web" / "data" / "29n.json"
RESULTADOS = C.REPO / "web" / "data" / "resultados.json"

# Nombre de la circunscripción (sin tildes, en minúsculas, tal como sale del BOE) -> código INE de provincia.
PROVINCIAS = {
    "albacete": "02", "alicante": "03", "alicante/alacant": "03", "almeria": "04", "alava": "01",
    "araba/alava": "01", "asturias": "33", "avila": "05", "badajoz": "06", "illes balears": "07",
    "balears (illes)": "07", "barcelona": "08", "bizkaia": "48", "burgos": "09", "caceres": "10",
    "cadiz": "11", "cantabria": "39", "castellon": "12", "castellon/castello": "12", "ciudad real": "13",
    "cordoba": "14", "a coruna": "15", "coruna (a)": "15", "cuenca": "16", "gipuzkoa": "20", "girona": "17",
    "granada": "18", "guadalajara": "19", "huelva": "21", "huesca": "22", "jaen": "23", "leon": "24",
    "lleida": "25", "lugo": "27", "madrid": "28", "malaga": "29", "murcia": "30", "navarra": "31",
    "ourense": "32", "palencia": "34", "las palmas": "35", "palmas (las)": "35", "pontevedra": "36",
    "la rioja": "26", "rioja (la)": "26", "salamanca": "37", "santa cruz de tenerife": "38", "segovia": "40",
    "sevilla": "41", "soria": "42", "tarragona": "43", "teruel": "44", "toledo": "45", "valencia": "46",
    "valencia/valencia": "46", "valladolid": "47", "zamora": "49", "zaragoza": "50", "ceuta": "51",
    "melilla": "52",
}
NUMEROS = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
           "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
           "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "treinta": 30, "cuarenta": 40}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip(" .")


def _numero(s: str) -> int:
    """'Treinta y ocho' -> 38."""
    return sum(NUMEROS[p] for p in _norm(s).split() if p != "y")


def descargar(cache: Path = CACHE) -> dict[str, Path]:
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for nombre, ident in DOCS.items():
        p = cache / f"{ident}.xml"
        if not p.exists():
            with urllib.request.urlopen(BOE + ident, timeout=120) as r:
                p.write_bytes(r.read())
        out[nombre] = p
    return out


def _parrafos(path: Path) -> list[str]:
    t = path.read_text(encoding="utf-8")
    t = t[t.rfind("<texto>"):]
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()
            for x in re.findall(r"<(?:p|td|th)\b[^>]*>(.*?)</(?:p|td|th)>", t, flags=re.S)]


def leer_escanos(path: Path) -> dict[str, int]:
    """Anexo del real decreto: pares (circunscripción, número en letra)."""
    ps = _parrafos(path)
    ps = ps[max(i for i, x in enumerate(ps) if _norm(x) == "anexo"):]
    out = {}
    for a, b in zip(ps, ps[1:]):
        if _norm(a) in PROVINCIAS and all(p in NUMEROS or p == "y" for p in _norm(b).split()):
            out[PROVINCIAS[_norm(a)]] = _numero(b)
    return out


_TITULO = re.compile(r"^(\d+)\.\s*(.+?)\s*(?:\(([^()]*(?:\([^()]*\)[^()]*)*)\))?\.?$")


def _parrafos_con_clase(path: Path) -> list[tuple[str, str]]:
    t = path.read_text(encoding="utf-8")
    t = t[t.rfind("<texto>"):]
    return [(c, re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip())
            for c, x in re.findall(r'<p class="([^"]+)"[^>]*>(.*?)</p>', t, flags=re.S)]


def leer_candidaturas(path: Path) -> list[dict]:
    """Candidaturas proclamadas al Congreso por circunscripción (una fila por lista).

    En el XML del BOE el título de cada lista va en un párrafo de clase `centro_redonda`
    («5. VOX (VOX)»); los candidatos, en `parrafo`/`parrafo_2`. No sirve distinguirlos por el
    texto: en las coaliciones los candidatos llevan su partido entre paréntesis. Las listas
    seguidas de «No proclamada.» se descartan (`proclamada = False` no se exporta).
    """
    ps = _parrafos_con_clase(path)
    filas, prov, camara = [], None, None
    for i, (clase, x) in enumerate(ps):
        m = re.match(r"^JUNTA ELECTORAL (?:PROVINCIAL )?DE (.+)$", x)
        if m:
            nueva = PROVINCIAS[_norm(m.group(1))]
            if nueva != prov:
                prov, camara = nueva, None
            continue
        n = _norm(x)
        if n == "congreso de los diputados":
            camara = "C"
        elif n == "senado":
            camara = "S"
        elif camara == "C" and prov and clase == "centro_redonda":
            m = _TITULO.match(x)
            if not m:
                raise ValueError(f"Título de candidatura no reconocido en {prov}: {x!r}")
            if i + 1 < len(ps) and _norm(ps[i + 1][1]).startswith("no proclamada"):
                continue
            den = m.group(2).strip()
            filas.append({"provincia": prov, "orden": int(m.group(1)), "denominacion": den,
                          "siglas": re.sub(r"\s+", " ", m.group(3)).strip() if m.group(3) else den})
    return filas


def aplicar_correcciones(filas: list[dict]) -> list[dict]:
    """Correcciones del BOE de 7 de noviembre que afectan a la denominación de listas al Congreso.

    Navarra: «EUSKAL HERRIA BILDU-ESQUERRA REPUBLICANA DE CATALUNYA (EH BILDU-ERC)» debe decir
    «EUSKAL HERRIA BILDU (EH BILDU)». El resto de correcciones son nombres de candidatos.
    """
    for f in filas:
        if f["provincia"] == "31" and _norm(f["siglas"]).replace(" ", "") == "ehbildu-erc":
            f["denominacion"], f["siglas"] = "EUSKAL HERRIA BILDU", "EH BILDU"
    return filas


# Reglas de clasificación (sobre siglas + denominación sin tildes). El orden importa.
_REGLAS = [
    ("PP", r"\bpp\b|partido popular"),
    ("PSOE", r"psoe|\bpsc\b|socialist"),
    ("VOX", r"\bvox\b"),
    ("SALF", r"\bsalf\b|se acabo la fiesta"),
    ("COMPROMIS", r"compromis"),
    ("NC", r"\bnc-bc\b|nueva canarias"),
    ("ADELANTE", r"adelante andalucia"),
    ("FA", r"frente amplio|front ampli|fronte ampl|fronte zabala|\bfa\b|arames|\bcomuns\b"),
    ("PODEMOS", r"podemos|\bpodem\b|paz, ?casa y trabajo"),   # «PAZ,CASA Y TRABAJO»: siglas de Podemos en Ceuta
    ("EH_BILDU", r"bildu"),
    ("ERC", r"\berc\b|esquerra republicana"),
    ("JUNTS", r"jxcat|junts"),
    ("PNV", r"pnv"),
    ("BNG", r"b\.?n\.?g|bloque nacionalista galego"),
    ("CC", r"\bcca\b|coalicion canaria"),
    ("TERUEL_EXISTE", r"teruel existe"),
    ("GBAI", r"gbai|geroa bai"),
    ("PACMA", r"pacma"),
]


def espacio(denominacion: str, siglas: str) -> str:
    t = _norm(siglas) + " | " + _norm(denominacion)
    for esp, patron in _REGLAS:
        if re.search(patron, t):
            return esp
    return "OTROS"


def _escanos_2023() -> dict[str, dict]:
    d = json.loads(RESULTADOS.read_text(encoding="utf-8"))
    e = next(x for x in d["elecciones"] if x["id"] == "2023")
    return {k: {"nombre": p["nombre"], "escanos": p["escanos_total"]} for k, p in e["provincias"].items()}


def build(cache: Path = CACHE) -> dict:
    docs = descargar(cache)
    escanos = leer_escanos(docs["decreto"])
    cands = aplicar_correcciones(leer_candidaturas(docs["proclamadas"]))
    for f in cands:
        f["espacio"] = espacio(f["denominacion"], f["siglas"])
    previo = _escanos_2023()
    OUT_CSV.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV / "escanos.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["provincia", "nombre", "escanos_29n", "escanos_2023"])
        for k in sorted(escanos):
            w.writerow([k, previo[k]["nombre"], escanos[k], previo[k]["escanos"]])
    with open(OUT_CSV / "candidaturas_congreso.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["provincia", "orden", "denominacion", "siglas", "espacio"])
        w.writeheader()
        w.writerows(cands)
    out = {"fuente": {k: BOE + v for k, v in DOCS.items()}, "escanos": dict(sorted(escanos.items())),
           "candidaturas": {}}
    for f in cands:
        out["candidaturas"].setdefault(f["provincia"], []).append({"s": f["siglas"], "n": f["denominacion"], "e": f["espacio"]})
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


if __name__ == "__main__":
    o = build()
    n = sum(len(v) for v in o["candidaturas"].values())
    print(f"{len(o['escanos'])} circunscripciones, {sum(o['escanos'].values())} escaños, {n} candidaturas al Congreso")
