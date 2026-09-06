import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_pupil_blinks_reject_missing_explicit_time_column():
    data = pd.DataFrame({"LPD": [3.0, 3.1, 3.2]})
    with pytest.raises(ValueError, match="time_col"):
        gp.detect_gazepoint_pupil_blinks(
            data,
            pupil_cols="LPD",
            time_col="missing_time",
        )


def test_pupil_blinks_reject_missing_explicit_validity_column():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 0.1, 0.2],
            "LPD": [3.0, 3.1, 3.2],
        }
    )
    with pytest.raises(ValueError, match="Validity column not found"):
        gp.detect_gazepoint_pupil_blinks(
            data,
            pupil_cols="LPD",
            time_col="time_s",
            validity_cols="missing_validity",
        )


def test_pupil_blinks_numeric_validity_marks_zero_and_nonfinite_invalid():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 0.1, 0.2],
            "LPD": [3.0, 3.1, 3.2],
            "LPV": [1.0, 0.0, np.nan],
        }
    )
    flags = gp.detect_gazepoint_pupil_blinks(
        data,
        pupil_cols="LPD",
        time_col="time_s",
        validity_cols="LPV",
        return_="flags",
    )
    assert flags.tolist() == [False, True, True]


def test_pupil_blinks_boolean_validity_marks_false_and_missing_invalid():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 0.1, 0.2],
            "LPD": [3.0, 3.1, 3.2],
            "LPV": pd.Series([True, False, pd.NA], dtype="boolean"),
        }
    )
    flags = gp.detect_gazepoint_pupil_blinks(
        data,
        pupil_cols="LPD",
        time_col="time_s",
        validity_cols="LPV",
        return_="flags",
    )
    assert flags.tolist() == [False, True, True]


def test_pupil_blinks_short_invalid_run_is_below_minimum_interval_length():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 0.1, 0.2],
            "LPD": [3.0, 0.0, 3.1],
        }
    )
    intervals = gp.detect_gazepoint_pupil_blinks(
        data,
        pupil_cols="LPD",
        time_col="time_s",
        min_blink_samples=2,
    )
    assert intervals.empty


def test_filter_gaze_rejects_nonfinite_screen_bounds():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 0.1],
            "x": [0.2, 0.3],
            "y": [0.4, 0.5],
        }
    )
    with pytest.raises(ValueError, match="screen_bounds"):
        gp.filter_gazepoint_gaze(
            data,
            x_col="x",
            y_col="y",
            time_col="time_s",
            screen_bounds=(0.0, 1.0, np.nan, 1.0),
        )


def test_filter_gaze_singleton_groups_skip_velocity_difference_path():
    data = pd.DataFrame(
        {
            "group": ["A", "B"],
            "time_s": [0.0, 1.0],
            "x": [0.2, 0.8],
            "y": [0.3, 0.7],
        }
    )
    out = gp.filter_gazepoint_gaze(
        data,
        x_col="x",
        y_col="y",
        time_col="time_s",
        group_cols="group",
        max_velocity=0.01,
    )
    assert out["gaze_valid"].tolist() == [True, True]
    assert out["gaze_velocity"].isna().all()
