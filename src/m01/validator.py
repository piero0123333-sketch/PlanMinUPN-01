"""Validación computacional de los datos de entrada de M01.

Responsabilidad:
    Aplicar el plan de validación aprobado en Etapa 3 sobre los datos
    observados entregados por loader.py, verificando su aptitud para las
    etapas posteriores y reportando hallazgos de forma trazable. Este módulo
    no corrige silenciosamente datos, no realiza desurvey, no posiciona
    intervalos y no interpreta resultados mineros.

Input esperado:
    Colección estructurada producida por loader.py, con las fuentes collar,
    survey, assay, lithology y density, junto con los criterios del plan de
    validación aprobado en Etapa 3.

Output esperado:
    Resultado estructurado de validación que identifique controles
    ejecutados, hallazgos, errores y estado de aptitud de los datos para
    continuar el flujo. No modifica data/raw/ ni produce coordenadas
    derivadas.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import isclose
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SEVERITIES = ("ERROR", "WARNING", "INFO")

EXPECTED_COLUMNS = {
    "collar": (
        "hole_id", "dataset_id", "project_id", "campaign_id", "x", "y", "z",
        "azimuth_deg", "dip_deg", "final_depth_m",
    ),
    "survey": (
        "hole_id", "dataset_id", "project_id", "campaign_id", "depth_m",
        "azimuth_deg", "dip_deg",
    ),
    "assay": (
        "sample_id", "hole_id", "dataset_id", "project_id", "campaign_id",
        "from_m", "to_m", "length_m", "cu_pct", "mo_pct", "au_gt",
    ),
    "lithology": (
        "hole_id", "dataset_id", "project_id", "campaign_id", "from_m",
        "to_m", "length_m", "lith_code",
    ),
    "density": (
        "density_sample_id", "hole_id", "dataset_id", "project_id",
        "campaign_id", "from_m", "to_m", "length_m", "density_t_m3",
    ),
}

NON_NULL_COLUMNS = EXPECTED_COLUMNS
INTERVAL_TABLES = ("assay", "lithology", "density")
NUMERIC_COLUMNS = {
    "collar": ("x", "y", "z", "azimuth_deg", "dip_deg", "final_depth_m"),
    "survey": ("depth_m", "azimuth_deg", "dip_deg"),
    "assay": ("from_m", "to_m", "length_m", "cu_pct", "mo_pct", "au_gt"),
    "lithology": ("from_m", "to_m", "length_m"),
    "density": ("from_m", "to_m", "length_m", "density_t_m3"),
}

# These are the controls represented in T1_audit_summary. Controls explicitly
# marked NOT_IMPLEMENTED in that evidence are intentionally absent.
DEFAULT_VALIDATION_PLAN = {
    "schema": True,
    "missing_data": True,
    "relationships": True,
    "interval_order": True,
    "interval_non_negative": True,
    "interval_length": True,
    "interval_final_depth": True,
    "interval_duplicates": True,
    "interval_overlaps": True,
    "survey_start_depth": True,
    "survey_duplicates": True,
    "survey_non_negative_depth": True,
    "survey_final_depth": True,
    "survey_zero_orientation": True,
}


@dataclass(frozen=True)
class Finding:
    """Trazabilidad mínima de una observación de validación."""

    rule_id: str
    severity: str
    table: str
    row_number: Optional[int]
    field: Optional[str]
    observed_value: Any
    message: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "table": self.table,
            "row_number": self.row_number,
            "field": self.field,
            "observed_value": self.observed_value,
            "message": self.message,
        }


def validate_loaded_data(
    data: Mapping[str, Sequence[Mapping[str, str]]],
    validation_plan: Optional[Mapping[str, bool]] = None,
) -> Dict[str, Any]:
    """Valida las tablas cargadas con los controles aprobados para M01.

    ``validation_plan`` puede desactivar explícitamente un control mediante
    ``False``; si no se entrega, se utiliza la transcripción reproducible de
    los controles observados en T1_audit_summary.
    """
    plan = dict(DEFAULT_VALIDATION_PLAN)
    if validation_plan is not None:
        plan.update(validation_plan)

    findings: List[Finding] = []
    findings.extend(_check_required_tables(data))

    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        rows = data.get(table_name, ())
        if plan["schema"]:
            findings.extend(_check_schema(table_name, rows, expected_columns))
            findings.extend(_check_numeric_types(table_name, rows))
        if plan["missing_data"]:
            findings.extend(_check_missing_data(table_name, rows, expected_columns))

    collar = data.get("collar", ())
    if plan["relationships"]:
        findings.extend(_check_relationships(collar, data))

    if plan["interval_order"] or plan["interval_non_negative"]:
        findings.extend(_check_interval_bounds(data, plan))
    if plan["interval_length"]:
        findings.extend(_check_interval_lengths(data))
    if plan["interval_final_depth"]:
        findings.extend(_check_interval_final_depth(data, collar))
    if plan["interval_duplicates"] or plan["interval_overlaps"]:
        findings.extend(_check_interval_structure(data, plan))

    if (
        plan["survey_start_depth"]
        or plan["survey_duplicates"]
        or plan["survey_non_negative_depth"]
        or plan["survey_final_depth"]
        or plan["survey_zero_orientation"]
    ):
        findings.extend(_check_survey(data, plan))

    counts = Counter(f.severity for f in findings)
    return {
        "findings": [finding.as_dict() for finding in findings],
        "summary": {
            "ERROR": counts.get("ERROR", 0),
            "WARNING": counts.get("WARNING", 0),
            "INFO": counts.get("INFO", 0),
            "records_checked": sum(len(rows) for rows in data.values()),
        },
        "is_valid": counts.get("ERROR", 0) == 0,
    }


def _finding(
    rule_id: str,
    table: str,
    message: str,
    observed_value: Any,
    row_number: Optional[int] = None,
    field: Optional[str] = None,
    severity: str = "ERROR",
) -> Finding:
    if severity not in SEVERITIES:
        raise ValueError(f"Unsupported finding severity: {severity}")
    return Finding(
        rule_id=rule_id,
        severity=severity,
        table=table,
        row_number=row_number,
        field=field,
        observed_value=observed_value,
        message=message,
    )


def _check_required_tables(data: Mapping[str, Sequence[Mapping[str, str]]]) -> List[Finding]:
    return [
        _finding(
            "M01_REQUIRED_TABLE",
            table_name,
            "Required table is missing from loaded data.",
            None,
        )
        for table_name in EXPECTED_COLUMNS
        if table_name not in data
    ]


def _check_schema(
    table_name: str,
    rows: Sequence[Mapping[str, str]],
    expected_columns: Iterable[str],
) -> List[Finding]:
    expected = set(expected_columns)
    observed = set(rows[0]) if rows else expected
    findings = []
    for column in sorted(expected - observed):
        findings.append(
            _finding(
                "M01_SCHEMA",
                table_name,
                "Required column is missing.",
                None,
                field=column,
            )
        )
    return findings


def _check_missing_data(
    table_name: str,
    rows: Sequence[Mapping[str, str]],
    expected_columns: Iterable[str],
) -> List[Finding]:
    findings = []
    for row_number, row in enumerate(rows, start=2):
        for column in expected_columns:
            value = row.get(column)
            if value is None or value == "":
                findings.append(
                    _finding(
                        "M01_MISSING_DATA",
                        table_name,
                        "Non-null field is empty.",
                        value,
                        row_number=row_number,
                        field=column,
                    )
                )
    return findings


def _check_numeric_types(
    table_name: str,
    rows: Sequence[Mapping[str, str]],
) -> List[Finding]:
    findings = []
    for row_number, row in enumerate(rows, start=2):
        for column in NUMERIC_COLUMNS.get(table_name, ()):
            value = row.get(column)
            if value not in (None, ""):
                try:
                    float(value)
                except (TypeError, ValueError):
                    findings.append(
                        _finding(
                            "M01_SCHEMA_TYPE",
                            table_name,
                            "Declared numeric field is not numeric.",
                            value,
                            row_number=row_number,
                            field=column,
                        )
                    )
    return findings


def _check_relationships(
    collar: Sequence[Mapping[str, str]],
    data: Mapping[str, Sequence[Mapping[str, str]]],
) -> List[Finding]:
    collar_holes = {row.get("hole_id") for row in collar}
    findings = []
    for table_name in ("survey", "assay", "lithology", "density"):
        for row_number, row in enumerate(data.get(table_name, ()), start=2):
            hole_id = row.get("hole_id")
            if hole_id not in collar_holes:
                findings.append(
                    _finding(
                        "M01_RELATIONSHIP",
                        table_name,
                        "hole_id does not exist in collar.",
                        hole_id,
                        row_number=row_number,
                        field="hole_id",
                    )
                )
    return findings


def _number(row: Mapping[str, str], field: str) -> Optional[float]:
    value = row.get(field)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check_interval_bounds(
    data: Mapping[str, Sequence[Mapping[str, str]]],
    plan: Mapping[str, bool],
) -> List[Finding]:
    findings = []
    for table_name in INTERVAL_TABLES:
        for row_number, row in enumerate(data.get(table_name, ()), start=2):
            from_m = _number(row, "from_m")
            to_m = _number(row, "to_m")
            if from_m is None or to_m is None:
                continue
            if plan["interval_order"] and from_m > to_m:
                findings.append(
                    _finding(
                        "M01_INTERVAL_ORDER",
                        table_name,
                        "from_m must be less than or equal to to_m.",
                        {"from_m": row.get("from_m"), "to_m": row.get("to_m")},
                        row_number=row_number,
                        field="from_m/to_m",
                    )
                )
            if plan["interval_non_negative"] and (from_m < 0 or to_m < 0):
                findings.append(
                    _finding(
                        "M01_INTERVAL_NON_NEGATIVE",
                        table_name,
                        "Interval depths must not be negative.",
                        {"from_m": row.get("from_m"), "to_m": row.get("to_m")},
                        row_number=row_number,
                        field="from_m/to_m",
                    )
                )
    return findings


def _check_interval_lengths(
    data: Mapping[str, Sequence[Mapping[str, str]]],
) -> List[Finding]:
    findings = []
    for table_name in INTERVAL_TABLES:
        for row_number, row in enumerate(data.get(table_name, ()), start=2):
            from_m = _number(row, "from_m")
            to_m = _number(row, "to_m")
            length_m = _number(row, "length_m")
            if from_m is None or to_m is None or length_m is None:
                continue
            if not isclose(to_m - from_m, length_m, rel_tol=0.0, abs_tol=1e-9):
                findings.append(
                    _finding(
                        "M01_INTERVAL_LENGTH",
                        table_name,
                        "length_m must equal to_m - from_m.",
                        {
                            "from_m": row.get("from_m"),
                            "to_m": row.get("to_m"),
                            "length_m": row.get("length_m"),
                        },
                        row_number=row_number,
                        field="length_m",
                    )
                )
    return findings


def _check_interval_final_depth(
    data: Mapping[str, Sequence[Mapping[str, str]]],
    collar: Sequence[Mapping[str, str]],
) -> List[Finding]:
    final_depths = {
        row.get("hole_id"): _number(row, "final_depth_m") for row in collar
    }
    findings = []
    for table_name in INTERVAL_TABLES:
        for row_number, row in enumerate(data.get(table_name, ()), start=2):
            final_depth = final_depths.get(row.get("hole_id"))
            to_m = _number(row, "to_m")
            if final_depth is not None and to_m is not None and to_m > final_depth:
                findings.append(
                    _finding(
                        "M01_INTERVAL_FINAL_DEPTH",
                        table_name,
                        "Interval end exceeds collar final_depth_m.",
                        {"to_m": row.get("to_m"), "final_depth_m": str(final_depth)},
                        row_number=row_number,
                        field="to_m",
                    )
                )
    return findings


def _check_interval_structure(
    data: Mapping[str, Sequence[Mapping[str, str]]],
    plan: Mapping[str, bool],
) -> List[Finding]:
    findings = []
    for table_name in INTERVAL_TABLES:
        rows = data.get(table_name, ())
        by_hole = defaultdict(list)
        for row_number, row in enumerate(rows, start=2):
            by_hole[row.get("hole_id")].append((row_number, row))
        for hole_id, hole_rows in by_hole.items():
            seen = set()
            ordered = sorted(
                hole_rows,
                key=lambda item: (_number(item[1], "from_m") or 0.0, item[0]),
            )
            previous_to = None
            for row_number, row in ordered:
                key = (
                    row.get("from_m"),
                    row.get("to_m"),
                    row.get("hole_id"),
                )
                if plan["interval_duplicates"] and key in seen:
                    findings.append(
                        _finding(
                            "M01_INTERVAL_DUPLICATE",
                            table_name,
                            "Duplicate interval detected for hole_id.",
                            key,
                            row_number=row_number,
                            field="from_m/to_m",
                        )
                    )
                seen.add(key)
                from_m = _number(row, "from_m")
                to_m = _number(row, "to_m")
                if (
                    plan["interval_overlaps"]
                    and previous_to is not None
                    and from_m is not None
                    and from_m < previous_to
                ):
                    findings.append(
                        _finding(
                            "M01_INTERVAL_OVERLAP",
                            table_name,
                            "Interval overlaps a preceding interval for hole_id.",
                            {"hole_id": hole_id, "from_m": row.get("from_m")},
                            row_number=row_number,
                            field="from_m",
                        )
                    )
                if to_m is not None:
                    previous_to = max(previous_to or to_m, to_m)
    return findings


def _check_survey(
    data: Mapping[str, Sequence[Mapping[str, str]]],
    plan: Mapping[str, bool],
) -> List[Finding]:
    findings = []
    collar_by_hole = {row.get("hole_id"): row for row in data.get("collar", ())}
    by_hole = defaultdict(list)
    for row_number, row in enumerate(data.get("survey", ()), start=2):
        by_hole[row.get("hole_id")].append((row_number, row))

    for hole_id, rows in by_hole.items():
        depths = [_number(row, "depth_m") for _, row in rows]
        if plan["survey_start_depth"] and depths and depths[0] != 0:
            findings.append(
                _finding(
                    "M01_SURVEY_START_DEPTH",
                    "survey",
                    "First survey station must start at depth zero.",
                    rows[0][1].get("depth_m"),
                    row_number=rows[0][0],
                    field="depth_m",
                )
            )
        seen_depths = set()
        for row_number, row in rows:
            depth = _number(row, "depth_m")
            if plan["survey_duplicates"] and depth in seen_depths:
                findings.append(
                    _finding(
                        "M01_SURVEY_DUPLICATE",
                        "survey",
                        "Duplicate survey station depth detected.",
                        row.get("depth_m"),
                        row_number=row_number,
                        field="depth_m",
                    )
                )
            seen_depths.add(depth)
            if plan["survey_non_negative_depth"] and depth is not None and depth < 0:
                findings.append(
                    _finding(
                        "M01_SURVEY_NON_NEGATIVE",
                        "survey",
                        "Survey depth must not be negative.",
                        row.get("depth_m"),
                        row_number=row_number,
                        field="depth_m",
                    )
                )
            final_depth = _number(collar_by_hole.get(hole_id, {}), "final_depth_m")
            if (
                plan["survey_final_depth"]
                and final_depth is not None
                and depth is not None
                and depth > final_depth
            ):
                findings.append(
                    _finding(
                        "M01_SURVEY_FINAL_DEPTH",
                        "survey",
                        "Survey depth exceeds collar final_depth_m.",
                        {"depth_m": row.get("depth_m"), "final_depth_m": str(final_depth)},
                        row_number=row_number,
                        field="depth_m",
                    )
                )

        first_row_number, first_row = min(
            rows,
            key=lambda item: (_number(item[1], "depth_m") is None, _number(item[1], "depth_m") or 0.0),
        )
        if (
            plan["survey_zero_orientation"]
            and rows
            and _number(first_row, "depth_m") == 0
        ):
            collar_row = collar_by_hole.get(hole_id)
            if collar_row:
                for field in ("azimuth_deg", "dip_deg"):
                    if not isclose(
                        float(first_row[field]),
                        float(collar_row[field]),
                        rel_tol=0.0,
                        abs_tol=1e-9,
                    ):
                        findings.append(
                            _finding(
                                "M01_SURVEY_ZERO_ORIENTATION",
                                "survey",
                                "Zero-depth survey orientation must match collar.",
                                first_row.get(field),
                                row_number=first_row_number,
                                field=field,
                            )
                        )
    return findings
