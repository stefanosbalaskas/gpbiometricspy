import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_hrv_segments_skip_group_with_no_finite_time_and_continue():
    data = pd.DataFrame(
        {
            "group": ["A", "A", "B"],
            "time_s": [np.nan, np.nan, 0.0],
            "rr_ms": [800.0, 810.0, 820.0],
        }
    )
    out = gp.flag_gazepoint_hrv_segments(
        data,
        rr_col="rr_ms",
        time_col="time_s",
        group_cols="group",
        window_s=None,
        min_beats=1,
        min_duration_s=0,
    )
    assert out["group"].tolist() == ["B"]


def test_hrv_segments_singleton_skips_successive_change_branch():
    out = gp.flag_gazepoint_hrv_segments(
        [800.0],
        window_s=None,
        min_beats=1,
        min_duration_s=0,
    )
    assert len(out) == 1
    assert int(out.iloc[0].n_large_successive_changes) == 0


def test_signal_lag_matrix_requires_at_least_two_signals():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 1.0, 2.0],
            "a": [1.0, 2.0, 3.0],
        }
    )
    with pytest.raises(ValueError, match="At least two"):
        gp.compute_gazepoint_signal_lag_matrix(
            data,
            signal_cols=["a"],
            time_col="time_s",
        )


def test_signal_lag_matrix_skips_group_without_positive_time_step():
    data = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "B", "B"],
            "time_s": [0.0, 0.0, 0.0, 1.0, 2.0, 3.0],
            "a": [1.0, 2.0, 1.0, 2.0, 3.0, 4.0],
            "b": [2.0, 3.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    out = gp.compute_gazepoint_signal_lag_matrix(
        data,
        signal_cols=["a", "b"],
        time_col="time_s",
        group_cols="group",
        max_lag_s=1,
        min_overlap=3,
    )
    assert set(out["group"]) == {"B"}


def test_signal_lag_matrix_continues_after_insufficient_overlap_pair():
    data = pd.DataFrame(
        {
            "time_s": [0.0, 1.0, 2.0, 3.0, 4.0],
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [1.0, np.nan, np.nan, np.nan, 5.0],
            "c": [5.0, 4.0, 3.0, 2.0, 1.0],
        }
    )
    out = gp.compute_gazepoint_signal_lag_matrix(
        data,
        signal_cols=["a", "b", "c"],
        time_col="time_s",
        max_lag_s=1,
        min_overlap=3,
    )
    assert ((out["signal_1"] == "a") & (out["signal_2"] == "c")).any()
