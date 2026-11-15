from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from .datos import ELECCIONES, PARTIDOS

PARTIDOS_MODELO = ["pp", "psoe", "vox", "podemos_sumar", "cs", "erc", "ciu_jxcat", "pnv",
                   "eh_bildu", "bng", "cc", "compromis", "iu", "upyd"]

SOCIO_MODELO = ["edad_media", "escolarizacion", "esperanza_vida", "pct_mujeres",
                "pct_inmigrantes", "tasa_paro", "pib_per_capita", "tasa_criminalidad_1000"]

OBJETIVOS = [f"rel_{p}" for p in PARTIDOS_MODELO] + ["rel_participacion"]

UMBRAL_NACIONAL = 0.5


def _indice(eleccion):
    return ELECCIONES.index(eleccion)


class ModeloEscenarios:

    def __init__(self, almacen, ruta_cache=None):
        self.a = almacen
        self.ruta_cache = Path(ruta_cache) if ruta_cache else None
        self.tabla = self._preparar()
        self.modelos = {}
        self.entradas = None
        self.metricas = {}

    def _preparar(self):
        m = self.a.mun.copy()
        m["conv"] = m["eleccion"].map(_indice)
        columnas = (["conv", "eleccion", "prov_cod", "ccaa_cod", "mun_id", "municipio",
                     "provincia", "mun_poblacion", "censo_escrutinio", "votos_contabilizados",
                     "participacion", "pct_izquierda_total", "pct_derecha_total",
                     "pct_nacionalista", "indice_izq_der"] +
                    [f"pct_{p}" for p in PARTIDOS_MODELO] + SOCIO_MODELO)
        m = m[columnas]
        nacional = self._nacional_por_eleccion()
        for retardo in (1, 2):
            previo = m.copy()
            previo["conv"] = previo["conv"] + retardo
            renombre = {c: f"r{retardo}_{c}" for c in
                        [f"pct_{p}" for p in PARTIDOS_MODELO] +
                        ["participacion", "pct_izquierda_total", "pct_derecha_total",
                         "pct_nacionalista", "indice_izq_der"]}
            previo = previo[["conv", "mun_id"] + list(renombre)].rename(columns=renombre)
            m = m.merge(previo, on=["conv", "mun_id"], how="left")
        m = m.merge(nacional, on="conv", how="left")
        m["log_poblacion"] = np.log10(m["mun_poblacion"].clip(lower=1))
        for p in PARTIDOS_MODELO:
            nac = m[f"nac_pct_{p}"].where(m[f"nac_pct_{p}"] > UMBRAL_NACIONAL)
            m[f"rel_{p}"] = m[f"pct_{p}"] / nac
            for retardo in (1, 2):
                nac_previo = m["conv"].map(
                    nacional.set_index("conv")[f"nac_pct_{p}"].shift(0).to_dict())
                previo_nac = m["conv"].sub(retardo).map(
                    nacional.set_index("conv")[f"nac_pct_{p}"].to_dict())
                previo_nac = previo_nac.where(previo_nac > UMBRAL_NACIONAL)
                m[f"r{retardo}_rel_{p}"] = m[f"r{retardo}_pct_{p}"] / previo_nac
        m["rel_participacion"] = m["participacion"] / m["nac_participacion"]
        for retardo in (1, 2):
            previo_nac = m["conv"].sub(retardo).map(
                nacional.set_index("conv")["nac_participacion"].to_dict())
            m[f"r{retardo}_rel_participacion"] = m[f"r{retardo}_participacion"] / previo_nac
        return m

    def _nacional_por_eleccion(self):
        filas = []
        for e in ELECCIONES:
            r = self.a.resultado("nacional", None, e)
            fila = {"conv": _indice(e), "nac_participacion": r["resumen"]["participacion"]}
            for p in PARTIDOS_MODELO:
                fila[f"nac_pct_{p}"] = r["resumen"][f"pct_{p}"]
            filas.append(fila)
        return pd.DataFrame(filas)

    def _columnas_entrada(self):
        return ([f"r1_rel_{p}" for p in PARTIDOS_MODELO] +
                [f"r2_rel_{p}" for p in PARTIDOS_MODELO] +
                ["r1_rel_participacion", "r2_rel_participacion",
                 "r1_indice_izq_der", "r2_indice_izq_der",
                 "r1_pct_nacionalista", "r2_pct_nacionalista"] +
                SOCIO_MODELO + ["log_poblacion", "prov_cod", "ccaa_cod"])

    def entrenar(self, hasta_conv=None, verbose=False):
        self.entradas = self._columnas_entrada()
        datos = self.tabla[self.tabla["r1_rel_pp"].notna()].copy()
        if hasta_conv is not None:
            datos = datos[datos["conv"] <= hasta_conv]
        for c in ("prov_cod", "ccaa_cod"):
            datos[c] = datos[c].astype("category")
        self.categorias = {c: datos[c].cat.categories for c in ("prov_cod", "ccaa_cod")}
        peso = datos["censo_escrutinio"].clip(lower=1)
        for objetivo in OBJETIVOS:
            ok = datos[objetivo].notna()
            modelo = HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.08, max_depth=None,
                categorical_features="from_dtype", random_state=0)
            modelo.fit(datos.loc[ok, self.entradas], datos.loc[ok, objetivo],
                       sample_weight=peso[ok])
            self.modelos[objetivo] = modelo
            if verbose:
                print(f"   entrenado {objetivo}")
        return self

    def _preparar_entrada(self, datos):
        X = datos[self.entradas].copy()
        for c in ("prov_cod", "ccaa_cod"):
            X[c] = pd.Categorical(X[c], categories=self.categorias[c])
        return X

    def _predecir(self, datos):
        X = self._preparar_entrada(datos)
        salida = pd.DataFrame(index=datos.index)
        for objetivo, modelo in self.modelos.items():
            salida[objetivo] = np.clip(modelo.predict(X), 0, 100)
        return salida

    def backtest(self, eleccion="2023"):
        conv = _indice(eleccion)
        self.entrenar(hasta_conv=conv - 1)
        reales = self.tabla[(self.tabla["conv"] == conv) &
                            self.tabla["r1_rel_pp"].notna()].copy()
        rel = self._predecir(reales)
        peso = reales["censo_escrutinio"].clip(lower=1)
        pred = pd.DataFrame(index=reales.index)
        for p in PARTIDOS_MODELO:
            nac = float(reales[f"nac_pct_{p}"].iloc[0])
            pred[f"pct_{p}"] = np.clip(rel[f"rel_{p}"] * nac, 0, 100) if nac > UMBRAL_NACIONAL \
                else 0.0
        pred["participacion"] = np.clip(
            rel["rel_participacion"] * float(reales["nac_participacion"].iloc[0]), 0, 100)
        resumen = []
        for p in PARTIDOS_MODELO + ["participacion"]:
            objetivo = "participacion" if p == "participacion" else f"pct_{p}"
            if p != "participacion" and float(reales[f"nac_pct_{p}"].iloc[0]) <= UMBRAL_NACIONAL:
                continue
            ok = reales[objetivo].notna()
            if ok.sum() < 50:
                continue
            y, yp = reales.loc[ok, objetivo], pred.loc[ok, objetivo]
            nombre = "Participación" if p == "participacion" else PARTIDOS[p][0]
            resumen.append({
                "objetivo": objetivo, "nombre": nombre,
                "mae": float(mean_absolute_error(y, yp, sample_weight=peso[ok])),
                "r2": float(r2_score(y, yp, sample_weight=peso[ok])),
                "media_real": float(np.average(y, weights=peso[ok])),
                "media_pred": float(np.average(yp, weights=peso[ok])),
            })
        resumen.sort(key=lambda r: -r["media_real"])
        detalle = []
        muestra = reales.assign(_p=pred["pct_pp"], _s=pred["pct_psoe"],
                                _v=pred["pct_vox"]).nlargest(150, "censo_escrutinio")
        for _, r in muestra.iterrows():
            detalle.append({"municipio": r["municipio"], "provincia": r["provincia"],
                            "censo": int(r["censo_escrutinio"]),
                            "pp_real": float(r["pct_pp"]), "pp_pred": float(r["_p"]),
                            "psoe_real": float(r["pct_psoe"]), "psoe_pred": float(r["_s"]),
                            "vox_real": float(r["pct_vox"]), "vox_pred": float(r["_v"])})
        acierto = 0
        claves = [f"pct_{p}" for p in PARTIDOS_MODELO]
        real_gan = reales[claves].idxmax(axis=1)
        pred_gan = pred[claves].idxmax(axis=1)
        acierto = float((real_gan.to_numpy() == pred_gan.to_numpy()).mean())
        self.metricas = {"eleccion": eleccion, "resumen": resumen, "detalle": detalle,
                         "n_municipios": int(len(reales)),
                         "acierto_ganador": acierto,
                         "entrenado_hasta": ELECCIONES[conv - 1]}
        self.entrenar()
        return self.metricas

    def base_escenario(self):
        ultimo = _indice(ELECCIONES[-1])
        base = self.tabla[self.tabla["conv"] == ultimo].copy()
        base = base[base["r1_rel_pp"].notna()]
        partida = {}
        for p in PARTIDOS_MODELO:
            partida[p] = float(base[f"nac_pct_{p}"].iloc[0])
        partida["participacion"] = float(base["nac_participacion"].iloc[0])
        return base, partida

    def simular(self, nacional):
        base, partida = self.base_escenario()
        futuro = base.copy()
        futuro["conv"] = futuro["conv"] + 1
        for p in PARTIDOS_MODELO:
            futuro[f"r2_rel_{p}"] = base[f"r1_rel_{p}"].to_numpy()
            futuro[f"r1_rel_{p}"] = base[f"rel_{p}"].to_numpy()
        futuro["r2_rel_participacion"] = base["r1_rel_participacion"].to_numpy()
        futuro["r1_rel_participacion"] = base["rel_participacion"].to_numpy()
        for campo in ("indice_izq_der", "pct_nacionalista"):
            futuro[f"r2_{campo}"] = base[f"r1_{campo}"].to_numpy()
            futuro[f"r1_{campo}"] = base[campo].to_numpy()
        rel = self._predecir(futuro)
        pred = pd.DataFrame(index=futuro.index)
        objetivo_part = float(nacional.get("participacion", partida["participacion"]))
        pred["participacion"] = np.clip(rel["rel_participacion"] * objetivo_part, 0, 100)
        peso = (futuro["censo_escrutinio"].to_numpy() *
                pred["participacion"].to_numpy() / 100).clip(min=1)
        for p in PARTIDOS_MODELO:
            objetivo = float(nacional.get(p, partida[p]))
            pred[f"pct_{p}"] = np.clip(rel[f"rel_{p}"].fillna(0) * objetivo, 0, 100)
            implicito = float(np.average(pred[f"pct_{p}"], weights=peso))
            if implicito > 0.01 and objetivo > 0:
                pred[f"pct_{p}"] = np.clip(pred[f"pct_{p}"] * objetivo / implicito, 0, 100)
        suma = pred[[f"pct_{p}" for p in PARTIDOS_MODELO]].sum(axis=1)
        exceso = (suma > 99).to_numpy()
        if exceso.any():
            factor = 99 / suma[exceso]
            for p in PARTIDOS_MODELO:
                pred.loc[exceso, f"pct_{p}"] *= factor
        salida = futuro[["mun_id", "municipio", "provincia", "prov_cod", "ccaa_cod",
                         "mun_poblacion", "censo_escrutinio"]].copy()
        for p in PARTIDOS_MODELO:
            salida[f"pct_{p}"] = pred[f"pct_{p}"].to_numpy()
        salida["participacion"] = pred["participacion"].to_numpy()
        salida["ganador"] = salida[[f"pct_{p}" for p in PARTIDOS_MODELO]].idxmax(axis=1) \
            .str.replace("pct_", "", regex=False)
        return salida, peso

    def resumen_simulacion(self, nacional):
        salida, peso = self.simular(nacional)
        provincias = []
        for cod, grupo in salida.groupby("prov_cod", observed=True):
            w = grupo["censo_escrutinio"].clip(lower=1)
            fila = {"codigo": cod, "nombre": self.a.nombre("provincia", cod)}
            for p in PARTIDOS_MODELO:
                fila[p] = float(np.average(grupo[f"pct_{p}"], weights=w))
            fila["participacion"] = float(np.average(grupo["participacion"], weights=w))
            ganador = max(PARTIDOS_MODELO, key=lambda p: fila[p])
            fila["ganador"] = PARTIDOS[ganador][0]
            fila["ganador_clave"] = ganador
            fila["color"] = PARTIDOS[ganador][1]
            provincias.append(fila)
        provincias.sort(key=lambda f: f["nombre"])
        conteo = {}
        for f in provincias:
            conteo[f["ganador"]] = conteo.get(f["ganador"], 0) + 1
        municipios_ganados = salida["ganador"].value_counts().to_dict()
        return {
            "provincias": provincias,
            "provincias_ganadas": conteo,
            "municipios_ganados": {PARTIDOS[k][0]: int(v)
                                   for k, v in municipios_ganados.items() if k in PARTIDOS},
            "nacional": nacional,
        }
