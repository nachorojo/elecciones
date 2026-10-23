# Traspaso del proyecto — Atlas Electoral (elecciones generales, 29N)

Escrito el 2026-10-23 para retomar el trabajo desde otro PC **solo con GitHub** y sin acceso a la conversación
original. Léelo entero antes de tocar nada; después lee `CLAUDE.md` (hallazgos y decisiones, más largo).

## 1. Qué es el proyecto
Web para ondacero.es con datos de las elecciones generales 1996–2023 y, más adelante, simulador/predictor para el
**29 de noviembre de 2026** (29N). Tres capas:
1. **Consulta histórica** con buscador y mapa (hecha en gran parte: provincias, municipios, secciones 2019 y 2023).
2. **Simulador de escenarios** con reparto de escaños (el motor de escaños d'Hondt está hecho y validado; falta el simulador).
3. **Noche electoral** (actualización continua tras las 20:00; sin empezar; depende de un flujo de datos en vivo).

**Créditos:** la base de datos y el trabajo previo son de **Mikel Ibáñez González** (hijo de Nacho; TFM, Universidad
Autónoma de Madrid, tutor David Domínguez). Debe figurar con todos los créditos en lo que se publique. Desarrollo:
Nacho Rojo con Claude. Cartografía: INE (CC BY 4.0, hay que citarlo). Resultados: Ministerio del Interior.

## 2. Qué hay en GitHub y qué NO (importante)
Repo: `github.com/nachorojo/elecciones`, rama `claude/blissful-dirac-j8h7p9` (es la rama de trabajo; `main` no se usa).

| En GitHub | NO está en GitHub (solo en el PC del trabajo, carpeta `Elecciones 2026\`) |
|---|---|
| Código (`pipeline/`, `web/`), tests, documentación | `datos\db_mesas.parquet` y los CSV de 1 GB (base de Mikel) |
| `web/data/**`: datos ya procesados que consume la web (≈75 MB) | `datos\infoelectoral\` (ficheros .DAT oficiales, 54 MB comprimidos) |
| `data/web/candidaturas_clasificadas_mikel.csv` (clasificación de partidos) | `datos\INE\Elecciones 2026\` (tablas del Censo Electoral) |
| | `datos\TFM\` (trabajo de Mikel completo, incluida su web `tfm_web`) |
| | Cartografía descargada del INE (se re-descarga) |

**Qué puedes hacer desde casa solo con GitHub:** editar la web (`web/*.html|js|css`), verla (`python -m http.server
--directory web` y abrir `http://127.0.0.1:8000`), desplegarla en Netlify, y tocar el código del pipeline. **Qué NO
puedes sin datos:** regenerar `web/data/` ni ejecutar la mayoría de los tests (se saltan solos si faltan los datos).
Para regenerar, recupera los datos como se explica en la sección 4.

## 3. Puesta en marcha en un PC nuevo
```bash
git clone https://github.com/nachorojo/elecciones.git repo
cd repo && git checkout claude/blissful-dirac-j8h7p9
python -m venv ~/venvs/elecciones          # FUERA de OneDrive (un .venv dentro se sincroniza con miles de ficheros)
~/venvs/elecciones/bin/pip install -r requirements.txt   # en Windows: ...\Scripts\pip.exe
python -m pytest                           # sin datos, la mayoría de tests se saltan: es normal
python -m http.server 8000 --directory web # ver la web
```
Clonar dentro de OneDrive es posible pero arriesgado (sincroniza `.git`). Si hay errores raros de git (`index.lock`),
pausa la sincronización de OneDrive. Haz push al terminar cada sesión.

## 4. Datos que faltan en un PC nuevo y cómo recuperarlos
- **Ficheros oficiales de Interior (los necesitan casi todos los exportadores):**
  `python -m pipeline.descargar_interior` → `..\datos\infoelectoral\congreso\02AAAAMM_MESA\` (10 elecciones, ~54 MB).
  Sin credenciales: las direcciones `…/estaticos/docxl/apliextr/02AAAAMM_MESA.zip` son públicas.
- **Cartografía del INE:** `pipeline/export_mapa.py` (`descargar_distritos`, `descargar_secciones`). Detalles en §6.
- **Base de Mikel (`db_mesas.parquet`, 109–130 MB):** solo hace falta para `pipeline.run` (Parquet limpio) y los tests de
  `test_problemas_conocidos.py`. **La web NO depende de ella** (usa los ficheros de Interior). Está en
  `datos\TFM\db_tfm\` y `datos\db_mesas.parquet` del PC del trabajo; no se puede subir a GitHub (límite de 100 MB por
  fichero). Variable `ELECCIONES_RAW` para cambiar su ruta.
- **Tablas del Censo Electoral del 29N:** `https://www.ine.es/oficina_censo/elecgen2026/Elecgral_2026_cc_tabN.xlsx`
  (N = 1…12; todas descargadas el 2026-10-23). Faltan por publicar: listas de votación definitivas, reclamaciones y voto
  por correo.

## 5. Mapa del repositorio
```
CLAUDE.md                    hallazgos, decisiones y avisos (LÉELO)
HANDOFF.md                   este documento
netlify.toml                 publish = "web", noindex
requirements.txt, pytest.ini
pipeline/
  config.py                  rutas y grupos de columnas (RAW, CLEAN_DIR)
  clean.py, dims.py, run.py  Parquet limpio de la base de Mikel: data/clean/ (ignorado por git)  [python -m pipeline.run]
  audit_interior.py          compara mesas.parquet con Interior mesa a mesa (573.617 idénticas)
  cera.py                    voto exterior (CERA) por provincia y candidatura → data/clean/
  escanos.py                 motor d'Hondt + backtest (520 repartos oficiales reproducidos)
  descargar_interior.py      baja los 10 zips de mesa de Interior
  export_web.py              web/data/resultados.{json,js}: España y provincias, escaños, CERA aparte
  export_municipios.py       web/data/mun/NN.json, partidos.json, indice.json: 8.136 municipios
  export_secciones.py        web/data/sec/NN.json, partidos_sec.json: secciones 2019a, 2019b, 2023
  export_mapa.py             descarga y simplifica cartografía INE → municipios.geojson y sec/g/AAAA/NN.geojson
web/                         sitio estático: index.html, estilo.css, app.js (provincias), municipios.js, secciones.js, data/
data/web/                    clasificación de candidaturas de Mikel (usada para colorear partidos)
tests/                       68+ tests (se saltan solos si faltan los datos)
```

## 6. Estado de la web (`web/`)
Tres vistas con el mismo selector de convocatoria:
- **Provincias:** mosaico de 52 casillas (no mapa geográfico), ficha con votos, %, escaños, CERA aparte, ganadores 1996–2023.
- **Municipios:** mapa real de 8.132 municipios (límites 2026 del INE), buscador sin tildes, ficha. Solo por HTTP.
- **Secciones (2019 abril, 2019 noviembre, 2023):** mapa por provincia cargado bajo demanda; modos "candidatura más
  votada" y "dónde cambió el ganador"; ficha con primer, segundo y tercer partido. Solo por HTTP.
Cifras: **oficiales de Interior**, % sobre votos válidos (candidaturas + blancos); participación = residentes (sin CERA).
No hay predicción en la web todavía (la insignia lo dice). El selector "colorear por participación" está **oculto**, no borrado.

**Cartografía INE** (API OGC del GeoServer `https://www.ine.es/geoserver/ogc/features/v1/collections/…`):
capas `WMS_INE_SECCIONES_G01:Secciones_AAAA` (2007–2025), `…Secciones_Censo_Poblacion_Viviendas_2001|2011` y la vigente
`…SU.VectorStatisticalUnit` (2026). Trampas aprendidas: (a) la paginación estándar `offset` se IGNORA, hay que usar
`startIndex`; (b) las secciones llevan `TIPO='SECCIONADO'` (no `SECCION`), filtrar con `CSEC<>'000'`; los distritos,
`TIPO='DISTRITO'`; (c) con desplazamientos grandes el servidor tarda 40 s por página: descargar **por provincia**
(`CUSEC LIKE 'NN%'`); (d) sin años 1996/2000/2004 a nivel de sección (solo hay 2001 censal).
Simplificación: municipios 0,003° (6 MB); secciones 0,0004° (≈36 MB por año). `shapely.coverage_simplify` conserva las
fronteras compartidas. Cada regeneración de geometrías añade ~36 MB por año a la historia de git: no la repitas sin motivo.

## 7. Decisiones tomadas (con Nacho)
- La web es **estática** (como Marcador, Cuadrante y KPIs): Netlify + datos precalculados, sin servidor ni IA en producción.
  El chatbot de Mikel (`datos\TFM\tfm_web`: Flask + Ollama) se reutiliza como diseño, pero no se despliega tal cual.
- **Cifras oficiales de Interior**, no las de la base de Mikel (que da PP 2023 = 33,33 % sobre candidaturas, con coaliciones
  asignadas al socio que encabeza las siglas y sin CERA; Interior: PP 8.160.837 votos, 33,06 % de válidos, 137 escaños).
- Predictor: escenario base de continuidad con intervalo ancho (no un pronóstico) + escenario del usuario ("el PSOE sube
  3 escaños, ¿qué pasa?"). Encuestas = entrada separada del "puro dato". Disclaimer con el error medido en el backtest.
- Hallazgo de arquitectura: en `tfm_web/motor/escenarios.py` los índices relativos por municipio no dependen del resultado
  nacional elegido (solo se multiplican y reescalan), así que el simulador puede ser **100 % estático en JavaScript**
  (precalcular `rel` por municipio una vez; d'Hondt en el navegador).
- Selector de participación fuera de la interfaz (Nacho: no lo entendía y no aportaba).
- La "calle" no existe en los datos de voto: la unidad mínima es la sección censal (las mesas se reparten por apellidos).
  Toda la web lo avisa.

## 8. Hallazgos sobre los datos (resumen; detalle en `CLAUDE.md`)
- La base de Mikel coincide con Interior en las 573.617 mesas (censo, votantes, candidaturas, avances). Su socioeconómica
  es **provincial** (comunitaria en internet y pobreza) y en 1996–2004 usa datos **posteriores** a la elección.
- `desfase_*` no tiene signo (solo |años|): en 2023 hay 1–2 años cuya dirección no se puede verificar.
- `datos_oficiales`: S = publicado por las Juntas Electorales; N = no oficial (1996–2004). `censo_cere` NO es el voto exterior:
  es el censo de extranjeros residentes (siempre 0 en Congreso). El voto exterior (CERA) no está en la base de Mikel pero sí en
  Interior (municipio 999): 203.254 votos (0,8 %) y 2,33 M de electores en 2023; se hunde en 2011 (voto rogado, sin verificar).
- Descuadre de bloques en 1996, 2000 y 2015 (fuente). Secciones con sufijo de letra en Zaragoza 1996–2004.
- Códigos de sección no comparables entre elecciones si el municipio cambia de distritos (Alcalá 8→5 en 2011).
- Municipios fusionados sin polígono: Darrical 04039, Cesuras 15026, Oza dos Ríos 15063, Cerdedo 36011, Cotobade 36012.
  **Municipio nuevo en 2026: Usansolo 48916** (segregado de Galdakao), sin historia propia.
- Defectos de la fuente de Interior (todos pequeños, documentados en tests): Toledo 2023 (municipios +175 votos sobre el
  provincial, sin explicar); censo de mesa ≠ censo municipal en 490/285 municipios en 2019 (Torres de Alcanadre 176 vs 88).
- Motor de escaños: d'Hondt con barrera del 3 % de **votos válidos** (candidaturas + blancos), inclusiva. Validado contra
  Interior; ningún sorteo en 10 elecciones (devuelve `empate=True` si lo hubiera).
- 2015: el CERA tiene ~600 candidaturas con códigos `9xxxxx` que no están en el fichero de candidaturas: sin siglas.

## 9. Pendiente (orden recomendado)
1. **Cerrar el nivel de sección:** comprobar que existe `web/data/sec/g/2019/` en la repo. Si no está (la vista de 2019 avisa de que faltan
   los límites), generarlo desde cualquier PC con internet (~30 min de descarga, sin necesidad de datos locales):
   `python -c "from pathlib import Path; from pipeline import export_mapa as M; d=Path('sec2019'); M.descargar_secciones(2019, d); print(M.construir_secciones(d, 2019))"`.
   Después probar en Netlify.
2. **Simulador de escenarios estático** con escaños: exportar `rel` por municipio desde el modelo de Mikel
   (`datos\TFM\tfm_web\motor\escenarios.py`), reescalar al resultado nacional elegido, agregar por provincia, d'Hondt en JS.
   Hay que estimar el CERA por provincia (mantener proporción de la última elección) y tratar Usansolo.
3. **Listas del 29N** (se publican el 28 de octubre): candidaturas por circunscripción y escaños por provincia.
4. Incorporar votos **posteriores a julio de 2023** (Europeas 2024, autonómicas) como señal de desplazamiento.
5. Mapear candidaturas a partidos/familias de forma única (mesas y CERA); validar con Redacción antes de publicar bloques.
6. Chatbot (reglas deterministas de Mikel portadas a JS; LLM opcional).
7. Noche electoral: ingestión en vivo (ver preguntas abiertas).
8. Más variables sociodemográficas por municipio/sección (ver §11).

## 10. Preguntas abiertas para Nacho
- ¿De dónde llegará el flujo de datos en vivo de la noche electoral y con qué granularidad? ¿Hay registros con hora del 23J 2023?
- **Jurídico:** LOREG art. 69.7 prohíbe difundir sondeos en los cinco días previos (desde el 24 de noviembre para el 29N). ¿Afecta
  a un simulador propio o alimentado con encuestas? Hasta saberlo, nada predictivo en abierto.
- URL de Netlify, dominio y si se incrusta en el CMS de ondacero.es (iframe) o es independiente. Contraseña/`noindex` actual.
- Guía de marca (tipografía y colores); hoy se usa la fuente del sistema.
- Acordar con Mikel la forma de crédito y qué se publica de su trabajo.

## 11. Fuentes
- **Interior (Infoelectoral):** https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/ — ficheros 01–10
  de ancho fijo; diseño en `FICHEROS.doc` (dentro de cada zip). Fichero 09 = mesas, 10 = votos por candidatura y mesa,
  05/06 = municipio, 07/08 = provincia/circunscripción (incluyen CERA), 03 = candidaturas.
- **INE, cartografía:** https://ine.es/dyngs/DAB/index.htm?cid=1389 y el GeoServer (arriba).
- **Censo Electoral 29N:** ver §4. tab4 = electores por municipio, tab11 = por provincia, sexo y edad.
- **Variables socioeconómicas de Mikel** (de su bitácora `datos\TFM\Prediccion-elecciones\pdf\llenarDB`): edad media
  t=3199; escolarización educ019.px; esperanza de vida t=1485; población t=2852; acceso a internet tpx=39494 (por
  comunidad); % mujeres 03002.px; inmigración 03005.px; pobreza t=9963 (por comunidad, desde 2008); paro t=3996 y t=5399;
  criminalidad t=49055; PIB `pr_cre.xlsx` (Contabilidad Regional). Todas **provinciales o autonómicas**. Lo que falta es
  renta por sección (Atlas de Distribución de Renta de los Hogares, desde 2015), Censo 2021 por sección y padrón por municipio.
- La tabla INE 56934 que bajó Nacho es **solo total nacional**: no sirve para completar la base.
- **Ley:** https://www.boe.es/buscar/act.php?id=BOE-A-1985-11672 (LOREG).

## 12. Trampas técnicas
- DuckDB 2.x: `con.execute(...).fetchone()`; las relaciones (`con.sql`) ya no tienen `fetchone`.
- Consola de Windows: los acentos salen como `�` aunque los datos estén bien (UTF-8). No es pérdida de datos.
- Ejecutar Python con `-I` ignora el directorio actual: usa `python -m pipeline.xxx` desde la raíz de la repo.
- `[hidden]` pierde frente a `display:flex`: el CSS lleva `[hidden]{display:none !important}`.
- Abrir `web/index.html` con doble clic funciona para provincias (datos en `resultados.js`), no para municipios ni secciones (fetch).
- Git avisa de LF→CRLF en Windows; es inofensivo.
- El panel del navegador de Claude muestra los ficheros locales como instantánea sin scripts: prueba siempre por HTTP.

## 13. Cómo retomar con Claude Code
Abre la carpeta de la repo y di, por ejemplo: «Lee HANDOFF.md y CLAUDE.md. Estado: revisa `git log` y dime qué quedó a medias.
Después continúa con el punto 2 de pendientes (simulador estático con escaños)». Pide siempre que haga commit y push al terminar.
