from __future__ import annotations

import numpy as np
import pandas as pd

import gpbiometricspy as gp


def test_hrv_asymmetry_single_direction_run_paths():
    increasing = pd.DataFrame({"IBI": [0.80, 0.81, 0.82, 0.83, 0.84, 0.85]})
    inc = gp.extract_gazepoint_hrv_asymmetry(increasing)["features"].iloc[0]
    assert inc["status"] == "hrv_asymmetry_extracted"
    assert inc["acceleration_count"] == 0
    assert inc["deceleration_count"] > 0
    assert np.isnan(inc["mean_acceleration_run_length"])
    assert np.isnan(inc["longest_acceleration_run"])

    decreasing = pd.DataFrame({"IBI": [0.85, 0.84, 0.83, 0.82, 0.81, 0.80]})
    dec = gp.extract_gazepoint_hrv_asymmetry(decreasing)["features"].iloc[0]
    assert dec["status"] == "hrv_asymmetry_extracted"
    assert dec["acceleration_count"] > 0
    assert dec["deceleration_count"] == 0
    assert np.isnan(dec["mean_deceleration_run_length"])
    assert np.isnan(dec["longest_deceleration_run"])


def test_pdr_automatic_sampling_rate_short_and_duplicate_time_paths():
    too_short = pd.DataFrame({"CNT": [0.0, 1.0], "HRP": [0.0, 0.0]})
    short = gp.extract_gazepoint_pdr_signals(
        too_short,
        sampling_rate=None,
        smooth_window=1,
    )
    assert np.isnan(short["pdr_summary"].loc[0, "sampling_rate_hz"])
    assert short["pdr_summary"].loc[0, "status"] == "insufficient_pulse_peaks"

    duplicate_time = pd.DataFrame(
        {"CNT": [1.0, 1.0, 1.0, 1.0], "HRP": [0.0, 1.0, 0.0, 0.0]}
    )
    dup = gp.extract_gazepoint_pdr_signals(
        duplicate_time,
        sampling_rate=None,
        smooth_window=1,
    )
    assert np.isnan(dup["pdr_summary"].loc[0, "sampling_rate_hz"])


def test_pdr_automatic_millisecond_sampling_and_no_peak_path():
    dat = pd.DataFrame(
        {
            "CNT": [0.0, 20.0, 40.0, 60.0, 80.0],
            "HRP": [0.0, 0.1, 0.2, 0.3, 0.4],
        }
    )
    out = gp.extract_gazepoint_pdr_signals(
        dat,
        sampling_rate=None,
        smooth_window=1,
    )
    assert out["pdr_summary"].loc[0, "sampling_rate_hz"] == 50.0
    assert out["pdr_summary"].loc[0, "n_pulses"] == 0


def test_pdr_short_pulse_feature_rate_path():
    dat = pd.DataFrame(
        {
            "CNT": np.arange(9, dtype=float) * 0.25,
            "HRP": [0.0, 1.0, 0.0, 1.2, 0.0, 0.9, 0.0, 1.1, 0.0],
        }
    )
    out = gp.extract_gazepoint_pdr_signals(
        dat,
        sampling_rate=None,
        min_peak_distance_s=0.1,
        smooth_window=1,
    )
    assert out["pdr_summary"].loc[0, "n_pulses"] == 4
    assert out["pdr_summary"].loc[0, "status"] == "pdr_rate_not_estimated"


def test_pdr_feature_rate_short_grid_path():
    times = np.arange(21, dtype=float) * 0.15
    peaks = np.linspace(0.8, 1.4, 10)
    signal = np.zeros(21, dtype=float)
    signal[1:20:2] = peaks
    dat = pd.DataFrame({"CNT": times, "HRP": signal})
    out = gp.extract_gazepoint_pdr_signals(
        dat,
        sampling_rate=None,
        min_peak_distance_s=0.1,
        smooth_window=1,
        pdr_resample_rate=4,
    )
    assert out["pdr_summary"].loc[0, "n_pulses"] == 10
    assert np.isnan(out["pdr_summary"].loc[0, "pav_resp_rate_hz"])


def test_pdr_feature_rate_interpolated_constant_path():
    peak_times = [0.10, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.00, 4.01]
    times = [0.0]
    values = [0.0]
    for i, peak_time in enumerate(peak_times):
        if peak_time > times[-1]:
            times.append(peak_time)
            values.append(2.0 if i == len(peak_times) - 1 else 1.0)
        if i < len(peak_times) - 1:
            next_peak = peak_times[i + 1]
            trough_time = peak_time + (next_peak - peak_time) / 2
            times.append(trough_time)
            values.append(0.0)
    times.append(4.02)
    values.append(0.0)
    dat = pd.DataFrame({"CNT": times, "HRP": values})
    out = gp.extract_gazepoint_pdr_signals(
        dat,
        sampling_rate=None,
        min_peak_distance_s=0.001,
        smooth_window=1,
        pdr_resample_rate=4,
    )
    assert out["pdr_summary"].loc[0, "n_pulses"] >= 10


def test_rsa_short_and_short_grid_power_paths():
    short = pd.DataFrame(
        {"CNT": np.arange(5, dtype=float), "IBI": [0.80, 0.82, 0.79, 0.83, 0.81]}
    )
    s = gp.calculate_gazepoint_rsa(short)
    assert np.isnan(s["rsa_summary"].loc[0, "rsa_pb_log_power_proxy"])

    compact = pd.DataFrame(
        {
            "CNT": np.linspace(0.0, 3.0, 8),
            "IBI": 0.8 + 0.03 * np.sin(np.linspace(0.0, 2 * np.pi, 8)),
        }
    )
    c = gp.calculate_gazepoint_rsa(compact, resample_rate=4)
    assert np.isnan(c["rsa_summary"].loc[0, "rsa_pb_log_power_proxy"])


def test_rsa_pdr_timeseries_too_short_for_p2t_path():
    ppg = pd.DataFrame(
        {
            "CNT": np.arange(9, dtype=float) * 0.25,
            "HRP": [0.0, 1.0, 0.0, 1.2, 0.0, 0.9, 0.0, 1.1, 0.0],
        }
    )
    pdr = gp.extract_gazepoint_pdr_signals(
        ppg,
        min_peak_distance_s=0.1,
        smooth_window=1,
    )
    assert len(pdr["pdr_timeseries"]) == 3

    t = np.arange(20, dtype=float) * 0.5
    ibi = pd.DataFrame({"CNT": t, "IBI": 0.8 + 0.03 * np.sin(t)})
    rsa = gp.calculate_gazepoint_rsa(ibi, pdr=pdr)
    assert "rsa_p2t_proxy" in rsa["rsa_summary"]
