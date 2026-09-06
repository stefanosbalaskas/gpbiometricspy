import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_hrv_segments_skip_all_nonfinite_time_group():
    data = pd.DataFrame(
        {
            "participant": ["P01", "P01"],
            "time_s": [np.nan, np.nan],
            "rr_ms": [800.0, 820.0],
        }
    )

    out = gp.flag_gazepoint_hrv_segments(
        data,
        rr_col="rr_ms",
        time_col="time_s",
        group_cols="participant",
        window_s=None,
    )

    assert out.empty


def test_hrv_segments_singleton_skips_successive_change_branch():
    data = pd.DataFrame({"time_s": [0.0], "rr_ms": [800.0]})

    out = gp.flag_gazepoint_hrv_segments(
        data,
        rr_col="rr_ms",
        time_col="time_s",
        window_s=None,
        min_beats=1,
        min_duration_s=0,
        max_artifact_prop=1.0,
    )

    assert len(out) == 1
    assert int(out.loc[0, "n_large_successive_changes"]) == 0
    assert bool(out.loc[0, "quality_ok"])


def test_signal_lag_matrix_rejects_fewer_than_two_signals():
    data = pd.DataFrame({"time_s": [0.0, 1.0], "x": [1.0, 2.0]})

    with pytest.raises(ValueError, match="At least two numeric"):
        gp.compute_gazepoint_signal_lag_matrix(
            data,
            signal_cols=["x"],
            time_col="time_s",
            min_overlap=1,
        )


def test_signal_lag_matrix_skips_group_without_positive_time_step():
    data = pd.DataFrame(
        {
            "participant": ["A", "A", "B", "B", "B"],
            "time_s": [0.0, 0.0, 0.0, 1.0, 2.0],
            "x": [1.0, 2.0, 1.0, 2.0, 3.0],
            "y": [2.0, 3.0, 3.0, 2.0, 1.0],
        }
    )

    out = gp.compute_gazepoint_signal_lag_matrix(
        data,
        signal_cols=["x", "y"],
        time_col="time_s",
        group_cols="participant",
        max_lag_s=0,
        min_overlap=2,
    )

    assert out["participant"].tolist() == ["B"]


def test_signal_lag_matrix_skips_pair_with_insufficient_overlap():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 1.0, 2.0, 3.0],
            "x": [1.0, np.nan, np.nan, np.nan],
            "y": [1.0, 2.0, 3.0, 4.0],
        }
    )

    out = gp.compute_gazepoint_signal_lag_matrix(
        data,
        signal_cols=["x", "y"],
        time_col="time_s",
        max_lag_s=0,
        min_overlap=2,
    )

    assert out.empty
