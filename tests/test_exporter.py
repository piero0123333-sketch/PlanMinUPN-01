"""Pruebas del HTML, PNG y paquete CSV de exportación."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.m01.exporter import export_results
from src.m01.visualizer import create_visualizations


def test_exporter_generates_static_and_datamine_outputs(tmp_path):
    root = Path(__file__).parents[1]
    figure_dir = tmp_path / "figures"
    visualization = create_visualizations(
        {
            "trajectory_path": root / "data" / "processed" / "drillhole_trajectory.csv",
            "assay_path": root / "data" / "processed" / "assay_xyz.csv",
            "collars_path": root / "data" / "raw" / "collar.csv",
            "html_name": "test.html",
        },
        figure_dir,
    )
    outputs = export_results(
        {
            **visualization,
            "png_name": "test.png",
            "collars_path": root / "data" / "raw" / "collar.csv",
            "survey_path": root / "data" / "raw" / "survey.csv",
            "assay_path": root / "data" / "processed" / "assay_xyz.csv",
            "lithology_path": root / "data" / "raw" / "lithology.csv",
            "density_path": root / "data" / "raw" / "density.csv",
            "alteration_path": root / "data" / "raw" / "alteration.csv",
        },
        tmp_path,
    )
    assert visualization["html_path"].is_file()
    assert outputs["png_path"].is_file()
    assert outputs["png_path"].stat().st_size > 0
    for key in (
        "collar_path",
        "survey_path",
        "assay_xyz_path",
        "drillholes_datamine_path",
        "field_mapping_path",
    ):
        assert outputs[key].is_file()

    with outputs["field_mapping_path"].open(newline="", encoding="utf-8") as stream:
        mapping = list(csv.DictReader(stream))
    assert {"internal_field", "datamine_field", "source_table", "description"} == set(mapping[0])

    with outputs["assay_xyz_path"].open(newline="", encoding="utf-8") as stream:
        assay = list(csv.DictReader(stream))
    assert assay
    assert all(row["x_mid"] and row["y_mid"] and row["z_mid"] for row in assay)

    with outputs["drillholes_datamine_path"].open(
        newline="", encoding="utf-8"
    ) as stream:
        datamine = list(csv.DictReader(stream))
    assert len(datamine) == len(assay)
    assert "density_t_m3" in datamine[0]
    assert "alteration_code" not in datamine[0]
    assert datamine[0]["LITH_CODE"]
