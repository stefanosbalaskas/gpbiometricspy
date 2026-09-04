from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest

from studio.event_alignment_services import (
    event_alignment_reproducibility_script,
    event_alignment_tables,
    event_group_choices,
    event_time_choices,
    load_event_log,
    run_event_alignment,
    summary_signal_choices,
    ttl_column_choices,
    ttl_validity_choices,
)


def _stream(participant: str = "P01", *, offset: float = 0.0, slope: float = 1.0) -> pd.DataFrame:
    base = np.arange(0.0, 10.0, 0.1)
    time = offset + slope * base
    ttl = np.zeros(len(base), dtype=int)
    for event_time in [2.0, 5.0, 8.0]:
        ttl[int(np.argmin(np.abs(base - event_time)))] = 1
    return pd.DataFrame(
        {
            "participant_id": participant,
            "time_s": time,
            "TTL0": ttl,
            "TTLV": 1,
            "GSR_US": 2.0 + 0.1 * np.sin(base),
            "HR": 70.0 + np.cos(base),
        }
    )


def _two_group_stream() -> pd.DataFrame:
    return pd.concat([_stream("P01"), _stream("P02")], ignore_index=True)


def test_event_schema_choices_detect_reference_roles():
    data = _stream()
    assert event_time_choices(data)[0] == "time_s"
    assert ttl_column_choices(data) == ["TTL0"]
    assert ttl_validity_choices(data) == ["TTLV"]
    assert event_group_choices(data)[0] == "participant_id"
    assert "GSR_US" in summary_signal_choices(data)


def test_ttl_event_alignment_matches_windows_within_selected_group():
    result = run_event_alignment(
        _two_group_stream(),
        source_mode="ttl",
        time_col="time_s",
        ttl_col="TTL0",
        validity_col="TTLV",
        group_col="participant_id",
        pre_s=0.2,
        post_s=0.4,
        summary_cols=["GSR_US"],
    )
    events = result["events"]
    summary = result["event_summary"]
    windows = result["event_windows"]
    assert len(events) == 6
    assert set(events["participant_id"]) == {"P01", "P02"}
    assert len(summary) == 6
    assert set(summary["participant_id"]) == {"P01", "P02"}
    assert set(windows["participant_id"]) == {"P01", "P02"}
    assert "relative_time_s" in windows.columns
    assert "GSR_US_mean" in summary.columns
    assert not result["ttl_alignment"]["overview"].empty


def test_external_event_log_mode_is_group_safe():
    events = pd.DataFrame(
        {
            "event_id": ["P1_A", "P2_A"],
            "event_time": [2.0, 5.0],
            "event_label": ["stimulus", "stimulus"],
            "participant_id": ["P01", "P02"],
        }
    )
    result = run_event_alignment(
        _two_group_stream(),
        source_mode="event_log",
        time_col="time_s",
        group_col="participant_id",
        external_events=events,
        pre_s=0.1,
        post_s=0.2,
        summary_cols=["HR"],
    )
    assert len(result["event_summary"]) == 2
    assert set(result["event_summary"]["participant_id"]) == {"P01", "P02"}
    p1 = result["event_windows"].loc[result["event_windows"]["event_id"] == "P1_A"]
    assert set(p1["participant_id"]) == {"P01"}


def test_grouped_event_log_requires_matching_group_column():
    events = pd.DataFrame({"event_time": [2.0], "event_id": ["E1"], "event_label": ["stimulus"]})
    with pytest.raises(ValueError, match="requires `participant_id`"):
        run_event_alignment(
            _two_group_stream(),
            source_mode="event_log",
            time_col="time_s",
            group_col="participant_id",
            external_events=events,
        )


def test_cross_stream_linear_alignment_and_drift_diagnostics():
    reference = _stream("P01")
    target = _stream("P01", offset=0.5, slope=1.002)
    result = run_event_alignment(
        reference,
        source_mode="ttl",
        time_col="time_s",
        ttl_col="TTL0",
        validity_col="TTLV",
        group_col="participant_id",
        pre_s=0.2,
        post_s=0.3,
        summary_cols=["GSR_US"],
        target_stream=target,
        target_time_col="time_s",
        target_ttl_col="TTL0",
        target_validity_col="TTLV",
        target_group_col="participant_id",
        stream_method="linear",
    )
    diagnostics = result["stream_alignment"]["diagnostics"].iloc[0]
    assert int(diagnostics["n_event_pairs"]) == 3
    assert diagnostics["intercept_s"] == pytest.approx(0.5, abs=1e-6)
    assert diagnostics["slope_target_per_reference"] == pytest.approx(1.002, abs=1e-6)
    drift = result["drift"]["summary"].iloc[0]
    assert drift["median_lag_s"] > 0.5
    assert drift["drift_slope_s_per_s"] == pytest.approx(0.002, abs=1e-6)
    aligned = result["stream_alignment"]["target_aligned"]
    assert "target_time_aligned_s" in aligned.columns


def test_cross_stream_rejects_multiple_participant_groups():
    with pytest.raises(ValueError, match="one participant/session at a time"):
        run_event_alignment(
            _two_group_stream(),
            source_mode="ttl",
            time_col="time_s",
            ttl_col="TTL0",
            validity_col="TTLV",
            group_col="participant_id",
            target_stream=_stream("P01", offset=0.25),
            target_time_col="time_s",
            target_ttl_col="TTL0",
            target_validity_col="TTLV",
            target_group_col="participant_id",
        )


def test_event_upload_uses_package_importer(tmp_path):
    path = tmp_path / "events.csv"
    path.write_text("trial,onset,condition\nT1,1.0,A\nT2,2.0,B\n", encoding="utf-8")
    events, name = load_event_log([{"name": "events.csv", "datapath": str(path), "size": path.stat().st_size}])
    assert name == "events.csv"
    assert list(events.columns[:3]) == ["event_id", "event_time", "event_label"]
    assert events["event_id"].tolist() == ["T1", "T2"]


def test_alignment_table_adapter_and_reproducibility_script():
    result = run_event_alignment(
        _stream(),
        source_mode="ttl",
        time_col="time_s",
        ttl_col="TTL0",
        validity_col="TTLV",
        pre_s=0.1,
        post_s=0.2,
        summary_cols=["GSR_US"],
    )
    tables = event_alignment_tables(result)
    assert {"events", "event_windows", "event_summary", "ttl_alignment_overview"}.issubset(tables)
    script = event_alignment_reproducibility_script(result)
    assert "align_gazepoint_biometrics_to_ttl" in script
    assert "match_gazepoint_events_to_biometrics" in script
    assert "gp.import_gazepoint_biometrics('reference.csv')" in script


def test_event_alignment_module_and_app_import():
    module = importlib.import_module("studio.modules.event_alignment")
    app = importlib.import_module("studio.app")
    assert callable(module.event_alignment_ui)
    assert callable(module.event_alignment_server)
    assert app.app is not None
