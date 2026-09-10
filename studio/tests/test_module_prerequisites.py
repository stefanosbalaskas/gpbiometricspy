from __future__ import annotations

import pandas as pd

from studio.module_prerequisites import (
    cardiac_readiness,
    eda_readiness,
    event_alignment_readiness,
    gaze_readiness,
    multimodal_readiness,
    pupil_readiness,
)
from studio.state import ProjectState


def _loaded_state() -> ProjectState:
    data = pd.DataFrame({"TIME": [0.0, 0.1, 0.2], "SIGNAL": [1.0, 1.1, 1.2]})
    return ProjectState().with_dataset(
        data,
        source_name="participant.csv",
        validation={"valid": True},
        operation="test_load",
    )


def test_signal_module_readiness_progresses_from_data_to_qc_to_complete():
    empty = ProjectState()
    assert eda_readiness(empty, has_signal=False).title == "Dataset required"

    loaded = _loaded_state()
    assert eda_readiness(loaded, has_signal=False).kind == "unavailable"
    pending = eda_readiness(loaded, has_signal=True)
    assert pending.kind == "needs_setup"
    assert pending.title == "Foundation QC pending"

    qc = loaded.with_qc({"validation": {"valid": True}})
    assert eda_readiness(qc, has_signal=True).kind == "ready"
    complete = qc.with_analysis("eda_scr", {"status": "ok"})
    assert eda_readiness(complete, has_signal=True).kind == "complete"


def test_cardiac_readiness_requires_any_supported_cardiac_family():
    state = _loaded_state().with_qc({"validation": {"valid": True}})
    missing = cardiac_readiness(state, has_signal=False)
    assert missing.kind == "unavailable"
    assert "PPG, HR, or IBI/RR" in missing.next_action
    assert cardiac_readiness(state, has_signal=True).kind == "ready"


def test_pupil_and_gaze_readiness_require_time_and_coordinate_inputs():
    state = _loaded_state().with_qc({"validation": {"valid": True}})

    assert pupil_readiness(state, has_pupil=False, has_time=True).kind == "unavailable"
    assert pupil_readiness(state, has_pupil=True, has_time=False).title == "Time column not detected"
    assert pupil_readiness(state, has_pupil=True, has_time=True).kind == "ready"

    assert gaze_readiness(state, has_x=True, has_y=False, has_time=True).title == "Gaze coordinate pair not detected"
    assert gaze_readiness(state, has_x=True, has_y=True, has_time=False).title == "Time column not detected"
    assert gaze_readiness(state, has_x=True, has_y=True, has_time=True).kind == "ready"


def test_event_alignment_readiness_tracks_selected_reference_source_without_interpreting_events():
    state = _loaded_state().with_qc({"validation": {"valid": True}})

    ttl_missing = event_alignment_readiness(
        state,
        has_time=True,
        source_mode="ttl",
        has_ttl=False,
        has_event_upload=False,
    )
    assert ttl_missing.kind == "needs_setup"
    assert ttl_missing.title == "TTL / marker source required"

    upload_missing = event_alignment_readiness(
        state,
        has_time=True,
        source_mode="event_log",
        has_ttl=True,
        has_event_upload=False,
    )
    assert upload_missing.title == "External event log required"

    ready = event_alignment_readiness(
        state,
        has_time=True,
        source_mode="event_log",
        has_ttl=False,
        has_event_upload=True,
    )
    assert ready.kind == "ready"


def test_multimodal_readiness_requires_alignment_and_multiple_modalities():
    loaded = _loaded_state()
    first = multimodal_readiness(
        loaded,
        has_time=True,
        has_event_alignment=False,
        modality_count=2,
    )
    assert first.title == "Quality and event alignment pending"

    qc = loaded.with_qc({"validation": {"valid": True}})
    no_alignment = multimodal_readiness(
        qc,
        has_time=True,
        has_event_alignment=False,
        modality_count=2,
    )
    assert no_alignment.title == "Events & Alignment required"

    one_modality = multimodal_readiness(
        qc,
        has_time=True,
        has_event_alignment=True,
        modality_count=1,
    )
    assert one_modality.title == "At least two modalities recommended"

    ready = multimodal_readiness(
        qc,
        has_time=True,
        has_event_alignment=True,
        modality_count=3,
    )
    assert ready.kind == "ready"
    assert "3 supported modality families" in ready.detail


def test_completed_result_takes_precedence_over_later_capability_resolution():
    state = _loaded_state().with_analysis("gaze", {"status": "ok"})
    result = gaze_readiness(state, has_x=False, has_y=False, has_time=False)
    assert result.kind == "complete"
    assert result.title == "Gaze / Fixation / AOI result stored"
