"""Exportación trazable de datos derivados y entregables de M01.

Responsabilidad:
    Definir el punto de integración para persistir resultados producidos por
    los módulos de M01 en data/processed/ y outputs/, respetando los formatos
    y destinos aprobados. Este módulo no carga, valida, calcula, desurveya,
    posiciona ni visualiza datos.

Input esperado:
    Resultados estructurados generados por módulos de M01 y rutas de destino
    dentro de data/processed/ u outputs/, conforme al contrato de cada
    entregable.

Output esperado:
    Archivos derivados o entregables persistidos con trazabilidad de origen,
    sin sobrescribir data/raw/ y sin transformar silenciosamente los
    resultados recibidos.
"""

import csv
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping


def _copy_csv(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _write_mapping(path: Path) -> None:
    rows = [
        ("internal_field", "datamine_field", "source_table", "description"),
        ("hole_id", "HOLEID", "collar/survey/assay_xyz", "Drillhole identifier"),
        ("x", "X", "collar", "Local Easting collar coordinate (m)"),
        ("y", "Y", "collar", "Local Northing collar coordinate (m)"),
        ("z", "Z", "collar", "Local elevation collar coordinate (m)"),
        ("depth_m", "DEPTH", "survey", "Measured depth (m)"),
        ("x_mid", "X_MID", "assay_xyz", "Local Easting interval midpoint (m)"),
        ("y_mid", "Y_MID", "assay_xyz", "Local Northing interval midpoint (m)"),
        ("z_mid", "Z_MID", "assay_xyz", "Local elevation interval midpoint (m)"),
        ("density_sample_id", "density_sample_id", "density", "Density sample identifier"),
        ("density_t_m3", "density_t_m3", "density", "Observed density (t/m3)"),
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(rows)


_DATAMINE_HEADERS = (
    "BHID", "FROM", "TO", "ENDDEPTH", "CuPCT", "dataset_id", "project_id",
    "campaign_id", "LITH_CODE", "X", "Y", "Z", "LENGTH", "RADIUS", "A0",
    "B0",
)
_INTERVAL_JOIN_COLUMNS = {
    "hole_id", "dataset_id", "project_id", "campaign_id", "from_m", "to_m",
    "length_m",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _interval_match(
    base_row: Mapping[str, str],
    auxiliary_rows: Iterable[Mapping[str, str]],
) -> Mapping[str, str] | None:
    midpoint = (float(base_row["FROM"]) + float(base_row["TO"])) / 2.0
    matches = [
        row for row in auxiliary_rows
        if row.get("hole_id") == base_row["BHID"]
        and float(row["from_m"]) <= midpoint < float(row["to_m"])
    ]
    if len(matches) > 1:
        raise ValueError(
            "Multiple auxiliary intervals match "
            f"{base_row['BHID']} {base_row['FROM']}-{base_row['TO']}."
        )
    return matches[0] if matches else None


def _write_datamine_csv(
    assay_xyz_path: Path,
    collars_path: Path,
    lithology_path: Path,
    auxiliary_paths: Mapping[str, Path],
    target: Path,
) -> None:
    """Escribe una tabla integrada compatible con la importación de Datamine.

    Las columnas base siguen el contrato DH. Cada tabla auxiliar no vacía
    agrega sus atributos no estructurales cuando puede asociarse sin
    ambigüedad al intervalo de ensayo por sondaje y punto medio.
    """
    assay_xyz = _read_csv(assay_xyz_path)
    collars = {row["hole_id"]: row for row in _read_csv(collars_path)}
    lithology = _read_csv(lithology_path)

    lithology_by_hole: dict[str, list[dict[str, str]]] = {}
    for row in lithology:
        lithology_by_hole.setdefault(row["hole_id"], []).append(row)

    active_auxiliary: dict[str, tuple[list[dict[str, str]], list[str]]] = {}
    for table_name, path in auxiliary_paths.items():
        rows = _read_csv(path) if path.is_file() else []
        if not rows:
            continue
        fields = [
            field for field in rows[0]
            if field not in _INTERVAL_JOIN_COLUMNS
        ]
        fields = [field for field in fields if any(row.get(field) for row in rows)]
        if fields:
            active_auxiliary[table_name] = (rows, fields)

    auxiliary_fields = [
        field
        for _, (_, fields) in active_auxiliary.items()
        for field in fields
        if field not in _DATAMINE_HEADERS
    ]
    headers = list(_DATAMINE_HEADERS) + auxiliary_fields
    output_rows = []

    for source in assay_xyz:
        collar = collars[source["hole_id"]]
        midpoint = (float(source["from_m"]) + float(source["to_m"])) / 2.0
        lith_matches = [
            row for row in lithology_by_hole.get(source["hole_id"], [])
            if float(row["from_m"]) <= midpoint < float(row["to_m"])
        ]
        if len(lith_matches) > 1:
            raise ValueError(
                "Multiple lithology intervals match "
                f"{source['hole_id']} {source['from_m']}-{source['to_m']}."
            )

        row = {
            "BHID": source["hole_id"],
            "FROM": source["from_m"],
            "TO": source["to_m"],
            "ENDDEPTH": collar["final_depth_m"],
            "CuPCT": source["cu_pct"],
            "dataset_id": source["dataset_id"],
            "project_id": source["project_id"],
            "campaign_id": source["campaign_id"],
            "LITH_CODE": lith_matches[0]["lith_code"] if lith_matches else "",
            "X": source["x_mid"],
            "Y": source["y_mid"],
            "Z": source["z_mid"],
            "LENGTH": source["length_m"],
            "RADIUS": "1",
            "A0": format(float(collar["azimuth_deg"]), ".8f").rstrip("0").rstrip("."),
            "B0": format(abs(float(collar["dip_deg"])), ".8f").rstrip("0").rstrip("."),
        }
        for _, (auxiliary_rows, fields) in active_auxiliary.items():
            match = _interval_match(row, auxiliary_rows)
            for field in fields:
                row[field] = match.get(field, "") if match else ""
        output_rows.append(row)

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)


def _write_png_with_timeout(figure: Any, png_path: Path, timeout_seconds: int = 30) -> None:
    payload = figure.to_json()
    script = (
        "import asyncio, sys, plotly.io as pio, kaleido; "
        "fig=pio.from_json(open(sys.argv[1], encoding='utf-8').read()); "
        "asyncio.run(kaleido.write_fig(fig, path=sys.argv[2], opts={'format': 'png'}))"
    )
    with tempfile.TemporaryDirectory(prefix="m01_kaleido_") as temp_dir:
        payload_path = Path(temp_dir) / "figure.json"
        payload_path.write_text(payload, encoding="utf-8")
        try:
            subprocess.run(
                [sys.executable, "-c", script, str(payload_path), str(png_path)],
                check=True,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Automated PNG export exceeded {timeout_seconds} seconds; "
                "the headless renderer was stopped."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise RuntimeError(
                "Automated PNG export failed in headless mode: "
                f"{detail[:500]}"
            ) from exc


def export_results(results: Mapping[str, Any], output_path: str | Path) -> dict[str, Path]:
    """Escribe figuras estáticas y el paquete CSV trazable de Datamine."""
    output_path = Path(output_path)
    figures_dir = output_path / "figures"
    datamine_dir = output_path / "datamine"
    figures_dir.mkdir(parents=True, exist_ok=True)
    datamine_dir.mkdir(parents=True, exist_ok=True)

    if importlib.util.find_spec("kaleido") is None:
        raise RuntimeError(
            "Kaleido is required for headless PNG export. "
            "Install the declared dependency with: pip install kaleido==1.4.0"
        )
    png_path = figures_dir / results["png_name"]
    _write_png_with_timeout(results["figure"], png_path)

    _copy_csv(Path(results["collars_path"]), datamine_dir / "collar.csv")
    _copy_csv(Path(results["survey_path"]), datamine_dir / "survey.csv")
    _copy_csv(Path(results["assay_path"]), datamine_dir / "assay_xyz.csv")
    compatible_path = datamine_dir / "drillholes_datamine.csv"
    _write_datamine_csv(
        Path(results["assay_path"]),
        Path(results["collars_path"]),
        Path(results["lithology_path"]),
        {
            "density": Path(results["density_path"]),
            "alteration": Path(results["alteration_path"]),
        },
        compatible_path,
    )
    mapping_path = datamine_dir / "field_mapping.csv"
    _write_mapping(mapping_path)
    return {
        "png_path": png_path,
        "collar_path": datamine_dir / "collar.csv",
        "survey_path": datamine_dir / "survey.csv",
        "assay_xyz_path": datamine_dir / "assay_xyz.csv",
        "drillholes_datamine_path": compatible_path,
        "field_mapping_path": mapping_path,
    }
