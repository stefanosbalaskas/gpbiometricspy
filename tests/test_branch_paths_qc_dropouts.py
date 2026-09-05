import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_time_reset_exact_autodetection_and_nonfinite_reindex_path():
    exact = gp.audit_gazepoint_time_resets(pd.DataFrame({"TIME": [0.0, 1.0, 2.0]}))
    assert exact["overview"].loc[0, "time_col"] == "TIME"

    nonfinite = gp.audit_gazepoint_time_resets(
        pd.DataFrame({"TIME": [np.nan, np.nan]}),
        return_reindexed_time=True,
    )
    assert nonfinite["overview"].loc[0, "status"] == "fail_no_numeric_time"
    assert nonfinite["data_with_segments"]["time_reindexed_within_segment"].isna().all()


def test_nonwear_short_run_and_short_low_variance_public_paths():
    short_missing = gp.detect_gazepoint_nonwear(
        pd.DataFrame({"signal": [1.0, np.nan, 1.0]}),
        signal_cols="signal",
        min_run_length=2,
        detect_missing=True,
        detect_zero=False,
        detect_constant=False,
        detect_low_variance=False,
    )
    assert short_missing["intervals"].empty

    short_lowvar = gp.detect_gazepoint_nonwear(
        pd.DataFrame({"signal": [1.0, 1.0]}),
        signal_cols="signal",
        min_run_length=3,
        low_variance_threshold=0.1,
        detect_missing=False,
        detect_zero=False,
        detect_constant=False,
        detect_low_variance=True,
    )
    assert short_lowvar["intervals"].empty


def test_nonwear_summary_public_validation_paths():
    with pytest.raises(ValueError, match="missing required columns"):
        gp.summarize_gazepoint_nonwear(pd.DataFrame({"signal": ["x"]}))

    nonwear = gp.detect_gazepoint_nonwear(
        pd.DataFrame({"signal": [1.0, 1.0, 1.0]}),
        signal_cols="signal",
        min_run_length=2,
    )
    with pytest.raises(ValueError, match="by"):
        gp.summarize_gazepoint_nonwear(nonwear, by="missing")


def test_filter_signal_public_validation_paths():
    data = pd.DataFrame(
        {
            "signal": [1.0, 2.0, 3.0],
            "group": ["A", "A", "A"],
            "time": [0.0, 1.0, 2.0],
            "time_text": ["0", "1", "2"],
        }
    )

    with pytest.raises(ValueError, match="signal_cols"):
        gp.filter_gazepoint_signal(data, [])
    with pytest.raises(ValueError, match="method"):
        gp.filter_gazepoint_signal(data, "signal", method="bad")
    with pytest.raises(ValueError, match="not found"):
        gp.filter_gazepoint_signal(data, "missing")
    with pytest.raises(ValueError, match="group_cols"):
        gp.filter_gazepoint_signal(data, "signal", group_cols="missing")
    with pytest.raises(ValueError, match="time_col"):
        gp.filter_gazepoint_signal(data, "signal", time_col="missing")
    with pytest.raises(TypeError, match="time_col"):
        gp.filter_gazepoint_signal(data, "signal", time_col="time_text")
    with pytest.raises(ValueError, match="window"):
        gp.filter_gazepoint_signal(data, "signal", window=0)
    with pytest.raises(TypeError, match="suffix"):
        gp.filter_gazepoint_signal(data, "signal", suffix=123)


def test_filter_signal_roll_skip_no_time_and_sparse_detrend_paths():
    rolled = gp.filter_gazepoint_signal(
        pd.DataFrame({"signal": [1.0, np.nan, 3.0]}),
        "signal",
        method="moving_average",
        window=3,
        na_rm=False,
    )
    assert rolled["signal_moving_average"].isna().all()

    detrended = gp.filter_gazepoint_signal(
        pd.DataFrame({"signal": [1.0, np.nan]}),
        "signal",
        method="detrend",
    )
    assert detrended["signal_detrend"].isna().all()


def test_upsample_public_validation_paths():
    empty = pd.DataFrame({"time": pd.Series(dtype=float), "signal": pd.Series(dtype=float)})
    with pytest.raises(ValueError, match="at least one row"):
        gp.upsample_gazepoint_data(empty, "time", signal_cols="signal")

    data = pd.DataFrame({"time": [0.0, 1.0], "signal": [1.0, 2.0], "group": ["A", "A"]})
    with pytest.raises(ValueError, match="time_col"):
        gp.upsample_gazepoint_data(data, "missing", signal_cols="signal")
    with pytest.raises(ValueError, match="group_cols"):
        gp.upsample_gazepoint_data(data, "time", signal_cols="signal", group_cols="missing")

    with pytest.raises(ValueError, match="No numeric signal"):
        gp.upsample_gazepoint_data(
            pd.DataFrame({"time": [0.0, 1.0], "label": ["a", "b"]}),
            "time",
        )
    with pytest.raises(ValueError, match="signal_cols"):
        gp.upsample_gazepoint_data(data, "time", signal_cols="missing")
    with pytest.raises(ValueError, match="interval"):
        gp.upsample_gazepoint_data(data, "time", signal_cols="signal", interval=0)
    with pytest.raises(ValueError, match="method"):
        gp.upsample_gazepoint_data(data, "time", signal_cols="signal", method="spline")


def test_upsample_group_skip_and_no_rows_paths():
    with pytest.raises(ValueError, match="No groups contained"):
        gp.upsample_gazepoint_data(
            pd.DataFrame({"time": [0.0], "signal": [1.0]}),
            "time",
            signal_cols="signal",
        )

    with pytest.raises(ValueError, match="No groups contained"):
        gp.upsample_gazepoint_data(
            pd.DataFrame({"time": [0.0, 0.0], "signal": [1.0, 2.0]}),
            "time",
            signal_cols="signal",
        )


def test_upsample_sparse_signal_reaches_interpolation_guard():
    out = gp.upsample_gazepoint_data(
        pd.DataFrame({"time": [0.0, 1.0], "signal": [1.0, np.nan]}),
        "time",
        signal_cols="signal",
        interval=0.5,
    )
    assert out["signal"].isna().all()
