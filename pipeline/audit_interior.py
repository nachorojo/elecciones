"""Audita mesas.parquet contra los ficheros oficiales 09 (mesas) de Interior (infoelectoral).

    python -m pipeline.audit_interior [carpeta_congreso]

Lee ..\\datos\\infoelectoral\\congreso\\02AAAAMM_MESA\\09..DAT (ancho fijo; diseño en FICHEROS.doc)
y compara mesa a mesa con mesas.parquet. Las pseudo-mesas del CERA (voto exterior; municipio 999)
no están en mesas.parquet: se cuentan aparte, por provincia (se excluyen las filas de total
autonómico/nacional, con provincia 99).
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

from . import config as C

DEFAULT = C.REPO.parent / "datos" / "infoelectoral" / "congreso"
# carpeta -> valor de `eleccion` en mesas.parquet
ELECCIONES = {"199603": "1996", "200003": "2000", "200403": "2004", "200803": "2008", "201111": "2011",
              "201512": "2015", "201606": "2016", "201904": "2019a", "201911": "2019b", "202307": "2023"}


def read_09(path: Path):
    rows = []
    with open(path, encoding="latin-1", newline="") as f:
        for ln in f:
            ln = ln.rstrip("\r\n")
            if len(ln) < 101:
                continue
            g = lambda a, b: ln[a - 1:b]  # posiciones 1-based, como en FICHEROS.doc
            rows.append((g(12, 13), g(14, 16), g(17, 18), g(19, 22).strip(), g(23, 23),
                         int(g(31, 37)), int(g(52, 58)), int(g(59, 65)),
                         int(g(66, 72)), int(g(73, 79)), int(g(80, 86)), g(101, 101)))
    return rows


def main(base: Path = DEFAULT, mesas: Path | None = None) -> int:
    con = duckdb.connect()
    con.execute("create table oficial (eleccion varchar, prov varchar, mun varchar, dis varchar, sec varchar, mesa varchar, "
                "censo_esc bigint, av1 bigint, av2 bigint, blancos bigint, nulos bigint, cand bigint, oficial varchar)")
    cols = ["eleccion", "prov", "mun", "dis", "sec", "mesa", "censo_esc", "av1", "av2", "blancos", "nulos", "cand", "oficial"]
    data = []
    for per, el in ELECCIONES.items():
        f = base / f"02{per}_MESA" / f"0902{per[2:]}.DAT"
        data += [(el,) + r for r in read_09(f)]
    df = pd.DataFrame(data, columns=cols)  # carga en bloque: executemany fila a fila tardaba >5 min
    con.execute("insert into oficial select * from df")
    mesas = mesas or C.CLEAN_DIR / "mesas.parquet"
    con.execute(f"create view m as select * from read_parquet('{mesas}')")
    con.execute("create view o as select prov || mun || dis || sec as seccion_id, * from oficial where mun <> '999'")
    res = con.execute("""
        select o.eleccion, count(*) n_of, count(m.mesa_id) emparejadas,
               count(*) filter (where m.votantes = o.cand + o.blancos + o.nulos
                                  and m.censo_escrutinio = o.censo_esc
                                  and m.votos_candidaturas = o.cand
                                  and m.votantes_avance_1 = o.av1 and m.votantes_avance_2 = o.av2) identicas,
               (select count(*) from m where m.eleccion = o.eleccion) n_nuestras
        from o left join m on m.eleccion = o.eleccion and m.seccion_id = o.seccion_id and m.mesa = o.mesa
        group by o.eleccion order by min(array_position(['1996','2000','2004','2008','2011','2015','2016','2019a','2019b','2023'], o.eleccion))
    """).fetchall()
    cera = {e: (n, c, v) for e, n, c, v in con.execute(
        "select eleccion, count(*), sum(censo_esc), sum(cand) from oficial where mun = '999' and prov <> '99' group by 1").fetchall()}
    ok = True
    print(f"{'eleccion':9}{'oficial':>9}{'emparej.':>10}{'identicas':>11}{'nuestras':>10} | CERA: prov  electores  votos")
    for e, n_of, emp, ide, nuestras in res:
        n, c, v = cera.get(e, (0, 0, 0))
        print(f"{e:9}{n_of:>9}{emp:>10}{ide:>11}{nuestras:>10} | {n:>10}{c:>11}{v:>8}")
        ok &= (n_of == emp == ide == nuestras)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT))
