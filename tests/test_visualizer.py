"""Pruebas del visualizador 3D usando artefactos reales del pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.m01.visualizer import _equal_interval_limits, _percentile_limits, build_figure


def test_visualizer_contains_required_layers():
    root = Path(__file__).parents[1]
    figure = build_figure(
        root / "data" / "processed" / "drillhole_trajectory.csv",
        root / "data" / "processed" / "assay_xyz.csv",
        root / "data" / "raw" / "collar.csv",
        lithology_path=root / "data" / "raw" / "lithology.csv",
        density_path=root / "data" / "raw" / "density.csv",
        alteration_path=root / "data" / "raw" / "alteration.csv",
    )
    names = {trace.name for trace in figure.data}
    assert "Collars" in names
    assert "Lithology: REG" in names
    assert sum(name.startswith("Trajectory ") for name in names) >= 1
    assert all(len(trace.x) == len(trace.y) == len(trace.z) for trace in figure.data)
    assert figure.layout.scene.xaxis.title.text == "X — Easting local (m)"
    interval_traces = [
        trace for trace in figure.data if trace.name == "Lithology: REG"
    ]
    assert interval_traces
    assert "Density range=" in interval_traces[0].hovertemplate
    assert figure.layout.updatemenus
    assert {button["label"] for button in figure.layout.updatemenus[0].buttons} >= {
        "Mostrar Litología",
        "Mostrar Leyes",
        "Mostrar Densidades",
        "Mostrar todo",
    }
    assert "Ley Cu (continua, p1–p99)" in names
    assay_trace = next(
        trace for trace in figure.data
        if trace.name == "Ley Cu (continua, p1–p99)"
    )
    assert assay_trace.marker.colorscale[0][1] == "#440154"
    assert assay_trace.marker.colorscale[-1][1] == "#fde725"
    assert assay_trace.marker.colorbar.title.text == "Cu (%)"
    density_names = sorted(name for name in names if name.startswith("Densidad:"))
    assert density_names == [
        "Densidad: 2.27 – 2.43 t/m³",
        "Densidad: 2.43 – 2.59 t/m³",
        "Densidad: 2.59 – 2.75 t/m³",
    ]
    assert len(figure.layout.updatemenus) >= 2
    assert {button["label"] for button in figure.layout.updatemenus[1].buttons} == {
        "Mostrar leyendas",
        "Ocultar leyendas",
    }
    assert figure.layout.legend.title.text == "Leyendas · intervalos de valores"


def test_numeric_ranges_use_ordered_equal_intervals():
    limits = _equal_interval_limits([0.0, 0.3, 0.9])
    assert limits["low"] == 0.3
    assert limits["high"] == 0.6
    assert limits["low"] < limits["high"]


def test_assay_color_scale_uses_percentiles_one_to_ninety_nine():
    limits = _percentile_limits([0.0, 1.0, 2.0, 100.0])
    assert limits["low"] == 0.03
    assert abs(limits["high"] - 97.06) < 1e-12
