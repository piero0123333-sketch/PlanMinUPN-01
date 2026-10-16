"""Carga controlada de datos observados de M01.

Responsabilidad:
    Leer los archivos de fuente inmutable requeridos por M01 y exponerlos a
    las etapas posteriores sin alterar su contenido. La carga se limita a
    collar, survey, assay, lithology y density; la definición detallada de
    columnas, tipos, unidades y controles se implementará en Etapa 5 con
    base en los datos reales y el plan de validación aprobado.

Input esperado:
    Directorio data/raw/ que contiene los archivos observados de collar,
    survey, assay, lithology y density, además de los parámetros de carga que
    se definan en el contrato de implementación.

Output esperado:
    Colección estructurada de los datos observados cargados, identificable
    por fuente y disponible para validator.py. No genera datos derivados, no
    modifica data/raw/ y no escribe resultados.
"""

from csv import DictReader
from pathlib import Path
from typing import Dict, List, Union


TABLE_FILES = {
    "collar": "collar.csv",
    "survey": "survey.csv",
    "assay": "assay.csv",
    "lithology": "lithology.csv",
    "density": "density.csv",
}

RawTable = List[Dict[str, str]]
RawData = Dict[str, RawTable]


def load_raw_data(raw_dir: Union[str, Path]) -> RawData:
    """Carga las cinco tablas observadas requeridas por M01.

    Los valores se conservan como texto, igual que en los CSV de origen. La
    función solo lee archivos y no corrige, normaliza ni escribe datos.
    """
    raw_path = Path(raw_dir)
    tables: RawData = {}

    for table_name, file_name in TABLE_FILES.items():
        file_path = raw_path / file_name
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Required raw source is missing: {file_path}"
            )
        with file_path.open("r", encoding="utf-8-sig", newline="") as stream:
            tables[table_name] = list(DictReader(stream))

    return tables
