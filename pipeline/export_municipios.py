"""Resultados OFICIALES por municipio (10 elecciones al Congreso) para la web: web/data/mun/NN.json.

    python -m pipeline.export_municipios

Fuente: ficheros 03 (siglas), 05 (datos globales municipales) y 06 (votos por candidatura y
municipio) de Interior; solo las filas de total municipal (distrito 99). El CERA no está en estos
ficheros (no es asignable a un municipio), así que la participación es la de residentes.
Los porcentajes de la web se calculan sobre votos válidos (candidaturas + blancos).

Formato de cada municipio: {"n": nombre, "h": {"2023": [censo, votantes, blancos, nulos, candidaturas,
[[código_candidatura, votos], ...]]}}. Solo se guardan las candidaturas con >= 1,5 % de los votos
válidos del municipio (máximo 8); el resto se deduce por diferencia. web/data/partidos.json traduce
los códigos de cada elección a siglas y familia (familia: clasificación de Mikel Ibáñez).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config as C
from .audit_interior import DEFAULT, ELECCIONES
from .export_web import CLASIF, _familias, _lines

SALIDA = C.REPO / "web" / "data"
UMBRAL_PARTIDO = 0.015
MAX_PARTIDOS = 8
_ARTICULO = re.compile(r"^(.+), (el|la|los|las|l'|a|o|as|os|els|les|es|sa|ses|na|n')$", re.I)


def nombre_visible(n: str) -> str:
    """'Coruña, A' -> 'A Coruña'; 'Alcora, l'' -> 'l'Alcora' (el INE invierte el artículo)."""
    m = _ARTICULO.match(n.strip())
    if not m:
        return n.strip()
    base, art = m.groups()
    return f"{art}{base}" if art.endswith("'") else f"{art} {base}"


def leer_eleccion(base: Path, per: str):
    d = base / f"02{per}_MESA"
    muni = {}
    for ln in _lines(d / f"0502{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(17, 18) != "99":
            continue
        muni[g(12, 13) + g(14, 16)] = {"n": g(19, 118).strip(), "censo": int(g(150, 157)),
                                       "blancos": int(g(190, 197)), "nulos": int(g(198, 205)),
                                       "cand": int(g(206, 213)), "votos": []}
    for ln in _lines(d / f"0602{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(15, 16) != "99":
            continue
        mid = g(10, 11) + g(12, 14)
        if mid in muni:
            muni[mid]["votos"].append((g(17, 22), int(g(23, 30))))
    siglas = {ln[8:14]: ln[14:64].strip() for ln in _lines(d / f"0302{per[2:]}.DAT")}
    return muni, siglas


def build(base: Path = DEFAULT, salida: Path = SALIDA) -> dict:
    fam = _familias()
    por_id: dict[str, dict] = {}
    partidos: dict[str, dict] = {}
    for per, el in ELECCIONES.items():
        muni, siglas = leer_eleccion(base, per)
        usados: set[str] = set()
        for mid, m in muni.items():
            validos = m["cand"] + m["blancos"]
            votos = sorted((v for v in m["votos"] if v[1] >= UMBRAL_PARTIDO * validos), key=lambda x: -x[1])[:MAX_PARTIDOS]
            usados.update(c for c, _ in votos)
            registro = por_id.setdefault(mid, {"n": m["n"], "h": {}})
            registro["n"] = m["n"]  # se queda el nombre de la última elección en la que existe
            registro["h"][el] = [m["censo"], m["cand"] + m["blancos"] + m["nulos"], m["blancos"], m["nulos"], m["cand"],
                                 [[c, v] for c, v in votos]]
        partidos[el] = {c: [siglas.get(c, c), fam.get((el, c), "OTROS")] for c in sorted(usados)}
    (salida / "mun").mkdir(parents=True, exist_ok=True)
    por_prov: dict[str, dict] = {}
    for mid, r in por_id.items():
        r["n"] = nombre_visible(r["n"])
        por_prov.setdefault(mid[:2], {})[mid] = r
    for prov, d in por_prov.items():
        (salida / "mun" / f"{prov}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (salida / "partidos.json").write_text(json.dumps(partidos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # índice de búsqueda: id, nombre, provincia (compacto)
    indice = sorted(([mid, r["n"]] for mid, r in por_id.items()), key=lambda x: x[0])
    (salida / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"municipios": len(por_id), "provincias": len(por_prov)}


if __name__ == "__main__":
    print(build())
