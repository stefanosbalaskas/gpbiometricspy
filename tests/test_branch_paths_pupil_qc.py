from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_pupil_column_type_and_blink_guardrails():
    nonnumeric = pd.DataFrame(
        {"participant": ["P01"], "pupil_text": ["3.1"]}
    )
    with pytest.raises(TypeError, match="numeric"):
        gp.detect_gazepoint_blinks(
            nonnumeric,
            pupil_cols="pupil_text",
            id_cols="participant",
        )

    numeric = pd.DataFrame(
        {"participant": ["P01"], "pupil_left": [3.1]}
    )
    with pytest.raises(ValueError, match="extend_samples"):
        gp.detect_gazepoint_blinks(
            numeric,
            pupil_cols="pupil_left",
            id_cols="participant",
            extend_samples=-1,
        )


def test_blink_change_detection_singleton_group_path():
    data = pd.DataFrame(
        {
            "participant": ["P01", "P02"],
            "pupil_left": [3.0, 3.2],
        }
    )
    out = gp.detect_gazepoint_blinks(
        data,
        pupil_cols="pupil_left",
        id_cols="participant",
        max_pupil=np.inf,
        change_threshold=0.5,
        mask=False,
    )
    assert not out["data"]["pupil_left_blink_flag"].any()


def test_pupil_smoothing_residual_guardrails():
    data = pd.DataFrame({"pupil_left": [3.0, 3.1, 3.2]})

    with pytest.raises(ValueError, match="min_nonmissing"):
        gp.smooth_gazepoint_pupil(
            data,
            pupil_cols="pupil_left",
            window=3,
            min_nonmissing=0,
        )

    with pytest.raises(ValueError, match="larger than"):
        gp.smooth_gazepoint_pupil(
            data,
            pupil_cols="pupil_left",
            window=3,
            min_nonmissing=4,
        )


def test_missingness_plot_max_points_guardrail():
    data = pd.DataFrame({"pupil_left": [3.0, np.nan, 3.2]})
    with pytest.raises(ValueError, match="max_points"):
        gp.plot_gazepoint_missingness(
            data,
            cols="pupil_left",
            max_points=0,
        )


def test_metadata_allow_missing_ids_and_no_time_path():
    data = pd.DataFrame(
        {"participant": [None, "P02"], "value": [1.0, 2.0]}
    )
    out = gp.validate_gazepoint_metadata(
        data,
        id_cols="participant",
        allow_missing_ids=True,
    )
    assert out["status"] == "pass"


def test_metadata_time_and_unique_key_residual_paths():
    data = pd.DataFrame(
        {"participant": ["P01", "P02"], "time": [1.0, 2.0]}
    )

    multi_time = gp.validate_gazepoint_metadata(
        data,
        time_col=["time", "other"],
    )
    assert multi_time["status"] == "review"
    assert any("exactly one" in p for p in multi_time["problems"])

    missing_time = gp.validate_gazepoint_metadata(
        data,
        time_col="missing_time",
    )
    assert missing_time["status"] == "review"
    assert any("Missing time column" in p for p in missing_time["problems"])

    missing_unique = gp.validate_gazepoint_metadata(
        data,
        unique_cols="missing_unique",
    )
    assert missing_unique["status"] == "review"
    assert any("Missing unique-key columns" in p for p in missing_unique["problems"])
