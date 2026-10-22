"""Fixtures: construyen el Parquet limpio en un directorio temporal a partir del bruto.

Si el bruto no está (p. ej. en la nube, donde no se sube), todos los tests se saltan.
"""
import duckdb
import pytest

from pipeline import clean, config as C, dims


@pytest.fixture(scope="session")
def con(tmp_path_factory):
    if not C.RAW.exists():
        pytest.skip(f"No hay Parquet bruto en {C.RAW}")
    out = tmp_path_factory.mktemp("clean")
    c = duckdb.connect()
    mesas = clean.build(C.RAW, out, c)
    dims.build(mesas, out, c)
    c.execute(f"create view raw as select * from read_parquet('{C.RAW}')")
    for name in ("mesas", "dim_municipios", "dim_provincias", "dim_ccaa", "dim_partidos"):
        c.execute(f"create view {name} as select * from read_parquet('{out / (name + '.parquet')}')")
    return c


@pytest.fixture(scope="session")
def q(con):
    def run(sql):
        return con.execute(sql).fetchall()

    def one(sql):
        return con.execute(sql).fetchone()[0]

    run.one = one
    return run
