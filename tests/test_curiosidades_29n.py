"""Temas para artículos (pipeline/curiosidades_29n.py) con los ficheros municipales reales del simulacro del 18-N."""
import json
from pathlib import Path

from pipeline import curiosidades_29n as C

DATOS = Path(__file__).parent / "datos" / "simulacro"
VIVO = json.loads((C.WEB / "simulacro_29n.json").read_text(encoding="utf-8"))


def test_genera_temas_con_reglas_y_filas():
    d = C.generar(C.leer_envio(DATOS), VIVO)
    assert d["municipios"] > 100 and 0 < d["municipios_completos"] <= d["municipios"]
    assert len(d["temas"]) >= 25
    for t in d["temas"]:
        assert t["titular"] and t["regla"] and t["filas"]
        assert all(len(f) == len(t["columnas"]) for f in t["filas"]), t["id"]
    ids = {t["id"] for t in d["temas"]}
    assert {"fuerte_VOX", "ganadores", "abstencion", "pequenos", "tamano"} <= ids


def test_subidas_y_caidas_llevan_el_signo_que_dicen():
    d = C.generar(C.leer_envio(DATOS), VIVO)
    for t in d["temas"]:
        if t["id"].startswith("cae_") or t["id"] == "participacion_cae":
            assert all(f[1] < 0 for f in t["filas"]), t["id"]
        if t["id"].startswith("sube_") or t["id"] == "participacion_sube":
            assert all(f[1] > 0 for f in t["filas"]), t["id"]


def test_nombres_de_interior_a_tipo_titulo():
    assert C._bonito("CORUÑA, A") == "A Coruña"
    assert C._bonito("BASURTO/ZORROZA") == "Basurto/Zorroza"
    assert C._bonito("VALLE DE MENA") == "Valle de Mena"
