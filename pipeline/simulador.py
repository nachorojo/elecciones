"""Simulador de escaños: reparto territorial de un resultado nacional y backtest del método.

    python -m pipeline.simulador            # backtest 2000–2023 + exporta web/data/simulador.json

Idea (la misma que usa la web en JavaScript, `web/simulador.js`):
  1. Base: votos de la elección anterior por provincia y espacio político.
  2. El usuario fija el porcentaje NACIONAL de cada espacio.
  3. Ajuste proporcional iterativo (IPF / "raking"): se escalan las columnas (espacios) hasta su
     total nacional y las filas (provincias) hasta sus votos válidos, alternando hasta converger.
     Conserva el perfil territorial de cada espacio (dónde es fuerte y dónde débil).
  4. d'Hondt con barrera del 3 % por circunscripción (`pipeline.escanos.repartir`).

NO es un pronóstico: responde a "si el resultado nacional fuera este y cada espacio conservara su
perfil territorial, ¿qué reparto saldría?". El backtest mide cuánto se equivoca ese supuesto: se
toma el resultado nacional REAL de cada elección, se reparte con el perfil de la anterior y se
compara con los escaños oficiales.

Solo necesita `web/data/resultados.json` (ya en la repo): no hacen falta los ficheros de Interior.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import config as C
from .escanos import repartir

RESULTADOS = C.REPO / "web" / "data" / "resultados.json"
CONV = C.REPO / "data" / "web" / "29n"
SALIDA = C.REPO / "web" / "data" / "simulador.json"
RESTO = "_RESTO"  # blancos + candidaturas sin espacio propio: cuenta para la barrera, nunca recibe escaños

# Familia de 2023 (clasificación de Mikel en resultados.json) -> espacio de 2026 que hereda su perfil.
# "IZQ" es el voto de Sumar de 2023 (y socios): lo heredan, cada una donde se presenta, las listas
# FA, PODEMOS, ADELANTE, COMPROMIS y NC. Lo demás sin espacio propio va a RESTO.
HEREDA_2023 = {
    "PP": "PP", "UPN": "PP",  # 2026: UPN concurre en coalición con el PP en Navarra
    "PSOE": "PSOE", "VOX": "VOX", "ERC": "ERC", "CIU_JXCAT": "JUNTS", "EH_BILDU": "EH_BILDU", "PNV": "PNV",
    "BNG": "BNG", "CC": "CC", "GEROA_BAI": "GBAI",
    "PODEMOS_SUMAR": "IZQ", "COMPROMIS": "IZQ",  # COMPROMIS en 2023 = Sumar-Més en Baleares (así lo clasifica Mikel)
    "NUEVA_CANARIAS": "IZQ_NC",
}
HEREDEROS_IZQ = ("FA", "PODEMOS", "ADELANTE", "COMPROMIS", "NC")
ETIQUETAS = {
    "PP": "PP", "PSOE": "PSOE", "VOX": "Vox", "FA": "Frente Amplio", "PODEMOS": "Podemos",
    "SALF": "Se Acabó la Fiesta", "ERC": "ERC", "JUNTS": "Junts", "EH_BILDU": "EH Bildu", "PNV": "PNV",
    "BNG": "BNG", "CC": "Coalición Canaria", "COMPROMIS": "Compromís-EUPV-Podem", "NC": "NC-Podemos-IU-Sumar",
    "ADELANTE": "Adelante Andalucía", "TERUEL_EXISTE": "Teruel Existe", "GBAI": "Geroa Bai",
}
ORDEN = list(ETIQUETAS)


def cargar() -> list[dict]:
    return json.loads(RESULTADOS.read_text(encoding="utf-8"))["elecciones"]


def ajustar(base: dict[str, dict[str, float]], objetivo: dict[str, float], filas: dict[str, float],
            iteraciones: int = 200, tol: float = 1e-9) -> dict[str, dict[str, float]]:
    """IPF. `base[prov][esp]` >= 0; `objetivo[esp]` = votos nacionales; `filas[prov]` = votos válidos.

    Devuelve votos estimados por provincia y espacio. Los objetivos se reescalan para sumar lo
    mismo que las filas. Un espacio con objetivo > 0 y base nula en todas partes se ignora.
    """
    x = {p: {e: float(v) for e, v in fila.items() if v > 0 and objetivo.get(e, 0) > 0} for p, fila in base.items()}
    total = sum(filas.values())
    presentes = {e for fila in x.values() for e in fila}
    suma_obj = sum(objetivo[e] for e in presentes)
    obj = {e: objetivo[e] * total / suma_obj for e in presentes}
    for _ in range(iteraciones):
        col = {e: 0.0 for e in presentes}
        for fila in x.values():
            for e, v in fila.items():
                col[e] += v
        for fila in x.values():
            for e in fila:
                fila[e] *= obj[e] / col[e]
        error = 0.0
        for p, fila in x.items():
            s = sum(fila.values())
            if s > 0:
                k = filas[p] / s
                error = max(error, abs(k - 1))
                for e in fila:
                    fila[e] *= k
        if error < tol:
            break
    return x


def escanos(votos: dict[str, dict[str, float]], n_escanos: dict[str, int]) -> dict[str, dict[str, int]]:
    """d'Hondt por provincia. RESTO cuenta como votos válidos para la barrera y no recibe escaños."""
    out = {}
    for p, fila in votos.items():
        cand = {e: round(v) for e, v in fila.items() if e != RESTO}
        r = repartir(cand, n_escanos[p], blancos=round(fila.get(RESTO, 0)))
        out[p] = {e: s for e, s in r.escanos.items() if s}
    return out


def _por_familia(prov: dict) -> dict[str, int]:
    """Votos por familia en una provincia; lo no listado (y los blancos) va a RESTO."""
    out: dict[str, int] = {}
    for x in prov["partidos"]:
        out[x["f"]] = out.get(x["f"], 0) + x["v"]
    out[RESTO] = prov["validos"] - sum(out.values())
    return out


def _escanos_familia(prov: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in prov["partidos"]:
        if x["e"]:
            out[x["f"]] = out.get(x["f"], 0) + x["e"]
    return out


def backtest_par(antes: dict, despues: dict) -> dict:
    """Reparte el resultado nacional real de `despues` con el perfil territorial de `antes`."""
    real_v = {p: _por_familia(v) for p, v in despues["provincias"].items()}
    prev_v = {p: _por_familia(v) for p, v in antes["provincias"].items()}
    familias = {f for v in real_v.values() for f in v if f not in (RESTO, "OTROS")}
    # Cuota previa de cada familia en las provincias donde tiene historia: es lo que se le supone
    # donde se presenta sin historia. Si no tiene historia en ninguna, la misma cuota en todas.
    cuota, nuevas = {}, set()
    for f in familias:
        con = [p for p in real_v if f in real_v[p] and prev_v[p].get(f, 0) > 0]
        if con:
            cuota[f] = sum(prev_v[p][f] for p in con) / sum(antes["provincias"][p]["validos"] for p in con)
        else:
            cuota[f] = 1.0
            nuevas.add(f)
    base = {}
    for p, real in real_v.items():
        fila = {RESTO: float(prev_v[p][RESTO] + prev_v[p].get("OTROS", 0))}
        for f in familias:
            if f not in real:  # no se presentó (o no llegó al 1 %) en esta provincia
                continue
            fila[f] = float(prev_v[p].get(f, 0)) or cuota[f] * antes["provincias"][p]["validos"]
        base[p] = fila
    objetivo = {f: float(sum(v.get(f, 0) for v in real_v.values())) for f in familias}
    objetivo[RESTO] = float(sum(v[RESTO] + v.get("OTROS", 0) for v in real_v.values()))
    filas = {p: float(v["validos"]) for p, v in antes["provincias"].items()}
    est = ajustar(base, objetivo, filas)
    sim = escanos(est, {p: v["escanos_total"] for p, v in despues["provincias"].items()})
    real_e = {p: _escanos_familia(v) for p, v in despues["provincias"].items()}
    # Los escaños reales de familia "OTROS" no son simulables: cuentan como error.
    mal_prov = sum(sum(abs(sim[p].get(f, 0) - real_e[p].get(f, 0)) for f in set(sim[p]) | set(real_e[p])) // 2
                   for p in sim)
    tot_sim, tot_real = {}, {}
    for p in sim:
        for f, s in sim[p].items():
            tot_sim[f] = tot_sim.get(f, 0) + s
        for f, s in real_e[p].items():
            tot_real[f] = tot_real.get(f, 0) + s
    dif = {f: tot_sim.get(f, 0) - tot_real.get(f, 0) for f in set(tot_sim) | set(tot_real)}
    dif = {f: d for f, d in dif.items() if d}
    return {"de": antes["id"], "a": despues["id"], "escanos_mal_provincia": mal_prov,
            "provincias_exactas": sum(1 for p in sim if sim[p] == real_e[p]),
            "escanos_mal_nacional": sum(abs(d) for d in dif.values()) // 2,
            "max_error_partido": max((abs(d) for d in dif.values()), default=0),
            "dif": dict(sorted(dif.items(), key=lambda t: -abs(t[1]))), "sin_historia": sorted(nuevas)}


def backtest() -> list[dict]:
    el = cargar()
    return [backtest_par(a, b) for a, b in zip(el, el[1:])]


def base_29n() -> dict:
    """Base del simulador del 29N: votos de 2023 trasladados a los espacios de 2026 por provincia."""
    e23 = next(x for x in cargar() if x["id"] == "2023")
    with open(CONV / "escanos.csv", encoding="utf-8", newline="") as fh:
        n_escanos = {r["provincia"]: int(r["escanos_29n"]) for r in csv.DictReader(fh)}
    listas: dict[str, set[str]] = {}
    with open(CONV / "candidaturas_congreso.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            listas.setdefault(r["provincia"], set()).add(r["espacio"])
    provincias, e2023, sin_base = {}, {}, []
    for p, prov in sorted(e23["provincias"].items()):
        v23 = _por_familia(prov)
        her: dict[str, int] = {}
        for f, v in v23.items():
            if f in HEREDA_2023:
                her[HEREDA_2023[f]] = her.get(HEREDA_2023[f], 0) + v
        if p == "44":  # Teruel Existe (familia ESPANA_VACIADA; en Soria es otra lista, sin escaño)
            her["TERUEL_EXISTE"] = v23.get("ESPANA_VACIADA", 0)
        izq = her.pop("IZQ", 0)
        izq_nc = her.pop("IZQ_NC", 0)
        base = {}
        for esp in listas[p]:
            if esp in HEREDEROS_IZQ:
                base[esp] = izq + (izq_nc if esp == "NC" else 0)
            elif esp == "SALF":
                base[esp] = prov["validos"]  # sin historia en generales: mismo porcentaje en todas partes
            elif esp in her:
                base[esp] = her[esp]
        # Lista en 2026 de un espacio con historia nacional pero sin votos en esta provincia en 2023
        # (Vox no concurrió en Santa Cruz de Tenerife): se resuelve abajo con su cuota media.
        sin_base += [(p, e) for e in listas[p] if e in ETIQUETAS and e not in HEREDEROS_IZQ and e != "SALF"
                     and not her.get(e)]
        base = {e: v for e, v in base.items() if v > 0}
        for x in prov["partidos"]:
            if x["e"]:
                esp = "TERUEL_EXISTE" if x["f"] == "ESPANA_VACIADA" else HEREDA_2023.get(x["f"], RESTO)
                esp = "IZQ" if esp == "IZQ_NC" else esp
                e2023[esp] = e2023.get(esp, 0) + x["e"]
        provincias[p] = {"nombre": prov["nombre"], "escanos": n_escanos[p], "escanos_2023": prov["escanos_total"],
                         "validos": prov["validos"], "base": dict(sorted(base.items())),
                         "resto": prov["validos"] - sum(her.values()) - izq - izq_nc,
                         "v2023": {k: v for k, v in sorted(her.items())} | ({"IZQ": izq + izq_nc} if izq + izq_nc else {})}
    # Punto de partida: el voto de 2023 tal cual. El espacio de Sumar se asigna entero a la lista que
    # lo hereda donde solo hay una; donde hay varias, a FA (continuidad jurídica de la coalición), y
    # Podemos, Adelante y SALF empiezan en 0. Es una convención, no una estimación.
    inicio = {e: 0 for e in ORDEN}
    for p, d in provincias.items():
        v = d["v2023"]
        for esp in d["base"]:
            if esp in HEREDEROS_IZQ or esp == "SALF":
                continue
            inicio[esp] += v.get(esp, 0)
        her_izq = [e for e in HEREDEROS_IZQ if e in d["base"]]
        if her_izq:
            destino = "FA" if "FA" in her_izq else her_izq[0]
            inicio[destino] += v.get("IZQ", 0)
    for p, esp in sin_base:
        con = [d for d in provincias.values() if d["v2023"].get(esp)]
        cuota = sum(d["v2023"][esp] for d in con) / sum(d["validos"] for d in con)
        supuesto = round(cuota * provincias[p]["validos"])
        provincias[p]["base"][esp] = supuesto
        provincias[p]["base"] = dict(sorted(provincias[p]["base"].items()))
        inicio[esp] += supuesto
    validos = sum(d["validos"] for d in provincias.values())
    for d in provincias.values():
        del d["v2023"]
    return {"validos": validos, "escanos_2023": dict(sorted(e2023.items())),
            "sin_historia": [{"provincia": p, "espacio": e} for p, e in sin_base], "espacios": [{"id": e, "nombre": ETIQUETAS[e], "inicio": round(100 * inicio[e] / validos, 2),
                                             "provincias": sum(1 for d in provincias.values() if e in d["base"])}
                                            for e in ORDEN],
            "provincias": provincias}


def simular(datos: dict, pct: dict[str, float], escanos_de: str = "escanos") -> dict:
    """Reparto de un escenario: `pct[espacio]` = % nacional de votos válidos. Espejo de web/simulador.js."""
    validos = datos["validos"]
    objetivo = {e: validos * v / 100 for e, v in pct.items() if v > 0}
    resto = 100 - sum(pct.values())
    if resto > 0:
        objetivo[RESTO] = validos * resto / 100
    base = {p: dict(d["base"]) | {RESTO: d["resto"]} for p, d in datos["provincias"].items()}
    votos = ajustar(base, objetivo, {p: d["validos"] for p, d in datos["provincias"].items()})
    esc = escanos(votos, {p: d[escanos_de] for p, d in datos["provincias"].items()})
    total: dict[str, int] = {}
    for fila in esc.values():
        for e, n in fila.items():
            total[e] = total.get(e, 0) + n
    return {"votos": votos, "escanos": esc, "total": dict(sorted(total.items(), key=lambda t: -t[1]))}


def build(salida: Path = SALIDA) -> dict:
    bt = backtest()
    utiles = [r for r in bt if not r["sin_historia"] or r["a"] not in ("2015",)]
    out = base_29n()
    out["backtest"] = [{k: r[k] for k in ("de", "a", "escanos_mal_nacional", "escanos_mal_provincia",
                                         "max_error_partido", "provincias_exactas", "sin_historia")} for r in bt]
    out["nota"] = ("Backtest: resultado nacional real de cada elección repartido con el perfil territorial de la "
                   "anterior; error = escaños asignados a un partido distinto del real.")
    salida.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"backtest": bt, "utiles": utiles, "datos": out}


if __name__ == "__main__":
    r = build()
    for f in r["backtest"]:
        print(f"{f['de']:>5} → {f['a']:<5}  mal (nacional) {f['escanos_mal_nacional']:>2}  mal (por provincia) "
              f"{f['escanos_mal_provincia']:>2}  provincias exactas {f['provincias_exactas']:>2}/52  "
              f"máx. por partido {f['max_error_partido']}  {f['dif']}  sin historia: {f['sin_historia']}")
