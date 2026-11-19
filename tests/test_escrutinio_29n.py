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
            "nulos": 15000, "pct_nulos": 0.88, "diputados": 38, "cod_ultima": "0001", "cod_proxima": "0007",
            "votos_faltan": 1234,
            "partidos": [{"c": "0007", "s": "PP", "v": 700000, "e": 16}, {"c": "0001", "s": "PSOE", "v": 500000, "e": 11},
                         {"c": "0072", "s": "FRENTE AMPLIO-FRONTE ZABALA", "v": 90000, "e": 2}]}
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
        ("0007", "PP", 700000, 16), ("0001", "PSOE", 500000, 11), ("0072", "FRENTE AMPLIO-FRONTE ZABALA", 90000, 2)]


def test_salida_para_la_web():
    web = E.a_web(E.leer_totales(E.escribir_totales([_registro(tipo="TO", prov="99", nombre="Total", diputados=350),
                                                     _registro()])))
    assert web["id"] == "2026" and web["hora"] == "21:14" and web["avisos"] == []
    m = web["provincias"]["28"]
    assert m["nombre"] == "Madrid" and m["escanos_total"] == 38 and m["escrutado"] == 50.0
    assert m["validos"] == 700000 + 500000 + 90000 + 12000
    assert m["participacion_residentes"] == 68.0
    assert [(p["s"], p["f"]) for p in m["partidos"]] == [("PP", "PP"), ("PSOE", "PSOE"), ("FRENTE AMPLIO-FRONTE ZABALA", "FA")]
    assert m["ultimo"] == {"ultima": "0001", "proxima": "0007", "faltan": 1234}


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


# --- Ficheros REALES del simulacro de Interior (18 de noviembre de 2026), en tests/datos/simulacro/ -------------

SIM = E.C.REPO / "tests" / "datos" / "simulacro"


def test_totales_reales_del_simulacro():
    r = E.leer_totales(E.texto((SIM / "totales.csv").read_bytes()))
    assert [x["tipo"] for x in r].count("PR") == 52 and [x["tipo"] for x in r].count("CM") == 19 and r[0]["tipo"] == "TO"
    web = E.a_web(r, simulacro=True, avances=E.leer_avances(E.texto((SIM / "avances.csv").read_bytes())))
    n = web["nacional"]
    assert web["hora"] == "21:26" and web["avisos"] == [] and web["simulacro"] is True
    assert n["escrutado"] == 98.54 and n["censo"] == 35_953_653 and n["escanos_total"] == 350
    esc = {}
    for p in n["partidos"]:
        esc[p["f"]] = esc.get(p["f"], 0) + p["e"]
    assert {k: v for k, v in esc.items() if v} == {"PP": 137, "PSOE": 126, "VOX": 34, "FA": 27, "ERC": 7, "JUNTS": 6,
                                                   "PNV": 5, "EH_BILDU": 5, "NC": 2, "BNG": 1}
    # Una fila por espacio: PP suma el escaño de UPN-PP, y EH Bildu los votos de la lista «EH BILDU-ERC» de Navarra.
    pp = next(p for p in n["partidos"] if p["f"] == "PP")
    assert (pp["s"], pp["e"], pp["v"], pp["incluye"]) == ("PP", 137, 8_102_993 + 65_135, ["UPN-PP"])
    bildu = next(p for p in n["partidos"] if p["f"] == "EH_BILDU")
    assert (bildu["e"], bildu["v"], bildu["incluye"]) == (5, 270_073 + 8_234, ["EH BILDU-ERC"])
    assert sum(1 for p in n["partidos"] if p["f"] == "COMPROMIS") == 1 and len([p for p in n["partidos"] if p["f"] == "OTROS"]) > 20
    assert n["avances"] == [40.4, 53.1] and n["mesas"] == {"total": 61033, "constituidas": 61033}
    m = web["provincias"]["28"]
    assert m["escanos_total"] == 38 and m["avances"] == [41.14, 53.93]
    assert m["ultimo"] == {"ultima": "0007", "proxima": "0006", "faltan": 40925}          # último PP; Vox a 40.925 votos
    assert all(sum(p["e"] for p in a["partidos"]) == a["escanos_total"] for a in web["provincias"].values())


def test_municipios_reales_del_simulacro():
    bilbao = [x for x in E.leer_municipios(E.texto((SIM / "municipios_48.csv").read_bytes())) if x["id"] == "48020"]
    assert [x["nombre"] for x in bilbao if x["distrito"] != "99"] == [
        "Deusto", "Uribarri", "Otxarkoaga/Txurdinaga", "Begoña", "Ibaiondo", "Abando", "Rekalde", "Basurto/Zorroza"]
    mun = next(x for x in bilbao if x["distrito"] == "99")
    assert mun["censo"] == sum(x["censo"] for x in bilbao if x["distrito"] != "99") == 268_669
    # Antes del escrutinio el fichero ya trae las candidaturas de la circunscripción, a cero.
    melilla = E.leer_municipios(E.texto((SIM / "municipios_52.csv").read_bytes()))
    assert len(melilla) == 1 and melilla[0]["censo_escrutado"] == 0
    assert [p["s"] for p in melilla[0]["partidos"]] == ["PSOE", "FO", "SALF", "VOX", "PP"]


def test_candidaturas_de_la_api_por_codigo():
    """El código manda sobre las siglas, y ambos caminos clasifican igual las 81 candidaturas del fichero oficial."""
    import csv
    from pipeline.convocatoria_29n import espacio
    with open(E.CONV / "candidaturas_api_2026.csv", encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 81
    assert all(E.espacio_api(r["codigo"], "") == espacio(r["denominacion"], r["siglas"]) for r in filas)
    assert E.espacio_api("0041", "") == "PSOE" and E.espacio_api("0152", "") == "PODEMOS" and E.espacio_api("0045", "") == "FA"
    assert E.espacio_api("9999", "VOX") == "VOX"                 # código desconocido: se cae a las siglas


def test_fichero_del_simulacro_para_la_web_al_dia():
    """web/data/simulacro_29n.json (se ve con ?simulacro) sale de los ficheros reales y va rotulado."""
    web = json.loads(E.SIMULACRO.read_text(encoding="utf-8"))
    assert web == json.loads(json.dumps(E.simulacro_web())) and web["simulacro"] is True


def test_resumen_para_pantallas():
    """Fichero mínimo para el proveedor de pantallas: mismas cifras que la web, pocas y con nombres legibles."""
    web = E.simulacro_web()
    d = E.pantallas(web, "130")
    assert (d["fase"], d["escrutado_pct"], d["participacion_pct"], d["mayoria_absoluta"], d["envio"]) == ("escrutinio", 98.54, 69.66, 176, "130")
    assert d["avances"] == [{"hora": "14:00", "participacion_pct": 40.4}, {"hora": "18:00", "participacion_pct": 53.1}]
    assert d["mesas"] == {"total": 61033, "constituidas": 61033, "suspendidas": 0}
    pp = d["partidos"][0]
    assert (pp["id"], pp["nombre"], pp["escanos"], pp["escanos_2023"], pp["porcentaje"]) == ("PP", "PP", 137, 138, 33.42)
    assert sum(p["escanos"] for p in d["partidos"]) == 350
    assert next(p for p in d["partidos"] if p["id"] == "FA")["escanos_2023"] is None       # sin comparación directa
    csv_ = E.pantallas_csv(d).splitlines()
    assert csv_[0] == "tipo;id;nombre;escanos;votos;porcentaje;escanos_2023" and "partido;PP;PP;137;8168128;33.42;138" in csv_
    antes = E.pantallas(E.vacio())
    assert antes["fase"] == "previa" and antes["partidos"] == [] and antes["participacion_pct"] is None
    assert json.loads(E.PANTALLAS_EJEMPLO.read_text(encoding="utf-8")) == json.loads(json.dumps(d))
    assert json.loads(E.PANTALLAS.read_text(encoding="utf-8")) == json.loads(json.dumps(antes))
