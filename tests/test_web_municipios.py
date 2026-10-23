"""Datos municipales de la web (web/data/mun/*.json): consistencia con los totales oficiales provinciales."""
import json

import pytest

from pipeline import export_municipios, export_web
from pipeline.audit_interior import DEFAULT

ELECCIONES = ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]


@pytest.fixture(scope="module")
def web(tmp_path_factory):
    if not DEFAULT.exists():
        pytest.skip(f"No hay ficheros de Interior en {DEFAULT}")
    out = tmp_path_factory.mktemp("web")
    export_web.build(DEFAULT, out / "resultados.json")
    resumen = export_municipios.build(DEFAULT, out)
    prov = json.loads((out / "resultados.json").read_text(encoding="utf-8"))
    muni = {}
    for f in (out / "mun").glob("*.json"):
        muni.update(json.loads(f.read_text(encoding="utf-8")))
    return {"resumen": resumen, "prov": {e["id"]: e for e in prov["elecciones"]}, "muni": muni,
            "partidos": json.loads((out / "partidos.json").read_text(encoding="utf-8")),
            "indice": json.loads((out / "indice.json").read_text(encoding="utf-8"))}


def test_8136_municipios_en_52_provincias(web):
    assert web["resumen"] == {"municipios": 8136, "provincias": 52}
    assert len(web["indice"]) == 8136


def test_madrid_2023_oficial(web):
    h = web["muni"]["28079"]["h"]["2023"]
    assert (h[0], h[4]) == (2_367_140, 1_710_933)
    assert h[5][0] == ["000005", 720_547]                                  # PP
    assert web["partidos"]["2023"]["000005"] == ["PP", "PP"]


def test_nombres_con_articulo_invertido(web):
    n = {i: nombre for i, nombre in web["indice"]}
    assert n["15030"] == "A Coruña" and n["12005"] == "L'Alcora" and n["03014"] == "Alicante/Alacant"


def test_municipios_mas_cera_igual_al_total_provincial(web):
    # Interior: total provincial (07/08) = suma de municipios (05/06) + CERA. Cuadra EXACTO en 2011, 2016,
    # 2019a y 2019b. En el resto hay defectos de la propia fuente, todos pequeños (< 0,5 % de la provincia):
    # el descuadre de 1996 (1.013 votos), 2000 (461) y 2015 (47.548, partido en dos bloques), y casos sueltos
    # en 2004 (La Rioja, -5), 2008 (Soria, -124) y 2023 (Toledo, +175 en municipios).
    diferencias = {}
    for el in ELECCIONES:
        for cod, p in web["prov"][el]["provincias"].items():
            suma = sum(m["h"][el][4] for mid, m in web["muni"].items() if mid.startswith(cod) and el in m["h"])
            d = p["candidaturas"] - suma - p["cera"]["votos"]
            if d:
                diferencias[(el, cod)] = d
                assert abs(d) <= max(0.005 * p["candidaturas"], 250), (el, cod, d)   # Melilla 2015: 201 votos
    assert not {el for el, _ in diferencias} & {"2011", "2016", "2019a", "2019b"}
    assert {el for el, _ in diferencias} == {"1996", "2000", "2004", "2008", "2015", "2023"}
    assert diferencias[("2023", "45")] == -175


def test_las_candidaturas_guardadas_estan_en_partidos(web):
    for mid, m in web["muni"].items():
        for el, h in m["h"].items():
            for cod, v in h[5]:
                assert cod in web["partidos"][el], (mid, el, cod)
                assert v >= 0.015 * (h[4] + h[2]) - 1


def test_participacion_municipal_coherente(web):
    for m in web["muni"].values():
        for h in m["h"].values():
            assert h[1] == h[4] + h[2] + h[3]
            assert h[1] <= h[0] * 1.2 + 5      # pocas mesas con más votantes que censo (ver CLAUDE.md)
