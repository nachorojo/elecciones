"""Cómo evolucionaron el recuento y la proyección a lo largo de una prueba (o de la noche del 29N).

La captura publica con cada envío `web/data/vivo_29n.json` (recuento de Interior) y `web/data/proyeccion_29n.json`
(estimación propia) en un commit «29N: envío N (...)». Este módulo recorre esos commits, así que funciona desde
cualquier copia de la repo, sin los ficheros brutos del PC.

    python -m pipeline.analisis_prueba                          # rama actual, todos los envíos publicados
    python -m pipeline.analisis_prueba origin/RAMA --desde 2026-11-25 --hasta 2026-11-26
    python -m pipeline.analisis_prueba --csv salida.csv

Para cada envío compara dos repartos de escaños con el REPARTO FINAL (el recuento del último envío del periodo):
el recuento tal cual y la proyección. La medida es «escaños mal asignados»: escaños que están en un espacio y en
el final acaban en otro (mitad de la suma de diferencias absolutas), a nivel nacional y sumando provincia a provincia.

Límites: (1) el «final» es el último envío capturado, no el escrutinio definitivo (ni incluye el CERA); (2) en los
simulacros de Interior los datos son ficticios: sirve para comprobar que todo funciona, no para medir la proyección.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys

from . import config as C

VIVO, PROY = "web/data/vivo_29n.json", "web/data/proyeccion_29n.json"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=C.REPO, capture_output=True, text=True, encoding="utf-8").stdout


def _json(commit: str, ruta: str) -> dict | None:
    try:
        return json.loads(_git("show", f"{commit}:{ruta}"))
    except ValueError:
        return None


def _por_espacio(ambito: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in ambito["partidos"]:
        if p["e"]:
            out[p["f"]] = out.get(p["f"], 0) + p["e"]
    return out


def mal(a: dict, b: dict) -> int:
    """Escaños de `a` que en `b` están en otro espacio."""
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b)) // 2


def envios(ref: str = "HEAD", desde: str | None = None, hasta: str | None = None) -> list[dict]:
    """Un registro por envío publicado con escrutinio, del más antiguo al más reciente."""
    args = ["log", ref, "--reverse", "--full-history", "--format=%H|%ad|%s", "--date=format:%Y-%m-%d %H:%M:%S",
            "--grep=^29N: envío"]
    if desde:
        args.append(f"--since={desde}")
    if hasta:
        args.append(f"--until={hasta}")
    out = []
    for linea in _git(*args, "--", VIVO).splitlines():
        commit, fecha, asunto = linea.split("|", 2)
        m = re.search(r"envío (\d+)", asunto)
        v = _json(commit, VIVO)
        if not m or not v or v["nacional"]["escrutado"] <= 0:
            continue
        r = {"commit": commit[:7], "publicado": fecha, "envio": m.group(1), "hora": v.get("hora", ""),
             "escrutado": v["nacional"]["escrutado"], "recuento": _por_espacio(v["nacional"]),
             "recuento_prov": {k: _por_espacio(a) for k, a in v["provincias"].items()},
             "pct": {p["f"]: round(100 * p["v"] / v["nacional"]["validos"], 2) for p in v["nacional"]["partidos"]
                     if p["f"] != "OTROS" and v["nacional"]["validos"]}}
        p = _json(commit, PROY)
        if p and p.get("envio") == r["envio"] and p.get("nacional", {}).get("escanos"):
            r |= {"proyeccion": {k: n for k, n in p["nacional"]["escanos"].items() if n},
                  "proyeccion_prov": {k: {e: n for e, n in a["escanos"].items() if n} for k, a in p["provincias"].items()},
                  "proyeccion_pct": p["nacional"]["pct"], "margen": p["margen"]["escanos_media"]}
        out.append(r)
    return out


def analizar(serie: list[dict]) -> list[dict]:
    """Añade a cada envío su distancia al reparto final (el recuento del último envío)."""
    if not serie:
        return []
    final, final_prov, final_pct = serie[-1]["recuento"], serie[-1]["recuento_prov"], serie[-1]["pct"]
    grandes = [e for e in ("PP", "PSOE") if e in final_pct]
    for r in serie:
        r["rec_mal"] = mal(r["recuento"], final)
        r["rec_mal_prov"] = sum(mal(a, final_prov.get(k, {})) for k, a in r["recuento_prov"].items())
        r["rec_err_pct"] = round(max((abs(r["pct"].get(e, 0) - final_pct[e]) for e in grandes), default=0), 2)
        if "proyeccion" in r:
            r["proy_mal"] = mal(r["proyeccion"], final)
            r["proy_mal_prov"] = sum(mal(a, final_prov.get(k, {})) for k, a in r["proyeccion_prov"].items())
            r["proy_err_pct"] = round(max((abs(r["proyeccion_pct"].get(e, 0) - final_pct[e]) for e in grandes), default=0), 2)
            r["dentro_margen"] = r["proy_mal"] <= r["margen"]
    return serie


def resumen(serie: list[dict]) -> str:
    if not serie:
        return "No hay envíos con escrutinio publicados en ese periodo."
    principales = sorted(serie[-1]["recuento"], key=lambda k: -serie[-1]["recuento"][k])[:4]
    cab = (f"{'envío':>5} {'hora':>5} {'escrut.':>8} | " + " ".join(f"{e[:5]:>5}" for e in principales) + " | "
           + " ".join(f"{e[:5]:>5}" for e in principales) + " | mal asignados (nac / por prov.)    error % PP-PSOE")
    lineas = [f"Reparto final de referencia (envío {serie[-1]['envio']}, {serie[-1]['escrutado']} % escrutado): {serie[-1]['recuento']}",
              f"{'':>21} | {'recuento':^{6 * len(principales) - 1}} | {'proyección':^{6 * len(principales) - 1}} | recuento  →  proyección", cab]
    for r in serie:
        rec = " ".join(f"{r['recuento'].get(e, 0):>5}" for e in principales)
        if "proyeccion" in r:
            pro = " ".join(f"{r['proyeccion'].get(e, 0):>5}" for e in principales)
            cmp = (f"{r['rec_mal']:>3} / {r['rec_mal_prov']:<3} → {r['proy_mal']:>3} / {r['proy_mal_prov']:<3}"
                   f" (margen ±{r['margen']}{'' if r['dentro_margen'] else ' SUPERADO'})   {r['rec_err_pct']:.2f} → {r['proy_err_pct']:.2f}")
        else:
            pro = " ".join(f"{'—':>5}" for _ in principales)
            cmp = f"{r['rec_mal']:>3} / {r['rec_mal_prov']:<3} →   sin proyección publicada           {r['rec_err_pct']:.2f}"
        lineas.append(f"{r['envio']:>5} {r['hora']:>5} {r['escrutado']:>7.2f}% | {rec} | {pro} | {cmp}")
    con = [r for r in serie if "proyeccion" in r]
    if con:
        gana = sum(r["proy_mal_prov"] < r["rec_mal_prov"] for r in con)
        pierde = sum(r["proy_mal_prov"] > r["rec_mal_prov"] for r in con)
        lineas.append(f"\nDe {len(con)} envíos con proyección: más cerca del final que el recuento en {gana}, más lejos en {pierde}, "
                      f"igual en {len(con) - gana - pierde}. Fuera del margen del backtest en {sum(not r['dentro_margen'] for r in con)}.")
        primero = next((r for i, r in enumerate(con) if all(x["proy_mal"] == 0 for x in con[i:])), None)
        primero_rec = next((r for i, r in enumerate(serie) if all(x["rec_mal"] == 0 for x in serie[i:])), None)
        lineas.append("Reparto nacional final clavado y ya sin moverse: proyección desde el "
                      + (f"{primero['escrutado']} % escrutado" if primero else "—") + "; recuento desde el "
                      + (f"{primero_rec['escrutado']} %." if primero_rec else "—."))
    return "\n".join(lineas)


def a_csv(serie: list[dict], salida: str) -> None:
    campos = ["envio", "publicado", "hora", "escrutado", "rec_mal", "rec_mal_prov", "rec_err_pct", "proy_mal",
              "proy_mal_prov", "proy_err_pct", "margen", "dentro_margen", "recuento", "proyeccion"]
    with open(salida, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for r in serie:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v for k, v in r.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ref", nargs="?", default="HEAD", help="rama o commit donde publica la captura (por defecto, HEAD)")
    ap.add_argument("--desde"), ap.add_argument("--hasta"), ap.add_argument("--csv")
    a = ap.parse_args()
    serie = analizar(envios(a.ref, a.desde, a.hasta))
    sys.stdout.reconfigure(encoding="utf-8")
    print(resumen(serie))
    if a.csv:
        a_csv(serie, a.csv)
