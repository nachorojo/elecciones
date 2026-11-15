"""Lector de la API de descargas de Interior para el 29N (pipeline/escrutinio_29n.py).

No hay ficheros reales hasta el simulacro (18 de noviembre): se prueba con registros construidos
según el diseño del manual (apartado 3.2) y con el fichero de demostración.
"""
import json

from pipeline import escrutinio_29n as E


def _registro(**kw):
    base = {"fecha": "2611292114", "tipo": "PR", "ccaa": "13", "prov": "28", "fijo": "9", "nombre": "Madrid",
            "mesas": 7000, "censo": 5000000, "censo_escrutado": 2500000, "pct_escrutado": 50.0, "votantes": 1700000,
            "pct_votantes": 68.0, "abstencion": 800000, "pct_abstencion": 32.0, "blancos": 12000, "pct_blancos": 0.71,
            "nulos": 15000, "pct_nulos": 0.88, "diputados": 38, "cod_ultima": "0002", "cod_proxima": "0001",
            "votos_faltan": 1234,
            "partidos": [{"c": "0001", "s": "PP", "v": 700000, "e": 16}, {"c": "0002", "s": "PSOE", "v": 500000, "e": 11},
                         {"c": "0007", "s": "FRENTE AMPLIO-FRONTE ZABALA", "v": 90000, "e": 2}]}
    return base | kw


def test_formato_del_manual():
    """422 campos separados por «;»: 22 fijos + 80 candidaturas × 5; longitudes fijas; fin de registro CR LF."""
    txt = E.escribir_totales([_registro()])
    assert txt.endswith("\r\n")
    campos = txt.strip("\r\n").split(";")
    assert len(campos) == 22 + 80 * 5
    assert [len(c) for c in campos[:22]] == [n for _, n in E.CAMPOS]
    assert [len(c) for c in campos[22:27]] == [4, 55, 8, 5, 3]
    assert campos[9] == "05000"            # porcentaje: las dos últimas posiciones son decimales


def test_ida_y_vuelta():
    r = E.leer_totales(E.escribir_totales([_registro()]))[0]
    assert (r["tipo"], r["prov"], r["nombre"], r["diputados"]) == ("PR", "28", "Madrid", 38)
    assert r["pct_escrutado"] == 50.0 and r["pct_blancos"] == 0.71 and r["votos_faltan"] == 1234
    assert [(p["c"], p["s"], p["v"], p["e"]) for p in r["partidos"]] == [
        ("0001", "PP", 700000, 16), ("0002", "PSOE", 500000, 11), ("0007", "FRENTE AMPLIO-FRONTE ZABALA", 90000, 2)]


def test_salida_para_la_web():
    web = E.a_web(E.leer_totales(E.escribir_totales([_registro(tipo="TO", prov="99", nombre="Total", diputados=350),
                                                     _registro()])))
    assert web["id"] == "2026" and web["hora"] == "21:14" and web["avisos"] == []
    m = web["provincias"]["28"]
    assert m["nombre"] == "Madrid" and m["escanos_total"] == 38 and m["escrutado"] == 50.0
    assert m["validos"] == 700000 + 500000 + 90000 + 12000
    assert m["participacion_residentes"] == 68.0
    assert [(p["s"], p["f"]) for p in m["partidos"]] == [("PP", "PP"), ("PSOE", "PSOE"), ("FRENTE AMPLIO-FRONTE ZABALA", "FA")]
    assert m["ultimo"] == {"ultima": "0002", "proxima": "0001", "faltan": 1234}


def test_avisa_si_los_escanos_no_coinciden_con_el_boe():
    web = E.a_web(E.leer_totales(E.escribir_totales([_registro(tipo="TO", prov="99", diputados=350),
                                                     _registro(diputados=37)])))
    assert web["avisos"] == ["28: 37 diputados en el fichero, 38 en el BOE"]


def test_fichero_vacio_y_demo():
    v = E.vacio()
    assert len(v["provincias"]) == 52 and sum(p["escanos_total"] for p in v["provincias"].values()) == 350
    assert v["nacional"]["escrutado"] == 0 and v["nacional"]["partidos"] == [] and v["prueba"] is False
    d = E.a_web(E.leer_totales(E.demo()), prueba=True)
    assert d["prueba"] is True and d["avisos"] == [] and len(d["provincias"]) == 52
    assert sum(p["e"] for p in d["nacional"]["partidos"]) == 350
    assert all(sum(p["e"] for p in a["partidos"]) == a["escanos_total"] for a in d["provincias"].values())


def test_ficheros_de_la_web_al_dia():
    assert json.loads(E.VIVO.read_text(encoding="utf-8")) == json.loads(json.dumps(E.vacio()))
    assert json.loads(E.DEMO.read_text(encoding="utf-8"))["prueba"] is True
