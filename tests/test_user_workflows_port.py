from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def _bio(n=120):
    user = np.where(np.arange(n) < n // 2, "U1", "U2")
    media = np.ones(n, dtype=int)
    t = np.arange(n, dtype=float) * 100.0
    phase = np.arange(n) / 10.0
    return pd.DataFrame({
        "USER": user,
        "MEDIA_ID": media,
        "CNT": np.arange(1, n + 1),
        "time_ms": t,
        "GSR_US": 2.0 + 0.1 * np.sin(phase),
        "GSRV": np.ones(n),
        "HR": 72.0 + 2.0 * np.sin(phase / 2),
        "HRV": np.ones(n),
        "IBI": 60.0 / (72.0 + 2.0 * np.sin(phase / 2)),
        "DIAL": 0.5 + 0.1 * np.sin(phase / 3),
        "DIALV": np.ones(n),
        "TTL0": np.where(np.arange(n) == 30, 1, 0),
    })


def test_feature_inventory_and_formatting_reflect_true_python_implementation():
    inv = gp.create_gazepoint_biometrics_feature_inventory()
    assert inv["_class"] == "gazepoint_biometrics_feature_inventory"
    assert {"domain", "function_name", "available", "status"}.issubset(inv["inventory"].columns)
    assert {"aoi_biometrics", "interoperability", "plotting", "eda_scr", "ibi_hr_hrv"}.issubset(set(inv["inventory"]["domain"]))
    assert inv["domain_summary"]["feature_count"].sum() == len(inv["inventory"])
    formatted = gp.format_gazepoint_biometrics_feature_inventory(inv)
    expected = {"domain", "domain_label", "workflow_stage", "method_family", "user_level", "function_name", "interpretation_caution", "available", "availability_label", "status"}
    assert expected.issubset(formatted.columns)
    assert formatted["domain_label"].str.len().gt(0).all()
    summary = gp.summarise_gazepoint_biometrics_feature_inventory(formatted)
    assert set(summary) == {"overview", "domain_summary", "method_summary", "user_level_summary"}
    assert int(summary["overview"].iloc[0]["feature_rows"]) == len(formatted)
    with pytest.raises(TypeError):
        gp.create_gazepoint_biometrics_feature_inventory(include_internal=None)


def test_plotting_contracts_qc_dashboard_and_timeline():
    dat = _bio(40)
    dat.loc[10:19, "GSR_US"] = 0
    fig = gp.plot_gazepoint_biometric_signals(dat, ["GSR_US", "HR"], "time_ms", group_col="USER", standardize=True, type="both", max_points=25)
    assert isinstance(fig, Figure) and fig._gazepoint_plot_contract
    assert fig._gazepoint_plot_type == "biometric_signals"
    q = gp.plot_gazepoint_biometric_quality(dat, signal_cols=["GSR_US", "HR"], group_col="USER", plot=False)
    assert q._gazepoint_plot_contract
    act = gp.plot_gazepoint_signal_activity(dat, ["GSR_US", "HR"], "USER", metric="nonzero_prop")
    assert {"signal", ".plot_value", ".plot_group"}.issubset(act._gazepoint_plot_data.columns)
    reset_dat = dat.copy()
    reset_dat.loc[10:19, "time_ms"] -= 1500
    resets = gp.plot_gazepoint_time_resets(reset_dat, "time_ms", "USER")
    assert ".any_time_issue" in resets._gazepoint_plot_data
    assert resets._gazepoint_plot_data[".any_time_issue"].any()
    dash = gp.plot_gazepoint_biometric_report_dashboard(reset_dat, signal_cols=["GSR_US", "HR"], group_cols="USER", time_col="time_ms")
    assert dash["_class"] == "gazepoint_biometric_plot_dashboard"
    assert dash["overview"].iloc[0]["status"] == "dashboard_created"
    assert set(dash["plots"]) == {"signal_activity", "time_resets"}
    partial = gp.plot_gazepoint_biometric_report_dashboard(reset_dat, signal_cols=["missing_signal"], group_cols="USER", time_col="time_ms", continue_on_error=True)
    assert partial["overview"].iloc[0]["status"] == "partial_dashboard_created"
    assert partial["errors"].iloc[0]["plot"] == "signal_activity"

    decomp = dat.assign(GSR_US_TONIC=dat.GSR_US.rolling(3, center=True, min_periods=1).mean())
    decomp["GSR_US_PHASIC"] = decomp.GSR_US - decomp.GSR_US_TONIC
    p = gp.plot_gazepoint_eda_decomposition(decomp, "time_ms")
    assert p._gazepoint_plot_type == "eda_decomposition"
    peaks = pd.DataFrame({"peak_time": [1000.0, 2000.0], "peak_value": [0.2, 0.3]})
    pe = gp.plot_gazepoint_scr_events(decomp, peaks, time_col="time_ms", phasic_col="GSR_US_PHASIC")
    assert pe._gazepoint_plot_type == "scr_events"
    timeline = gp.plot_gazepoint_multimodal_timeline(dat, time_col="time_ms", signal_cols=["GSR_US", "HR", "IBI"], event_col="TTL0")
    assert timeline._gazepoint_plot_type == "multimodal_timeline"
    assert len(timeline._gazepoint_event_data) == 1
    spec = gp.plot_gazepoint_scr_specification_curve(pd.DataFrame({"specification_id": ["s1", "s2"], "estimate": [-.1, .2]}))
    assert spec._gazepoint_plot_type == "scr_specification_curve"


def test_full_windows_multimodal_model_and_lme_contracts():
    dat = _bio(24)
    full = gp.summarise_gazepoint_full_biometric_windows(dat, ["USER", "MEDIA_ID"])
    assert len(full) == 2
    assert {"gsr_mean_value", "hr_mean_value", "dial_mean_value", "ibi_mean_ibi_sec", "ibi_rmssd_ms"}.issubset(full.columns)
    noibi = gp.summarise_gazepoint_full_biometric_windows(dat, ["USER", "MEDIA_ID"], include_ibi_hrv=False)
    assert "ibi_mean_ibi_sec" not in noibi
    with pytest.raises(ValueError):
        gp.summarise_gazepoint_full_biometric_windows(dat, ["missing"])

    model = gp.prepare_gazepoint_multimodal_model_data(dat, group_columns=["USER", "MEDIA_ID"])
    assert len(model) == 2
    assert model.attrs["model_data_summary"]["source"] == "biometrics_only"
    eye = pd.DataFrame({"USER": ["U1", "U2"], "MEDIA_ID": [1, 1], "dwell_time": [1200, 900], "fixation_count": [8, 6]})
    merged = gp.prepare_gazepoint_multimodal_model_data(dat, eye_tracking=eye, group_columns=["USER", "MEDIA_ID"])
    assert {"dwell_time", "fixation_count", "gsr_mean_value"}.issubset(merged.columns)
    assert merged.attrs["model_data_summary"]["has_eye_tracking"] is True
    summarised = full[["USER", "MEDIA_ID", "gsr_mean_value", "hr_mean_value", "dial_mean_value"]]
    already = gp.prepare_gazepoint_multimodal_model_data(summarised, group_columns=["USER", "MEDIA_ID"], biometric_is_summarised=True)
    assert len(already) == 2

    lme = pd.DataFrame({
        "participant": np.repeat(["P1", "P2"], 6),
        "condition": np.tile(["A", "B", "A"], 4),
        "outcome": np.linspace(10, 21, 12),
        "baseline": np.repeat(2.0, 12),
        "age": np.linspace(20, 31, 12),
    })
    prep = gp.prepare_gazepoint_biometrics_lme_data(lme, "outcome", condition_cols=["condition"], participant_col="participant", baseline_col="baseline", baseline_correct=True, continuous_cols=["age"], scale_continuous=True, min_rows=5)
    assert prep["_class"] == "gazepoint_biometrics_lme_data"
    assert prep["overview"].iloc[0]["status"] == "ready"
    assert "outcome_baseline_corrected" in prep["model_data"]
    assert "z_age" in prep["data"]
    assert "(1 | participant)" in prep["model_formula"]


def test_readiness_pass_warn_fail_and_join_alias():
    dat = _bio(150)
    ready = gp.run_gazepoint_biometrics_real_data_readiness(dat, min_rows=100, min_active_signal_count=2, time_col="time_ms")
    assert ready["overview"].iloc[0]["final_status"] == "pass"
    gsr_only = pd.DataFrame({"time_ms": np.arange(120) * 100, "GSR": np.linspace(1_000_000, 500_000, 120), "HRV": 1})
    warn = gp.run_gazepoint_biometrics_real_data_readiness(gsr_only, min_rows=100, min_active_signal_count=1)
    assert warn["overview"].iloc[0]["final_status"] == "warn"
    short = gp.run_gazepoint_biometrics_real_data_readiness(dat.head(10), min_rows=100)
    assert short["overview"].iloc[0]["final_status"] == "fail"
    via = gp.run_gazepoint_biometrics_real_data_readiness(workflow_result={"biometrics": dat}, min_rows=100, min_active_signal_count=2)
    assert via["overview"].iloc[0]["row_count"] == 150
    dial = gp.summarise_gazepoint_dial_windows(dat, group_columns=["USER", "MEDIA_ID"])
    assert len(dial) == 2
    master = dat[["USER", "MEDIA_ID", "CNT"]].copy()
    bio = dat[["USER", "MEDIA_ID", "CNT", "GSR_US"]].copy()
    joined = gp.join_gazepoint_biometrics_to_gp3tools(bio, master, by=["USER", "MEDIA_ID", "CNT"])
    assert "GSR_US" in joined


def test_end_to_end_workflow_reports_and_export(tmp_path: Path):
    root = tmp_path / "exports"
    root.mkdir()
    dat = _bio(120)
    # folder importer recognizes all_gaze/fixation naming.
    dat.to_csv(root / "P01_all_gaze.csv", index=False)
    wf = gp.run_gazepoint_biometrics_workflow(root, group_columns=["source_participant", "MEDIA_ID"], sampling_time_column="CNT")
    assert wf["_class"] == "gazepoint_biometrics_workflow"
    assert wf["overview"].iloc[0]["n_rows"] == 120
    assert wf["windows"] is not None
    diag = gp.diagnose_gazepoint_biometrics_workflow(wf, require_gsr=True, require_hr=True)
    assert diag.iloc[0]["final_status"] in {"pass", "fail"}
    summary = gp.summarise_gazepoint_biometrics_workflow(wf)
    assert summary.iloc[0]["n_rows"] == 120

    tables = gp.create_gazepoint_biometrics_report_tables(workflow=wf, max_ttl_events=5)
    assert tables["_class"] == "gazepoint_biometrics_report_tables"
    assert {"overview", "diagnostics", "channels", "quality", "sampling", "window_recommendations", "participant_recommendations", "ttl_events"}.issubset(tables)
    written = gp.write_gazepoint_biometrics_report_tables(tables, tmp_path / "tables", prefix="study")
    assert written["written"].any()
    written2 = gp.write_gazepoint_biometrics_report_tables(tables, tmp_path / "tables", prefix="study", overwrite=False)
    assert (~written2["written"]).any()

    dashboard = gp.plot_gazepoint_biometric_report_dashboard(wf["data"], signal_cols=["GSR_US", "HR"], group_cols="source_participant", time_col="CNT")
    report = gp.create_gazepoint_biometrics_report(workflow=wf, output_file=tmp_path / "report.md", overwrite=True)
    assert report["overview"].iloc[0]["status"] == "report_created"
    assert (tmp_path / "report.md").exists()
    bundle = gp.export_gazepoint_biometrics_report_bundle(
        output_dir=tmp_path / "bundle", tables=tables,
        text={"methods": ["Methods line"]}, plots=dashboard["plots"], overwrite=True,
    )
    assert bundle["overview"].iloc[0]["status"] == "bundle_exported"
    assert (tmp_path / "bundle" / "gpbiometrics_report_manifest.csv").exists()
    with pytest.raises(FileExistsError):
        gp.export_gazepoint_biometrics_report_bundle(output_dir=tmp_path / "bundle", tables={"x": pd.DataFrame({"x": [1]})}, overwrite=False)


def test_integration_validation_edges(tmp_path: Path):
    dat = _bio(20)
    with pytest.raises(ValueError):
        gp.plot_gazepoint_biometric_signals(dat, ["missing"])
    with pytest.raises(ValueError):
        gp.plot_gazepoint_signal_activity(dat, ["GSR_US"], metric="bad")
    with pytest.raises(ValueError):
        gp.plot_gazepoint_time_resets(pd.DataFrame({"GSR_US": [1, 2]}))
    with pytest.raises(ValueError):
        gp.plot_gazepoint_biometric_report_dashboard()
    with pytest.raises(ValueError):
        gp.prepare_gazepoint_multimodal_model_data(dat, group_columns=["missing"])
    with pytest.raises(ValueError):
        gp.prepare_gazepoint_biometrics_lme_data(dat, "missing")
    with pytest.raises(ValueError):
        gp.diagnose_gazepoint_biometrics_workflow({})
    with pytest.raises(ValueError):
        gp.summarise_gazepoint_biometrics_workflow({})
    with pytest.raises(TypeError):
        gp.write_gazepoint_biometrics_report_tables([], tmp_path)
    with pytest.raises(ValueError):
        gp.export_gazepoint_biometrics_report_bundle(output_dir=None)
