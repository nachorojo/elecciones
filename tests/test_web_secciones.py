"""Datos por sección de la web (web/data/sec/*.json): coherencia con los totales municipales oficiales."""
import json

import pytest

from pipeline import export_municipios, export_secciones
from pipeline.audit_interior import DEFAULT

PER = {"2019a": "201904", "2019b": "201911", "2023": "202307"}


@pytest.fixture(scope="module")
def sec(tmp_path_factory):
    if not DEFAULT.exists():
        pytest.skip(f"No hay ficheros de Interior en {DEFAULT}")
    out = tmp_path_factory.mktemp("sec")
    resumen = export_secciones.build(DEFAULT, out)
    datos = {}
    for f in (out / "sec").glob("*.json"):
        datos.update(json.loads(f.read_text(encoding="utf-8")))
    return {"resumen": resumen, "datos": datos,
            "partidos": json.loads((out / "partidos_sec.json").read_text(encoding="utf-8"))}


def test_numero_de_secciones(sec):
    assert {k: v["secciones"] for k, v in sec["resumen"].items()} == {"2019a": 36317, "2019b": 36302, "2023": 36460}
    assert len([s for s in sec["datos"] if "2023" in sec["datos"][s]]) == 36460


@pytest.mark.parametrize("el", ["2019a", "2019b", "2023"])
def test_secciones_suman_el_total_municipal_oficial(sec, el):
    # sección = agregación de mesas (ficheros 09/10); municipio = ficheros 05/06.
    # Votos a candidaturas y blancos: EXACTO en los tres. Censo: exacto en 2023; en 2019 la propia fuente
    # difiere en 490 (abril) y 285 (noviembre) municipios, casi siempre por 1-9 electores, con casos
    # extremos en municipios diminutos (Torres de Alcanadre 22235: 176 frente a 88 en abril).
    muni, _ = export_municipios.leer_eleccion(DEFAULT, PER[el])
    suma = {}
    for s, h in sec["datos"].items():
        if el in h:
            a = suma.setdefault(s[:5], [0, 0, 0])
            a[0] += h[el][0]; a[1] += h[el][4]; a[2] += h[el][2]
    assert set(suma) == set(muni)
    assert [m for m, v in suma.items() if v[1:] != [muni[m]["cand"], muni[m]["blancos"]]] == []
    dif = {m: abs(v[0] - muni[m]["censo"]) / muni[m]["censo"] for m, v in suma.items() if v[0] != muni[m]["censo"]}
    if el == "2023":
        assert dif == {}
    else:
        assert len(dif) < 0.07 * len(suma)
        assert max((r for m, r in dif.items() if m != "22235"), default=0) < 0.12


def test_top3_ordenado_y_coherente(sec):
    for s, h in sec["datos"].items():
        for el, f in h.items():
            votos = [v for _, v in f[5]]
            assert votos == sorted(votos, reverse=True) and len(votos) <= 3
            assert sum(votos) <= f[4]
            assert f[1] == f[4] + f[2] + f[3]


def test_comparabilidad_y_cambio(sec):
    r = sec["resumen"]
    assert r["2019a"]["comparables"] == 0                       # no hay elección anterior
    assert r["2019b"]["comparables"] > 0.98 * r["2019b"]["secciones"]
    assert 0.9 < r["2023"]["comparables"] / r["2023"]["secciones"] < 1.0    # algunos municipios cambiaron de distritos
    for h in sec["datos"].values():
        for f in h.values():
            assert (f[6] is None) == (f[7] is None)
            assert f[7] in (None, 0, 1)


def test_el_ganador_anterior_esta_en_los_partidos(sec):
    for h in sec["datos"].values():
        for el, f in h.items():
            if f[6]:
                ant = {"2019b": "2019a", "2023": "2019b"}[el]
                assert f[6] in sec["partidos"][ant]
            for cod, _ in f[5]:
                assert cod in sec["partidos"][el]
