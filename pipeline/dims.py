"""Tablas de dimensión: territorios canónicos y partidos.

dim_municipios / dim_provincias / dim_ccaa
    Un nombre por código. PROVISIONAL: se elige entre las variantes del bruto (la de la
    elección más reciente que no esté toda en mayúsculas). Hay que sustituirlo por el
    nomenclátor del INE; `nombre_fuente` lo deja marcado.

dim_partidos
    Una fila por (elección, columna de partido) con los votos totales. `columna_vacia` sale
    de los datos (suma 0), no de una suposición. `familia` solo se rellena para lo que
    fija el CLAUDE.md; el resto queda en 'por_confirmar' a la espera de la redacción.
"""
from __future__ import annotations

import duckdb

from . import config as C

# (columna de votos, nombre visible, familia fijada en CLAUDE.md o None)
PARTIDOS_META = {
    "pp": ("PP", "centro_derecha"),
    "psoe": ("PSOE", "centro_izquierda"),
    "vox": ("Vox", "derecha"),
    "podemos_sumar": ("Podemos/Sumar", "izquierda"),
    "cs": ("Cs", None),
    "iu": ("IU", None),
    "upyd": ("UPyD", None),
    "erc": ("ERC", None),
    "ciu_jxcat": ("CiU/Junts", None),
    "pnv": ("PNV", None),
    "eh_bildu": ("EH Bildu", None),
    "bng": ("BNG", None),
    "cc": ("CC", None),
    "compromis": ("Compromís", None),
}

# Problemas conocidos de columnas por elección (CLAUDE.md, problema 9).
NOTAS = {
    ("2016", "iu"): "IU va dentro de podemos_sumar en 2016",
    ("2015", "compromis"): "Compromís va dentro de podemos_sumar (columna a 0)",
    ("2016", "compromis"): "Compromís va dentro de podemos_sumar (columna a 0)",
    ("2019b", "compromis"): "Compromís va dentro de otra columna (columna a 0)",
    ("2023", "cs"): "Cs no se presentó de forma general (columna a 0)",
}

_CANON = """
select {key} as {key},
       arg_max({nombre}, rank) as nombre,
       count(distinct {nombre}) as n_variantes_nombre,
       'provisional_bruto' as nombre_fuente
{extra}
from (
  select {key}, {nombre}, {cols_extra}
         (conv_idx * 2 + case when {nombre} = upper({nombre}) then 0 else 1 end) as rank
  from read_parquet('{mesas}')
)
group by {key}
order by {key}
"""


def _canon(con, mesas, key: str, nombre: str, extra_cols: list[str]) -> str:
    extra = "".join(f", arg_max({c}, rank) as {c}" for c in extra_cols)
    cols_extra = "".join(f"{c}, " for c in extra_cols)
    return _CANON.format(key=key, nombre=nombre, extra=extra, cols_extra=cols_extra, mesas=mesas)


def build(mesas, out_dir=C.CLEAN_DIR, con: duckdb.DuckDBPyConnection | None = None):
    con = con or duckdb.connect()
    out = {}
    specs = {
        "dim_municipios": ("municipio_id", "municipio_nombre_original", ["prov_cod", "ccaa_cod"]),
        "dim_provincias": ("prov_cod", "provincia", ["ccaa_cod"]),
        "dim_ccaa": ("ccaa_cod", "ccaa", []),
    }
    for name, (key, nombre, extra) in specs.items():
        path = out_dir / f"{name}.parquet"
        con.execute(f"copy ({_canon(con, mesas, key, nombre, extra)}) to '{path}' (format parquet, compression zstd)")
        out[name] = path

    # dim_partidos
    sums = " union all ".join(
        f"select eleccion, '{p}' as columna, sum(votos_{p}) as votos_total from read_parquet('{mesas}') group by eleccion"
        for p in C.PARTIDOS
    )
    rows = con.execute(f"select * from ({sums}) order by eleccion, columna").fetchall()
    order = {e: i for i, e in enumerate(C.ELECCIONES)}
    rows.sort(key=lambda r: (order[r[0]], C.PARTIDOS.index(r[1])))
    values = ", ".join(
        "('{e}','{c}','{n}',{f},{v},{vac},{nota})".format(
            e=e, c=c, n=PARTIDOS_META[c][0],
            f="'%s'" % PARTIDOS_META[c][1] if PARTIDOS_META[c][1] else "'por_confirmar'",
            v=int(v or 0), vac=str(not v).lower(),
            nota="'%s'" % NOTAS[(e, c)] if (e, c) in NOTAS else "null",
        )
        for e, c, v in rows
    )
    path = out_dir / "dim_partidos.parquet"
    con.execute(
        "copy (select * from (values %s) t(eleccion, columna, partido, familia, votos_total, columna_vacia, nota)) "
        "to '%s' (format parquet, compression zstd)" % (values, path)
    )
    out["dim_partidos"] = path
    return out
