from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_bids_sampling_eye_inference_and_auto_timestamp_residuals(tmp_path):
    single = pd.DataFrame(
        {"time_s": [0.0], "gaze_x": [0.1], "gaze_y": [0.2]}
    )
    one = gp.export_gazepoint_to_bids(
        single, tmp_path / "one", "01", "task", dry_run=True
    )
    assert not one["audit"]["ready_to_write"]
    assert np.isnan(one["audit"]["sampling_rate_hz"])

    constant = pd.DataFrame(
        {"time_s": [0.0, 0.0], "gaze_x": [0.1, 0.2], "gaze_y": [0.2, 0.3]}
    )
    no_positive_step = gp.export_gazepoint_to_bids(
        constant, tmp_path / "constant", "01", "task", dry_run=True
    )
    assert np.isnan(no_positive_step["audit"]["sampling_rate_hz"])

    ticks = pd.DataFrame(
        {"TIMETICK": [0.0, 10.0], "gaze_x": [0.1, 0.2], "gaze_y": [0.2, 0.3]}
    )
    tick_export = gp.export_gazepoint_to_bids(
        ticks, tmp_path / "ticks", "01", "task", dry_run=True
    )
    assert tick_export["settings"]["timestamp_units"] == "milliseconds"

    left = pd.DataFrame(
        {
            "TIME": [0.0, 1.0],
            "LPOGX": [0.1, 0.2],
            "LPOGY": [0.2, 0.3],
            "LPD": [3.0, 3.1],
        }
    )
    left_export = gp.export_gazepoint_to_bids(
        left, tmp_path / "left", "01", "task", recorded_eye="left", dry_run=True
    )
    assert left_export["settings"]["x_col"] == "LPOGX"
    assert left_export["settings"]["pupil_col"] == "LPD"

    right = pd.DataFrame(
        {
            "TIME": [0.0, 1.0],
            "RPOGX": [0.1, 0.2],
            "RPOGY": [0.2, 0.3],
            "RPD": [3.0, 3.1],
        }
    )
    right_export = gp.export_gazepoint_to_bids(
        right, tmp_path / "right", "01", "task", recorded_eye="right", dry_run=True
    )
    assert right_export["settings"]["x_col"] == "RPOGX"
    assert right_export["settings"]["pupil_col"] == "RPD"


def test_adapter_time_public_residual_paths():
    no_time = pd.DataFrame(
        {
            "participant": ["P1"],
            "trial": ["T1"],
            "gaze_x": [0.1],
            "gaze_y": [0.2],
        }
    )
    with pytest.raises(ValueError, match="detect time column"):
        gp.prepare_gazepoint_eyetrackingr_input(no_time)

    milliseconds = pd.DataFrame(
        {
            "participant": ["P1", "P1"],
            "trial": ["T1", "T1"],
            "time_ms": [100.0, 200.0],
            "gaze_x": [0.1, 0.2],
            "gaze_y": [0.2, 0.3],
        }
    )
    auto_ms = gp.prepare_gazepoint_eyetrackingr_input(milliseconds)
    assert auto_ms["data"].Time_ms.tolist() == [100.0, 200.0]

    explicit = gp.prepare_gazepoint_eyetrackingr_input(
        milliseconds,
        time_col="time_ms",
        time_unit="milliseconds",
        irregular="allow",
    )
    assert explicit["data"].Time_ms.tolist() == [100.0, 200.0]

    samples = pd.DataFrame(
        {
            "participant": ["P1", "P1"],
            "trial": ["T1", "T1"],
            "CNT": [5.0, 6.0],
            "gaze_x": [0.1, 0.2],
            "gaze_y": [0.2, 0.3],
        }
    )
    sampled = gp.prepare_gazepoint_eyetrackingr_input(
        samples, sampling_rate_hz=10.0, irregular="allow"
    )
    assert sampled["data"].Time_ms.tolist() == [500.0, 600.0]

    duplicate = pd.DataFrame(
        {
            "participant": ["P1", "P1"],
            "trial": ["T1", "T1"],
            "time_s": [0.0, 0.0],
            "gaze_x": [0.1, 0.2],
            "gaze_y": [0.2, 0.3],
        }
    )
    with pytest.raises(ValueError, match="Participant-trial-time"):
        gp.prepare_gazepoint_eyetrackingr_input(duplicate)


def test_public_gaze_required_column_and_preprocess_no_gaze_paths():
    with pytest.raises(ValueError, match="Required gaze columns"):
        gp.detect_gazepoint_fixations(
            pd.DataFrame({"time": [0.0, 0.1], "x": [0.1, 0.2]}),
            velocity_threshold=10.0,
        )

    no_gaze = gp.preprocess_gazepoint_all(
        pd.DataFrame({"signal": [1.0, 2.0]}),
        impute_missing=False,
        clean_pupil=False,
        filter_gaze=True,
    )
    assert "gaze_valid" not in no_gaze.columns


def test_autoencoder_public_guardrails_and_model_paths():
    with pytest.raises(ValueError, match="was not found"):
        gp.denoise_gazepoint_eda_autoencoder(pd.DataFrame({"x": [1.0]}))

    existing = pd.DataFrame(
        {
            "GSR_US": [1.0, 2.0],
            "GSR_US_autoencoder_denoised": [1.0, 2.0],
        }
    )
    with pytest.raises(ValueError, match="already exists"):
        gp.denoise_gazepoint_eda_autoencoder(existing)
    replaced = gp.denoise_gazepoint_eda_autoencoder(existing, overwrite=True)
    assert replaced.attrs["autoencoder_denoising_overview"].loc[0, "status"] == (
        "autoencoder_no_model_supplied"
    )

    all_missing = pd.DataFrame({"GSR_US": [np.nan, np.nan]})
    reconstructed = gp.denoise_gazepoint_eda_autoencoder(
        all_missing, model=lambda values: values, window_samples=2
    )
    assert reconstructed.attrs["autoencoder_denoising_overview"].loc[0, "status"] == (
        "autoencoder_reconstruction_complete"
    )
    assert reconstructed.GSR_US_autoencoder_denoised.tolist() == [0.0, 0.0]

    class PredictModel:
        def predict(self, values):
            return values

    predicted = gp.denoise_gazepoint_ppg_autoencoder(
        pd.DataFrame({"HRP": [1.0, 2.0]}),
        model=PredictModel(),
        window_samples=2,
    )
    assert predicted.HRP_autoencoder_denoised.tolist() == [1.0, 2.0]

    with pytest.raises(ValueError, match="length mismatch"):
        gp.denoise_gazepoint_eda_autoencoder(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}),
            model=lambda values: values[:1],
            window_samples=2,
        )


def test_point_process_empty_interval_and_missing_smoke_directory(tmp_path):
    one_event = gp.model_gazepoint_eda_point_process(
        pd.DataFrame(
            {
                "time": [0.0, 1.0, 2.0],
                "GSR_US": [1.0, 1.1, 1.2],
                "event": [False, True, False],
            }
        ),
        eda_col="GSR_US",
        time_col="time",
        event_indicator_col="event",
    )
    assert one_event["process_summary"].loc[0, "status"] == "insufficient_events"
    assert np.isnan(one_event["process_summary"].loc[0, "inverse_gaussian_mu"])

    with pytest.raises(FileNotFoundError, match="does not exist"):
        gp.run_gazepoint_real_data_smoke(tmp_path / "missing")
