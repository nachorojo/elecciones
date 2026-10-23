"""Motor de escaños d'Hondt: casos de manual y backtest contra los escaños oficiales de las 10 elecciones."""
from fractions import Fraction

import pytest

from pipeline import escanos as E
from pipeline.audit_interior import DEFAULT, ELECCIONES


# --- Casos de manual (no necesitan datos) ------------------------------------
def test_dhondt_ejemplo_clasico():
    # 7 escaños: A 340.000, B 280.000, C 160.000, D 60.000, E 15.000 -> 3, 3, 1, 0, 0
    r = E.repartir({"A": 340_000, "B": 280_000, "C": 160_000, "D": 60_000, "E": 15_000}, 7)
    assert r.escanos == {"A": 3, "B": 3, "C": 1, "D": 0, "E": 0}
    assert not r.empate


def test_barrera_del_3_por_ciento_es_inclusiva_y_cuenta_los_blancos():
    # 37 escaños: el cociente de corte ronda 270, así que C (290-300 votos) ganaría un escaño sin barrera.
    def c(votos_c, a, b, blancos=0, **kw):
        return E.repartir({"A": a, "B": b, "C": votos_c}, 37, blancos, **kw).escanos["C"]

    assert c(290, 6_000, 3_710, umbral=0) == 1       # sin barrera, C tendría escaño...
    assert c(290, 6_000, 3_710) == 0                 # ...pero está en el 2,9 %: queda fuera
    assert c(300, 6_000, 3_700) == 1                 # exactamente el 3,0 %: entra (barrera inclusiva)
    assert c(300, 6_000, 3_700, blancos=100) == 0    # los blancos suben el total de válidos: 2,97 %, fuera


def test_empate_en_el_ultimo_escaño_se_avisa():
    r = E.repartir({"A": 100, "B": 100}, 1)
    assert r.empate and sum(r.escanos.values()) == 1


def test_un_escaño_gana_el_mas_votado():
    assert E.repartir({"A": 10, "B": 60, "C": 30}, 1).escanos == {"A": 0, "B": 1, "C": 0}


# --- Backtest contra Interior ------------------------------------------------
@pytest.fixture(scope="module")
def prov():
    if not DEFAULT.exists():
        pytest.skip(f"No hay ficheros de Interior en {DEFAULT}")
    return {el: E.leer_provincias(DEFAULT, per) for per, el in ELECCIONES.items()}


def test_350_escanos_en_cada_eleccion(prov):
    for el, P in prov.items():
        assert len(P) == 52, el
        assert sum(p["escanos"] for p in P.values()) == 350, el
        assert sum(sum(p["oficial"].values()) for p in P.values()) == 350, el


def test_dhondt_reproduce_los_520_repartos_oficiales(prov):
    malas = E.backtest()
    assert len(malas) == 520
    assert [f for f in malas if f["dif"]] == []
    assert not any(f["empate"] for f in malas)       # ningún sorteo en 10 elecciones


def test_votos_provinciales_cuadran_con_el_fichero_07(prov):
    # La suma por candidatura (08, con CERA incluido) debe igualar el total provincial (07).
    # Excepciones heredadas de la fuente: 2 provincias en 2000 y 1 en 2008.
    mal = {el: sum(sum(p["votos"].values()) != p["candidaturas"] for p in P.values()) for el, P in prov.items()}
    assert {el: n for el, n in mal.items() if n} == {"2000": 2, "2008": 1}


def test_el_backtest_discrimina_un_metodo_incorrecto(prov):
    # Con Sainte-Laguë (otro método) el resultado difiere del oficial en muchas circunscripciones.
    def sainte(votos, n):
        q = sorted(((Fraction(v, 2 * k + 1), c) for c, v in votos.items() for k in range(n)), reverse=True)[:n]
        out = {c: 0 for c in votos}
        for _, c in q:
            out[c] += 1
        return out

    dist = 0
    for P in prov.values():
        for p in P.values():
            elegibles = {c: v for c, v in p["votos"].items() if v >= 0.03 * (sum(p["votos"].values()) + p["blancos"])}
            s = sainte(elegibles, p["escanos"])
            dist += any(s.get(c, 0) != p["oficial"].get(c, 0) for c in p["votos"])
    assert dist > 100


def test_la_barrera_es_el_3_y_no_otro_valor(prov):
    # Barcelona 2019a: sin barrera cambiaría el reparto. Con el 5 % cambian Barcelona 1996/2000 y Madrid 2008:
    # hay listas entre el 3 % y el 5 % con escaño, así que el umbral correcto es el 3 %.
    def cambia(el, cod, **kw):
        p = prov[el][cod]
        r = E.repartir(p["votos"], p["escanos"], p["blancos"], **kw).escanos
        return any(r.get(c, 0) != p["oficial"].get(c, 0) for c in p["votos"])

    assert cambia("2019a", "08", umbral=0)
    for el, cod in (("1996", "08"), ("2000", "08"), ("2008", "28")):
        assert cambia(el, cod, umbral=0.05)
        assert not cambia(el, cod)
