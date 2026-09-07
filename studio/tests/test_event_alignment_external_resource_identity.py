from __future__ import annotations

from pathlib import Path

import gpbiometricspy as gp
import numpy as np
import pandas as pd
import pytest

from studio.event_alignment_services import (
    REPLAY_EVENT_LOG_ENV,
    REPLAY_TARGET_STREAM_ENV,
    run_event_alignment,
)
from studio.reporting_services import workflow_replay_script
from studio.state import ProjectState


def _stream() -> pd.DataFrame:
    time = np.arange(0.0, 10.0, 0.1)
    ttl = np.zeros(len(time), dtype=int)
    for event_time in (2.0, 5.0, 8.0):
        ttl[int(np.argmin(np.abs(time - event_time)))] = 1
    return pd.DataFrame(
        {
            "time_s": time,
            "TTL0": ttl,
            "TTLV": 1,
            "GSR_US": 2.0 + 0.1 * np.sin(time),
        }
    )


def _write_event_log(path: Path, *, second_onset: float = 5.0) -> pd.DataFrame:
    path.write_text(
        "trial,onset,condition\n"
        "E1,2.0,stimulus\n"
        f"E2,{second_onset},stimulus\n",
        encoding="utf-8",
    )
    return gp.import_gazepoint_event_log(path)


def test_external_event_log_identity_is_recorded_and_env_replay_is_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    reference = _stream()
    event_path = tmp_path / "events.csv"
    events = _write_event_log(event_path)

    recorded = run_event_alignment(
        reference,
        source_mode="event_log",
        time_col="time_s",
        external_events=events,
        pre_s=0.1,
        post_s=0.2,
        summary_cols=["GSR_US"],
    )
    expected = recorded["parameters"]["external_events_sha256"]
    assert isinstance(expected, str) and len(expected) == 64

    monkeypatch.setenv(REPLAY_EVENT_LOG_ENV, str(event_path))
    replayed = run_event_alignment(
        reference,
        source_mode="event_log",
        time_col="time_s",
        external_events_sha256=expected,
        pre_s=0.1,
        post_s=0.2,
        summary_cols=["GSR_US"],
    )
    assert replayed["parameters"]["external_events_sha256"] == expected
    assert len(replayed["event_summary"]) == 2

    wrong_path = tmp_path / "wrong-events.csv"
    _write_event_log(wrong_path, second_onset=6.0)
    monkeypatch.setenv(REPLAY_EVENT_LOG_ENV, str(wrong_path))
    with pytest.raises(ValueError, match="External event log fingerprint mismatch"):
        run_event_alignment(
            reference,
            source_mode="event_log",
            time_col="time_s",
            external_events_sha256=expected,
        )


def test_target_stream_identity_is_recorded_and_env_replay_is_exact(
    monkeypatch: pytest.MonkeyPatch,
):
    files = gp.kiosk_demo_files()
    assert len(files) >= 2
    reference = gp.import_gazepoint_biometrics(files[0])
    target = gp.import_gazepoint_biometrics(files[1])

    recorded = run_event_alignment(
        reference,
        source_mode="ttl",
        time_col="TIME",
        ttl_col="TTL0",
        validity_col="TTLV",
        group_col="participant_id",
        pre_s=1.0,
        post_s=5.0,
        summary_cols=["GSR_US"],
        target_stream=target,
        target_time_col="TIME",
        target_ttl_col="TTL0",
        target_validity_col="TTLV",
        target_group_col="participant_id",
        stream_method="linear",
    )
    expected = recorded["parameters"]["target_stream_sha256"]
    assert isinstance(expected, str) and len(expected) == 64

    monkeypatch.setenv(REPLAY_TARGET_STREAM_ENV, str(files[1]))
    replayed = run_event_alignment(
        reference,
        source_mode="ttl",
        time_col="TIME",
        ttl_col="TTL0",
        validity_col="TTLV",
        group_col="participant_id",
        pre_s=1.0,
        post_s=5.0,
        summary_cols=["GSR_US"],
        target_stream_used=True,
        target_stream_sha256=expected,
        target_time_col="TIME",
        target_ttl_col="TTL0",
        target_validity_col="TTLV",
        target_group_col="participant_id",
        stream_method="linear",
    )
    assert replayed["parameters"]["target_stream_sha256"] == expected
    assert "stream_alignment" in replayed

    monkeypatch.setenv(REPLAY_TARGET_STREAM_ENV, str(files[0]))
    with pytest.raises(ValueError, match="Target stream fingerprint mismatch"):
        run_event_alignment(
            reference,
            source_mode="ttl",
            time_col="TIME",
            ttl_col="TTL0",
            validity_col="TTLV",
            group_col="participant_id",
            target_stream_used=True,
            target_stream_sha256=expected,
            target_time_col="TIME",
            target_ttl_col="TTL0",
            target_validity_col="TTLV",
            target_group_col="participant_id",
        )


def test_workflow_replay_serializes_secondary_resource_identities():
    data = _stream()
    validation = gp.validate_gazepoint_biometrics(data, require_active_signal=False)
    state = ProjectState().with_dataset(
        data,
        source_name="reference.csv",
        validation=validation,
        operation="load_upload",
    )
    parameters = {
        "source_mode": "event_log",
        "time_col": "time_s",
        "external_events_sha256": "a" * 64,
        "target_stream_used": True,
        "target_stream_sha256": "b" * 64,
        "target_time_col": "time_s",
        "target_ttl_col": "TTL0",
        "target_validity_col": "TTLV",
        "target_group_col": None,
        "stream_method": "linear",
    }
    state = state.with_analysis(
        "event_alignment",
        {"parameters": parameters},
        parameters=parameters,
    )

    script = workflow_replay_script(state)
    assert "'external_events_sha256': '" + "a" * 64 + "'" in script
    assert "'target_stream_sha256': '" + "b" * 64 + "'" in script
