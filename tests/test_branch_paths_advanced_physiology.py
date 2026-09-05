from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_ipfm_insufficient_beats_public_path():
    out = gp.model_gazepoint_hrv_ipfm(
        pd.DataFrame({"IBI": [1000.0, 1000.0]}),
        ibi_col="IBI",
        ibi_units="milliseconds",
    )
    assert out["summary"].iloc[0].status == "insufficient_beats"
    assert out["overview"].iloc[0].status == "ipfm_model_failed"


def test_external_eda_explicit_millisecond_and_second_time_units():
    ms = gp.prepare_gazepoint_ledalab_input(
        pd.DataFrame({"time": [0.0, 1000.0, 2000.0], "EDA": [1.0, 1.1, 1.2]}),
        eda_col="EDA",
        time_col="time",
        time_unit="ms",
    )
    assert ms["signal_table"].detected_time_unit.eq("milliseconds").all()
    np.testing.assert_allclose(ms["signal_table"].time_s, [0.0, 1.0, 2.0])

    sec = gp.prepare_gazepoint_pspm_input(
        pd.DataFrame({"time": [0.0, 1.0, 2.0], "EDA": [1.0, 1.1, 1.2]}),
        eda_col="EDA",
        time_col="time",
        time_unit="seconds",
    )
    assert sec["signal_table"].detected_time_unit.eq("seconds").all()
    np.testing.assert_allclose(sec["signal_table"].time_s, [0.0, 1.0, 2.0])


def test_response_pattern_missing_inferred_column_raises():
    with pytest.raises(ValueError, match="No EDA response column"):
        gp.classify_gazepoint_eda_response_pattern(
            pd.DataFrame({"unrelated": [1.0, 2.0, 3.0]})
        )


def test_bilateral_asymmetry_without_time_column():
    out = gp.extract_gazepoint_bilateral_eda_asymmetry(
        pd.DataFrame({"left": [1.0, 1.2, 1.4], "right": [0.9, 1.0, 1.1]}),
        left_col="left",
        right_col="right",
        time_col=None,
    )
    ts = out["asymmetry_timeseries"]
    assert "time" not in ts.columns
    assert ts["beda_difference_gradient"].isna().all()


def test_quantization_noise_existing_output_guard():
    data = pd.DataFrame({
        "signal": [1.0, 1.1, 1.2],
        "signal_jitter": [1.0, 1.1, 1.2],
    })
    with pytest.raises(ValueError, match="already exists"):
        gp.denoise_gazepoint_quantization_noise(
            data,
            signal_cols="signal",
            resolution=0.1,
            output_suffix="_jitter",
            overwrite=False,
        )


def test_edr_pca_insufficient_complete_and_unscaled_paths():
    sparse = gp.extract_gazepoint_edr_pca(
        pd.DataFrame({"ecg_a": [1.0, 2.0], "ecg_b": [2.0, 3.0]}),
        ecg_cols=["ecg_a", "ecg_b"],
        n_components=1,
    )
    assert sparse["edr_timeseries"]["edr_pca_status"].eq(
        "insufficient_complete_ecg_morphology"
    ).all()

    unscaled = gp.extract_gazepoint_edr_pca(
        pd.DataFrame(
            {
                "ecg_a": [1.0, 2.0, 4.0, 7.0],
                "ecg_b": [2.0, 2.5, 5.0, 8.0],
            }
        ),
        ecg_cols=["ecg_a", "ecg_b"],
        n_components=1,
        scale=False,
    )
    assert unscaled["overview"].iloc[0].status == "edr_pca_extracted"
    assert unscaled["edr_timeseries"]["edr_pca_pc1"].notna().all()


def test_skin_potential_threshold_and_direction_paths():
    no_threshold = gp.analyze_gazepoint_skin_potential(
        pd.DataFrame({"time": [0.0, 1.0, 2.0], "sp": [1.0, 1.0, 1.0]}),
        sp_col="sp",
        time_col="time",
        response_threshold=None,
    )
    assert no_threshold["response_table"].empty

    positive = gp.analyze_gazepoint_skin_potential(
        pd.DataFrame({"time": [0.0, 1.0, 2.0], "sp": [0.0, 1.0, 1.0]}),
        sp_col="sp",
        time_col="time",
        response_direction="positive",
        response_threshold=0.5,
    )
    assert len(positive["response_table"]) == 1
    assert positive["response_table"].iloc[0].response_polarity == "positive"

    negative = gp.analyze_gazepoint_skin_potential(
        pd.DataFrame({"time": [0.0, 1.0, 2.0], "sp": [1.0, 0.0, 0.0]}),
        sp_col="sp",
        time_col="time",
        response_direction="negative",
        response_threshold=0.5,
    )
    assert len(negative["response_table"]) == 1
    assert negative["response_table"].iloc[0].response_polarity == "negative"
