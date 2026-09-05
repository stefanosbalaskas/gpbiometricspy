from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_eda_artifact_public_validation_and_alternative_status_paths():
    with pytest.raises(TypeError, match="data frame"):
        gp.audit_gazepoint_eda_artifacts("bad")
    with pytest.raises(ValueError, match="group_cols"):
        gp.audit_gazepoint_eda_artifacts(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), group_cols="missing"
        )
    with pytest.raises(ValueError, match="No usable EDA"):
        gp.audit_gazepoint_eda_artifacts(pd.DataFrame({"x": [1.0, 2.0]}))
    with pytest.raises(TypeError, match="numeric"):
        gp.audit_gazepoint_eda_artifacts(
            pd.DataFrame({"GSR_US": ["a", "b"]}), signal_col="GSR_US"
        )
    with pytest.raises(ValueError, match="time_col"):
        gp.audit_gazepoint_eda_artifacts(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), time_col="missing"
        )

    short = gp.audit_gazepoint_eda_artifacts(
        pd.DataFrame({"GSR_US": [1.0, 2.0]}),
        signal_col="GSR_US",
        flat_run_length=3,
        zero_run_length=3,
    )
    assert short["overview"].loc[0, "status"] == "pass"

    flagged = gp.audit_gazepoint_eda_artifacts(
        pd.DataFrame({"GSR_US": [np.nan, np.inf, -1.0, 0.0, 5.0, 5.0]}),
        signal_col="GSR_US",
        flat_run_length=2,
        zero_run_length=1,
        saturation_min=0.1,
        saturation_max=4.0,
        negative_allowed=False,
    )
    assert flagged["overview"].loc[0, "artifact_rows"] > 0
    assert flagged["overview"].loc[0, "negative_conductance_rows"] == 1
    assert flagged["overview"].loc[0, "out_of_bounds_rows"] >= 2

    phasic = gp.audit_gazepoint_eda_artifacts(
        pd.DataFrame({"GSR_US_PHASIC": [-0.2, 0.0, 0.2]}),
        signal_col="GSR_US_PHASIC",
    )
    assert phasic["settings"]["negative_allowed"] is True


def test_scr_peak_validation_no_signal_and_incomplete_recovery_paths():
    base = pd.DataFrame({"EDA": [0.0, 1.0, 0.0]})
    with pytest.raises(ValueError, match="amplitude_min"):
        gp.detect_gazepoint_scr_peaks(base, signal_col="EDA", amplitude_min=-0.1)
    with pytest.raises(ValueError, match="recovery_fraction"):
        gp.detect_gazepoint_scr_peaks(base, signal_col="EDA", recovery_fraction=1.0)
    with pytest.raises(ValueError, match="min_peak_distance"):
        gp.detect_gazepoint_scr_peaks(base, signal_col="EDA", min_peak_distance=0)
    with pytest.raises(ValueError, match="No usable SCR"):
        gp.detect_gazepoint_scr_peaks(pd.DataFrame({"x": [0.0, 1.0, 0.0]}))
    with pytest.raises(TypeError, match="numeric"):
        gp.detect_gazepoint_scr_peaks(
            pd.DataFrame({"EDA": ["a", "b", "c"]}), signal_col="EDA"
        )

    incomplete = gp.detect_gazepoint_scr_peaks(
        pd.DataFrame({"EDA": [0.0, 1.0, 0.9, 0.8, 0.7]}),
        signal_col="EDA",
        prefer_vendor_phasic=False,
        amplitude_min=0.1,
        recovery_fraction=0.5,
    )
    assert incomplete["overview"].loc[0, "detected_peaks"] == 1
    assert incomplete["peaks"].loc[0, "status"] == "detected_incomplete_recovery"

    tiny = gp.detect_gazepoint_scr_peaks(
        pd.DataFrame({"EDA": [0.0, 0.1]}),
        signal_col="EDA",
        prefer_vendor_phasic=False,
    )
    assert tiny["group_summary"].loc[0, "status"] == "insufficient_signal"


def test_scr_event_window_public_validation_empty_and_selection_paths():
    peaks = pd.DataFrame(
        {
            "peak_id": [1, 2],
            "peak_time": [2.0, 3.0],
            "onset_time": [1.5, 2.5],
            "amplitude": [0.03, 0.08],
            "rise_time": [0.5, 0.5],
            "recovery_time_after_peak": [2.0, 2.0],
            "status": ["detected", "detected"],
        }
    )
    events = pd.DataFrame({"event_time": [1.0]})

    with pytest.raises(ValueError, match="collapse_simultaneous_events"):
        gp.summarise_gazepoint_scr_event_windows(
            scr_peaks=peaks,
            events=events,
            collapse_simultaneous_events="yes",
        )
    with pytest.raises(ValueError, match="peak_selection"):
        gp.summarise_gazepoint_scr_event_windows(
            scr_peaks=peaks, events=events, peak_selection="bad"
        )
    with pytest.raises(ValueError, match="event_detection"):
        gp.summarise_gazepoint_scr_event_windows(
            scr_peaks=peaks, events=events, event_detection="bad"
        )

    empty = gp.summarise_gazepoint_scr_event_windows(
        scr_peaks=pd.DataFrame(), data=None, ttl_cols=None
    )
    assert empty["overview"].loc[0, "status"] == "fail_no_events"

    with pytest.raises(ValueError, match="event time"):
        gp.summarise_gazepoint_scr_event_windows(
            data=pd.DataFrame({"TTL0": [0, 1, 0]}),
            scr_peaks=pd.DataFrame(),
            ttl_cols="TTL0",
        )
    with pytest.raises(ValueError, match="event_time_col"):
        gp.summarise_gazepoint_scr_event_windows(
            scr_peaks=pd.DataFrame(), events=pd.DataFrame({"label": ["a"]})
        )
    with pytest.raises(ValueError, match="missing grouping columns"):
        gp.summarise_gazepoint_scr_event_windows(
            scr_peaks=peaks.assign(participant="P1"),
            events=events,
            group_cols="participant",
        )

    first = gp.summarise_gazepoint_scr_event_windows(
        scr_peaks=peaks,
        events=events,
        analysis_window=(0, 4),
        response_window=(0.5, 3),
        peak_selection="first_peak",
    )
    assert first["event_table"].loc[0, "selected_peak_id"] == "1"

    no_response = gp.summarise_gazepoint_scr_event_windows(
        scr_peaks=peaks,
        events=pd.DataFrame({"event_time": [0.0]}),
        analysis_window=(0, 4),
        response_window=(0.1, 0.5),
    )
    assert no_response["overview"].loc[0, "status"] == "warn_no_scr_responses"
    assert no_response["event_table"].loc[0, "event_status"] == "no_peaks_in_response_window"


def test_nonresponder_hurdle_and_sensitivity_validation_paths():
    with pytest.raises(ValueError, match="min_events"):
        gp.screen_gazepoint_eda_nonresponders(
            pd.DataFrame({"response_flag": [0]}), min_events=-1
        )
    with pytest.raises(ValueError, match="min_response_rate"):
        gp.screen_gazepoint_eda_nonresponders(
            pd.DataFrame({"response_flag": [0]}), min_response_rate=1.1
        )

    insufficient = gp.screen_gazepoint_eda_nonresponders(
        pd.DataFrame({"response_flag": [1], "scr_amplitude": [0.1]}),
        min_events=2,
    )
    assert insufficient["group_summary"].loc[0, "status"] == "insufficient_events"

    with pytest.raises(ValueError, match="response_col"):
        gp.prepare_gazepoint_scr_hurdle_model_data(
            pd.DataFrame({"scr_amplitude": [0.1]})
        )
    with pytest.raises(ValueError, match="Requested columns"):
        gp.prepare_gazepoint_scr_hurdle_model_data(
            pd.DataFrame({"response_flag": [1], "scr_amplitude": [0.1]}),
            predictor_cols="missing",
        )

    no_positive = gp.prepare_gazepoint_scr_hurdle_model_data(
        pd.DataFrame(
            {
                "response_flag": [0, 0],
                "scr_amplitude": [np.nan, np.nan],
                "condition": ["A", np.nan],
            }
        ),
        predictor_cols="condition",
        drop_missing_predictors=False,
    )
    assert no_positive["overview"].loc[0, "status"] == "warn_no_positive_amplitude_rows"

    with pytest.raises(TypeError, match="data frame"):
        gp.run_gazepoint_scr_threshold_sensitivity("bad")
    with pytest.raises(ValueError, match="min_peak_distance_values"):
        gp.run_gazepoint_scr_threshold_sensitivity(
            pd.DataFrame({"EDA": [0.0, 1.0, 0.0]}),
            signal_col="EDA",
            min_peak_distance_values=[0],
        )

    sensitivity = gp.run_gazepoint_scr_threshold_sensitivity(
        pd.DataFrame({"time": [0.0, 1.0, 2.0, 3.0], "EDA": [0.0, 1.0, 0.0, 0.0]}),
        signal_col="EDA",
        time_col="time",
        amplitude_min_values=[0.1],
        min_peak_distance_values=[1],
        events=pd.DataFrame({"event_time": [0.0]}),
        include_event_windows=True,
        keep_objects=True,
        analysis_window=(0, 3),
        response_window=(0.5, 2.5),
    )
    assert len(sensitivity["event_window_summary"]) == 1
    assert len(sensitivity["objects"]) == 1


def test_spectral_wavelet_and_tvsymp_failure_partial_paths():
    with pytest.raises(ValueError, match="eda_col"):
        gp.extract_gazepoint_eda_spectral_power(pd.DataFrame({"x": [1.0, 2.0]}))

    no_rate = gp.extract_gazepoint_eda_spectral_power(
        pd.DataFrame({"GSR_US": np.linspace(0.0, 1.0, 40)}), min_samples=4
    )
    assert no_rate["spectral_summary"].loc[0, "status"] == "insufficient_data"

    constant_time = gp.extract_gazepoint_eda_spectral_power(
        pd.DataFrame({"time": [1.0] * 40, "GSR_US": np.linspace(0.0, 1.0, 40)}),
        time_col="time",
        min_samples=4,
    )
    assert constant_time["overview"].loc[0, "status"] == "eda_spectral_power_failed"

    invalid_rate = gp.extract_gazepoint_eda_spectral_power(
        pd.DataFrame({"GSR_US": np.linspace(0.0, 1.0, 40)}),
        sampling_rate=0,
        min_samples=4,
    )
    assert invalid_rate["spectral_summary"].loc[0, "status"] == "insufficient_data"

    with pytest.raises(ValueError, match="Column"):
        gp.denoise_gazepoint_eda_wavelet(pd.DataFrame({"x": [1.0]}))
    with pytest.raises(ValueError, match="already exists"):
        gp.denoise_gazepoint_eda_wavelet(
            pd.DataFrame({"GSR_US": np.arange(8.0), "GSR_US_wavelet_denoised": 0.0})
        )

    short = gp.denoise_gazepoint_eda_wavelet(pd.DataFrame({"GSR_US": [1.0, 2.0, np.nan]}))
    assert short.attrs["wavelet_denoising_overview"]["status"] == "eda_wavelet_denoising_failed"

    mixed = pd.DataFrame(
        {
            "g": ["good"] * 10 + ["bad"] * 3,
            "GSR_US": list(np.linspace(0.0, 1.0, 10)) + [1.0, np.nan, 2.0],
        }
    )
    partial = gp.denoise_gazepoint_eda_wavelet(mixed, group_cols="g")
    assert partial.attrs["wavelet_denoising_overview"]["status"] == "eda_wavelet_denoising_partial"

    tv_no_rate = gp.extract_gazepoint_eda_tvsymp(
        pd.DataFrame({"CNT": [1.0] * 8, "GSR_US": np.arange(8.0)}),
        window_seconds=4,
    )
    assert tv_no_rate["overview"].loc[0, "status"] == "eda_tvsymp_failed"

    tv_missing = gp.extract_gazepoint_eda_tvsymp(
        pd.DataFrame(
            {
                "CNT": np.arange(8.0),
                "GSR_US": [1.0, np.nan, np.nan, np.nan, 1.0, np.nan, np.nan, np.nan],
            }
        ),
        sampling_rate=1,
        window_seconds=4,
        step_seconds=2,
        min_valid_fraction=0.75,
    )
    assert tv_missing["overview"].loc[0, "status"] == "eda_tvsymp_failed"


def test_nonlinear_hrv_alternative_and_validation_paths():
    fuzzy_short = gp.extract_gazepoint_hrv_fuzzy_csi(
        pd.DataFrame({"IBI": [0.8, 0.9, 1.0]}), min_intervals=3, m=2
    )
    assert fuzzy_short["features"].loc[0, "status"] == "fuzzy_csi_extracted"

    fuzzy_constant = gp.extract_gazepoint_hrv_fuzzy_csi(
        pd.DataFrame({"IBI": [0.8] * 5}), min_intervals=3
    )
    assert fuzzy_constant["overview"].loc[0, "status"] == "fuzzy_csi_failed"

    with pytest.raises(ValueError, match="scales"):
        gp.extract_gazepoint_hrv_rcmse(pd.DataFrame({"IBI": [0.8, 0.9]}), scales=[])

    coarse = gp.extract_gazepoint_hrv_rcmse(
        pd.DataFrame({"IBI": np.linspace(0.75, 0.95, 12)}),
        scales=[1, 10],
        min_intervals=5,
    )
    assert len(coarse["rcmse_by_scale"]) == 2
    assert coarse["rcmse_by_scale"].loc[
        coarse["rcmse_by_scale"].scale == 10, "status"
    ].iloc[0] == "rcmse_not_estimated"

    custom = gp.test_gazepoint_hrv_nonlinearity(
        pd.DataFrame({"IBI": np.linspace(0.75, 0.95, 9)}),
        statistic_fun=lambda x: float(np.mean(x)),
        surrogate_method="shuffle",
        n_surrogates=3,
        seed=2,
    )
    assert custom["results"].loc[0, "status"] == "surrogate_test_complete"
    assert len(custom["surrogate_statistics"]) == 3


def test_respiration_kalman_mad_and_drift_alternative_paths():
    kalman = gp.fuse_gazepoint_respiration_kalman(
        pd.DataFrame(
            {
                "time": [3.0, 2.0, 1.0, 0.0],
                "primary": [np.nan, 1.0, np.nan, 2.0],
                "secondary": [np.nan, np.nan, 1.5, 2.5],
            }
        ),
        primary_col="primary",
        secondary_col="secondary",
        time_col="time",
    )
    assert set(kalman["respiration_kalman_fused_status"]) >= {
        "missing",
        "primary_only",
        "secondary_only",
        "fused",
    }

    failed = gp.fuse_gazepoint_respiration_kalman(
        pd.DataFrame({"primary": [np.nan, np.nan], "secondary": [np.nan, np.nan]}),
        primary_col="primary",
        secondary_col="secondary",
    )
    assert failed.attrs["kalman_respiration_overview"]["status"] == "kalman_respiration_fusion_failed"

    wall = gp.flag_gazepoint_mad_artifacts(
        pd.DataFrame({"GSR_US": [0.0, 0.0, 10.0, 10.0]}),
        mad_multiplier=100,
        flatline_min_run=10,
        wall_abs_change=5,
    )
    assert wall["mad_artifact"].any()

    tiny = gp.audit_gazepoint_distributional_drift(
        pd.DataFrame({"session": [1, 2], "GSR_US": [1.0, 2.0]}),
        signal_cols="GSR_US",
    )
    assert np.isnan(tiny["drift_summary"].loc[0, "psi"])

    constant = gp.audit_gazepoint_distributional_drift(
        pd.DataFrame(
            {
                "session": [1, 1, 2, 2],
                "GSR_US": [1.0, 1.0, 1.0, 1.0],
            }
        ),
        signal_cols="GSR_US",
        reference_session=1,
    )
    assert constant["drift_summary"].loc[0, "psi"] == 0.0
    assert constant["drift_summary"].loc[0, "status"] == "pass"


def test_changepoint_and_recovery_no_sampling_no_event_paths():
    cp = gp.detect_gazepoint_doubly_stochastic_changepoints(
        pd.DataFrame({"CNT": [1.0] * 8, "signal": np.arange(8.0)}),
        signal_col="signal",
        window_seconds=2,
        step_seconds=1,
    )
    assert cp["overview"].loc[0, "status"] == "changepoint_scoring_complete"

    no_events = gp.extract_gazepoint_scr_recovery_times(
        pd.DataFrame({"CNT": np.arange(5.0), "GSR_US": np.arange(5.0)}),
        event_onset_col=None,
    )
    assert no_events["overview"].loc[0, "status"] == "no_events"

    outside = gp.extract_gazepoint_scr_recovery_times(
        pd.DataFrame(
            {
                "CNT": np.arange(5.0),
                "GSR_US": np.arange(5.0),
                "onset": [10.0, np.nan, np.nan, np.nan, np.nan],
            }
        ),
        event_onset_col="onset",
        peak_window_s=1,
    )
    assert outside["overview"].loc[0, "status"] == "no_events"

    rising = gp.extract_gazepoint_scr_recovery_times(
        pd.DataFrame(
            {
                "CNT": [0.0, 1.0, 2.0, 3.0],
                "GSR_US": [1.0, 2.0, 3.0, 4.0],
                "onset": [0.0, np.nan, np.nan, np.nan],
            }
        ),
        event_onset_col="onset",
        pre_onset_baseline_s=1,
        peak_window_s=3,
        recovery_window_s=3,
    )
    assert len(rising["recovery_table"]) == 1
    assert np.isnan(rising["recovery_table"].loc[0, "rec_tc"])
