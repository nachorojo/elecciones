"""Convocatoria del 29N: escaños por circunscripción y candidaturas proclamadas (BOE).

Los CSV de data/web/29n/ están en la repo; se regeneran con `python -m pipeline.convocatoria_29n`.
El test de lectura del BOE se salta si no hay copia local de los XML (../datos/boe/).
"""
import csv

import pytest

from pipeline import config as C, convocatoria_29n as M

CONV = C.REPO / "data" / "web" / "29n"


def _csv(nombre):
    with open(CONV / nombre, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_350_escanos_en_52_circunscripciones():
    filas = _csv("escanos.csv")
    assert len(filas) == 52
    assert sum(int(r["escanos_29n"]) for r in filas) == 350
    assert sum(int(r["escanos_2023"]) for r in filas) == 350


def test_cambios_de_escanos_respecto_a_2023():
    """Solo cambian dos circunscripciones: Madrid gana un escaño y Cádiz lo pierde."""
    cambios = {r["provincia"]: (int(r["escanos_2023"]), int(r["escanos_29n"]))
               for r in _csv("escanos.csv") if r["escanos_29n"] != r["escanos_2023"]}
    assert cambios == {"11": (9, 8), "28": (37, 38)}


def test_minimos_legales():
    esc = {r["provincia"]: int(r["escanos_29n"]) for r in _csv("escanos.csv")}
    assert esc["51"] == esc["52"] == 1                      # Ceuta y Melilla
    assert min(v for k, v in esc.items() if k not in ("51", "52")) == 2   # mínimo provincial (Soria)


def test_534_candidaturas_proclamadas_al_congreso():
    c = _csv("candidaturas_congreso.csv")
    assert len(c) == 534
    assert len({r["provincia"] for r in c}) == 52
    por_prov = {}
    for r in c:
        por_prov.setdefault(r["provincia"], []).append(int(r["orden"]))
    # La numeración del BOE es creciente dentro de cada circunscripción; los huecos son listas
    # presentadas que figuran como «No proclamada» (p. ej. la n.º 9 de Málaga) y no se exportan.
    assert all(o == sorted(set(o)) for o in por_prov.values())
    assert 9 not in por_prov["29"] and max(por_prov["29"]) == 12


def test_espacios_una_lista_por_provincia():
    """Ningún espacio (salvo OTROS) tiene dos listas en la misma circunscripción."""
    vistos = set()
    for r in _csv("candidaturas_congreso.csv"):
        if r["espacio"] != "OTROS":
            assert (r["provincia"], r["espacio"]) not in vistos, r
            vistos.add((r["provincia"], r["espacio"]))


def test_presencia_territorial_de_los_espacios():
    c = _csv("candidaturas_congreso.csv")
    prov = lambda esp: sorted(r["provincia"] for r in c if r["espacio"] == esp)
    assert len(prov("PP")) == len(prov("PSOE")) == len(prov("VOX")) == 52
    assert len(prov("SALF")) == 46 and len(prov("FA")) == 44 and len(prov("PODEMOS")) == 41
    assert prov("COMPROMIS") == ["03", "12", "46"] and prov("NC") == ["35", "38"]
    assert prov("ERC") == prov("JUNTS") == ["08", "17", "25", "43"]
    assert prov("EH_BILDU") == ["01", "20", "31", "48"] and prov("PNV") == ["01", "20", "48"]
    # Corrección de errores del BOE de 7 de noviembre: en Navarra la lista es EH BILDU, no EH BILDU-ERC.
    assert [r["siglas"] for r in c if r["provincia"] == "31" and r["espacio"] == "EH_BILDU"] == ["EH BILDU"]
    # UPN concurre en coalición con el PP: no hay lista de UPN aparte.
    assert [r["siglas"] for r in c if r["provincia"] == "31" and r["espacio"] == "PP"] == ["UPN-PP"]


def test_lectura_del_boe_reproduce_los_csv():
    docs = {k: M.CACHE / f"{v}.xml" for k, v in M.DOCS.items()}
    if not all(p.exists() for p in docs.values()):
        pytest.skip(f"No hay copia local del BOE en {M.CACHE}")
    esc = M.leer_escanos(docs["decreto"])
    assert esc == {r["provincia"]: int(r["escanos_29n"]) for r in _csv("escanos.csv")}
    cands = M.aplicar_correcciones(M.leer_candidaturas(docs["proclamadas"]))
    assert [(f["provincia"], f["siglas"]) for f in cands] == [(r["provincia"], r["siglas"]) for r in _csv("candidaturas_congreso.csv")]
