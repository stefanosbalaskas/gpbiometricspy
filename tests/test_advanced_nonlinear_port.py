import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_nonlinear_hrv_and_eda_complexity_r_fixtures():
    hrv = pd.DataFrame({"participant": "p1", "IBI": 0.8 + 0.05 * np.sin(np.linspace(0, 4 * np.pi, 60))})
    out = gp.extract_gazepoint_hrv_nonlinear(hrv, group_cols=["participant"])
    assert out["overview"].loc[0, "status"] == "nonlinear_hrv_extracted"
    assert np.isfinite(out["features"].loc[0, "sd1"])
    assert np.isfinite(out["features"].loc[0, "sd2"])
    assert {"approximate_entropy", "dfa_alpha", "mse_mean", "mse_scale_1"} <= set(out["features"])

    rng = np.random.default_rng(1)
    hrv2 = pd.DataFrame({"participant": "p1", "IBI": 0.8 + 0.04 * np.sin(np.linspace(0, 10 * np.pi, 80)) + rng.normal(0, 0.005, 80)})
    out2 = gp.extract_gazepoint_hrv_nonlinear(hrv2, group_cols=["participant"], mse_scales=[1, 2, 3])
    assert list(c for c in out2["features"] if c.startswith("mse_scale_")) == ["mse_scale_1", "mse_scale_2", "mse_scale_3"]

    eda = pd.DataFrame({"participant": "p1", "GSR_US": np.sin(np.linspace(0, 8 * np.pi, 128)) + rng.normal(0, 0.05, 128)})
    eo = gp.extract_gazepoint_eda_complexity(eda, group_cols=["participant"])
    assert eo["overview"].loc[0, "status"] == "eda_complexity_extracted"
    assert np.isfinite(eo["features"].loc[0, "dfa_alpha"])

    short = gp.extract_gazepoint_hrv_nonlinear(pd.DataFrame({"IBI": [0.8] * 4}), min_intervals=10)
    assert short["features"].loc[0, "status"] == "insufficient_intervals"
    constant = gp.extract_gazepoint_eda_complexity(pd.DataFrame({"GSR_US": [1.0] * 40}))
    assert constant["features"].loc[0, "status"] == "insufficient_or_constant_signal"
    with pytest.raises(ValueError, match="mse_scales"):
        gp.extract_gazepoint_hrv_nonlinear(hrv, mse_scales=[0])


def test_fragmentation_and_asymmetry_r_fixtures_and_edge_states():
    frag_dat = pd.DataFrame({"participant": "p1", "IBI": [0.80, 0.82, 0.79, 0.83, 0.78, 0.84, 0.81, 0.85, 0.80, 0.86]})
    frag = gp.extract_gazepoint_hrv_fragmentation(frag_dat, group_cols=["participant"])
    assert np.isfinite(frag["features"].loc[0, "pip"])
    assert np.isfinite(frag["features"].loc[0, "ials"])

    asym_dat = pd.DataFrame({"participant": "p1", "IBI": [0.80, 0.82, 0.84, 0.81, 0.79, 0.83, 0.85, 0.82, 0.80, 0.86]})
    asym = gp.extract_gazepoint_hrv_asymmetry(asym_dat, group_cols=["participant"])
    assert {"guzik_index", "porta_index"} <= set(asym["features"])
    assert len(asym["run_table"]) > 0

    short = pd.DataFrame({"IBI": [0.8, 0.81, 0.82]})
    assert gp.extract_gazepoint_hrv_fragmentation(short)["features"].loc[0, "status"] == "insufficient_intervals"
    flat = pd.DataFrame({"IBI": [0.8] * 8})
    assert gp.extract_gazepoint_hrv_fragmentation(flat)["features"].loc[0, "status"] == "insufficient_nonzero_differences"
    assert gp.extract_gazepoint_hrv_asymmetry(flat)["features"].loc[0, "status"] == "insufficient_nonzero_differences"


def test_rqa_and_geometric_r_fixtures_and_insufficient_paths():
    rqa_dat = pd.DataFrame({"participant": "p1", "IBI": 0.8 + 0.04 * np.sin(np.linspace(0, 8 * np.pi, 80))})
    rqa = gp.extract_gazepoint_hrv_rqa(rqa_dat, group_cols=["participant"], embedding_dimension=2, delay=1)
    assert np.isfinite(rqa["features"].loc[0, "recurrence_rate"])
    assert np.isfinite(rqa["features"].loc[0, "determinism"])

    rng = np.random.default_rng(2)
    geo_dat = pd.DataFrame({"participant": "p1", "IBI": 0.8 + rng.normal(0, 0.03, 100)})
    geo = gp.extract_gazepoint_hrv_geometric(geo_dat, group_cols=["participant"])
    assert np.isfinite(geo["features"].loc[0, "hrv_triangular_index"])
    assert np.isfinite(geo["features"].loc[0, "tinn"])

    tiny = pd.DataFrame({"IBI": [0.8, 0.81, 0.79]})
    assert gp.extract_gazepoint_hrv_rqa(tiny)["features"].loc[0, "status"] == "insufficient_intervals"
    assert gp.extract_gazepoint_hrv_geometric(tiny)["features"].loc[0, "status"] == "insufficient_intervals"
    constant = gp.extract_gazepoint_hrv_rqa(pd.DataFrame({"IBI": [0.8] * 20}), radius=None)
    assert constant["features"].loc[0, "status"] == "hrv_rqa_extracted"


def test_pdr_and_rsa_r_fixtures_and_insufficient_paths():
    rng = np.random.default_rng(1)
    time = np.arange(0, 60.0001, 0.05)
    respiration = 1 + 0.15 * np.sin(2 * np.pi * 0.25 * time)
    ppg = respiration * np.sin(2 * np.pi * 1.2 * time) + rng.normal(0, 0.02, len(time))
    dat = pd.DataFrame({"participant": "p1", "time": time, "HRP": ppg})
    pdr = gp.extract_gazepoint_pdr_signals(dat, ppg_col="HRP", time_col="time", group_cols=["participant"], sampling_rate=20, min_peak_distance_s=0.4)
    assert len(pdr["pulse_features"]) > 10
    assert "proxy_resp_rate_hz" in pdr["pdr_summary"]
    assert pdr["overview"].loc[0, "status"] in {"pdr_extraction_complete", "pdr_extraction_partial"}
    assert pdr["pulse_features"]["peak_row"].min() >= 1

    ibi_time = np.arange(0, 61, 1.0)
    ibi = pd.DataFrame({"participant": "p1", "time": ibi_time, "IBI": 0.8 + 0.05 * np.sin(2 * np.pi * 0.25 * ibi_time)})
    rsa = gp.calculate_gazepoint_rsa(ibi, ibi_col="IBI", time_col="time", group_cols=["participant"], pdr=pdr)
    assert "rsa_pb_log_power_proxy" in rsa["rsa_summary"]
    assert rsa["overview"].loc[0, "status"] in {"rsa_proxy_complete", "rsa_proxy_partial"}

    sparse = pd.DataFrame({"time": [0.0, 1.0, 2.0], "HRP": [0.0, 1.0, 0.0]})
    poor = gp.extract_gazepoint_pdr_signals(sparse, time_col="time")
    assert poor["pdr_summary"].loc[0, "status"] == "insufficient_pulse_peaks"
    no_pdr = gp.calculate_gazepoint_rsa(ibi, ibi_col="IBI", time_col="time", resp_rate_hz=0.25)
    assert np.isfinite(no_pdr["rsa_summary"].loc[0, "rsa_pb_log_power_proxy"])
    with pytest.raises(ValueError, match="output from"):
        gp.calculate_gazepoint_rsa(ibi, time_col="time", pdr={})


def test_advanced_nonlinear_input_validation():
    with pytest.raises(TypeError):
        gp.extract_gazepoint_eda_complexity([1, 2, 3])
    with pytest.raises(ValueError, match="Column"):
        gp.extract_gazepoint_hrv_geometric(pd.DataFrame({"x": [1, 2, 3]}))
    with pytest.raises(ValueError, match="group_cols"):
        gp.extract_gazepoint_hrv_fragmentation(pd.DataFrame({"IBI": [0.8] * 6}), group_cols=["participant"])
    with pytest.raises(ValueError, match="respiration_band"):
        gp.extract_gazepoint_pdr_signals(pd.DataFrame({"HRP": [0, 1, 0], "CNT": [0, 1, 2]}), respiration_band=[0.6, 0.1])
