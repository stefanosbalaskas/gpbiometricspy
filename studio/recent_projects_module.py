from __future__ import annotations

import pandas as pd
from shiny import module, reactive, render, ui

try:
    from studio.error_guidance import format_failure
    from studio.recent_projects import (
        clear_recent_projects,
        load_recent_projects,
        recent_projects_frame,
    )
    from studio.reporting_services import dataset_fingerprint
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from error_guidance import format_failure
    from recent_projects import (
        clear_recent_projects,
        load_recent_projects,
        recent_projects_frame,
    )
    from reporting_services import dataset_fingerprint


@module.ui
def recent_projects_ui():
    return ui.card(
        ui.card_header("Recent projects on this device"),
        ui.p(
            "This optional local index remembers only project name, save time, dataset fingerprint, coarse counts and the suggested recipe filename. It does not store source paths, raw biometric rows, column names, annotations, provenance payloads, parameters or analysis tables.",
            class_="small text-secondary",
        ),
        ui.p(
            "Recent history is a locator, not a restore source. Reopening still requires you to select the source dataset and project recipe, and Studio keeps the exact fingerprint gate.",
            class_="small text-secondary",
        ),
        ui.output_data_frame("table"),
        ui.layout_columns(
            ui.input_action_button("refresh", "Refresh recent projects", class_="btn-outline-primary w-100"),
            ui.input_action_button("clear", "Clear recent-project history", class_="btn-outline-danger w-100"),
            col_widths=(6, 6),
        ),
        ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
    )


@module.server
def recent_projects_server(input, output, session, state, external_refresh):
    local_version = reactive.Value(0)
    local_status = reactive.Value(
        "Recent-project history is local metadata only. Nothing is stored unless you opt in when saving a project recipe."
    )

    @reactive.effect
    @reactive.event(input.refresh)
    def _refresh():
        local_version.set(local_version() + 1)
        local_status.set("Recent-project metadata refreshed from this device.")

    @reactive.effect
    @reactive.event(input.clear)
    def _clear():
        try:
            removed = clear_recent_projects()
            local_version.set(local_version() + 1)
            local_status.set(
                "Recent-project metadata cleared from this device."
                if removed
                else "No recent-project metadata was stored on this device."
            )
        except Exception as exc:
            local_status.set(
                format_failure(
                    "Recent-project history could not be cleared",
                    exc,
                    context="external resource recent-project metadata",
                )
            )

    @render.text
    def status():
        return local_status()

    @render.data_frame
    def table():
        local_version()
        external_refresh()
        try:
            records = load_recent_projects()
            current = state()
            fingerprint = dataset_fingerprint(current.data) if current.data is not None else None
            frame = recent_projects_frame(records, current_fingerprint=fingerprint)
        except Exception as exc:
            frame = pd.DataFrame(
                {
                    "status": [
                        format_failure(
                            "Recent-project history unavailable",
                            exc,
                            context="external resource recent-project metadata",
                        )
                    ]
                }
            )
        if frame.empty:
            frame = pd.DataFrame(
                {"status": ["No recent project metadata is remembered on this device."]}
            )
        return render.DataGrid(frame, filters=True, height="300px")
