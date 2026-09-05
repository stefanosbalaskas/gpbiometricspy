import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_biosppy_preparation_validation_modes_and_time_guards(tmp_path):
    base = pd.DataFrame({"time_s": [0.0, 0.1, 0.2], "EDA": [1.0, 1.1, 1.2]})

    for kwargs, match in [
        ({"signal_type": "bad"}, "signal_type"),
        ({"signal_type": "eda", "missing": "bad"}, "missing"),
        ({"signal_type": "eda", "irregular": "bad"}, "irregular"),
        ({"signal_type": "eda", "sampling_tolerance": -1}, "settings"),
        ({"signal_type": "eda", "min_segment_samples": 0}, "settings"),
    ]:
        with pytest.raises(ValueError, match=match):
            gp.prepare_gazepoint_biosppy_input(base, **kwargs)

    with pytest.raises(ValueError, match="signal_col"):
        gp.prepare_gazepoint_biosppy_input(
            base, signal_type="eda", signal_col="missing"
        )

    nonfinite_time = pd.DataFrame({"time_s": [0.0, np.nan, 0.2], "EDA": [1.0, 1.1, 1.2]})
    with pytest.raises(ValueError, match="Non-finite time"):
        gp.prepare_gazepoint_biosppy_input(nonfinite_time, signal_type="eda")

    nonincreasing = pd.DataFrame({"time_s": [0.0, 0.1, 0.1], "EDA": [1.0, 1.1, 1.2]})
    with pytest.raises(ValueError, match="strictly increasing"):
        gp.prepare_gazepoint_biosppy_input(nonincreasing, signal_type="eda")

    one = pd.DataFrame({"time_s": [0.0], "EDA": [1.0]})
    with pytest.raises(ValueError, match="valid sampling rate"):
        gp.prepare_gazepoint_biosppy_input(one, signal_type="eda")

    sparse = pd.DataFrame({"time_s": [0.0, 0.1, 0.2], "EDA": [np.nan, 1.0, np.nan]})
    with pytest.raises(ValueError, match="two finite"):
        gp.prepare_gazepoint_biosppy_input(
            sparse, signal_type="eda", missing="interpolate"
        )

    out = gp.prepare_gazepoint_biosppy_input(
        [1.0, 1.1, 1.2],
        signal_type="eda",
        sampling_rate_hz=10,
        output_dir=tmp_path,
        write_manifest=False,
    )
    assert len(out["files"]) == 1
    assert out["manifest"].iloc[0].sample_count == 3

    again = gp.prepare_gazepoint_biosppy_input(
        [1.0, 1.1, 1.2],
        signal_type="eda",
        sampling_rate_hz=10,
        output_dir=tmp_path,
        write_manifest=False,
        overwrite=True,
    )
    assert len(again["files"]) == 1


def test_biosppy_exported_prepare_signal_frontdoor_errors():
    with pytest.raises(TypeError, match="data frame or numeric vector"):
        gp.extract_gazepoint_eda_events_biosppy_style(object())

    with pytest.raises(ValueError, match="signal_col"):
        gp.extract_gazepoint_eda_events_biosppy_style(
            pd.DataFrame({"time_s": [0.0, 0.1], "EDA": [1.0, 1.1]}),
            signal_col="missing",
            time_col="time_s",
            sampling_rate_hz=10,
        )

    with pytest.raises(ValueError, match="time_col"):
        gp.extract_gazepoint_eda_events_biosppy_style(
            pd.DataFrame({"EDA": [1.0, 1.1]}),
            signal_col="EDA",
            time_col="missing",
            sampling_rate_hz=10,
        )

    with pytest.raises(ValueError, match="time_col.*sampling_rate_hz|Supply"):
        gp.extract_gazepoint_eda_events_biosppy_style(
            pd.DataFrame({"EDA": [1.0, 1.1]}), signal_col="EDA"
        )

    with pytest.raises(ValueError, match="infer signal"):
        gp.extract_gazepoint_eda_events_biosppy_style(
            pd.DataFrame({"time_s": [0.0, 0.1], "x": [1.0, 1.1]}),
            time_col="time_s",
            sampling_rate_hz=10,
        )


def test_biosppy_short_ppg_empty_peaks_templates_and_recovery():
    short = pd.DataFrame(
        {"time_s": np.arange(6) / 10.0, "PPG": [0.0, 1.0, 0.0, 1.0, 0.0, 0.0]}
    )
    ppg = gp.run_gazepoint_biosppy_ppg(
        short, "PPG", "time_s", sampling_rate_hz=10
    )
    assert len(ppg["signal"]) == 6

    no_peaks = pd.DataFrame(columns=["peak_index", "group"])
    templates = gp.extract_gazepoint_ppg_templates(
        short,
        "PPG",
        "time_s",
        peaks=no_peaks,
        sampling_rate_hz=10,
    )
    assert templates["templates"].shape[0] == 0
    assert np.isnan(templates["template_quality_correlation"])

    onsets = gp.detect_gazepoint_ppg_onsets(
        short,
        "PPG",
        "time_s",
        peaks=no_peaks,
        sampling_rate_hz=10,
    )
    assert onsets.empty

    eda = pd.DataFrame({"time_s": np.arange(8) / 10.0, "EDA": np.ones(8)})
    recovery = gp.estimate_gazepoint_eda_recovery_times(
        eda,
        events=pd.DataFrame(
            {
                "onset_index": [1],
                "peak_index": [2],
                "peak_time_s": [0.1],
            }
        ),
        signal_col="EDA",
        time_col="time_s",
        sampling_rate_hz=10,
        recovery_prop=0.5,
        max_recovery_seconds=0.01,
    )
    assert "recovery_time_s" in recovery


def test_biosppy_rri_validation_short_and_replacement_paths():
    with pytest.raises(ValueError, match="Invalid `method`"):
        gp.detrend_gazepoint_rri_window([800, 810, 790], method="bad")

    short = gp.detrend_gazepoint_rri_window([800, 810], method="median")
    assert short["rri_detrended_ms"].isna().all()

    with pytest.raises(ValueError, match="Invalid method"):
        gp.correct_gazepoint_rri_artifacts_local([800, 810], method="bad")
    with pytest.raises(ValueError, match="Invalid method"):
        gp.correct_gazepoint_rri_artifacts_local(
            [800, 810], replacement="bad"
        )

    clean_short = gp.correct_gazepoint_rri_artifacts_local(
        [800.0, 810.0], method="local_median"
    )
    assert not clean_short.artifact.any()

    flat_z = gp.correct_gazepoint_rri_artifacts_local(
        [800.0, 800.0, 800.0], method="zscore"
    )
    assert not flat_z.artifact.any()

    all_bad = gp.correct_gazepoint_rri_artifacts_local(
        [np.nan, -1.0, 0.0], method="local_median", replacement="local_median"
    )
    assert all_bad.rri_corrected_ms.isna().all()

    interp_too_few = gp.correct_gazepoint_rri_artifacts_local(
        [800.0, np.nan, np.nan], method="quotient", replacement="interpolate"
    )
    assert np.isnan(interp_too_few.rri_corrected_ms.iloc[1])


def test_biosppy_spectrum_band_phase_and_correlation_guard_paths():
    assert gp.compute_gazepoint_signal_power_spectrum([], 10).empty
    with pytest.raises(ValueError, match="sampling rate"):
        gp.compute_gazepoint_signal_power_spectrum([1.0, 2.0, 3.0, 4.0], 0)

    raw = np.sin(np.linspace(0, 4 * np.pi, 64))
    ps = gp.compute_gazepoint_signal_power_spectrum(raw, 20, detrend=False)
    assert not ps.empty

    zero = pd.DataFrame({"frequency_hz": [0.1, 0.2], "power": [0.0, 0.0]})
    bp = gp.compute_gazepoint_signal_band_power(
        zero, bands={"x": (0.0, 0.5)}, relative=True
    )
    assert np.isnan(bp.loc[0, "relative_power"])

    bp_abs = gp.compute_gazepoint_signal_band_power(
        ps, bands={"x": (0.0, 2.0)}, relative=False
    )
    assert np.isnan(bp_abs.loc[0, "relative_power"])

    phase = gp.compute_gazepoint_signal_phase_locking(raw, raw, 20, band=None)
    assert phase.loc[0, "phase_locking_value"] == pytest.approx(1.0)

    with pytest.raises(ValueError, match="Invalid `method`"):
        gp.compute_gazepoint_signal_correlation([1, 2, 3], [1, 2, 3], method="bad")

    insufficient = gp.compute_gazepoint_signal_correlation(
        [1.0, np.nan], [1.0, 2.0], lag_max=2
    )
    assert np.isnan(insufficient.loc[0, "correlation"])
    assert np.isnan(insufficient.loc[0, "best_lag_correlation"])

    x = np.arange(8.0)
    y = np.roll(x, 1)
    lagged = gp.compute_gazepoint_signal_correlation(x, y, lag_max=2)
    assert np.isfinite(lagged.loc[0, "best_lag_correlation"])
