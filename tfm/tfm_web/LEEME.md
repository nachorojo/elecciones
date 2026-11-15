# Atlas Electoral — web local del TFM

Consulta conversacional de las diez convocatorias al Congreso celebradas en España entre 1996 y
2023, sobre los datos de `db_tfm/` (573.617 mesas, 8.136 municipios).

## Arrancar

```bash
cd tfm_web
python3 app.py
```

Abre `http://127.0.0.1:7800`. Con `--entrenar-al-arrancar` el modelo de escenarios se entrena al
inicio (unos 20 s) en vez de la primera vez que abras esa pestaña.

Opciones: `--datos DIR` (por defecto `../db_tfm`), `--puerto N`, `--host`.

Dependencias: `flask`, `pandas`, `pyarrow`, `scikit-learn`, `numpy`. Todas ya instaladas.

## Activar el chat con modelo de lenguaje

La web **funciona sin modelo**: un intérprete de reglas entiende las preguntas y la respuesta se
compone con plantillas. Para tener chat libre de verdad:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
```

Arranca la web otra vez y la insignia de la esquina pasará de *sin modelo* a *modelo qwen2.5:7b*.
Con tu RTX 4060 de 8 GB el modelo cabe entero en la GPU y responde en dos o tres segundos.
Si prefieres algo más ligero, `ollama pull qwen2.5:3b`. Para forzar uno concreto:
`MODELO_OLLAMA=qwen2.5:3b python3 app.py`.

**Lo que hace y lo que no hace el modelo.** Interpreta la pregunta y redacta la respuesta.
No produce ni una sola cifra: todos los números se consultan en la base de datos antes de
pasárselos. El pie de cada respuesta indica si la redactó el modelo o una plantilla.

## Las cuatro pestañas

**Preguntar.** Chat. Entiende territorios (municipio, provincia, comunidad, España), las diez
convocatorias, los partidos y unas cuantas métricas, y mantiene el contexto entre preguntas
(puedes decir «¿y en Cuenca?»). Tipos de consulta: resultado, evolución, ranking, comparación y
detalle por mesa.

**Explorar.** Mapa de las 52 provincias en mosaico, coloreable por partido ganador, índice
izquierda-derecha o participación. Al pinchar una provincia se abre su ficha con resultados,
serie 1996-2023 y contexto socioeconómico. El buscador llega hasta cualquier municipio.

**Escenarios.** Fijas el resultado nacional de cada partido y el modelo reparte ese voto por el
territorio. **No predice el futuro**: reparte un resultado que tú le das.

**Validación.** El modelo entrenado solo con datos hasta noviembre de 2019 reparte el resultado
nacional de 2023 entre los 8.131 municipios, sin haber visto nunca el resultado municipal de ese
año. Acierta el partido más votado en el **82,1 %** de los municipios.

## Enlaces directos

- `?q=Quién ganó en Sevilla en 2011` lanza esa pregunta al cargar.
- `#explorar`, `#escenarios`, `#backtest` abren esa pestaña.

## Estructura

```
tfm_web/
├── app.py                 servidor Flask y API
├── motor/
│   ├── datos.py           carga del parquet y consultas agregadas
│   ├── entidades.py       catálogo de territorios, partidos y métricas
│   ├── consultas.py       detección de intención y ejecución
│   ├── llm.py             adaptador de Ollama
│   └── escenarios.py      modelo de reparto territorial y backtest
├── plantillas/index.html
└── static/                estilo.css, app.js
```

La interfaz habla con la API por HTTP y no tiene dependencias externas: ni CDN, ni ficheros de
geometría, ni fuentes remotas. Funciona sin conexión y se puede publicar moviendo `app.py` a un
servidor y apuntando el frontend a su dirección.

## API

| Ruta | Qué devuelve |
|---|---|
| `POST /api/chat` | `{pregunta, historial, contexto}` → respuesta, datos e intención |
| `GET /api/resultado?nivel=&codigo=&eleccion=` | Resultado completo de un territorio |
| `GET /api/evolucion?nivel=&codigo=` | Serie de las diez convocatorias |
| `GET /api/ranking?metrica=&eleccion=&nivel=&orden=` | Ranking de territorios |
| `GET /api/mapa?eleccion=&metrica=` | Datos del mapa provincial |
| `GET /api/mesas?mun_id=&eleccion=` | Detalle mesa a mesa de un municipio |
| `GET /api/buscar?q=` | Autocompletado de territorios |
| `POST /api/escenario` | Simulación del reparto territorial |
| `GET /api/backtest` | Métricas de validación |
