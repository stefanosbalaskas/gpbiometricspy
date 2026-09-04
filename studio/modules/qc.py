from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.services import physiology_quality_table, run_advanced_qc, time_column_choices
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import physiology_quality_table, run_advanced_qc, time_column_choices


@module.ui
def qc_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Advanced QC settings"),
                ui.input_select("time_col", "Time column", choices=[]),
                ui.input_numeric("sampling_rate", "Expected sampling rate (Hz)", value=60, min=1),
                ui.layout_columns(
                    ui.input_numeric("gsr_min", "GSR minimum", value=0),
                    ui.input_numeric("gsr_max", "GSR maximum", value=100),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.input_numeric("hr_min", "HR minimum (bpm)", value=30),
                    ui.input_numeric("hr_max", "HR maximum (bpm)", value=220),
                    col_widths=(6, 6),
                ),
                ui.input_task_button("run", "Run advanced QC", label_busy="Running QC...", width="100%"),
                ui.tags.small(ui.output_text("status"), class_="text-secondary"),
            ),
            ui.card(
                ui.card_header("QC interpretation"),
                ui.p(
                    "These checks identify data-quality and timing conditions. They do not convert physiological or gaze measures into psychological states."
                ),
                ui.p(
                    "Thresholds are visible and editable so that exported provenance can document the exact QC configuration used.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Time integrity",
                ui.layout_columns(
                    ui.card(ui.card_header("Time overview"), ui.output_data_frame("time_overview")),
                    ui.card(ui.card_header("Segment summary"), ui.output_data_frame("time_segments")),
                    col_widths=(5, 7),
                ),
                ui.card(
                    ui.card_header("Time-reset diagnostics"),
                    ui.output_plot("time_plot", height="430px"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Physiology",
                ui.card(
                    ui.card_header("EDA / HR quality audit"),
                    ui.output_data_frame("physiology_quality"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("Biometric signal overview"),
                    ui.output_plot("physiology_plot", height="430px"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Gaze",
                ui.layout_columns(
                    ui.card(ui.card_header("Gaze summary"), ui.output_data_frame("gaze_summary")),
                    ui.card(ui.card_header("Gaze checks"), ui.output_data_frame("gaze_checks")),
                    col_widths=(5, 7),
                ),
                ui.card(
                    ui.card_header("Group-level gaze diagnostics"),
                    ui.output_data_frame("gaze_groups"),
                    full_screen=True,
                ),
            ),
            id="qc_tabs",
            selected="Time integrity",
        ),
    )


@module.server
def qc_server(input, output, session, state, status_text):
    local_status = reactive.Value("Load a dataset, review settings, then run advanced QC.")

    @reactive.effect
    def _sync_time_choices():
        choices = time_column_choices(state().data)
        ui.update_select("time_col", choices=choices, selected=choices[0] if choices else None)

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a dataset before running advanced QC.")
            return
        try:
            qc = run_advanced_qc(
                current.data,
                time_col=input.time_col() or None,
                expected_sampling_rate_hz=float(input.sampling_rate()),
                gsr_min=float(input.gsr_min()),
                gsr_max=float(input.gsr_max()),
                hr_min=float(input.hr_min()),
                hr_max=float(input.hr_max()),
            )
            state.set(current.with_qc(qc, operation="run_advanced_qc"))
            local_status.set("Advanced QC complete using public gpbiometricspy APIs.")
            status_text.set("Advanced QC complete. Review the Quality Control tab.")
        except Exception as exc:
            local_status.set(f"Advanced QC failed: {exc}")

    @render.text
    def status():
        return local_status()

    @render.data_frame
    def time_overview():
        audit = (state().qc or {}).get("time_resets")
        table = audit.get("overview") if isinstance(audit, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame({"status": [(state().qc or {}).get("time_resets_error", "Run advanced QC to populate this table.")]})
        return render.DataGrid(table, filters=True)

    @render.data_frame
    def time_segments():
        audit = (state().qc or {}).get("time_resets")
        table = audit.get("segment_summary") if isinstance(audit, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame({"status": ["No segment summary available."]})
        return render.DataGrid(table, filters=True, height="360px")

    @render.plot(alt="Gazepoint time-reset diagnostic plot")
    def time_plot():
        audit = (state().qc or {}).get("time_resets")
        if isinstance(audit, dict):
            return gp.plot_gazepoint_time_resets(audit)
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Run advanced QC to generate timing diagnostics.", ha="center", va="center")
        ax.set_axis_off()
        return fig

    @render.data_frame
    def physiology_quality():
        table = physiology_quality_table(state().qc)
        if table.empty:
            table = pd.DataFrame({"status": ["No EDA/HR quality result is available."]})
        return render.DataGrid(table, filters=True)

    @render.plot(alt="Gazepoint biometric signal overview")
    def physiology_plot():
        data = state().data
        if data is not None:
            signals = [c for c in ["GSR_US", "GSR", "HR", "IBI", "HRP"] if c in data.columns]
            if signals:
                time_choices = time_column_choices(data)
                return gp.plot_gazepoint_biometric_signals(
                    data,
                    signal_cols=signals[:4],
                    time_col=time_choices[0] if time_choices else None,
                    max_points=5000,
                )
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No supported physiology signals are available.", ha="center", va="center")
        ax.set_axis_off()
        return fig

    def _gaze_result():
        return (state().qc or {}).get("gaze_validation")

    @render.data_frame
    def gaze_summary():
        result = _gaze_result()
        table = result.get("summary") if isinstance(result, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame({"status": [(state().qc or {}).get("gaze_validation_error", "Run advanced QC to populate gaze checks.")]})
        return render.DataGrid(table, filters=True)

    @render.data_frame
    def gaze_checks():
        result = _gaze_result()
        table = result.get("checks") if isinstance(result, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame({"status": ["No gaze checks available."]})
        return render.DataGrid(table, filters=True)

    @render.data_frame
    def gaze_groups():
        result = _gaze_result()
        table = result.get("groups") if isinstance(result, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame({"status": ["No group-level gaze diagnostics available."]})
        return render.DataGrid(table, filters=True, height="360px")
