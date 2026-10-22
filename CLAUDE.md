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
12. `datos_oficiales` = N en 1996–2004 y S desde 2008. **Significado pendiente de confirmar.**
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
python -m pytest            # 41 tests; se saltan si no hay Parquet bruto
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

## Pendiente de decidir
- Dónde se publica: CMS de Onda Cero (embebido) o web independiente (dominio y propiedad de la URL).
- Significado de `datos_oficiales`.
