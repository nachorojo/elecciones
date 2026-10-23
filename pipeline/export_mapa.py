"""Mapa municipal para la web: web/data/municipios.geojson a partir de la cartografía oficial del INE.

    python -m pipeline.export_mapa [carpeta_con_paginas_de_distritos]

Entrada: páginas GeoJSON de distritos (capa SU.VectorStatisticalUnit, TIPO = 'DISTRITO') del
GeoServer del INE (https://www.ine.es/geoserver/ogc/features/v1/collections/
WMS_INE_SECCIONES_G01:SU.VectorStatisticalUnit/items, paginando con startIndex). Ver
`descargar_distritos`. La capa vigente es la de 2026 (la del 29N).

Proceso: unión de los distritos de cada municipio (CUMUN = provincia + municipio), simplificación
que conserva las fronteras compartidas entre municipios (coverage_simplify) y coordenadas a 4
decimales (~11 m). Fuente de los datos: Instituto Nacional de Estadística, licencia CC BY 4.0
(la web debe citarlo).
"""
from __future__ import annotations

import glob
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import shapely
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from . import config as C

BASE = "https://www.ine.es/geoserver/ogc/features/v1/collections/WMS_INE_SECCIONES_G01:SU.VectorStatisticalUnit/items"
CONSULTA = "f=json&filter-lang=cql-text&filter=TIPO%3D%27DISTRITO%27&properties=CUMUN,CUDIS,NMUN,NPRO,CPRO,TIPO"
SALIDA = C.REPO / "web" / "data" / "municipios.geojson"
TOLERANCIA = 0.003  # grados (~300 m): 6 MB; solo 12 de 8.132 municipios pierden >10 % de superficie
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"


def descargar_distritos(destino: Path, pagina: int = 100, hilos: int = 4) -> None:
    """Descarga todas las páginas de distritos (unos 100-150 MB). Idempotente."""
    destino.mkdir(parents=True, exist_ok=True)
    total = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{BASE}?{CONSULTA}&limit=1", headers={"User-Agent": UA}), timeout=120))["numberMatched"]

    def pedir(inicio: int):
        f = destino / f"p{inicio:06d}.json"
        if f.exists() and f.stat().st_size > 1000:
            return
        for intento in range(5):
            try:
                req = urllib.request.Request(f"{BASE}?{CONSULTA}&limit={pagina}&startIndex={inicio}", headers={"User-Agent": UA})
                datos = urllib.request.urlopen(req, timeout=180).read()
                json.loads(datos)
                f.write_bytes(datos)
                return
            except Exception:
                time.sleep(3 * (intento + 1))
        raise RuntimeError(f"no se pudo descargar la página {inicio}")

    with ThreadPoolExecutor(hilos) as ex:
        list(ex.map(pedir, range(0, total, pagina)))


def cargar(carpeta: Path) -> dict[str, list]:
    por_municipio: dict[str, list] = {}
    vistos: set[str] = set()
    for f in sorted(glob.glob(str(carpeta / "p*.json"))):
        for ft in json.load(open(f, encoding="utf-8"))["features"]:
            p = ft["properties"]
            if p["CUDIS"] in vistos:
                continue
            vistos.add(p["CUDIS"])
            por_municipio.setdefault(p["CUMUN"], []).append(shape(ft["geometry"]))
    return por_municipio


def construir(carpeta: Path, salida: Path = SALIDA, tolerancia: float = TOLERANCIA) -> dict:
    por_municipio = cargar(carpeta)
    ids = sorted(por_municipio)
    unidos = [unary_union(por_municipio[i]) for i in ids]
    try:
        simples = list(shapely.coverage_simplify(unidos, tolerancia))
        metodo = "coverage_simplify"
    except Exception:  # cobertura no válida: simplificación por polígono (puede dejar rendijas)
        simples = [g.simplify(tolerancia, preserve_topology=True) for g in unidos]
        metodo = "simplify(preserve_topology)"
    features = []
    for i, g in zip(ids, simples):
        g = shapely.set_precision(g, 0.0001) if not g.is_empty else g
        if g.is_empty:
            continue
        features.append({"type": "Feature", "properties": {"id": i}, "geometry": mapping(g)})
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
    return {"municipios": len(features), "distritos": sum(len(v) for v in por_municipio.values()),
            "metodo": metodo, "bytes": salida.stat().st_size}


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "AppData" / "Local" / "Temp" / "carto" / "distritos"
    print(construir(carpeta))
