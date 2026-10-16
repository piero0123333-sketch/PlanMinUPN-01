"""Pruebas de DESURVEY para Minimum Curvature y datos reales representativos."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.m01.desurvey import desurvey
from src.m01.loader import load_raw_data


def _control_trajectory(azimuth_deg, dip_deg):
    collar = [
        {
            "hole_id": "CONTROL",
            "x": "1000.00",
            "y": "1000.00",
            "z": "4000.00",
        }
    ]
    survey = [
        {
            "hole_id": "CONTROL",
            "depth_m": "0.00",
            "azimuth_deg": str(azimuth_deg),
            "dip_deg": str(dip_deg),
        },
        {
            "hole_id": "CONTROL",
            "depth_m": "10.00",
            "azimuth_deg": str(azimuth_deg),
            "dip_deg": str(dip_deg),
        },
    ]
    return desurvey(collar, survey)


def test_desurvey_vertical_fixture():
    trajectory = _control_trajectory(0.0, -90.0)
    expected = np.array([1000.0, 1000.0, 3990.0])
    actual = np.array([trajectory["x"][-1], trajectory["y"][-1], trajectory["z"][-1]])
    np.testing.assert_allclose(actual, expected, atol=1e-6)


def test_desurvey_horizontal_east_fixture():
    trajectory = _control_trajectory(90.0, 0.0)
    expected = np.array([1010.0, 1000.0, 4000.0])
    actual = np.array([trajectory["x"][-1], trajectory["y"][-1], trajectory["z"][-1]])
    np.testing.assert_allclose(actual, expected, atol=1e-6)


def test_desurvey_inclined_east_fixture():
    trajectory = _control_trajectory(90.0, -45.0)
    expected = np.array([1007.071067812, 1000.0, 3992.928932188])
    actual = np.array([trajectory["x"][-1], trajectory["y"][-1], trajectory["z"][-1]])
    np.testing.assert_allclose(actual, expected, atol=1e-6)
    assert np.isclose(
        trajectory["x"][-1] - 1000.0,
        -(trajectory["z"][-1] - 4000.0),
        atol=1e-6,
    )


def test_desurvey_real_subset_preserves_trajectory_invariants():
    raw_dir = Path(__file__).parents[1] / "data" / "raw"
    data = load_raw_data(raw_dir)
    selected_holes = {"CA-C01-001", "CA-C02-001", "CA-C03-001"}
    collar = [row for row in data["collar"] if row["hole_id"] in selected_holes]
    survey = [row for row in data["survey"] if row["hole_id"] in selected_holes]

    trajectory = desurvey(collar, survey)
    collar_by_hole = {row["hole_id"]: row for row in collar}
    first = np.r_[True, trajectory["hole_id"][1:] != trajectory["hole_id"][:-1]]

    same_hole = trajectory["hole_id"][1:] == trajectory["hole_id"][:-1]
    assert np.all(
        trajectory["md"][1:][same_hole] >= trajectory["md"][:-1][same_hole]
    )
    assert np.all(np.isfinite(trajectory["x"]))
    assert np.all(np.isfinite(trajectory["y"]))
    assert np.all(np.isfinite(trajectory["z"]))
    assert np.all(trajectory["beta_rad"] >= 0.0)
    assert np.all(trajectory["ratio_factor"] >= 1.0)

    for index in np.flatnonzero(first):
        row = collar_by_hole[trajectory["hole_id"][index]]
        np.testing.assert_allclose(
            trajectory["x"][index],
            float(row["x"]),
            atol=1e-6,
        )
        np.testing.assert_allclose(
            trajectory["y"][index],
            float(row["y"]),
            atol=1e-6,
        )
        np.testing.assert_allclose(
            trajectory["z"][index],
            float(row["z"]),
            atol=1e-6,
        )

    final_depth = {
        row["hole_id"]: float(row["final_depth_m"]) for row in collar
    }
    assert all(
        md <= final_depth[hole] + 1e-9
        for hole, md in zip(trajectory["hole_id"], trajectory["md"])
    )
