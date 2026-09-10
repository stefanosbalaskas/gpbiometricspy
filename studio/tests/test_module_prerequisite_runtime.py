from __future__ import annotations

import pandas as pd

from studio.module_prerequisite_runtime import resolve_runtime_readiness
from studio.state import ProjectState


def _state(columns: dict[str, list[float]]) -> ProjectState:
    return ProjectState().with_dataset(
        pd.DataFrame(columns),
        source_name="participant.csv",
        validation={"valid": True},
        operation="test_load",
    )


def test_event_alignment_runtime_uses_shared_ttl_capability_without_cross_module_inputs():
    state = _state({"TIME": [0.0, 0.1, 0.2], "TTL": [0.0, 1.0, 0.0]})
    pending = resolve_runtime_readiness("event_alignment", state)
    assert pending.title == "Foundation QC pending"

    state = state.with_qc({"validation": {"valid": True}})
    ready = resolve_runtime_readiness("event_alignment", state)
    assert ready.kind == "ready"
    assert "TTL/marker source" in ready.detail


def test_event_alignment_runtime_explains_external_log_alternative_when_ttl_is_absent():
    state = _state({"TIME": [0.0, 0.1, 0.2], "GSR": [0.2, 0.3, 0.4]})
    state = state.with_qc({"validation": {"valid": True}})
    readiness = resolve_runtime_readiness("event_alignment", state)
    assert readiness.kind == "needs_setup"
    assert readiness.title == "Event source required"
    assert "External event-log mode remains available" in readiness.detail
    assert "external event log" in readiness.next_action


def test_runtime_completed_result_takes_precedence_for_event_alignment():
    state = _state({"TIME": [0.0, 0.1], "GSR": [0.2, 0.3]})
    state = state.with_analysis("event_alignment", {"status": "ok"})
    readiness = resolve_runtime_readiness("event_alignment", state)
    assert readiness.kind == "complete"
    assert readiness.title == "Events & Alignment result stored"
