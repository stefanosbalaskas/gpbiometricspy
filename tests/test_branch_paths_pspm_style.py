import json

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_pspm_public_preprocessing_helper_guardrails():
    out = gp.preprocess_gazepoint_scr_pspm_style(
        np.array([1.0, 2.0, 3.0]),
        sampling_rate_hz=10,
        min_valid_island_seconds=0,
        smoothing_seconds=0,
    )
    assert len(out["signal"]) == 3

    with pytest.raises(ValueError, match="Invalid `response`"):
        gp.create_gazepoint_pspm_glm_design(
            pd.DataFrame({"onset_time_s": [0.2]}),
            np.array([0.0, 0.1, 0.2]),
            response="invalid",
        )


def test_pspm_marker_and_session_residual_paths():
    markers = pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "TTL0": [0, 0, 0]})

    with pytest.raises(ValueError, match="Invalid `edge`"):
        gp.extract_gazepoint_markerinfo_pspm_style(markers, "TTL0", "time_s", edge="bad")
    with pytest.raises(ValueError, match="Missing marker columns"):
        gp.extract_gazepoint_markerinfo_pspm_style(markers, "missing", "time_s")

    combined = gp.combine_gazepoint_marker_channels_pspm_style(markers, "TTL0", "time_s")
    assert combined["markers"].empty
    assert combined["data"]["pspm_marker"].isna().all()

    empty = gp.split_gazepoint_sessions_pspm_style(
        pd.DataFrame({"time_s": pd.Series(dtype=float)}), "time_s"
    )
    assert empty["data"].empty and empty["sessions"].empty

    unsplit = gp.split_gazepoint_sessions_pspm_style(
        pd.DataFrame({"time_s": [0.0, 0.1, 0.2], "scr": [1.0, 1.1, 1.2]}),
        "time_s",
        reset_time=False,
    )
    assert "pspm_session_time_s" not in unsplit["data"].columns
    assert len(unsplit["split_data"]) == 1


def test_pspm_scr_and_segment_validation_residual_paths():
    with pytest.raises(ValueError, match="`signal_col` not found"):
        gp.preprocess_gazepoint_scr_pspm_style(
            pd.DataFrame({"time_s": [0.0, 0.1], "GSR": [1.0, 1.1]}),
            signal_col="missing",
            time_col="time_s",
            sampling_rate_hz=10,
        )

    with pytest.raises(ValueError, match="Could not infer a valid sampling rate"):
        gp.preprocess_gazepoint_scr_pspm_style(
            pd.DataFrame({"time_s": [0.0], "GSR": [1.0]}),
            signal_col="GSR",
            time_col="time_s",
        )

    signal = pd.DataFrame({"time_s": [0.0, 0.5, 1.0], "scr": [1.0, 1.1, 1.2]})
    events = pd.DataFrame({"onset_time_s": [100.0]})

    with pytest.raises(ValueError, match="`signal_col` not found"):
        gp.extract_gazepoint_segments_pspm_style(signal, events, "missing", "time_s")
    with pytest.raises(ValueError, match="`events` must contain `event_time_col`"):
        gp.extract_gazepoint_segments_pspm_style(signal, pd.DataFrame({"x": [1]}), "scr", "time_s")

    no_overlap = gp.extract_gazepoint_segments_pspm_style(
        signal, events, "scr", "time_s", pre_s=0.1, post_s=0.1
    )
    assert no_overlap.empty


def test_pspm_design_residual_guardrails_and_nonfinite_onset():
    events = pd.DataFrame({"onset_time_s": [0.1]})

    with pytest.raises(ValueError, match="At least three time points"):
        gp.create_gazepoint_pspm_glm_design(events, np.array([0.0, 0.1]))

    with pytest.raises(ValueError, match="Could not infer sampling interval"):
        gp.create_gazepoint_pspm_glm_design(events, np.array([1.0, 1.0, 1.0]))

    d = gp.create_gazepoint_pspm_glm_design(
        pd.DataFrame({"onset_time_s": [np.nan], "condition": ["A"]}),
        np.array([0.0, 0.1, 0.2, 0.3]),
    )
    assert np.allclose(d["pspm_A"], 0.0)


def test_pspm_glm_fit_residual_guardrails():
    data = pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "scr": [1.0, 2.0, 3.0]})
    design = pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "x": [1.0, 1.0, 1.0]})

    with pytest.raises(ValueError, match="`signal_col` not found"):
        gp.fit_gazepoint_convolution_glm(data, design, "missing", "time_s")
    with pytest.raises(ValueError, match="`design` must be a data frame containing `design_time_col`"):
        gp.fit_gazepoint_convolution_glm(data, pd.DataFrame({"x": [1.0]}), "scr", "time_s")

    with pytest.raises(ValueError, match="Insufficient finite signal samples for interpolation"):
        gp.fit_gazepoint_convolution_glm(
            pd.DataFrame({"time_s": [0.0, 1.0], "scr": [1.0, np.nan]}),
            pd.DataFrame({"time_s": [0.0, 0.5, 1.0], "x": [1.0, 1.0, 1.0]}),
            "scr",
            "time_s",
        )

    with pytest.raises(ValueError, match="No regressors found"):
        gp.fit_gazepoint_convolution_glm(data, design[["time_s"]], "scr", "time_s", regressor_cols=[])

    with pytest.raises(ValueError, match="Regressors not found"):
        gp.fit_gazepoint_convolution_glm(data, design, "scr", "time_s", regressor_cols=["missing"])

    with pytest.raises(ValueError, match="No complete rows available"):
        gp.fit_gazepoint_convolution_glm(
            data,
            pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "x": [np.nan, np.nan, np.nan]}),
            "scr",
            "time_s",
        )


def test_pspm_export_residual_paths(tmp_path):
    with pytest.raises(TypeError, match="PsPM-style GLM result"):
        gp.export_gazepoint_pspm_model_estimates({}, tmp_path / "bad.csv")

    model = {
        "coefficients": pd.DataFrame({"term": ["x"], "estimate": [1.0]}),
        "summary": pd.DataFrame({"n": [3]}),
        "predictions": pd.DataFrame({"time_s": [0.0], "fitted": [1.0]}),
    }

    manifest = gp.export_gazepoint_pspm_model_estimates(
        model,
        tmp_path / "explicit",
        format="csv",
        include_predictions=False,
    )
    assert manifest["role"].tolist() == ["coefficients", "summary"]
    assert (tmp_path / "explicit.csv").exists()

    with pytest.raises(ValueError, match="Invalid `format`"):
        gp.export_gazepoint_pspm_model_estimates(model, tmp_path / "bad", format="yaml")

    model_with_array = dict(model)
    model_with_array["kernel"] = np.array([0.0, 1.0])
    json_manifest = gp.export_gazepoint_pspm_model_estimates(
        model_with_array, tmp_path / "model.json", format="json"
    )
    assert json_manifest.iloc[0]["role"] == "model_json"
    payload = json.loads((tmp_path / "model.json").read_text(encoding="utf-8"))
    assert payload["kernel"] == [0.0, 1.0]
