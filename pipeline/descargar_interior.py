"""Descarga los ficheros oficiales de mesa de las 10 elecciones al Congreso desde Infoelectoral (Interior).

    python -m pipeline.descargar_interior [carpeta_destino]

Destino por defecto: ..\\datos\\infoelectoral\\congreso\\02AAAAMM_MESA\\ (fuera de la repo). Cada zip trae los ficheros
01..10 de ancho fijo (.DAT) y FICHEROS.doc con el diseño de registro. ~54 MB en total. Idempotente.

Las direcciones son públicas (https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/02AAAAMM_MESA.zip);
la API que alimenta el listado de la página exige una credencial del navegador y NO se usa. Para otras convocatorias
(Senado 03, Municipales 04, Europeas 07) el patrón de nombre es el mismo con otro tipo, pero hay que localizar el
nombre exacto en la página (botón Consultar).
"""
from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path

from . import config as C
from .audit_interior import ELECCIONES

DESTINO = C.REPO.parent / "datos" / "infoelectoral" / "congreso"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"


def descargar(destino: Path = DESTINO) -> list[str]:
    hechos = []
    for per in ELECCIONES:
        nombre = f"02{per}_MESA"
        out = destino / nombre
        if out.exists() and any(out.glob("*.DAT")):
            continue
        url = f"https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/{nombre}.zip"
        datos = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180).read()
        out.mkdir(parents=True, exist_ok=True)
        z = out / f"{nombre}.zip"
        z.write_bytes(datos)
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():                       # evita rutas fuera de la carpeta
                t = (out / m).resolve()
                if out.resolve() not in t.parents and t != out.resolve():
                    raise SystemExit(f"ruta sospechosa en el zip: {m}")
            zf.extractall(out)
        hechos.append(nombre)
    return hechos


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO
    print("descargados:", descargar(d) or "nada (ya estaban todos)")
