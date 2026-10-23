"""Motor de escaños del Congreso (ley d'Hondt por circunscripción) y backtest contra Interior.

Reglas (LOREG art. 163): en cada circunscripción (provincia; Ceuta y Melilla, 1 escaño) solo
concurren al reparto las candidaturas con al menos el 3 % de los votos VÁLIDOS (candidaturas +
blancos) de la circunscripción; los escaños se asignan por cocientes de d'Hondt. Si el último
cociente empata con el primero que se queda fuera, decide un sorteo que aquí no podemos
reproducir: `repartir` devuelve `empate=True` para que quien consuma lo vea.

Backtest: `backtest()` reparte con los votos oficiales de cada provincia (fichero 08, que ya
incluye el voto CERA) y compara con los escaños oficiales (columna "candidatos obtenidos").
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .audit_interior import DEFAULT, ELECCIONES

UMBRAL = 0.03


@dataclass
class Reparto:
    escanos: dict[str, int]
    empate: bool = False  # el último escaño se decidiría por sorteo


def repartir(votos: dict[str, int], n_escanos: int, blancos: int = 0, umbral: float = UMBRAL) -> Reparto:
    """d'Hondt con barrera. `votos`: candidatura -> votos; `blancos` cuenta para la barrera."""
    validos = sum(votos.values()) + blancos
    elegibles = {c: v for c, v in votos.items() if v > 0 and v >= umbral * validos}
    if n_escanos <= 0 or not elegibles:
        return Reparto({c: 0 for c in votos})
    cocientes = sorted(
        ((Fraction(v, k), v, c) for c, v in elegibles.items() for k in range(1, n_escanos + 1)),
        key=lambda t: (t[0], t[1], t[2]), reverse=True)
    elegidos = cocientes[:n_escanos]
    resto = cocientes[n_escanos:]
    empate = bool(resto) and resto[0][0] == elegidos[-1][0]
    out = {c: 0 for c in votos}
    for _, _, c in elegidos:
        out[c] += 1
    return Reparto(out, empate)


def _lines(path: Path):
    with open(path, encoding="latin-1", newline="") as f:
        for ln in f:
            ln = ln.rstrip("\r\n")
            if ln:
                yield ln


def leer_provincias(base: Path, per: str) -> dict[str, dict]:
    """Por provincia: escaños a repartir, blancos, votos a candidaturas y votos/escaños oficiales por candidatura."""
    d = base / f"02{per}_MESA"
    out: dict[str, dict] = {}
    for ln in _lines(d / f"0702{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(12, 13) != "99" and g(14, 14) == "9":
            out[g(12, 13)] = {"nombre": g(15, 64).strip(), "escanos": int(g(150, 155)), "blancos": int(g(126, 133)),
                              "candidaturas": int(g(142, 149)), "votos": {}, "oficial": {}}
    for ln in _lines(d / f"0802{per[2:]}.DAT"):
        g = lambda a, b: ln[a - 1:b]
        if g(12, 13) != "99" and g(14, 14) == "9" and g(12, 13) in out:
            out[g(12, 13)]["votos"][g(15, 20)] = int(g(21, 28))
            out[g(12, 13)]["oficial"][g(15, 20)] = int(g(29, 33))
    return out


def backtest(base: Path = DEFAULT) -> list[dict]:
    """Una fila por (elección, provincia) con el resultado de comparar d'Hondt con el oficial."""
    filas = []
    for per, el in ELECCIONES.items():
        for prov, p in leer_provincias(base, per).items():
            r = repartir(p["votos"], p["escanos"], p["blancos"])
            dif = {c: (r.escanos.get(c, 0), p["oficial"].get(c, 0)) for c in p["votos"]
                   if r.escanos.get(c, 0) != p["oficial"].get(c, 0)}
            filas.append({"eleccion": el, "prov": prov, "nombre": p["nombre"], "escanos": p["escanos"],
                          "suma_votos": sum(p["votos"].values()), "votos_oficiales": p["candidaturas"],
                          "suma_escanos_oficial": sum(p["oficial"].values()), "empate": r.empate, "dif": dif})
    return filas


def main() -> int:
    filas = backtest()
    malas = [f for f in filas if f["dif"]]
    print(f"{len(filas)} circunscripciones-elección; con diferencias: {len(malas)}")
    for f in malas[:30]:
        print(f["eleccion"], f["prov"], f["nombre"], "escaños", f["escanos"], "empate" if f["empate"] else "", f["dif"])
    return 0 if not malas else 1


if __name__ == "__main__":
    raise SystemExit(main())
