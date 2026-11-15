"""Simulador de escaños: ajuste territorial + d'Hondt, backtest y paridad con el JavaScript de la web.

Solo usa ficheros de la repo (web/data/resultados.json, data/web/29n/): no se salta en la nube.
"""
import json
import shutil
import subprocess

import pytest

from pipeline import config as C, simulador as S


@pytest.fixture(scope="module")
def datos():
    return S.base_29n()


@pytest.fixture(scope="module")
def inicio(datos):
    return {e["id"]: e["inicio"] for e in datos["espacios"]}


def test_ajuste_respeta_filas_y_columnas():
    base = {"a": {"x": 10.0, "y": 30.0}, "b": {"x": 40.0, "y": 20.0}}
    r = S.ajustar(base, {"x": 60.0, "y": 40.0}, {"a": 50.0, "b": 50.0})
    assert sum(r["a"].values()) == pytest.approx(50) and sum(r["b"].values()) == pytest.approx(50)
    assert r["a"]["x"] + r["b"]["x"] == pytest.approx(60)
    assert r["a"]["x"] < r["b"]["x"]          # conserva el perfil: x sigue siendo más fuerte en b


def test_ajuste_sin_cambios_devuelve_la_base():
    base = {"a": {"x": 10.0, "y": 30.0}, "b": {"x": 40.0, "y": 20.0}}
    r = S.ajustar(base, {"x": 50.0, "y": 50.0}, {"a": 40.0, "b": 60.0})
    assert r["a"] == pytest.approx(base["a"]) and r["b"] == pytest.approx(base["b"])


def test_base_29n_cuadra_con_2023(datos):
    assert len(datos["provincias"]) == 52
    assert datos["validos"] == 24_688_087                       # votos válidos de 2023 (Interior, con CERA)
    assert sum(d["escanos"] for d in datos["provincias"].values()) == 350
    assert sum(datos["escanos_2023"].values()) == 350
    assert datos["escanos_2023"]["PP"] == 138 and datos["escanos_2023"]["IZQ"] == 31   # PP + UPN; Sumar
    assert all(d["resto"] > 0 for d in datos["provincias"].values())


def test_voto_de_2023_reproduce_los_escanos_de_2023(datos, inicio):
    """Con el voto y el mapa de escaños de 2023 sale el reparto oficial en 49 provincias. Cambian tres,
    por cómo se presentan las candidaturas en 2026:
      - Navarra: UPN va en coalición con el PP (2 escaños juntos; en 2023, 1 + 1).
      - Las Palmas: la lista conjunta NC-Podemos-IU-Sumar suma 2 (Sumar tuvo 1); el PP baja de 3 a 2.
      - Santa Cruz de Tenerife: Vox no concurrió en 2023 y ahora sí; con su cuota media le quita uno al PSOE.
    """
    r = S.simular(datos, inicio, "escanos_2023")
    t = r["total"]
    assert t == {"PP": 137, "PSOE": 120, "VOX": 34, "FA": 26, "ERC": 7, "JUNTS": 7, "EH_BILDU": 6, "PNV": 5,
                 "COMPROMIS": 4, "NC": 2, "BNG": 1, "CC": 1}
    assert r["escanos"]["31"] == {"PP": 2, "PSOE": 2, "EH_BILDU": 1}
    assert r["escanos"]["35"] == {"PSOE": 3, "PP": 2, "NC": 2, "VOX": 1}
    assert r["escanos"]["38"] == {"PP": 3, "PSOE": 2, "CC": 1, "VOX": 1}
    oficial = {p: sorted(x["e"] for x in v["partidos"] if x["e"])
               for p, v in next(e for e in S.cargar() if e["id"] == "2023")["provincias"].items()}
    distintas = sorted(p for p in oficial if sorted(r["escanos"][p].values()) != oficial[p])
    assert distintas == ["31", "35", "38"]


def test_listas_sin_historia_en_la_provincia(datos):
    assert datos["sin_historia"] == [{"provincia": "38", "espacio": "VOX"}]
    assert datos["provincias"]["38"]["base"]["VOX"] == 62467      # 12,6 % (cuota de Vox donde sí concurrió)


def test_mapa_del_29n_mueve_un_escano_de_cadiz_a_madrid(datos, inicio):
    a = S.simular(datos, inicio, "escanos_2023")["escanos"]
    b = S.simular(datos, inicio)["escanos"]
    distintas = sorted(p for p in a if a[p] != b[p])
    assert distintas == ["11", "28"]
    assert sum(b["28"].values()) == 38 and sum(b["11"].values()) == 8


def test_escenario_suma_350_y_la_barrera_se_aplica(datos, inicio):
    esc = dict(inicio, PP=32.0, PSOE=29.5, VOX=15.0, FA=6.0, PODEMOS=4.0, SALF=3.0)
    r = S.simular(datos, esc)
    assert sum(r["total"].values()) == 350
    for p, fila in r["escanos"].items():
        validos = sum(r["votos"][p].values())
        for e in fila:
            assert r["votos"][p][e] >= 0.03 * validos - 1, (p, e)


def test_backtest_error_medido():
    """El método, con el resultado nacional real, falla entre 4 y 13 escaños de 350 (2000–2023)."""
    bt = S.backtest()
    assert [b["a"] for b in bt] == ["2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]
    errores = [b["escanos_mal_nacional"] for b in bt]
    assert min(errores) == 4 and max(errores) == 13
    assert sorted(errores)[len(errores) // 2] == 6
    peor = max(bt, key=lambda b: b["escanos_mal_nacional"])
    assert peor["a"] == "2015" and "PODEMOS_SUMAR" in peor["sin_historia"]   # irrupción de partidos nuevos
    assert max(b["max_error_partido"] for b in bt) == 9


def test_json_de_la_web_al_dia(datos):
    web = json.loads(S.SALIDA.read_text(encoding="utf-8"))
    assert web["provincias"] == json.loads(json.dumps(datos["provincias"]))
    assert web["espacios"] == datos["espacios"]


def test_javascript_da_el_mismo_reparto(datos, inicio):
    node = shutil.which("node")
    if not node:
        pytest.skip("No hay node para ejecutar web/simulador.js")
    escenarios = [inicio, dict(inicio, PP=32.0, PSOE=29.5, VOX=15.0, FA=6.0, PODEMOS=4.0, SALF=3.0),
                  dict(inicio, PP=28.0, PSOE=27.0, VOX=19.0, FA=4.0, PODEMOS=5.5, SALF=5.0, JUNTS=1.2),
                  dict(inicio, PP=40.0, PSOE=35.0, VOX=14.0, FA=8.0, PODEMOS=3.0, SALF=4.0)]   # suma > 100: se reescala
    guion = ("const M=require(process.argv[1]);const fs=require('fs');"
             "const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
             "const esc=JSON.parse(fs.readFileSync(0,'utf8'));"
             "console.log(JSON.stringify(esc.map(e=>M.simular(d,e).escanos)));")
    out = subprocess.run([node, "-e", guion, str(C.REPO / "web" / "simulador.js"), str(S.SALIDA)],
                         input=json.dumps(escenarios), capture_output=True, text=True, check=True).stdout
    for esc, js in zip(escenarios, json.loads(out)):
        assert js == S.simular(datos, esc)["escanos"]
