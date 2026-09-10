"""Local, privacy-minimal recent-project index for gpbiometricspy Studio.

The index is intentionally smaller than a Studio project recipe. It stores only
metadata needed to recognize recent work and never stores source paths, source
filenames, column names, annotations, provenance payloads, analysis parameters,
raw biometric rows, cached analysis tables, or credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

import pandas as pd

try:
    from studio.config import studio_runtime_config
    from studio.product_services import project_export_stem
    from studio.reporting_services import dataset_fingerprint
    from studio.state import ProjectState
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from config import studio_runtime_config
    from product_services import project_export_stem
    from reporting_services import dataset_fingerprint
    from state import ProjectState


RECENT_PROJECTS_SCHEMA = "gpbiometricspy-studio-recent-projects"
RECENT_PROJECTS_VERSION = 1
RECENT_PROJECTS_PATH_ENV = "GPBIOMETRICSPY_STUDIO_RECENT_PROJECTS_PATH"
MAX_RECENT_PROJECTS = 12
MAX_RECENT_PROJECTS_BYTES = 256 * 1024

_RECORD_FIELDS = frozenset(
    {
        "project_name",
        "saved_utc",
        "dataset_sha256",
        "row_count",
        "column_count",
        "analysis_count",
        "annotation_count",
        "recipe_filename",
    }
)
_PAYLOAD_FIELDS = frozenset({"schema", "schema_version", "updated_utc", "projects"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def recent_project_store_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the local metadata-index path, supporting a test/deployment override."""

    values = os.environ if env is None else env
    override = str(values.get(RECENT_PROJECTS_PATH_ENV, "") or "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".gpbiometricspy" / "studio" / "recent-projects.json"


def _require_local_runtime() -> None:
    if studio_runtime_config().is_public_demo:
        raise PermissionError("Recent-project persistence is disabled in public-demo mode.")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Recent-project timestamp must be non-empty.")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Recent-project timestamp must use ISO-8601 format.") from exc
    if parsed.tzinfo is None:
        raise ValueError("Recent-project timestamp must include a timezone.")
    return text


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Recent-project {field} must be a non-negative integer.")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Recent-project {field} must be a non-negative integer.") from exc
    if number < 0 or number != value:
        raise ValueError(f"Recent-project {field} must be a non-negative integer.")
    return number


def _validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("Recent-project entries must be JSON objects.")
    keys = frozenset(map(str, record))
    if keys != _RECORD_FIELDS:
        raise ValueError("Recent-project entry contains missing or unexpected metadata fields.")

    project_name = str(record["project_name"] or "").strip()
    if not project_name or len(project_name) > 120:
        raise ValueError("Recent-project name must contain 1 to 120 characters.")

    fingerprint = str(record["dataset_sha256"] or "").strip().lower()
    if not _SHA256.fullmatch(fingerprint):
        raise ValueError("Recent-project dataset fingerprint must be a 64-character SHA-256 value.")

    recipe_filename = str(record["recipe_filename"] or "").strip()
    if not recipe_filename or len(recipe_filename) > 180:
        raise ValueError("Recent-project recipe filename is invalid.")
    if Path(recipe_filename).name != recipe_filename or Path(recipe_filename).suffix.lower() != ".json":
        raise ValueError("Recent-project recipe filename must be a basename ending in .json.")

    return {
        "project_name": project_name,
        "saved_utc": _valid_timestamp(record["saved_utc"]),
        "dataset_sha256": fingerprint,
        "row_count": _nonnegative_int(record["row_count"], "row_count"),
        "column_count": _nonnegative_int(record["column_count"], "column_count"),
        "analysis_count": _nonnegative_int(record["analysis_count"], "analysis_count"),
        "annotation_count": _nonnegative_int(record["annotation_count"], "annotation_count"),
        "recipe_filename": recipe_filename,
    }


def recent_project_record(state: ProjectState, *, saved_utc: str | None = None) -> dict[str, Any]:
    """Build one privacy-minimal recent-project record from current Studio state."""

    if state.data is None:
        raise ValueError("Load a dataset before recording recent-project metadata.")
    record = {
        "project_name": state.project_name,
        "saved_utc": saved_utc or _utc_now(),
        "dataset_sha256": dataset_fingerprint(state.data),
        "row_count": state.n_rows,
        "column_count": state.n_columns,
        "analysis_count": len(state.analyses),
        "annotation_count": len(state.annotations),
        "recipe_filename": f"{project_export_stem(state.project_name)}-project-recipe.json",
    }
    return _validate_record(record)


def _validate_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise TypeError("Recent-project index must decode to a JSON object.")
    if frozenset(map(str, payload)) != _PAYLOAD_FIELDS:
        raise ValueError("Recent-project index contains missing or unexpected top-level fields.")
    if payload.get("schema") != RECENT_PROJECTS_SCHEMA:
        raise ValueError("Unrecognized recent-project index schema.")
    if int(payload.get("schema_version", -1)) != RECENT_PROJECTS_VERSION:
        raise ValueError("Unsupported recent-project index schema version.")
    _valid_timestamp(payload.get("updated_utc"))
    projects = payload.get("projects")
    if not isinstance(projects, list):
        raise TypeError("Recent-project index projects must be a JSON array.")
    if len(projects) > MAX_RECENT_PROJECTS:
        raise ValueError("Recent-project index exceeds the supported entry limit.")
    return [_validate_record(record) for record in projects]


def load_recent_projects(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Read and validate the local recent-project metadata index."""

    _require_local_runtime()
    target = recent_project_store_path() if path is None else Path(path).expanduser()
    if not target.exists():
        return []
    if not target.is_file():
        raise ValueError("Recent-project index path is not a regular file.")
    if target.stat().st_size > MAX_RECENT_PROJECTS_BYTES:
        raise ValueError("Recent-project index exceeds the 256 KB metadata limit.")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Recent-project index is unreadable or invalid JSON.") from exc
    return _validate_payload(payload)


def _write_projects(path: Path, projects: list[dict[str, Any]]) -> None:
    validated = [_validate_record(record) for record in projects]
    if len(validated) > MAX_RECENT_PROJECTS:
        raise ValueError("Recent-project index exceeds the supported entry limit.")
    payload = {
        "schema": RECENT_PROJECTS_SCHEMA,
        "schema_version": RECENT_PROJECTS_VERSION,
        "updated_utc": _utc_now(),
        "projects": validated,
    }
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_RECENT_PROJECTS_BYTES:
        raise ValueError("Recent-project index exceeds the 256 KB metadata limit.")

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=".recent-projects-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp_path.chmod(0o600)
        except OSError:
            pass
        temp_path.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def record_recent_project(
    state: ProjectState,
    path: str | Path | None = None,
    *,
    saved_utc: str | None = None,
) -> dict[str, Any]:
    """Opt-in persistence of one metadata-only recent-project entry."""

    _require_local_runtime()
    target = recent_project_store_path() if path is None else Path(path).expanduser()
    record = recent_project_record(state, saved_utc=saved_utc)
    existing = load_recent_projects(target)
    key = (record["project_name"].casefold(), record["dataset_sha256"])
    kept = [
        item
        for item in existing
        if (item["project_name"].casefold(), item["dataset_sha256"]) != key
    ]
    projects = [record, *kept][:MAX_RECENT_PROJECTS]
    _write_projects(target, projects)
    return record


def clear_recent_projects(path: str | Path | None = None) -> bool:
    """Delete the local recent-project metadata index and report whether it existed."""

    _require_local_runtime()
    target = recent_project_store_path() if path is None else Path(path).expanduser()
    if not target.exists():
        return False
    if not target.is_file():
        raise ValueError("Recent-project index path is not a regular file.")
    target.unlink()
    return True


def recent_projects_frame(
    records: list[dict[str, Any]],
    *,
    current_fingerprint: str | None = None,
) -> pd.DataFrame:
    """Return a researcher-readable table without exposing the full stored fingerprint."""

    rows: list[dict[str, Any]] = []
    current = str(current_fingerprint or "").strip().lower()
    for raw in records:
        record = _validate_record(raw)
        rows.append(
            {
                "Project": record["project_name"],
                "Last saved (UTC)": record["saved_utc"],
                "Dataset fingerprint": f"{record['dataset_sha256'][:12]}…",
                "Current dataset": "Match" if current and record["dataset_sha256"] == current else "—",
                "Rows": record["row_count"],
                "Columns": record["column_count"],
                "Analyses": record["analysis_count"],
                "Annotations": record["annotation_count"],
                "Recipe file": record["recipe_filename"],
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Project",
            "Last saved (UTC)",
            "Dataset fingerprint",
            "Current dataset",
            "Rows",
            "Columns",
            "Analyses",
            "Annotations",
            "Recipe file",
        ],
    )
