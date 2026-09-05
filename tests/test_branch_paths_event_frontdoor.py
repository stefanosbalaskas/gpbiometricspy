from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_event_and_group_validation_paths():
    amplitudes = pd.DataFrame({"group": ["a", "b"], "scr_amplitude": [1.0, 2.0]})
    with pytest.raises(ValueError, match="Missing grouping columns"):
        gp.normalize_gazepoint_scr(amplitudes, group_cols="missing_group")

    data = pd.DataFrame({"time": [0.0, 1.0, 2.0], "GSR": [0.0, 0.1, 0.0]})
    events = pd.DataFrame({"event_time": [0.0], "event_id": [1]})
    with pytest.raises(ValueError, match="Missing event grouping columns"):
        gp.epoch_gazepoint_scr(data, events, 0.0, 1.0, event_group_cols="missing_group")

    with pytest.raises(TypeError, match="data frame"):
        gp.epoch_gazepoint_scr([], [0.0], 0.0, 1.0)


def test_scr_peak_continue_paths_and_short_response_auc():
    close_peaks = pd.DataFrame(
        {
            "time": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            "GSR": [0.0, 1.0, 0.0, 0.9, 0.0, 0.0],
        }
    )
    close = gp.epoch_gazepoint_scr(
        close_peaks,
        [0.0],
        0.0,
        1.0,
        min_amplitude=0.05,
        min_distance_s=1.0,
    )
    assert close.loc[0, "scr_count"] == 1

    low_peak = pd.DataFrame({"time": [0.0, 0.5, 1.0], "GSR": [0.0, 0.1, 0.0]})
    low = gp.epoch_gazepoint_scr(
        low_peak,
        [0.0],
        0.0,
        1.0,
        min_amplitude=0.5,
        min_distance_s=0.0,
    )
    assert low.loc[0, "scr_count"] == 0

    sparse_response = pd.DataFrame({"time": [-1.0, 0.0, 1.0], "GSR": [0.0, 0.0, 0.1]})
    sparse = gp.epoch_gazepoint_scr(
        sparse_response,
        [0.0],
        1.0,
        1.0,
        response_window=[0.5, 1.0],
    )
    assert np.isnan(sparse.loc[0, "response_auc"])


def test_normalization_none_center_and_invalid_method_paths():
    raw = np.array([1.0, 2.0, 3.0])
    np.testing.assert_allclose(gp.normalize_gazepoint_scr(raw, method="none"), raw)
    centered = gp.normalize_gazepoint_scr(raw, method="center")
    assert centered.mean() == pytest.approx(0.0)
    with pytest.raises(ValueError, match="Invalid normalization method"):
        gp.normalize_gazepoint_scr(raw, method="invalid")


def test_engagement_invalid_group_all_missing_group_and_scalar_paths():
    with pytest.raises(ValueError, match="group.*same length"):
        gp.compute_gazepoint_engagement_index([1.0, 2.0], group=["a"])

    grouped = gp.compute_gazepoint_engagement_index(
        [np.nan, np.nan, 60.0, 70.0],
        time=[0.0, 1.0, 0.0, 1.0],
        group=["missing", "missing", "valid", "valid"],
    )
    missing = grouped.loc[grouped["group"] == "missing"].iloc[0]
    assert missing["n_valid"] == 0

    scalar = gp.compute_gazepoint_engagement_index([40.0, 60.0], time=[0.0, 1.0], return_="scalar")
    assert scalar == pytest.approx(0.0)


def test_missingness_and_detrend_validation_and_alternatives():
    with pytest.raises(TypeError, match="data frame"):
        gp.summarize_gazepoint_missingness(pd.DataFrame())

    with pytest.raises(ValueError, match="signal_col"):
        gp.detrend_gazepoint_signal(pd.DataFrame({"label": ["a", "b"]}), signal_col="missing")

    grouped = pd.DataFrame(
        {
            "group": ["missing", "missing", "valid", "valid"],
            "time": [0.0, 1.0, 0.0, 1.0],
            "signal": [np.nan, np.nan, 1.0, 2.0],
        }
    )
    out = gp.detrend_gazepoint_signal(grouped, signal_col="signal", time_col="time", group_cols="group")
    assert out.loc[:1, "signal_detrended"].isna().all()

    for method in ("none", "mean", "median"):
        detrended = gp.detrend_gazepoint_signal([1.0, 2.0, 3.0], method=method)
        assert "signal_detrended" in detrended


def test_biometrics_audit_invalid_data_path():
    with pytest.raises(TypeError, match="data frame"):
        gp.audit_gazepoint_biometrics_file(data=pd.DataFrame())
