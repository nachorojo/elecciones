from __future__ import annotations

import re

import pandas as pd

from .datos import BLOQUES, ELECCION_ETIQUETA, ELECCIONES, PARTIDOS, SOCIO_ETIQUETA
from .entidades import normalizar


def num(n):
    return f"{int(n):,}".replace(",", ".")


def dec(x, decimales=2):
    if x is None or (isinstance(x, float) and x != x):
        return "sin dato"
    return f"{x:,.{decimales}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")

PATRONES = [
    ("escenario", r"\bsi\s+(el|la|los)\b.*\b(saca|sacara|obtiene|sube|baja)\b|escenario|simula|"
                  r"que pasaria si|simulacion"),
    ("futuro", r"\bfuturo\b|\b2027\b|\b2028\b|proxima[s]? elecci|quien ganara|"
               r"que va a pasar|prediccion|predice|pronostico"),
    ("mesas", r"\bmesas?\b|\bseccion(es)?\b|\bdistrito\b|colegio electoral"),
    ("ranking", r"\bdonde\b|\branking\b|\btop\b|\blos que mas\b|\blos que menos\b|"
                r"\bmas alt[ao]s?\b|\bmas baj[ao]s?\b|\bmejores\b|\bpeores\b|"
                r"en que (sitio|lugar)|"
                r"\b(municipios?|provincias?|comunidades?|pueblos?|ciudades?)\b[^.]*"
                r"\b(con mas|con menos|mas|menos|mayor(es)?|menor(es)?)\b"),
    ("evolucion", r"\bevolucion\b|\bhistori[ac]\b|\bdesde\b|\ba lo largo\b|\bcomo ha (cambiado|"
                  r"evolucionado)\b|\bpor ano\b|\bcada eleccion\b|\ben el tiempo\b|\btendencia\b"),
    ("comparar", r"\bcompar|\bdiferencia entre\b|\bfrente a\b|\bcontra\b|\bvs\b|\bversus\b"),
]


def detectar_tipo(frase, n_territorios):
    texto = normalizar(frase)
    for tipo, patron in PATRONES:
        if re.search(patron, texto):
            return tipo
    if n_territorios >= 2:
        return "comparar"
    if n_territorios >= 1:
        return "resultado"
    return "ayuda"


class Motor:

    def __init__(self, almacen, catalogo):
        self.a = almacen
        self.c = catalogo

    def interpretar(self, frase, contexto=None):
        territorios = self.c.extraer_territorios(frase)
        elecciones, ambigua = self.c.extraer_elecciones(frase)
        partidos = self.c.extraer_partidos(frase)
        metrica = self.c.extraer_metrica(frase)
        contexto = contexto or {}
        if not territorios and contexto.get("territorios"):
            territorios = contexto["territorios"]
        if not elecciones and contexto.get("elecciones"):
            elecciones = contexto["elecciones"]
        tipo = detectar_tipo(frase, len(territorios))
        if tipo in ("resultado", "comparar", "mesas", "ranking") and not elecciones:
            elecciones = ["2023"]
        return {"tipo": tipo, "territorios": territorios, "elecciones": elecciones,
                "partidos": partidos, "metrica": metrica, "eleccion_ambigua": ambigua,
                "frase": frase}

    def ejecutar(self, intencion):
        tipo = intencion["tipo"]
        metodo = getattr(self, f"_h_{tipo}", None)
        if metodo is None:
            return self._h_ayuda(intencion)
        return metodo(intencion)

    def _territorio(self, intencion):
        if intencion["territorios"]:
            t = intencion["territorios"][0]
            return t["nivel"], t.get("codigo")
        return "nacional", None

    def _h_resultado(self, intencion):
        nivel, codigo = self._territorio(intencion)
        salida = []
        for e in intencion["elecciones"][:3]:
            r = self.a.resultado(nivel, codigo, e)
            if r:
                salida.append(r)
        if not salida:
            return {"tipo": "vacio", "mensaje": "No tengo datos para esa combinación."}
        return {"tipo": "resultado", "resultados": salida,
                "partidos_pedidos": intencion["partidos"],
                "metrica": intencion["metrica"],
                "alternativas": (intencion["territorios"][0].get("alternativas", [])
                                 if intencion["territorios"] else [])}

    def _h_comparar(self, intencion):
        objetivos = [(t["nivel"], t.get("codigo")) for t in intencion["territorios"][:4]]
        if len(objetivos) < 2:
            return self._h_resultado(intencion)
        eleccion = intencion["elecciones"][0]
        return {"tipo": "comparar", **self.a.comparar(objetivos, eleccion),
                "partidos_pedidos": intencion["partidos"]}

    def _h_evolucion(self, intencion):
        nivel, codigo = self._territorio(intencion)
        datos = self.a.evolucion(nivel, codigo)
        datos["partidos_pedidos"] = intencion["partidos"] or ["pp", "psoe"]
        datos["metrica"] = intencion["metrica"] or "participacion"
        datos["tipo"] = "evolucion"
        return datos

    def _h_ranking(self, intencion):
        texto = normalizar(intencion["frase"])
        metrica = intencion["metrica"]
        if intencion["partidos"]:
            metrica = f"pct_{intencion['partidos'][0]}"
        if not metrica:
            metrica = "participacion"
        orden = "asc" if re.search(r"\bmenos\b|\bmenor|\bmas baj|\bpeor", texto) else "desc"
        invertir_valor = False
        orden_mostrado = orden
        if metrica == "abstencion":
            invertir_valor = True
            metrica = "participacion"
            orden = "desc" if orden == "asc" else "asc"
        nivel = "municipio"
        if re.search(r"\bprovincia", texto):
            nivel = "provincia"
        elif re.search(r"\bcomunidad|\bautonomi", texto):
            nivel = "ccaa"
        ambito_ccaa = ambito_prov = None
        for t in intencion["territorios"]:
            if t["nivel"] == "ccaa":
                ambito_ccaa = t["codigo"]
            elif t["nivel"] == "provincia":
                ambito_prov = t["codigo"]
        minimo = 0
        m = re.search(r"(mas|mayores) de ([\d.]+)\s*(mil|habitantes|hab)", texto)
        if m:
            minimo = int(float(m.group(2).replace(".", "")) * (1000 if m.group(3) == "mil" else 1))
        elif nivel == "municipio" and not re.search(r"\bpueblo|\baldea|\bpeque", texto):
            minimo = 5000
        eleccion = intencion["elecciones"][0]
        r = self.a.ranking(metrica, eleccion, nivel=nivel, orden=orden, n=15,
                           poblacion_minima=minimo, ccaa=ambito_ccaa, provincia=ambito_prov)
        if invertir_valor:
            for f in r["filas"]:
                f["valor"] = 100 - f["valor"]
            r["etiqueta"] = "Abstención"
            r["orden"] = orden_mostrado
        r["tipo"] = "ranking"
        r["poblacion_minima"] = minimo
        r["ambito"] = (self.a.nombre("ccaa", ambito_ccaa) if ambito_ccaa else
                       self.a.nombre("provincia", ambito_prov) if ambito_prov else "España")
        return r

    def _h_mesas(self, intencion):
        territorio = next((t for t in intencion["territorios"] if t["nivel"] == "municipio"), None)
        if territorio is None:
            for t in intencion["territorios"]:
                alt = next((x for x in t.get("alternativas", [])
                            if x["nivel"] == "municipio"), None)
                if alt:
                    territorio = alt
                    break
        if territorio is None:
            return {"tipo": "aviso",
                    "mensaje": "El detalle por mesa necesita un municipio concreto. "
                               "Prueba con \"mesas de Segovia en 2023\"."}
        datos = self.a.detalle_mesas(territorio["codigo"], intencion["elecciones"][0])
        datos["tipo"] = "mesas"
        return datos

    def _h_futuro(self, intencion):
        return {"tipo": "futuro",
                "mensaje": "No puedo decirte quién ganará las próximas elecciones, y "
                           "desconfía de cualquier modelo que diga que sí puede.",
                "detalle": "Entre 1996 y 2023 el vuelco del voto nacional de una convocatoria "
                           "a la siguiente tiene una desviación típica de 11,7 puntos y un "
                           "máximo de 18,9. Con nueve saltos observados, y sin datos sobre "
                           "liderazgos, campañas o partidos que aún no existen, ese vuelco no "
                           "se puede aprender. Lo que sí sé hacer es repartir por el territorio "
                           "un resultado nacional que tú me des: ve a la pestaña de escenarios."}

    def _h_escenario(self, intencion):
        return {"tipo": "escenario_redirigir",
                "mensaje": "Para eso tengo el simulador de escenarios.",
                "partidos": intencion["partidos"]}

    def _h_ayuda(self, intencion):
        return {"tipo": "ayuda", "mensaje": "No he identificado ningún territorio en la pregunta.",
                "ejemplos": ["¿Quién ganó en Sevilla en 2011?",
                             "Participación en el País Vasco en 2023",
                             "Evolución del PP en Galicia",
                             "¿Dónde sacó más VOX en 2023?",
                             "Compara Madrid y Barcelona en 2019 de noviembre",
                             "Mesas de Cuenca en 2023"]}


def redactar_plantilla(resultado, intencion, almacen):
    tipo = resultado.get("tipo")
    if tipo == "resultado":
        partes = []
        for r in resultado["resultados"]:
            g = r["ganador"]
            res = r["resumen"]
            linea = (f"En **{r['territorio']}**, en las elecciones del {r['fecha']}, "
                     f"ganó **{g['nombre']}** con {num(g['votos'])} votos "
                     f"({dec(g['pct'])} %).")
            segundo = r["partidos"][1] if len(r["partidos"]) > 1 else None
            if segundo:
                linea += (f" Le siguió {segundo['nombre']} con {num(segundo['votos'])} votos "
                          f"({dec(segundo['pct'])} %).")
            linea += (f" La participación fue del {dec(res['participacion'])} % sobre un censo "
                      f"de {num(res['censo_escrutinio'])} electores.")
            if res["pct_izquierda_total"] and res["pct_derecha_total"]:
                linea += (f" El bloque de izquierdas sumó {dec(res['pct_izquierda_total'])} % "
                          f"y el de derechas {dec(res['pct_derecha_total'])} %.")
            partes.append(linea)
        for clave in intencion.get("partidos", []):
            r = resultado["resultados"][0]
            p = next((x for x in r["partidos"] if x["clave"] == clave), None)
            if p:
                partes.append(f"{p['nombre']} obtuvo {num(p['votos'])} votos "
                              f"({dec(p['pct'])} %) en {r['territorio']}.")
        metrica = intencion.get("metrica")
        if metrica in SOCIO_ETIQUETA:
            valor = resultado["resultados"][0]["socio"].get(metrica)
            if valor is not None:
                partes.append(f"{SOCIO_ETIQUETA[metrica]}: {dec(valor)}.")
        return " ".join(partes)
    if tipo == "comparar":
        trozos = []
        for r in resultado["resultados"]:
            g = r["ganador"]
            trozos.append(f"**{r['territorio']}**: ganó {g['nombre']} con {dec(g['pct'])} %, "
                          f"participación {dec(r['resumen']['participacion'])} %")
        return (f"Comparación en las elecciones de {resultado['eleccion']}. " +
                ". ".join(trozos) + ".")
    if tipo == "evolucion":
        serie = resultado["serie"]
        if not serie:
            return "No tengo serie para ese territorio."
        ganadores = {}
        for e in serie:
            ganadores.setdefault(e["ganador"], []).append(e["eleccion"])
        detalle = "; ".join(f"{k} en {', '.join(v)}" for k, v in ganadores.items() if k)
        return (f"Evolución de **{resultado['territorio']}** en las diez convocatorias entre "
                f"1996 y 2023. Ganadores: {detalle}. La participación pasó del "
                f"{dec(serie[0]['participacion'])} % en 1996 al "
                f"{dec(serie[-1]['participacion'])} % en 2023.")
    if tipo == "ranking":
        filas = resultado["filas"]
        if not filas:
            return "No he encontrado resultados con esos filtros."
        sentido = "de mayor a menor" if resultado["orden"] == "desc" else "de menor a mayor"
        cabeza = ", ".join(f"{f['nombre']} ({dec(f['valor'])})" for f in filas[:3])
        nivel = {"municipio": "municipios", "provincia": "provincias",
                 "ccaa": "comunidades"}[resultado["nivel"]]
        return (f"Ranking de {nivel} por {resultado['etiqueta'].lower()} en "
                f"{resultado['eleccion']}, {sentido}, dentro de {resultado['ambito']}. "
                f"Encabezan: {cabeza}.")
    if tipo == "mesas":
        return (f"**{resultado['municipio']}** tuvo {num(resultado['total_mesas'])} mesas "
                f"en {resultado['eleccion']}.")
    for clave in ("mensaje",):
        if clave in resultado:
            return resultado[clave]
    return "No he sabido interpretar la pregunta."
