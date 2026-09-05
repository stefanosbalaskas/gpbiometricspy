from __future__ import annotations

import pandas as pd
import pytest

import gpbiometricspy as gp


def _summary_frame():
    return pd.DataFrame(
        {
            "aoi_label": ["A", "B"],
            "signal": ["GSR", "GSR"],
            "mean_value": [1.0, 2.0],
            "n_rows": [3, 3],
            "n_finite": [3, 3],
            "summary_status": ["usable", "usable"],
        }
    )


def test_aoi_summary_input_and_detection_guardrails():
    with pytest.raises(TypeError, match="data frame"):
        gp.summarise_gazepoint_aoi_biometrics([1, 2, 3])

    with pytest.raises(ValueError, match="No biometric signal"):
        gp.summarise_gazepoint_aoi_biometrics(pd.DataFrame({"AOI": ["A", "B"]}))

    data = pd.DataFrame({"AOI": ["A", "B"], "GSR": [1.0, 2.0]})
    with pytest.raises(ValueError, match="group_cols"):
        gp.summarise_gazepoint_aoi_biometrics(data, group_cols="participant")
    with pytest.raises(ValueError, match="time_col"):
        gp.summarise_gazepoint_aoi_biometrics(data, time_col="missing_time")
    with pytest.raises(TypeError, match="drop_missing_aoi"):
        gp.summarise_gazepoint_aoi_biometrics(data, drop_missing_aoi="yes")
    with pytest.raises(ValueError, match="min_rows"):
        gp.summarise_gazepoint_aoi_biometrics(data, min_rows=0)


def test_aoi_summary_ungrouped_public_path():
    out = gp.summarise_gazepoint_aoi_biometrics(
        pd.DataFrame({"AOI": ["A", "A", "B"], "GSR": [1.0, 1.2, 2.0]}),
        group_cols=[],
    )
    assert set(out["summary"].group_id) == {"all"}
    assert out["overview"].iloc[0].group_count == 1


def test_aoi_model_guardrails_and_missing_predictor_skip():
    summary = _summary_frame()

    with pytest.raises(ValueError, match="standardise_within"):
        gp.prepare_gazepoint_aoi_biometrics_model_data(
            summary,
            standardise_within="invalid",
        )

    with pytest.raises(ValueError, match="min_rows"):
        gp.prepare_gazepoint_aoi_biometrics_model_data(summary, min_rows=0)

    out = gp.prepare_gazepoint_aoi_biometrics_model_data(
        summary,
        predictor_cols=["aoi_label", "missing_predictor"],
        factor_cols=["aoi_label"],
        group_cols=[],
    )
    assert "missing_predictor" not in out["model_data"].columns
    assert "missing_predictor" not in set(out["variable_summary"].variable)
    assert "aoi_label" in out["model_formulas"].iloc[0].formula


def test_aoi_plot_guardrails():
    summary = _summary_frame()

    with pytest.raises(ValueError, match="plot_type"):
        gp.plot_gazepoint_aoi_biometrics(summary, plot_type="invalid")

    with pytest.raises(ValueError, match="group_col"):
        gp.plot_gazepoint_aoi_biometrics(summary, group_col="participant")
