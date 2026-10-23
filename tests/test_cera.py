"""CERA (voto exterior): tablas construidas desde los ficheros oficiales de Interior."""
import duckdb
import pytest

from pipeline import cera

ELECCIONES = ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]


@pytest.fixture(scope="module")
def cq(tmp_path_factory):
    if not cera.DEFAULT.exists():
        pytest.skip(f"No hay ficheros de Interior en {cera.DEFAULT}")
    out = tmp_path_factory.mktemp("cera")
    con = duckdb.connect()
    p1, p2 = cera.build(cera.DEFAULT, out, con)
    con.execute(f"create view prov as select * from read_parquet('{p1}')")
    con.execute(f"create view cand as select * from read_parquet('{p2}')")
    return lambda sql: con.execute(sql).fetchall()


def test_52_provincias_por_eleccion(cq):
    assert cq("select eleccion, count(*), count(distinct prov_cod) from prov group by 1 order by 1") == \
        [(e, 52, 52) for e in ELECCIONES]


def test_totales_2023_coinciden_con_el_fichero_09(cq):
    # cifras verificadas contra el fichero oficial (suma de las 52 provincias)
    assert cq("select sum(censo_cera), sum(votos_candidaturas) from prov where eleccion = '2023'") == [(2_328_260, 203_254)]


def test_votos_se_hunden_en_2011(cq):
    v = dict(cq("select eleccion, sum(votos_candidaturas) from prov group by 1"))
    assert v["2011"] < 0.25 * v["2008"]            # el censo CERA crece, el voto cae
    c = dict(cq("select eleccion, sum(censo_cera) from prov group by 1"))
    assert c["2011"] > c["2008"]


def test_votos_por_candidatura_suman_el_total_provincial(cq):
    # exacto salvo 2015, donde el propio Interior difiere en 1 voto (ver CLAUDE.md, problema 8)
    d = cq("""select p.eleccion, p.v - c.v from
              (select eleccion, sum(votos_candidaturas) v from prov group by 1) p
              join (select eleccion, sum(votos) v from cand group by 1) c using (eleccion) order by 1""")
    for e, diff in d:
        assert diff == (1 if e == "2015" else 0), e


def test_candidaturas_etiquetadas_salvo_2015(cq):
    sin = dict(cq("select eleccion, count(*) from cand where siglas is null group by 1"))
    assert set(sin) == {"2015"}                    # limitación documentada: códigos 9xxxxx sin fichero 03
    # En 2015 casi TODO el voto CERA queda sin etiquetar. Si este assert falla es que se resolvió: actualizar.
    sin_2015, total_2015 = cq("select sum(votos) filter (where siglas is null), sum(votos) from cand "
                              "where eleccion = '2015'")[0]
    assert sin_2015 / total_2015 > 0.99


def test_partidos_principales_2023(cq):
    top = [r[0] for r in cq("select siglas_nacional from cand where eleccion = '2023' "
                            "group by 1 order by sum(votos) desc limit 4")]
    assert top == ["PP", "PSOE", "SUMAR", "VOX"]
