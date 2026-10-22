"""Rutas y grupos de columnas del pipeline.

El Parquet bruto vive FUERA de la repo (pesa >100 MB, límite de GitHub).
Por defecto: <repo>/../datos/db_mesas.parquet. Se puede cambiar con la
variable de entorno ELECCIONES_RAW.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("ELECCIONES_RAW", REPO.parent / "datos" / "db_mesas.parquet"))
CLEAN_DIR = Path(os.environ.get("ELECCIONES_CLEAN", REPO / "data" / "clean"))

# Elecciones en orden cronológico (`eleccion` es texto; 2019a/2019b son abril/noviembre).
ELECCIONES = ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]

# --- Columnas que NO se pasan al Parquet limpio -----------------------------
# meta_*: información del resultado de la propia elección (fuga de información).
# split_sugerido: valida en 2019b (repetición de 2019a), validación demasiado optimista.
DROP_PREFIXES = ("meta_",)
DROP_COLS = {"split_sugerido"}

# --- Tipos -------------------------------------------------------------------
# Identificadores y códigos: SIEMPRE texto (ceros a la izquierda).
CODE_COLS = {
    "eleccion", "mesa_id", "seccion_id", "municipio_id", "ccaa_cod", "prov_cod",
    "mun_cod", "distrito", "seccion", "mesa", "comarca", "partido_judicial",
}
DATE_COLS = {"fecha"}
BOOL_TEXT_COLS = {"es_repeticion"}  # 'True'/'False'
BOOL_01_COLS = {  # 0/1 → boolean
    "gana_izquierda", "mun_es_mayor_de_prov", "gob_ccaa_igual_estado",
    "tiene_ret1_mun", "tiene_ret2_mun", "tiene_ret1_secc",
}
INT_COLS = {
    "conv_idx", "anio", "mes", "votos_blancos", "votos_nulos", "votos_candidaturas",
    "votos_izquierda", "votos_centro_izquierda", "votos_centro_derecha", "votos_derecha",
    "votos_reg_izquierda", "votos_reg_derecha", "votos_otros", "votos_pp", "votos_psoe",
    "votos_vox", "votos_podemos_sumar", "votos_cs", "votos_iu", "votos_upyd", "votos_erc",
    "votos_ciu_jxcat", "votos_pnv", "votos_eh_bildu", "votos_bng", "votos_cc",
    "votos_compromis", "votantes", "votos_validos", "votos_contabilizados",
    "votos_otras_familias", "votos_izquierda_total", "votos_derecha_total",
    "censo_ine", "censo_escrutinio", "censo_cere", "votantes_cere", "votantes_avance_1",
    "votantes_avance_2", "mun_poblacion", "mun_n_mesas", "mun_censo", "mun_blancos",
    "mun_nulos", "mun_votos_candidaturas", "prov_poblacion", "prov_n_mesas", "prov_censo",
    "prov_blancos", "prov_nulos", "prov_votos_candidaturas", "prov_escanos",
    "mun_rango_poblacion_prov", "n_mesas_seccion", "inmigrantes", "criminalidad",
    "gob_ccaa_anios", "gob_estado_anios", "descuadre_votos",
    "desfase_edad_media", "desfase_escolarizacion", "desfase_esperanza_vida",
    "desfase_poblacion_provincia", "desfase_pct_mujeres", "desfase_inmigrantes",
    "desfase_tasa_paro", "desfase_criminalidad", "desfase_pib_per_capita",
    "desfase_acceso_internet", "desfase_tasa_pobreza",
}
# Resto de columnas: texto si están en TEXT_COLS, DOUBLE en cualquier otro caso.
TEXT_COLS = {
    "ccaa", "provincia", "municipio", "bloque_ganador", "familia_ganadora",
    "datos_oficiales", "mun_tramo_poblacion", "gob_ccaa_partido", "gob_ccaa_familia",
    "gob_ccaa_bloque", "gob_estado_partido", "gob_estado_bloque",
}

# --- Resultados electorales --------------------------------------------------
PARTIDOS = ["pp", "psoe", "vox", "podemos_sumar", "cs", "iu", "upyd", "erc",
            "ciu_jxcat", "pnv", "eh_bildu", "bng", "cc", "compromis"]
BLOQUES = ["izquierda", "centro_izquierda", "centro_derecha", "derecha",
           "reg_izquierda", "reg_derecha", "otros"]
DESFASE_COLS = [
    "desfase_edad_media", "desfase_escolarizacion", "desfase_esperanza_vida",
    "desfase_poblacion_provincia", "desfase_pct_mujeres", "desfase_inmigrantes",
    "desfase_tasa_paro", "desfase_criminalidad", "desfase_pib_per_capita",
    "desfase_acceso_internet", "desfase_tasa_pobreza",
]
