"""Un test (o varios) por cada problema de la lista de CLAUDE.md > Datos > Problemas conocidos.

Convención: cada test reproduce el problema en la vista `raw` y comprueba cómo queda en `mesas`
(el Parquet limpio). Si un test de "reproduce" empieza a fallar es que cambió el bruto: revisar.
Los números son los verificados en octubre de 2026.
"""
import pytest

N_FILAS = 573_617
ELECCIONES = ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]


# --- Estructura general ------------------------------------------------------
def test_filas_y_elecciones(q):
    assert q.one("select count(*) from mesas") == N_FILAS
    assert [r[0] for r in q("select eleccion from mesas group by 1 order by min(conv_idx)")] == ELECCIONES
    assert {r[0] for r in q("select distinct eleccion from mesas")} == set(ELECCIONES)


def test_mesa_unica_por_eleccion(q):
    assert q.one("select count(*) - count(distinct (eleccion, mesa_id)) from mesas") == 0


def test_se_quitan_meta_y_split(q):
    cols = {r[0] for r in q("describe select * from mesas")}
    assert not [c for c in cols if c.startswith("meta_")]
    assert "split_sugerido" not in cols


# --- 1. CSV mal formado ------------------------------------------------------
def test_1_municipios_con_coma_se_leen_enteros(q):
    # 73 líneas venían entrecomilladas; ya desenvueltas, la fila debe tener todas las columnas.
    assert q.one("select count(*) from raw where municipio like '%,%'") == 73
    # Si la línea hubiera quedado mal, el id o los votos no serían números.
    assert q.one("select count(*) from mesas where municipio_nombre_original like '%,%' and votantes is null") == 0
    assert q.one("select count(*) from mesas where municipio_nombre_original like '%,%' "
                 "and not regexp_full_match(municipio_id, '[0-9]{5}')") == 0


# --- 3. Ids siempre como texto ----------------------------------------------
def test_3_ids_son_texto_con_ceros(q):
    tipos = dict(q("select column_name, column_type from (describe select * from mesas)"))
    for c in ("municipio_id", "seccion_id", "mesa_id", "prov_cod", "ccaa_cod", "mun_cod", "distrito"):
        assert tipos[c] == "VARCHAR", c
    assert q.one("select count(*) from mesas where not regexp_full_match(municipio_id, '[0-9]{5}')") == 0
    assert q.one("select count(*) from mesas where municipio_id = '04003'") > 0
    assert q.one("select count(*) from mesas where length(prov_cod) <> 2 or length(distrito) <> 2") == 0


def test_3b_secciones_con_sufijo_de_letra(q):
    # No documentado antes: Zaragoza 1996-2004 usa secciones tipo 011A (formato antiguo del INE).
    n = q("select eleccion, count(*) from mesas where flag_seccion_con_sufijo group by 1 order by 1")
    assert n == [("1996", 23), ("2000", 15), ("2004", 15)]
    assert q.one("select count(distinct municipio_id) from mesas where flag_seccion_con_sufijo") == 1
    assert q.one("select count(*) from mesas where not flag_seccion_con_sufijo "
                 "and not regexp_full_match(seccion_id, '[0-9]{10}')") == 0


# --- 4. Nombres inconsistentes ----------------------------------------------
def test_4_nombres_de_municipio_varian_entre_elecciones(q):
    assert q.one("select count(distinct municipio_nombre_original) from mesas where municipio_id = '28005'") > 1


def test_4_una_fila_por_municipio_en_la_dimension(q):
    assert q.one("select count(*) - count(distinct municipio_id) from dim_municipios") == 0
    assert q.one("select count(*) from dim_municipios") == q.one("select count(distinct municipio_id) from mesas")
    assert q.one("select n_variantes_nombre from dim_municipios where municipio_id = '28005'") > 1
    # el nombre canónico no es la variante en mayúsculas
    assert q.one("select nombre from dim_municipios where municipio_id = '28005'") == "Alcalá de Henares"


def test_4_mesas_no_expone_columna_municipio(q):
    cols = {r[0] for r in q("describe select * from mesas")}
    assert "municipio" not in cols and "municipio_nombre_original" in cols


# --- 5. Socioeconómicas provinciales ----------------------------------------
@pytest.mark.parametrize("col", ["tasa_paro", "pib_per_capita", "esperanza_vida", "edad_media"])
def test_5_variable_socioeconomica_es_unica_por_provincia_y_eleccion(q, col):
    assert q.one(f"select max(n) from (select count(distinct {col}) n from mesas group by eleccion, prov_cod)") == 1


# --- 6. Datos socioeconómicos del futuro ------------------------------------
def test_6_desfase_en_primeras_elecciones(q):
    d = {r[0]: r[1:] for r in q(
        "select eleccion, max(desfase_tasa_paro), max(desfase_pib_per_capita), "
        "max(desfase_tasa_pobreza), max(desfase_criminalidad), max(desfase_acceso_internet) "
        "from mesas group by 1")}
    assert d["2000"][0] == 4          # paro de 2004 en la elección de 2000
    assert d["1996"][1] == 4          # PIB de 2000 en 1996
    assert d["2004"][2:] == (4, 4, 4)  # pobreza, criminalidad e internet de 2008 en 2004


def test_6_sin_dato_en_primeras_elecciones(q):
    assert q.one("select count(tasa_paro) from mesas where eleccion = '1996'") == 0
    assert q.one("select count(tasa_pobreza) from mesas where eleccion in ('1996', '2000')") == 0


def test_6_flag_socio_futuro(q):
    flag = dict(q("select eleccion, bool_or(flag_socio_futuro) from mesas group by 1"))
    assert [e for e in ELECCIONES if flag[e]] == ["1996", "2000", "2004"]


def test_6_desfase_no_tiene_signo(q):
    # El bruto solo guarda |años|. En 2023 hay desfases de 1-2 años cuya dirección NO se puede
    # saber desde los datos (CLAUDE.md dice "hacia atrás", sin verificar). Por eso el flag
    # `flag_socio_futuro` no se activa en 2023 pero `socio_desfase_max` sí lo refleja.
    assert q.one("select min(least(desfase_tasa_paro, desfase_pib_per_capita)) from mesas") >= 0
    r = dict(q("select eleccion, max(socio_desfase_max) from mesas group by 1"))
    assert r["2023"] == 2 and all(r[e] == 0 for e in ("2008", "2011", "2015", "2016", "2019a", "2019b"))
    assert r["2004"] == 4


# --- 7. Continuidad de secciones --------------------------------------------
def test_7_alcala_reorganiza_distritos_en_2011(q):
    r = dict(q("select eleccion, count(distinct distrito) from mesas where municipio_id = '28005' group by 1"))
    assert (r["2008"], r["2011"]) == (8, 5)


def test_7_marca_de_territorio_no_comparable(q):
    r = dict(q("select eleccion, bool_and(territorio_comparable_prev) from mesas "
               "where municipio_id = '28005' group by 1"))
    assert r["1996"] is None          # sin elección anterior
    assert r["2008"] is True
    assert r["2011"] is False         # cambio 8 -> 5 distritos
    assert r["2015"] is True


def test_7_correlacion_cae_donde_el_codigo_cambia_de_territorio(q):
    def corr(a, b):
        return q.one(f"""
            with s as (select eleccion, seccion_id, 100.0 * sum(votos_pp) / sum(votos_candidaturas) pp
                       from mesas where municipio_id = '28005' group by 1, 2)
            select corr(x.pp, y.pp) from s x join s y using (seccion_id)
            where x.eleccion = '{a}' and y.eleccion = '{b}'""")
    assert corr("2008", "2011") < 0.8     # ~0,67: mismo código, otro territorio
    # Referencia sin cambio de distritos ni de oferta (repetición electoral): ~0,97 (lo normal).
    # No usar 2011-2015: la irrupción de Cs/Podemos baja la correlación por motivos políticos.
    assert corr("2019a", "2019b") > 0.9


# --- 8. Bloques que no suman -------------------------------------------------
def test_8_bloques_no_cuadran_2015(q):
    n = q.one("select count(*) from mesas where eleccion = '2015' and flag_bloques_no_cuadran")
    assert n == 26_353
    assert 0.45 < n / q.one("select count(*) from mesas where eleccion = '2015'") < 0.47
    # coincide con la marca original
    assert q.one("select count(*) from mesas where eleccion = '2015' "
                 "and flag_bloques_no_cuadran <> (descuadre_votos <> 0)") == 0


def test_8_descuadre_tambien_en_1996_y_2000(q):
    # No documentado antes: aquí los bloques suman MENOS que las candidaturas.
    got = dict(q("select eleccion, count(*) from mesas where flag_bloques_no_cuadran group by 1"))
    assert got == {"1996": 16, "2000": 8, "2015": 26_353}


# --- 9. Columnas de partido no homogéneas -----------------------------------
def test_9_columnas_vacias_por_eleccion(q):
    vacia = {(e, c) for e, c in q("select eleccion, columna from dim_partidos where columna_vacia")}
    assert ("2023", "cs") in vacia
    for e in ("2015", "2016", "2019b"):
        assert (e, "compromis") in vacia
    assert ("2019a", "compromis") not in vacia


def test_9_iu_dentro_de_podemos_en_2016(q):
    iu, ps = q("select (select votos_total from dim_partidos where eleccion='2016' and columna='iu'), "
               "(select votos_total from dim_partidos where eleccion='2016' and columna='podemos_sumar')")[0]
    assert iu < 0.01 * ps


def test_9_familias_solo_las_fijadas(q):
    fam = dict(q("select distinct partido, familia from dim_partidos"))
    assert fam["PP"] == "centro_derecha" and fam["PSOE"] == "centro_izquierda"
    assert fam["Vox"] == "derecha" and fam["Podemos/Sumar"] == "izquierda"
    assert fam["Cs"] == "por_confirmar"
    assert q.one("select count(*) from dim_partidos") == 10 * 14


# --- 10. Avances imposibles --------------------------------------------------
def test_10_avances_imposibles_marcados(q):
    # El bruto: avance_2 > votantes en 150-240 mesas por elección.
    for e, n in q("select eleccion, count(*) from raw "
                  "where cast(votantes_avance_2 as double) > cast(votantes as double) group by 1"):
        assert 90 < n < 250, e
    assert q.one("select count(*) from mesas where votantes_avance_2 > votantes and not flag_avance_imposible") == 0
    assert q.one("select count(*) from mesas where votantes_avance_1 > votantes_avance_2 "
                 "and not flag_avance_imposible") == 0
    share = q.one("select avg(flag_avance_imposible::int) from mesas")
    assert 0.002 < share < 0.01       # 0,2-1 % de las mesas


def test_10_avances_iguales_se_marcan_aparte(q):
    assert q.one("select count(*) from mesas where flag_avances_iguales") > 0


# --- 11. indice_izq_der ------------------------------------------------------
def test_11_indice_izq_der_es_derecha_menos_izquierda(q):
    assert q.one("select max(abs(indice_izq_der - (pct_derecha_total - pct_izquierda_total))) from mesas") < 1e-9


# --- 12. datos_oficiales -----------------------------------------------------
def test_12_datos_oficiales_patron_observado(q):
    # Significado PENDIENTE de confirmar. Solo se fija el patrón para detectar cambios.
    got = dict(q("select eleccion, any_value(datos_oficiales) from mesas group by 1"))
    assert [e for e in ELECCIONES if got[e] == "N"] == ["1996", "2000", "2004"]
    # un único valor por elección
    assert q("select eleccion from mesas group by 1 having count(distinct datos_oficiales) > 1") == []


# --- 13. poblacion_provincia vs prov_poblacion ------------------------------
def test_13_poblaciones_provinciales_no_coinciden(q):
    # Decisión pendiente: se mantienen las dos columnas hasta saber qué fuente es cada una.
    assert q.one("select count(*) from mesas where poblacion_provincia = prov_poblacion") == 0
    r = q.one("select max(abs(prov_poblacion / poblacion_provincia - 1)) from mesas")
    assert 0.01 < r < 0.1


# --- Lo que SÍ está bien (y no debe romperse al limpiar) --------------------
def test_aritmetica_electoral(q):
    assert q.one("select count(*) from mesas where votos_candidaturas + votos_blancos <> votos_validos") == 0
    assert q.one("select count(*) from mesas where votos_validos + votos_nulos <> votantes") == 0


def test_votantes_sobre_censo_solo_18_mesas_marcadas(q):
    # CLAUDE.md decía "votantes <= censo"; no es del todo cierto: 18 excepciones.
    assert q.one("select count(*) from mesas where flag_votantes_gt_censo") == 18
    assert q.one("select count(*) from mesas where votantes > censo_escrutinio and not flag_votantes_gt_censo") == 0


# --- Porcentajes recalculados ------------------------------------------------
def test_participacion_recalculada(q):
    assert q.one("select max(abs(participacion - 100.0 * votantes / censo_escrutinio)) from mesas "
                 "where censo_escrutinio > 0") < 1e-9


@pytest.mark.parametrize("col", ["pct_pp", "pct_psoe", "pct_izquierda", "pct_derecha", "pct_blancos", "pct_nulos",
                                 "participacion"])
def test_pct_recalculado_coincide_con_bruto_en_mesas_sin_problema(q, col):
    # Valida los denominadores elegidos: donde el bruto es correcto, el recalculado es igual.
    d = q.one(f"""select max(abs(m.{col} - cast(r.{col} as double)))
                  from mesas m join raw r on r.mesa_id = m.mesa_id and r.eleccion = m.eleccion
                  where not m.flag_bloques_no_cuadran and m.{col} is not null and r.{col} is not null""")
    assert d < 1e-6, f"{col}: dif. máxima {d}"


def test_pct_2015_ahora_cuadra(q):
    # En 2015 el bruto usa la suma de bloques (inflada) como denominador; aquí, votos_candidaturas.
    s = q.one("select max(pp_psoe) from (select pct_pp + pct_psoe pp_psoe from mesas where eleccion = '2015')")
    assert s <= 100 + 1e-9
