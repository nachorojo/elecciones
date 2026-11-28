"""Temas para artículos con los resultados municipales del 29N: rankings y curiosidades listos para Redacción.

    python -m pipeline.curiosidades_29n                 # último envío guardado en ..\\datos\\29n_envios
    python -m pipeline.curiosidades_29n --carpeta RUTA  # un envío concreto (carpeta con municipios_NN.csv[.gz])
    python -m pipeline.curiosidades_29n --publicar      # además, git add + commit + push del JSON

Lee los ficheros de municipios de Interior de un envío (los guarda `captura_29n`) y los compara con 2023
(`web/data/mun/NN.json`, y la tabla del TFM si está). Escribe `web/data/curiosidades_29n.json`, que pinta
`web/curiosidades.html`. No toca la captura: se lanza en otra ventana, mejor con la captura ya parada
(dos procesos haciendo `git push` a la vez pueden chocar).

Cada tema lleva su regla escrita. Reglas editoriales que se respetan aquí:
  - Solo entran municipios con el 100 % escrutado (salvo `--parcial`), y casi siempre con un mínimo de electores:
    en un pueblo de 20 votantes cualquier porcentaje es extremo.
  - «Electores» es el censo electoral de Interior, no la población.
  - No se habla de trasvases de voto: con datos por municipio se sabe cuánto sube o baja cada partido, no de quién
    vienen los votos. Los temas de «sube X y baja Y» son movimientos que coinciden, no una transferencia medida.
  - El espacio de Sumar de 2023 concurre dividido en 2026: se compara con la SUMA de sus herederos (Frente Amplio,
    Podemos, Adelante Andalucía, Compromís y NC), nunca partido a partido.
"""
from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

from . import escrutinio_29n as E

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web" / "data"
SALIDA = WEB / "curiosidades_29n.json"
ENVIOS = REPO.parent / "datos" / "29n_envios"

NOMBRE = {"PP": "PP", "PSOE": "PSOE", "VOX": "Vox", "FA": "Frente Amplio", "PODEMOS": "Podemos", "SALF": "Se Acabó la Fiesta",
          "ERC": "ERC", "JUNTS": "Junts", "EH_BILDU": "EH Bildu", "PNV": "PNV", "BNG": "BNG", "CC": "Coalición Canaria",
          "COMPROMIS": "Compromís", "NC": "NC-Podemos-IU-Sumar", "ADELANTE": "Adelante Andalucía", "TERUEL_EXISTE": "Teruel Existe",
          "GBAI": "Geroa Bai", "PACMA": "PACMA", "IZQ": "Espacio de Sumar"}
# Familias de 2023 (web/data/partidos.json) -> clave comparable con 2026. UPN va hoy con el PP.
DE_2023 = {"PP": "PP", "UPN": "PP", "PSOE": "PSOE", "VOX": "VOX", "PODEMOS_SUMAR": "IZQ", "COMPROMIS": "IZQ", "NUEVA_CANARIAS": "IZQ",
           "ERC": "ERC", "CIU_JXCAT": "JUNTS", "EH_BILDU": "EH_BILDU", "PNV": "PNV", "BNG": "BNG", "CC": "CC", "GEROA_BAI": "GBAI"}
HEREDEROS = ("FA", "PODEMOS", "ADELANTE", "COMPROMIS", "NC")       # en 2026 suman el «espacio de Sumar»
ELECCIONES = ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]


def _bonito(nombre: str) -> str:
    """«CORUÑA, A» -> «A Coruña»; mayúsculas de Interior a tipo título."""
    n = nombre.strip()
    if ", " in n:
        a, b = n.rsplit(", ", 1)
        n = f"{b} {a}"
    menores = {"de", "del", "la", "las", "los", "el", "y", "i", "d'", "l'", "da", "do", "das", "dos", "en", "a", "o"}
    import re
    pal = re.split(r"([ /\-])", n.lower())
    return "".join(p if (i and p in menores) or p in " /-" else p[:1].upper() + p[1:] for i, p in enumerate(pal))


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def leer_envio(carpeta: Path) -> list[dict]:
    """Registros municipales (y de distrito) de todas las provincias que haya en la carpeta del envío."""
    out = []
    for f in sorted(carpeta.glob("municipios_*.csv*")):
        datos = gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
        out += E.leer_municipios(E.texto(datos))
    return out


def ultimo_envio(raiz: Path = ENVIOS) -> Path:
    cand = [p for p in raiz.glob("envio_*") if p.is_dir() and any(p.glob("municipios_*.csv*"))]
    if not cand:
        raise SystemExit(f"No hay envíos con ficheros de municipios en {raiz}")
    return max(cand, key=lambda p: p.stat().st_mtime)


def _historia() -> tuple[dict, dict]:
    """Por municipio: nombre y, por elección, (censo, votantes, válidos, {familia: votos}, familia ganadora)."""
    partidos = json.loads((WEB / "partidos.json").read_text(encoding="utf-8"))
    try:                                      # votos íntegros de 2023 (la web recorta al 1,5 %); solo si hay pyarrow
        from . import noche as N
        integros = N._votos_tfm(("2023",))
    except Exception:
        integros = {}
    nombres, hist = {}, {}
    for f in sorted((WEB / "mun").glob("*.json")):
        for mid, m in json.loads(f.read_text(encoding="utf-8")).items():
            nombres[mid] = m["n"]
            hist[mid] = {}
            for e, h in m["h"].items():
                if not h or h[0] <= 0:
                    continue
                fam = {c: v[1] for c, v in partidos.get(e, {}).items()}
                votos: dict[str, int] = {}
                for cod, n in h[5]:
                    k = fam.get(cod, "OTROS")
                    votos[k] = votos.get(k, 0) + n
                if e == "2023":
                    votos.update(integros.get(("2023", mid), {}))
                gana = max(h[5], key=lambda x: x[1])[0] if h[5] else None
                hist[mid][e] = {"censo": h[0], "votantes": h[1], "validos": h[4] + h[2], "votos": votos,
                                "gana": fam.get(gana, "OTROS") if gana else None}
    return nombres, hist


def _muni(r: dict, nombres: dict, hist: dict, provs: dict) -> dict:
    """Un municipio (o distrito) de 2026 con todo lo que usan los temas."""
    votos: dict[str, int] = {}
    siglas: dict[str, str] = {}
    for p in r["partidos"]:
        k = E.espacio_api(p["c"], p["s"])
        if k == "OTROS":
            k = "OTROS:" + p["s"]
        votos[k] = votos.get(k, 0) + p["v"]
        siglas.setdefault(k, p["s"])
    validos = sum(votos.values()) + r["blancos"]
    orden = sorted(votos.items(), key=lambda x: -x[1])
    izq = sum(votos.get(k, 0) for k in HEREDEROS)
    comp = {k: v for k, v in votos.items() if not k.startswith("OTROS:") and k not in HEREDEROS}
    comp["IZQ"] = izq
    h23 = hist.get(r["id"], {}).get("2023") if r["distrito"] == "99" else None
    v23 = {}
    if h23:
        for f, n in h23["votos"].items():
            k = "TERUEL_EXISTE" if (f == "ESPANA_VACIADA" and r["prov"] == "44") else DE_2023.get(f)
            if k:
                v23[k] = v23.get(k, 0) + n
    return {"id": r["id"], "prov": r["prov"], "distrito": r["distrito"],
            "nombre": nombres.get(r["id"]) if r["distrito"] == "99" and r["id"] in nombres else _bonito(r["nombre"]),
            "provincia": provs.get(r["prov"], r["prov"]), "censo": r["censo"], "escrutado": r["pct_escrutado"],
            "votantes": r["votantes"], "blancos": r["blancos"], "nulos": r["nulos"], "validos": validos,
            "votos": votos, "siglas": siglas, "orden": orden, "comp": comp,
            "h23": h23, "v23": v23, "validos23": h23["validos"] if h23 else 0}


def _n(k: str, m: dict | None = None) -> str:
    if k.startswith("OTROS:"):
        return (m or {}).get("siglas", {}).get(k, k[6:])
    return NOMBRE.get(k, k)


def _el(k: str) -> str:
    """Con artículo: «el PP», «el Frente Amplio», «Vox»."""
    return {"IZQ": "el espacio de Sumar", "FA": "el Frente Amplio"}.get(k) or (("el " if k in ("PP", "PSOE", "PNV", "BNG") else "") + _n(k))


def _al(k: str) -> str:
    return _el(k).replace("el ", "al ", 1) if _el(k).startswith("el ") else "a " + _el(k)


def _pct(a: float, b: float, d: int = 1):
    return round(100 * a / b, d) if b else None


def _lugar(m: dict) -> str:
    return f"{m['nombre']} ({m['provincia']})"


def tema(ident, titular, regla, columnas, filas, nota=""):
    return {"id": ident, "titular": titular, "regla": regla, "columnas": columnas, "filas": filas, "nota": nota}


def generar(registros: list[dict], vivo: dict | None = None, parcial: bool = False, top: int = 15) -> dict:
    nombres, hist = _historia()
    provs = {k: v["nombre"] for k, v in (vivo or {}).get("provincias", {}).items()}
    todos = [_muni(r, nombres, hist, provs) for r in registros]
    listo = (lambda m: m["validos"] > 0) if parcial else (lambda m: m["escrutado"] >= 100 and m["validos"] > 0)
    M = [m for m in todos if m["distrito"] == "99" and listo(m)]
    D = [m for m in todos if m["distrito"] != "99" and listo(m)]
    n_mun = sum(1 for m in todos if m["distrito"] == "99")
    T: list[dict] = []
    ganador = lambda m: m["orden"][0][0] if m["orden"] and m["orden"][0][1] > 0 else None
    con = lambda minimo: [m for m in M if m["censo"] >= minimo]
    p = lambda m, k: _pct(m["votos"].get(k, 0), m["validos"])
    part = lambda m: _pct(m["votantes"], m["censo"], 2)

    # 1-6. Dónde es más fuerte cada partido
    for k, minimo in (("VOX", 1000), ("PP", 1000), ("PSOE", 1000), ("FA", 1000), ("SALF", 1000), ("PODEMOS", 1000)):
        l = sorted((m for m in con(minimo) if m["votos"].get(k, 0) >= 10), key=lambda m: -p(m, k))[:top]
        T.append(tema(f"fuerte_{k}", f"El municipio donde más se ha votado {_al(k)}",
                      f"Mayor porcentaje de {_n(k)} sobre votos válidos, entre municipios con al menos {minimo:,} electores y el 100 % escrutado.".replace(",", "."),
                      ["Municipio", "% " + _n(k), "Votos", "Electores"],
                      [[_lugar(m), p(m, k), m["votos"][k], m["censo"]] for m in l]))
    # 7. Dónde gana Vox (y cada partido): recuento y los mayores
    gan: dict[str, list] = {}
    for m in M:
        g = ganador(m)
        if g:
            gan.setdefault(g, []).append(m)
    T.append(tema("ganadores", "Cuántos municipios gana cada partido",
                  "Candidatura más votada en cada municipio con el 100 % escrutado. Se añade el más poblado de los que gana.",
                  ["Candidatura", "Municipios ganados", "El mayor que gana", "Electores"],
                  [[_n(k, l[0]), len(l), _lugar(max(l, key=lambda m: m["censo"])), max(l, key=lambda m: m["censo"])["censo"]]
                   for k, l in sorted(gan.items(), key=lambda x: -len(x[1]))][:25]))
    for k in ("VOX", "FA", "SALF"):
        l = sorted(gan.get(k, []), key=lambda m: -m["censo"])[:top]
        T.append(tema(f"gana_{k}", f"Los municipios donde ha ganado {_el(k)}",
                      f"Municipios donde {_n(k)} es la candidatura más votada ({len(gan.get(k, []))} en total), ordenados por electores.",
                      ["Municipio", "% " + _n(k), "Electores", "Ganó en 2023"],
                      [[_lugar(m), p(m, k), m["censo"], NOMBRE.get(DE_2023.get((m["h23"] or {}).get("gana"), ""), (m["h23"] or {}).get("gana") or "—")] for m in l]))
    # 8-9. Participación
    for ident, tit, signo, minimo in (("abstencion", "El municipio con mayor abstención", 1, 1000), ("participacion", "El municipio donde más se ha votado", -1, 1000),
                                      ("abstencion_ciudades", "La ciudad que menos ha votado", 1, 50000), ("participacion_ciudades", "La ciudad que más ha votado", -1, 50000)):
        l = sorted(con(minimo), key=lambda m: signo * part(m))[:top]
        T.append(tema(ident, tit, f"Participación (votantes sobre electores), municipios con al menos {minimo:,} electores.".replace(",", "."),
                      ["Municipio", "Participación %", "Abstención %", "Electores", "Participación 2023 %"],
                      [[_lugar(m), part(m), round(100 - part(m), 2), m["censo"], _pct(m["h23"]["votantes"], m["h23"]["censo"], 2) if m["h23"] else None] for m in l]))
    dpart = lambda m: part(m) - _pct(m["h23"]["votantes"], m["h23"]["censo"], 2)
    l = sorted((m for m in con(1000) if m["h23"]), key=dpart)
    for ident, tit, trozo in (("participacion_cae", "Donde más se ha hundido la participación", [m for m in l if dpart(m) < 0][:top]),
                              ("participacion_sube", "Donde más ha subido la participación", [m for m in l[::-1] if dpart(m) > 0][:top])):
        T.append(tema(ident, tit, "Diferencia de participación frente a julio de 2023, en puntos; municipios con al menos 1.000 electores.",
                      ["Municipio", "Diferencia (puntos)", "2026 %", "2023 %", "Electores"],
                      [[_lugar(m), round(part(m) - _pct(m["h23"]["votantes"], m["h23"]["censo"], 2), 2), part(m), _pct(m["h23"]["votantes"], m["h23"]["censo"], 2), m["censo"]] for m in trozo]))
    # 10. Los más pequeños
    l = sorted(M, key=lambda m: m["censo"])[:10]
    T.append(tema("pequenos", "Así han votado los 10 municipios con menos electores de España",
                  "Los diez municipios con menor censo electoral (electores, no habitantes) y el 100 % escrutado.",
                  ["Municipio", "Electores", "Votantes", "Ganador", "Votos del ganador", "Reparto completo"],
                  [[_lugar(m), m["censo"], m["votantes"], _n(ganador(m), m) if ganador(m) else "—", m["orden"][0][1] if m["orden"] else 0,
                    ", ".join(f"{_n(k, m)} {v}" for k, v in m["orden"] if v > 0)] for m in l]))
    l = [m for m in M if m["censo"] > 0 and m["votantes"] == m["censo"]]
    T.append(tema("pleno", "Los pueblos donde ha votado todo el censo", f"Municipios con participación del 100 % ({len(l)}).",
                  ["Municipio", "Electores", "Ganador"], [[_lugar(m), m["censo"], _n(ganador(m), m) if ganador(m) else "—"] for m in sorted(l, key=lambda m: -m["censo"])[:top]]))
    # 11-13. Unanimidad, empates, por un voto
    l = sorted((m for m in M if m["orden"] and m["validos"] >= 10 and m["orden"][0][1] / m["validos"] >= 0.8), key=lambda m: -m["orden"][0][1] / m["validos"])[:top]
    T.append(tema("unanimidad", "Los pueblos del voto casi unánime", "Municipios (con al menos 10 votos válidos) donde una candidatura supera el 80 % de los votos válidos.",
                  ["Municipio", "Candidatura", "%", "Votos", "Votos válidos"], [[_lugar(m), _n(m["orden"][0][0], m), _pct(m["orden"][0][1], m["validos"]), m["orden"][0][1], m["validos"]] for m in l]))
    emp = [m for m in M if len(m["orden"]) > 1 and m["orden"][0][1] > 0 and m["orden"][0][1] == m["orden"][1][1]]
    T.append(tema("empates", "Empate exacto: los municipios donde nadie ha ganado", f"Municipios donde las dos candidaturas más votadas tienen los mismos votos ({len(emp)}), de mayor a menor.",
                  ["Municipio", "Candidaturas", "Votos de cada una", "Electores"],
                  [[_lugar(m), " y ".join(_n(k, m) for k, v in m["orden"] if v == m["orden"][0][1]), m["orden"][0][1], m["censo"]] for m in sorted(emp, key=lambda m: -m["censo"])[:top]]))
    uno = [m for m in M if len(m["orden"]) > 1 and m["orden"][0][1] - m["orden"][1][1] == 1]
    T.append(tema("un_voto", "Ganar por un solo voto", f"Municipios donde la primera candidatura saca un voto a la segunda ({len(uno)}), de mayor a menor.",
                  ["Municipio", "Gana", "Segunda", "Votos", "Electores"],
                  [[_lugar(m), _n(m["orden"][0][0], m), _n(m["orden"][1][0], m), f"{m['orden'][0][1]} a {m['orden'][1][1]}", m["censo"]] for m in sorted(uno, key=lambda m: -m["censo"])[:top]]))
    l = sorted((m for m in con(5000) if len(m["orden"]) > 1), key=lambda m: (m["orden"][0][1] - m["orden"][1][1]) / m["validos"])[:top]
    T.append(tema("ajustados", "Las ciudades más reñidas", "Menor distancia en puntos entre primera y segunda candidatura, municipios con al menos 5.000 electores.",
                  ["Municipio", "Primera", "Segunda", "Diferencia en votos", "Diferencia (puntos)"],
                  [[_lugar(m), _n(m["orden"][0][0], m), _n(m["orden"][1][0], m), m["orden"][0][1] - m["orden"][1][1], _pct(m["orden"][0][1] - m["orden"][1][1], m["validos"], 2)] for m in l]))
    # 14. Cambios de color frente a 2023
    g23 = lambda m: DE_2023.get((m["h23"] or {}).get("gana") or "", None)
    g26 = lambda m: "IZQ" if ganador(m) in HEREDEROS else ganador(m)
    cambia = [m for m in M if m["h23"] and g23(m) and g26(m) and g23(m) != g26(m)]
    cuenta: dict[str, int] = {}
    for m in cambia:
        k = f"{_n(g23(m))} → {_n(ganador(m), m)}"
        cuenta[k] = cuenta.get(k, 0) + 1
    T.append(tema("vuelcos_resumen", "El mapa cambia de color: cuántos municipios cambian de ganador",
                  f"Municipios cuyo partido más votado es distinto del de julio de 2023 ({len(cambia)} de {len(M)}). UPN cuenta como PP.",
                  ["Cambio", "Municipios"], [[k, v] for k, v in sorted(cuenta.items(), key=lambda x: -x[1])][:20]))
    T.append(tema("vuelcos", "Las mayores ciudades que cambian de ganador", "Municipios con distinto ganador que en 2023, ordenados por electores.",
                  ["Municipio", "Ganó en 2023", "Gana ahora", "% ahora", "Electores"],
                  [[_lugar(m), _n(g23(m)), _n(ganador(m), m), _pct(m["orden"][0][1], m["validos"]), m["censo"]] for m in sorted(cambia, key=lambda m: -m["censo"])[:top]]))
    # 15. Feudos que caen: mismo ganador en las diez elecciones desde 1996 y hoy gana otro
    feudos = []
    for m in M:
        h = hist.get(m["id"], {})
        if all(e in h for e in ELECCIONES):
            gs = {("PP" if h[e]["gana"] == "UPN" else h[e]["gana"]) for e in ELECCIONES}
            if len(gs) == 1 and next(iter(gs)) in ("PP", "PSOE", "PNV", "ERC", "CIU_JXCAT", "EH_BILDU", "BNG", "CC") and g26(m) != DE_2023.get(next(iter(gs)), next(iter(gs))):
                feudos.append((m, next(iter(gs))))
    T.append(tema("feudos", "Cae el feudo: municipios que cambian de ganador por primera vez desde 1996",
                  f"Municipios donde la misma fuerza fue la más votada en las diez generales de 1996 a 2023 y ahora gana otra ({len(feudos)}), por electores.",
                  ["Municipio", "Ganaba siempre", "Gana ahora", "Electores"],
                  [[_lugar(m), NOMBRE.get(DE_2023.get(f, f), f), _n(ganador(m), m), m["censo"]] for m, f in sorted(feudos, key=lambda x: -x[0]["censo"])[:top]],
                  "La historia se compara por municipio con los límites actuales; los municipios fusionados o nuevos no entran."))
    # 16-18. Subidas y caídas frente a 2023 (puntos sobre votos válidos)
    def dif(m, k):
        if not m["h23"] or not m["validos23"] or k not in m["v23"]:
            return None
        return round(100 * m["comp"].get(k, 0) / m["validos"] - 100 * m["v23"][k] / m["validos23"], 2)
    for k in ("PP", "PSOE", "VOX", "IZQ"):
        l = sorted(((m, dif(m, k)) for m in con(1000) if dif(m, k) is not None), key=lambda x: x[1])
        for ident, tit, trozo in ((f"cae_{k}", f"Donde más se hunde {_el(k)}", [x for x in l if x[1] < 0][:top]),
                                  (f"sube_{k}", f"Donde más crece {_el(k)}", [x for x in l[::-1] if x[1] > 0][:top])):
            T.append(tema(ident, tit, f"Variación de {_n(k)} en puntos sobre votos válidos frente a julio de 2023; municipios con al menos 1.000 electores."
                          + (" El espacio de Sumar de 2023 se compara con la suma de Frente Amplio, Podemos, Adelante Andalucía, Compromís y NC." if k == "IZQ" else ""),
                          ["Municipio", "Variación (puntos)", "2026 %", "2023 %", "Electores"],
                          [[_lugar(m), d, _pct(m["comp"].get(k, 0), m["validos"]), _pct(m["v23"][k], m["validos23"]), m["censo"]] for m, d in trozo]))
    # 19. Movimientos que coinciden (no es un trasvase medido)
    for a, b in (("PP", "VOX"), ("VOX", "PP"), ("PSOE", "PP"), ("PP", "PSOE"), ("PSOE", "IZQ"), ("IZQ", "PSOE")):
        l = [(m, dif(m, a), dif(m, b)) for m in con(1000) if dif(m, a) is not None and dif(m, b) is not None and dif(m, a) < 0 < dif(m, b)]
        l = sorted(l, key=lambda x: -min(-x[1], x[2]))[:top]
        T.append(tema(f"mov_{a}_{b}", f"Donde {_el(a)} baja y {_el(b)} sube a la vez",
                      f"Municipios (al menos 1.000 electores) donde {_el(a)} pierde puntos y {_el(b)} los gana frente a 2023, ordenados por el menor de los dos movimientos.",
                      ["Municipio", f"{_n(a)} (puntos)", f"{_n(b)} (puntos)", f"{_n(a)} votos 2023 → 2026", f"{_n(b)} votos 2023 → 2026"],
                      [[_lugar(m), x, y, f"{m['v23'][a]} → {m['comp'].get(a, 0)}", f"{m['v23'][b]} → {m['comp'].get(b, 0)}"] for m, x, y in l],
                      "Son dos movimientos que coinciden en el mismo municipio. No demuestra que los votos pasen de un partido a otro: "
                      "también cambian la participación, el censo y el resto de candidaturas."))
    # 20. Blanco y nulo
    for ident, tit, campo in (("blanco", "Donde más se ha votado en blanco", "blancos"), ("nulo", "Donde hay más voto nulo", "nulos")):
        base = (lambda m: m["validos"]) if campo == "blancos" else (lambda m: m["votantes"])
        l = sorted(con(1000), key=lambda m: -m[campo] / base(m) if base(m) else 0)[:top]
        T.append(tema(ident, tit, f"Porcentaje de voto {'en blanco sobre votos válidos' if campo == 'blancos' else 'nulo sobre votantes'}; municipios con al menos 1.000 electores.",
                      ["Municipio", "%", "Votos", "Electores"], [[_lugar(m), _pct(m[campo], base(m), 2), m[campo], m["censo"]] for m in l]))
    # 21. El pueblo que vota como España
    nac = (vivo or {}).get("nacional")
    if nac and nac.get("validos"):
        ref = {}
        for x in nac["partidos"]:
            if x["f"] != "OTROS":
                ref[x["f"]] = ref.get(x["f"], 0) + 100 * x["v"] / nac["validos"]
        claves = [k for k, v in sorted(ref.items(), key=lambda x: -x[1])[:6]]
        l = sorted(con(1000), key=lambda m: sum(abs((p(m, k) or 0) - ref[k]) for k in claves))[:top]
        T.append(tema("espejo", "El pueblo que vota como España", "Municipio (al menos 1.000 electores) cuyo reparto se parece más al nacional: suma de diferencias en puntos entre "
                      + ", ".join(_n(k) for k in claves) + ".", ["Municipio", "Distancia (puntos)"] + [_n(k) + " %" for k in claves] + ["Electores"],
                      [[_lugar(m), round(sum(abs((p(m, k) or 0) - ref[k]) for k in claves), 2)] + [p(m, k) for k in claves] + [m["censo"]] for m in l],
                      "España: " + ", ".join(f"{_n(k)} {round(ref[k], 1)} %" for k in claves) + "."))
        # 22. Votos por escaño y votos sin escaño (nivel nacional)
        l = sorted((x for x in nac["partidos"] if x["e"] > 0), key=lambda x: x["v"] / x["e"])
        T.append(tema("coste_escano", "El escaño más barato y el más caro", "Votos de cada candidatura en toda España divididos entre sus escaños.",
                      ["Candidatura", "Votos por escaño", "Votos", "Escaños"], [[NOMBRE.get(x["f"], x["s"]), round(x["v"] / x["e"]), x["v"], x["e"]] for x in l]))
        l = sorted((x for x in nac["partidos"] if x["e"] == 0), key=lambda x: -x["v"])[:10]
        T.append(tema("sin_escano", "Los votos que se quedan sin escaño", "Candidaturas con más votos en toda España y ningún diputado.",
                      ["Candidatura", "Votos", "% de válidos"], [[NOMBRE.get(x["f"], x["s"]), x["v"], _pct(x["v"], nac["validos"], 2)] for x in l]))
    # 23. Fragmentación y candidaturas locales
    l = sorted((m for m in con(5000) if m["orden"]), key=lambda m: m["orden"][0][1] / m["validos"])[:top]
    T.append(tema("fragmentado", "Ganar con poco: los municipios más repartidos", "Menor porcentaje de la candidatura ganadora; municipios con al menos 5.000 electores.",
                  ["Municipio", "Ganador", "% del ganador", "Candidaturas con más del 10 %"],
                  [[_lugar(m), _n(m["orden"][0][0], m), _pct(m["orden"][0][1], m["validos"]), sum(1 for k, v in m["orden"] if v / m["validos"] > 0.1)] for m in l]))
    l = sorted((m for m in M if ganador(m) and ganador(m).startswith("OTROS:")), key=lambda m: -m["censo"])[:top]
    T.append(tema("locales", "Donde gana una candidatura sin presencia nacional", "Municipios cuya candidatura más votada no pertenece a ninguno de los espacios con grupo o historia estatal o autonómica.",
                  ["Municipio", "Candidatura", "%", "Electores"], [[_lugar(m), _n(ganador(m), m), _pct(m["orden"][0][1], m["validos"]), m["censo"]] for m in l]))
    # 24. Podemos frente a Frente Amplio
    l = [m for m in con(1000) if m["votos"].get("PODEMOS", 0) > m["votos"].get("FA", 0) > 0]
    T.append(tema("podemos_fa", "Donde Podemos supera al Frente Amplio", f"Municipios (al menos 1.000 electores) donde Podemos tiene más votos que el Frente Amplio ({len(l)}), por electores.",
                  ["Municipio", "Podemos %", "Frente Amplio %", "Electores"], [[_lugar(m), p(m, "PODEMOS"), p(m, "FA"), m["censo"]] for m in sorted(l, key=lambda m: -m["censo"])[:top]]))
    # 25. España por tamaño de municipio
    tramos = [(0, 1000, "Menos de 1.000 electores"), (1000, 10000, "De 1.000 a 10.000"), (10000, 100000, "De 10.000 a 100.000"), (100000, 10**9, "Más de 100.000")]
    claves = ["PP", "PSOE", "VOX", "FA", "PODEMOS", "SALF"]
    filas = []
    for a, b, rot in tramos:
        g = [m for m in M if a <= m["censo"] < b]
        val = sum(m["validos"] for m in g)
        filas.append([rot, len(g), _pct(sum(m["votantes"] for m in g), sum(m["censo"] for m in g), 2)] + [_pct(sum(m["votos"].get(k, 0) for m in g), val) for k in claves])
    T.append(tema("tamano", "La España de los pueblos y la de las ciudades votan distinto", "Resultado agregado según el tamaño del municipio (electores). Se describe el voto de cada grupo de municipios, no el de sus vecinos uno a uno.",
                  ["Tamaño del municipio", "Municipios", "Participación %"] + [_n(k) + " %" for k in claves], filas))
    # 26. El municipio más poblado de cada provincia
    filas = []
    for cod in sorted({m["prov"] for m in M}):
        m = max((x for x in M if x["prov"] == cod), key=lambda x: x["censo"])
        filas.append([_lugar(m), _n(ganador(m), m) if ganador(m) else "—", _pct(m["orden"][0][1], m["validos"]) if m["orden"] else None, _n(g23(m)) if g23(m) else "—", part(m)])
    T.append(tema("mayores", "Quién gana en la mayor ciudad de cada provincia", "Municipio con más electores de cada provincia (no siempre es la capital).",
                  ["Municipio", "Gana", "%", "Ganó en 2023", "Participación %"], filas))
    # 27. Distritos de las siete grandes ciudades
    if D:
        ciudad = nombres
        for k in ("PP", "PSOE", "VOX", "FA"):
            l = sorted((m for m in D if m["votos"].get(k, 0) > 0), key=lambda m: -p(m, k))[:10]
            T.append(tema(f"distrito_{k}", f"El distrito más fiel {_al(k)} en las grandes ciudades",
                          "Distritos de Madrid, Barcelona, Valencia, Sevilla, Zaragoza, Málaga y Bilbao (los que da Interior), por porcentaje.",
                          ["Distrito", "Ciudad", "% " + _n(k), "Electores"], [[m["nombre"], ciudad.get(m["id"], m["provincia"]), p(m, k), m["censo"]] for m in l]))
        l = sorted(D, key=part)
        T.append(tema("distrito_participacion", "El distrito que más vota y el que menos", "Participación por distrito en las siete grandes ciudades: los cinco de menor y los cinco de mayor participación.",
                      ["Distrito", "Ciudad", "Participación %", "Gana"], [[m["nombre"], ciudad.get(m["id"], m["provincia"]), part(m), _n(ganador(m), m) if ganador(m) else "—"] for m in l[:5] + l[-5:]]))
    # 28. Usansolo, municipio nuevo
    u = next((m for m in todos if m["id"] == "48916" and m["distrito"] == "99"), None)
    if u and u["validos"]:
        T.append(tema("usansolo", "Usansolo vota por primera vez como municipio", "Usansolo (Bizkaia) se segregó de Galdakao en 2026: es su primera elección general con resultado propio.",
                      ["Candidatura", "Votos", "%"], [[_n(k, u), v, _pct(v, u["validos"])] for k, v in u["orden"] if v > 0][:8],
                      f"Escrutado: {u['escrutado']} %. Electores: {u['censo']}."))

    T = [t for t in T if t["filas"]]
    return {"generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "municipios": n_mun, "municipios_completos": len(M), "parcial": parcial,
            "escrutado": (vivo or {}).get("nacional", {}).get("escrutado"), "simulacro": bool((vivo or {}).get("simulacro")), "temas": T}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--carpeta", type=Path, help="carpeta de un envío (por defecto, el último de ..\\datos\\29n_envios)")
    ap.add_argument("--vivo", type=Path, default=E.VIVO, help="fichero de totales de la web (nombres de provincia y resultado nacional)")
    ap.add_argument("--salida", type=Path, default=SALIDA)
    ap.add_argument("--parcial", action="store_true", help="admite municipios sin el 100 % escrutado (para mirar antes de que acabe el recuento)")
    ap.add_argument("--publicar", action="store_true", help="git add + commit + push del fichero generado")
    a = ap.parse_args()
    carpeta = a.carpeta or ultimo_envio()
    vivo = json.loads(a.vivo.read_text(encoding="utf-8")) if a.vivo.exists() else None
    d = generar(leer_envio(carpeta), vivo, a.parcial)
    d["envio"] = carpeta.name
    a.salida.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(d['temas'])} temas con {d['municipios_completos']} de {d['municipios']} municipios completos ({carpeta.name}) -> {a.salida}")
    if a.publicar:
        for orden in (["git", "add", str(a.salida)], ["git", "commit", "-q", "-m", f"29N: temas para artículos ({carpeta.name})"], ["git", "push", "-q"]):
            r = subprocess.run(orden, cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
                print("   no se pudo publicar ->", (r.stderr or r.stdout).strip()[:200])
                break
        else:
            print("   publicado")


if __name__ == "__main__":
    main()
