"""Exporta a web/data/resultados.json los resultados OFICIALES de Interior (España y provincias, 10 elecciones).

    python -m pipeline.export_web

Fuente: ficheros 03 (siglas), 07 (totales por provincia) y 08 (votos y escaños por candidatura)
de Interior, que incluyen el voto CERA. Los porcentajes de la web se calculan sobre VOTOS VÁLIDOS
(candidaturas + blancos), como los publica Interior; no sobre votos a candidaturas.
Las familias de partido (solo para colorear) vienen de la clasificación de candidaturas de Mikel
Ibáñez (data/web/candidaturas_clasificadas_mikel.csv).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import cera, config as C
from .audit_interior import DEFAULT, ELECCIONES

FECHAS = {"1996": "3 de marzo de 1996", "2000": "12 de marzo de 2000", "2004": "14 de marzo de 2004",
          "2008": "9 de marzo de 2008", "2011": "20 de noviembre de 2011", "2015": "20 de diciembre de 2015",
          "2016": "26 de junio de 2016", "2019a": "28 de abril de 2019", "2019b": "10 de noviembre de 2019",
          "2023": "23 de julio de 2023"}
CLASIF = C.REPO / "data" / "web" / "candidaturas_clasificadas_mikel.csv"
SALIDA = C.REPO / "web" / "data" / "resultados.json"


def _lines(path: Path):
    with open(path, encoding="latin-1", newline="") as f:
        for ln in f:
            ln = ln.rstrip("\r\n")
            if ln:
                yield ln


def _familias() -> dict[tuple[str, str], str]:
    with open(CLASIF, encoding="utf-8", newline="") as f:
        return {(r["eleccion"], r["codigo"]): r["familia"] for r in csv.DictReader(f)}


def _ambito(base: Path, per: str, el: str, fam: dict, siglas: dict[str, str]) -> dict:
    """{'nacional': {...}, 'provincias': {cod: {...}}} para una elección."""
    d = base / f"02{per}_MESA"
    tot, votos = {}, {}
    for ln in _lines(d / f"0702{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(14, 14) != "9":
            continue
        clave = "nacional" if g(10, 11) == "99" and g(12, 13) == "99" else (g(12, 13) if g(12, 13) != "99" else None)
        if clave is None:
            continue
        cand, blancos, nulos, censo = int(g(142, 149)), int(g(126, 133)), int(g(134, 141)), int(g(86, 93))
        tot[clave] = {"nombre": "España" if clave == "nacional" else g(15, 64).strip(), "censo": censo,
                      "votantes": cand + blancos + nulos, "blancos": blancos, "nulos": nulos, "candidaturas": cand,
                      "validos": cand + blancos, "escanos_total": int(g(150, 155))}
    for ln in _lines(d / f"0802{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(14, 14) != "9":
            continue
        clave = "nacional" if g(10, 11) == "99" and g(12, 13) == "99" else (g(12, 13) if g(12, 13) != "99" else None)
        if clave is None:
            continue
        votos.setdefault(clave, []).append((g(15, 20), int(g(21, 28)), int(g(29, 33))))
    # El censo/votantes de Interior incluyen el CERA (voto exterior, muy baja participación). La
    # participación "habitual" es la de residentes: se resta el CERA y se da aparte.
    exterior = {r[1]: r for r in cera.read_cera_totales(d / f"0902{per[2:]}.DAT", el)}
    exterior["nacional"] = (el, "99", "09") + tuple(sum(r[i] for r in exterior.values()) for i in range(3, 7)) + ("S",)
    out = {}
    for clave, t in tot.items():
        _, _, _, c_censo, c_bl, c_nu, c_cand, _ = exterior[clave] if clave in exterior else (0,) * 8
        t["cera"] = {"censo": c_censo, "votantes": c_cand + c_bl + c_nu, "votos": c_cand}
        t["participacion_residentes"] = round(100 * (t["votantes"] - t["cera"]["votantes"]) / (t["censo"] - c_censo), 2)
        partidos, otros = [], 0
        for cod, v, e in sorted(votos.get(clave, []), key=lambda x: -x[1]):
            if e > 0 or v >= 0.01 * t["validos"]:
                partidos.append({"c": cod, "s": siglas.get(cod, cod), "f": fam.get((el, cod), "OTROS"), "v": v, "e": e})
            else:
                otros += v
        t["partidos"] = partidos
        t["otros"] = otros
        out[clave] = t
    return out


def build(base: Path = DEFAULT, salida: Path = SALIDA) -> Path:
    fam = _familias()
    elecciones = []
    for per, el in ELECCIONES.items():
        siglas = {ln[8:14]: ln[14:64].strip() for ln in _lines(base / f"02{per}_MESA" / f"0302{per[2:]}.DAT")}
        ambito = _ambito(base, per, el, fam, siglas)
        elecciones.append({"id": el, "fecha": FECHAS[el], "nacional": ambito.pop("nacional"), "provincias": ambito})
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({"elecciones": elecciones}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return salida


if __name__ == "__main__":
    p = build()
    print(p, p.stat().st_size, "bytes")
