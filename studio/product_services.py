
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import re
import unicodedata
from typing import Any

import pandas as pd

try:
    from studio.state import ProjectState
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from state import ProjectState


@dataclass(frozen=True)
class GuidedStart:
    key: str
    label: str
    project_name: str
    summary: str
    target_nav: str
    run_foundation_qc: bool = True


_GUIDED_STARTS = (
    GuidedStart(
        key="multimodal",
        label="Multimodal research walkthrough",
        project_name="Synthetic multimodal walkthrough",
        summary="Load the bundled multimodal demo, run foundation QC, then continue through alignment and multimodal analysis.",
        target_nav="multimodal",
    ),
    GuidedStart(
        key="eye_tracking",
        label="Eye-tracking walkthrough",
        project_name="Synthetic eye-tracking walkthrough",
        summary="Load the bundled demo, run foundation QC, then begin with pupil and gaze/AOI workflows.",
        target_nav="pupil",
    ),
    GuidedStart(
        key="physiology",
        label="EDA and cardiovascular walkthrough",
        project_name="Synthetic physiology walkthrough",
        summary="Load the bundled demo, run foundation QC, then begin with EDA/SCR before PPG/HR/HRV.",
        target_nav="eda_scr",
    ),
)


def guided_start_choices() -> dict[str, str]:
    """Return stable value-to-label choices for the Studio guided-start control."""
    return {preset.key: preset.label for preset in _GUIDED_STARTS}


def guided_start(value: Any) -> GuidedStart:
    """Resolve one guided-start preset and reject unknown values explicitly."""
    key = str(value or "").strip()
    for preset in _GUIDED_STARTS:
        if preset.key == key:
            return preset
    allowed = ", ".join(preset.key for preset in _GUIDED_STARTS)
    raise ValueError(f"Unknown guided-start preset {key!r}. Allowed values: {allowed}.")


def _analysis_names(state: ProjectState) -> set[str]:
    return {str(name).strip().lower() for name in state.analyses if str(name).strip()}


def _operation_names(state: ProjectState) -> set[str]:
    return {
        str(event.get("operation") or "").strip().lower()
        for event in state.provenance
        if isinstance(event, dict)
    }


def workflow_progress(state: ProjectState) -> pd.DataFrame:
    """Summarize the six-stage Studio journey without changing scientific state."""
    names = _analysis_names(state)
    operations = _operation_names(state)
    alignment_done = any("align" in name or "multimodal" in name for name in names)
    modelling_done = any("model" in name or "statistic" in name for name in names)
    core_analysis_done = bool(
        names
        - {name for name in names if "align" in name or "multimodal" in name or "model" in name or "statistic" in name}
    )
    report_done = "build_reporting_artifacts" in operations

    def blocked_or_ready(ready: bool, *, optional: bool = False) -> str:
        if optional:
            return "Optional"
        return "Ready" if ready else "Blocked"

    rows = [
        {
            "stage": "Project",
            "status": "Complete" if state.loaded else "Start here",
            "next_action": "Inspect the loaded dataset" if state.loaded else "Load data or start a guided demo",
            "destination": "Home",
        },
        {
            "stage": "Quality",
            "status": "Complete" if state.qc is not None else blocked_or_ready(state.loaded),
            "next_action": "Review QC evidence" if state.qc is not None else "Run foundation QC",
            "destination": "Quality",
        },
        {
            "stage": "Analyze",
            "status": "Complete" if core_analysis_done else blocked_or_ready(state.qc is not None),
            "next_action": "Review stored analyses" if core_analysis_done else "Choose a signal workflow",
            "destination": "Analyze",
        },
        {
            "stage": "Align",
            "status": "Complete" if alignment_done else blocked_or_ready(state.qc is not None, optional=True),
            "next_action": "Review alignment outputs" if alignment_done else "Use when events or streams require alignment",
            "destination": "Integrate",
        },
        {
            "stage": "Model",
            "status": "Complete" if modelling_done else blocked_or_ready(core_analysis_done, optional=True),
            "next_action": "Review model outputs" if modelling_done else "Use when inferential modelling is required",
            "destination": "Model",
        },
        {
            "stage": "Report",
            "status": "Complete" if report_done else blocked_or_ready(state.loaded and state.qc is not None),
            "next_action": "Export or replay" if report_done else "Build reporting artifacts and save a project recipe",
            "destination": "Report",
        },
    ]
    return pd.DataFrame(rows, columns=["stage", "status", "next_action", "destination"])


def readiness_percent(state: ProjectState) -> int:
    """Return a simple first-session completion score for the required product journey."""
    names = _analysis_names(state)
    operations = _operation_names(state)
    core_analysis_done = bool(
        names
        - {name for name in names if "align" in name or "multimodal" in name or "model" in name or "statistic" in name}
    )
    milestones = (
        state.loaded,
        state.qc is not None,
        core_analysis_done,
        "build_reporting_artifacts" in operations,
    )
    return int(round(100 * sum(bool(value) for value in milestones) / len(milestones)))


_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def project_export_stem(name: Any) -> str:
    """Return a cross-platform, Unicode-preserving project stem for exported artifacts."""
    text = unicodedata.normalize("NFKC", str(name or "")).strip()
    text = re.sub(r"[^\w.-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip(" ._-")
    if not text:
        text = "gpbiometricspy-studio-project"
    if text.upper() in _WINDOWS_RESERVED:
        text = f"project-{text}"
    return text[:72].rstrip(" .") or "gpbiometricspy-studio-project"


def support_snapshot(
    state: ProjectState,
    *,
    runtime_mode: str,
    package_version: str,
) -> dict[str, Any]:
    """Return privacy-safe support metadata without raw samples or the source filename."""
    source_suffix = Path(state.source_name).suffix.lower() if state.loaded else ""
    return {
        "product": "gpbiometricspy Studio",
        "package_version": str(package_version),
        "python_version": platform.python_version(),
        "runtime_mode": str(runtime_mode),
        "project_name": state.project_name,
        "dataset_loaded": state.loaded,
        "source_type": source_suffix or None,
        "row_count": state.n_rows,
        "column_count": state.n_columns,
        "foundation_qc_complete": state.qc is not None,
        "analysis_names": sorted(map(str, state.analyses)),
        "annotation_count": len(state.annotations),
        "provenance_events": len(state.provenance),
        "raw_data_included": False,
        "source_filename_included": False,
    }
