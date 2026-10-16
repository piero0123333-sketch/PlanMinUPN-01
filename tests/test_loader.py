"""Pruebas previstas para el contrato de carga de datos de M01.

Responsabilidad:
    Reservar las pruebas computacionales del loader.py conforme al plan de
    validación aprobado en Etapa 3, sin ejecutar todavía lógica de carga.

Input esperado:
    Casos de prueba y archivos de datos controlados definidos para verificar
    el contrato de loader.py cuando se implemente en Etapa 5.

Output esperado:
    Pruebas automatizadas que verifiquen la carga de collar, survey, assay,
    lithology y density, el respeto de data/raw/ como fuente inmutable y el
    formato del resultado entregado a validator.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_loads_required_raw_sources():
    """Verifica la carga de las fuentes observadas requeridas."""
    from src.m01.loader import TABLE_FILES, load_raw_data

    raw_dir = Path(__file__).parents[1] / "data" / "raw"
    tables = load_raw_data(raw_dir)

    assert set(tables) == set(TABLE_FILES)
    assert all(tables[name] for name in TABLE_FILES)
    assert set(tables["collar"][0]) == {
        "hole_id",
        "dataset_id",
        "project_id",
        "campaign_id",
        "x",
        "y",
        "z",
        "azimuth_deg",
        "dip_deg",
        "final_depth_m",
    }
    assert all(isinstance(value, str) for value in tables["collar"][0].values())


def test_loader_preserves_raw_source_boundary():
    """Verifica que la carga no modifique data/raw/."""
    from hashlib import sha256

    from src.m01.loader import TABLE_FILES, load_raw_data

    raw_dir = Path(__file__).parents[1] / "data" / "raw"
    before = {
        file_name: sha256((raw_dir / file_name).read_bytes()).hexdigest()
        for file_name in TABLE_FILES.values()
    }

    load_raw_data(raw_dir)

    after = {
        file_name: sha256((raw_dir / file_name).read_bytes()).hexdigest()
        for file_name in TABLE_FILES.values()
    }
    assert after == before
