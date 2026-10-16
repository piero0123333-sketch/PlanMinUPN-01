"""Pruebas de posicionamiento curvo y caso límite sin curvatura."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.m01.desurvey import desurvey
from src.m01.positioning import position_intervals


def test_positioning_uses_curvature_for_intermediate_points():
    collar = [{"hole_id": "CURVED", "x": "0.0", "y": "0.0", "z": "0.0"}]
    survey = [
        {
            "hole_id": "CURVED",
            "depth_m": "0.0",
            "azimuth_deg": "0.0",
            "dip_deg": "0.0",
        },
        {
            "hole_id": "CURVED",
            "depth_m": "10.0",
            "azimuth_deg": "90.0",
            "dip_deg": "0.0",
        },
    ]
    trajectory = desurvey(collar, survey)
    positioned = position_intervals(
        trajectory,
        [{"hole_id": "CURVED", "from_m": "0.0", "to_m": "10.0"}],
    )

    linear_mid = 0.5 * np.array(
        [trajectory["x"][-1], trajectory["y"][-1], trajectory["z"][-1]]
    )
    actual_mid = np.array(
        [positioned["mid_x"][0], positioned["mid_y"][0], positioned["mid_z"][0]]
    )
    assert not np.allclose(actual_mid, linear_mid, atol=1e-9)
    assert np.isclose(positioned["mid_m"][0], 5.0, atol=1e-12)


def test_positioning_zero_curvature_matches_linear_interpolation():
    collar = [{"hole_id": "STRAIGHT", "x": "1000.0", "y": "1000.0", "z": "4000.0"}]
    survey = [
        {
            "hole_id": "STRAIGHT",
            "depth_m": "0.0",
            "azimuth_deg": "90.0",
            "dip_deg": "-45.0",
        },
        {
            "hole_id": "STRAIGHT",
            "depth_m": "10.0",
            "azimuth_deg": "90.0",
            "dip_deg": "-45.0",
        },
    ]
    trajectory = desurvey(collar, survey)
    positioned = position_intervals(
        trajectory,
        [{"hole_id": "STRAIGHT", "from_m": "2.0", "to_m": "8.0"}],
    )
    expected_mid = 0.5 * np.array(
        [
            positioned["from_x"][0] + positioned["to_x"][0],
            positioned["from_y"][0] + positioned["to_y"][0],
            positioned["from_z"][0] + positioned["to_z"][0],
        ]
    )
    actual_mid = np.array(
        [positioned["mid_x"][0], positioned["mid_y"][0], positioned["mid_z"][0]]
    )
    np.testing.assert_allclose(actual_mid, expected_mid, atol=1e-6)
    assert positioned["mid_m"][0] == 5.0


def test_positioning_treats_numerically_straight_segments_as_linear():
    collar = [{"hole_id": "NEAR_STRAIGHT", "x": "0.0", "y": "0.0", "z": "0.0"}]
    survey = [
        {
            "hole_id": "NEAR_STRAIGHT",
            "depth_m": "0.0",
            "azimuth_deg": "90.0",
            "dip_deg": "-45.0",
        },
        {
            "hole_id": "NEAR_STRAIGHT",
            "depth_m": "40.0",
            "azimuth_deg": "90.0000000001",
            "dip_deg": "-45.0000000001",
        },
    ]
    positioned = position_intervals(
        desurvey(collar, survey),
        [{"hole_id": "NEAR_STRAIGHT", "from_m": "0.0", "to_m": "2.0"}],
    )
    assert positioned["mid_x"][0] > positioned["from_x"][0]
