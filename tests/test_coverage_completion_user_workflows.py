from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp
import gpbiometricspy.user_workflows as uw


def _bio(n=12):
    return pd.DataFrame({
        "USER": np.repeat(["U1", "U2"], n // 2),
        "MEDIA_ID": 1,
        "CNT": np.arange(n),
        "time_ms": np.arange(n, dtype=float) * 10,
        "GSR_US": np.linspace(1, 2, n),
        "HR": np.linspace(60, 70, n),
        "IBI": np.linspace(.8, 1.0, n),
        "DIAL": np.linspace(.2, .8, n),
        "TTL0": np.r_[np.zeros(n-1), 1],
    })


def test_workflow_private_and_signal_plot_error_paths():
    with pytest.raises(TypeError, match="data frame"):
        uw._df([1])
    with pytest.raises(TypeError, match="numeric"):
        uw._signals(pd.DataFrame({"x": ["a"]}), ["x"])
    with pytest.raises(ValueError, match="max_points"):
        uw._downsample_indices(10, 0)

    d = _bio()
    for kwargs, exc in [
        ({"standardize": 1}, TypeError),
        ({"plot": 1}, TypeError),
        ({"type": "bad"}, ValueError),
        ({"time_col": "bad"}, ValueError),
        ({"group_col": "bad"}, ValueError),
    ]:
        with pytest.raises(exc):
            gp.plot_gazepoint_biometric_signals(d, ["GSR_US"], **kwargs)
    with pytest.raises(ValueError, match="No biometric"):
        gp.plot_gazepoint_biometric_signals(pd.DataFrame({"time": [1, 2]}))
    fig = gp.plot_gazepoint_biometric_signals(d, ["GSR_US"], plot=False)
    assert fig._gazepoint_plot_type == "biometric_signals"


def test_quality_plot_all_sources_and_group_paths():
    assert uw._as_quality_flag(pd.Series([1, 0, np.nan]), "GSRV").tolist() == [False, True, True]
    assert uw._as_quality_flag(pd.Series([0, 1, np.nan]), "artifact").tolist() == [False, True, False]
    d = _bio()
    d["flag"] = [0, 1] * 6
    d["GSRV"] = [1, 0] * 6
    for kwargs, exc in [
        ({"plot": 1}, TypeError),
        ({"dropout_prefix": ""}, ValueError),
        ({"group_col": "bad"}, ValueError),
        ({"time_col": "bad"}, ValueError),
    ]:
        with pytest.raises(exc):
            gp.plot_gazepoint_biometric_quality(d, **kwargs)
    with pytest.raises(ValueError, match="Quality columns"):
        gp.plot_gazepoint_biometric_quality(d, quality_cols=["missing"])
    explicit = gp.plot_gazepoint_biometric_quality(d, quality_cols=["GSRV", "flag"], group_col="USER", plot=False)
    assert len(explicit._gazepoint_quality_summary) == 2
    drop = d.assign(biometric_dropout_GSR=[False, True] * 6)
    found = gp.plot_gazepoint_biometric_quality(drop, group_col="USER", plot=False)
    assert found._gazepoint_overview.iloc[0].derived_from_signals == False
    with pytest.raises(ValueError, match="No quality columns"):
        gp.plot_gazepoint_biometric_quality(pd.DataFrame({"x": ["a"]}))


def test_group_labels_activity_time_reset_and_dashboard_edges():
    assert uw._group_label_from_audit(pd.DataFrame({"x": [1, 2]})).tolist() == ["all", "all"]
    labels = uw._group_label_from_audit(pd.DataFrame({"USER": ["u", None], "MEDIA_ID": [1, 2]}))
    assert labels.iloc[0] == "u||1"

    with pytest.raises(ValueError, match="max_groups"):
        gp.plot_gazepoint_signal_activity(_bio(), max_groups=0)
    with pytest.raises(ValueError, match="No signal-activity"):
        gp.plot_gazepoint_signal_activity({"signal_by_group": pd.DataFrame()})
    with pytest.raises(ValueError, match="max_groups"):
        gp.plot_gazepoint_time_resets(_bio(), max_groups=0)
    with pytest.raises(ValueError, match="No time-reset"):
        gp.plot_gazepoint_time_resets({"row_flags": pd.DataFrame()})
    with pytest.raises(ValueError, match="time_value"):
        gp.plot_gazepoint_time_resets({"row_flags": pd.DataFrame({"x": [1]})})

    with pytest.raises(TypeError, match="include_signal_activity"):
        gp.plot_gazepoint_biometric_report_dashboard(data=_bio(), include_signal_activity=1)
    with pytest.raises(ValueError):
        gp.plot_gazepoint_biometric_report_dashboard()
    with pytest.raises(ValueError):
        gp.plot_gazepoint_biometric_report_dashboard(data=pd.DataFrame({"x": [1]}), include_time_resets=False, continue_on_error=False)
    # Force the second try/except to re-raise as well.
    with pytest.raises(ValueError):
        gp.plot_gazepoint_biometric_report_dashboard(data=pd.DataFrame({"GSR_US": [1, 2]}), include_signal_activity=False, continue_on_error=False)
    partial_time = gp.plot_gazepoint_biometric_report_dashboard(
        data=pd.DataFrame({"GSR_US": [1, 2]}), include_signal_activity=False, continue_on_error=True
    )
    assert partial_time["errors"].iloc[0]["plot"] == "time_resets"


def test_scr_and_multimodal_plot_edge_paths():
    with pytest.raises(ValueError, match="No EDA"):
        gp.plot_gazepoint_scr_events(pd.DataFrame({"time": [0, 1]}), pd.DataFrame())
    d = pd.DataFrame({"time": [0, 1, 2], "GSR_US": [1., 2., 1.]})
    amp = gp.plot_gazepoint_scr_events(d, pd.DataFrame({"peak_time": [1], "peak_amplitude": [.5]}), time_col="time")
    assert len(amp._gazepoint_peak_data) == 1
    zero = gp.plot_gazepoint_scr_events(d, pd.DataFrame({"peak_time": [1]}), time_col="time")
    assert len(zero._gazepoint_peak_data) == 1

    with pytest.raises(TypeError, match="standardise"):
        gp.plot_gazepoint_multimodal_timeline(d, standardise=1)
    with pytest.raises(ValueError, match="No time"):
        gp.plot_gazepoint_multimodal_timeline(pd.DataFrame({"GSR_US": [1, 2]}))
    with pytest.raises(ValueError, match="time_col"):
        gp.plot_gazepoint_multimodal_timeline(d, time_col="missing")
    with pytest.raises(ValueError, match="No biometric"):
        gp.plot_gazepoint_multimodal_timeline(pd.DataFrame({"time": [0, 1], "x": [1, 2]}))
    with pytest.raises(ValueError, match="Grouping columns"):
        gp.plot_gazepoint_multimodal_timeline(d, group_cols="missing")
    no_groups = gp.plot_gazepoint_multimodal_timeline(d, standardise=False)
    assert set(no_groups._gazepoint_plot_data[".data_group"]) == {"all"}
    with pytest.raises(ValueError, match="event_col"):
        gp.plot_gazepoint_multimodal_timeline(d, event_col="bad")
    e = d.assign(evt=[0, 1, 0])
    with pytest.raises(ValueError, match="event_time_col"):
        gp.plot_gazepoint_multimodal_timeline(e, event_col="evt", event_time_col="bad")
    rel = pd.DataFrame({"event_relative_time_ms": [-10, 0, 10], "GSR_US": [1, 2, 1]})
    relfig = gp.plot_gazepoint_multimodal_timeline(rel, standardise=False)
    assert relfig._gazepoint_settings["event_times"] == [0]

    with pytest.raises(ValueError, match="specification_col"):
        gp.plot_gazepoint_scr_specification_curve(pd.DataFrame({"estimate": [1]}))
    with pytest.raises(ValueError, match="numeric estimate"):
        gp.plot_gazepoint_scr_specification_curve(pd.DataFrame({"specification_id": ["a"], "x": ["bad"]}))


def test_model_lme_join_sampling_and_readiness_edges():
    d = _bio()
    eye = pd.DataFrame({"USER": ["U1"]})
    with pytest.raises(ValueError, match="missing merge keys"):
        gp.prepare_gazepoint_multimodal_model_data(d, eye_tracking=eye, group_columns=["USER", "MEDIA_ID"])

    assert uw._first_existing(["USER"], ["USER"]) == "USER"
    assert uw._first_existing(["User"], ["USER"]) == "User"
    assert uw._first_existing(["x"], ["USER"]) is None

    lme = pd.DataFrame({"USER": ["u1", "u2"], "out": [1., 2.], "base": [1., 1.], "cond": ["a", "b"]})
    with pytest.raises(ValueError, match="outcome_col"):
        gp.prepare_gazepoint_biometrics_lme_data(lme, "")
    with pytest.raises(ValueError, match="min_rows"):
        gp.prepare_gazepoint_biometrics_lme_data(lme, "out", min_rows=0)
    with pytest.raises(TypeError, match="baseline_correct"):
        gp.prepare_gazepoint_biometrics_lme_data(lme, "out", baseline_correct=1)
    with pytest.raises(ValueError, match="requested columns"):
        gp.prepare_gazepoint_biometrics_lme_data(lme, "out", fixed_effect_cols="missing")
    with pytest.raises(ValueError, match="numeric values"):
        gp.prepare_gazepoint_biometrics_lme_data(lme.assign(out=["x", "y"]), "out")
    with pytest.raises(ValueError, match="baseline_col"):
        gp.prepare_gazepoint_biometrics_lme_data(lme, "out", baseline_correct=True)
    with pytest.raises(ValueError, match="baseline_col.*numeric"):
        gp.prepare_gazepoint_biometrics_lme_data(lme.assign(base=["x", "y"]), "out", baseline_col="base", baseline_correct=True)
    inferred = gp.prepare_gazepoint_biometrics_lme_data(lme, "out", condition_cols="cond", min_rows=1)
    assert "USER" in inferred["settings"]["random_effect_cols"]

    class FlakyFrame(pd.DataFrame):
        _metadata = ["ghost_checks"]
        @property
        def _constructor(self):
            return FlakyFrame
        def __contains__(self, key):
            if key == "ghost":
                self.ghost_checks = (getattr(self, "ghost_checks", 0) or 0) + 1
                return self.ghost_checks == 1
            return super().__contains__(key)

    flaky = FlakyFrame({"out": [1.0, 2.0]})
    skipped = gp.prepare_gazepoint_biometrics_lme_data(flaky, "out", baseline_col="ghost", min_rows=1)
    assert "ghost" not in skipped["variable_summary"].get("variable", pd.Series(dtype=object)).tolist()

    with pytest.raises(ValueError, match="No shared join"):
        gp.join_gazepoint_biometrics_to_gp3tools(pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [1]}))
    with pytest.raises(ValueError, match="Join columns"):
        gp.join_gazepoint_biometrics_to_gp3tools(pd.DataFrame({"a": [1]}), pd.DataFrame({"a": [1]}), by=["a", "b"])
    assert uw._signal_is_active({}, "gsr_eda") is False

    assert uw._sampling_audit(pd.DataFrame({"x": [1]})).iloc[0].status == "time_column_missing"
    with pytest.raises(ValueError, match="sampling_time_column"):
        uw._sampling_audit(d, time_column="bad")
    with pytest.raises(ValueError, match="Sampling group"):
        uw._sampling_audit(d, group_columns="bad", time_column="time_ms")
    for unit, expected in [("seconds", 100.0), ("milliseconds", 100.0), ("microseconds", 100.0)]:
        vals = np.arange(4) * ({"seconds": .01, "milliseconds": 10, "microseconds": 10000}[unit])
        out = uw._sampling_audit(pd.DataFrame({"t": vals}), time_column="t", time_unit=unit)
        assert out.iloc[0].observed_rate_hz == pytest.approx(expected)
    excl = uw._exclusion_recommendations(pd.DataFrame({"gsr_usable_pct": [10, 90]}))
    assert "participant_recommendation" in excl["participants"]

    with pytest.raises(ValueError, match="Supply `data`"):
        gp.run_gazepoint_biometrics_real_data_readiness()
    with pytest.raises(ValueError, match="Supply `data`"):
        gp.run_gazepoint_biometrics_real_data_readiness(workflow_result={})
    rd = gp.run_gazepoint_biometrics_real_data_readiness(d, min_rows=1, required_signal_cols=["missing"])
    assert rd["checks"].set_index("check").loc["required_signals", "status"] == "fail"


def test_workflow_reporting_remaining_paths(monkeypatch, tmp_path: Path):
    d = _bio()
    # No sampling audit path without hitting disk importer complexity.
    monkeypatch.setattr(uw, "import_gazepoint_biometric_folder", lambda *a, **k: d.copy())
    monkeypatch.setattr(uw, "validate_gazepoint_biometrics", lambda data, **k: {
        "overview": pd.DataFrame([{"active_signal_count": 3}]),
        "active_channels": pd.DataFrame({"signal": ["gsr_eda", "heart_rate"], "active": [True, True]}),
        "issues": [],
    })
    monkeypatch.setattr(uw, "audit_gazepoint_biometric_missingness", lambda data: pd.DataFrame())
    monkeypatch.setattr(uw, "audit_gazepoint_gsr_quality", lambda data: pd.DataFrame())
    monkeypatch.setattr(uw, "audit_gazepoint_hr_quality", lambda data: pd.DataFrame())
    monkeypatch.setattr(uw, "audit_gazepoint_engagement_dial", lambda data: pd.DataFrame())
    monkeypatch.setattr(uw, "extract_gazepoint_ttl_events", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(uw, "create_gazepoint_biometrics_checklist", lambda *a, **k: {})
    monkeypatch.setattr(uw, "create_gazepoint_biometrics_methods_text", lambda *a, **k: "methods")
    wf = gp.run_gazepoint_biometrics_workflow("unused", audit_sampling=False, extract_ttl_events=False)
    assert wf["sampling"] is None

    badwf = dict(wf)
    badwf["validation"] = {"active_channels": pd.DataFrame({"signal": [], "active": []})}
    badwf["exclusion_recommendations"] = {"windows": pd.DataFrame({"recommendation": ["review", "exclude"]})}
    diag = gp.diagnose_gazepoint_biometrics_workflow(badwf, require_gsr=True, require_hr=True, require_dial=True, max_review_window_pct=0, max_exclude_window_pct=0)
    reasons = diag.iloc[0].diagnostic_reasons
    assert "GSR/EDA" in reasons and "heart rate" in reasons and "dial" in reasons
    assert "review-window" in reasons and "exclude-window" in reasons

    msg = uw._message_table("none", "value")
    assert list(msg.columns) == ["message", "value"]
    with pytest.raises(ValueError, match="workflow"):
        gp.create_gazepoint_biometrics_report_tables(workflow={})
    empty = gp.create_gazepoint_biometrics_report_tables()
    assert empty["overview"].iloc[0].message.startswith("No overview")
    exdf = pd.DataFrame({"x": [1]})
    t = gp.create_gazepoint_biometrics_report_tables(exclusion_recommendations=exdf)
    assert "recommendation" in t["window_recommendations"]
    t2 = gp.create_gazepoint_biometrics_report_tables(exclusion_recommendations=None)
    assert "message" in t2["window_recommendations"]

    workflow_tables = gp.write_gazepoint_biometrics_report_tables(wf, tmp_path / "wf_tables")
    assert len(workflow_tables)
    skipped = gp.write_gazepoint_biometrics_report_tables({"msg": pd.DataFrame({"message": ["x"]})}, tmp_path / "skip")
    assert skipped.iloc[0].skipped_reason == "message_only_table"

    bundle = {"tables": {"a": pd.DataFrame({"x": [1]})}, "text": {"m": "txt"}, "plots": {}}
    out = gp.export_gazepoint_biometrics_report_bundle(bundle=bundle, output_dir=tmp_path / "bundle", overwrite=True)
    assert out["overview"].iloc[0].status == "bundle_exported"

    report_file = tmp_path / "existing.md"
    report_file.write_text("old")
    with pytest.raises(FileExistsError):
        gp.create_gazepoint_biometrics_report(report_tables={"x": pd.DataFrame({"x": [1]})}, output_file=report_file, overwrite=False)
