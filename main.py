"""Orquestador mínimo de M01 — PlanMinUPN.

Responsabilidad:
    Coordinar, en el orden definido por el flujo de M01, las llamadas a los
    módulos de carga, validación, desurvey, positioning, visualización y
    exportación. Este archivo no calcula, no valida datos, no transforma
    trayectorias, no posiciona intervalos y no dibuja resultados.

Input esperado:
    Rutas y parámetros de ejecución que serán definidos por el contrato de
    integración de M01, junto con los datos observados de collar, survey,
    assay, lithology y density ubicados en data/raw/ y el plan de validación
    aprobado en Etapa 3.

Output esperado:
    Flujo coordinado entre módulos, sin producir resultados mineros por sí
    mismo. Los datos derivados deberán dirigirse a data/processed/ y los
    entregables a outputs/ mediante los módulos responsables.
"""

from pathlib import Path
import csv
import json

from src.m01.desurvey import desurvey
from src.m01.exporter import export_results
from src.m01.loader import load_raw_data
from src.m01.positioning import position_intervals
from src.m01.validator import validate_loaded_data
from src.m01.visualizer import create_visualizations


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _trajectory_rows(trajectory: dict) -> list[dict]:
    return [
        {key: value[index].item() if hasattr(value[index], "item") else value[index]
         for key, value in trajectory.items()}
        for index in range(len(trajectory["md"]))
    ]


def _interval_rows(source_rows: list[dict], positioned: dict) -> list[dict]:
    output = []
    for index, source in enumerate(source_rows):
        row = dict(source)
        for prefix in ("from", "mid", "to"):
            for axis in ("x", "y", "z"):
                row[f"{axis}_{prefix}"] = float(positioned[f"{prefix}_{axis}"][index])
        output.append(row)
    return output


def main() -> dict:
    """Orquesta el pipeline M01 sin contener cálculos geométricos."""
    project_dir = Path(__file__).resolve().parent
    data = load_raw_data(project_dir / "data" / "raw")
    validation = validate_loaded_data(data)
    trajectory = desurvey(data["collar"], data["survey"])
    processed_dir = project_dir / "data" / "processed"
    trajectory_path = processed_dir / "drillhole_trajectory.csv"
    assay_path = processed_dir / "assay_xyz.csv"
    _write_rows(trajectory_path, _trajectory_rows(trajectory))
    positioned = position_intervals(trajectory, data["assay"])
    _write_rows(assay_path, _interval_rows(data["assay"], positioned))

    manifest = json.loads(
        (project_dir / "data" / "raw" / "release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    dataset = manifest["dataset_id"]
    release = manifest["release_id"]
    figures_dir = project_dir / "outputs" / "figures"
    visualization = create_visualizations(
        {
            "trajectory_path": trajectory_path,
            "assay_path": assay_path,
            "collars_path": project_dir / "data" / "raw" / "collar.csv",
            "lithology_path": project_dir / "data" / "raw" / "lithology.csv",
            "density_path": project_dir / "data" / "raw" / "density.csv",
            "alteration_path": project_dir / "data" / "raw" / "alteration.csv",
            "html_name": f"m01_drillholes_3d_{dataset}_{release}.html",
        },
        figures_dir,
    )
    exported = export_results(
        {
            **visualization,
            "png_name": f"m01_drillholes_3d_{dataset}_{release}.png",
            "collars_path": project_dir / "data" / "raw" / "collar.csv",
            "survey_path": project_dir / "data" / "raw" / "survey.csv",
            "assay_path": assay_path,
            "lithology_path": project_dir / "data" / "raw" / "lithology.csv",
            "density_path": project_dir / "data" / "raw" / "density.csv",
            "alteration_path": project_dir / "data" / "raw" / "alteration.csv",
        },
        project_dir / "outputs",
    )
    return {"validation": validation, **visualization, **exported}


if __name__ == "__main__":
    main()
