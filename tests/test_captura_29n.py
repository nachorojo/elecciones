"""Recuento por municipio, base del 29N, proyección y captura de un envío, de extremo a extremo y sin red.

Se fabrica una «noche» ficticia (la base de 2023 con cambios distintos por provincia, más Podemos, Frente
Amplio y Se Acabó la Fiesta), se escribe en el formato de la API de Interior, y se comprueba que la captura
la lee, actualiza el fichero de la web y proyecta un reparto cercano al final.
"""
import json

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
    cod = {e: f"{i:04d}" for i, e in enumerate(b["espacios"])}
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


def test_margen_segun_lo_escrutado():
    assert P.margen(2)["escanos_media"] > P.margen(30)["escanos_media"] > P.margen(90)["escanos_media"]
    assert P.margen(10)["escanos_max"] >= 8
