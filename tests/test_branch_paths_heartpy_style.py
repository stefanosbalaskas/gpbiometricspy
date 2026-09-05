import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_heartpy_input_inference_group_and_output_paths(tmp_path):
    canonical = pd.DataFrame({"PPG": [1.0, 2.0, 3.0], "time_s": [0.0, 0.1, 0.2]})
    inferred = gp.prepare_gazepoint_heartpy_input(canonical, signal_col="PPG")
    assert inferred["sampling_rate_hz"] == pytest.approx(10.0)
    assert inferred["path"] == []

    with pytest.raises(ValueError, match="Missing group columns"):
        gp.prepare_gazepoint_heartpy_input(
            canonical,
            signal_col="PPG",
            group_cols="missing",
        )

    written = gp.prepare_gazepoint_heartpy_input(
        canonical,
        signal_col="PPG",
        output_dir=tmp_path,
        prefix="branch",
    )
    assert len(written["path"]) == 2


def test_clipping_enhancement_filter_and_hampel_guard_paths():
    short = gp.reconstruct_gazepoint_ppg_clipping([1.0, 2.0])
    assert not short["clipped"].any()

    nonfinite = gp.reconstruct_gazepoint_ppg_clipping([np.nan] * 4)
    assert not nonfinite["clipped"].any()

    constant = gp.reconstruct_gazepoint_ppg_clipping([2.0] * 6)
    assert not constant["clipped"].any()

    with pytest.raises(ValueError, match="Invalid sampling rate"):
        gp.enhance_gazepoint_ppg_peaks([0.0, 1.0, 0.0], 0)
    with pytest.raises(ValueError, match="Invalid sampling rate"):
        gp.filter_gazepoint_ppg_butterworth([0.0, 1.0, 0.0], sampling_rate_hz=None)
    with pytest.raises(ValueError, match="Invalid sampling rate"):
        gp.correct_gazepoint_ppg_hampel([0.0, 1.0, 0.0], 0)

    flat = gp.correct_gazepoint_ppg_hampel([1.0] * 8, 20)
    assert np.allclose(flat, 1.0)


def test_peak_detection_numeric_and_sampling_guard_paths():
    with pytest.raises(TypeError, match="data frame or numeric vector"):
        gp.detect_gazepoint_ppg_peaks(np.zeros((2, 2)), sampling_rate_hz=20)
    with pytest.raises(ValueError, match="sampling_rate_hz"):
        gp.detect_gazepoint_ppg_peaks(np.arange(8.0))

    bad_time = pd.DataFrame(
        {"pulse": [0.0, 1.0, 0.0, 1.0], "time_s": [0.0, 0.0, 0.0, 0.0]}
    )
    with pytest.raises(ValueError, match="valid sampling rate"):
        gp.detect_gazepoint_ppg_peaks(bad_time, "pulse", "time_s")

    # Four closely spaced samples reach the public high-precision fallback where
    # the 1 kHz interpolation grid contains fewer than three points.
    tiny_time = pd.DataFrame(
        {
            "pulse": [0.0, 1.0, 0.0, 0.0],
            "time_s": [0.0, 0.0002, 0.0004, 0.0006],
        }
    )
    detected = gp.detect_gazepoint_ppg_peaks(
        tiny_time,
        "pulse",
        "time_s",
        sampling_rate_hz=5000,
        threshold_offsets=[0.0],
        reconstruct_clipping=False,
        high_precision=True,
    )
    assert len(detected["peaks"]) == 1
    assert detected["peaks"].iloc[0].peak_time_s == pytest.approx(0.0002)


def test_peak_rejection_and_rr_from_peaks_guard_paths():
    empty = gp.reject_gazepoint_ppg_peaks(pd.DataFrame())
    assert empty.empty
    assert gp.reject_gazepoint_ppg_peaks([1, 2]) == [1, 2]

    with pytest.raises(ValueError, match="peak_time_s"):
        gp.reject_gazepoint_ppg_peaks(pd.DataFrame({"x": [1]}))

    two = pd.DataFrame({"peak_time_s": [0.0, 0.8], "group": ["g", "g"]})
    kept = gp.reject_gazepoint_ppg_peaks(two)
    assert len(kept) == 2

    assert gp.compute_gazepoint_ppg_frequency_measures(peaks=pd.DataFrame()).empty
    with pytest.raises(ValueError, match="peak_time_s"):
        gp.compute_gazepoint_ppg_frequency_measures(peaks=pd.DataFrame({"x": [1]}))


def test_rr_resampling_frequency_and_measure_empty_paths():
    empty_freq = gp.compute_gazepoint_ppg_frequency_measures(rr_ms=[np.nan, -1.0])
    assert np.isnan(empty_freq.loc[0, "total_power"])

    tiny_grid = gp.compute_gazepoint_ppg_frequency_measures(
        rr_ms=[1.0, 1.0, 1.0, 1.0],
        resample_hz=4,
    )
    assert np.isnan(tiny_grid.loc[0, "total_power"])

    with pytest.raises(ValueError, match="peaks.*rr_ms|either"):
        gp.compute_gazepoint_ppg_frequency_measures()

    assert gp.compute_gazepoint_ppg_measures(pd.DataFrame()).empty


def test_plot_and_report_validation_paths():
    with pytest.raises(ValueError, match="Invalid detection object"):
        gp.plot_gazepoint_ppg_peak_detection({})
    with pytest.raises(ValueError, match="Invalid detection object"):
        gp.create_gazepoint_heartpy_report({})


def test_section_scaling_without_sections_path():
    data = pd.DataFrame({"pulse": [1.0, 2.0, 3.0]})
    out = gp.scale_gazepoint_ppg_sections(
        data,
        signal_col="pulse",
        section_cols=None,
        method="center",
    )
    assert np.allclose(out["ppg_scaled"], [-1.0, 0.0, 1.0])


def test_rr_cleaning_validation_short_and_zero_scale_paths():
    with pytest.raises(ValueError, match="Invalid cleaning method"):
        gp.clean_gazepoint_rr_intervals([800.0, 810.0], method="bad")

    short_peaks = pd.DataFrame({"peak_time_s": [0.0, 0.8], "group": ["g", "g"]})
    cleaned_peaks = gp.clean_gazepoint_rr_intervals(short_peaks, method="quotient")
    assert len(cleaned_peaks) == 2

    modified = gp.clean_gazepoint_rr_intervals(
        [800.0, 800.0, 800.0], method="modified_z"
    )
    assert modified["accepted"].all()

    single = gp.clean_gazepoint_rr_intervals([800.0], method="quotient")
    assert bool(single.loc[0, "accepted"])

    zflat = gp.clean_gazepoint_rr_intervals([800.0, 800.0, 800.0], method="zscore")
    assert zflat["accepted"].all()


def test_segmentwise_input_and_plot_guard_paths():
    with pytest.raises(ValueError, match="sampling_rate_hz"):
        gp.process_gazepoint_ppg_segmentwise(np.arange(20.0))

    with pytest.raises(ValueError, match="segmentwise"):
        gp.plot_gazepoint_ppg_segmentwise({})
    with pytest.raises(ValueError, match="No segmentwise measures"):
        gp.plot_gazepoint_ppg_segmentwise({"measures": pd.DataFrame()})
    with pytest.raises(ValueError, match="Measure column not found"):
        gp.plot_gazepoint_ppg_segmentwise(
            {"measures": pd.DataFrame({"start_s": [0.0], "bpm": [70.0]})},
            measure="rmssd_ms",
        )
