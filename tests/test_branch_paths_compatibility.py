from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_standardization_dataframe_and_conflict_guardrails():
    with pytest.raises(TypeError, match="data frame"):
        gp.standardize_gazepoint_column_names([1, 2, 3])
    with pytest.raises(ValueError, match="no rows"):
        gp.standardize_gazepoint_column_names(pd.DataFrame({"GSR": []}))
    with pytest.raises(ValueError, match="conflict"):
        gp.standardize_gazepoint_column_names(
            pd.DataFrame({"GSR": [1.0]}),
            conflict="invalid",
        )

    dat = pd.DataFrame({"GSR": [1.0, 2.0], "EDA": [3.0, 4.0]})
    kept = gp.standardize_gazepoint_column_names(dat, conflict="keep")
    assert list(kept.columns) == ["GSR", "EDA"]
    audit = kept.attrs["gazepoint_column_standardization"]
    assert audit.loc[audit["original_name"] == "EDA", "role"].iloc[0] == "GSR"


def test_pupil_interpolation_short_time_and_early_return_paths():
    short_time = pd.DataFrame(
        {
            "time": [np.nan, 1.0, np.nan],
            "pupil_left": [3.0, np.nan, 4.0],
        }
    )
    out = gp.interpolate_gazepoint_pupil_blinks(
        short_time,
        pupil_cols="pupil_left",
        time_col="time",
    )
    assert out["pupil_left_was_interpolated"].tolist() == [False, True, False]

    complete = gp.interpolate_gazepoint_pupil_blinks(
        pd.DataFrame({"pupil_left": [3.0, 3.1, 3.2]}),
        pupil_cols="pupil_left",
    )
    assert not complete["pupil_left_was_interpolated"].any()

    too_sparse = gp.interpolate_gazepoint_pupil_blinks(
        pd.DataFrame({"pupil_left": [np.nan, 3.1, np.nan]}),
        pupil_cols="pupil_left",
    )
    assert not too_sparse["pupil_left_was_interpolated"].any()

    edge_gap = gp.interpolate_gazepoint_pupil_blinks(
        pd.DataFrame({"pupil_left": [np.nan, 3.1, 3.2]}),
        pupil_cols="pupil_left",
    )
    assert not edge_gap["pupil_left_was_interpolated"].any()


def test_pupil_interpolation_public_validation_paths():
    dat = pd.DataFrame({"pupil_left": [3.0, np.nan, 3.2], "time": [0.0, 1.0, 2.0]})
    with pytest.raises(ValueError, match="method"):
        gp.interpolate_gazepoint_pupil_blinks(dat, method="spline")
    with pytest.raises(ValueError, match="Missing columns"):
        gp.interpolate_gazepoint_pupil_blinks(dat, pupil_cols="missing_pupil")
    with pytest.raises(ValueError, match="time_col"):
        gp.interpolate_gazepoint_pupil_blinks(
            dat,
            pupil_cols="pupil_left",
            time_col="missing_time",
        )
    with pytest.raises(ValueError, match="blink_col"):
        gp.interpolate_gazepoint_pupil_blinks(
            dat,
            pupil_cols="pupil_left",
            blink_col="missing_blink",
        )


def test_mixed_model_missing_drop_and_scale_alternatives():
    dat = pd.DataFrame(
        {
            "participant": ["P1", "P2", "P3"],
            "outcome": [1.0, np.nan, 3.0],
            "age": [20.0, 30.0, 40.0],
        }
    )
    with pytest.raises(ValueError, match="Missing columns"):
        gp.prepare_gazepoint_mixed_model_data(
            dat,
            outcome_cols="missing_outcome",
        )

    out = gp.prepare_gazepoint_mixed_model_data(
        dat,
        outcome_cols="outcome",
        participant_col="participant",
        numeric_cols="age",
        drop_missing_outcomes=False,
        center_numeric=True,
        scale_numeric=False,
    )
    assert len(out) == 3
    assert "age_c" in out.columns
    assert "age_z" not in out.columns
    assert str(out["participant"].dtype) == "category"
