---
estado: "EN MARCHA — web de datos electorales por mesa (generales 1996–2023). Pendientes: actualización con el 29N y modelo predictivo."
revisado: "2026-10-31"
proximo: "Leer HANDOFF.md del repo (estado, decisiones, pendientes y trampas) y preparar la carga de resultados del 29N."
corre_en: "Netlify (proyecto `elecciones2030`) desde GitHub nachorojo/elecciones. Datos fuera del repo, en `Elecciones 2026/datos/` (OneDrive)."
bloqueos: "Ver «Pendiente de decidir» en este doc."
---

# Web electoral por mesa (Generales 1996–2023 → 29N)

> **Retomando el trabajo (otro PC, solo GitHub): lee primero [HANDOFF.md](HANDOFF.md)** — qué hay y qué no hay en la repo,
> cómo recuperar los datos, estado de la web, decisiones, pendientes y trampas. Este fichero es el detalle de datos y decisiones.

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
python -m pytest            # 68 tests; se saltan si no hay Parquet bruto (ni ficheros de Interior)
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
- **Legal (Nacho, 2026-10-23):** LOREG art. 69.7: "durante los cinco días anteriores al de la votación queda prohibida la publicación y difusión o reproducción de sondeos electorales por cualquier medio de comunicación" (BOE-A-1985-11672). Para el 29N, desde el 24 de noviembre. **Sigue sin confirmar** si un simulador/predictor propio (no es un sondeo) o uno alimentado con encuestas queda afectado: consultar a Jurídico antes de publicar nada predictivo, y plantear desactivarlo (o dejar solo resultados históricos) del 24 al 29 de noviembre.
- **Web estática v0 hecha** (`web/`, `netlify.toml`, `pipeline/export_web.py`): resultados oficiales de Interior por España y provincia con escaños, mosaico de provincias, historia de ganadores. Cifras oficiales (PP 2023: 8.160.837 votos, 33,06 % de válidos, 137 escaños), **no** las de la web local de Mikel (que da 33,33 %: porcentaje sobre votos a candidaturas, coaliciones asignadas al socio que encabeza las siglas, sin CERA). Participación = residentes (70,41 % en 2023); el CERA va aparte. `web/data/resultados.json` se regenera con `python -m pipeline.export_web` y se sube a la repo. Despliegue: Netlify conectado a la repo (publish = `web`), `noindex`. Colores de partido: clasificación de candidaturas de Mikel (`data/web/candidaturas_clasificadas_mikel.csv`).
- **Nivel municipio en la web** (`pipeline/export_municipios.py` → `web/data/mun/NN.json`, `partidos.json`, `indice.json`; 8.136 municipios × 10 elecciones; datos oficiales de los ficheros 05/06 de Interior, sin CERA, solo candidaturas con ≥1,5 % de los válidos, resto por diferencia). **Consistencia verificada**: suma de municipios + CERA = total provincial oficial, exacto en 2011, 2016, 2019a y 2019b; en el resto hay defectos de la fuente, siempre < 0,5 % de la provincia: descuadre de 1996 (1.013 votos) y 2000 (461), 2015 (47.548 votos, 51 provincias), La Rioja 2004 (−5), Soria 2008 (−124) y **Toledo 2023 (municipios suman 175 votos más que el total provincial; no explicado)**. Nombres: el INE invierte el artículo ("Coruña, A") y se normaliza ("A Coruña").
- **Cartografía INE (verificado 2026-10-23):** API OGC de GeoServer con capas de secciones de 2007 a 2025 por año (Secciones_AAAA), 2001 y 2011 del censo y la de 2026 (`SU.VectorStatisticalUnit`, 47.121 entidades = secciones + distritos, TIPO = SECCION|DISTRITO). La paginación solo funciona con `startIndex` (el parámetro estándar `offset` se ignora y devuelve siempre la primera página). Descarga de distritos: ~10.452 features, 100-150 MB, `pipeline/export_mapa.py` (`descargar_distritos`). Años 1996, 2000 y 2004: sin capa de sección anual (solo 2001 censal).
- **Mapa municipal HECHO** (`web/municipios.js`, `web/data/municipios.geojson`, `pipeline/export_mapa.py`): 8.132 municipios con los límites vigentes del INE (capa 2026), unión de distritos + `coverage_simplify` (tolerancia 0,003° ≈ 300 m: 6 MB, 1,5 MB comprimido; solo 12 municipios pierden >10 % de superficie, ninguno desaparece), Leaflet 1.9.4 desde cdnjs, sin mapa base. Buscador sin tildes, salto a provincia, ficha con resultados y ganadores 1996–2023. Solo funciona por HTTP (no abriendo index.html desde disco). Para regenerar: descargar distritos con `export_mapa.descargar_distritos` y `python -m pipeline.export_mapa <carpeta>`.
- **Cambios de municipios (importante para el modelo):** 5 municipios históricos sin polígono por fusión (Darrical 04039, Cesuras 15026 y Oza dos Ríos 15063 → Oza-Cesuras, Cerdedo 36011 y Cotobade 36012 → Cerdedo-Cotobade) y **1 municipio nuevo en 2026, Usansolo (48916), segregado de Galdakao**, sin historia propia: el 29N votará como unidad separada. Hay que asignarle un histórico (parte de Galdakao) o tratarlo como caso especial.
- **Mapa real (siguiente fase):** el INE publica la cartografía de secciones censales en shapefile (UTM huso 30), con licencia CC BY 4.0 (hay que citar al INE), y capas por año en su GeoServer (`https://www.ine.es/geoserver/ogc/features/v1/collections/WMS_INE_SECCIONES_G01:...`: vistas 2001, 2011 y una capa 2026; **no verificado** qué años existen). Plan por fases: (a) mapa municipal (~8.100 polígonos simplificados), (b) secciones de 2023/2026 cargadas por provincia, (c) para años antiguos solo municipal, porque los límites de sección cambian. La web v0 solo tiene nivel provincial; faltan los niveles municipio, sección y mesa (cargados bajo demanda por provincia).
- **Hallazgo de arquitectura:** en `tfm_web/motor/escenarios.py` los índices relativos por municipio (`rel_*`) NO dependen del resultado nacional elegido (las entradas del modelo son solo retardos y socioeconomía); el escenario solo multiplica `rel × objetivo` y reescala. Por tanto el simulador puede ser 100 % estático: precalcular `rel` por municipio una vez y hacer el resto en el navegador (JS), con d'Hondt en JS, sin servidor ni IA en producción.
- **Cartografía:** no hay ninguna en la carpeta del TFM (solo un mosaico de provincias). Hay que descargar límites municipales y de sección por año.

## Convocatoria del 29N y simulador (2026-11-15)
- **Escaños y candidaturas HECHO** (`pipeline/convocatoria_29n.py` → `data/web/29n/escanos.csv`, `candidaturas_congreso.csv`, `web/data/29n.json`). Fuente: BOE (público, accesible desde la nube): Real Decreto 806/2026 (BOE-A-2026-20742, anexo de diputados), candidaturas proclamadas (BOE-A-2026-23103, 3 de noviembre) y corrección de errores (BOE-A-2026-23383, 7 de noviembre). Copia de los XML en `..\datos\boe\` (se re-descargan solos).
- **Escaños:** solo cambian dos circunscripciones respecto a 2023: **Madrid 37 → 38 y Cádiz 9 → 8**.
- **534 candidaturas proclamadas al Congreso** (coincide con la cifra de prensa). En el XML del BOE el título de lista va en `<p class="centro_redonda">`; no se puede distinguir por el texto (en las coaliciones los candidatos llevan su partido entre paréntesis). Las listas seguidas de «No proclamada.» se descartan. La única corrección que afecta a una denominación del Congreso: Navarra, «EH BILDU-ERC» → «EH BILDU».
- **Mapa de candidaturas del 29N** (columna `espacio`, clasificación PROVISIONAL por reglas, a validar con Redacción): PP, PSOE y Vox en las 52; **UPN va en coalición con el PP** (Navarra, «UPN-PP»); **Se Acabó la Fiesta en 46**; el espacio de Sumar de 2023 concurre dividido: **Frente Amplio (FA) en 44** (con Comuns en Cataluña, CHA-IU-MS en Aragón, Aramés en Baleares), **Podemos en 41**, **Adelante Andalucía en las 8 andaluzas**, y listas conjuntas **Compromís-EUPV-Podem** (Alicante, Castellón, Valencia) y **NC-BC, Podemos, IU, Sumar** (Las Palmas, Santa Cruz de Tenerife). No se presentan la CUP ni UPL. Teruel Existe sí; Soria ¡Ya! también (va en OTROS).
- **Simulador de escaños HECHO** (`pipeline/simulador.py`, `web/simulador.js`, `web/data/simulador.json`): el usuario fija el % nacional de cada espacio; ajuste proporcional iterativo (IPF) sobre el perfil provincial de 2023 (columnas = total nacional, filas = votos válidos de 2023 de cada provincia) y d'Hondt con barrera. Es **provincial**, no usa el modelo municipal de Mikel (`rel`): para escaños basta la provincia. JS y Python dan el mismo reparto (test con node).
- **Visibilidad:** la pestaña «Simulador 29N» **solo aparece si la dirección lleva `?simulador`** (pendiente de Jurídico, LOREG 69.7). Solo funciona por HTTP.
- **Backtest del método** (`python -m pipeline.simulador`): con el resultado nacional REAL de cada elección repartido con el perfil de la anterior, **entre 4 y 13 de 350 escaños acaban en un partido distinto (mediana 6); un partido se desvía hasta 9 escaños**. Peor cuando irrumpen partidos nuevos: 2015 (13) y abril de 2019 (10), que es la situación del 29N. Ese es el error mínimo del simulador *aunque se acierte el voto nacional*. Limitación del backtest: `resultados.json` solo guarda candidaturas con ≥1 % o escaño por provincia.
- **Supuestos del punto de partida** (convenciones, no estimaciones): voto de 2023; el voto de Sumar se asigna a FA donde FA se presenta, y a la lista conjunta donde solo hay esa; Podemos, Adelante y SALF empiezan en 0; SALF se reparte con el mismo % en todas sus provincias (sin historia en generales; mejorable con las Europeas 2024); Vox **no concurrió en Santa Cruz de Tenerife en 2023** y se le supone allí su cuota media (62.467 votos). Con voto y mapa de 2023 el simulador reproduce el reparto oficial en 49 provincias; cambian Navarra, Las Palmas y Santa Cruz de Tenerife por esas tres razones.
- **Interior desde la nube:** `infoelectoral.interior.gob.es` responde 403 (desafío de Cloudflare) en las sesiones de Claude Code en la web, así que `pipeline.descargar_interior` no funciona ahí; BOE e INE sí. Los exportadores que leen los `.DAT` hay que ejecutarlos en el PC.

## Noche electoral del 29N: API de Interior y página en vivo (2026-11-15)
- **Manual de la API de descargas para medios** (Interior, PDF que aportó Nacho; no está en la repo). Ficheros CSV por GET, separador «;», campos de longitud fija, CR LF, porcentajes con dos decimales implícitos. Flujo: `/descargas/csv/data/getEnvio/2` (número de envío; 2 = Congreso, 3 = Senado) → `/descargas/csv/data/getEscrutinioTotales/2/{numEnv}` (España, comunidades y provincias) → `/descargas/csv/data/getEscrutinioMunicipios/2/{codPrv}/{numEnv}` (municipios y distritos de Barcelona, Bilbao, Madrid, Málaga, Sevilla, Valencia y Zaragoza). Avances: `getAvancesTotales/2/{numEnv}` y `getAvancesMunicipios/2/{codPrv}/{numEnv}`. Fijos: `/descargas/csv/fijos/getCandidaturas/2`, y de 2023 `.../fijos/getEscrutinioTotales/ANT/2/07-23`, `.../getEscrutinioMunicipios/ANT/2/{codPrv}/07-23`, `.../getCandidaturas/ANT/2/07-23`. Usar el mismo número de envío para totales y municipios.
- **Granularidad: municipio (y distrito en 7 ciudades). No hay mesa ni sección en vivo**, ni orden de llegada de mesas. El registro de totales trae además, por provincia: diputados a elegir, candidatura que se lleva el último escaño, la más próxima y los votos que le faltan.
- **Calendario del servicio:** simulacro el **miércoles 18 de noviembre** (15:00 constitución, 16:00 y 17:00 avances, 18:00 escrutinio). El 29N: avances a las 14:00 y 18:00, escrutinio desde las 20:00, publicación de resultados a las 21:00 (hora peninsular). Interior recomienda no desplegar el consumo en servicios cloud de capa gratuita.
- **No sabemos todavía:** el dominio del repositorio, el usuario y la clave (predefinidos por medio) ni el método de autenticación. `pipeline/escrutinio_29n.py --descargar` supone autenticación HTTP básica y variables `ELECCIONES_API_URL/_USER/_PASS`: **sin probar**.
- **Hecho:** `pipeline/escrutinio_29n.py` lee `getEscrutinioTotales` y escribe `web/data/vivo_29n.json` con la misma forma que una elección de `resultados.json` (más `escrutado`, `hora`, `ultimo`). La web añade «29 de noviembre de 2026» al desplegable (solo nivel España/provincias), con hemiciclo (fuera 2026, dentro 2023; el hemiciclo sale ahora en todas las convocatorias con la anterior dentro), % escrutado, participación y ▲▼ de escaños frente a 2023 donde hay continuidad (PP frente a PP + UPN; el espacio de Sumar no se compara). Se vuelve a pedir el fichero cada 30 s. Antes del escrutinio el fichero está vacío (`--vacio`). **`?demo` carga `demo_29n.json`: DATOS DE PRUEBA** (voto de 2023 pasado por el formato de la API), con rótulo visible.
- **Pendiente:** cómo llega `vivo_29n.json` a la web publicada cada pocos minutos (Netlify es estática: hace falta un proceso con las credenciales que descargue y publique, o una función); nivel municipal en vivo; mapear códigos de candidatura de la API con `getCandidaturas` (hoy se clasifica por siglas); mapa geográfico de provincias en lugar del mosaico; la proyección («anticiparnos al resultado»): con datos por municipio se puede comparar cada municipio escrutado con su 2023 y extrapolar al resto, pero **no hay registro horario del 23J para validarlo** salvo que se grabe el simulacro o alguien conserve los envíos de 2023.

## Web: mapa de provincias, hemiciclo y distritos (2026-11-15)
- **Mapa geográfico de provincias** en lugar del mosaico (`pipeline/export_provincias.py` → `web/data/provincias.js`, 67 KB, SVG ya proyectado; función `mapaProvincias` en `app.js`, compartida con el simulador). Sale de `municipios.geojson` (unión por provincia + `coverage_simplify` 0,012°). Canarias desplazada en un recuadro; Ceuta y Melilla son un punto. Necesita `shapely` (no está en `requirements.txt`, igual que para `export_mapa.py`).
- **Hemiciclo** a nivel España en todas las convocatorias (fuera la elegida, dentro la anterior), encima de los datos.
- **Nombres de distrito** en la vista de secciones (`DISTRITOS` en `secciones.js`): Madrid, Barcelona, Valencia, Sevilla y Bilbao. Verificado con el centro geográfico de cada distrito censal en la cartografía de 2019 y 2023 (no con una fuente oficial de nombres: el INE solo da el número). **Málaga y Zaragoza no**: su numeración censal no coincide con los distritos municipales (en Málaga los distritos censales 01, 03 y 05 tienen 2-3 secciones). La API de Interior trae el nombre de distrito de las 7 ciudades: usarla para confirmar y completar cuando haya credenciales.
- **Credenciales de la API de Interior:** llegan el martes 17 de noviembre (URL, usuario y contraseña). **No desplegar ni fusionar la rama hasta que Nacho lo diga.**

## Revisión del TFM de Mikel (2026-11-15)
- **En la repo:** `tfm/` (web `tfm_web`, scripts, cuadernos, clasificación de partidos y `tfm/db_tfm/db_municipios.parquet`, 81.179 filas municipio × elección). Falta `tfm/ine/` (no llegó a subirse). El informe del TFM (PDF, mayo de 2025) no está en la repo.
- **Cuadernos del informe (`ml.ipynb`, `sl.ipynb`, `KNN.ipynb`): no sirven para predecir.** La etiqueta «Candidatura Ganadora» es fija por año, escrita a mano en `scripts/18_ganadora.py` (quién gobernó: 2023 = PSOE), no el ganador de cada mesa; la partición es aleatoria entre mesas. El 96 % mide reconocer el año.
- **Modelo de la web (`tfm_web/motor/escenarios.py`): correcto y sin fuga.** Gradient boosting por partido sobre `rel` = % municipal / % nacional, con dos retardos, participación, tamaño, provincia e indicadores provinciales. Reproducido aquí: 82,2 % de municipios en 2023 (Mikel: 82,1 %).
- **Pero no mejora de forma clara a la referencia simple** «repetir el perfil relativo de la elección anterior y reescalar al nacional» (`pipeline/backtest_tfm.py`, validación hacia delante 2008–2023, 7 elecciones): en municipios acertados gana la referencia en 6 de 7 (2023: 83,3 % frente a 82,2 %); en error medio de PP y PSOE, en 5 de 7; en escaños mal asignados a nivel nacional gana el modelo en 5 de 7 por 1–4 escaños (2023: 5 frente a 7). Los indicadores provinciales del INE no aportan señal apreciable: casi todo está en los retardos. El «68,5 %» del LEEME es otra referencia más débil (repetir el ganador sin reescalar).
- Los errores absolutos de escaños de ese backtest están inflados por el mapeo de partidos de la tabla municipal (UPN, Amaiur 2011, etc. no tienen columna); la comparación entre los dos métodos sí es justa.

## Proyección de la noche electoral y su backtest (2026-11-16)
- **`pipeline/noche.py`** (`python -m pipeline.noche`, 1 min; tests en `tests/test_noche.py`). `proyectar()` recibe, por municipio, electores totales, electores ya escrutados, votos contados por espacio y una base (votos de la elección anterior ajustados al censo actual). Calcula la razón contado/esperado por espacio y la aplica a lo que falta, en cascada con encogimiento: España → provincia → provincia × tamaño de municipio (4 tramos: 1.000, 10.000 y 100.000 electores) → el propio municipio. Los espacios con menos del 2 % en la provincia en la base (nuevos o marginales) se proyectan con su porcentaje en lo contado. Es la función que usará la página en vivo: sus entradas son las de `getEscrutinioMunicipios` de Interior.
- **Backtest con recuentos SIMULADOS** (no existe registro del orden real de llegada): secciones censales de 2019a, 2019b y 2023 llegando bajo cinco supuestos (al azar, municipios pequeños primero, mesas pequeñas primero y dos adversos: secciones más de derechas o más de izquierdas primero), agregadas por municipio. Resultado en `data/web/29n/backtest_noche.json`. Escaños que difieren del reparto final, media de las tres elecciones (máximo entre paréntesis), recuento tal cual → proyección:

| % censo escrutado | 2 | 5 | 10 | 20 | 30 | 50 | 70 | 90 |
|---|---|---|---|---|---|---|---|---|
| supuestos normales | 12,8 (38) → 6,4 (13) | 9,6 → 4,4 (12) | 7,5 → 3,4 (8) | 5,8 → 2,7 (7) | 4,6 → 2,1 (6) | 2,7 → 1,5 (4) | 1,7 → 1,0 (3) | 0,9 → 0,6 (3) |
| supuestos adversos | 39,3 → 24,1 (41) | 30,4 → 18,9 (31) | 24,4 → 15,4 (25) | 18,7 → 11,3 (18) | 15,2 → 9,2 (14) | 9,9 → 6,3 (10) | 6,4 → 3,9 (8) | 2,9 → 2,2 (5) |

- Error en el porcentaje nacional de PP/PSOE con supuestos normales: de 2,2 puntos (recuento) a 0,65 (proyección) con el 2 %; 0,3 con el 10 %.
- **Límites:** (1) el orden real de llegada es desconocido; si dentro de cada municipio llegan antes las mesas de un signo político, la proyección solo corrige la mitad (fila «adversos»), porque Interior no da el dato por mesa; en las 7 ciudades con distritos se podría afinar. (2) Las secciones del backtest solo tienen las tres primeras candidaturas (el resto se reparte con el perfil municipal): subestima la variación dentro del municipio. (3) `FUERZA = 300` se eligió con estas mismas tres elecciones (apenas influye entre 30 y 1.000). (4) Sin CERA: el reparto de la noche puede cambiar después (Madrid 2023: sin CERA, PSOE 11 y PP 15; con CERA, 10 y 16). (5) Para el 29N la base es 2023 por municipio y hay candidaturas sin base (SALF, Podemos y Frente Amplio por separado): irán por porcentaje, como Vox en abril de 2019, que es el caso más parecido del backtest.
- **Lección del desarrollo:** encoger hacia el cambio medio de España es dañino (el cambio de voto difiere mucho entre provincias); el nivel que manda es la provincia. La tabla municipal del TFM (`tfm/db_tfm/db_municipios.parquet`) se usa para completar la base, porque `web/data/mun/` recorta al 1,5 %.

## Captura en vivo y proyección enganchada (2026-11-16)
- **`pipeline/escrutinio_29n.py`**: además de los totales, lee `getEscrutinioMunicipios` (341 campos: 21 fijos + 80 × código, siglas, votos, %; `distrito` = «99» para el municipio, otro valor para los distritos de las 7 ciudades). `Cliente` hace las peticiones (envío, totales, municipios, avances); la autenticación básica sigue siendo una suposición SIN PROBAR (`ELECCIONES_API_AUTH=ninguna` la desactiva).
- **`pipeline/captura_29n.py`** (para el PC que descargue): cada 60 s pregunta por el envío; si es nuevo, guarda los ficheros tal cual en `..\datos\29n_envios\envio_<n>_<fecha-hora>\` (totales, avances y 52 de municipios), reescribe `web/data/vivo_29n.json`, calcula la proyección (`proyeccion.json`, en la carpeta del envío, **no se publica**) y anota una línea en `registro.csv`. Opciones: `--simulacro` (rótulo en la web), `--publicar` (git commit + push del fichero de la web), `--una-vez`, `--repetir CARPETA` (reprocesa un envío guardado, sin red: sirve para validar la proyección después con lo grabado).
- **`pipeline/proyeccion_29n.py`**: base del 29N por municipio (2023 trasladado a las candidaturas de 2026 y al censo de `tab4`) + `noche.proyectar`. El voto de Sumar solo se hereda donde hay una única lista heredera en la provincia; donde compiten FA, Podemos y Adelante, ninguna tiene base y van por porcentaje, como SALF. Usansolo (48916) recibe el perfil medio de Bizkaia. Incluye el margen del backtest según el % escrutado.
- **Web:** `web/config.js` (`vivo`: de dónde se lee el recuento; `refresco`); rótulo «SIMULACRO» cuando el fichero lleva `simulacro: true`; el simulador muestra la fila «Otras candidaturas y voto en blanco», el total y avisos si no cuadra.
- **Probado solo con ficheros fabricados según el manual** (`tests/test_captura_29n.py` monta una noche ficticia de extremo a extremo). Falta la prueba contra el servicio real (martes 17) y el simulacro (miércoles 18).
- Pendiente: mapear candidaturas por código con `getCandidaturas` (hoy por siglas: revisar las que caigan en `_RESTO`); usar los distritos de las 7 ciudades en la proyección; `tab4` suma 315 electores menos que el total del INE (alguna fila sin leer; sin efecto apreciable).

## Simulacro de Interior del 18 de noviembre (2026-11-19)
- **Funcionó de extremo a extremo** desde el PC del trabajo: `python -m pipeline.captura_29n --simulacro --publicar` de 14:31 a 21:33. 131 envíos (uno cada ~3 min): del 1 al 61, constitución de mesas y avances (recuento a cero, no se publicó nada); del 63 al 130, escrutinio (36,9 % en el primero, 98,54 % al final). 65 publicaciones en GitHub → 65 despliegues de Netlify de ~5 s cada uno: asumible.
- **Servicio:** dominio `https://prensa.29neleccionesgenerales.es`, autenticación HTTP básica (`Www-Authenticate: Basic realm="descargas", charset="UTF-8"`), detrás de CloudFront. En PowerShell las variables se ponen con comillas simples. **El usuario y la clave no están en la repo ni deben estarlo** (quedaron pegados en una conversación: recomendado pedir a Interior que los cambien).
- **Formato real = manual.** Totales: 72 registros (TO + 19 CM + 52 PR), 422 campos más uno vacío por el «;» final. Municipios: 341 + 1. Los registros de municipio llevan la fecha sin hora (`...0000`). Las provincias traen candidatura del último escaño, la siguiente y los votos que le faltan (Madrid: último PP, siguiente Vox a 40.925 votos). Los códigos de candidatura son nacionales de 4 dígitos (0007 PP, 0001 PSOE, 0006 VOX, 0013 FA, 0003 SALF, 0012 PODEMOS…); `UPN-PP` (0067) va aparte del PP. Navarra figura como «EH BILDU-ERC» (no aplican la corrección del BOE).
- **Distritos de Madrid según Interior** (confirman la numeración usada en la web): 01 Centro … 08 Fuencarral-Pardo … 13 Puente-Vallecas … 18 Villa-Vallecas … 20 San Blas, 21 Barajas. Faltan por ver los de Barcelona, Bilbao, Málaga, Sevilla, Valencia y Zaragoza (ficheros de municipios 08, 48, 29, 41, 46 y 50).
- **Incidencias y arreglos:** (1) el envío 72 trajo los totales a cero con el recuento al 85 % y la página volvió a 0 % tres minutos → la captura ya no publica un recuento que retrocede. (2) Los ficheros de municipios pesan ~50 MB por envío sin comprimir (≈6,5 GB el simulacro, en OneDrive) → ahora se guardan en gzip. (3) «PAZ,CASA Y TRABAJO» (Podemos en Ceuta) caía en OTROS → regla añadida. (4) El envío 62 falló al bajar los totales y el 86 no se capturó: sin consecuencias.
- **La proyección no se pudo evaluar de verdad:** los datos del simulacro son sintéticos y el recuento ya estaba casi en el reparto final con el 37 %. La proyección dio PP 137 / PSOE 126 (el final) desde el segundo envío y se mantuvo, mientras el recuento osciló entre 135 y 137 para el PP hasta las 20:00; hubo un salto raro en el envío 75 (FA 30) sin explicar.
- **Añadido el 19-N con los ficheros que aportó Nacho:** (a) candidaturas oficiales de la API (`data/web/29n/candidaturas_api_2026.csv` y `_2023.csv`: código, agrupación, siglas, denominación); la clasificación va ahora por código (`escrutinio_29n.espacio_api`, vía agrupación) y solo cae a las siglas si el código es desconocido; ambos caminos coinciden en las 81 candidaturas. A nivel de provincia la API usa códigos propios (0041 PSC, 0046 PP en Cataluña, 0045 Comuns…). (b) La página enseña, antes del escrutinio, mesas constituidas y los dos avances de participación (`leer_avances`), y en cada provincia el último escaño (quién lo tiene, quién va detrás y cuántos votos le faltan). (c) Distritos según Interior de las 7 ciudades: confirman Madrid, Barcelona, Valencia, Sevilla y Bilbao, y dan los de Málaga y Zaragoza (ya en `secciones.js`; «Carret y Alamos» y «Ronda I.-Campan» se han desarrollado como «Carretería y Álamos» y «Ronda Intermedia-Campanillas»: interpretación propia). (d) Ficheros reales del simulacro como datos de prueba en `tests/datos/simulacro/`.
- **`?simulacro` en la web:** carga `web/data/simulacro_29n.json`, el último envío real del simulacro (98,54 % escrutado, datos ficticios, rotulado), para ver la página con recuento, último escaño incluido. Se regenera con `python -m pipeline.escrutinio_29n --simulacro-web`. En el recuento las candidaturas del mismo espacio van en una sola fila (PP + UPN-PP, EH Bildu + EH Bildu-ERC).
- **Clave de la API:** Nacho ha decidido no cambiarla. No está en la repo; no copiarla a ningún fichero.
- **Antes del 29N:** dejar `web/data/vivo_29n.json` vacío (`python -m pipeline.escrutinio_29n --vacio`, ya hecho el 19-N) y lanzar la captura SIN `--simulacro`.

## Calendario del 29N
- **28 de octubre de 2026**: candidaturas presentadas (BOE-A-2026-22607); **3 de noviembre**: proclamadas; 7 de noviembre: corrección. Recogido (ver sección anterior). Campaña: 13–27 de noviembre. Constitución de las Cámaras: 23 de diciembre.
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
