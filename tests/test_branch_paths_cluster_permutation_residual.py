from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def _minimal_cluster_result():
    return {
        "clusters": pd.DataFrame(),
        "timewise": pd.DataFrame(),
        "null_distribution": np.array([0.0, 0.5, 1.0]),
        "settings": {},
    }


def _valid_export_data():
    return pd.DataFrame(
        {
            "participant": ["P01", "P01", "P02", "P02"],
            "condition": ["A", "B", "A", "B"],
            "time": [1.0, 1.0, 1.0, 1.0],
            "value": [1.0, 1.1, 0.9, 1.0],
        }
    )


def test_cluster_public_dataframe_type_guard():
    with pytest.raises(TypeError, match="data frame"):
        gp.audit_gazepoint_timecourse_grid(
            [],
            "participant",
            "condition",
            "time",
            "value",
        )


def test_cluster_null_plot_explicit_observed_mass_path():
    result = {
        "null_distribution": np.array([0.1, 0.2, 0.4]),
        "clusters": pd.DataFrame(),
    }
    fig = gp.plot_gazepoint_cluster_null_distribution(
        result,
        observed_mass=0.3,
        bins=3,
    )
    assert fig.axes


def test_cluster_result_component_collision_guard(tmp_path):
    out = tmp_path / "component_collision"
    out.mkdir()
    (out / "case_clusters.csv").write_text("existing\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="File exists"):
        gp.export_gazepoint_cluster_results(
            _minimal_cluster_result(),
            out,
            prefix="case",
            overwrite=False,
        )


def test_cluster_result_report_collision_guard(tmp_path):
    out = tmp_path / "report_collision"
    out.mkdir()
    (out / "case_report.txt").write_text("existing\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="File exists"):
        gp.export_gazepoint_cluster_results(
            _minimal_cluster_result(),
            out,
            prefix="case",
            overwrite=False,
        )


def test_external_cluster_export_rejects_missing_values():
    bad = pd.DataFrame(
        {
            "participant": ["P01", "P01"],
            "condition": ["A", "B"],
            "time": [1.0, 1.0],
            "value": [1.0, np.nan],
        }
    )
    with pytest.raises(ValueError, match="no missing values"):
        gp.export_gazepoint_permuco_cluster_input(
            bad,
            "value",
            "time",
            "condition",
            "participant",
        )


def test_external_cluster_export_collision_guard(tmp_path):
    out = tmp_path / "external_collision"
    out.mkdir()
    (out / "case_long.csv").write_text("existing\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        gp.export_gazepoint_permuco_cluster_input(
            _valid_export_data(),
            "value",
            "time",
            "condition",
            "participant",
            path=out,
            prefix="case",
            overwrite=False,
        )


def test_mne_cluster_export_requires_two_conditions():
    one_condition = pd.DataFrame(
        {
            "participant": ["P01", "P02"],
            "condition": ["A", "A"],
            "time": [1.0, 1.0],
            "value": [1.0, 0.9],
        }
    )
    with pytest.raises(ValueError, match="exactly two conditions"):
        gp.export_gazepoint_mne_cluster_input(
            one_condition,
            "value",
            "time",
            "condition",
            "participant",
        )
