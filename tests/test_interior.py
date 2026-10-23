"""mesas.parquet debe coincidir mesa a mesa con los ficheros oficiales de Interior (las 10 elecciones)."""
import pytest

from pipeline import audit_interior


def test_mesas_identicas_a_interior(con, clean_dir):
    if not audit_interior.DEFAULT.exists():
        pytest.skip(f"No hay ficheros de Interior en {audit_interior.DEFAULT}")
    assert audit_interior.main(mesas=clean_dir / "mesas.parquet") == 0
