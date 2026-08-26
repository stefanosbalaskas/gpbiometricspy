from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_automated_statistics_ac_eda_and_online_design():
    rng = np.random.default_rng(1)
    dat = pd.DataFrame({
        "condition": np.repeat(["A", "B", "C"], 12),
        "feature_1": np.r_[rng.normal(0, 1, 12), rng.normal(1, 1, 12), rng.normal(1.5, 1, 12)],
        "feature_2": np.r_[rng.normal(0, 1, 12), rng.normal(0, 1, 12), rng.normal(0.2, 1, 12)],
    })
    out = gp.run_gazepoint_automated_statistics(dat, ["feature_1", "feature_2"], "condition")
    assert out["class"][0] == "gazepoint_automated_statistics"
    assert len(out["test_table"]) == 2
    assert "p_adjusted" in out["test_table"]

    ac = pd.DataFrame({
        "participant": "p1",
        "frequency": np.repeat([10, 20], 20),
        "conductance": rng.normal(1, 0.05, 40),
        "susceptance": rng.normal(0.2, 0.02, 40),
    })
    ac_out = gp.analyze_gazepoint_ac_susceptance(
        ac,
        conductance_col="conductance",
        susceptance_col="susceptance",
        frequency_col="frequency",
        group_cols="participant",
    )
    assert ac_out["class"][0] == "gazepoint_ac_susceptance"
    assert "ac_eda_admittance_magnitude" in ac_out["timeseries"]
    assert len(ac_out["summary"]) >= 2

    candidates = pd.DataFrame({
        "condition": ["attention", "no_attention", "control"],
        "expected_utility": [0.70, 0.55, 0.40],
        "cost": [0.05, 0.02, 0.01],
    })
    opt = gp.run_gazepoint_online_design_optimization(
        candidates, cost_col="cost", previous_assignments=["attention", "attention", "control"]
    )
    assert opt["class"][0] == "gazepoint_online_design_optimization"
    assert len(opt["recommendation"]) == 1
    assert "optimization_rank" in opt["ranked_candidates"]


def test_cardiorespiratory_ctsi_and_pspm_dcm(tmp_path):
    rng = np.random.default_rng(2)
    n = 120
    resp = np.sin(np.linspace(0, 8 * np.pi, n))
    cardiac = np.r_[np.zeros(3), resp[:-3]] + rng.normal(0, 0.1, n)
    dat = pd.DataFrame({"participant": "p1", "time": np.arange(1, n + 1), "resp": resp, "cardiac": cardiac})
    out = gp.analyze_gazepoint_cardiorespiratory_causality(
        dat, "resp", "cardiac", time_col="time", group_cols="participant", lag_order=3, min_rows=40
    )
    assert out["class"][0] == "gazepoint_cardiorespiratory_causality"
    assert "respiration_to_cardiac_p" in out["causality_summary"]
    assert out["overview"].iloc[0]["status"] == "cardiorespiratory_directionality_estimated"

    t = np.arange(0, 20.5, 0.5)
    ctsi_dat = pd.DataFrame({
        "participant": "p1",
        "time": t,
        "GSR_US": 1 + np.sin(t) * 0.05,
        "onset": np.resize([5, 10, np.nan], len(t)),
        "condition": np.resize(["A", "B", "none"], len(t)),
    })
    ctsi = gp.prepare_gazepoint_ctsi_input(
        ctsi_dat, eda_col="GSR_US", time_col="time", group_cols="participant",
        event_onset_col="onset", event_name_col="condition", sampling_rate=2,
        output_dir=tmp_path / "ctsi",
    )
    assert ctsi["class"][0] == "gazepoint_ctsi_input"
    assert len(ctsi["signal_table"]) > 0 and len(ctsi["ctsi_config"]) > 0
    assert ctsi["overview"].iloc[0]["status"] == "ctsi_input_prepared"
    assert ctsi["written_files"]

    t2 = np.arange(0, 10.5, 0.5)
    dcm_dat = pd.DataFrame({
        "participant": "p1", "session": "s1", "time": t2,
        "GSR_US": 1 + np.sin(t2) * 0.1,
        "event_onset": np.resize([2, 6, np.nan], len(t2)),
        "event_duration": 0,
        "condition": np.resize(["A", "B", "none"], len(t2)),
    })
    dcm = gp.prepare_gazepoint_pspm_dcm_input(
        dcm_dat, eda_col="GSR_US", time_col="time", event_onset_col="event_onset",
        event_duration_col="event_duration", event_name_col="condition",
        participant_col="participant", session_col="session", output_dir=tmp_path / "dcm",
    )
    assert dcm["class"][0] == "gazepoint_pspm_dcm_input"
    assert len(dcm["signal_table"]) > 0 and len(dcm["event_table"]) > 0
    assert dcm["overview"].iloc[0]["status"] == "pspm_dcm_input_prepared"


def test_condition_bootstrap_modes_are_reproducible():
    rng = np.random.default_rng(3)
    dat = pd.DataFrame({
        "condition": np.repeat(["control", "treatment"], 40),
        "outcome": np.r_[rng.normal(0, 1, 40), rng.normal(1, 1, 40)],
    })
    out1 = gp.compare_gazepoint_conditions_bootstrap(
        dat, "outcome", "condition", condition_levels=["control", "treatment"], n_boot=200, seed=10
    )
    out2 = gp.compare_gazepoint_conditions_bootstrap(
        dat, "outcome", "condition", condition_levels=["control", "treatment"], n_boot=200, seed=10
    )
    assert out1.attrs["class"][0] == "gazepoint_bootstrap_condition_comparison"
    assert len(out1) == 1 and out1.iloc[0]["estimate"] > 0.5
    assert out1.iloc[0]["contrast"] == "treatment - control"
    assert out1.iloc[0]["ci_high"] > out1.iloc[0]["ci_low"]
    np.testing.assert_allclose(out1.attrs["bootstrap_samples"]["all"], out2.attrs["bootstrap_samples"]["all"])

    participants = [f"P{i:02d}" for i in range(1, 31)]
    base = rng.normal(size=30)
    paired = pd.DataFrame({
        "participant": np.repeat(participants, 2),
        "condition": np.tile(["pre", "post"], 30),
        "outcome": np.column_stack([base, base + 0.5 + rng.normal(0, 0.05, 30)]).ravel(),
    })
    po = gp.compare_gazepoint_conditions_bootstrap(
        paired, "outcome", "condition", participant_col="participant",
        condition_levels=["pre", "post"], paired=True, n_boot=100, seed=20,
    )
    assert po.iloc[0]["n_pairs"] == 30
    assert po.iloc[0]["estimate"] > 0.4
    assert po.iloc[0]["unit_level"] == "participant_condition_mean"


def test_cvxeda_tau_and_scr_multiverse():
    rng = np.random.default_rng(4)
    time = np.arange(0, 120.5, 0.5)
    eda = 1 + 0.01 * np.sin(2 * np.pi * 0.05 * time) + 0.05 * np.exp(-np.maximum(0, time - 20) / 3) + 0.03 * np.exp(-np.maximum(0, time - 70) / 3)
    dat = pd.DataFrame({"participant": "p1", "time": time, "GSR_US": eda})
    out = gp.optimize_gazepoint_cvxeda_tau(
        dat, eda_col="GSR_US", time_col="time", group_cols="participant", tau0_grid=[2, 3, 4], sampling_rate=2
    )
    assert out["class"][0] == "gazepoint_cvxeda_tau_optimization"
    assert len(out["best_tau"]) == 1
    assert out["best_tau"].iloc[0]["tau0"] in {2, 3, 4}
    assert "rmse" in out["optimization_table"]

    rel = np.arange(-1, 5.5, 0.5)
    time2 = np.tile(rel, 4)
    participant = np.repeat(["p1", "p1", "p2", "p2"], len(rel))
    trial = np.repeat(["p1_1", "p1_2", "p2_1", "p2_2"], len(rel))
    condition = np.repeat(["control", "treatment", "control", "treatment"], len(rel))
    x = 1 + np.where((time2 >= 1) & (time2 <= 3), 0.08, 0) + rng.normal(0, 0.005, len(time2))
    mdat = pd.DataFrame({"participant": participant, "trial": trial, "condition": condition, "time": time2, "GSR_US": x})
    m = gp.run_gazepoint_scr_multiverse(
        mdat, signal_col="GSR_US", time_col="time", trial_cols=["participant", "trial"], condition_col="condition",
        latency_windows=[(1, 3), (1, 4)], thresholds=[0.01, 0.05], baseline_methods=["median", "none"],
    )
    assert m["class"][0] == "gazepoint_scr_multiverse"
    assert m["overview"].iloc[0]["specification_count"] == 8
    assert len(m["scored_trials"]) > 0
    assert {"response_amplitude", "response_present"}.issubset(m["scored_trials"].columns)


def test_eda_pipeline_create_and_run():
    pipe = gp.create_gazepoint_eda_analysis_pipeline()
    assert pipe["class"][0] == "gazepoint_eda_analysis_pipeline"
    assert pipe["overview"].iloc[0]["status"] == "eda_analysis_pipeline_created"
    assert pipe["overview"].iloc[0]["phase_count"] == 6
    assert len(pipe["phases"]) == 6
    expected = {
        "import_gazepoint_biometrics", "audit_gazepoint_time_resets", "audit_gazepoint_signal_activity",
        "audit_gazepoint_eda_artifacts", "detect_gazepoint_scr_peaks", "summarise_gazepoint_scr_event_windows",
        "classify_gazepoint_eda_response_pattern", "prepare_gazepoint_cvxeda_input",
        "align_gazepoint_biometrics_to_ttl", "estimate_gazepoint_signal_lag",
        "prepare_gazepoint_scr_hurdle_model_data", "prepare_gazepoint_biometrics_lme_data",
        "export_gazepoint_biometrics_report_bundle", "create_gazepoint_biometrics_methods_text",
    }
    assert expected.issubset(set(pipe["function_map"]["function_name"]))
    assert pipe["function_map"]["available"].all()

    reduced = gp.create_gazepoint_eda_analysis_pipeline(False, False, False)
    assert "prepare_gazepoint_cvxeda_input" not in set(reduced["function_map"]["function_name"])
    assert len(reduced["model_templates"]) == 0 and len(reduced["reporting_guidance"]) == 0

    dat = pd.DataFrame({
        "source_file": "user1_all_gaze.csv", "MEDIA_ID": 1, "CNT": np.arange(1, 121),
        "GSR_US": 1 + np.sin(np.linspace(0, 4 * np.pi, 120)) * 0.1,
        "GSR_US_PHASIC": np.sin(np.linspace(0, 8 * np.pi, 120)) * 0.03,
        "HR": 70 + np.sin(np.linspace(0, 2 * np.pi, 120)) * 3,
        "IBI": 0.8, "DIAL": 1,
    })
    run = gp.run_gazepoint_eda_analysis_pipeline(
        data=dat, eda_col="GSR_US", time_col="CNT", group_cols=["source_file", "MEDIA_ID"],
        signal_cols=["GSR_US", "GSR_US_PHASIC", "HR", "IBI", "DIAL"], sampling_rate=60,
        prepare_external_bridges=False, prepare_model_data=False, create_reports=False, continue_on_error=True,
    )
    assert run["class"][0] == "gazepoint_eda_analysis_pipeline_run"
    assert run["overview"].iloc[0]["phase_count"] == 6
    assert run["overview"].iloc[0]["input_rows"] == 120
    assert list(run["phases"]) == [
        "phase_1_ingestion_qc", "phase_2_preprocessing_peaks", "phase_3_external_bridges",
        "phase_4_sync_model_formatting", "phase_5_model_templates", "phase_6_reporting",
    ]


def test_lsl_xdf_missing_file_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="File does not exist"):
        gp.import_gazepoint_lsl_xdf(tmp_path / "missing_file.xdf")
