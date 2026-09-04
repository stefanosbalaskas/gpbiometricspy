from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
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


@dataclass(frozen=True)
class ProjectState:
    """Immutable per-session state for gpbiometricspy Studio."""

    data: pd.DataFrame | None = None
    source_name: str = "No dataset loaded"
    loaded_at: str | None = None
    validation: dict[str, Any] | None = None
    qc: dict[str, Any] | None = None
    annotations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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

    def with_dataset(
        self,
        data: pd.DataFrame,
        *,
        source_name: str,
        validation: dict[str, Any],
        operation: str,
    ) -> "ProjectState":
        event = _event(operation, source_name, len(data), len(data.columns))
        return ProjectState(
            data=data,
            source_name=source_name,
            loaded_at=event["timestamp_utc"],
            validation=validation,
            qc=None,
            annotations=(),
            provenance=(*self.provenance, event),
        )

    def with_qc(self, qc: dict[str, Any], *, operation: str = "run_qc") -> "ProjectState":
        if self.data is None:
            raise ValueError("A dataset must be loaded before QC can be stored.")
        merged = {**(self.qc or {}), **qc}
        event = _event(operation, self.source_name, self.n_rows, self.n_columns)
        return replace(self, qc=merged, provenance=(*self.provenance, event))

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
            annotation_count=len(kept),
        )
        return replace(self, annotations=kept, provenance=(*self.provenance, event))

    def without_annotations(self) -> "ProjectState":
        event = _event(
            "clear_annotations",
            self.source_name,
            self.n_rows,
            self.n_columns,
            annotation_count=0,
        )
        return replace(self, annotations=(), provenance=(*self.provenance, event))
