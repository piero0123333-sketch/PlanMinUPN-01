"""Posicionamiento espacial de intervalos downhole.

Responsabilidad:
    Definir el punto de integración para asignar coordenadas XYZ a los
    intervalos geológicos o de ensayo identificados mediante FROM/TO,
    utilizando una trayectoria de sondaje ya disponible. POSITIONING es
    distinto de DESURVEY: recibe o consulta la trayectoria XYZ y ubica el
    intervalo; no convierte MD + azimuth + dip en trayectoria.

Input esperado:
    Trayectoria XYZ producida por DESURVEY y registros de intervalos
    FROM/TO provenientes de assay, lithology, density u otras fuentes
    observadas que sean incorporadas al contrato de M01. Los puntos
    intermedios se calculan mediante el arco de MINIMUM CURVATURE del tramo.

Output esperado:
    Intervalos posicionados espacialmente con coordenadas XYZ derivadas y
    trazabilidad hacia el sondaje y los límites FROM/TO originales.
"""

from typing import Any, Dict, Mapping, Sequence

import numpy as np


def _as_float(rows: Sequence[Mapping[str, Any]], field: str) -> np.ndarray:
    return np.asarray([float(row[field]) for row in rows], dtype=float)


def _position_md(
    trajectory: Mapping[str, np.ndarray],
    target_hole_id: np.ndarray,
    target_md: np.ndarray,
) -> np.ndarray:
    hole_id = trajectory["hole_id"]
    md = trajectory["md"]
    xyz = np.column_stack((trajectory["x"], trajectory["y"], trajectory["z"]))
    first = np.r_[True, hole_id[1:] != hole_id[:-1]]
    group_number = np.cumsum(first) - 1
    first_indices = np.flatnonzero(first)
    group_holes = hole_id[first_indices]
    group_lookup = {value: index for index, value in enumerate(group_holes)}
    target_group = np.asarray([group_lookup[value] for value in target_hole_id])
    span = np.max(md) + 1.0
    station_key = group_number * span + md
    target_key = target_group * span + target_md
    station_index = np.searchsorted(station_key, target_key, side="right") - 1
    station_index = np.maximum(station_index, 0)
    last_index = np.r_[first_indices[1:] - 1, len(md) - 1]
    is_last = station_index >= last_index[target_group]
    station_index = np.minimum(station_index, last_index[target_group])

    exact_station = np.isclose(md[station_index], target_md, atol=1e-12)
    next_index = np.minimum(station_index + 1, len(md) - 1)
    valid_segment = (
        ~is_last
        & (hole_id[next_index] == target_hole_id)
        & (target_md >= md[station_index])
        & (target_md <= md[next_index])
    )

    output = xyz[station_index].copy()
    if np.any(valid_segment):
        start = station_index[valid_segment]
        end = next_index[valid_segment]
        partial_md = target_md[valid_segment] - md[start]
        start_direction = np.column_stack(
            (
                np.cos(np.deg2rad(trajectory["dip_deg"][start]))
                * np.sin(np.deg2rad(trajectory["azimuth_deg"][start])),
                np.cos(np.deg2rad(trajectory["dip_deg"][start]))
                * np.cos(np.deg2rad(trajectory["azimuth_deg"][start])),
                np.sin(np.deg2rad(trajectory["dip_deg"][start])),
            )
        )
        end_direction = np.column_stack(
            (
                np.cos(np.deg2rad(trajectory["dip_deg"][end]))
                * np.sin(np.deg2rad(trajectory["azimuth_deg"][end])),
                np.cos(np.deg2rad(trajectory["dip_deg"][end]))
                * np.cos(np.deg2rad(trajectory["azimuth_deg"][end])),
                np.sin(np.deg2rad(trajectory["dip_deg"][end])),
            )
        )
        dot = np.einsum("ij,ij->i", start_direction, end_direction)
        beta = np.arccos(np.clip(dot, -1.0, 1.0))
        beta_is_zero = np.isclose(beta, 0.0, atol=1e-7)
        safe_beta = np.where(beta_is_zero, 1.0, beta)
        ratio_factor = np.where(
            beta_is_zero,
            1.0,
            (2.0 / safe_beta) * np.tan(safe_beta / 2.0),
        )
        theta = np.where(
            beta_is_zero,
            0.0,
            beta * partial_md / (md[end] - md[start]),
        )
        safe_sin_beta = np.where(beta_is_zero, 1.0, np.sin(beta))
        arc_integral = (
            (
                (np.cos(beta - theta) - np.cos(beta))[:, None]
                * start_direction
                + (1.0 - np.cos(theta))[:, None] * end_direction
            )
            * (
                partial_md / np.where(beta_is_zero, 1.0, beta * safe_sin_beta)
            )[:, None]
        )
        linear_increment = partial_md[:, None] * start_direction
        output[valid_segment] = xyz[start] + np.where(
            beta_is_zero[:, None],
            linear_increment,
            arc_integral,
        )

    output[exact_station] = xyz[station_index[exact_station]]
    return output


def position_intervals(
    trajectory: Mapping[str, np.ndarray],
    intervals: Sequence[Mapping[str, Any]],
) -> Dict[str, np.ndarray]:
    """Posiciona FROM, MID y TO usando Minimum Curvature por tramo.

    Los puntos intermedios se calculan sobre el arco de Minimum Curvature del
    tramo que los contiene; no se interpola linealmente entre coordenadas XYZ
    de estaciones.
    """
    if not intervals:
        empty = np.array([], dtype=float)
        return {
            "hole_id": np.array([], dtype=str),
            "from_m": empty,
            "mid_m": empty,
            "to_m": empty,
            "from_x": empty,
            "from_y": empty,
            "from_z": empty,
            "mid_x": empty,
            "mid_y": empty,
            "mid_z": empty,
            "to_x": empty,
            "to_y": empty,
            "to_z": empty,
        }

    hole_id = np.asarray([row["hole_id"] for row in intervals], dtype=str)
    from_md = _as_float(intervals, "from_m")
    to_md = _as_float(intervals, "to_m")
    mid_md = 0.5 * (from_md + to_md)
    target_holes = np.repeat(hole_id, 3)
    target_md = np.column_stack((from_md, mid_md, to_md)).reshape(-1)
    positioned = _position_md(trajectory, target_holes, target_md).reshape(
        (-1, 3, 3)
    )
    return {
        "hole_id": hole_id,
        "from_m": from_md,
        "mid_m": mid_md,
        "to_m": to_md,
        "from_x": positioned[:, 0, 0],
        "from_y": positioned[:, 0, 1],
        "from_z": positioned[:, 0, 2],
        "mid_x": positioned[:, 1, 0],
        "mid_y": positioned[:, 1, 1],
        "mid_z": positioned[:, 1, 2],
        "to_x": positioned[:, 2, 0],
        "to_y": positioned[:, 2, 1],
        "to_z": positioned[:, 2, 2],
    }
