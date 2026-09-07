from __future__ import annotations

import inspect

import gpbiometricspy as gp
import pytest

from studio.event_alignment_services import run_event_alignment
from studio.reporting_services import workflow_replay_script
from studio.state import ProjectState


def _recorded_target_state() -> tuple[ProjectState, dict[str, object]]:
    data = gp.import_gazepoint_biometrics(gp.kiosk_demo_files()[0])
    validation = gp.validate_gazepoint_biometrics(data, require_active_signal=False)
    state = ProjectState().with_dataset(
        data,
        source_name="packaged_participant.csv",
        validation=validation,
        operation="load_upload",
    )
    parameters: dict[str, object] = {
        "source_mode": "ttl",
        "time_col": "TIME",
        "ttl_col": "TTL0",
        "validity_col": "TTLV",
        "group_col": "participant_id",
        "extraction_mode": "changes",
        "event_edge": "rising",
        "pre_s": 1.0,
        "post_s": 5.0,
        "collapse_nearby_ms": 0.0,
        "summary_cols": ["GSR_US"],
        "target_stream_used": True,
        "target_time_col": "TIME",
        "target_ttl_col": "TTL0",
        "target_validity_col": "TTLV",
        "target_group_col": "participant_id",
        "stream_method": "linear",
    }
    state = state.with_analysis(
        "event_alignment",
        {"parameters": parameters},
        parameters=parameters,
    )
    return state, parameters


def test_recorded_target_stream_guard_survives_replay_parameter_filtering():
    state, parameters = _recorded_target_state()
    script = workflow_replay_script(state)

    assert "'target_stream_used': True" in script
    allowed = inspect.signature(run_event_alignment).parameters
    assert "target_stream_used" in allowed
    clean = {key: value for key, value in parameters.items() if key in allowed}
    assert clean["target_stream_used"] is True

    with pytest.raises(ValueError, match="separately managed target stream"):
        run_event_alignment(state.data, **clean)
