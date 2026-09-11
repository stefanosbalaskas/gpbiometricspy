from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from studio.state import ProjectState
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from state import ProjectState


_STAGE_ORDER = {
    "Project": 1,
    "Quality": 2,
    "Analyze": 3,
    "Integrate": 4,
    "Model": 5,
    "Report": 6,
}

_ANALYSIS_LABELS = {
    "eda_scr": "EDA / SCR",
    "ppg_hr_hrv": "PPG / HR / HRV",
    "pupil": "Pupil",
    "gaze": "Gaze / Fixation / AOI",
    "event_alignment": "Events & Alignment",
    "multimodal": "Multimodal",
    "statistics_modelling": "Statistics & modelling",
}


def _operation_stage(operation: str) -> str:
    key = str(operation or "").strip().lower()
    if key in {"run_qc", "guided_foundation_qc"} or key.startswith("run_advanced_qc"):
        return "Quality"
    if key in {"add_annotation", "remove_annotation", "clear_annotations"}:
        return "Analyze"
    if key.startswith("run_") and key.endswith("_analysis"):
        analysis = key[4:-9]
        if analysis in {"event_alignment", "multimodal"}:
            return "Integrate"
        if analysis == "statistics_modelling" or "model" in analysis or "statistic" in analysis:
            return "Model"
        return "Analyze"
    if key == "build_reporting_artifacts" or "report" in key:
        return "Report"
    return "Project"


def _operation_label(event: dict[str, Any]) -> str:
    operation = str(event.get("operation") or "").strip()
    key = operation.lower()
    fixed = {
        "set_project_name": "Project renamed",
        "load_demo": "Synthetic dataset loaded",
        "load_upload": "Research dataset loaded",
        "load_guided_demo": "Guided synthetic dataset loaded",
        "run_qc": "Foundation QC completed",
        "guided_foundation_qc": "Foundation QC completed",
        "add_annotation": "Annotation added",
        "remove_annotation": "Annotation removed",
        "clear_annotations": "Annotations cleared",
        "start_guided_walkthrough": "Guided walkthrough started",
        "build_reporting_artifacts": "Reporting artifacts built",
        "restore_project_recipe": "Project recipe restored",
    }
    if key in fixed:
        return fixed[key]
    if key.startswith("run_") and key.endswith("_analysis"):
        analysis = str(event.get("analysis") or key[4:-9]).strip().lower()
        label = _ANALYSIS_LABELS.get(analysis, analysis.replace("_", " ").title())
        return f"{label} completed"
    return operation.replace("_", " ").strip().title() or "Recorded operation"


def _event_detail(event: dict[str, Any]) -> str:
    operation = str(event.get("operation") or "").strip().lower()
    if operation in {"load_demo", "load_upload", "load_guided_demo"}:
        rows = event.get("n_rows")
        columns = event.get("n_columns")
        if isinstance(rows, int) and isinstance(columns, int):
            return f"Dataset registered with {rows:,} rows and {columns:,} columns."
        return "Dataset registered in the current Studio session."
    if operation == "set_project_name":
        name = str(event.get("project_name") or "").strip()
        return f"Project identity changed to {name!r}." if name else "Project identity updated."
    if operation in {"run_qc", "guided_foundation_qc"}:
        return "Foundation quality-control results were recorded in project state."
    if operation.startswith("run_") and operation.endswith("_analysis"):
        return "Analysis result and recorded parameters were added to project state."
    if operation == "add_annotation":
        kind = str(event.get("annotation_type") or "annotation").replace("_", " ")
        return f"Recorded {kind}; project annotation count is {event.get('annotation_count', 'updated')}."
    if operation == "remove_annotation":
        return f"Annotation removed; {event.get('annotation_count', 'updated')} annotations remain."
    if operation == "clear_annotations":
        return "All manual annotations were cleared."
    if operation == "start_guided_walkthrough":
        preset = str(event.get("preset") or "guided").replace("_", " ")
        return f"Started the {preset} guided workflow."
    if operation == "build_reporting_artifacts":
        return "Report, manifest, methods and reproducibility artifacts were regenerated."
    if operation == "restore_project_recipe":
        count = event.get("restored_provenance_count")
        if isinstance(count, int):
            return f"Metadata restored after fingerprint verification; {count:,} prior provenance records were supplied."
        return "Metadata restored after exact dataset-fingerprint verification."
    return "Recorded Studio operation."


def _display_time(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    try:
        parsed = pd.to_datetime(text, utc=True)
    except (TypeError, ValueError):
        return text
    if pd.isna(parsed):
        return text
    return parsed.strftime("%Y-%m-%d %H:%M:%S UTC")


def project_timeline(state: ProjectState) -> pd.DataFrame:
    """Return a readable, metadata-only view of the recorded Studio provenance log."""
    columns = ["step", "time_utc", "stage", "stage_order", "action", "detail", "status"]
    if not state.provenance:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(state.provenance, start=1):
        if not isinstance(raw, dict):
            continue
        stage = _operation_stage(raw.get("operation", ""))
        rows.append(
            {
                "step": index,
                "time_utc": _display_time(raw.get("timestamp_utc")),
                "stage": stage,
                "stage_order": _STAGE_ORDER[stage],
                "action": _operation_label(raw),
                "detail": _event_detail(raw),
                "status": str(raw.get("status") or "recorded"),
            }
        )
    return pd.DataFrame(rows, columns=columns)
