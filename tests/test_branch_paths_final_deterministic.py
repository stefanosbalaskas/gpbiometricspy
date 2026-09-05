import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_adaptive_ema_without_time_column_success_path():
    dat = pd.DataFrame({"GSR_US": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]})
    out = gp.standardise_gazepoint_adaptive_ema(dat, alpha=0.2)
    assert out.attrs["adaptive_ema_overview"]["status"] == "adaptive_ema_normalization_complete"
    assert np.isfinite(out["GSR_US_adaptive_ema"]).all()


def test_downsample_additional_public_validation_paths():
    d = pd.DataFrame(
        {
            "time": [0.0, 1.0, 2.0],
            "group": ["a", "a", "a"],
            "x": [1.0, 2.0, 3.0],
        }
    )
    with pytest.raises(ValueError, match="must not include `time_col`"):
        gp.downsample_gazepoint_data(
            d, "time", signal_cols="x", group_cols="time", interval=1
        )
    with pytest.raises(ValueError, match="No numeric signal columns"):
        gp.downsample_gazepoint_data(
            pd.DataFrame({"time": [0.0, 1.0], "label": ["a", "b"]}),
            "time",
            interval=1,
        )
    with pytest.raises(ValueError, match="signal_cols.*not found"):
        gp.downsample_gazepoint_data(d, "time", signal_cols="missing", interval=1)


def test_sampling_audit_additional_validation_and_estimated_status():
    base = pd.DataFrame({"TIME": [0.0, 0.1, 0.2]})
    with pytest.raises(ValueError, match="Unsupported `time_unit`"):
        gp.audit_gazepoint_biometric_sampling(base, time_unit="minutes")
    with pytest.raises(ValueError, match="time_column.*not found"):
        gp.audit_gazepoint_biometric_sampling(base, time_column="missing")
    with pytest.raises(ValueError, match="group_columns.*not found"):
        gp.audit_gazepoint_biometric_sampling(base, group_columns="participant")

    estimated = gp.audit_gazepoint_biometric_sampling(
        base,
        time_column="TIME",
        expected_rate_hz=None,
    )
    assert estimated.loc[0, "rate_status"] == "estimated"
    assert estimated.loc[0, "estimated_rate_hz"] == pytest.approx(10.0)


def test_hrv_feature_public_validation_and_explicit_column_paths():
    with pytest.raises(TypeError, match="data frame"):
        gp.summarise_gazepoint_hrv_features([1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="group_cols"):
        gp.summarise_gazepoint_hrv_features(
            pd.DataFrame({"IBI": [1.0, 1.0, 1.0]}), group_cols="missing"
        )
    with pytest.raises(ValueError, match="time_col"):
        gp.summarise_gazepoint_hrv_features(
            pd.DataFrame({"IBI": [1.0, 1.0, 1.0]}), time_col="missing"
        )
    with pytest.raises(ValueError, match="min_valid_ibi"):
        gp.summarise_gazepoint_hrv_features(
            pd.DataFrame({"IBI": [1.0, 1.0, 1.0]}), min_valid_ibi=0
        )
    with pytest.raises(ValueError, match="validity/vendor flag"):
        gp.summarise_gazepoint_hrv_features(
            pd.DataFrame({"HRV": [1.0, 1.0, 1.0]}), ibi_col="HRV"
        )
    with pytest.raises(TypeError, match="numeric"):
        gp.summarise_gazepoint_hrv_features(
            pd.DataFrame({"IBI": ["a", "b", "c"]}), ibi_col="IBI"
        )

    explicit = gp.summarise_gazepoint_hrv_features(
        pd.DataFrame({"IBI": [0.9, 1.0, 1.1]}),
        ibi_col="IBI",
        ibi_unit="seconds",
    )
    assert explicit["settings"]["ibi_col"] == "IBI"
    assert explicit["features"].loc[0, "unit_detected"] == "seconds"


def test_ibi_window_missing_columns_and_no_validity_column():
    with pytest.raises(ValueError, match="group_columns.*not found"):
        gp.summarise_gazepoint_ibi_hrv_windows(
            pd.DataFrame({"IBI": [1.0]}), "participant"
        )
    with pytest.raises(ValueError, match="ibi_column.*not found"):
        gp.summarise_gazepoint_ibi_hrv_windows(
            pd.DataFrame({"participant": ["p1"], "x": [1.0]}), "participant"
        )

    out = gp.summarise_gazepoint_ibi_hrv_windows(
        pd.DataFrame(
            {"participant": ["p1", "p1", "p1"], "IBI": [0.9, 1.0, 1.1]}
        ),
        "participant",
        validity_column=None,
    )
    assert np.isnan(out.loc[0, "validity_column"])
    assert out.loc[0, "ibi_usable_rows"] == 3


def test_exclusion_recommendation_type_row_level_and_no_participant_paths():
    with pytest.raises(TypeError, match="data frame"):
        gp.recommend_gazepoint_biometric_exclusions(
            [1, 2, 3], data_is_window_summary=True
        )
    with pytest.raises(ValueError, match="group_columns.*supplied"):
        gp.recommend_gazepoint_biometric_exclusions(
            pd.DataFrame({"GSR_US": [1.0]}), data_is_window_summary=False
        )

    windows = pd.DataFrame(
        {
            "gsr_usable_pct": [100.0],
            "hr_usable_pct": [100.0],
            "dial_usable_pct": [100.0],
        }
    )
    out = gp.recommend_gazepoint_biometric_exclusions(
        windows,
        data_is_window_summary=True,
        participant_column=None,
    )
    assert out["participant_recommendations"].empty
    assert np.isnan(out["overview"].loc[0, "n_participants"])
    assert out["window_recommendations"].loc[0, "recommendation"] == "keep"


def test_pupil_baseline_insufficient_reference_rows_path():
    d = pd.DataFrame(
        {
            "trial": [1, 1, 1],
            "time": [-200.0, 0.0, 100.0],
            "pupil": [3.0, 4.0, 4.2],
        }
    )
    out = gp.baseline_correct_gazepoint_pupil(
        d,
        pupil_col="pupil",
        trial_cols="trial",
        baseline_window=(-250, -150),
        min_baseline_rows=2,
    )
    assert out.attrs["pupil_baseline_summary"]["status"] == "pupil_baseline_correction_failed"
    assert out.attrs["pupil_baseline_table"][0]["status"] == "insufficient_baseline_rows"
    assert out["pupil_baseline_corrected"].isna().all()


def test_eye_simulator_parameter_guardrails_and_zero_invalid_prop():
    with pytest.raises(TypeError, match="named list/dict"):
        gp.simulate_gazepoint_eye_data([1, 2])
    with pytest.raises(ValueError, match="single finite numeric"):
        gp.simulate_gazepoint_eye_data({"sampling_rate_hz": "fast"})
    with pytest.raises(ValueError, match=">= 1"):
        gp.simulate_gazepoint_eye_data({"sampling_rate_hz": 0})
    with pytest.raises(ValueError, match="<= 1"):
        gp.simulate_gazepoint_eye_data(
            {"n": 20, "include_invalid_gaze": True, "invalid_gaze_prop": 1.5}
        )
    with pytest.raises(ValueError, match="screen_bounds"):
        gp.simulate_gazepoint_eye_data({"screen_bounds": [0, 1, 0]})

    no_invalid = gp.simulate_gazepoint_eye_data(
        {
            "n": 40,
            "seed": 7,
            "include_invalid_gaze": True,
            "invalid_gaze_prop": 0,
        }
    )
    assert no_invalid["gaze_valid_simulated"].all()


def test_biometric_simulator_sampling_and_no_pulse_paths():
    with pytest.raises(ValueError, match="sampling_rate"):
        gp.simulate_gazepoint_biometrics(n_seconds=1, sampling_rate=0)

    short = gp.simulate_gazepoint_biometrics(
        n_seconds=0.2,
        sampling_rate=10,
        scr_onsets=[],
        pulse_rate_bpm=30,
        include_ttl=False,
        seed=2,
    )
    assert short["ground_truth"]["pulse_peaks"].empty
    assert (short["data"]["TTL0"] == 0).all()
    assert np.isfinite(short["data"]["IBI"]).all()
