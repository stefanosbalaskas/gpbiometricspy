from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shiny import module, render, ui

try:
    from studio.event_alignment_services import event_time_choices, ttl_column_choices
    from studio.gaze_services import gaze_time_choices, gaze_x_choices, gaze_y_choices
    from studio.multimodal_services import (
        event_alignment_available,
        multimodal_signal_choices,
        multimodal_time_choices,
    )
    from studio.ppg_services import hr_signal_choices, ibi_signal_choices, ppg_signal_choices
    from studio.pupil_services import pupil_signal_choices, time_column_choices as pupil_time_choices
    from studio.services import eda_signal_choices
    from studio.state import ProjectState
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from event_alignment_services import event_time_choices, ttl_column_choices
    from gaze_services import gaze_time_choices, gaze_x_choices, gaze_y_choices
    from multimodal_services import event_alignment_available, multimodal_signal_choices, multimodal_time_choices
    from ppg_services import hr_signal_choices, ibi_signal_choices, ppg_signal_choices
    from pupil_services import pupil_signal_choices, time_column_choices as pupil_time_choices
    from services import eda_signal_choices
    from state import ProjectState


@dataclass(frozen=True)
class ModuleReadiness:
    """Human-facing, non-interpretive prerequisite state for one Studio module."""

    kind: str
    title: str
    detail: str
    next_action: str


_MODULE_LABELS = {
    "eda_scr": "EDA / SCR",
    "ppg_hr_hrv": "PPG / HR / HRV",
    "pupil": "Pupil",
    "gaze": "Gaze / Fixation / AOI",
    "event_alignment": "Events & Alignment",
    "multimodal": "Multimodal",
}


def _complete(state: ProjectState, key: str) -> ModuleReadiness | None:
    if key not in state.analyses:
        return None
    label = _MODULE_LABELS[key]
    return ModuleReadiness(
        "complete",
        f"{label} result stored",
        "This project already contains a stored result for this workflow.",
        "Review the outputs, or rerun only if the analysis choices should change.",
    )


def _needs_data(label: str) -> ModuleReadiness:
    return ModuleReadiness(
        "needs_setup",
        "Dataset required",
        f"{label} needs a loaded research dataset before its inputs can be evaluated.",
        "Load the synthetic demo or import a supported Gazepoint research file from Home.",
    )


def _needs_qc(label: str) -> ModuleReadiness:
    return ModuleReadiness(
        "needs_setup",
        "Foundation QC pending",
        f"The required inputs for {label} are present, but foundation QC has not been recorded for this dataset.",
        "Run foundation QC first for the guided path. Expert controls remain available for deliberate use.",
    )


def _ready(label: str, detail: str) -> ModuleReadiness:
    return ModuleReadiness(
        "ready",
        "Ready for guided analysis",
        detail,
        f"Review the selected inputs and run {label} when they match the study design.",
    )


def eda_readiness(state: ProjectState, *, has_signal: bool) -> ModuleReadiness:
    label = _MODULE_LABELS["eda_scr"]
    if not state.loaded:
        return _needs_data(label)
    if complete := _complete(state, "eda_scr"):
        return complete
    if not has_signal:
        return ModuleReadiness(
            "unavailable",
            "EDA channel not detected",
            "The current dataset does not expose a supported EDA/GSR signal through Studio's existing signal-choice service.",
            "Inspect Quality Control or load a dataset containing a supported EDA/GSR channel.",
        )
    if state.qc is None:
        return _needs_qc(label)
    return _ready(label, "A supported EDA/GSR signal is available and foundation QC is recorded.")


def cardiac_readiness(state: ProjectState, *, has_signal: bool) -> ModuleReadiness:
    label = _MODULE_LABELS["ppg_hr_hrv"]
    if not state.loaded:
        return _needs_data(label)
    if complete := _complete(state, "ppg_hr_hrv"):
        return complete
    if not has_signal:
        return ModuleReadiness(
            "unavailable",
            "Cardiac input not detected",
            "No supported pulse waveform, heart-rate, or genuine IBI/RR input is available through the existing cardiac signal services.",
            "Inspect Quality Control or load a dataset containing a supported PPG, HR, or IBI/RR signal.",
        )
    if state.qc is None:
        return _needs_qc(label)
    return _ready(label, "At least one supported PPG, HR, or IBI/RR input is available and foundation QC is recorded.")


def pupil_readiness(state: ProjectState, *, has_pupil: bool, has_time: bool) -> ModuleReadiness:
    label = _MODULE_LABELS["pupil"]
    if not state.loaded:
        return _needs_data(label)
    if complete := _complete(state, "pupil"):
        return complete
    if not has_pupil:
        return ModuleReadiness(
            "unavailable",
            "Pupil channel not detected",
            "The current dataset does not expose a supported pupil signal through Studio's existing pupil service.",
            "Inspect Quality Control or load a dataset containing a supported pupil channel.",
        )
    if not has_time:
        return ModuleReadiness(
            "unavailable",
            "Time column not detected",
            "A pupil signal is present, but the workflow also requires a supported time column.",
            "Confirm the acquisition/export schema or load data with a supported time field.",
        )
    if state.qc is None:
        return _needs_qc(label)
    return _ready(label, "A supported pupil signal and time column are available and foundation QC is recorded.")


def gaze_readiness(state: ProjectState, *, has_x: bool, has_y: bool, has_time: bool) -> ModuleReadiness:
    label = _MODULE_LABELS["gaze"]
    if not state.loaded:
        return _needs_data(label)
    if complete := _complete(state, "gaze"):
        return complete
    if not (has_x and has_y):
        return ModuleReadiness(
            "unavailable",
            "Gaze coordinate pair not detected",
            "Gaze analysis requires supported X and Y coordinate channels from the existing gaze-choice service.",
            "Inspect Quality Control or load data containing a supported gaze X/Y pair.",
        )
    if not has_time:
        return ModuleReadiness(
            "unavailable",
            "Time column not detected",
            "Supported gaze coordinates are present, but fixation/saccade analysis also requires a supported time column.",
            "Confirm the acquisition/export schema or load data with a supported time field.",
        )
    if state.qc is None:
        return _needs_qc(label)
    return _ready(label, "Supported gaze X/Y coordinates and time are available and foundation QC is recorded.")


def event_alignment_readiness(
    state: ProjectState,
    *,
    has_time: bool,
    source_mode: str,
    has_ttl: bool,
    has_event_upload: bool,
) -> ModuleReadiness:
    label = _MODULE_LABELS["event_alignment"]
    if not state.loaded:
        return _needs_data(label)
    if complete := _complete(state, "event_alignment"):
        return complete
    if not has_time:
        return ModuleReadiness(
            "unavailable",
            "Reference time column not detected",
            "Events & Alignment requires a supported reference time column before event anchors can be resolved.",
            "Confirm the reference export schema or load data with a supported time field.",
        )
    if source_mode == "event_log" and not has_event_upload:
        return ModuleReadiness(
            "needs_setup",
            "External event log required",
            "External event-log mode is selected, but no event-log file is currently attached.",
            "Attach a supported event-log CSV/TXT/TSV, or switch the reference source to a detected TTL/marker column.",
        )
    if source_mode != "event_log" and not has_ttl:
        return ModuleReadiness(
            "needs_setup",
            "TTL / marker source required",
            "TTL mode is selected, but the current dataset does not expose a supported TTL/marker column.",
            "Switch to External event log or load a reference dataset containing a supported TTL/marker field.",
        )
    if state.qc is None:
        return _needs_qc(label)
    source = "external event log" if source_mode == "event_log" else "TTL/marker source"
    return _ready(label, f"A supported time column and {source} are available and foundation QC is recorded.")


def multimodal_readiness(
    state: ProjectState,
    *,
    has_time: bool,
    has_event_alignment: bool,
    modality_count: int,
) -> ModuleReadiness:
    label = _MODULE_LABELS["multimodal"]
    if not state.loaded:
        return _needs_data(label)
    if complete := _complete(state, "multimodal"):
        return complete
    if state.qc is None and not has_event_alignment:
        return ModuleReadiness(
            "needs_setup",
            "Quality and event alignment pending",
            "The guided multimodal path has neither foundation QC nor a standardized Events & Alignment result yet.",
            "Run foundation QC, then complete Events & Alignment before combining modalities.",
        )
    if not has_event_alignment:
        return ModuleReadiness(
            "needs_setup",
            "Events & Alignment required",
            "Multimodal Analysis consumes the standardized event table produced by Events & Alignment.",
            "Complete Events & Alignment and review its timing diagnostics first.",
        )
    if not has_time:
        return ModuleReadiness(
            "unavailable",
            "Reference time column not detected",
            "A standardized event result exists, but the current dataset does not expose a supported multimodal time column.",
            "Confirm the source schema before attempting multimodal extraction.",
        )
    if modality_count < 2:
        return ModuleReadiness(
            "needs_setup",
            "At least two modalities recommended",
            "Fewer than two supported physiological/eye-tracking modality families are available for a genuinely multimodal workflow.",
            "Add or restore another supported modality, or analyse the available signal in its dedicated module instead.",
        )
    if state.qc is None:
        return _needs_qc(label)
    return _ready(label, f"Events are aligned and {modality_count} supported modality families are available.")


def resolve_module_readiness(module_key: str, state: ProjectState, input: Any) -> ModuleReadiness:
    """Resolve readiness using the same service-level capability helpers as the scientific modules."""

    data = state.data
    try:
        if module_key == "eda_scr":
            return eda_readiness(state, has_signal=bool(eda_signal_choices(data)))
        if module_key == "ppg_hr_hrv":
            has_signal = bool(
                ppg_signal_choices(data)
                or hr_signal_choices(data)
                or ibi_signal_choices(data)
            )
            return cardiac_readiness(state, has_signal=has_signal)
        if module_key == "pupil":
            return pupil_readiness(
                state,
                has_pupil=bool(pupil_signal_choices(data)),
                has_time=bool(pupil_time_choices(data)),
            )
        if module_key == "gaze":
            return gaze_readiness(
                state,
                has_x=bool(gaze_x_choices(data)),
                has_y=bool(gaze_y_choices(data)),
                has_time=bool(gaze_time_choices(data)),
            )
        if module_key == "event_alignment":
            source_mode = str(input.source_mode() or "ttl")
            return event_alignment_readiness(
                state,
                has_time=bool(event_time_choices(data)),
                source_mode=source_mode,
                has_ttl=bool(ttl_column_choices(data)),
                has_event_upload=bool(input.event_upload()),
            )
        if module_key == "multimodal":
            analyses = state.analyses
            choices = multimodal_signal_choices(data, analyses, prefer_processed=True)
            gaze_family = bool(choices.get("gaze_x")) and bool(choices.get("gaze_y"))
            modality_count = sum(
                bool(choices.get(key)) for key in ("eda", "cardiac", "pupil")
            ) + int(gaze_family)
            return multimodal_readiness(
                state,
                has_time=bool(multimodal_time_choices(data)),
                has_event_alignment=event_alignment_available(analyses),
                modality_count=modality_count,
            )
    except Exception:
        label = _MODULE_LABELS.get(module_key, "This workflow")
        return ModuleReadiness(
            "unavailable",
            "Prerequisite check unavailable",
            f"{label} readiness could not be resolved from the current capability metadata.",
            "Inspect the module inputs and Quality Control before running the workflow.",
        )
    raise ValueError(f"Unsupported Studio module readiness key: {module_key}")


def readiness_banner(readiness: ModuleReadiness):
    tone = {
        "complete": "success",
        "ready": "success",
        "needs_setup": "warning",
        "unavailable": "secondary",
    }.get(readiness.kind, "secondary")
    return ui.div(
        ui.tags.strong(f"Workflow readiness — {readiness.title}"),
        ui.div(readiness.detail, class_="mt-1"),
        ui.tags.small(f"Next: {readiness.next_action}", class_="d-block mt-1"),
        class_=f"alert alert-{tone} py-2 mb-3",
    )


@module.server
def module_readiness_server(input, output, session, state, module_key: str):
    @render.ui
    def module_readiness():
        return readiness_banner(resolve_module_readiness(module_key, state(), input))
