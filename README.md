# Atlas Electoral — elecciones generales 1996–2023 (y 29N)

Web estática de resultados oficiales por provincia, municipio y sección censal, con motor de escaños d'Hondt validado.
Base de datos y trabajo previo: **Mikel Ibáñez González** (TFM, UAM). Resultados: Ministerio del Interior. Cartografía: INE (CC BY 4.0).

- Ver la web: `python -m http.server 8000 --directory web` → http://127.0.0.1:8000 (en Netlify: publica la carpeta `web`).
- **Para continuar el trabajo: [HANDOFF.md](HANDOFF.md)** y [CLAUDE.md](CLAUDE.md).
- Tests: `pip install -r requirements.txt && python -m pytest` (sin los datos locales, la mayoría se saltan).
