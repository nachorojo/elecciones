"""Limpieza de db_mesas.parquet -> data/clean/mesas.parquet.

Qué hace:
  * tipa las 198 columnas (el bruto es todo VARCHAR); los ids se quedan en texto;
  * quita meta_* y split_sugerido (ver config.py);
  * recalcula desde los votos participacion y los pct_* de partidos y bloques;
  * añade banderas (flag_*) para los problemas que no se pueden "arreglar"
    sino solo marcar. NO borra ninguna mesa: filtrar es decisión de quien consume.

Denominadores de los porcentajes recalculados (verificados contra el bruto:
coinciden salvo en las mesas con problema):
  pct_<partido|bloque>  = 100 * votos / votos_candidaturas   (el bruto usa la suma de bloques)
  pct_blancos           = 100 * votos_blancos / votos_validos
  pct_nulos             = 100 * votos_nulos / votantes
  participacion         = 100 * votantes / censo_escrutinio
Los agregados que dependen de ellos (pct_izquierda_total, indice_izq_der, ret*, tend*,
*_z) se dejan como vienen en el bruto: NO están recalculados.
"""
from __future__ import annotations

import duckdb

from . import config as C


def _q(c: str) -> str:
    return f'"{c}"'


def _expr(c: str) -> str:
    q = _q(c)
    if c in C.CODE_COLS or c in C.TEXT_COLS:
        return f"cast({q} as varchar)"
    if c in C.DATE_COLS:
        return f"cast({q} as date)"
    if c in C.BOOL_TEXT_COLS:
        return f"({q} = 'True')"
    if c in C.BOOL_01_COLS:
        return f"(cast({q} as double) = 1)"
    if c in C.INT_COLS:
        return f"cast(cast({q} as double) as bigint)"
    return f"cast({q} as double)"


def _pct(num: str, den: str) -> str:
    """Opera sobre las columnas BRUTAS (texto), de ahí el cast."""
    return f"100.0 * cast({_q(num)} as double) / nullif(cast({_q(den)} as double), 0)"


def raw_columns(con: duckdb.DuckDBPyConnection, raw) -> list[str]:
    return [r[0] for r in con.execute(f"describe select * from read_parquet('{raw}')").fetchall()]


def kept_columns(cols: list[str]) -> list[str]:
    return [c for c in cols if c not in C.DROP_COLS and not c.startswith(C.DROP_PREFIXES)]


def check_int_lossless(con, raw, cols: list[str]) -> None:
    """Un cast double->bigint redondea en silencio: comprobar que no pierde nada."""
    for c in cols:
        if c not in C.INT_COLS:
            continue
        n = con.execute(
            f"select count(*) from read_parquet('{raw}') "
            f"where {_q(c)} is not null and cast({_q(c)} as double) <> round(cast({_q(c)} as double))"
        ).fetchone()[0]
        if n:
            raise ValueError(f"{c}: {n} valores no enteros; no puede ir en INT_COLS")


def build_sql(raw, cols: list[str]) -> str:
    cols = kept_columns(cols)
    recalculated = {
        "participacion": _pct("votantes", "censo_escrutinio"),
        "pct_blancos": _pct("votos_blancos", "votos_validos"),
        "pct_nulos": _pct("votos_nulos", "votantes"),
        **{f"pct_{p}": _pct(f"votos_{p}", "votos_candidaturas") for p in C.PARTIDOS + C.BLOQUES},
    }
    select = []
    for c in cols:
        if c == "municipio":
            # El nombre del bruto es inconsistente entre elecciones: no usarlo para agrupar.
            select.append(f"{_expr(c)} as municipio_nombre_original")
        elif c in recalculated:
            select.append(f"{recalculated[c]} as {_q(c)}")
        else:
            select.append(f"{_expr(c)} as {_q(c)}")
    typed = ",\n    ".join(select)

    bloques_sum = " + ".join(f"coalesce(votos_{b}, 0)" for b in C.BLOQUES)
    futuro = " or ".join(f"coalesce({d}, 0) > 0" for d in C.DESFASE_COLS)
    desfase_max = ", ".join(f"coalesce({d}, 0)" for d in C.DESFASE_COLS)
    return f"""
with typed as (
  select
    {typed}
  from read_parquet('{raw}')
),
distritos as (
  select municipio_id, conv_idx, list_sort(list(distinct distrito)) as ds
  from typed group by 1, 2
)
select
  t.*,
  -- 1) secciones con sufijo de letra (Zaragoza 1996-2004): seccion_id no mide 10 dígitos
  not regexp_full_match(t.seccion_id, '[0-9]{{10}}') as flag_seccion_con_sufijo,
  -- 7) false = el municipio cambió su lista de distritos respecto a la elección anterior
  --    (el mismo código de sección puede ser otro territorio). NULL = sin elección anterior.
  case when p.ds is null then null else d.ds = p.ds end as territorio_comparable_prev,
  -- 8) los bloques no suman votos_candidaturas (2015: partido en dos bloques; 1996/2000: faltan votos)
  (({bloques_sum}) <> t.votos_candidaturas) as flag_bloques_no_cuadran,
  -- 10) avances imposibles: el acumulado baja o supera a los votantes finales
  (t.votantes_avance_2 > t.votantes or t.votantes_avance_1 > t.votantes_avance_2) as flag_avance_imposible,
  (t.votantes_avance_1 = t.votantes_avance_2) as flag_avances_iguales,
  -- aritmética: votantes por encima del censo del escrutinio
  (t.votantes > t.censo_escrutinio) as flag_votantes_gt_censo,
  -- 6) años de desfase de la variable socioeconómica más desfasada. SIN SIGNO: el bruto no
  --    guarda si el dato es anterior o posterior a la elección.
  greatest({desfase_max}) as socio_desfase_max,
  -- Solo se afirma "dato del futuro" donde la dirección está documentada (1996-2004).
  -- En 2023 hay desfases de 1-2 años cuya dirección NO está verificada.
  (t.anio <= 2004 and ({futuro})) as flag_socio_futuro
from typed t
join distritos d using (municipio_id, conv_idx)
left join distritos p on p.municipio_id = t.municipio_id and p.conv_idx = t.conv_idx - 1
"""


def build(raw=C.RAW, out_dir=C.CLEAN_DIR, con: duckdb.DuckDBPyConnection | None = None):
    """Genera mesas.parquet y devuelve su ruta."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "mesas.parquet"
    con = con or duckdb.connect()
    cols = raw_columns(con, raw)
    check_int_lossless(con, raw, cols)
    sql = build_sql(raw, cols)
    con.execute(
        f"copy ({sql} order by t.conv_idx, t.mesa_id) to '{out}' "
        "(format parquet, compression zstd)"
    )
    return out
