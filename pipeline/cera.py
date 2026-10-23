"""CERA (voto exterior) de las 10 elecciones al Congreso, desde los ficheros oficiales de Interior.

mesas.parquet NO contiene el CERA. En los ficheros 09/10 viene como pseudo-mesas con
municipio 999, sección 0000 y mesa U, una por provincia (distrito 09). Las filas con provincia 99
son totales autonómicos/nacionales y se descartan aquí (se usan solo para validar).

Salidas en data/clean/:
  cera_provincia.parquet      una fila por (eleccion, prov_cod): censo CERA, blancos, nulos, votos a candidaturas
  cera_candidaturas.parquet   votos por (eleccion, prov_cod, candidatura), con las siglas y la candidatura
                              "cabecera" nacional (columna 227-232 del fichero 03) para agrupar coaliciones.
Las candidaturas NO se mapean aquí a las columnas de partido de mesas.parquet: ese mapeo está
pendiente (ver dim_partidos, familia = por_confirmar).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from . import config as C
from .audit_interior import DEFAULT, ELECCIONES


def _lines(path: Path):
    with open(path, encoding="latin-1", newline="") as f:
        for ln in f:
            ln = ln.rstrip("\r\n")
            if ln:
                yield ln


def read_cera_totales(path: Path, eleccion: str) -> list[tuple]:
    """Fichero 09: una fila por provincia (mun 999, prov != 99)."""
    out = []
    for ln in _lines(path):
        g = lambda a, b: ln[a - 1:b]
        if g(14, 16) == "999" and g(12, 13) != "99":
            out.append((eleccion, g(12, 13), g(17, 18), int(g(31, 37)), int(g(66, 72)), int(g(73, 79)),
                        int(g(80, 86)), g(101, 101)))
    return out


def read_cera_votos(path: Path, eleccion: str) -> list[tuple]:
    """Fichero 10: votos por candidatura de cada pseudo-mesa CERA provincial."""
    out = []
    for ln in _lines(path):
        g = lambda a, b: ln[a - 1:b]
        if g(14, 16) == "999" and g(12, 13) != "99":
            out.append((eleccion, g(12, 13), g(17, 18), g(24, 29), int(g(30, 36))))
    return out


def read_candidaturas(path: Path, eleccion: str) -> list[tuple]:
    """Fichero 03: código, siglas, denominación y candidatura cabecera nacional."""
    out = []
    for ln in _lines(path):
        g = lambda a, b: ln[a - 1:b]
        out.append((eleccion, g(9, 14), g(15, 64).strip(), g(65, 214).strip(), g(227, 232).strip()))
    return out


def build(base: Path = DEFAULT, out_dir: Path = C.CLEAN_DIR, con: duckdb.DuckDBPyConnection | None = None):
    con = con or duckdb.connect()
    out_dir.mkdir(parents=True, exist_ok=True)
    tot, vot, cand = [], [], []
    for per, el in ELECCIONES.items():
        d = base / f"02{per}_MESA"
        tot += read_cera_totales(d / f"0902{per[2:]}.DAT", el)
        vot += read_cera_votos(d / f"1002{per[2:]}.DAT", el)
        cand += read_candidaturas(d / f"0302{per[2:]}.DAT", el)
    t = pd.DataFrame(tot, columns=["eleccion", "prov_cod", "distrito", "censo_cera", "votos_blancos", "votos_nulos",
                                   "votos_candidaturas", "datos_oficiales"])
    v = pd.DataFrame(vot, columns=["eleccion", "prov_cod", "distrito", "cod_candidatura", "votos"])
    k = pd.DataFrame(cand, columns=["eleccion", "cod_candidatura", "siglas", "denominacion", "cod_nacional"])
    k["cod_nacional"] = k["cod_nacional"].where(k["cod_nacional"].str.strip("0") != "", k["cod_candidatura"])
    con.register("t", t)
    con.register("v", v)
    con.register("k", k)
    p1, p2 = out_dir / "cera_provincia.parquet", out_dir / "cera_candidaturas.parquet"
    con.execute(f"copy (select *, votos_candidaturas + votos_blancos + votos_nulos as votantes from t "
                f"order by eleccion, prov_cod) to '{p1}' (format parquet, compression zstd)")
    # LIMITACIÓN 2015: unas 600 candidaturas del CERA llevan códigos 9xxxxx que NO están en el
    # fichero 03 (ni como código local ni como cabecera nacional), así que quedan sin siglas
    # (siglas = NULL, ~88.000 votos, el 0,4 % de 2015). Resto de elecciones: todo etiquetado.
    con.execute(f"""copy (
        select v.eleccion, v.prov_cod, v.cod_candidatura, c.siglas, c.denominacion,
               c.cod_nacional, n.siglas as siglas_nacional, v.votos
        from v
        left join k c on c.eleccion = v.eleccion and c.cod_candidatura = v.cod_candidatura
        left join k n on n.eleccion = v.eleccion and n.cod_candidatura = c.cod_nacional
        order by 1, 2, 3) to '{p2}' (format parquet, compression zstd)""")
    return p1, p2


if __name__ == "__main__":
    for p in build():
        print(p)
