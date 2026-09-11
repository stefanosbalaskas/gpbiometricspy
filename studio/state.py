from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json
from typing import Any

import pandas as pd


def _event(operation: str, source: str, n_rows: int, n_columns: int, **extra: Any) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "source": source,
        "n_rows": int(n_rows),
        "n_columns": int(n_columns),
        "status": "ok",
        **extra,
    }


def _validated_annotations(annotations: Any) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for annotation in annotations or ():
        if not isinstance(annotation, dict):
            raise TypeError("Restored annotations must be dictionaries.")
        annotation_type = str(annotation.get("annotation_type") or "").strip()
        if annotation_type not in {"manual_peak", "artifact_interval"}:
            raise ValueError("Unsupported annotation type in restored project metadata.")
        row = dict(annotation)
        row["annotation_type"] = annotation_type
        rows.append(row)
    return tuple(rows)


def _validated_provenance(provenance: Any) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for event in provenance or ():
        if not isinstance(event, dict):
            raise TypeError("Restored provenance entries must be dictionaries.")
        rows.append(dict(event))
    return tuple(rows)


def _clean_project_name(value: Any) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("Project name must be non-empty.")
    if len(name) > 120:
        raise ValueError("Project name must be 120 characters or fewer.")
    return name


@dataclass(frozen=True)
class ProjectState:
    """Immutable per-session state for gpbiometricspy Studio."""

    project_name: str = "Untitled project"
    data: pd.DataFrame | None = None
    source_name: str = "No dataset loaded"
    loaded_at: str | None = None
    validation: dict[str, Any] | None = None
    qc: dict[str, Any] | None = None
    annotations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    analyses: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def loaded(self) -> bool:
        return self.data is not None

    @property
    def n_rows(self) -> int:
        return 0 if self.data is None else len(self.data)

    @property
    def n_columns(self) -> int:
        return 0 if self.data is None else len(self.data.columns)

    def with_project_name(self, name: str) -> "ProjectState":
        clean = _clean_project_name(name)
        if clean == self.project_name:
            return self
        event = _event(
            "set_project_name",
            self.source_name,
            self.n_rows,
            self.n_columns,
            project_name=clean,
        )
        return replace(self, project_name=clean, provenance=(*self.provenance, event))

    def with_dataset(
        self,
        data: pd.DataFrame,
        *,
        source_name: str,
        validation: dict[str, Any],
        operation: str,
    ) -> "ProjectState":
        event = _event(operation, source_name, len(data), len(data.columns), project_name=self.project_name)
        return ProjectState(
            project_name=self.project_name,
            data=data,
            source_name=source_name,
            loaded_at=event["timestamp_utc"],
            validation=validation,
            qc=None,
            annotations=(),
            analyses={},
            provenance=(*self.provenance, event),
        )

    def with_operation(self, operation: str, **extra: Any) -> "ProjectState":
        """Append an auditable Studio operation without mutating scientific results."""
        key = str(operation).strip()
        if not key:
            raise ValueError("Operation must be non-empty.")
        event = _event(key, self.source_name, self.n_rows, self.n_columns, project_name=self.project_name, **extra)
        return replace(self, provenance=(*self.provenance, event))

    def with_qc(self, qc: dict[str, Any], *, operation: str = "run_qc") -> "ProjectState":
        if self.data is None:
            raise ValueError("A dataset must be loaded before QC can be stored.")
        merged = {**(self.qc or {}), **qc}
        event = _event(operation, self.source_name, self.n_rows, self.n_columns, project_name=self.project_name)
        return replace(self, qc=merged, provenance=(*self.provenance, event))

    def with_analysis(
        self,
        name: str,
        result: dict[str, Any],
        *,
        parameters: dict[str, Any] | None = None,
    ) -> "ProjectState":
        if self.data is None:
            raise ValueError("A dataset must be loaded before analysis can be stored.")
        key = str(name).strip()
        if not key:
            raise ValueError("Analysis name must be non-empty.")
        if not isinstance(result, dict):
            raise TypeError("Analysis result must be a dictionary.")
        merged = {**self.analyses, key: result}
        event = _event(
            f"run_{key}_analysis",
            self.source_name,
            self.n_rows,
            self.n_columns,
            project_name=self.project_name,
            analysis=key,
            parameters_json=json.dumps(parameters or {}, sort_keys=True, default=str),
            analysis_count=len(merged),
        )
        return replace(self, analyses=merged, provenance=(*self.provenance, event))

    def with_annotation(self, annotation: dict[str, Any]) -> "ProjectState":
        if self.data is None:
            raise ValueError("A dataset must be loaded before annotations can be stored.")
        annotation_type = str(annotation.get("annotation_type") or "").strip()
        if annotation_type not in {"manual_peak", "artifact_interval"}:
            raise ValueError("Unsupported annotation type.")
        row = dict(annotation)
        row["annotation_type"] = annotation_type
        event = _event(
            "add_annotation",
            self.source_name,
            self.n_rows,
            self.n_columns,
            project_name=self.project_name,
            annotation_type=annotation_type,
            annotation_count=len(self.annotations) + 1,
        )
        return replace(
            self,
            annotations=(*self.annotations, row),
            provenance=(*self.provenance, event),
        )

    def without_annotation(self, row_number: int) -> "ProjectState":
        if not isinstance(row_number, int) or row_number < 1 or row_number > len(self.annotations):
            raise ValueError("Annotation row number is out of range.")
        kept = tuple(row for i, row in enumerate(self.annotations, start=1) if i != row_number)
        event = _event(
            "remove_annotation",
            self.source_name,
            self.n_rows,
            self.n_columns,
            project_name=self.project_name,
            annotation_count=len(kept),
        )
        return replace(self, annotations=kept, provenance=(*self.provenance, event))

    def without_annotations(self) -> "ProjectState":
        event = _event(
            "clear_annotations",
            self.source_name,
            self.n_rows,
            self.n_columns,
            project_name=self.project_name,
            annotation_count=0,
        )
        return replace(self, annotations=(), provenance=(*self.provenance, event))

    def with_restored_session_metadata(
        self,
        *,
        annotations: Any = (),
        provenance: Any = (),
        recipe_fingerprint: str | None = None,
        project_name: str | None = None,
    ) -> "ProjectState":
        """Restore non-raw project metadata after an external fingerprint check."""
        if self.data is None:
            raise ValueError("Load the source dataset before restoring a Studio project recipe.")
        restored_annotations = _validated_annotations(annotations)
        restored_provenance = _validated_provenance(provenance)
        restored_name = self.project_name if project_name is None else _clean_project_name(project_name)
        event = _event(
            "restore_project_recipe",
            self.source_name,
            self.n_rows,
            self.n_columns,
            project_name=restored_name,
            restored_annotation_count=len(restored_annotations),
            restored_provenance_count=len(restored_provenance),
            recipe_fingerprint=recipe_fingerprint,
            analysis_outputs_restored=False,
        )
        return replace(
            self,
            project_name=restored_name,
            annotations=restored_annotations,
            analyses={},
            provenance=(*self.provenance, *restored_provenance, event),
        )
