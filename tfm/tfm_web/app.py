from __future__ import annotations

import argparse
import json
import os
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from motor.consultas import Motor, dec, num, redactar_plantilla
from motor.datos import (BLOQUES, ELECCION_ETIQUETA, ELECCIONES, METRICAS, PARTIDOS,
                         SOCIO_ETIQUETA, Almacen)
from motor.entidades import Catalogo
from motor.escenarios import PARTIDOS_MODELO, ModeloEscenarios
from motor.llm import Ollama

RAIZ = Path(__file__).resolve().parent
app = Flask(__name__, template_folder="plantillas", static_folder="static")

estado = {"almacen": None, "catalogo": None, "motor": None, "llm": None,
          "escenarios": None, "backtest": None, "entrenando": False}
candado = threading.Lock()


def arrancar(directorio_datos):
    estado["almacen"] = Almacen(directorio_datos)
    estado["catalogo"] = Catalogo(estado["almacen"])
    estado["motor"] = Motor(estado["almacen"], estado["catalogo"])
    estado["llm"] = Ollama(os.environ.get("MODELO_OLLAMA"))


def modelo_escenarios():
    with candado:
        if estado["escenarios"] is None:
            estado["entrenando"] = True
            me = ModeloEscenarios(estado["almacen"])
            estado["backtest"] = me.backtest("2023")
            estado["escenarios"] = me
            estado["entrenando"] = False
    return estado["escenarios"]


def datos_verificados(resultado, intencion):
    a = estado["almacen"]
    tipo = resultado.get("tipo")
    lineas = []
    if tipo == "resultado":
        for r in resultado["resultados"]:
            res = r["resumen"]
            lineas.append(f"Territorio: {r['territorio']} ({r['nivel']})")
            lineas.append(f"Eleccion: {r['fecha']}")
            lineas.append(f"Censo: {num(res['censo_escrutinio'])} electores")
            lineas.append(f"Votantes: {num(res['votantes'])}")
            lineas.append(f"Participacion: {dec(res['participacion'])} %")
            lineas.append(f"Voto en blanco: {dec(res['pct_blancos'])} % | "
                          f"Voto nulo: {dec(res['pct_nulos'])} %")
            lineas.append("Resultados por candidatura:")
            for p in r["partidos"]:
                lineas.append(f"  - {p['nombre']}: {num(p['votos'])} votos, {dec(p['pct'])} %")
            lineas.append(f"Bloque de izquierdas: {dec(res['pct_izquierda_total'])} % | "
                          f"bloque de derechas: {dec(res['pct_derecha_total'])} % | "
                          f"nacionalistas: {dec(res['pct_nacionalista'])} %")
            socio = {SOCIO_ETIQUETA[k]: v for k, v in r["socio"].items() if v is not None}
            if socio:
                lineas.append("Contexto socioeconomico: " +
                              ", ".join(f"{k} {dec(v)}" for k, v in socio.items()))
            lineas.append("")
    elif tipo == "comparar":
        lineas.append(f"Comparacion en la eleccion de {resultado['eleccion']}")
        for r in resultado["resultados"]:
            arriba = ", ".join(f"{p['nombre']} {dec(p['pct'])} %" for p in r["partidos"][:5])
            lineas.append(f"  {r['territorio']}: participacion "
                          f"{dec(r['resumen']['participacion'])} %; {arriba}")
    elif tipo == "evolucion":
        lineas.append(f"Serie historica de {resultado['territorio']}")
        for e in resultado["serie"]:
            cabeza = ", ".join(f"{PARTIDOS[p][0]} {dec(e[f'pct_{p}'])} %"
                               for p in ("pp", "psoe", "vox", "podemos_sumar")
                               if e.get(f"pct_{p}", 0) > 1)
            lineas.append(f"  {e['eleccion']}: gano {e['ganador']}, participacion "
                          f"{dec(e['participacion'])} %; {cabeza}")
    elif tipo == "ranking":
        lineas.append(f"{resultado['etiqueta']} en {resultado['eleccion']}, "
                      f"ambito {resultado['ambito']}, nivel {resultado['nivel']}")
        for i, f in enumerate(resultado["filas"], 1):
            lineas.append(f"  {i}. {f['nombre']} ({f['contexto']}): {dec(f['valor'])}")
    elif tipo == "mesas":
        lineas.append(f"{resultado['municipio']} en {resultado['eleccion']}: "
                      f"{num(resultado['total_mesas'])} mesas")
        for f in resultado["mesas"][:25]:
            lineas.append(f"  distrito {f['distrito']} seccion {f['seccion']} mesa {f['mesa']}: "
                          f"censo {num(f['censo'])}, participacion {dec(f['participacion'])} %, "
                          f"gano {f['ganador']}")
    else:
        lineas.append(resultado.get("mensaje", ""))
        if resultado.get("detalle"):
            lineas.append(resultado["detalle"])
    return "\n".join(lineas)


@app.route("/")
def indice():
    return render_template("index.html")


@app.route("/api/estado")
def api_estado():
    llm = estado["llm"]
    llm.comprobar()
    return jsonify({
        "llm_disponible": llm.disponible, "modelo": llm.modelo, "error": llm.error,
        "modelos": llm.modelos,
        "elecciones": [{"clave": e, "etiqueta": ELECCION_ETIQUETA[e]} for e in ELECCIONES],
        "partidos": {k: {"nombre": v[0], "color": v[1]} for k, v in PARTIDOS.items()},
        "bloques": {k: {"nombre": v[0], "color": v[1]} for k, v in BLOQUES.items()},
        "metricas": {k: v[0] for k, v in METRICAS.items()},
        "n_mesas": 573617, "n_municipios": len(estado["almacen"].nombres_mun),
        "escenarios_listos": estado["escenarios"] is not None,
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    cuerpo = request.get_json(force=True)
    pregunta = (cuerpo.get("pregunta") or "").strip()
    historial = cuerpo.get("historial") or []
    contexto = cuerpo.get("contexto") or {}
    if not pregunta:
        return jsonify({"error": "pregunta vacía"}), 400

    motor = estado["motor"]
    intencion = motor.interpretar(pregunta, contexto)
    llm = estado["llm"]
    usado_llm = False

    if llm.disponible:
        sugerencia = llm.intencion(pregunta, intencion, historial)
        if sugerencia and sugerencia.get("tipo") in (
                "resultado", "evolucion", "ranking", "comparar", "mesas", "futuro",
                "escenario", "ayuda"):
            if intencion["territorios"] or sugerencia["tipo"] in ("futuro", "escenario", "ayuda"):
                intencion["tipo"] = sugerencia["tipo"]
            if sugerencia.get("metrica") and not intencion["metrica"]:
                intencion["metrica"] = sugerencia["metrica"]
        if intencion["tipo"] in ("resultado", "comparar", "mesas", "ranking") \
                and not intencion["elecciones"]:
            intencion["elecciones"] = ["2023"]

    resultado = motor.ejecutar(intencion)
    hechos = datos_verificados(resultado, intencion)
    texto = None
    if llm.disponible and resultado.get("tipo") not in ("ayuda",):
        texto = llm.redactar(pregunta, hechos)
        usado_llm = texto is not None
    if not texto:
        texto = redactar_plantilla(resultado, intencion, estado["almacen"])

    nuevo_contexto = {
        "territorios": [{"nivel": t["nivel"], "codigo": t.get("codigo"),
                         "nombre": t["nombre"]} for t in intencion["territorios"]],
        "elecciones": intencion["elecciones"],
    }
    return jsonify({"texto": texto, "datos": resultado, "intencion": {
        "tipo": intencion["tipo"],
        "territorios": nuevo_contexto["territorios"],
        "elecciones": intencion["elecciones"],
        "partidos": intencion["partidos"], "metrica": intencion["metrica"]},
        "contexto": nuevo_contexto, "llm": usado_llm, "hechos": hechos})


@app.route("/api/buscar")
def api_buscar():
    q = request.args.get("q", "")
    if len(q) < 2:
        return jsonify([])
    return jsonify(estado["catalogo"].buscar(q, limite=8))


@app.route("/api/resultado")
def api_resultado():
    r = estado["almacen"].resultado(request.args.get("nivel", "nacional"),
                                    request.args.get("codigo") or None,
                                    request.args.get("eleccion", "2023"))
    return jsonify(r or {})


@app.route("/api/evolucion")
def api_evolucion():
    return jsonify(estado["almacen"].evolucion(request.args.get("nivel", "nacional"),
                                               request.args.get("codigo") or None))


@app.route("/api/mapa")
def api_mapa():
    return jsonify(estado["almacen"].mapa(request.args.get("eleccion", "2023"),
                                          request.args.get("metrica", "indice_izq_der"),
                                          request.args.get("nivel", "provincia")))


@app.route("/api/ranking")
def api_ranking():
    a = estado["almacen"]
    return jsonify(a.ranking(request.args.get("metrica", "participacion"),
                             request.args.get("eleccion", "2023"),
                             nivel=request.args.get("nivel", "provincia"),
                             orden=request.args.get("orden", "desc"),
                             n=int(request.args.get("n", 15)),
                             poblacion_minima=int(request.args.get("minimo", 0))))


@app.route("/api/mesas")
def api_mesas():
    return jsonify(estado["almacen"].detalle_mesas(request.args.get("mun_id"),
                                                   request.args.get("eleccion", "2023")))


@app.route("/api/backtest")
def api_backtest():
    modelo_escenarios()
    return jsonify(estado["backtest"])


@app.route("/api/escenario", methods=["POST"])
def api_escenario():
    cuerpo = request.get_json(force=True)
    modelo = modelo_escenarios()
    _, partida = modelo.base_escenario()
    nacional = {k: float(v) for k, v in (cuerpo.get("nacional") or {}).items()}
    completo = dict(partida)
    completo.update(nacional)
    return jsonify({"partida": partida, "resultado": modelo.resumen_simulacion(completo)})


@app.route("/api/escenario/partida")
def api_escenario_partida():
    modelo = modelo_escenarios()
    _, partida = modelo.base_escenario()
    return jsonify({"partida": partida,
                    "partidos": [{"clave": p, "nombre": PARTIDOS[p][0],
                                  "color": PARTIDOS[p][1], "valor": partida[p]}
                                 for p in PARTIDOS_MODELO if partida[p] > 0.4]})


def main():
    ap = argparse.ArgumentParser(description="Web de consulta electoral del TFM")
    ap.add_argument("--datos", default=str(RAIZ.parent / "db_tfm"))
    ap.add_argument("--puerto", type=int, default=7800)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--entrenar-al-arrancar", action="store_true")
    args = ap.parse_args()

    print(f"Cargando datos desde {args.datos} ...")
    arrancar(args.datos)
    llm = estado["llm"]
    print(f"  {len(estado['almacen'].nombres_mun):,} municipios, "
          f"{len(estado['catalogo'].indice):,} nombres indexados")
    if llm.disponible:
        print(f"  Modelo de lenguaje: {llm.modelo}")
    else:
        print(f"  Sin modelo de lenguaje ({llm.error}). Se usará el intérprete de reglas.")
    if args.entrenar_al_arrancar:
        print("  Entrenando modelo de escenarios ...")
        modelo_escenarios()
        print(f"  Listo. Acierto del ganador municipal en 2023: "
              f"{100 * estado['backtest']['acierto_ganador']:.1f} %")
    print(f"\n  http://{args.host}:{args.puerto}\n")
    app.run(host=args.host, port=args.puerto, debug=False, threaded=True)


if __name__ == "__main__":
    main()
