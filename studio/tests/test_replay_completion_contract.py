from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp
from studio.reporting_services import replay_completion_summary, workflow_replay_script
from studio.state import ProjectState


def _state() -> ProjectState:
    n = 48
    phase = np.arange(n, dtype=float) / 5.0
    data = pd.DataFrame(
        {
            "CNT": np.arange(1, n + 1),
            "GSR_US": 2.0 + 0.1 * np.sin(phase),
            "GSRV": np.ones(n),
            "HR": 72.0 + np.sin(phase),
            "HRV": np.ones(n),
            "DIAL": 0.5 + 0.05 * np.cos(phase),
            "DIALV": np.ones(n),
            "TTL0": np.where(np.arange(n) == 20, 1, 0),
            "TTLV": np.ones(n),
        }
    )
    state = ProjectState().with_dataset(
        data,
        source_name="replay_contract.csv",
        validation=gp.validate_gazepoint_biometrics(data, require_active_signal=False),
        operation="load_upload",
    )
    return state.with_analysis(
        "eda_scr",
        {"parameters": {"signal_col": "GSR_US", "time_col": "CNT"}},
        parameters={"signal_col": "GSR_US", "time_col": "CNT"},
    )


def test_replay_completion_summary_requires_exact_names_and_order():
    summary = replay_completion_summary(
        ["gaze", "pupil"],
        {"gaze": {"status": "ok"}, "pupil": {"status": "ok"}},
    )
    assert summary == {
        "analysis_count": 2,
        "analysis_names": ["gaze", "pupil"],
    }

    with pytest.raises(RuntimeError, match="analysis inventory mismatch"):
        replay_completion_summary(["gaze", "pupil"], {"gaze": {"status": "ok"}})

    with pytest.raises(RuntimeError, match="analysis inventory mismatch"):
        replay_completion_summary(
            ["gaze", "pupil"],
            {"pupil": {"status": "ok"}, "gaze": {"status": "ok"}},
        )


def test_generated_replay_records_expected_inventory_and_emits_summary():
    script = workflow_replay_script(_state())
    assert "EXPECTED_ANALYSES = ['eda_scr']" in script
    assert "replay_completion_summary(EXPECTED_ANALYSES, analyses)" in script
    assert "GPBIOMETRICSPY_STUDIO_REPLAY_SUMMARY=" in script


def test_unregistered_replay_adapter_is_visible_and_fail_closed_at_completion():
    state = _state().with_analysis(
        "custom_analysis",
        {"parameters": {}},
        parameters={},
    )
    script = workflow_replay_script(state)
    assert "EXPECTED_ANALYSES = ['eda_scr', 'custom_analysis']" in script
    assert 'No automatic Studio replay adapter is registered for "custom_analysis"' in script
    assert "replay_completion_summary(EXPECTED_ANALYSES, analyses)" in script
