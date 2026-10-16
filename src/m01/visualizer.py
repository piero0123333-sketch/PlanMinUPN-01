"""Representación visual de datos y resultados espaciales de M01.

Responsabilidad:
    Definir el punto de integración para generar visualizaciones de los datos
    observados y de los productos espaciales de M01, sin calcular, validar,
    desurveyar ni posicionar información.

Input esperado:
    Datos observados o derivados previamente procesados por los módulos de
    M01, junto con parámetros de visualización que sean definidos y
    aprobados para los entregables.

Output esperado:
    Figuras o representaciones visuales dirigidas a outputs/figures/ u otro
    destino de entregables que se confirme en el contrato de implementación.
    No modifica data/raw/ y no altera los datos recibidos.
"""

import csv
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, Iterable, Mapping, Sequence

import plotly.graph_objects as go
from plotly.io import to_html


LITHOLOGY_COLORS = {
    "AIR": "#9E9E9E",
    "BRX": "#D95F02",
    "DIO": "#1B9E77",
    "POR": "#7570B3",
    "REG": "#E7298A",
    "UNKNOWN": "#444444",
}
GRADE_COLORS = {
    "Baja": "#2C7BB6",
    "Media": "#FDAE61",
    "Alta": "#D7191C",
}
DENSITY_COLORS = {
    "Baja": "#A6CEE3",
    "Media": "#1F78B4",
    "Alta": "#08306B",
}
ALTERATION_COLORS = {
    "UNKNOWN": "#444444",
    "LOW": "#B2DF8A",
    "MEDIUM": "#33A02C",
    "HIGH": "#006D2C",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _numeric(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _add_numeric_display(interval: dict[str, str], field: str) -> None:
    value = _numeric(interval.get(field))
    interval[field] = "" if value is None else format(value, ".6f").rstrip("0").rstrip(".")
    interval[f"_{field}_value"] = value


def _equal_interval_limits(values: Sequence[float | None]) -> dict[str, float]:
    valid = sorted(value for value in values if value is not None)
    if not valid:
        return {}
    minimum = valid[0]
    maximum = valid[-1]
    step = (maximum - minimum) / 3.0
    return {
        "low": minimum + step,
        "high": minimum + (2.0 * step),
    }


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile without numeric values.")
    position = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _percentile_limits(values: Sequence[float | None]) -> dict[str, float]:
    valid = [value for value in values if value is not None]
    if not valid:
        return {}
    return {
        "low": _percentile(valid, 1.0),
        "high": _percentile(valid, 99.0),
    }


def _grade(value: float | None, limits: Mapping[str, float]) -> str | None:
    if value is None or not limits:
        return None
    if value <= limits["low"]:
        return "Baja"
    if value <= limits["high"]:
        return "Media"
    return "Alta"


def _format_number(value: float | None) -> str:
    if value is None:
        return "N/D"
    return format(value, ".2f").rstrip("0").rstrip(".")


def _grade_ranges(
    values: Sequence[float | None],
    limits: Mapping[str, float],
) -> dict[str, str]:
    valid = [value for value in values if value is not None]
    if not valid or not limits:
        return {}
    minimum = min(valid)
    maximum = max(valid)
    return {
        "Baja": f"{_format_number(minimum)} – {_format_number(limits['low'])}",
        "Media": f"{_format_number(limits['low'])} – {_format_number(limits['high'])}",
        "Alta": f"{_format_number(limits['high'])} – {_format_number(maximum)}",
    }


def _enrich_intervals(
    intervals: list[dict[str, str]],
    lithology_path: str | Path | None,
    density_path: str | Path | None,
    alteration_path: str | Path | None,
) -> list[dict[str, str]]:
    sources = []
    for path in (lithology_path, density_path, alteration_path):
        if path is not None:
            rows = _read_csv(Path(path))
            if rows:
                sources.append(rows)
    for interval in intervals:
        midpoint = (float(interval["from_m"]) + float(interval["to_m"])) / 2.0
        for rows in sources:
            matches = [
                row for row in rows
                if row.get("hole_id") == interval["hole_id"]
                and float(row["from_m"]) <= midpoint < float(row["to_m"])
            ]
            if len(matches) > 1:
                raise ValueError(
                    "Multiple auxiliary intervals match "
                    f"{interval['hole_id']} {interval['from_m']}-{interval['to_m']}."
                )
            if matches:
                for field, value in matches[0].items():
                    if field not in {
                        "hole_id", "dataset_id", "project_id", "campaign_id",
                        "from_m", "to_m", "length_m",
                    }:
                        interval[field] = value
    for interval in intervals:
        _add_numeric_display(interval, "cu_pct")
        _add_numeric_display(interval, "mo_pct")
        _add_numeric_display(interval, "au_gt")
        _add_numeric_display(interval, "density_t_m3")
    return intervals


def _trajectory_traces(rows: Sequence[Mapping[str, str]]) -> Iterable[go.Scatter3d]:
    by_hole: Dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        by_hole.setdefault(row["hole_id"], []).append(row)
    for hole_id, hole_rows in by_hole.items():
        yield go.Scatter3d(
            x=[float(row["x"]) for row in hole_rows],
            y=[float(row["y"]) for row in hole_rows],
            z=[float(row["z"]) for row in hole_rows],
            mode="lines",
            name=f"Trajectory {hole_id}",
            legendgroup="trajectories",
            showlegend=hole_id == next(iter(by_hole)),
            line={"width": 3},
            customdata=[
                [row["md"], row["azimuth_deg"], row["dip_deg"]]
                for row in hole_rows
            ],
            hovertemplate=(
                f"{hole_id}<br>MD=%{{customdata[0]:.3f}} m"
                "<br>Azimuth=%{customdata[1]:.3f}°"
                "<br>Dip=%{customdata[2]:.3f}°"
                "<br>X=%{x:.3f}<br>Y=%{y:.3f}<br>Z=%{z:.3f}"
                "<extra></extra>"
            ),
        )


def build_figure(
    trajectory_path: str | Path,
    assay_path: str | Path,
    collars_path: str | Path,
    interval_layer: str = "assay",
    lithology_path: str | Path | None = None,
    density_path: str | Path | None = None,
    alteration_path: str | Path | None = None,
) -> go.Figure:
    """Construye la figura leyendo únicamente resultados ya procesados."""
    trajectory = _read_csv(Path(trajectory_path))
    intervals = _enrich_intervals(
        _read_csv(Path(assay_path)),
        lithology_path,
        density_path,
        alteration_path,
    )
    collars = _read_csv(Path(collars_path))
    figure = go.Figure()
    for trace in _trajectory_traces(trajectory):
        figure.add_trace(trace)
    figure.add_trace(
        go.Scatter3d(
            x=[float(row["x"]) for row in collars],
            y=[float(row["y"]) for row in collars],
            z=[float(row["z"]) for row in collars],
            mode="markers",
            name="Collars",
            marker={"size": 5, "symbol": "diamond", "color": "black"},
            text=[row["hole_id"] for row in collars],
            hovertemplate="Collar %{text}<br>X=%{x:.3f}<br>Y=%{y:.3f}<br>Z=%{z:.3f}<extra></extra>",
        )
    )
    base_trace_count = len(figure.data)
    layer_traces: dict[str, list[go.Scatter3d]] = defaultdict(list)

    def add_interval_trace(
        layer: str,
        name: str,
        rows: Sequence[Mapping[str, str]],
        color: str,
    ) -> None:
        customdata = [
            [
                row["hole_id"],
                row["from_m"],
                row["to_m"],
                row.get("_cu_pct_value"),
                row.get("_mo_pct_value"),
                row.get("_au_gt_value"),
                row.get("_density_range", ""),
                row.get("lith_code", "UNKNOWN") or "UNKNOWN",
                row.get("alteration_code", "") or "N/D",
            ]
            for row in rows
        ]
        trace = go.Scatter3d(
            x=[float(row["x_mid"]) for row in rows],
            y=[float(row["y_mid"]) for row in rows],
            z=[float(row["z_mid"]) for row in rows],
            mode="markers",
            name=name,
            legendgroup=layer,
            visible=layer == "lithology",
            marker={"size": 4, "color": color},
            customdata=customdata,
            hovertemplate=(
                f"{interval_layer.title()} %{{customdata[0]}}"
                "<br>From=%{customdata[1]} m"
                "<br>To=%{customdata[2]} m"
                "<br>Cu=%{customdata[3]} %"
                "<br>Mo=%{customdata[4]} %"
                "<br>Au=%{customdata[5]} g/t"
                "<br>Density range=%{customdata[6]}"
                "<br>Lithology=%{customdata[7]}"
                "<br>Alteration=%{customdata[8]}"
                "<br>X=%{x:.3f}<br>Y=%{y:.3f}<br>Z=%{z:.3f}"
                "<extra></extra>"
            ),
        )
        figure.add_trace(trace)
        layer_traces[layer].append(trace)

    by_lithology: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in intervals:
        by_lithology[row.get("lith_code", "UNKNOWN") or "UNKNOWN"].append(row)
    for lithology, lith_rows in sorted(by_lithology.items()):
        add_interval_trace(
            "lithology",
            f"Lithology: {lithology}",
            lith_rows,
            LITHOLOGY_COLORS.get(lithology, LITHOLOGY_COLORS["UNKNOWN"]),
        )

    cu_values = [row.get("_cu_pct_value") for row in intervals]
    cu_percentiles = _percentile_limits(cu_values)
    numeric_rows = [
        row for row in intervals if row.get("_cu_pct_value") is not None
    ]
    if numeric_rows:
        customdata = [
            [
                row["hole_id"],
                row["from_m"],
                row["to_m"],
                row.get("_cu_pct_value"),
                row.get("_mo_pct_value"),
                row.get("_au_gt_value"),
                row.get("_density_range", ""),
                row.get("lith_code", "UNKNOWN") or "UNKNOWN",
                row.get("alteration_code", "") or "N/D",
            ]
            for row in numeric_rows
        ]
        figure.add_trace(
            go.Scatter3d(
                x=[float(row["x_mid"]) for row in numeric_rows],
                y=[float(row["y_mid"]) for row in numeric_rows],
                z=[float(row["z_mid"]) for row in numeric_rows],
                mode="markers",
                name="Ley Cu (continua, p1–p99)",
                legendgroup="grades",
                visible=False,
                customdata=customdata,
                marker={
                    "size": 4,
                    "color": [row["_cu_pct_value"] for row in numeric_rows],
                    "colorscale": "Viridis",
                    "cmin": cu_percentiles["low"],
                    "cmax": cu_percentiles["high"],
                    "colorbar": {"title": "Cu (%)"},
                },
                hovertemplate=(
                    f"{interval_layer.title()} %{{customdata[0]}}"
                    "<br>From=%{customdata[1]} m"
                    "<br>To=%{customdata[2]} m"
                    "<br>Cu=%{customdata[3]:.6f} %"
                    "<br>Mo=%{customdata[4]} %"
                    "<br>Au=%{customdata[5]} g/t"
                    "<br>Density range=%{customdata[6]}"
                    "<br>Lithology=%{customdata[7]}"
                    "<br>Alteration=%{customdata[8]}"
                    "<br>X=%{x:.3f}<br>Y=%{y:.3f}<br>Z=%{z:.3f}"
                    "<extra></extra>"
                ),
            )
        )
        layer_traces["grades"].append(figure.data[-1])

    density_limits = _equal_interval_limits(
        [row.get("_density_t_m3_value") for row in intervals],
    )
    density_ranges = _grade_ranges(
        [row.get("_density_t_m3_value") for row in intervals],
        density_limits,
    )
    by_density: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in intervals:
        grade = _grade(row.get("_density_t_m3_value"), density_limits)
        if grade:
            row["_density_range"] = density_ranges[grade]
            by_density[grade].append(row)
    for grade in ("Baja", "Media", "Alta"):
        if by_density[grade]:
            add_interval_trace(
                "density",
                f"Densidad: {density_ranges[grade]} t/m³",
                by_density[grade],
                DENSITY_COLORS[grade],
            )

    by_alteration: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in intervals:
        alteration = row.get("alteration_code", "").strip()
        if alteration:
            by_alteration[alteration].append(row)
    for alteration, alteration_rows in sorted(by_alteration.items()):
        add_interval_trace(
            "alteration",
            f"Alteración: {alteration}",
            alteration_rows,
            ALTERATION_COLORS.get(alteration.upper(), "#6A3D9A"),
        )

    layer_names = list(layer_traces)
    total_traces = len(figure.data)
    always_visible = [True] * base_trace_count
    buttons = []
    for layer in layer_names:
        visible = always_visible + [
            trace in layer_traces[layer] for trace in figure.data[base_trace_count:]
        ]
        buttons.append({
            "label": {
                "lithology": "Mostrar Litología",
                "grades": "Mostrar Leyes",
                "density": "Mostrar Densidades",
                "alteration": "Mostrar Alteración",
            }.get(layer, f"Mostrar {layer.title()}"),
            "method": "update",
            "args": [{"visible": visible}],
        })
    buttons.append({
        "label": "Mostrar todo",
        "method": "update",
        "args": [{"visible": [True] * total_traces}],
    })
    figure.update_layout(
        title="M01 Drillhole Exploration — Local Cartesian Coordinates",
        scene={
            "xaxis_title": "X — Easting local (m)",
            "yaxis_title": "Y — Northing local (m)",
            "zaxis_title": "Z — Elevation local (m)",
            "aspectmode": "data",
        },
        legend={"title": "Leyendas · intervalos de valores"},
        updatemenus=[{
            "type": "dropdown",
            "direction": "down",
            "x": 0.01,
            "y": 1.16,
            "xanchor": "left",
            "yanchor": "top",
            "buttons": buttons,
            "showactive": True,
        }, {
            "type": "buttons",
            "direction": "right",
            "x": 0.25,
            "y": 1.16,
            "xanchor": "left",
            "yanchor": "top",
            "buttons": [{
                "label": "Mostrar leyendas",
                "method": "relayout",
                "args": [{"showlegend": True}],
            }, {
                "label": "Ocultar leyendas",
                "method": "relayout",
                "args": [{"showlegend": False}],
            }],
            "showactive": True,
        }],
        annotations=[{
            "text": f"<b>Archivo</b><br>{Path(assay_path).name}",
            "showarrow": False,
            "x": 0.01,
            "y": 1.19,
            "xref": "paper",
            "yref": "paper",
            "xanchor": "left",
            "yanchor": "bottom",
        }, {
            "text": "<b>3D</b>",
            "showarrow": False,
            "x": 0.25,
            "y": 1.19,
            "xref": "paper",
            "yref": "paper",
            "xanchor": "left",
            "yanchor": "bottom",
        }, {
            "text": "<b>Leyendas</b>",
            "showarrow": False,
            "x": 0.52,
            "y": 1.19,
            "xref": "paper",
            "yref": "paper",
            "xanchor": "left",
            "yanchor": "bottom",
        }],
        template="plotly_white",
    )
    return figure


def _build_analysis_figures(
    intervals: Sequence[Mapping[str, str]],
) -> tuple[go.Figure, go.Figure]:
    numeric_rows = [
        row for row in intervals if row.get("_cu_pct_value") is not None
    ]
    histogram = go.Figure(
        go.Histogram(
            x=[row["_cu_pct_value"] for row in numeric_rows],
            nbinsx=30,
            marker={"color": "#2C7BB6"},
            name="Cu",
            hovertemplate="Cu=%{x:.4f} %<br>Intervalos=%{y}<extra></extra>",
        )
    )
    histogram.update_layout(
        title="Distribución de leyes Cu",
        xaxis_title="Cu (%)",
        yaxis_title="Número de intervalos",
        template="plotly_white",
    )

    by_hole: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in numeric_rows:
        by_hole[row["hole_id"]].append(row)
    profile = go.Figure()
    for hole_id, rows in sorted(by_hole.items()):
        profile.add_trace(
            go.Scatter(
                x=[row["_cu_pct_value"] for row in rows],
                y=[
                    (float(row["from_m"]) + float(row["to_m"])) / 2.0
                    for row in rows
                ],
                mode="lines+markers",
                name=hole_id,
                customdata=[
                    [row["from_m"], row["to_m"], row.get("lith_code", "N/D")]
                    for row in rows
                ],
                hovertemplate=(
                    f"{hole_id}<br>Cu=%{{x:.6f}} %"
                    "<br>From=%{customdata[0]} m"
                    "<br>To=%{customdata[1]} m"
                    "<br>Lithology=%{customdata[2]}"
                    "<extra></extra>"
                ),
            )
        )
    profile.update_layout(
        title="Perfil down-hole: ley Cu vs profundidad",
        xaxis_title="Cu (%)",
        yaxis_title="Profundidad media (m)",
        yaxis={"autorange": "reversed"},
        template="plotly_white",
    )
    return histogram, profile


def create_visualizations(data, output_dir):
    """Genera el HTML interactivo autocontenido de M01."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    figure = build_figure(
        data["trajectory_path"],
        data["assay_path"],
        data["collars_path"],
        data.get("interval_layer", "assay"),
        data.get("lithology_path"),
        data.get("density_path"),
        data.get("alteration_path"),
    )
    html_path = output_dir / data["html_name"]
    intervals = _enrich_intervals(
        _read_csv(Path(data["assay_path"])),
        data.get("lithology_path"),
        data.get("density_path"),
        data.get("alteration_path"),
    )
    histogram, profile = _build_analysis_figures(intervals)
    dashboard = "\n".join([
        "<html><head><meta charset='utf-8'><title>M01 Visualizador</title></head><body>",
        "<h1>Visualizador M01</h1>",
        "<h2>Vista 3D</h2>",
        to_html(figure, include_plotlyjs=True, full_html=False),
        "<h2>Histograma de leyes</h2>",
        to_html(histogram, include_plotlyjs=False, full_html=False),
        "<h2>Perfil down-hole</h2>",
        to_html(profile, include_plotlyjs=False, full_html=False),
        "</body></html>",
    ])
    html_path.write_text(dashboard, encoding="utf-8")
    return {
        "figure": figure,
        "html_path": html_path,
        "histogram_figure": histogram,
        "profile_figure": profile,
    }
