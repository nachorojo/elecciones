from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PARTIDOS = {
    "pp": ("PP", "#1D84CE"),
    "psoe": ("PSOE", "#E30713"),
    "vox": ("VOX", "#5BA82B"),
    "podemos_sumar": ("Podemos / Sumar", "#6B2E7A"),
    "cs": ("Ciudadanos", "#EB6109"),
    "iu": ("IU", "#A61B29"),
    "upyd": ("UPyD", "#E4007C"),
    "erc": ("ERC", "#FFB232"),
    "ciu_jxcat": ("CiU / JxCat", "#00A99D"),
    "pnv": ("PNV", "#0F6B3C"),
    "eh_bildu": ("EH Bildu", "#9FC131"),
    "bng": ("BNG", "#79A9D1"),
    "cc": ("Coalición Canaria", "#F2C200"),
    "compromis": ("Compromís", "#D96A2B"),
}

BLOQUES = {
    "izquierda": ("Izquierda", "#8E0E2E"),
    "centro_izquierda": ("Centro izquierda", "#E30713"),
    "centro_derecha": ("Centro derecha", "#1D84CE"),
    "derecha": ("Derecha", "#0E2D5B"),
    "reg_izquierda": ("Regionalista izquierda", "#F2A03D"),
    "reg_derecha": ("Regionalista derecha", "#00A99D"),
    "otros": ("Otros", "#9AA5B1"),
}

SOCIO = ["edad_media", "escolarizacion", "esperanza_vida", "pct_mujeres", "pct_inmigrantes",
         "tasa_paro", "pib_per_capita", "tasa_criminalidad_1000"]

SOCIO_ETIQUETA = {
    "edad_media": "Edad media",
    "escolarizacion": "Escolarización",
    "esperanza_vida": "Esperanza de vida",
    "pct_mujeres": "% de mujeres",
    "pct_inmigrantes": "% de población extranjera",
    "tasa_paro": "Tasa de paro",
    "pib_per_capita": "PIB per cápita",
    "tasa_criminalidad_1000": "Condenados por 1000 hab.",
}

METRICAS = {
    "participacion": ("Participación", "%"),
    "pct_izquierda_total": ("Voto de izquierdas", "%"),
    "pct_derecha_total": ("Voto de derechas", "%"),
    "pct_nacionalista": ("Voto nacionalista", "%"),
    "indice_izq_der": ("Índice izquierda-derecha", "pts"),
    "posicion_ideologica": ("Posición ideológica (0-10)", ""),
    "censo_escrutinio": ("Censo", "electores"),
    "votantes": ("Votantes", "votos"),
    "votos_contabilizados": ("Votos a candidaturas", "votos"),
    "pct_blancos": ("Voto en blanco", "%"),
    "pct_nulos": ("Voto nulo", "%"),
}

ELECCIONES = ["1996", "2000", "2004", "2008", "2011", "2015", "2016", "2019a", "2019b", "2023"]

ELECCION_ETIQUETA = {
    "1996": "3 de marzo de 1996", "2000": "12 de marzo de 2000",
    "2004": "14 de marzo de 2004", "2008": "9 de marzo de 2008",
    "2011": "20 de noviembre de 2011", "2015": "20 de diciembre de 2015",
    "2016": "26 de junio de 2016", "2019a": "28 de abril de 2019",
    "2019b": "10 de noviembre de 2019", "2023": "23 de julio de 2023",
}

COLS_VOTOS = ([f"votos_{p}" for p in PARTIDOS] + [f"votos_{b}" for b in BLOQUES] +
              ["votos_izquierda_total", "votos_derecha_total", "votos_contabilizados",
               "votos_candidaturas", "votos_validos", "votos_blancos", "votos_nulos",
               "censo_escrutinio", "votantes"])


class Almacen:

    def __init__(self, directorio):
        self.dir = Path(directorio)
        self.mun = pd.read_parquet(self.dir / "db_municipios.parquet")
        self.mun["mun_id"] = self.mun["prov_cod"] + self.mun["mun_cod"]
        self._ruta_mesas = self.dir / "db_mesas.parquet"
        self._mesas = None
        self._cache = {}
        self._preparar_catalogos()

    def _preparar_catalogos(self):
        ultimo = self.mun[self.mun["eleccion"] == "2023"]
        self.nombres_mun = dict(zip(ultimo["mun_id"], ultimo["municipio"]))
        for mid, nom in zip(self.mun["mun_id"], self.mun["municipio"]):
            self.nombres_mun.setdefault(mid, nom)
        self.nombres_prov = dict(zip(self.mun["prov_cod"], self.mun["provincia"]))
        self.nombres_ccaa = dict(zip(self.mun["ccaa_cod"], self.mun["ccaa"]))
        self.prov_de_mun = dict(zip(self.mun["mun_id"], self.mun["prov_cod"]))
        self.ccaa_de_prov = dict(zip(self.mun["prov_cod"], self.mun["ccaa_cod"]))
        pob = self.mun[self.mun["eleccion"] == "2023"].set_index("mun_id")["mun_poblacion"]
        self.poblacion_mun = pob.to_dict()

    @property
    def mesas(self):
        if self._mesas is None:
            columnas = (["eleccion", "prov_cod", "provincia", "mun_cod", "municipio",
                         "distrito", "seccion", "mesa", "censo_escrutinio", "votantes",
                         "participacion", "votos_contabilizados", "votos_blancos", "votos_nulos",
                         "indice_izq_der", "posicion_ideologica", "bloque_ganador",
                         "familia_ganadora", "pct_izquierda_total", "pct_derecha_total"] +
                        [f"votos_{p}" for p in PARTIDOS])
            self._mesas = pd.read_parquet(self._ruta_mesas, columns=columnas)
            self._mesas["mun_id"] = self._mesas["prov_cod"] + self._mesas["mun_cod"]
        return self._mesas

    def _filtrar(self, nivel, codigo):
        if nivel == "nacional":
            return self.mun
        if nivel == "ccaa":
            return self.mun[self.mun["ccaa_cod"] == codigo]
        if nivel == "provincia":
            return self.mun[self.mun["prov_cod"] == codigo]
        if nivel == "municipio":
            return self.mun[self.mun["mun_id"] == codigo]
        raise ValueError(f"nivel desconocido: {nivel}")

    def nombre(self, nivel, codigo):
        if nivel == "nacional":
            return "España"
        return {"ccaa": self.nombres_ccaa, "provincia": self.nombres_prov,
                "municipio": self.nombres_mun}[nivel].get(codigo, codigo)

    def existe(self, nivel, codigo):
        if nivel == "nacional":
            return True
        return not self._filtrar(nivel, codigo).empty

    def _agregar(self, datos):
        if datos.empty:
            return None
        suma = datos[COLS_VOTOS].sum()
        fila = {c: int(suma[c]) for c in COLS_VOTOS}
        base = max(int(suma["votos_contabilizados"]), 1)
        fila["participacion"] = 100 * suma["votantes"] / max(int(suma["censo_escrutinio"]), 1)
        for p in PARTIDOS:
            fila[f"pct_{p}"] = 100 * suma[f"votos_{p}"] / base
        for b in BLOQUES:
            fila[f"pct_{b}"] = 100 * suma[f"votos_{b}"] / base
        fila["pct_izquierda_total"] = 100 * suma["votos_izquierda_total"] / base
        fila["pct_derecha_total"] = 100 * suma["votos_derecha_total"] / base
        fila["pct_nacionalista"] = fila["pct_reg_izquierda"] + fila["pct_reg_derecha"]
        fila["indice_izq_der"] = fila["pct_derecha_total"] - fila["pct_izquierda_total"]
        fila["pct_blancos"] = 100 * suma["votos_blancos"] / max(int(suma["votos_validos"]), 1)
        fila["pct_nulos"] = 100 * suma["votos_nulos"] / max(int(suma["votantes"]), 1)
        fila["mun_poblacion"] = int(datos["mun_poblacion"].sum())
        peso = datos["mun_poblacion"].clip(lower=1)
        eje = datos["posicion_ideologica"] * datos["votos_contabilizados"]
        fila["posicion_ideologica"] = (eje.sum() /
                                       max(datos.loc[eje.notna(), "votos_contabilizados"].sum(), 1))
        for s in SOCIO:
            valores = datos[s]
            ok = valores.notna()
            fila[s] = float((valores[ok] * peso[ok]).sum() / peso[ok].sum()) if ok.any() else None
        fila["n_municipios"] = int(datos["mun_id"].nunique())
        return fila

    def resultado(self, nivel, codigo, eleccion):
        datos = self._filtrar(nivel, codigo)
        datos = datos[datos["eleccion"] == eleccion]
        fila = self._agregar(datos)
        if fila is None:
            return None
        partidos = sorted(
            ({"clave": p, "nombre": PARTIDOS[p][0], "color": PARTIDOS[p][1],
              "votos": fila[f"votos_{p}"], "pct": fila[f"pct_{p}"]}
             for p in PARTIDOS if fila[f"votos_{p}"] > 0),
            key=lambda d: -d["votos"])
        otros = fila["votos_contabilizados"] - sum(p["votos"] for p in partidos)
        if otros > 0:
            partidos.append({"clave": "otros", "nombre": "Otras candidaturas",
                             "color": "#9AA5B1", "votos": int(otros),
                             "pct": 100 * otros / max(fila["votos_contabilizados"], 1)})
        bloques = sorted(
            ({"clave": b, "nombre": BLOQUES[b][0], "color": BLOQUES[b][1],
              "votos": fila[f"votos_{b}"], "pct": fila[f"pct_{b}"]}
             for b in BLOQUES if fila[f"votos_{b}"] > 0),
            key=lambda d: -d["votos"])
        return {
            "nivel": nivel, "codigo": codigo, "territorio": self.nombre(nivel, codigo),
            "eleccion": eleccion, "fecha": ELECCION_ETIQUETA[eleccion],
            "resumen": fila, "partidos": partidos, "bloques": bloques,
            "ganador": partidos[0] if partidos else None,
            "socio": {s: fila[s] for s in SOCIO},
        }

    def evolucion(self, nivel, codigo):
        datos = self._filtrar(nivel, codigo)
        serie = []
        for e in ELECCIONES:
            fila = self._agregar(datos[datos["eleccion"] == e])
            if fila is None:
                continue
            entrada = {"eleccion": e, "participacion": fila["participacion"],
                       "indice_izq_der": fila["indice_izq_der"],
                       "pct_izquierda_total": fila["pct_izquierda_total"],
                       "pct_derecha_total": fila["pct_derecha_total"],
                       "pct_nacionalista": fila["pct_nacionalista"],
                       "posicion_ideologica": fila["posicion_ideologica"],
                       "censo_escrutinio": fila["censo_escrutinio"],
                       "votantes": fila["votantes"]}
            for p in PARTIDOS:
                entrada[f"pct_{p}"] = fila[f"pct_{p}"]
                entrada[f"votos_{p}"] = fila[f"votos_{p}"]
            ganador = max(PARTIDOS, key=lambda p: fila[f"votos_{p}"])
            entrada["ganador"] = PARTIDOS[ganador][0] if fila[f"votos_{ganador}"] > 0 else None
            entrada["ganador_clave"] = ganador
            serie.append(entrada)
        return {"nivel": nivel, "codigo": codigo,
                "territorio": self.nombre(nivel, codigo), "serie": serie}

    def ranking(self, metrica, eleccion, nivel="municipio", orden="desc", n=15,
                poblacion_minima=0, ccaa=None, provincia=None):
        datos = self.mun[self.mun["eleccion"] == eleccion]
        if ccaa:
            datos = datos[datos["ccaa_cod"] == ccaa]
        if provincia:
            datos = datos[datos["prov_cod"] == provincia]
        if nivel == "municipio":
            datos = datos[datos["mun_poblacion"] >= poblacion_minima]
            grupos = [(r["mun_id"], r) for _, r in datos.iterrows()]
            filas = []
            for mid, r in grupos:
                filas.append({"codigo": mid, "nombre": r["municipio"],
                              "contexto": r["provincia"], "poblacion": int(r["mun_poblacion"]),
                              "valor": r.get(metrica)})
        else:
            clave = "ccaa_cod" if nivel == "ccaa" else "prov_cod"
            filas = []
            for cod, grupo in datos.groupby(clave):
                fila = self._agregar(grupo)
                if fila is None or fila.get(metrica) is None:
                    continue
                filas.append({"codigo": cod, "nombre": self.nombre(nivel, cod),
                              "contexto": "", "poblacion": fila["mun_poblacion"],
                              "valor": fila[metrica]})
        filas = [f for f in filas if f["valor"] is not None and not pd.isna(f["valor"])]
        filas.sort(key=lambda f: f["valor"], reverse=(orden == "desc"))
        etiqueta, unidad = METRICAS.get(metrica, (metrica, ""))
        if metrica.startswith("pct_") and metrica not in METRICAS:
            clave = metrica[4:]
            etiqueta = PARTIDOS.get(clave, BLOQUES.get(clave, (clave, ""))) [0]
            etiqueta = f"Voto a {etiqueta}"
            unidad = "%"
        return {"metrica": metrica, "etiqueta": etiqueta, "unidad": unidad,
                "eleccion": eleccion, "nivel": nivel, "orden": orden,
                "filas": filas[:n]}

    def comparar(self, objetivos, eleccion):
        salida = []
        for nivel, codigo in objetivos:
            r = self.resultado(nivel, codigo, eleccion)
            if r:
                salida.append(r)
        return {"eleccion": eleccion, "resultados": salida}

    def detalle_mesas(self, mun_id, eleccion, limite=400):
        d = self.mesas
        d = d[(d["mun_id"] == mun_id) & (d["eleccion"] == eleccion)]
        d = d.sort_values(["distrito", "seccion", "mesa"])
        filas = []
        for _, r in d.head(limite).iterrows():
            filas.append({
                "distrito": r["distrito"], "seccion": r["seccion"], "mesa": r["mesa"],
                "censo": int(r["censo_escrutinio"]), "votantes": int(r["votantes"]),
                "participacion": float(r["participacion"]) if pd.notna(r["participacion"]) else None,
                "ganador": r["familia_ganadora"],
                "indice": float(r["indice_izq_der"]) if pd.notna(r["indice_izq_der"]) else None,
            })
        return {"mun_id": mun_id, "municipio": self.nombres_mun.get(mun_id, mun_id),
                "eleccion": eleccion, "total_mesas": int(len(d)), "mesas": filas}

    def mapa(self, eleccion, metrica="indice_izq_der", nivel="provincia"):
        datos = self.mun[self.mun["eleccion"] == eleccion]
        clave = "ccaa_cod" if nivel == "ccaa" else "prov_cod"
        salida = []
        for cod, grupo in datos.groupby(clave):
            fila = self._agregar(grupo)
            ganador = max(PARTIDOS, key=lambda p: fila[f"votos_{p}"])
            salida.append({"codigo": cod, "nombre": self.nombre(nivel, cod),
                           "valor": fila.get(metrica),
                           "ganador": PARTIDOS[ganador][0],
                           "color_ganador": PARTIDOS[ganador][1],
                           "participacion": fila["participacion"]})
        return {"eleccion": eleccion, "nivel": nivel, "metrica": metrica, "zonas": salida}
