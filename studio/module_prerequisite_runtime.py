from __future__ import annotations

from shiny import module, render

try:
    from studio.event_alignment_services import event_time_choices, ttl_column_choices
    from studio.gaze_services import gaze_time_choices, gaze_x_choices, gaze_y_choices
    from studio.module_prerequisites import (
        ModuleReadiness,
        cardiac_readiness,
        eda_readiness,
        event_alignment_readiness,
        gaze_readiness,
        multimodal_readiness,
        pupil_readiness,
        readiness_banner,
    )
    from studio.multimodal_services import (
        event_alignment_available,
        multimodal_signal_choices,
        multimodal_time_choices,
    )
    from studio.ppg_services import hr_signal_choices, ibi_signal_choices, ppg_signal_choices
    from studio.pupil_services import pupil_signal_choices, time_column_choices as pupil_time_choices
    from studio.services import eda_signal_choices
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from event_alignment_services import event_time_choices, ttl_column_choices
    from gaze_services import gaze_time_choices, gaze_x_choices, gaze_y_choices
    from module_prerequisites import (
        ModuleReadiness,
        cardiac_readiness,
        eda_readiness,
        event_alignment_readiness,
        gaze_readiness,
        multimodal_readiness,
        pupil_readiness,
        readiness_banner,
    )
    from multimodal_services import event_alignment_available, multimodal_signal_choices, multimodal_time_choices
    from ppg_services import hr_signal_choices, ibi_signal_choices, ppg_signal_choices
    from pupil_services import pupil_signal_choices, time_column_choices as pupil_time_choices
    from services import eda_signal_choices


def resolve_runtime_readiness(module_key: str, state):
    """Resolve advisory readiness from state shared safely across sibling modules."""

    data = state.data
    try:
        if module_key == "eda_scr":
            return eda_readiness(state, has_signal=bool(eda_signal_choices(data)))
        if module_key == "ppg_hr_hrv":
            return cardiac_readiness(
                state,
                has_signal=bool(
                    ppg_signal_choices(data)
                    or hr_signal_choices(data)
                    or ibi_signal_choices(data)
                ),
            )
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
            has_time = bool(event_time_choices(data))
            has_ttl = bool(ttl_column_choices(data))
            if state.loaded and "event_alignment" not in state.analyses and has_time and not has_ttl:
                if state.qc is None:
                    return ModuleReadiness(
                        "needs_setup",
                        "Foundation QC and event source needed",
                        "A supported reference time column is present, but no TTL/marker source is detected and foundation QC is still pending.",
                        "Run foundation QC, then attach a compatible external event log or load a dataset containing a supported TTL/marker field.",
                    )
                return ModuleReadiness(
                    "needs_setup",
                    "Event source required",
                    "No supported TTL/marker source is detected. External event-log mode remains available when a compatible file is attached.",
                    "Attach a supported external event log, or load a reference dataset containing a supported TTL/marker field.",
                )
            return event_alignment_readiness(
                state,
                has_time=has_time,
                source_mode="ttl",
                has_ttl=has_ttl,
                has_event_upload=False,
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
        return ModuleReadiness(
            "unavailable",
            "Prerequisite check unavailable",
            "Workflow readiness could not be resolved from the current capability metadata.",
            "Inspect the module inputs and Quality Control before running the workflow.",
        )
    raise ValueError(f"Unsupported Studio module readiness key: {module_key}")


@module.server
def module_readiness_runtime_server(input, output, session, state, module_key: str):
    @render.ui
    def module_readiness():
        return readiness_banner(resolve_runtime_readiness(module_key, state()))
