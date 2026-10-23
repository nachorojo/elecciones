"""Ejecuta el pipeline completo:  python -m pipeline.run"""
import sys
import time

import duckdb

from . import cera, clean, config as C, dims


def main() -> int:
    if not C.RAW.exists():
        print(f"No encuentro el Parquet bruto: {C.RAW}\n"
              "Define ELECCIONES_RAW o colócalo en ..\\datos\\db_mesas.parquet", file=sys.stderr)
        return 1
    con = duckdb.connect()
    t = time.time()
    mesas = clean.build(C.RAW, C.CLEAN_DIR, con)
    print(f"mesas.parquet  ({time.time() - t:.0f}s)  {mesas}")
    for name, path in dims.build(mesas, C.CLEAN_DIR, con).items():
        print(f"{name}.parquet  {path}")
    if cera.DEFAULT.exists():
        for path in cera.build(cera.DEFAULT, C.CLEAN_DIR, con):
            print(f"{path.name}  {path}")
    else:
        print(f"Sin ficheros de Interior en {cera.DEFAULT}: se omite el CERA", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
