"""Mapa de provincias para la web: web/data/provincias.js (trazados SVG ya proyectados).

    python -m pipeline.export_provincias

Sale de web/data/municipios.geojson (límites municipales del INE, CC BY 4.0): se unen los municipios
de cada provincia y se simplifica conservando las fronteras compartidas. Proyección plana sencilla
(longitud × cos 40°). Canarias se dibuja desplazada, en un recuadro abajo a la izquierda; Ceuta y
Melilla, además de su contorno, llevan un punto (`puntos`) para que se puedan ver y pulsar.
Se guarda como script (window.MAPA_PROV) para que funcione también abriendo index.html desde el disco.
"""
from __future__ import annotations

import json
import math

import shapely
from shapely.affinity import translate
from shapely.geometry import shape
from shapely.ops import unary_union

from . import config as C

ENTRADA = C.REPO / "web" / "data" / "municipios.geojson"
SALIDA = C.REPO / "web" / "data" / "provincias.js"
ANCHO = 600
TOLERANCIA = 0.012          # grados (~1 km): suficiente para un mapa de 600 px
CANARIAS = {"35", "38"}
DESPLAZA = (5.4, 6.7)       # grados que se mueve Canarias (este, norte)
K = math.cos(math.radians(40))


def build() -> dict:
    g = json.loads(ENTRADA.read_text(encoding="utf-8"))
    por_prov: dict[str, list] = {}
    for f in g["features"]:
        por_prov.setdefault(f["properties"]["id"][:2], []).append(shape(f["geometry"]).buffer(0))
    cods = sorted(por_prov)
    geoms = [unary_union(por_prov[c]).buffer(0.0005).buffer(-0.0005) for c in cods]   # cierra rendijas entre municipios
    geoms = list(shapely.coverage_simplify(geoms, TOLERANCIA)) if shapely.coverage_is_valid(geoms).all() \
        else [x.simplify(TOLERANCIA, preserve_topology=True) for x in geoms]
    geoms = [translate(x, *DESPLAZA) if c in CANARIAS else x for c, x in zip(cods, geoms)]
    minx = min(x.bounds[0] for x in geoms); maxx = max(x.bounds[2] for x in geoms)
    miny = min(x.bounds[1] for x in geoms); maxy = max(x.bounds[3] for x in geoms)
    esc = (ANCHO - 8) / ((maxx - minx) * K)
    px = lambda lon, lat: (round(4 + (lon - minx) * K * esc, 1), round(4 + (maxy - lat) * esc, 1))

    def trazado(geom) -> str:
        partes = []
        for pol in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            if pol.area < 2e-4 and geom.area > 0.01:      # islotes diminutos de provincias grandes
                continue
            for anillo in [pol.exterior, *pol.interiors]:
                pts = [px(*c) for c in anillo.coords]
                pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
                if len(pts) >= 4:
                    partes.append("M" + "L".join(f"{x},{y}" for x, y in pts[:-1]) + "Z")
        return "".join(partes)

    can = unary_union([x for c, x in zip(cods, geoms) if c in CANARIAS]).bounds
    x0, y1 = px(can[0], can[1]); x1, y0 = px(can[2], can[3])
    out = {"ancho": ANCHO, "alto": round(16 + (maxy - miny) * esc),   # margen para el recuadro de Canarias
           "p": {c: trazado(x) for c, x in zip(cods, geoms)},
           "puntos": {c: list(px(*geoms[cods.index(c)].centroid.coords[0])) for c in ("51", "52")},
           "canarias": [max(1, round(x0 - 6)), round(y0 - 6), round(x1 - x0 + 12), round(y1 - y0 + 12)]}
    SALIDA.write_text("window.MAPA_PROV=" + json.dumps(out, separators=(",", ":")) + ";", encoding="utf-8")
    return out


if __name__ == "__main__":
    o = build()
    print(SALIDA, SALIDA.stat().st_size, "bytes;", len(o["p"]), "provincias;", o["ancho"], "x", o["alto"])
