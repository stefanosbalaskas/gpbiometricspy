from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ProjectState:
    """Immutable per-session state for gpbiometricspy Studio."""

    data: pd.DataFrame | None = None
    source_name: str = "No dataset loaded"
    loaded_at: str | None = None
    validation: dict[str, Any] | None = None
    qc: dict[str, Any] | None = None
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
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "source": source_name,
            "n_rows": int(len(data)),
            "n_columns": int(len(data.columns)),
            "status": "ok",
        }
        return ProjectState(
            data=data,
            source_name=source_name,
            loaded_at=event["timestamp_utc"],
            validation=validation,
            qc=None,
            provenance=(*self.provenance, event),
        )

    def with_qc(self, qc: dict[str, Any]) -> "ProjectState":
        if self.data is None:
            raise ValueError("A dataset must be loaded before QC can be stored.")
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "operation": "run_qc",
            "source": self.source_name,
            "n_rows": self.n_rows,
            "n_columns": self.n_columns,
            "status": "ok",
        }
        return replace(self, qc=qc, provenance=(*self.provenance, event))
