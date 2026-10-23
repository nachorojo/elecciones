# Web electoral por mesa (Generales 1996–2023 → 29N)

## Objetivo
1. Web pública de consulta: resultados de las generales 1996–2023 por municipio y sección censal, con contexto socioeconómico. Se actualizará con el 29N.
2. Más adelante: modelo predictivo validado (proyección de escrutinio la noche electoral y/o reparto territorial).

## Datos

### Ubicación (FUERA del repo)
- Carpeta: `C:\Users\iir44590\OneDrive - Atresmedia Corporacion De Medios De Comunicacion SA\1. MIS DOCUMENTOS\_____IA_____\Claude\Proyectos Claude\Elecciones 2026\datos\` (desde la repo: `..\datos\`)
- La repo vive en `...\Elecciones 2026\repo\`. Entorno Python fuera de OneDrive: `%LOCALAPPDATA%\venvs\elecciones` (duckdb, pandas, pyarrow, pytest).
- `db_mesas.csv`: original, 1 GB. NO MODIFICAR.
- `db_mesas_limpio.csv`: original con 73 líneas desenvueltas (ver más abajo).
- `db_mesas.parquet`: generado desde el limpio, todo como VARCHAR, zstd. 573.617 filas, 198 columnas. **Usar este como punto de partida.**
- Nunca subir CSV/Parquet brutos a GitHub (límite de 100 MB por fichero). Añadir `data/raw/` y `data/clean/` a `.gitignore`.

### Estructura
- Una fila por mesa electoral. Diez elecciones: 1996, 2000, 2004, 2008, 2011, 2015, 2016, 2019a, 2019b, 2023 (`eleccion` es texto).
- Jerarquía: ccaa → provincia → municipio → distrito → sección → mesa (A/B/C/D/U).
- Las mesas dentro de una sección se reparten por apellidos, NO por calles. La unidad geográfica mínima es la sección censal.

### Problemas conocidos (verificados con muestras)
1. **CSV mal formado**: 73 filas (municipios con coma en el nombre, p. ej. `ALCORA/ALCORA,L'`) venían con la línea entera entrecomillada y las comillas interiores duplicadas. Corregido en `db_mesas_limpio.csv`. Si se lee el CSV, usar siempre `delim=',', quote='"', escape='"', header=true`.
2. **Nunca abrir el CSV con Excel**: rompe los decimales (locale ES) y los ceros a la izquierda de los ids.
3. **Ids siempre como texto**: `seccion_id` = `0400301001`, `municipio_id` = `04003`.
4. **Nombres de municipio inconsistentes entre elecciones** (`ALCALA DE HENARES` / `Alcalá de Henares` / `ALCALÁ DE HENARES`). Nunca agrupar ni cruzar por nombre: usar siempre `municipio_id`, y sacar los nombres visibles de una tabla canónica (INE).
5. **Las variables socioeconómicas son PROVINCIALES** (un único valor por provincia y elección). No permiten análisis por mesa ni por sección. Para renta por sección: INE ADRH (desde 2015).
6. **Hay datos socioeconómicos del futuro en los primeros años** (`desfase` > 0 significa dato posterior a la elección):
   - 2004 usa pobreza, criminalidad e internet de 2008.
   - 2000 usa el paro de 2004.
   - 1996 usa el PIB de 2000.
   - Paro sin dato en 1996; pobreza, criminalidad e internet sin dato en 1996–2000.
   - En 2023 el desfase es hacia atrás (correcto).
7. **Continuidad de secciones**: `ret1_secc_*` está bien calculado, pero empareja solo por `seccion_id`. Cuando un municipio reorganiza distritos, el mismo código pasa a ser otro territorio. En Alcalá (28005), entre 2008 y 2011 se pasó de 8 a 5 distritos y la correlación del %PP entre secciones con el mismo código cae a 0,67 (lo normal es 0,97). Solo 52 de 194 códigos existen en las diez elecciones. Hace falta un cruce territorial (cartografía INE ponderada por población) o, como mínimo, marcar los pares no comparables.
8. **En 2015 los bloques suman más que `votos_candidaturas`** en ~47 % de las mesas (~0,3 %, aprox. un voto por mesa). Algún partido está asignado a dos bloques. Lo marca `descuadre_votos`.
9. **Las columnas de partido no son homogéneas entre elecciones**: IU va dentro de `podemos_sumar` en 2016; Compromís = 0 en 2015, 2016 y 2019b; Cs = 0 en 2023. Hace falta una tabla de mapeo partido → columna → familia por elección.
10. **Avances imposibles**: en el 0,2–1 % de las mesas, `votantes_avance_2` > `votantes`, y en algunas `avance_1` = `avance_2`. Filtrarlas antes de usar los avances.
11. `indice_izq_der` = %derecha − %izquierda (positivo = derecha); el nombre confunde.
12. `datos_oficiales` = N en 1996–2004 y S desde 2008. **Significado confirmado** (documentación de Interior): S = dato oficial publicado por las Juntas Electorales; N = no oficial.
13. `poblacion_provincia` ≠ `prov_poblacion` (fuentes o años distintos). Elegir una.

14. **Secciones con sufijo de letra** (verificado 2026-10-22): en Zaragoza (50297) 1996–2004 hay 53 filas con `seccion_id` de 11 caracteres (`5029702011C`, formato antiguo del INE). Desaparecen desde 2008. `seccion_id` no siempre mide 10 dígitos. Marca: `flag_seccion_con_sufijo`.
15. **El descuadre de bloques no es solo de 2015**: en 1996 (16 mesas) y 2000 (8) los bloques suman *menos* que `votos_candidaturas`. Marca: `flag_bloques_no_cuadran`.
16. **`votos_contabilizados` = suma de bloques**, no votos válidos. Los `pct_*` de partidos/bloques del bruto usan ese denominador (inflado en 2015). El limpio usa `votos_candidaturas`.
17. **`desfase_*` no tiene signo** (solo |años|). Corrección al punto 6: en 2023 hay desfases de 1–2 años (población provincial, % mujeres, PIB) y **no se puede verificar** que sea "hacia atrás". `flag_socio_futuro` solo se activa en 1996–2004; `socio_desfase_max` da los años para todas.
18. **18 mesas con `votantes` > `censo_escrutinio`** (corrige "votantes ≤ censo"). Marca: `flag_votantes_gt_censo`.

### Lo que sí está bien
- Aritmética electoral en todas las elecciones: candidaturas + blancos = válidos; válidos + nulos = votantes. (Votantes ≤ censo: salvo las 18 mesas del punto 18.)
- `participacion`, `pct_blancos` y `pct_nulos` coinciden con los recuentos. Aun así, recalcular siempre desde los votos.
- Los nombres con tilde están bien en el Parquet y en el CSV (UTF-8). Si en la consola de Windows salen como `�`, es la consola, no los datos.

## Pipeline (paso 1, hecho)
```
python -m pipeline.run      # ~6 s; lee ..\datos\db_mesas.parquet (o ELECCIONES_RAW) y escribe data/clean/
python -m pytest            # 57 tests; se saltan si no hay Parquet bruto (ni ficheros de Interior)
```
- `data/clean/mesas.parquet`: 573.617 filas, tipado (ids en texto), sin `meta_*` ni `split_sugerido`, `pct_*`/`participacion` recalculados, más `flag_*`, `territorio_comparable_prev` y `socio_desfase_max`. **No borra ninguna mesa**: quien consuma decide qué filtrar.
- `municipio` pasa a `municipio_nombre_original`; el nombre visible sale de `dim_municipios` (provisional, a sustituir por el nomenclátor del INE).
- `dim_partidos`: `familia` solo está fijada para PP, PSOE, Vox y Podemos/Sumar; el resto es `por_confirmar` hasta validar con la redacción.
- Sin recalcular (vienen del bruto): `pct_izquierda_total`, `pct_derecha_total`, `pct_nacionalista`, `indice_izq_der`, `ret*`, `tend*`, `*_z`.
- Entorno: `pip install -r requirements.txt`. El venv de la sesión de Claude está fuera de OneDrive (`%LOCALAPPDATA%\venvs\elecciones`); no crear `.venv` dentro de la carpeta sincronizada.

## Reglas para el modelo
- **Eliminar `meta_*`**: es información del resultado de la propia elección.
- `votantes_avance_*` y `participacion_avance_*` solo se usan en el modelo de la noche electoral.
- No usar `split_sugerido`: valida en 2019b, que es la repetición de 2019a y da una validación demasiado optimista. Validar hacia delante elección a elección, tratando 2015–2016 y 2019a–2019b como bloques.
- Con historial completo y sin datos del futuro, las elecciones utilizables son 2008–2023.

## Reglas editoriales
- Mostrar los partidos como vista principal. Los bloques (PP = centro_derecha, Vox = derecha, PSOE = centro_izquierda, Podemos/Sumar = izquierda) y los índices ideológicos son agrupaciones opcionales con la metodología explicada, y deben validarse con la redacción antes de publicar.
- Redactar siempre a nivel de zona: "las secciones de menor renta votaron más a X", nunca "los pobres votan a X" (falacia ecológica).
- Cualquier estimación de voto se publica después de las 20:00 del día de la elección (veda de la LOREG).

## Plan
1. (HECHO 2026-10-22, pendiente de commit) `pipeline/`: Parquet limpio en `data/clean/`, con tipos correctos, porcentajes recalculados, tabla canónica de municipios y tabla de partidos/familias. Incluir tests que reproduzcan cada problema de la lista anterior.
2. Web v1 a nivel de municipio, con las diez elecciones.
3. Secciones: cruce territorial y mapa con cartografía por año (PMTiles). Renta ADRH desde 2015.
4. Modelo: base por municipio y después por sección; proyección para la noche electoral.

## Estructura propuesta
```
/pipeline      scripts de limpieza y agregación (DuckDB/Python)
/tests         validaciones de los datos
/data/raw      (gitignored) enlace o copia local del CSV
/data/clean    (gitignored) Parquet limpio
/data/web      agregados pequeños que consume la web
/web           frontend estático
```

## Fuente oficial: Interior (infoelectoral) — verificado 2026-10-23
- Ficheros oficiales en `..\datos\infoelectoral\congreso\02AAAAMM_MESA\` (las 10 elecciones; `.DAT` de ancho fijo + `FICHEROS.doc/rtf` con el diseño de registro). Descargados el 2026-10-23 desde `https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/02AAAAMM_MESA.zip` (la API del listado exige credencial del navegador; los zips son públicos). Más muestras de 2023 en `..\datos\infoelectoral\` (MUNI, TOTA, xlsx de Senado, Municipales, Cabildos).
- El dataset del TFM sale de estos ficheros. **Auditoría de las 10 elecciones** (`python -m pipeline.audit_interior`, 4 s): las 573.617 mesas coinciden con el fichero 09 oficial en censo, votantes, votos a candidaturas y avances (100 %). Es un test (`tests/test_interior.py`).
- Para descargar otras convocatorias hay que usar el navegador (Consultar en la página); el patrón de nombre es el mismo con otro tipo (03 Senado, 04 Municipales, 07 Europeo).
- **`datos_oficiales`** (problema 12, resuelto): "S" = dato publicado en medios oficiales por las Juntas Electorales; "N" = no oficial (1996–2004). Fuente: FICHEROS.doc.
- **`censo_cere` ≠ voto exterior**: CERE = censo de *residentes extranjeros en España* (vota en municipales); en Congreso vale 0. Se corrige la lectura anterior.
- **El CERA (voto exterior) NO está en `mesas.parquet`** pero sí en el fichero oficial: pseudo-mesas con municipio `999`, sección `0000`, mesa `U` (72 filas = 52 provincias + comunidades + total). Son 52 filas provinciales por elección (más filas de total autonómico/nacional con provincia 99, que no hay que sumar). Electores / votos a candidaturas del CERA (suma de las 52 provincias):

| 1996 | 2000 | 2004 | 2008 | 2011 | 2015 | 2016 | 2019a | 2019b | 2023 |
|---|---|---|---|---|---|---|---|---|---|
| 526.065 / 177.920 | 930.926 / 210.631 | 1.113.754 / 301.182 | 1.205.329 / 377.377 | 1.482.786 / 72.555 | 1.880.064 / 87.978 | 1.924.021 / 119.815 | 2.099.463 / 116.203 | 2.130.754 / 143.986 | 2.328.260 / 203.254 |

  El voto CERA se hunde en 2011 pese a que el censo crece; coincide con la reforma de 2011 que obligó a solicitar el voto (el "voto rogado"; dato de contexto, sin verificar aquí). En 2023 son el 0,8 % de los votos a candidaturas. Hay que añadirlo para repartir escaños (puede decidir el último escaño en provincias con mucho voto exterior).
- **CERA ya en el pipeline** (`pipeline/cera.py`, parte de `pipeline.run`): `data/clean/cera_provincia.parquet` (52 provincias × 10 elecciones: censo, blancos, nulos, votos a candidaturas) y `data/clean/cera_candidaturas.parquet` (votos por candidatura con siglas y candidatura cabecera nacional). Suma de candidaturas = total provincial en todas las elecciones salvo 2015 (1 voto de diferencia, del propio Interior). **Limitación 2015**: unas 600 candidaturas del CERA llevan códigos `9xxxxx` que no están en el fichero 03, así que sus votos (≈88.000, casi todo el CERA de 2015) quedan sin siglas. No mapeadas todavía a las columnas de partido de `mesas.parquet`.
- Avances de participación: 1.º a las 14:00 y 2.º a las 18:00 (fichero 02); cierre a las 20:00.
- Fuera de la base: Europeas 2024, autonómicas y municipales posteriores a 2023 (los únicos votos reales desde 23J). Pendiente de decidir si se incorporan.

## Definición del proyecto (acordada con Nacho, 2026-10-23)
- **Créditos:** la base de datos y el trabajo previo son de Mikel (Miguel Ibáñez González, TFM UAM, tutor David Domínguez), hijo de Nacho. Tendrá todos los créditos en lo que se publique; Claude también figura como colaborador.
- **Producto:** web para ondacero.es con (1) consulta histórica con buscador, (2) mapa, (3) chatbot, (4) predictor/simulador. Hay que partir de `datos\TFM\tfm_web\` (Flask + Ollama local) y mejorar/completar; **pendiente leer su código** (solo se ha leído su documentación).
- **Arquitectura objetivo:** web estática con datos y resultados del modelo precalculados (como Marcador/Cuadrante: Netlify, sin IA en producción). El LLM del chatbot es opcional; el diseño del TFM ya funciona sin él (reglas + plantillas).
- **Predictor:** escenario base de continuidad con intervalo ancho (calibrado por backtest, nunca presentado como pronóstico) + escenario del usuario ("el PSOE sube 3 escaños, ¿qué pasa?"). Disclaimer con el error medido del backtest. Las encuestas son una entrada más del escenario, separada del "puro dato". Backtest del TFM: 82,1 % de municipios acertados en 2023 *dado el resultado nacional real*, frente a ~68,5 % repitiendo el ganador de 2019b.
- **Motor de escaños HECHO** (`pipeline/escanos.py`, `python -m pipeline.escanos`): d'Hondt por circunscripción con barrera del 3 % de votos válidos (candidaturas + blancos, inclusiva). **Validado: reproduce los 520 repartos oficiales (52 circunscripciones × 10 elecciones) sin ninguna diferencia y sin sorteos**, usando los votos del fichero 08 de Interior (que ya incluyen el CERA). Comprobaciones: los escaños oficiales suman 350 en todas; Sainte-Laguë daría un reparto distinto en 185 de 520 (el test discrimina el método); la barrera es el 3 % y no el 5 % (Barcelona 1996/2000/2019a y Madrid 2008 lo demuestran). Límites: solo 4 casos ejercitan la barrera; el sorteo de empates no se puede reproducir (se devuelve `empate=True`); en 2000 (2 provincias) y 2008 (1) la suma de candidaturas difiere del total provincial del propio fichero 07. **Aún no probado**: repartir con votos *estimados* (lo que hará el simulador); eso exige estimar votos por provincia, incluido el CERA, y las listas del 29N (28 de octubre).
- **Noche electoral (a partir de las 20:00):** actualización continua desde el inicio del escrutinio. Pendiente saber de dónde llega el flujo en vivo y si hay registros con hora del 23J 2023 (sin orden histórico de llegada de mesas no se puede validar el sesgo de las primeras mesas).
- **Legal (a confirmar con Jurídico):** veda de sondeos en los últimos días previos (cinco, según recuerdo); y que un simulador alimentado con encuestas no quede afectado.
- **Cartografía:** no hay ninguna en la carpeta del TFM (solo un mosaico de provincias). Hay que descargar límites municipales y de sección por año.

## Calendario del 29N
- **28 de octubre de 2026**: se publican las listas al Congreso en cada una de las 52 circunscripciones y el número de diputados que elige cada una (dato del usuario, 2026-10-23). Recogerlo cuando salga: es la base del reparto de escaños.
- Veda: cualquier estimación de voto se publica después de las 20:00 del día de la elección (LOREG).

## Datos del INE / Oficina del Censo Electoral (censo de consulta, provisional)
- Carpeta: `..\datos\INE\Elecciones 2026\` (fuera de la repo). Descargadas el 2026-10-23: `Elecgral_2026_cc_tab1..12.xlsx` desde `https://www.ine.es/oficina_censo/elecgen2026/Elecgral_2026_cc_tabN.xlsx`.
- **Política: Claude descarga las tablas del INE por su cuenta** (autorizado por el usuario); al hacerlo, guardar con fecha y no sobrescribir. Pendientes de publicar: listas de votación definitivas, reclamaciones y voto por correo; al salir, repetir la descarga.
- Granularidad: provincia (tab3, 5, 8, 11, 12) y **municipio** (tab4, con código provincia + municipio = `municipio_id`). Nada por sección ni mesa: el censo del 29N por sección habrá que estimarlo.
- 29N frente a 2023: 36.761 secciones (+301), 60.970 mesas (+656), 35.958.711 electores en España (+817.513); 1.615.127 nuevos electores desde 2023; 2.769.645 electores CERA (voto exterior), que **no están en `mesas.parquet`** (ver "Fuente oficial: Interior").
- `tab11` es de *electores* (españoles de 18 años o más con derecho a voto), no de población: es el denominador correcto del voto.

## Pendiente de decidir
- Dónde se publica: CMS de Onda Cero (embebido) o web independiente (dominio y propiedad de la URL).
- Qué población provincial usar (`poblacion_provincia` vs `prov_poblacion`).
- Mapear las candidaturas (incluidas las del CERA) a las columnas de partido/familia; resolver el CERA 2015.
- Incorporar elecciones posteriores a 2023 (Europeas 2024, autonómicas).
