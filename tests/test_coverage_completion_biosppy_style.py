import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.biosppy_style as m


def test_prepare_signal_numeric_dataframe_and_inference_branches():
    d, sc, tc, gc, fs = m._prepare_signal([1, 2, 3], sampling_rate_hz=10)
    assert (sc, tc, gc, fs) == ("signal", "time_s", ["group"], 10.0)
    with pytest.raises(ValueError, match="sampling_rate_hz"):
        m._prepare_signal([1, 2], sampling_rate_hz=None)
    with pytest.raises(ValueError, match="infer signal"):
        m._prepare_signal(pd.DataFrame({"x": [1, 2]}), candidates=("EDA",))
    d2, sc2, tc2, gc2, fs2 = m._prepare_signal(
        pd.DataFrame({"EDA": [1.0, 2.0, 3.0]}), candidates=("EDA",), sampling_rate_hz=5
    )
    assert sc2 == "EDA" and tc2 == "time_s" and fs2 == 5
    with pytest.raises(ValueError, match="time_col"):
        m._prepare_signal(pd.DataFrame({"EDA": [1.0]}), candidates=("EDA",))
    _, _, _, _, inferred = m._prepare_signal(
        pd.DataFrame({"time_s": [0.0, 0.25, 0.5], "EDA": [1.0, 2.0, 3.0]}),
        candidates=("EDA",), time_col="time_s",
    )
    assert inferred == pytest.approx(4.0)


def test_bandpass_filter_failure_falls_back(monkeypatch):
    x = np.sin(np.linspace(0, 4 * np.pi, 30))
    monkeypatch.setattr(m, "sosfiltfilt", lambda *a, **k: (_ for _ in ()).throw(ValueError("short")))
    assert np.allclose(m._bandpass(x, 20), x)


def test_peak_indices_time_empty_and_numeric_forms():
    time = np.array([0.0, 0.1, 0.2])
    via_time = m._peak_indices(pd.DataFrame({"peak_time_s": [0.19], "group": ["g"]}), time, 3)
    assert via_time.iloc[0]["index"] == 3
    assert m._peak_indices(pd.DataFrame({"x": [1]}), time, 3).empty
    via_numeric = m._peak_indices([1, 4], time, 3)
    assert via_numeric["index"].tolist() == [1]


def test_prepare_biosppy_auto_inference_no_time_segments_and_collisions(tmp_path):
    with pytest.raises(ValueError, match="Both EDA and PPG"):
        m.prepare_gazepoint_biosppy_input(pd.DataFrame({"EDA": [1, 2], "PPG": [1, 2], "time_s": [0, 1]}))
    eda = m.prepare_gazepoint_biosppy_input(pd.DataFrame({"EDA": [1.0, 2.0, 3.0], "time_s": [0, 1, 2]}))
    assert eda["settings"]["signal_type"] == "eda"
    ppg = m.prepare_gazepoint_biosppy_input(pd.DataFrame({"PPG": [1.0, 2.0, 3.0], "time_s": [0, 1, 2]}))
    assert ppg["settings"]["signal_type"] == "ppg"
    with pytest.raises(ValueError, match="Could not infer"):
        m.prepare_gazepoint_biosppy_input(pd.DataFrame({"x": [1.0], "time_s": [0]}))
    with pytest.raises(ValueError, match="time_col"):
        m.prepare_gazepoint_biosppy_input(pd.DataFrame({"EDA": [1.0, 2.0]}), signal_type="eda")
    no_time = m.prepare_gazepoint_biosppy_input(
        pd.DataFrame({"EDA": [1.0, 2.0, 3.0]}), signal_type="eda", sampling_rate_hz=2
    )
    assert no_time["samples"].time_s.tolist() == [0, 0.5, 1]

    seg = m.prepare_gazepoint_biosppy_input(
        pd.DataFrame({"time_s": [0, 1, 2], "EDA": [1.0, np.nan, np.nan]}),
        signal_type="eda", missing="segments", min_segment_samples=2
    )
    assert seg["vectors"] == {}
    assert seg["samples"].exclusion_reason.iloc[0] == "short_segment"

    base = pd.DataFrame({"time_s": [0, 1, 2], "EDA": [1.0, 2.0, 3.0]})
    m.prepare_gazepoint_biosppy_input(base, signal_type="eda", output_dir=tmp_path)
    with pytest.raises(FileExistsError):
        m.prepare_gazepoint_biosppy_input(base, signal_type="eda", output_dir=tmp_path)


def test_detrend_mean_linear_short_linear_and_zscore_artifacts():
    r = [800, 810, 790, 805, 795]
    mean = m.detrend_gazepoint_rri_window(r, method="mean")
    assert np.isfinite(mean.trend_ms).all()
    linear = m.detrend_gazepoint_rri_window(r, method="linear", window_seconds=100)
    assert np.isfinite(linear.trend_ms).all()
    short_windows = m.detrend_gazepoint_rri_window(r, method="linear", window_seconds=0.001)
    assert np.isfinite(short_windows.trend_ms).all()
    z = m.correct_gazepoint_rri_artifacts_local([800] * 10 + [5000], method="zscore")
    assert len(z) == 11


def test_signal_correlation_rank_methods():
    x = [1, 2, 3, 4]
    y = [1, 3, 2, 4]
    assert np.isfinite(m.compute_gazepoint_signal_correlation(x, y, method="spearman").correlation.iloc[0])
    assert np.isfinite(m.compute_gazepoint_signal_correlation(x, y, method="kendall").correlation.iloc[0])
