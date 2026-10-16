"""Pruebas previstas para el contrato de validación de datos de M01.

Responsabilidad:
    Reservar las pruebas computacionales del validator.py conforme al plan
    de validación aprobado en Etapa 3, sin ejecutar todavía lógica de
    validación.

Input esperado:
    Colecciones de datos cargados y casos controlados que representen los
    controles, hallazgos y estados esperados del plan de validación de M01.

Output esperado:
    Pruebas automatizadas que verifiquen el reporte estructurado de
    validación, la identificación explícita de errores y la aptitud de los
    datos para continuar el flujo sin correcciones silenciosas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_validates_loaded_sources_against_plan():
    """Verifica los controles definidos por el plan de validación."""
    from src.m01.loader import load_raw_data
    from src.m01.validator import validate_loaded_data

    raw_dir = Path(__file__).parents[1] / "data" / "raw"
    result = validate_loaded_data(load_raw_data(raw_dir))

    assert set(result) == {"findings", "summary", "is_valid"}
    assert set(result["summary"]) == {"ERROR", "WARNING", "INFO", "records_checked"}
    assert result["is_valid"] is True
    assert result["summary"]["ERROR"] == 0


def test_reports_validation_findings_explicitly():
    """Verifica que los hallazgos queden identificados y trazables."""
    from src.m01.loader import load_raw_data
    from src.m01.validator import validate_loaded_data

    raw_dir = Path(__file__).parents[1] / "data" / "raw"
    data = load_raw_data(raw_dir)
    data["survey"] = list(data["survey"])
    data["survey"][1] = dict(data["survey"][1])
    data["survey"][1]["depth_m"] = "-1.000000000"

    result = validate_loaded_data(data)
    findings = result["findings"]

    assert result["is_valid"] is False
    finding = next(item for item in findings if item["rule_id"] == "M01_SURVEY_NON_NEGATIVE")
    assert finding["severity"] == "ERROR"
    assert finding["table"] == "survey"
    assert finding["field"] == "depth_m"
    assert finding["observed_value"] == "-1.000000000"
