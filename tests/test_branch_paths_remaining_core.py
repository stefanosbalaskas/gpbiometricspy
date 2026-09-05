from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_baseline_explicit_signal_without_validity_or_zero_exclusion():
    dat = pd.DataFrame(
        {
            "GSR": [0.0, 2.0, 3.0],
            "baseline": [True, True, False],
        }
    )
    out = gp.baseline_correct_gazepoint_gsr(
        dat,
        dat["baseline"].to_numpy(),
        value_column="GSR",
        validity_column=None,
        exclude_zero=False,
    )
    np.testing.assert_allclose(out["GSR_baseline_corrected"], [-1.0, 1.0, 2.0])
    summary = out.attrs["baseline_summary"].iloc[0]
    assert summary["baseline_usable_rows"] == 2
    assert summary["baseline_value"] == pytest.approx(1.0)


def test_smoothing_can_preserve_nonfinite_windows():
    dat = pd.DataFrame({"HR": [70.0, np.nan, 74.0]})
    out = gp.smooth_gazepoint_biometrics(
        dat,
        "HR",
        window=3,
        na_rm=False,
    )
    assert out["HR_smoothed"].isna().all()


def test_ibi_filter_validation_singleton_and_ungrouped_paths():
    dat = pd.DataFrame({"IBI": [1000.0, 1010.0]})

    with pytest.raises(ValueError, match="time_col"):
        gp.filter_gazepoint_ibi_implausible(dat, time_col="missing_time")
    with pytest.raises(ValueError, match="validity_col"):
        gp.filter_gazepoint_ibi_implausible(dat, validity_col="missing_validity")
    with pytest.raises(ValueError, match="greater than"):
        gp.filter_gazepoint_ibi_implausible(
            dat,
            min_ibi_ms=1000,
            max_ibi_ms=900,
        )

    singleton = gp.filter_gazepoint_ibi_implausible(
        pd.DataFrame({"participant": ["P1"], "IBI": [1000.0]}),
        group_cols="participant",
    )
    assert singleton["overview"].iloc[0]["clean_rows"] == 1
    assert singleton["group_summary"].iloc[0]["rows"] == 1

    ungrouped = gp.filter_gazepoint_ibi_implausible(
        dat,
        group_cols=[],
    )
    assert "IBI_clean_ms" in ungrouped["data"]
    assert len(ungrouped["group_summary"]) == 1
    assert "IBI" not in ungrouped["group_summary"].columns


def test_hr_ibi_consistency_validation_and_ungrouped_summary():
    with pytest.raises(ValueError, match="ibi_col"):
        gp.compare_gazepoint_hr_ibi_consistency(
            pd.DataFrame({"HR": [60.0]})
        )

    dat = pd.DataFrame({"HR": [60.0, 60.0], "IBI": [1000.0, 1000.0]})
    with pytest.raises(ValueError, match="time_col"):
        gp.compare_gazepoint_hr_ibi_consistency(
            dat,
            time_col="missing_time",
        )

    out = gp.compare_gazepoint_hr_ibi_consistency(
        dat,
        group_cols=[],
    )
    assert out["overview"].iloc[0]["status"] == "hr_ibi_consistency_pass"
    assert len(out["group_summary"]) == 1
    assert out["group_summary"].iloc[0]["comparable_rows"] == 2


def test_hrv_missing_column_and_singleton_ungrouped_collapse():
    with pytest.raises(ValueError, match="ibi_col"):
        gp.extract_gazepoint_hrv_features(
            pd.DataFrame({"IBI": [1000.0]}),
            ibi_col="IBI_clean_ms",
        )

    out = gp.extract_gazepoint_hrv_features(
        pd.DataFrame({"IBI_clean_ms": [1000.0]}),
        group_cols=[],
        min_intervals=3,
        min_duration_s=0,
        collapse_repeated_intervals=True,
    )
    assert out["overview"].iloc[0]["status"] == "fail_no_hrv_features_computed"
    feature = out["features"].iloc[0]
    assert feature["input_interval_rows"] == 1
    assert feature["used_intervals_after_collapse"] == 1
    assert feature["feature_status"] == "insufficient_intervals"
