"""web/data/resultados.json: cifras oficiales que la web muestra (generado por pipeline.export_web)."""
import json

import pytest

from pipeline import export_web
from pipeline.audit_interior import DEFAULT


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    if not DEFAULT.exists():
        pytest.skip(f"No hay ficheros de Interior en {DEFAULT}")
    p = export_web.build(DEFAULT, tmp_path_factory.mktemp("web") / "resultados.json")
    return {e["id"]: e for e in json.loads(p.read_text(encoding="utf-8"))["elecciones"]}


def test_diez_elecciones_y_52_provincias(datos):
    assert list(datos) == ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]
    assert all(len(e["provincias"]) == 52 for e in datos.values())


def test_350_escanos_en_nacional_y_en_provincias(datos):
    for e in datos.values():
        assert sum(p["e"] for p in e["nacional"]["partidos"]) == 350
        assert sum(sum(p["e"] for p in v["partidos"]) for v in e["provincias"].values()) == 350


def test_cifras_oficiales_2023(datos):
    n = datos["2023"]["nacional"]
    pp = n["partidos"][0]
    assert (pp["s"], pp["v"], pp["e"]) == ("PP", 8_160_837, 137)
    assert round(100 * pp["v"] / n["validos"], 2) == 33.06            # sobre votos válidos, no sobre candidaturas
    assert n["participacion_residentes"] == 70.41                       # residentes: sin el CERA
    assert n["cera"]["votos"] == 203_254


def test_participacion_residentes_otras_elecciones(datos):
    esperado = {"2019a": 75.75, "2019b": 69.86, "2016": 69.83}
    assert {k: datos[k]["nacional"]["participacion_residentes"] for k in esperado} == esperado


def test_madrid_2023(datos):
    m = datos["2023"]["provincias"]["28"]
    assert [(p["s"], p["e"]) for p in m["partidos"][:4]] == [("PP", 16), ("PSOE", 10), ("SUMAR", 6), ("VOX", 5)]
