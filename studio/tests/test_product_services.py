from __future__ import annotations

import pandas as pd
import pytest

from studio.product_services import (
    active_guided_start,
    guided_next_step,
    guided_progress_text,
    guided_start,
    guided_start_choices,
    project_export_stem,
    readiness_percent,
    support_snapshot,
    workflow_progress,
)
from studio.state import ProjectState


def _loaded_state() -> ProjectState:
    data = pd.DataFrame({"TIME": [0.0, 0.1, 0.2], "BPOGV": [0.5, 0.6, 0.7]})
    return (
        ProjectState()
        .with_project_name("Pilot study")
        .with_dataset(data, source_name="participant_001.csv", validation={"valid": True}, operation="test_load")
    )


def test_guided_start_catalog_is_stable_and_unknown_values_fail_closed():
    choices = guided_start_choices()
    assert set(choices) == {"multimodal", "eye_tracking", "physiology"}
    assert guided_start("multimodal").target_nav == "event_alignment"
    assert guided_start("eye_tracking").target_nav == "pupil"
    assert [step.key for step in guided_start("physiology").steps] == [
        "eda_scr",
        "ppg_hr_hrv",
        "reporting",
    ]
    with pytest.raises(ValueError, match="Unknown guided-start preset"):
        guided_start("mystery")


def test_guided_workflow_advances_from_recorded_provenance_and_completed_analyses():
    state = _loaded_state().with_qc({"validation": {"valid": True}})
    state = state.with_operation(
        "start_guided_walkthrough",
        preset="physiology",
        target_nav="eda_scr",
    )
    assert active_guided_start(state).key == "physiology"
    assert guided_next_step(state).key == "eda_scr"
    assert guided_progress_text(state) == "EDA and cardiovascular walkthrough: 0/3 guided steps complete"

    state = state.with_analysis("eda_scr", {"status": "ok"})
    assert guided_next_step(state).key == "ppg_hr_hrv"
    assert guided_progress_text(state) == "EDA and cardiovascular walkthrough: 1/3 guided steps complete"

    state = state.with_analysis("ppg_hr_hrv", {"status": "ok"})
    assert guided_next_step(state).key == "reporting"

    state = state.with_operation("build_reporting_artifacts", raw_data_embedded=False)
    assert guided_next_step(state) is None
    assert guided_progress_text(state) == "EDA and cardiovascular walkthrough: 3/3 guided steps complete"


def test_manual_dataset_replacement_retires_the_previous_guided_walkthrough():
    state = _loaded_state().with_operation(
        "start_guided_walkthrough",
        preset="physiology",
        target_nav="eda_scr",
    )
    replacement = pd.DataFrame({"TIME": [1.0, 1.1], "BPOGV": [0.4, 0.3]})
    state = state.with_dataset(
        replacement,
        source_name="participant_002.csv",
        validation={"valid": True},
        operation="load_upload",
    )
    assert active_guided_start(state) is None
    assert guided_next_step(state) is None
    assert guided_progress_text(state) is None


def test_report_completion_is_invalidated_by_later_project_state_changes():
    state = _loaded_state().with_qc({"validation": {"valid": True}})
    state = state.with_analysis("eda_scr", {"status": "ok"})
    state = state.with_operation("build_reporting_artifacts", raw_data_embedded=False)
    assert readiness_percent(state) == 100
    assert workflow_progress(state).loc[
        lambda table: table["stage"] == "Report", "status"
    ].iloc[0] == "Complete"

    renamed = state.with_project_name("Renamed pilot study")
    assert readiness_percent(renamed) == 75
    assert workflow_progress(renamed).loc[
        lambda table: table["stage"] == "Report", "status"
    ].iloc[0] == "Ready"

    replacement = pd.DataFrame({"TIME": [1.0, 1.1], "BPOGV": [0.4, 0.3]})
    replaced = state.with_dataset(
        replacement,
        source_name="participant_002.csv",
        validation={"valid": True},
        operation="load_upload",
    )
    assert readiness_percent(replaced) == 25
    assert workflow_progress(replaced).loc[
        lambda table: table["stage"] == "Report", "status"
    ].iloc[0] == "Blocked"


def test_unknown_restored_guided_preset_fails_closed_to_no_active_walkthrough():
    state = _loaded_state().with_operation(
        "start_guided_walkthrough",
        preset="retired-preset",
        target_nav="home",
    )
    assert active_guided_start(state) is None
    assert guided_next_step(state) is None
    assert guided_progress_text(state) is None


def test_workflow_progress_and_readiness_follow_required_first_session_path():
    state = _loaded_state()
    progress = workflow_progress(state)
    assert progress.loc[progress["stage"] == "Project", "status"].iloc[0] == "Complete"
    assert progress.loc[progress["stage"] == "Quality", "status"].iloc[0] == "Ready"
    assert readiness_percent(state) == 25

    state = state.with_qc({"validation": {"valid": True}})
    state = state.with_analysis("eda_scr", {"status": "ok"})
    state = state.with_operation("build_reporting_artifacts", raw_data_embedded=False)
    assert readiness_percent(state) == 100
    complete = workflow_progress(state)
    assert complete.loc[complete["stage"] == "Analyze", "status"].iloc[0] == "Complete"
    assert complete.loc[complete["stage"] == "Report", "status"].iloc[0] == "Complete"


def test_project_export_stem_preserves_unicode_and_avoids_reserved_windows_names():
    assert project_export_stem("Μελέτη pupil / pilot") == "Μελέτη-pupil-pilot"
    assert project_export_stem("CON") == "project-CON"
    assert project_export_stem("   ") == "gpbiometricspy-studio-project"


def test_support_snapshot_excludes_source_filename_and_raw_samples():
    state = _loaded_state().with_qc({"validation": {"valid": True}})
    snapshot = support_snapshot(state, runtime_mode="local", package_version="0.1.6.dev0")
    assert snapshot["project_name"] == "Pilot study"
    assert snapshot["source_type"] == ".csv"
    assert snapshot["raw_data_included"] is False
    assert snapshot["source_filename_included"] is False
    assert "participant_001" not in repr(snapshot)
