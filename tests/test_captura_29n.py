"""Recuento por municipio, base del 29N, proyección y captura de un envío, de extremo a extremo y sin red.

Se fabrica una «noche» ficticia (la base de 2023 con cambios distintos por provincia, más Podemos, Frente
Amplio y Se Acabó la Fiesta), se escribe en el formato de la API de Interior, y se comprueba que la captura
la lee, actualiza el fichero de la web y proyecta un reparto cercano al final.
"""
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from pipeline import captura_29n as K, escrutinio_29n as E, noche as N, proyeccion_29n as P

SIGLAS = {"PP": "PP", "PSOE": "PSOE", "VOX": "VOX", "FA": "FA", "PODEMOS": "PODEMOS", "SALF": "SALF", "ERC": "ERC",
          "JUNTS": "JxCat", "EH_BILDU": "EH BILDU", "PNV": "EAJ-PNV", "BNG": "BNG", "CC": "CCa-1.ºCAN",
          "COMPROMIS": "COMPROMIS-EUPV-PODEM-ERPV", "NC": "NC-BC, PODEMOS, IU, SUMAR", "ADELANTE": "ADELANTE ANDALUCÍA",
          "TERUEL_EXISTE": "TERUEL EXISTE", "GBAI": "GBAI"}


@pytest.fixture(scope="module")
def base():
    return P.base_municipal()


def test_formato_municipal_del_manual():
    """341 campos: 21 fijos + 80 candidaturas × 4 (código, siglas, votos, porcentaje)."""
    r = {"fecha": "2611292114", "ccaa": "13", "prov": "28", "mun": "079", "distrito": "99", "nombre": "Madrid",
         "mesas": 3000, "censo": 2_400_000, "censo_escrutado": 1_200_000, "pct_escrutado": 50.0, "votantes": 800_000,
         "pct_votantes": 66.67, "abstencion": 400_000, "pct_abstencion": 33.33, "blancos": 5000, "pct_blancos": 0.6,
         "nulos": 6000, "pct_nulos": 0.75, "partidos": [{"c": "0001", "s": "PP", "v": 300_000}]}
    campos = E.escribir_municipios([r]).strip("\r\n").split(";")
    assert len(campos) == 21 + 80 * 4
    assert [len(c) for c in campos[:21]] == [n for _, n in E.CAMPOS_MUN]
    x = E.leer_municipios(E.escribir_municipios([r, dict(r, distrito="05", nombre="Chamartín")]))
    assert (x[0]["id"], x[0]["distrito"], x[0]["censo_escrutado"], x[0]["pct_votantes"]) == ("28079", "99", 1_200_000, 66.67)
    assert x[0]["partidos"] == [{"c": "0001", "s": "PP", "v": 300_000}] and x[1]["distrito"] == "05"


def test_base_del_29n(base):
    b = base
    assert len(b["municipios"]) == 8131 and b["n_escanos"].sum() == 350
    assert b["sin_2023"] == ["48916"]                        # Usansolo: municipio nuevo, perfil de Bizkaia
    assert b["base"][b["municipios"].index("48916")].sum() > 0
    assert 35_900_000 < b["censo"].sum() < 36_000_000        # electores residentes del censo de consulta
    tot = dict(zip(b["espacios"], b["base"].sum(axis=0)))
    assert tot["SALF"] == 0 and tot["ADELANTE"] == 0          # sin historia: irán por porcentaje
    madrid = b["prov"] == b["provincias"].index("28")
    assert b["base"][madrid][:, P.COL["FA"]].sum() == 0       # en Madrid compiten FA y Podemos: ninguna hereda a Sumar
    barcelona = b["prov"] == b["provincias"].index("08")
    assert b["base"][barcelona][:, P.COL["FA"]].sum() > 300_000   # en Barcelona solo Comuns-Front Ampli: hereda


def _noche_ficticia(b, carpeta, semilla=3):
    rng = np.random.default_rng(semilla)
    np_, ne = len(b["provincias"]), len(b["espacios"])
    final = b["base"] * rng.uniform(0.85, 1.15, size=(np_, ne))[b["prov"]]
    validos = b["base"].sum(axis=1)
    listas, _ = P._listas()
    for esp, cuota in (("FA", 0.06), ("PODEMOS", 0.04), ("SALF", 0.035)):
        donde = np.array([esp in listas[b["provincias"][p]] and b["base"][b["prov"] == p][:, P.COL[esp]].sum() == 0
                          for p in range(np_)])[b["prov"]]
        final[:, P.COL[esp]] += np.where(donde, cuota * validos * rng.uniform(0.6, 1.4, size=len(validos)), 0)
    final = np.round(final)
    f = np.where(b["censo"] < 20_000, 1.0, rng.choice([0.0, 0.3, 0.6], size=len(validos)))
    contado = np.round(final * f[:, None])
    esc_final = N.escanos(N._por_provincia({"provincias": b["provincias"], "prov": b["prov"]}, final), b["n_escanos"])
    cod = E.CODIGO
    regs = {p: [] for p in b["provincias"]}
    for i, mid in enumerate(b["municipios"]):
        if f[i] <= 0:
            continue
        regs[mid[:2]].append({"fecha": "2611181805", "ccaa": "99", "prov": mid[:2], "mun": mid[2:], "distrito": "99",
                              "nombre": mid, "mesas": 1, "censo": int(b["censo"][i]), "censo_escrutado": int(b["censo"][i] * f[i]),
                              "pct_escrutado": 100 * f[i], "votantes": int(contado[i].sum()), "pct_votantes": 0, "abstencion": 0,
                              "pct_abstencion": 0, "blancos": int(contado[i, 0]), "pct_blancos": 0, "nulos": 0, "pct_nulos": 0,
                              "partidos": [{"c": cod[e], "s": SIGLAS[e], "v": int(contado[i, k])}
                                           for k, e in enumerate(b["espacios"]) if k and contado[i, k] > 0]})
    carpeta.mkdir(parents=True, exist_ok=True)
    for p, r in regs.items():
        (carpeta / f"municipios_{p}.csv").write_text(E.escribir_municipios(r), encoding="utf-8")
    cont_prov = N._por_provincia({"provincias": b["provincias"], "prov": b["prov"]}, contado)
    esc_rec = N.escanos(cont_prov, b["n_escanos"])
    cc = np.bincount(b["prov"], weights=b["censo"] * f, minlength=np_)
    ct = np.bincount(b["prov"], weights=b["censo"], minlength=np_)

    def reg(tipo, prov, nombre, v, e, dip, c_tot, c_esc):
        return {"fecha": "2611181805", "tipo": tipo, "ccaa": "99", "prov": prov, "fijo": "9", "nombre": nombre, "mesas": 0,
                "censo": int(c_tot), "censo_escrutado": int(c_esc), "pct_escrutado": 100 * c_esc / c_tot,
                "votantes": int(v.sum()), "pct_votantes": 0, "abstencion": 0, "pct_abstencion": 0, "blancos": int(v[0]),
                "pct_blancos": 0, "nulos": 0, "pct_nulos": 0, "diputados": int(dip), "cod_ultima": "0", "cod_proxima": "0",
                "votos_faltan": 0, "partidos": [{"c": cod[x], "s": SIGLAS[x], "v": int(v[k]), "e": int(e[k])}
                                                for k, x in enumerate(b["espacios"]) if k and v[k] > 0]}
    tot = [reg("TO", "99", "Total", cont_prov.sum(axis=0), esc_rec.sum(axis=0), 350, ct.sum(), cc.sum())]
    tot += [reg("PR", p, p, cont_prov[i], esc_rec[i], b["n_escanos"][i], ct[i], cc[i]) for i, p in enumerate(b["provincias"])]
    (carpeta / "totales.csv").write_text(E.escribir_totales(tot), encoding="utf-8")
    return esc_final, esc_rec, 100 * cc.sum() / ct.sum()


def test_captura_de_un_envio_guardado(base, tmp_path):
    envio = tmp_path / "envio_7_20261118-180500"
    esc_final, esc_rec, pct = _noche_ficticia(base, envio)
    web = tmp_path / "vivo.json"
    r = K.capturar(K.Guardado(envio), "7", tmp_path, base["provincias"], base, simulacro=True, salida_web=web, guardar_bruto=False)
    assert r["envio"] == "7" and r["hora_interior"] == "18:05" and r["avisos"] == []
    assert r["fallos"] == ["avances.csv: " + r["fallos"][0].split(": ", 1)[1]]      # no había fichero de avances: se anota y sigue
    v = json.loads(web.read_text(encoding="utf-8"))
    assert v["simulacro"] is True and v["prueba"] is False and len(v["provincias"]) == 52
    assert v["nacional"]["escrutado"] == pytest.approx(pct, abs=0.01)
    assert sum(p["e"] for p in v["nacional"]["partidos"]) == 350
    proy = json.loads((envio / "proyeccion.json").read_text(encoding="utf-8"))
    assert proy["escrutado"] == pytest.approx(pct, abs=0.01) and proy["municipios_desconocidos"] == []
    assert sum(proy["nacional"]["escanos"].values()) == 350
    final = {e: int(n) for e, n in zip(base["espacios"], esc_final.sum(axis=0)) if n}
    rec = {e: int(n) for e, n in zip(base["espacios"], esc_rec.sum(axis=0)) if n}
    mal = lambda a: sum(abs(a.get(k, 0) - final.get(k, 0)) for k in set(a) | set(final)) // 2
    # Con los pueblos contados y las ciudades a medias, repartir lo contado se aleja del final; la proyección, poco.
    assert mal(rec) >= 8 and mal(proy["nacional"]["escanos"]) <= 5
    for esp in ("FA", "PODEMOS", "SALF"):                     # los tres espacios sin base salen proyectados
        assert proy["nacional"]["pct"][esp] > 2
    # La misma proyección se deja junto al fichero de la web (página oculta), con el recuento del envío para comparar.
    pub = json.loads((tmp_path / "proyeccion_29n.json").read_text(encoding="utf-8"))
    assert pub["nacional"] == proy["nacional"] and pub["envio"] == "7" and pub["simulacro"] is True
    assert sum(pub["recuento"]["nacional"].values()) == 350 and pub["recuento"]["nacional"] == rec
    assert len(pub["recuento"]["provincias"]) == 52 and pub["nombres"]["28"] == "Madrid"


def test_margen_segun_lo_escrutado():
    assert P.margen(2)["escanos_media"] > P.margen(30)["escanos_media"] > P.margen(90)["escanos_media"]
    assert P.margen(10)["escanos_max"] >= 8


def test_no_se_publica_un_recuento_que_retrocede(base, tmp_path):
    """Simulacro del 18-N: con el 85 % escrutado llegó un envío de totales a cero. No debe pisar la página."""
    envio = tmp_path / "envio_8_20261118-183300"
    _noche_ficticia(base, envio)
    web = tmp_path / "vivo.json"
    K.capturar(K.Guardado(envio), "8", tmp_path, base["provincias"], None, simulacro=True, salida_web=web, guardar_bruto=False)
    antes = web.read_text(encoding="utf-8")
    regs = E.leer_totales((envio / "totales.csv").read_text(encoding="utf-8"))
    for r in regs:
        r.update(censo_escrutado=0, pct_escrutado=0, votantes=0, blancos=0, partidos=[])
    (envio / "totales.csv").write_text(E.escribir_totales(regs), encoding="utf-8")
    r = K.capturar(K.Guardado(envio), "9", tmp_path, base["provincias"], None, simulacro=True, salida_web=web, guardar_bruto=False)
    assert any("retrocede" in f for f in r["fallos"]) and web.read_text(encoding="utf-8") == antes
    # Si el siguiente envío también va por debajo, Interior ha reiniciado el recuento (otra prueba, o la jornada real).
    r = K.capturar(K.Guardado(envio), "10", tmp_path, base["provincias"], None, simulacro=True, salida_web=web, guardar_bruto=False)
    assert not any("retrocede" in f for f in r["fallos"]) and json.loads(web.read_text(encoding="utf-8"))["nacional"]["escrutado"] == 0
    # Una sesión real (no simulacro) sí empieza de cero aunque el fichero publicado sea el del simulacro.
    K.capturar(K.Guardado(envio), "1", tmp_path, base["provincias"], None, simulacro=False, salida_web=web, guardar_bruto=False)
    assert json.loads(web.read_text(encoding="utf-8"))["nacional"]["escrutado"] == 0


def test_los_envios_se_guardan_comprimidos_y_se_releen(base, tmp_path):
    origen = tmp_path / "envio_5_20261118-180000"
    _noche_ficticia(base, origen)
    K.capturar(K.Guardado(origen), "5", tmp_path / "copia", ["28", "52"], None, salida_web=tmp_path / "v.json")
    guardado = next((tmp_path / "copia").iterdir())
    assert sorted(f.name for f in guardado.iterdir()) == ["municipios_28.csv.gz", "municipios_52.csv.gz", "totales.csv.gz"]
    assert K.Guardado(guardado).totales("5") == (origen / "totales.csv").read_bytes()
    assert (guardado / "municipios_28.csv.gz").stat().st_size < (origen / "municipios_28.csv").stat().st_size / 10


def test_siglas_reales_del_simulacro():
    from pipeline.convocatoria_29n import espacio
    casos = {"PAZ,CASA Y TRABAJO": "PODEMOS", "UPN-PP": "PP", "CCa-1ºCAN": "CC", "EH BILDU-ERC": "EH_BILDU", "JxCat": "JUNTS",
             "NC-BC, PODEMOS, IU, SUMAR": "NC", "COMPROMIS-EUPV-PODEM-ERPV": "COMPROMIS", "EAJ-PNV": "PNV", "FO": "OTROS"}
    assert {s: espacio("", s) for s in casos} == casos


# --- Manual final (24-N): ficheros por mesa, Senado y recomendaciones de descarga ---------------------------------

def test_formato_de_mesas_del_manual():
    """/mesas/getEscrutinio/2/{codPrv}.csv: 23 campos fijos + 80 × 4. Fichero fabricado según el manual, no real."""
    reg = {"fecha": "2611292330", "ccaa": "12", "prov": "28", "circ": "9", "mun": "079", "distrito": "01", "seccion": "004",
           "mesa": "B", "nombre": "MADRID 01-004-B", "mesas": 1, "censo": 812, "censo_escrutado": 812, "pct_escrutado": 100,
           "votantes": 560, "pct_votantes": 68.97, "abstencion": 252, "blancos": 4, "nulos": 6,
           "partidos": [{"c": "0007", "s": "PP", "v": 250}, {"c": "0001", "s": "PSOE", "v": 300}]}
    texto = E.escribir_municipios([reg])
    assert len(texto.splitlines()[0].split(";")) == 23 + 80 * 4
    assert sum(lon for _, lon in E.CAMPOS_MESA) == 156
    (m,) = E.leer_mesas(texto)
    assert (m["id"], m["seccion_id"], m["mesa"], m["censo"], m["pct_votantes"]) == ("28079", "2807901004", "B", 812, 68.97)
    assert [(p["s"], p["v"]) for p in m["partidos"]] == [("PP", 250), ("PSOE", 300)]


class _Falso:
    """Servicio de mentira: cuenta las peticiones y responde lo que diga `responder(ruta)`."""

    def __init__(self, responder):
        self.responder, self.pedidas = responder, []

    def _pedir(self, ruta):
        self.pedidas.append(ruta)
        return self.responder(ruta)

    def totales(self, envio, eleccion=2):
        return self._pedir(f"totales/{eleccion}/{envio}")

    def avances(self, envio):
        return self._pedir(f"avances/{envio}")

    def municipios(self, prov, envio):
        return self._pedir(f"municipios/{prov}/{envio}")

    def mesas(self, que, prov):
        return self._pedir(f"mesas/{que}/{prov}")


def _http(codigo):
    import urllib.error
    return urllib.error.HTTPError("http://x", codigo, "rechazado", None, None)


def test_tras_tres_403_seguidos_no_se_pide_el_resto(tmp_path):
    """Manual, apartado 4: ante un 401/403 hay que dejar de insistir (riesgo de bloqueo del usuario)."""
    def responder(ruta):
        raise _http(403)
    c = _Falso(responder)
    r = K.capturar(c, "9", tmp_path, [f"{i:02d}" for i in range(1, 53)], None, salida_web=tmp_path / "v.json")
    assert len(c.pedidas) == 3 and "no se pide el resto" in r["fallos"][-1]
    # Un fallo que no es 401/403 (un corte, un 500) no corta el envío: se sigue con las demás provincias.
    def cortes(ruta):
        raise TimeoutError("sin respuesta")
    c = _Falso(cortes)
    K.capturar(c, "9", tmp_path, ["01", "02", "03", "04"], None, salida_web=tmp_path / "v.json")
    assert len(c.pedidas) == 6


def test_ficheros_por_mesa_y_senado(tmp_path):
    """Los de mesa solo existen al acabar cada fase: lo que haya se guarda y lo que no, se deja a los tres fallos."""
    def responder(ruta):
        if "getEscrutinio/3" in ruta:
            raise _http(404)
        return b"contenido de " + ruta.encode()
    c = _Falso(responder)
    r = K.capturar_mesas(c, tmp_path, ["01", "02", "03", "04", "05"], pausa=0)
    assert r["avances"]["provincias"] == 5 and r["escrutinio_congreso"]["provincias"] == 5
    assert r["escrutinio_senado"]["provincias"] == 0 and "404" in r["escrutinio_senado"]["ultimo_error"]
    assert len(c.pedidas) == 5 + 5 + 3
    carpeta = Path(r["carpeta"])
    assert len(list(carpeta.iterdir())) == 10
    assert gzip.decompress((carpeta / "escrutinio_congreso_04.csv.gz").read_bytes()) == b"contenido de mesas/getEscrutinio/2/04"
    f = K.capturar_senado(_Falso(lambda ruta: b"senado " + ruta.encode()), "12", tmp_path)
    assert f.parent.name == "senado" and f.name.startswith("envio_12_") and gzip.decompress(f.read_bytes()) == b"senado totales/3/12"


def test_la_jornada_real_no_arranca_con_restos_de_una_prueba(tmp_path):
    f = tmp_path / "vivo_29n.json"
    f.write_text(json.dumps({"simulacro": True, "nacional": {"escrutado": 98.5}}), encoding="utf-8")
    assert K._es_simulacro(f)
    E.vaciar(f)
    d = json.loads(f.read_text(encoding="utf-8"))
    assert not K._es_simulacro(f) and d["nacional"]["escrutado"] == 0 and len(d["provincias"]) == 52
    assert json.loads((tmp_path / "pantallas_29n.json").read_text(encoding="utf-8"))["fase"] == "previa"


def test_cabecera_user_agent():
    c = E.Cliente("https://ejemplo.invalid/", "u", "c")
    assert c.cabeceras["User-Agent"] and c.cabeceras["Authorization"].startswith("Basic ")


def test_analisis_de_la_prueba_recuento_frente_a_proyeccion():
    """`analisis_prueba.analizar`: distancia de cada envío al reparto final (el recuento del último)."""
    from pipeline import analisis_prueba as A
    def envio(n, esc, rec, proy=None):
        r = {"envio": str(n), "hora": "", "escrutado": esc, "recuento": rec, "recuento_prov": {"28": rec},
             "pct": {"PP": 30.0 + n, "PSOE": 30.0}}
        if proy:
            r |= {"proyeccion": proy, "proyeccion_prov": {"28": proy}, "proyeccion_pct": {"PP": 33.0, "PSOE": 30.0}, "margen": 1.0}
        return r
    serie = A.analizar([envio(1, 10, {"PP": 12, "PSOE": 20, "VOX": 6}, {"PP": 15, "PSOE": 17, "VOX": 6}),
                        envio(2, 50, {"PP": 15, "PSOE": 18, "VOX": 5}, {"PP": 16, "PSOE": 17, "VOX": 5}),
                        envio(3, 99, {"PP": 16, "PSOE": 17, "VOX": 5})])
    assert [r["rec_mal"] for r in serie] == [4, 1, 0] and [r.get("proy_mal") for r in serie] == [1, 0, None]
    assert serie[0]["dentro_margen"] and serie[0]["rec_err_pct"] == 2.0 and serie[0]["proy_err_pct"] == 0.0
    texto = A.resumen(serie)
    assert "más cerca del final que el recuento en 2" in texto and "sin proyección publicada" in texto
    assert A.mal({"PP": 2}, {"PSOE": 2}) == 2 and A.resumen([]).startswith("No hay envíos")


def test_no_se_publican_datos_de_una_prueba_anterior(base, tmp_path):
    """Antes de empezar, el servicio puede seguir dando el último envío de la prueba anterior: se guarda, no se publica."""
    from datetime import datetime
    envio = tmp_path / "envio_130_20261118-212600"            # la noche ficticia lleva fecha de totalización del 18-N
    _noche_ficticia(base, envio)
    web = tmp_path / "vivo.json"
    r = K.capturar(K.Guardado(envio), "130", tmp_path, ["28"], None, simulacro=True, salida_web=web, guardar_bruto=False,
                   hoy=datetime(2026, 11, 25, 14, 50))
    assert r["antiguo"] and "hace 7 días" in r["fallos"][-1] and not web.exists()
    # Sin recuento (constitución y avances) la fecha antigua no bloquea: en la prueba del 25-N Interior sirvió así los totales.
    regs = E.leer_totales((envio / "totales.csv").read_text(encoding="utf-8"))
    for x in regs:
        x.update(censo_escrutado=0, pct_escrutado=0, votantes=0, blancos=0, partidos=[])
    cero = tmp_path / "envio_1_20261125-150000"
    cero.mkdir()
    (cero / "totales.csv").write_text(E.escribir_totales(regs), encoding="utf-8")
    r = K.capturar(K.Guardado(cero), "1", tmp_path, [], None, simulacro=True, salida_web=web, guardar_bruto=False,
                   hoy=datetime(2026, 11, 25, 15, 0))
    assert "antiguo" not in r and json.loads(web.read_text(encoding="utf-8"))["nacional"]["escrutado"] == 0
    web.unlink()
    # El mismo día, o pasada la medianoche de la noche electoral, sí se publica.
    r = K.capturar(K.Guardado(envio), "130", tmp_path, ["28"], None, simulacro=True, salida_web=web, guardar_bruto=False,
                   hoy=datetime(2026, 11, 19, 0, 20))
    assert "antiguo" not in r and web.exists()
