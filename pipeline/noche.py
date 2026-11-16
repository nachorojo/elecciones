"""Noche electoral: proyección del resultado final a partir de un recuento parcial, y su backtest.

    python -m pipeline.noche                 # reconstruye las noches de 2019 (abril y noviembre) y 2023

PROYECCIÓN (`proyectar`). Entrada, por municipio: electores totales (conocidos de antemano), electores
ya escrutados y votos contados por espacio político; y una BASE: los votos de la elección anterior.
Para cada espacio se calcula cuánto ha cambiado respecto a la base en lo ya contado (razón
contado / esperado) y se aplica esa razón a lo que falta. La razón se estima en cascada, cada nivel
"encogido" hacia el anterior según cuánto voto lleve contado: España -> provincia -> provincia y
tamaño de municipio -> el propio municipio. Así, un municipio a medio contar se extrapola sobre todo
con su propio cambio, y uno sin contar, con el de los municipios parecidos de su provincia.
Los espacios sin base (partidos nuevos) se proyectan con su porcentaje en lo contado.

BACKTEST. No hay registro de cómo llegó el recuento el 23J (ni mesa ni hora), así que se SIMULA el
orden de llegada de las secciones censales bajo varios supuestos (al azar, municipios pequeños
primero, mesas pequeñas primero, y dos casos adversos: llegan antes las secciones más de derechas o
más de izquierdas). El recuento parcial se agrega por municipio, que es lo que da la API de Interior.
Se mide, con distintos porcentajes de censo escrutado, cuántos escaños difieren del reparto final
(a) si se reparte tal cual lo contado y (b) con la proyección.

Datos: web/data/mun/NN.json (municipio, candidaturas con >= 1,5 %), completado con los votos íntegros
de las 14 familias de tfm/db_tfm/db_municipios.parquet (sin ese recorte), y web/data/sec/NN.json
(sección, tres primeras candidaturas; el resto del voto de la sección se reparte con el perfil del
municipio y se ajusta para que cada municipio sume su total). No incluye el voto exterior (CERA),
que tampoco se cuenta la noche electoral.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import config as C

WEB = C.REPO / "web" / "data"
RESTO = "_RESTO"          # blancos + candidaturas menores: cuenta para la barrera, no recibe escaños
TRAMOS = (1_000, 10_000, 100_000)     # electores: 4 tamaños de municipio
PUNTOS = (2, 5, 10, 20, 30, 50, 70, 90)
MODELOS = ("azar", "municipios pequeños primero", "mesas pequeñas primero", "derecha primero", "izquierda primero")
PREVIA = {"2019a": "2016", "2019b": "2019a", "2023": "2019b"}
FUERZA = 300.0            # votos esperados a partir de los cuales un nivel pesa tanto como el nivel superior (elegido por backtest)
BASE_MINIMA = 0.02        # un espacio con menos de este peso en la provincia en la elección anterior se trata como nuevo
TFM = C.REPO / "tfm" / "db_tfm" / "db_municipios.parquet"
FAMILIAS_TFM = ("PP", "PSOE", "VOX", "PODEMOS_SUMAR", "CS", "IU", "UPYD", "ERC", "CIU_JXCAT", "PNV", "EH_BILDU", "BNG",
                "CC", "COMPROMIS")


# ----------------------------------------------------------------------------- reparto

def dhondt(votos: np.ndarray, n: int, validos: float, umbral: float = 0.03) -> np.ndarray:
    """Escaños por columna. `votos`: vector de candidaturas (sin RESTO); `validos`: total de votos válidos."""
    v = np.where(votos >= umbral * validos, votos, 0.0)
    out = np.zeros(len(v), dtype=int)
    if n <= 0 or v.sum() <= 0:
        return out
    coc = v[:, None] / np.arange(1, n + 1)[None, :]
    idx = np.argsort(-coc, axis=None, kind="stable")[:n]
    np.add.at(out, idx // n, 1)
    return out


def escanos(votos_prov: np.ndarray, n_escanos: np.ndarray) -> np.ndarray:
    """`votos_prov`: provincias × espacios, con RESTO en la columna 0."""
    return np.array([np.concatenate(([0], dhondt(f[1:], int(n), float(f.sum())))) for f, n in zip(votos_prov, n_escanos)])


# ----------------------------------------------------------------------------- proyección

def proyectar(base: np.ndarray, censo: np.ndarray, censo_contado: np.ndarray, contado: np.ndarray,
              prov: np.ndarray, tramo: np.ndarray, fuerza: float = FUERZA, estratos: bool = True) -> np.ndarray:
    """Votos finales estimados por municipio y espacio.

    base[m, k]      votos de la elección anterior, ya ajustados al censo actual del municipio
    censo[m]        electores del municipio; censo_contado[m]: electores de las mesas ya escrutadas
    contado[m, k]   votos contados hasta ahora
    prov[m], tramo[m]  índices de provincia y de tamaño de municipio
    """
    f = np.divide(censo_contado, censo, out=np.zeros_like(censo, dtype=float), where=censo > 0).clip(0, 1)
    # Espacios sin base suficiente en la provincia (nuevos o antes marginales): multiplicar una base casi
    # nula es inestable, así que su "base" pasa a ser el voto válido anterior total del municipio, es
    # decir, se proyectan con el porcentaje que llevan en lo contado.
    n_prov = int(prov.max()) + 1
    base_prov = np.zeros((n_prov, base.shape[1]))
    np.add.at(base_prov, prov, base)
    debil = base_prov <= BASE_MINIMA * base_prov.sum(axis=1, keepdims=True)
    total_base = base.sum(axis=1, keepdims=True)
    base = np.where(debil[prov], total_base, base)
    esperado = base * f[:, None]

    def razon(grupo: np.ndarray, n: int, padre: np.ndarray) -> np.ndarray:
        x = np.zeros((n, base.shape[1])); e = np.zeros_like(x)
        np.add.at(x, grupo, contado); np.add.at(e, grupo, esperado)
        return (x + fuerza * padre) / (e + fuerza)

    # Nivel superior: la razón de toda España, calculada por separado para las provincias donde el espacio
    # tiene base propia y para aquellas donde se proyecta por porcentaje (no son magnitudes comparables).
    x_prov = np.zeros((n_prov, base.shape[1])); e_prov = np.zeros_like(x_prov)
    np.add.at(x_prov, prov, contado); np.add.at(e_prov, prov, esperado)
    r_propia = ((x_prov * ~debil).sum(axis=0) + 1.0) / ((e_prov * ~debil).sum(axis=0) + 1.0)
    r_cuota = ((x_prov * debil).sum(axis=0) + 1e-9) / ((e_prov * debil).sum(axis=0) + 1.0)
    r_prov = razon(prov, n_prov, np.where(debil, r_cuota, r_propia))
    if estratos:
        g = prov * (len(TRAMOS) + 1) + tramo
        ng = n_prov * (len(TRAMOS) + 1)
        r_est = razon(g, ng, np.repeat(r_prov, len(TRAMOS) + 1, axis=0))[g]
    else:
        r_est = r_prov[prov]
    r_mun = (contado + fuerza * r_est) / (esperado + fuerza)
    return contado + (1 - f)[:, None] * base * r_mun


# ----------------------------------------------------------------------------- datos

def _familias(eleccion: str) -> dict[str, str]:
    p = json.loads((WEB / "partidos.json").read_text(encoding="utf-8"))[eleccion]
    ps = json.loads((WEB / "partidos_sec.json").read_text(encoding="utf-8")).get(eleccion, {})
    return {c: v[1] for c, v in (ps | p).items()}


def _votos_tfm(elecciones: tuple[str, ...]) -> dict[tuple[str, str], dict[str, int]]:
    """Votos íntegros por municipio de las 14 familias con columna propia en la tabla del TFM (si está)."""
    if not TFM.exists():
        return {}
    import pandas as pd
    t = pd.read_parquet(TFM, columns=["eleccion", "prov_cod", "mun_cod"] + [f"votos_{f.lower()}" for f in FAMILIAS_TFM])
    t = t[t["eleccion"].isin(elecciones)]
    ids = (t["prov_cod"] + t["mun_cod"]).to_numpy()
    v = t[[f"votos_{f.lower()}" for f in FAMILIAS_TFM]].to_numpy()
    return {(e, m): {f: int(n) for f, n in zip(FAMILIAS_TFM, fila) if n > 0}
            for e, m, fila in zip(t["eleccion"].to_numpy(), ids, v)}


def cargar(eleccion: str) -> dict:
    """Matrices de la elección `eleccion` (final por municipio y por sección) y de su anterior (base)."""
    previa = PREVIA[eleccion]
    fam_a, fam_p = _familias(eleccion), _familias(previa)
    res = {e["id"]: e for e in json.loads((WEB / "resultados.json").read_text(encoding="utf-8"))["elecciones"]}
    espacios = [RESTO] + sorted({f for f in list(fam_a.values()) + list(fam_p.values()) if f != "OTROS"})
    col = {f: i for i, f in enumerate(espacios)}
    provs = sorted(res[eleccion]["provincias"])
    muns, fin, bas, censo, prov, sec_mun, sec_censo, sec_v = [], [], [], [], [], [], [], []
    integros = _votos_tfm((eleccion, previa))

    def vector(h, fam, mid, el):
        v = np.zeros(len(espacios))
        completo = integros.get((el, mid))
        for cod, n in h[5]:
            f = fam.get(cod, "OTROS")
            if not (completo and f in completo):
                v[col.get(f, 0)] += n
        for f, n in (completo or {}).items():
            if f in col:
                v[col[f]] = n
        v[0] = max(0.0, (h[4] + h[2]) - v[1:].sum())        # resto de candidaturas + blancos
        return v

    for ip, p in enumerate(provs):
        mun = json.loads((WEB / "mun" / f"{p}.json").read_text(encoding="utf-8"))
        sec = json.loads((WEB / "sec" / f"{p}.json").read_text(encoding="utf-8"))
        por_mun: dict[str, list] = {}
        for s, d in sec.items():
            if eleccion in d:
                por_mun.setdefault(s[:5], []).append(d[eleccion])
        for mid, m in mun.items():
            h = m["h"].get(eleccion)
            if not h or h[0] <= 0:
                continue
            t = vector(h, fam_a, mid, eleccion)
            hp = m["h"].get(previa)
            b = vector(hp, fam_p, mid, previa) * (h[0] / hp[0]) if hp and hp[0] > 0 else np.zeros(len(espacios))
            i = len(muns)
            muns.append(mid); fin.append(t); bas.append(b); censo.append(h[0]); prov.append(ip)
            ss = por_mun.get(mid) or [h[:5] + [[]]]
            vs = np.zeros((len(ss), len(espacios)))
            for j, d in enumerate(ss):
                top = np.zeros(len(espacios))
                for cod, n in d[5]:
                    top[col.get(fam_a.get(cod, "OTROS"), 0)] += n
                resto = max(0.0, (d[4] + d[2]) - top.sum())
                w = np.where(top > 0, 0.0, t)
                vs[j] = top + (resto * w / w.sum() if w.sum() > 0 else 0)
            suma = vs.sum(axis=0)
            c = np.array([d[0] for d in ss], dtype=float)
            # Ajuste: cada espacio suma en el municipio su total oficial.
            vs = np.where(suma > 0, vs * (t / np.where(suma > 0, suma, 1)), np.outer(c / c.sum(), t))
            sec_mun += [i] * len(ss); sec_censo += list(c * h[0] / c.sum()); sec_v.append(vs)
    censo = np.array(censo, dtype=float)
    return {"eleccion": eleccion, "previa": previa, "espacios": espacios, "provincias": provs, "municipios": muns,
            "final": np.array(fin), "base": np.array(bas), "censo": censo, "prov": np.array(prov),
            "tramo": np.searchsorted(TRAMOS, censo, side="right"),
            "n_escanos": np.array([res[eleccion]["provincias"][p]["escanos_total"] for p in provs]),
            "sec_mun": np.array(sec_mun), "sec_censo": np.array(sec_censo), "sec_votos": np.vstack(sec_v)}


# ----------------------------------------------------------------------------- simulación del recuento

def orden_de_llegada(d: dict, modelo: str, rng: np.random.Generator) -> np.ndarray:
    """Índices de las secciones en el orden en que se supone que llegan."""
    n = len(d["sec_mun"])
    ruido = rng.standard_normal(n)
    z = lambda x: (x - x.mean()) / (x.std() or 1)
    if modelo == "azar":
        nota = ruido
    elif modelo == "municipios pequeños primero":
        nota = 0.8 * z(np.log10(d["censo"][d["sec_mun"]])) + 0.6 * ruido
    elif modelo == "mesas pequeñas primero":
        c = d["sec_censo"]
        nota = 0.6 * z(c / np.ceil(c / 800)) + 0.8 * ruido
    else:
        e = d["espacios"]
        der = d["sec_votos"][:, [e.index(k) for k in ("PP", "VOX") if k in e]].sum(axis=1)
        cuota = der / np.maximum(d["sec_votos"].sum(axis=1), 1)
        nota = (-0.5 if modelo == "derecha primero" else 0.5) * z(cuota) + 0.87 * ruido
    return np.argsort(nota, kind="stable")


def estado(d: dict, orden: np.ndarray, pct: float) -> tuple[np.ndarray, np.ndarray]:
    """Recuento por municipio cuando va escrutado el `pct` % del censo: (censo_contado, votos contados)."""
    acum = np.cumsum(d["sec_censo"][orden])
    dentro = orden[: int(np.searchsorted(acum, acum[-1] * pct / 100, side="right"))]
    m = len(d["censo"])
    cc = np.bincount(d["sec_mun"][dentro], weights=d["sec_censo"][dentro], minlength=m)
    v = np.zeros((m, len(d["espacios"])))
    np.add.at(v, d["sec_mun"][dentro], d["sec_votos"][dentro])
    return cc, v


def _por_provincia(d: dict, votos_mun: np.ndarray) -> np.ndarray:
    out = np.zeros((len(d["provincias"]), votos_mun.shape[1]))
    np.add.at(out, d["prov"], votos_mun)
    return out


def backtest(eleccion: str, repeticiones: int = 12, semilla: int = 29) -> list[dict]:
    d = cargar(eleccion)
    real = escanos(_por_provincia(d, d["final"]), d["n_escanos"])
    cuota_real = d["final"].sum(axis=0) / d["final"].sum()
    grandes = [d["espacios"].index(k) for k in ("PP", "PSOE") if k in d["espacios"]]
    filas = []
    for modelo in MODELOS:
        rng = np.random.default_rng(semilla)
        acum = {p: {"recuento": [], "proyeccion": [], "sin_estratos": [], "cuota_rec": [], "cuota_proy": []} for p in PUNTOS}
        for _ in range(repeticiones):
            orden = orden_de_llegada(d, modelo, rng)
            for p in PUNTOS:
                cc, v = estado(d, orden, p)
                mal = lambda e: int(np.abs(e.sum(axis=0) - real.sum(axis=0)).sum() // 2)
                acum[p]["recuento"].append(mal(escanos(_por_provincia(d, v), d["n_escanos"])))
                for nombre, est in (("proyeccion", True), ("sin_estratos", False)):
                    y = proyectar(d["base"], d["censo"], cc, v, d["prov"], d["tramo"], estratos=est)
                    acum[p][nombre].append(mal(escanos(_por_provincia(d, y), d["n_escanos"])))
                    if est:
                        acum[p]["cuota_proy"].append(100 * np.abs(y.sum(axis=0) / y.sum() - cuota_real)[grandes].max())
                acum[p]["cuota_rec"].append(100 * np.abs(v.sum(axis=0) / v.sum() - cuota_real)[grandes].max())
        for p in PUNTOS:
            a = acum[p]
            filas.append({"eleccion": eleccion, "modelo": modelo, "escrutado": p,
                          "recuento_media": round(float(np.mean(a["recuento"])), 1), "recuento_max": int(max(a["recuento"])),
                          "proyeccion_media": round(float(np.mean(a["proyeccion"])), 1), "proyeccion_max": int(max(a["proyeccion"])),
                          "sin_estratos_media": round(float(np.mean(a["sin_estratos"])), 1),
                          "error_pp_psoe_recuento": round(float(np.mean(a["cuota_rec"])), 2),
                          "error_pp_psoe_proyeccion": round(float(np.mean(a["cuota_proy"])), 2)})
    return filas


def main() -> None:
    todo = []
    for el in ("2019a", "2019b", "2023"):
        filas = backtest(el)
        todo += filas
        print(f"\n== {el} (base: {PREVIA[el]}) · escaños que difieren del reparto final: recuento tal cual → proyección (media; máx.)")
        print("   % escrutado".ljust(34) + "".join(f"{p:>13}" for p in PUNTOS))
        for modelo in MODELOS:
            f = [x for x in filas if x["modelo"] == modelo]
            print(f"   {modelo:<31}" + "".join(f"{x['recuento_media']:>6.1f}→{x['proyeccion_media']:<4.1f}{x['proyeccion_max']:>2}" for x in f))
    salida = C.REPO / "data" / "web" / "29n" / "backtest_noche.json"
    salida.write_text(json.dumps(todo, ensure_ascii=False, indent=0), encoding="utf-8")
    print("\n", salida)


if __name__ == "__main__":
    main()
