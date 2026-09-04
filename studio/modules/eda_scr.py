from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.services import (
        analysis_group_column_choices,
        eda_analysis_tables,
        eda_reproducibility_script,
        eda_signal_choices,
        run_eda_scr_analysis,
        time_column_choices,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import (
        analysis_group_column_choices,
        eda_analysis_tables,
        eda_reproducibility_script,
        eda_signal_choices,
        run_eda_scr_analysis,
        time_column_choices,
    )


@module.ui
def eda_scr_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("EDA / SCR analysis controls"),
                ui.input_radio_buttons(
                    "mode",
                    "Workflow mode",
                    choices={"guided": "Guided", "expert": "Expert"},
                    selected="guided",
                    inline=True,
                ),
                ui.input_select("signal_col", "EDA signal", choices=[]),
                ui.input_select("time_col", "Time column", choices=[]),
                ui.input_select("group_col", "Grouping column", choices={"": "No grouping"}),
                ui.hr(),
                ui.tags.strong("Expert parameters"),
                ui.tags.small(
                    "Guided mode uses window=31, automatic threshold, and minimum peak distance=10.",
                    class_="text-secondary d-block mb-2",
                ),
                ui.input_numeric("window_size", "Tonic window (samples)", value=31, min=1, step=2),
                ui.input_checkbox("auto_threshold", "Automatic SCR threshold", value=True),
                ui.input_numeric("threshold", "Manual SCR threshold", value=0.05, min=0, step=0.01),
                ui.input_numeric("min_peak_distance", "Minimum peak distance (samples)", value=10, min=1),
                ui.input_checkbox("standardise_plot", "Standardise decomposition plot", value=False),
                ui.input_task_button(
                    "run",
                    "Run EDA / SCR analysis",
                    label_busy="Analysing EDA...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Scientific interpretation"),
                ui.p(
                    "Studio delegates decomposition, candidate SCR detection, summaries, and plots to gpbiometricspy."
                ),
                ui.p(
                    "The default rolling-median residual decomposition is descriptive. Confirmatory EDA/SCR work may require specialised decomposition choices, preregistered thresholds, event timing, and sensitivity analysis.",
                    class_="text-secondary",
                ),
                ui.p(
                    "EDA and SCR features quantify electrodermal signal characteristics; they do not identify emotion, stress, trust, preference, cognition, or diagnosis.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.layout_column_wrap(
            ui.value_box("Decomposition", ui.output_text("decomposition_method"), theme="primary"),
            ui.value_box("Detected SCR events", ui.output_text("event_count")),
            ui.value_box("Groups", ui.output_text("group_count")),
            ui.value_box("Status", ui.output_text("analysis_status")),
            width=1 / 4,
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Overview",
                ui.layout_columns(
                    ui.card(ui.card_header("EDA quality"), ui.output_data_frame("quality")),
                    ui.card(ui.card_header("Decomposition overview"), ui.output_data_frame("decomposition_overview")),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("SCR event overview"), ui.output_data_frame("event_overview")),
                    ui.card(ui.card_header("SCR group summary"), ui.output_data_frame("event_groups")),
                    col_widths=(5, 7),
                ),
            ),
            ui.nav_panel(
                "Decomposition",
                ui.card(
                    ui.card_header("Observed, tonic, and phasic EDA"),
                    ui.output_plot("decomposition_plot", height="500px"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "SCR events",
                ui.card(
                    ui.card_header("Candidate SCR events"),
                    ui.output_plot("events_plot", height="500px"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("Detected event table"),
                    ui.output_data_frame("events_table"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Summaries",
                ui.card(
                    ui.card_header("Tonic / phasic summary"),
                    ui.output_data_frame("tonic_phasic_summary"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("Parameters used"),
                    ui.output_data_frame("parameters"),
                ),
            ),
            ui.nav_panel(
                "Export",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Tabular exports"),
                        ui.download_button("download_events", "Download SCR events CSV", class_="btn-success w-100"),
                        ui.download_button("download_summary", "Download EDA summary CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_decomposition", "Download decomposition CSV", class_="btn-outline-success w-100 mt-2"),
                    ),
                    ui.card(
                        ui.card_header("Reproducible code"),
                        ui.p("Export the equivalent public gpbiometricspy calls used by this Studio workflow."),
                        ui.download_button("download_script", "Download Python script", class_="btn-primary w-100"),
                        ui.output_text_verbatim("script_preview"),
                    ),
                    col_widths=(5, 7),
                ),
            ),
            id="eda_tabs",
            selected="Overview",
        ),
    )


@module.server
def eda_scr_server(input, output, session, state, status_text):
    local_status = reactive.Value("Load a dataset with an EDA channel, then run the Guided workflow.")

    @reactive.effect
    def _sync_choices():
        data = state().data
        signals = eda_signal_choices(data)
        times = time_column_choices(data)
        groups = analysis_group_column_choices(data)
        ui.update_select("signal_col", choices=signals, selected=signals[0] if signals else None)
        ui.update_select("time_col", choices=times, selected=times[0] if times else None)
        group_choices = {"": "No grouping", **{column: column for column in groups}}
        ui.update_select("group_col", choices=group_choices, selected=groups[0] if groups else "")

    def _result():
        return state().analyses.get("eda_scr")

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a dataset before running EDA/SCR analysis.")
            return
        signal_col = input.signal_col()
        if not signal_col:
            local_status.set("No supported EDA signal was detected.")
            return
        guided = input.mode() == "guided"
        window_size = 31 if guided else int(input.window_size())
        threshold = None if guided or input.auto_threshold() else float(input.threshold())
        min_peak_distance = 10 if guided else int(input.min_peak_distance())
        standardise_plot = False if guided else bool(input.standardise_plot())
        parameters = {
            "signal_col": signal_col,
            "time_col": input.time_col() or None,
            "group_col": input.group_col() or None,
            "window_size": window_size,
            "threshold": threshold,
            "min_peak_distance": min_peak_distance,
            "standardise_plot": standardise_plot,
            "mode": input.mode(),
        }
        try:
            result = run_eda_scr_analysis(
                current.data,
                signal_col=signal_col,
                time_col=parameters["time_col"],
                group_col=parameters["group_col"],
                window_size=window_size,
                threshold=threshold,
                min_peak_distance=min_peak_distance,
                standardise_plot=standardise_plot,
            )
            result["parameters"]["mode"] = input.mode()
            state.set(current.with_analysis("eda_scr", result, parameters=parameters))
            local_status.set("EDA/SCR workflow complete using public gpbiometricspy APIs.")
            status_text.set("EDA/SCR analysis complete. Review the Analysis tab and export reproducible outputs.")
        except Exception as exc:
            local_status.set(f"EDA/SCR analysis failed: {exc}")

    @render.text
    def status():
        return local_status()

    @render.text
    def decomposition_method():
        result = _result()
        decomposition = result.get("decomposition") if isinstance(result, dict) else None
        if isinstance(decomposition, pd.DataFrame):
            overview = decomposition.attrs.get("overview")
            if isinstance(overview, pd.DataFrame) and not overview.empty and "method" in overview:
                return str(overview.iloc[0]["method"])
        return "Not run"

    @render.text
    def event_count():
        result = _result()
        events = result.get("events") if isinstance(result, dict) else None
        table = events.get("events") if isinstance(events, dict) else None
        return "0" if not isinstance(table, pd.DataFrame) else f"{len(table):,}"

    @render.text
    def group_count():
        result = _result()
        events = result.get("events") if isinstance(result, dict) else None
        overview = events.get("overview") if isinstance(events, dict) else None
        if isinstance(overview, pd.DataFrame) and not overview.empty and "group_count" in overview:
            return str(int(overview.iloc[0]["group_count"]))
        return "0"

    @render.text
    def analysis_status():
        result = _result()
        events = result.get("events") if isinstance(result, dict) else None
        overview = events.get("overview") if isinstance(events, dict) else None
        if isinstance(overview, pd.DataFrame) and not overview.empty and "status" in overview:
            return str(overview.iloc[0]["status"])
        return "Not run"

    def _table(name: str, fallback: str) -> pd.DataFrame:
        table = eda_analysis_tables(_result()).get(name)
        return table if isinstance(table, pd.DataFrame) and not table.empty else pd.DataFrame({"status": [fallback]})

    @render.data_frame
    def quality():
        return render.DataGrid(_table("quality", "Run EDA/SCR analysis to populate EDA quality."), filters=True)

    @render.data_frame
    def decomposition_overview():
        return render.DataGrid(_table("decomposition_overview", "No decomposition result available."), filters=True)

    @render.data_frame
    def event_overview():
        return render.DataGrid(_table("events_overview", "No SCR event result available."), filters=True)

    @render.data_frame
    def event_groups():
        return render.DataGrid(_table("events_group_summary", "No SCR group summary available."), filters=True)

    @render.data_frame
    def events_table():
        return render.DataGrid(_table("events_events", "No SCR events detected or analysis has not run."), filters=True, height="360px")

    @render.data_frame
    def tonic_phasic_summary():
        tables = eda_analysis_tables(_result())
        table = tables.get("summary_summary") or tables.get("summary_group_summary") or tables.get("summary_overview")
        if not isinstance(table, pd.DataFrame) or table.empty:
            table = pd.DataFrame({"status": ["No tonic/phasic summary available."]})
        return render.DataGrid(table, filters=True, height="360px")

    @render.data_frame
    def parameters():
        result = _result()
        p = result.get("parameters") if isinstance(result, dict) else None
        table = pd.DataFrame([p]) if isinstance(p, dict) else pd.DataFrame({"status": ["Run analysis to record parameters."]})
        return render.DataGrid(table)

    @render.plot(alt="Gazepoint EDA decomposition plot showing observed, tonic, and phasic components")
    def decomposition_plot():
        result = _result()
        if isinstance(result, dict) and isinstance(result.get("decomposition"), pd.DataFrame):
            data = result["decomposition"]
            p = result.get("parameters") or {}
            signal = p.get("signal_col")
            signals = [c for c in [signal, "studio_eda_tonic", "studio_eda_phasic"] if c and c in data.columns]
            return gp.plot_gazepoint_eda_decomposition(
                data,
                time_col=p.get("time_col"),
                signal_cols=signals,
                group_cols=[p["group_col"]] if p.get("group_col") else None,
                standardise=bool(p.get("standardise_plot", False)),
                max_points=8000,
                title="gpbiometricspy Studio: EDA decomposition",
            )
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Run EDA/SCR analysis to generate the decomposition plot.", ha="center", va="center")
        ax.set_axis_off()
        return fig

    @render.plot(alt="Gazepoint electrodermal trace with candidate skin conductance responses")
    def events_plot():
        result = _result()
        if isinstance(result, dict):
            data = result.get("decomposition")
            events = result.get("events")
            peaks = events.get("events") if isinstance(events, dict) else None
            p = result.get("parameters") or {}
            if isinstance(data, pd.DataFrame) and isinstance(peaks, pd.DataFrame):
                try:
                    return gp.plot_gazepoint_scr_events(
                        data,
                        peaks,
                        time_col=p.get("time_col"),
                        phasic_col="studio_eda_phasic",
                        group_cols=[p["group_col"]] if p.get("group_col") else None,
                        max_points=8000,
                        title="gpbiometricspy Studio: candidate SCR events",
                    )
                except (TypeError, ValueError):
                    pass
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Run EDA/SCR analysis to generate the SCR event plot.", ha="center", va="center")
        ax.set_axis_off()
        return fig

    @render.text
    def script_preview():
        script = eda_reproducibility_script(_result())
        lines = script.splitlines()
        return "\n".join(lines[:18]) + ("\n..." if len(lines) > 18 else "")

    @render.download_button(filename="gpbiometricspy_scr_events.csv")
    def download_events():
        table = eda_analysis_tables(_result()).get("events_events", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_eda_summary.csv")
    def download_summary():
        tables = eda_analysis_tables(_result())
        table = tables.get("summary_summary") or tables.get("summary_group_summary") or tables.get("summary_overview") or pd.DataFrame()
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_eda_decomposition.csv")
    def download_decomposition():
        result = _result()
        table = result.get("decomposition") if isinstance(result, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame()
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_eda_scr_analysis.py")
    def download_script():
        yield eda_reproducibility_script(_result())
