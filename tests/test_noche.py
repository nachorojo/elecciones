"""Proyección de la noche electoral (pipeline/noche.py) y su backtest con recuentos simulados.

Usa ficheros de la repo (web/data/mun, web/data/sec y, si está, tfm/db_tfm/db_municipios.parquet).
"""
import numpy as np
import pytest

from pipeline import noche as N


def test_dhondt_y_barrera():
    assert list(N.dhondt(np.array([340_000, 280_000, 160_000, 60_000, 15_000]), 7, 855_000)) == [3, 3, 1, 0, 0]
    # Con 2,9 % de los válidos no entra en el reparto aunque le correspondiera un cociente.
    assert list(N.dhondt(np.array([50.0, 47.1, 2.9]), 30, 100.0))[2] == 0


def _caso():
    rng = np.random.default_rng(0)
    base = rng.integers(200, 5000, size=(40, 4)).astype(float)
    censo = base.sum(axis=1) * 1.4
    prov = np.repeat(np.arange(4), 10)
    tramo = np.searchsorted(N.TRAMOS, censo, side="right")
    return base, censo, prov, tramo


def test_con_todo_contado_devuelve_lo_contado():
    base, censo, prov, tramo = _caso()
    final = base * 1.1
    assert N.proyectar(base, censo, censo, final, prov, tramo) == pytest.approx(final)


def test_recupera_un_cambio_distinto_en_cada_provincia():
    """Si cada provincia cambia a su manera y solo se ha contado una parte de cada municipio, la proyección
    reconstruye el final; repartir lo contado tal cual no puede (lo contado no pesa igual en cada provincia)."""
    base, censo, prov, tramo = _caso()
    cambio = np.array([[1.3, 0.8, 1.0, 1.0], [0.7, 1.2, 1.0, 1.1], [1.0, 1.0, 1.5, 0.6], [1.1, 0.9, 0.8, 1.2]])[prov]
    final = base * cambio
    f = np.where(np.arange(40) % 10 < 3, 0.5, 0.0)          # tres municipios de cada provincia, a medias
    y = N.proyectar(base, censo, censo * f, final * f[:, None], prov, tramo, fuerza=1e-6)
    assert y == pytest.approx(final, rel=1e-3)


def test_partido_nuevo_se_proyecta_por_porcentaje():
    base, censo, prov, tramo = _caso()
    base = np.hstack([base, np.zeros((40, 1))])               # quinto espacio: sin base
    final = np.hstack([base[:, :4] * 0.9, base[:, :4].sum(axis=1, keepdims=True) * 0.1])
    f = np.where(np.arange(40) % 2 == 0, 1.0, 0.0)
    y = N.proyectar(base, censo, censo * f, final * f[:, None], prov, tramo, fuerza=1e-6)
    assert y[:, 4].sum() == pytest.approx(final[:, 4].sum(), rel=1e-3)


@pytest.fixture(scope="module")
def d2023():
    return N.cargar("2023")


def test_datos_de_2023(d2023):
    d = d2023
    assert len(d["municipios"]) == 8131 and len(d["provincias"]) == 52 and d["n_escanos"].sum() == 350
    por_mun = np.zeros_like(d["final"])
    np.add.at(por_mun, d["sec_mun"], d["sec_votos"])
    assert por_mun == pytest.approx(d["final"])                # las secciones suman el total de su municipio
    real = N.escanos(N._por_provincia(d, d["final"]), d["n_escanos"])
    tot = {d["espacios"][k]: int(v) for k, v in enumerate(real.sum(axis=0)) if v}
    # Sin voto exterior (CERA), como la noche electoral: el PP tiene 136 y el PSOE 122. El escaño de Madrid
    # pasó del PSOE al PP con el recuento del CERA, días después (oficial: 137-121).
    assert tot["PP"] == 136 and tot["PSOE"] == 122 and tot["VOX"] == 33 and sum(tot.values()) == 350


def test_la_proyeccion_mejora_al_recuento_cuando_llegan_antes_los_pueblos(d2023):
    d = d2023
    real = N.escanos(N._por_provincia(d, d["final"]), d["n_escanos"])
    mal = lambda e: int(np.abs(e.sum(axis=0) - real.sum(axis=0)).sum() // 2)
    rng = np.random.default_rng(29)
    rec, proy = [], []
    for _ in range(4):
        orden = N.orden_de_llegada(d, "municipios pequeños primero", rng)
        cc, v = N.estado(d, orden, 10)
        assert cc.sum() / d["censo"].sum() == pytest.approx(0.10, abs=0.002)
        rec.append(mal(N.escanos(N._por_provincia(d, v), d["n_escanos"])))
        y = N.proyectar(d["base"], d["censo"], cc, v, d["prov"], d["tramo"])
        proy.append(mal(N.escanos(N._por_provincia(d, y), d["n_escanos"])))
    assert np.mean(rec) > 8 and np.mean(proy) < 6 and np.mean(proy) < np.mean(rec) / 2
