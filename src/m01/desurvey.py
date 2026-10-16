"""Transformación de mediciones downhole a trayectoria espacial.

Responsabilidad:
    Definir el punto de integración para convertir mediciones de survey
    expresadas como MD + azimuth + dip en una trayectoria XYZ del sondaje.
    La responsabilidad se limita al DESURVEY y aplica las convenciones y el
    método MINIMUM CURVATURE aprobados en Etapa 6; no incluye la asignación
    de coordenadas a intervalos FROM/TO.

Input esperado:
    Datos de collar y survey validados, incluyendo las variables necesarias
    para representar MD, azimuth y dip, con sus unidades y convenciones
    confirmadas en la etapa correspondiente.

Output esperado:
    Trayectoria XYZ derivada por sondaje, con trazabilidad hacia los datos de
    collar y survey utilizados, ordenada por sondaje y MD.
"""

from typing import Any, Dict, Mapping, Sequence

import numpy as np


Trajectory = Dict[str, np.ndarray]


def _as_float(rows: Sequence[Mapping[str, Any]], field: str) -> np.ndarray:
    return np.asarray([float(row[field]) for row in rows], dtype=float)


def desurvey(collar, survey) -> Trajectory:
    """Calcula estaciones XYZ mediante Minimum Curvature vectorizado.

    El primer survey de cada sondaje, con MD=0, usa la posición del collar y
    la orientación del survey como autoridad geométrica. La salida se ordena
    por ``hole_id`` y ``md`` y contiene las estaciones originales más
    ``x``, ``y`` y ``z`` derivados.
    """
    collar_by_hole = {row["hole_id"]: row for row in collar}
    if not survey:
        return {
            "hole_id": np.array([], dtype=str),
            "md": np.array([], dtype=float),
            "azimuth_deg": np.array([], dtype=float),
            "dip_deg": np.array([], dtype=float),
            "x": np.array([], dtype=float),
            "y": np.array([], dtype=float),
            "z": np.array([], dtype=float),
        }

    hole_id = np.asarray([row["hole_id"] for row in survey], dtype=str)
    md = _as_float(survey, "depth_m")
    azimuth_deg = _as_float(survey, "azimuth_deg")
    dip_deg = _as_float(survey, "dip_deg")
    order = np.lexsort((md, hole_id))
    hole_id = hole_id[order]
    md = md[order]
    azimuth_deg = azimuth_deg[order]
    dip_deg = dip_deg[order]

    azimuth = np.deg2rad(azimuth_deg)
    dip = np.deg2rad(dip_deg)
    direction = np.column_stack(
        (
            np.cos(dip) * np.sin(azimuth),
            np.cos(dip) * np.cos(azimuth),
            np.sin(dip),
        )
    )

    first = np.r_[True, hole_id[1:] != hole_id[:-1]]
    previous_direction = np.roll(direction, 1, axis=0)
    previous_md = np.roll(md, 1)
    same_hole = ~first
    dot = np.einsum("ij,ij->i", previous_direction, direction)
    dot = np.clip(dot, -1.0, 1.0)
    beta = np.arccos(dot)
    beta = np.where(same_hole, beta, 0.0)
    beta_is_zero = np.isclose(beta, 0.0, atol=1e-7)
    safe_beta = np.where(beta_is_zero, 1.0, beta)
    ratio_factor = np.where(
        beta_is_zero,
        1.0,
        (2.0 / safe_beta) * np.tan(safe_beta / 2.0),
    )

    delta_md = np.where(same_hole, md - previous_md, 0.0)
    average_direction = 0.5 * (previous_direction + direction)
    segment_delta = delta_md[:, None] * average_direction * ratio_factor[:, None]
    segment_delta[~same_hole] = 0.0

    cumulative_delta = np.cumsum(segment_delta, axis=0)
    group_number = np.cumsum(first) - 1
    first_indices = np.flatnonzero(first)
    origins = np.asarray(
        [
            [
                float(collar_by_hole[hole_id[index]]["x"]),
                float(collar_by_hole[hole_id[index]]["y"]),
                float(collar_by_hole[hole_id[index]]["z"]),
            ]
            for index in first_indices
        ],
        dtype=float,
    )
    offsets = origins - cumulative_delta[first_indices]
    xyz = cumulative_delta + offsets[group_number]

    return {
        "hole_id": hole_id,
        "md": md,
        "azimuth_deg": azimuth_deg,
        "dip_deg": dip_deg,
        "x": xyz[:, 0],
        "y": xyz[:, 1],
        "z": xyz[:, 2],
        "beta_rad": beta,
        "ratio_factor": ratio_factor,
    }
