"""Resultados OFICIALES por sección censal (2019 abril, 2019 noviembre y 2023) para la web: web/data/sec/NN.json.

    python -m pipeline.export_secciones

Fuente: ficheros 03 (siglas), 09 (datos de mesa) y 10 (votos por candidatura y mesa) de Interior,
agregando las mesas de cada sección. Se excluye el CERA (municipio 999). Clave de sección: provincia(2) +
municipio(3) + distrito(2) + sección(3), la misma que el CUSEC del INE.

Formato por sección y elección: [censo, votantes, blancos, nulos, candidaturas, [[cód, votos] x3 (top 3)],
cód_ganador_anterior | null, cambio(0/1) | null].

El ganador anterior y el cambio solo se informan cuando la comparación es legítima: el municipio conserva
exactamente los mismos distritos que en la elección anterior, la sección existe en ambas y su censo no varía
más de un 25 %/33 % (si no, el mismo código puede ser otro territorio: problema 7 del CLAUDE.md).
Ganador "cambia" = cambia la familia de partido (clasificación de Mikel Ibáñez) o, si no hay familia,
las siglas.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from . import config as C
from .audit_interior import DEFAULT
from .export_web import _familias, _lines

SALIDA = C.REPO / "web" / "data"
# (carpeta de Interior, id de elección) en orden cronológico
ELECCIONES_SEC = [("201904", "2019a"), ("201911", "2019b"), ("202307", "2023")]
TOP = 3


def leer(base: Path, per: str):
    """Agrega las mesas por sección: {sección: {censo, blancos, nulos, cand, votos{cod: v}}} y distritos por municipio."""
    d = base / f"02{per}_MESA"
    sec: dict[str, dict] = {}
    distritos: dict[str, set] = defaultdict(set)
    for ln in _lines(d / f"0902{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(14, 16) == "999":
            continue
        s = g(12, 13) + g(14, 16) + g(17, 18) + g(19, 22).strip()
        r = sec.setdefault(s, {"censo": 0, "blancos": 0, "nulos": 0, "cand": 0, "votos": defaultdict(int)})
        r["censo"] += int(g(31, 37)); r["blancos"] += int(g(66, 72)); r["nulos"] += int(g(73, 79)); r["cand"] += int(g(80, 86))
        distritos[g(12, 13) + g(14, 16)].add(g(17, 18))
    for ln in _lines(d / f"1002{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(14, 16) == "999":
            continue
        sec[g(12, 13) + g(14, 16) + g(17, 18) + g(19, 22).strip()]["votos"][g(24, 29)] += int(g(30, 36))
    siglas = {ln[8:14]: ln[14:64].strip() for ln in _lines(d / f"0302{per[2:]}.DAT")}
    return sec, distritos, siglas


def build(base: Path = DEFAULT, salida: Path = SALIDA) -> dict:
    fam = _familias()
    datos, partidos, anterior = {}, {}, None
    for per, el in ELECCIONES_SEC:
        sec, distritos, siglas = leer(base, per)
        datos[el] = (sec, distritos, siglas)
        partidos[el] = {}

    def clave(el, cod, siglas):
        f = fam.get((el, cod), "OTROS")
        return f if f != "OTROS" else "S:" + siglas.get(cod, cod).upper()

    por_prov: dict[str, dict] = defaultdict(lambda: defaultdict(dict))
    resumen = {}
    for i, (per, el) in enumerate(ELECCIONES_SEC):
        sec, distritos, siglas = datos[el]
        prev = datos[ELECCIONES_SEC[i - 1][1]] if i else None
        n_comp = n_cambio = 0
        for s, r in sec.items():
            top = sorted(r["votos"].items(), key=lambda x: -x[1])[:TOP]
            fila = [r["censo"], r["cand"] + r["blancos"] + r["nulos"], r["blancos"], r["nulos"], r["cand"], [[c, v] for c, v in top],
                    None, None]
            for c, _ in top:
                partidos[el][c] = [siglas.get(c, c), fam.get((el, c), "OTROS")]
            if prev and top:
                psec, pdis, psig = prev[0], prev[1], prev[2]
                p = psec.get(s)
                muni = s[:5]
                if p and p["votos"] and distritos[muni] == pdis.get(muni) and p["censo"] and 0.75 <= r["censo"] / p["censo"] <= 1.33:
                    pc = max(p["votos"].items(), key=lambda x: x[1])[0]
                    fila[6] = pc
                    fila[7] = int(clave(el, top[0][0], siglas) != clave(ELECCIONES_SEC[i - 1][1], pc, psig))
                    partidos[ELECCIONES_SEC[i - 1][1]].setdefault(pc, [psig.get(pc, pc), fam.get((ELECCIONES_SEC[i - 1][1], pc), "OTROS")])
                    n_comp += 1; n_cambio += fila[7]
            por_prov[s[:2]].setdefault(s, {})[el] = fila
        resumen[el] = {"secciones": len(sec), "comparables": n_comp, "cambian": n_cambio}
    (salida / "sec").mkdir(parents=True, exist_ok=True)
    for prov, d in por_prov.items():
        (salida / "sec" / f"{prov}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (salida / "partidos_sec.json").write_text(json.dumps(partidos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return resumen


if __name__ == "__main__":
    print(build())
