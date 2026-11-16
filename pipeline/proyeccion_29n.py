"""Proyección del resultado del 29N a partir del recuento por municipio de la API de Interior.

Une tres piezas: la base (votos de 2023 por municipio, trasladados a las candidaturas de 2026), el
censo del 29N por municipio (INE, tab4) y `pipeline.noche.proyectar`. La salida NO se publica en la
web: se guarda aparte (ver `pipeline.captura_29n`), hasta que se decida si se enseña.

Base, por municipio:
  - PP (+UPN), PSOE, Vox, ERC, Junts, EH Bildu, PNV, BNG, CC, Geroa Bai y Teruel Existe heredan su voto de 2023
    donde presentan lista.
  - El voto de Sumar de 2023 (y socios) pasa a la lista que lo hereda solo donde hay UNA heredera en la
    provincia (Comuns en Cataluña, Compromís-EUPV-Podem en la C. Valenciana, NC-Podemos-IU-Sumar en
    Canarias…). Donde compiten varias (Frente Amplio, Podemos, Adelante Andalucía) ninguna tiene base y se
    proyectan con el porcentaje que lleven en lo contado, igual que Se Acabó la Fiesta.
  - Lo demás (blancos, candidaturas menores, listas que ya no se presentan) va al resto.
  - Municipios sin datos de 2023 (Usansolo, segregado de Galdakao en 2026): perfil medio de su provincia.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from . import config as C
from . import noche as N
from .convocatoria_29n import espacio
from .simulador import HEREDA_2023, HEREDEROS_IZQ, ORDEN

CONV = C.REPO / "data" / "web" / "29n"
CENSO = C.REPO / "data" / "ine" / "censo_electoral_29n"
ESPACIOS = [N.RESTO] + ORDEN
COL = {e: i for i, e in enumerate(ESPACIOS)}


def censo_29n(carpeta: Path | None = None) -> dict[str, int]:
    """Electores residentes en España por municipio (tab4 del censo de consulta; la descarga más reciente)."""
    import openpyxl
    carpeta = carpeta or sorted(p for p in CENSO.iterdir() if p.is_dir())[-1]
    ws = openpyxl.load_workbook(carpeta / "Elecgral_2026_cc_tab4.xlsx", read_only=True).worksheets[0]
    out = {}
    for fila in ws.iter_rows(values_only=True):
        a, b = fila[0], fila[1]
        if isinstance(a, str) and isinstance(b, str) and a.isdigit() and b.isdigit() and len(a) == 2 and len(b) == 3:
            out[a + b] = int(fila[3])
    return out


def _listas() -> tuple[dict[str, set[str]], dict[str, int]]:
    listas: dict[str, set[str]] = {}
    with open(CONV / "candidaturas_congreso.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            listas.setdefault(r["provincia"], set()).add(r["espacio"])
    with open(CONV / "escanos.csv", encoding="utf-8", newline="") as fh:
        esc = {r["provincia"]: int(r["escanos_29n"]) for r in csv.DictReader(fh)}
    return listas, esc


def base_municipal() -> dict:
    """Matrices de la base del 29N: municipios (los del censo del INE), base, censo, provincia y tramo."""
    censo = censo_29n()
    listas, n_esc = _listas()
    fam = N._familias("2023")
    integros = N._votos_tfm(("2023",))
    provs = sorted(n_esc)
    muns = sorted(censo)
    fila_de = {m: i for i, m in enumerate(muns)}
    base = np.zeros((len(muns), len(ESPACIOS)))
    con_datos = np.zeros(len(muns), dtype=bool)
    for p in provs:
        mun = json.loads((N.WEB / "mun" / f"{p}.json").read_text(encoding="utf-8"))
        her_izq = [e for e in HEREDEROS_IZQ if e in listas[p]]
        for mid, m in mun.items():
            h = m["h"].get("2023")
            if not h or h[0] <= 0 or mid not in fila_de:
                continue
            votos: dict[str, float] = {}
            completo = integros.get(("2023", mid), {})
            for cod, n in h[5]:
                f = fam.get(cod, "OTROS")
                if f not in completo:
                    votos[f] = votos.get(f, 0) + n
            votos.update(completo)
            v = np.zeros(len(ESPACIOS))
            for f, n in votos.items():
                esp = "TERUEL_EXISTE" if (f == "ESPANA_VACIADA" and p == "44") else HEREDA_2023.get(f)
                if esp in ("IZQ", "IZQ_NC"):
                    esp = her_izq[0] if len(her_izq) == 1 else None
                if esp in COL and esp in listas[p]:
                    v[COL[esp]] += n
            v[0] = max(0.0, (h[4] + h[2]) - v[1:].sum())
            i = fila_de[mid]
            base[i] = v * (censo[mid] / h[0])
            con_datos[i] = True
    prov = np.array([provs.index(m[:2]) for m in muns])
    c = np.array([censo[m] for m in muns], dtype=float)
    # Municipios sin 2023: perfil de su provincia, a escala de su censo.
    for i in np.flatnonzero(~con_datos):
        igual = (prov == prov[i]) & con_datos
        base[i] = base[igual].sum(axis=0) * c[i] / c[igual].sum()
    return {"municipios": muns, "provincias": provs, "espacios": ESPACIOS, "base": base, "censo": c, "prov": prov,
            "tramo": np.searchsorted(N.TRAMOS, c, side="right"), "n_escanos": np.array([n_esc[p] for p in provs]),
            "sin_2023": [muns[i] for i in np.flatnonzero(~con_datos)]}


def margen(pct: float) -> dict:
    """Error de la proyección en el backtest (supuestos normales) para ese porcentaje de censo escrutado."""
    filas = json.loads((CONV / "backtest_noche.json").read_text(encoding="utf-8"))
    normales = [f for f in filas if f["modelo"] in N.MODELOS[:3]]
    puntos = sorted({f["escrutado"] for f in normales})
    media = [float(np.mean([f["proyeccion_media"] for f in normales if f["escrutado"] == p])) for p in puntos]
    maximo = [max(f["proyeccion_max"] for f in normales if f["escrutado"] == p) for p in puntos]
    return {"escanos_media": round(float(np.interp(pct, puntos, media)), 1),
            "escanos_max": int(np.ceil(np.interp(pct, puntos, maximo))),
            "nota": "Escaños que difirieron del reparto final en el backtest con recuentos simulados (2019 y 2023)."}


def proyectar_registros(registros: list[dict], b: dict | None = None) -> dict:
    """`registros`: salida de `escrutinio_29n.leer_municipios` de todas las provincias (se ignoran los distritos)."""
    b = b or base_municipal()
    fila_de = {m: i for i, m in enumerate(b["municipios"])}
    contado = np.zeros_like(b["base"])
    censo = b["censo"].copy()
    cc = np.zeros(len(censo))
    desconocidos = []
    for r in registros:
        if r["distrito"] != "99":
            continue
        i = fila_de.get(r["id"])
        if i is None:
            desconocidos.append(r["id"])
            continue
        if r["censo"] > 0:
            censo[i] = r["censo"]            # el censo de las mesas que da Interior manda sobre el del INE
        cc[i] = r["censo_escrutado"]
        for p in r["partidos"]:
            contado[i, COL.get(espacio("", p["s"]), 0)] += p["v"]
        contado[i, 0] += r["blancos"]
    base = b["base"] * (censo / b["censo"])[:, None]
    y = N.proyectar(base, censo, cc, contado, b["prov"], b["tramo"])
    np_ = len(b["provincias"])
    votos = np.zeros((np_, len(ESPACIOS))); rec = np.zeros_like(votos)
    np.add.at(votos, b["prov"], y); np.add.at(rec, b["prov"], contado)
    esc = N.escanos(votos, b["n_escanos"])
    pct = 100 * cc.sum() / censo.sum()

    def ambito(v, e):
        orden = sorted(range(1, len(ESPACIOS)), key=lambda k: (-e[k], -v[k]))
        return {"escanos": {ESPACIOS[k]: int(e[k]) for k in orden if e[k] > 0},
                "pct": {ESPACIOS[k]: round(100 * v[k] / v.sum(), 2) for k in orden if v[k] > 0.005 * v.sum()}}

    return {"escrutado": round(float(pct), 2), "margen": margen(pct), "nacional": ambito(votos.sum(axis=0), esc.sum(axis=0)),
            "provincias": {p: ambito(votos[i], esc[i]) for i, p in enumerate(b["provincias"])},
            "municipios_con_recuento": int((cc > 0).sum()), "municipios_desconocidos": sorted(set(desconocidos)),
            "aviso": "Estimación propia a partir del recuento parcial. No es un dato oficial."}


if __name__ == "__main__":
    b = base_municipal()
    tot = b["base"].sum(axis=0)
    print(len(b["municipios"]), "municipios;", int(b["censo"].sum()), "electores; sin datos de 2023:", b["sin_2023"])
    print({e: round(100 * v / tot.sum(), 2) for e, v in zip(ESPACIOS, tot) if v})
