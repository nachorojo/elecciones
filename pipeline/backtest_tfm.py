"""Backtest del modelo municipal de Mikel (tfm/tfm_web/motor/escenarios.py) medido en votos y escaños,
frente a la referencia simple: repetir el perfil relativo de la elección anterior.

    python pipeline/backtest_tfm.py 2008 2011 2015 2016 2019a 2019b 2023     (desde la raíz de la repo)

Necesita tfm/db_tfm/db_municipios.parquet y scikit-learn <= 1.7 (con 1.9 el entrenamiento falla
cuando una columna de entrada no tiene ningún dato). No modifica el código de Mikel.
"""
import json, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, 'tfm/tfm_web'); sys.path.insert(0, '.')
from motor.datos import Almacen, ELECCIONES
import motor.escenarios as E
from motor.escenarios import ModeloEscenarios, PARTIDOS_MODELO
TODOS = list(E.OBJETIVOS)
from pipeline.escanos import repartir

RES = {e['id']: e for e in json.load(open('web/data/resultados.json'))['elecciones']}
a = Almacen('tfm/db_tfm')
m = ModeloEscenarios(a)
claves = [f'pct_{p}' for p in PARTIDOS_MODELO]

def evaluar(reales, rel, nombre):
    """rel: DataFrame con rel_<partido> y rel_participacion predichos. Reescala al nacional real, como `simular`."""
    pred = pd.DataFrame(index=reales.index)
    part = np.clip(rel['rel_participacion'].fillna(1) * float(reales['nac_participacion'].iloc[0]), 0, 100)
    peso = (reales['censo_escrutinio'].to_numpy() * part.to_numpy() / 100).clip(min=1)
    for p in PARTIDOS_MODELO:
        nac = float(reales[f'nac_pct_{p}'].iloc[0])
        x = np.clip(rel[f'rel_{p}'].fillna(1.0) * nac, 0, 100) if nac > 0.5 else pd.Series(0.0, index=reales.index)
        imp = float(np.average(x, weights=peso))
        pred[f'pct_{p}'] = np.clip(x * nac / imp, 0, 100) if imp > 0.01 else 0.0
    pred = pred.fillna(0.0)
    reales = reales.copy(); reales[claves] = reales[claves].fillna(0.0)
    real_gan, pred_gan = reales[claves].idxmax(axis=1), pred[claves].idxmax(axis=1)
    ok = (real_gan.to_numpy() == pred_gan.to_numpy())
    censo = reales['censo_escrutinio'].to_numpy()
    mae = np.mean([np.average(np.abs(pred[c] - reales[c]), weights=censo) for c in ('pct_pp', 'pct_psoe')])
    # provincias: votos estimados = % × votos reales contabilizados previstos (peso)
    mal = 0; mal_nac = {}
    for prov, idx in reales.groupby('prov_cod').groups.items():
        w = pd.Series(peso, index=reales.index)[idx]
        votos = {p.upper(): float((pred.loc[idx, f'pct_{p}'] * w).sum() / 100) for p in PARTIDOS_MODELO}
        total = float(w.sum())
        votos = {k: round(v) for k, v in votos.items() if v > 0}
        otros = max(0, round(total - sum(votos.values())))
        oficial = RES[reales['eleccion'].iloc[0]]['provincias'][prov]
        sim = repartir(votos, oficial['escanos_total'], blancos=otros).escanos
        real = {}
        for x in oficial['partidos']:
            if x['e']: real[x['f']] = real.get(x['f'], 0) + x['e']
        ks = set(sim) | set(real)
        mal += sum(abs(sim.get(k, 0) - real.get(k, 0)) for k in ks) // 2
        for k in ks: mal_nac[k] = mal_nac.get(k, 0) + sim.get(k, 0) - real.get(k, 0)
    dif = {k: v for k, v in sorted(mal_nac.items(), key=lambda t: -abs(t[1])) if v}
    return {'modelo': nombre, 'mun_ok_%': round(100 * ok.mean(), 1), 'censo_ok_%': round(100 * np.average(ok, weights=censo), 1),
            'mae_pp_psoe': round(float(mae), 2), 'esc_mal_prov': int(mal), 'esc_mal_nac': sum(abs(v) for v in dif.values()) // 2, 'dif': dif}

for el in sys.argv[1:]:
    conv = ELECCIONES.index(el); t = time.time()
    # scikit-learn reciente falla con columnas sin ningún dato (p. ej. r2_rel_vox al entrenar hasta 2019b):
    # se quitan; no cambian el modelo, porque una columna vacía no puede usarse en ningún corte.
    ent = m.tabla[m.tabla['r1_rel_pp'].notna() & (m.tabla['conv'] <= conv - 1)]
    todas = ModeloEscenarios._columnas_entrada(m)
    m._columnas_entrada = lambda todas=todas, ent=ent: [c for c in todas if ent[c].notna().any()]
    # Partidos sin ninguna elección de entrenamiento (nuevos): no se pueden modelar; se les supone perfil plano.
    E.OBJETIVOS = [o for o in TODOS if ent[o].notna().any()]
    m.modelos = {}
    m.entrenar(hasta_conv=conv - 1)
    reales = m.tabla[(m.tabla['conv'] == conv) & m.tabla['r1_rel_pp'].notna()].copy()
    rel_modelo = m._predecir(reales)
    for o in TODOS:
        if o not in rel_modelo: rel_modelo[o] = 1.0
    nuevos = [o[4:] for o in TODOS if o not in E.OBJETIVOS]
    rel_lag = pd.DataFrame({f'rel_{p}': reales[f'r1_rel_{p}'] for p in PARTIDOS_MODELO} | {'rel_participacion': reales['r1_rel_participacion']})
    print(f'== {el}  ({len(reales)} municipios, {time.time()-t:.0f} s)  sin modelo: {nuevos}')
    for r in (evaluar(reales, rel_modelo, 'Mikel (gradient boosting)'), evaluar(reales, rel_lag, 'repetir perfil anterior')):
        print('  ', r)
