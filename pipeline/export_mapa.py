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

SALIDA = C.REPO / "web" / "data" / "municipios.geojson"
TOLERANCIA = 0.003  # grados (~300 m): 6 MB; solo 12 de 8.132 municipios pierden >10 % de superficie
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"


def descargar_capa(capa: str, destino: Path, filtro: str, props: str, pagina: int = 100, hilos: int = 4) -> int:
    """Descarga todas las páginas de una capa del GeoServer del INE (paginando con startIndex).

    `capa`: p. ej. 'WMS_INE_SECCIONES_G01:Secciones_2023'. `filtro`: CQL ya codificado, p. ej.
    "CSEC%3C%3E%27000%27" (secciones; en las capas por año las secciones llevan TIPO='SECCIONADO' y los
    distritos TIPO='DISTRITO', CSEC='000'). Idempotente. Devuelve el número de entidades esperado.
    """
    base = f"https://www.ine.es/geoserver/ogc/features/v1/collections/{capa}/items"
    consulta = f"f=json&filter-lang=cql-text&filter={filtro}&properties={props}"
    destino.mkdir(parents=True, exist_ok=True)
    total = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{base}?{consulta}&limit=1", headers={"User-Agent": UA}), timeout=120))["numberMatched"]

    def pedir(inicio: int):
        f = destino / f"p{inicio:06d}.json"
        if f.exists() and f.stat().st_size > 1000:
            return
        for intento in range(5):
            try:
                req = urllib.request.Request(f"{base}?{consulta}&limit={pagina}&startIndex={inicio}", headers={"User-Agent": UA})
                datos = urllib.request.urlopen(req, timeout=240).read()
                json.loads(datos)
                f.write_bytes(datos)
                return
            except Exception:
                time.sleep(3 * (intento + 1))
        raise RuntimeError(f"no se pudo descargar la página {inicio} de {capa}")

    with ThreadPoolExecutor(hilos) as ex:
        list(ex.map(pedir, range(0, total, pagina)))
    return total


def descargar_distritos(destino: Path) -> int:
    """Distritos de la capa vigente (2026): unos 10.452 polígonos, 100-150 MB."""
    return descargar_capa("WMS_INE_SECCIONES_G01:SU.VectorStatisticalUnit", destino,
                          "TIPO%3D%27DISTRITO%27", "CUMUN,CUDIS,NMUN,NPRO,CPRO,TIPO")


def descargar_secciones(anio: int, destino: Path, pagina: int = 100, hilos: int = 4) -> int:
    """Secciones censales de un año (capa Secciones_AAAA; 2007-2025): ~36.000 polígonos, de 250 a 400 MB.

    Se descarga provincia a provincia (filtro CUSEC LIKE 'NN%'): el servidor tarda 40 s por página con
    desplazamientos grandes y 7 s con desplazamientos pequeños. Idempotente."""
    capa = f"WMS_INE_SECCIONES_G01:Secciones_{anio}"
    base = f"https://www.ine.es/geoserver/ogc/features/v1/collections/{capa}/items"
    destino.mkdir(parents=True, exist_ok=True)

    def consulta(prov: str) -> str:
        return (f"f=json&filter-lang=cql-text&filter=CUSEC%20LIKE%20%27{prov}%25%27%20AND%20CSEC%3C%3E%27000%27"
                "&properties=CUSEC,CUMUN,CPRO,TIPO")

    def abrir(url: str, intentos: int = 5) -> bytes:
        for i in range(intentos):
            try:
                return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300).read()
            except Exception:
                time.sleep(3 * (i + 1))
        raise RuntimeError(f"no se pudo descargar {url}")

    provincias = [f"{i:02d}" for i in range(1, 53)]
    totales = {p: json.loads(abrir(f"{base}?{consulta(p)}&limit=1"))["numberMatched"] for p in provincias}

    def pedir(tarea):
        prov, inicio = tarea
        f = destino / f"p{prov}_{inicio:05d}.json"
        if f.exists() and f.stat().st_size > 100:
            return
        datos = abrir(f"{base}?{consulta(prov)}&limit={pagina}&startIndex={inicio}")
        json.loads(datos)
        f.write_bytes(datos)

    tareas = [(p, i) for p in provincias for i in range(0, totales[p], pagina)]
    with ThreadPoolExecutor(hilos) as ex:
        list(ex.map(pedir, tareas))
    return sum(totales.values())


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


TOLERANCIA_SECCIONES = 0.0004  # grados (~40 m): las secciones urbanas miden unos cientos de metros


def construir_secciones(carpeta: Path, anio: int, salida: Path = C.REPO / "web" / "data" / "sec" / "g",
                        tolerancia: float = TOLERANCIA_SECCIONES) -> dict:
    """GeoJSON de secciones por provincia: web/data/sec/g/AAAA/NN.geojson, propiedad `s` = CUSEC (10 dígitos).

    Cada provincia se simplifica como una cobertura (las fronteras compartidas se mantienen juntas)."""
    por_prov: dict[str, list] = {}
    vistos: set[str] = set()
    for f in sorted(glob.glob(str(carpeta / "p*.json"))):
        for ft in json.load(open(f, encoding="utf-8"))["features"]:
            cusec = ft["properties"]["CUSEC"]
            if cusec in vistos or cusec[-3:] == "000":
                continue
            vistos.add(cusec)
            por_prov.setdefault(cusec[:2], []).append((cusec, shape(ft["geometry"])))
    destino = salida / str(anio)
    destino.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    for prov, lista in sorted(por_prov.items()):
        ids = [c for c, _ in lista]
        geoms = [g for _, g in lista]
        try:
            simples = list(shapely.coverage_simplify(geoms, tolerancia))
        except Exception:
            simples = [g.simplify(tolerancia, preserve_topology=True) for g in geoms]
        feats = []
        for cusec, g in zip(ids, simples):
            g = shapely.set_precision(g, 0.0001) if not g.is_empty else g
            if not g.is_empty:
                feats.append({"type": "Feature", "properties": {"s": cusec}, "geometry": mapping(g)})
        f = destino / f"{prov}.geojson"
        f.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")), encoding="utf-8")
        total_bytes += f.stat().st_size
    return {"anio": anio, "secciones": len(vistos), "provincias": len(por_prov), "bytes": total_bytes}


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "AppData" / "Local" / "Temp" / "carto" / "distritos"
    print(construir(carpeta))
