from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

import gpbiometricspy as gp


def _bio(n: int = 80) -> pd.DataFrame:
    user = np.where(np.arange(n) < n // 2, "U1", "U2")
    phase = np.arange(n, dtype=float) / 10.0
    return pd.DataFrame(
        {
            "USER": user,
            "MEDIA_ID": np.ones(n, dtype=int),
            "CNT": np.arange(1, n + 1),
            "time_ms": np.arange(n, dtype=float) * 100.0,
            "GSR_US": 2.0 + 0.1 * np.sin(phase),
            "GSRV": np.ones(n),
            "HR": 72.0 + 2.0 * np.sin(phase / 2.0),
            "HRV": np.ones(n),
            "IBI": 60.0 / (72.0 + 2.0 * np.sin(phase / 2.0)),
            "DIAL": 0.5 + 0.1 * np.sin(phase / 3.0),
            "DIALV": np.ones(n),
            "TTL0": np.where(np.arange(n) == n // 3, 1, 0),
        }
    )


def test_user_workflow_plotting_alternative_paths():
    dat = _bio(24)

    signals = gp.plot_gazepoint_biometric_signals(
        dat,
        signal_cols=["GSR_US"],
        time_col="time_ms",
        type="points",
        legend=False,
        plot=True,
    )
    assert isinstance(signals, Figure)
    assert signals._gazepoint_plot_type == "biometric_signals"

    quality = gp.plot_gazepoint_biometric_quality(
        dat,
        quality_cols=[],
        plot=True,
    )
    assert isinstance(quality, Figure)
    assert quality._gazepoint_quality_summary.empty
    assert quality._gazepoint_group_summary.empty

    dashboard = gp.plot_gazepoint_biometric_report_dashboard(
        data=dat,
        signal_cols=["GSR_US"],
        include_time_resets=False,
    )
    assert set(dashboard["plots"]) == {"signal_activity"}
    assert dashboard["overview"].iloc[0]["status"] == "dashboard_created"


def test_user_workflow_scr_and_timeline_marker_alternatives():
    dat = _bio(24)

    scr = gp.plot_gazepoint_scr_events(
        dat,
        pd.DataFrame(),
        time_col="time_ms",
        signal_col="GSR_US",
    )
    assert isinstance(scr, Figure)
    assert scr._gazepoint_peak_data.empty

    timeline = gp.plot_gazepoint_multimodal_timeline(
        dat,
        time_col="time_ms",
        signal_cols=["GSR_US", "HR"],
        event_col="TTL0",
        show_event_markers=False,
    )
    assert isinstance(timeline, Figure)
    assert timeline._gazepoint_plot_type == "multimodal_timeline"

    spec = gp.plot_gazepoint_scr_specification_curve(
        pd.DataFrame({"specification_id": ["s1", "s2"], "estimate": [-0.1, 0.2]}),
        add_zero_line=False,
    )
    assert isinstance(spec, Figure)
    assert spec._gazepoint_plot_type == "scr_specification_curve"


def test_user_workflow_readiness_without_time_column():
    dat = pd.DataFrame(
        {
            "GSR_US": np.linspace(1.0, 1.5, 12),
            "HR": np.linspace(65.0, 75.0, 12),
        }
    )
    out = gp.run_gazepoint_biometrics_real_data_readiness(
        dat,
        min_rows=1,
        min_active_signal_count=1,
    )
    assert "time_column" not in set(out["checks"]["check"])
    assert out["overview"].iloc[0]["row_count"] == 12


def test_user_workflow_explicit_sampling_and_no_exclusion_recommendations(tmp_path: Path):
    root = tmp_path / "exports"
    root.mkdir()
    _bio(80).to_csv(root / "P01_all_gaze.csv", index=False)

    out = gp.run_gazepoint_biometrics_workflow(
        root,
        group_columns=["source_participant", "MEDIA_ID"],
        sampling_group_columns=["source_file"],
        sampling_time_column="CNT",
        create_exclusion_recommendations=False,
        extract_ttl_events=False,
    )
    assert out["sampling"] is not None
    assert out["windows"] is not None
    assert out["exclusion_recommendations"] is None
    assert out["ttl_events"] is None


def test_user_workflow_report_table_existing_recommendation_column():
    rec = pd.DataFrame({"recommendation": ["keep", "review"]})
    out = gp.create_gazepoint_biometrics_report_tables(
        exclusion_recommendations=rec,
    )
    assert out["window_recommendations"]["recommendation"].tolist() == ["keep", "review"]
    assert "participant_recommendation" in out["participant_recommendations"].columns


def test_user_workflow_report_bundle_optional_outputs(tmp_path: Path):
    out = gp.export_gazepoint_biometrics_report_bundle(
        output_dir=tmp_path / "bundle",
        tables={},
        text={},
        plots={"not_a_figure": object()},
        include_readme=False,
        include_session_info=False,
        overwrite=True,
    )
    assert out["overview"].iloc[0]["status"] == "bundle_exported"
    assert out["manifest"]["item"].tolist() == ["manifest"]


def test_user_workflow_report_without_output_file():
    tables = {"overview": pd.DataFrame({"status": ["ok"]})}
    out = gp.create_gazepoint_biometrics_report(
        report_tables=tables,
        methods_text="Methods text",
        output_file=None,
    )
    assert out["overview"].iloc[0]["output_file"] is None
    assert "# Gazepoint Biometrics report" in out["content"]
