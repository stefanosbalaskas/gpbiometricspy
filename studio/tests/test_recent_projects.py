from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from studio.config import STUDIO_MODE_ENV
from studio.recent_projects import (
    MAX_RECENT_PROJECTS,
    RECENT_PROJECTS_SCHEMA,
    clear_recent_projects,
    load_recent_projects,
    recent_project_record,
    recent_projects_frame,
    record_recent_project,
)
from studio.reporting_services import dataset_fingerprint
from studio.state import ProjectState


def _state(*, project_name: str = "Study Alpha", value: float = 0.25) -> ProjectState:
    data = pd.DataFrame(
        {
            "TIME": [0.0, 0.1, 0.2],
            "GSR_US": [value, value + 0.1, value + 0.2],
            "participant_id": ["P001", "P001", "P001"],
        }
    )
    return (
        ProjectState()
        .with_project_name(project_name)
        .with_dataset(
            data,
            source_name="C:/private/research/participant_P001.csv",
            validation={"status": "ok"},
            operation="load_upload",
        )
    )


def test_recent_project_record_is_strictly_metadata_minimal():
    state = _state()
    record = recent_project_record(state, saved_utc="2026-09-10T12:00:00+00:00")

    assert set(record) == {
        "project_name",
        "saved_utc",
        "dataset_sha256",
        "row_count",
        "column_count",
        "analysis_count",
        "annotation_count",
        "recipe_filename",
    }
    assert record["project_name"] == "Study Alpha"
    assert record["dataset_sha256"] == dataset_fingerprint(state.data)
    assert record["recipe_filename"] == "Study-Alpha-project-recipe.json"

    serialized = json.dumps(record)
    assert "participant_P001.csv" not in serialized
    assert "C:/private" not in serialized
    assert "GSR_US" not in serialized
    assert "participant_id" not in serialized
    assert "P001" not in serialized
    assert "provenance" not in serialized
    assert "parameters" not in serialized
    assert "analyses" not in serialized
    assert "annotations" not in serialized


def test_recent_project_round_trip_deduplicates_same_project_and_dataset(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "local")
    path = tmp_path / "recent-projects.json"
    state = _state()

    first = record_recent_project(
        state,
        path,
        saved_utc="2026-09-10T12:00:00+00:00",
    )
    second = record_recent_project(
        state,
        path,
        saved_utc="2026-09-10T13:00:00+00:00",
    )
    records = load_recent_projects(path)

    assert first["dataset_sha256"] == second["dataset_sha256"]
    assert len(records) == 1
    assert records[0]["saved_utc"] == "2026-09-10T13:00:00+00:00"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == RECENT_PROJECTS_SCHEMA
    assert payload["schema_version"] == 1
    assert len(payload["projects"]) == 1


def test_recent_project_index_is_bounded_and_latest_first(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "local")
    path = tmp_path / "recent-projects.json"

    for index in range(MAX_RECENT_PROJECTS + 3):
        record_recent_project(
            _state(project_name=f"Study {index}", value=float(index)),
            path,
            saved_utc=f"2026-09-{index + 1:02d}T12:00:00+00:00",
        )

    records = load_recent_projects(path)
    assert len(records) == MAX_RECENT_PROJECTS
    assert records[0]["project_name"] == f"Study {MAX_RECENT_PROJECTS + 2}"
    assert records[-1]["project_name"] == "Study 3"


def test_recent_project_index_rejects_unexpected_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "local")
    path = tmp_path / "recent-projects.json"
    state = _state()
    record = recent_project_record(state, saved_utc="2026-09-10T12:00:00+00:00")
    record["source_path"] = "C:/private/research/participant_P001.csv"
    path.write_text(
        json.dumps(
            {
                "schema": RECENT_PROJECTS_SCHEMA,
                "schema_version": 1,
                "updated_utc": "2026-09-10T12:00:00+00:00",
                "projects": [record],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unexpected metadata fields"):
        load_recent_projects(path)


def test_public_demo_blocks_recent_project_disk_access(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "public-demo")
    path = tmp_path / "recent-projects.json"
    state = _state()

    with pytest.raises(PermissionError, match="disabled in public-demo mode"):
        record_recent_project(state, path)
    with pytest.raises(PermissionError, match="disabled in public-demo mode"):
        load_recent_projects(path)
    with pytest.raises(PermissionError, match="disabled in public-demo mode"):
        clear_recent_projects(path)
    assert not path.exists()


def test_recent_projects_frame_hides_full_fingerprint_and_source_identity():
    state = _state()
    record = recent_project_record(state, saved_utc="2026-09-10T12:00:00+00:00")
    frame = recent_projects_frame(
        [record],
        current_fingerprint=dataset_fingerprint(state.data),
    )

    assert list(frame.columns) == [
        "Project",
        "Last saved (UTC)",
        "Dataset fingerprint",
        "Current dataset",
        "Rows",
        "Columns",
        "Analyses",
        "Annotations",
        "Recipe file",
    ]
    assert frame.iloc[0]["Current dataset"] == "Match"
    assert frame.iloc[0]["Dataset fingerprint"].endswith("…")
    assert len(frame.iloc[0]["Dataset fingerprint"]) == 13
    visible = frame.to_string()
    assert record["dataset_sha256"] not in visible
    assert "participant_P001.csv" not in visible


def test_clear_recent_projects_removes_only_metadata_index(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "local")
    path = tmp_path / "recent-projects.json"
    record_recent_project(_state(), path)
    assert path.exists()

    assert clear_recent_projects(path) is True
    assert not path.exists()
    assert clear_recent_projects(path) is False
