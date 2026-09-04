from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.pupil_services import (
        analysis_group_column_choices,
        marker_column_choices,
        onset_column_choices,
        pupil_analysis_tables,
        pupil_reproducibility_script,
        pupil_signal_choices,
        pupil_validity_choices,
        run_pupil_analysis,
        time_column_choices,
        trial_column_choices,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from pupil_services import (
        analysis_group_column_choices,
        marker_column_choices,
        onset_column_choices,
        pupil_analysis_tables,
        pupil_reproducibility_script,
        pupil_signal_choices,
        pupil_validity_choices,
        run_pupil_analysis,
        time_column_choices,
        trial_column_choices,
    )


def _placeholder(message: str):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


@module.ui
def pupil_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Pupil analysis controls"),
                ui.input_radio_buttons(
                    "mode",
                    "Workflow mode",
                    choices={"guided": "Guided", "expert": "Expert"},
                    selected="guided",
                    inline=True,
                ),
                ui.input_select("pupil_col", "Pupil channel", choices={"": "No pupil channel detected"}),
                ui.input_select("validity_col", "Validity channel", choices={"": "Automatic / none"}),
                ui.input_select("time_col", "Time column", choices={"": "No time column detected"}),
                ui.input_select("group_col", "Participant / grouping column", choices={"": "No grouping"}),
                ui.input_select("trial_col", "Trial column", choices={"": "No trial column"}),
                ui.hr(),
                ui.tags.strong("Expert preprocessing"),
                ui.tags.small(
                    "Guided mode detects blink-like gaps only. It does not interpolate, smooth, baseline-correct, or create event responses automatically.",
                    class_="text-secondary d-block mb-2",
                ),
                ui.input_numeric("min_blink_samples", "Minimum blink samples", value=2, min=1, step=1),
                ui.input_checkbox("interpolate", "Interpolate eligible internal pupil gaps", value=False),
                ui.layout_columns(
                    ui.input_numeric("max_gap", "Maximum interpolation gap (s)", value=0.25, min=0.01, step=0.05),
                    ui.input_select("interp_method", "Interpolation", choices={"linear": "Linear", "constant": "Constant / carry-forward"}, selected="linear"),
                    col_widths=(6, 6),
                ),
                ui.input_checkbox("smooth", "Apply centered moving-average smoothing", value=False),
                ui.input_numeric("smooth_window", "Smoothing window (odd samples)", value=5, min=1, step=2),
                ui.hr(),
                ui.tags.strong("Task-locked analysis"),
                ui.input_checkbox("baseline_correct", "Create baseline-corrected pupil channel", value=False),
                ui.input_select("stimulus_onset_col", "Stimulus-onset column", choices={"": "Not selected"}),
                ui.tags.small(
                    "Baseline-correction limits below are expressed in the selected time column's units.",
                    class_="text-secondary d-block",
                ),
                ui.layout_columns(
                    ui.input_numeric("baseline_start", "Baseline start", value=-0.5, step=0.1),
                    ui.input_numeric("baseline_end", "Baseline end", value=-0.1, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.input_select("baseline_function", "Baseline statistic", choices={"median": "Median", "mean": "Mean"}, selected="median"),
                    ui.input_select("correction", "Correction", choices={"subtract": "Subtract", "percent": "Percent change", "divide": "Divide"}, selected="subtract"),
                    col_widths=(6, 6),
                ),
                ui.input_checkbox("event_summary", "Summarize event-locked pupil responses", value=False),
                ui.input_select("event_onset_col", "Event-onset column", choices={"": "Not selected"}),
                ui.input_select("marker_col", "Or TTL / marker column", choices={"": "Not selected"}),
                ui.tags.small(
                    "Event windows are in seconds after gpbiometricspy time normalization. Prefer an explicit event-onset column when available.",
                    class_="text-secondary d-block",
                ),
                ui.layout_columns(
                    ui.input_numeric("pre_s", "Pre-event (s)", value=1.0, min=0, step=0.1),
                    ui.input_numeric("post_s", "Post-event (s)", value=3.0, min=0.1, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.input_numeric("response_start", "Response start (s)", value=0.0, step=0.1),
                    ui.input_numeric("response_end", "Response end (s)", value=3.0, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.input_task_button(
                    "run",
                    "Run Pupil Analysis",
                    label_busy="Analysing pupil signal...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Scientific interpretation"),
                ui.p(
                    "The workflow delegates blink detection, pupil interpolation, smoothing, baseline correction, missingness diagnostics, and event summaries to public gpbiometricspy APIs."
                ),
                ui.p(
                    "Blink/dropout repair is never implicit in Guided mode. Interpolation can alter amplitudes and temporal structure, so repaired samples remain explicitly flagged and should be reported.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Task-locked pupil responses depend on valid event timing, a defensible pre-event baseline, sufficient usable samples, luminance control where relevant, and protocol-specific exclusion rules.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Pupil diameter is a physiological measurement influenced by multiple optical, autonomic, cognitive, and environmental factors; it is not a direct measure of attention, effort, emotion, trust, preference, or diagnosis.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.layout_column_wrap(
            ui.value_box("Blink intervals", ui.output_text("blink_count"), theme="primary"),
            ui.value_box("Flagged samples", ui.output_text("flagged_pct")),
            ui.value_box("Interpolated samples", ui.output_text("interpolated_count")),
            ui.value_box("Event responses", ui.output_text("event_count")),
            width=1 / 4,
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Overview",
                ui.layout_columns(
                    ui.card(ui.card_header("Blink / invalid-sample audit"), ui.output_data_frame("blink_summary"), full_screen=True),
                    ui.card(ui.card_header("Blink intervals"), ui.output_data_frame("blink_intervals"), full_screen=True),
                    col_widths=(5, 7),
                ),
                ui.card(
                    ui.card_header("Package-native pupil missingness diagnostic"),
                    ui.output_plot("missingness_plot", height="420px"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Preprocessing",
                ui.card(
                    ui.card_header("Raw and analysis pupil trace"),
                    ui.output_plot("pupil_trace", height="480px"),
                    full_screen=True,
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Smoothing summary"), ui.output_data_frame("smoothing_summary")),
                    ui.card(ui.card_header("Repair flags"), ui.output_data_frame("repair_flags"), full_screen=True),
                    col_widths=(5, 7),
                ),
            ),
            ui.nav_panel(
                "Event-locked",
                ui.layout_columns(
                    ui.card(ui.card_header("Resolved event table"), ui.output_data_frame("events_table"), full_screen=True),
                    ui.card(ui.card_header("Pupil event-response summary"), ui.output_data_frame("event_summary_table"), full_screen=True),
                    col_widths=(5, 7),
                ),
                ui.p(
                    "Event-response amplitude, latency, mean response and AUC are baseline-relative summaries. They are descriptive features unless the study design and inferential model justify stronger claims.",
                    class_="text-secondary small",
                ),
            ),
            ui.nav_panel(
                "Export",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Tabular exports"),
                        ui.download_button("download_blinks", "Download blink intervals CSV", class_="btn-success w-100"),
                        ui.download_button("download_processed", "Download processed pupil CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_events", "Download event responses CSV", class_="btn-outline-success w-100 mt-2"),
                    ),
                    ui.card(
                        ui.card_header("Reproducible code"),
                        ui.download_button("download_script", "Download Python script", class_="btn-primary w-100"),
                        ui.output_text_verbatim("script_preview"),
                    ),
                    col_widths=(5, 7),
                ),
            ),
            id="pupil_tabs",
            selected="Overview",
        ),
    )


@module.server
def pupil_server(input, output, session, state, status_text):
    local_status = reactive.Value("Load a dataset with a pupil channel, then run the Guided blink audit.")

    @reactive.effect
    def _sync_choices():
        data = state().data
        pupils = pupil_signal_choices(data)
        selected_pupil = input.pupil_col() if input.pupil_col() in pupils else (pupils[0] if pupils else "")
        validity = pupil_validity_choices(data, selected_pupil or None)
        times = time_column_choices(data)
        groups = analysis_group_column_choices(data)
        trials = trial_column_choices(data)
        onsets = onset_column_choices(data)
        markers = marker_column_choices(data)
        ui.update_select("pupil_col", choices={"": "No pupil channel detected", **{c: c for c in pupils}}, selected=selected_pupil)
        ui.update_select("validity_col", choices={"": "Automatic / none", **{c: c for c in validity}}, selected=validity[0] if validity else "")
        ui.update_select("time_col", choices={"": "No time column detected", **{c: c for c in times}}, selected=times[0] if times else "")
        ui.update_select("group_col", choices={"": "No grouping", **{c: c for c in groups}}, selected=groups[0] if groups else "")
        ui.update_select("trial_col", choices={"": "No trial column", **{c: c for c in trials}}, selected=trials[0] if trials else "")
        ui.update_select("stimulus_onset_col", choices={"": "Not selected", **{c: c for c in onsets}}, selected=onsets[0] if onsets else "")
        ui.update_select("event_onset_col", choices={"": "Not selected", **{c: c for c in onsets}}, selected=onsets[0] if onsets else "")
        ui.update_select("marker_col", choices={"": "Not selected", **{c: c for c in markers}}, selected="")

    def _result():
        return state().analyses.get("pupil")

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a dataset before running Pupil Analysis.")
            return
        if not input.pupil_col() or not input.time_col():
            local_status.set("Select a pupil channel and time column before running Pupil Analysis.")
            return
        guided = input.mode() == "guided"
        parameters = {
            "pupil_col": input.pupil_col(),
            "time_col": input.time_col(),
            "validity_col": input.validity_col() or None,
            "group_col": input.group_col() or None,
            "trial_col": input.trial_col() or None,
            "min_blink_samples": 2 if guided else int(input.min_blink_samples()),
            "interpolate": False if guided else bool(input.interpolate()),
            "interpolation_max_gap_s": 0.25 if guided else float(input.max_gap()),
            "interpolation_method": "linear" if guided else input.interp_method(),
            "smooth": False if guided else bool(input.smooth()),
            "smooth_window": 5 if guided else int(input.smooth_window()),
            "baseline_correct": False if guided else bool(input.baseline_correct()),
            "stimulus_onset_col": None if guided else (input.stimulus_onset_col() or None),
            "baseline_window": (-0.5, -0.1) if guided else (float(input.baseline_start()), float(input.baseline_end())),
            "baseline_function": "median" if guided else input.baseline_function(),
            "correction": "subtract" if guided else input.correction(),
            "summarize_events": False if guided else bool(input.event_summary()),
            "event_onset_col": None if guided else (input.event_onset_col() or None),
            "marker_col": None if guided else (input.marker_col() or None),
            "pre_s": 1.0 if guided else float(input.pre_s()),
            "post_s": 3.0 if guided else float(input.post_s()),
            "response_window": (0.0, 3.0) if guided else (float(input.response_start()), float(input.response_end())),
            "mode": input.mode(),
        }
        try:
            result = run_pupil_analysis(
                current.data,
                pupil_col=parameters["pupil_col"],
                time_col=parameters["time_col"],
                validity_col=parameters["validity_col"],
                group_col=parameters["group_col"],
                trial_col=parameters["trial_col"],
                min_blink_samples=parameters["min_blink_samples"],
                interpolate=parameters["interpolate"],
                interpolation_max_gap_s=parameters["interpolation_max_gap_s"],
                interpolation_method=parameters["interpolation_method"],
                smooth=parameters["smooth"],
                smooth_window=parameters["smooth_window"],
                baseline_correct=parameters["baseline_correct"],
                stimulus_onset_col=parameters["stimulus_onset_col"],
                baseline_window=parameters["baseline_window"],
                baseline_function=parameters["baseline_function"],
                correction=parameters["correction"],
                summarize_events=parameters["summarize_events"],
                event_onset_col=parameters["event_onset_col"],
                marker_col=parameters["marker_col"],
                pre_s=parameters["pre_s"],
                post_s=parameters["post_s"],
                response_window=parameters["response_window"],
            )
            result["parameters"]["mode"] = input.mode()
            state.set(current.with_analysis("pupil", result, parameters=parameters))
            local_status.set("Pupil workflow complete using public gpbiometricspy APIs.")
            status_text.set("Pupil analysis complete. Review blink QC, preprocessing, event-locked summaries, and exports.")
        except Exception as exc:
            local_status.set(f"Pupil analysis failed: {exc}")

    @render.text
    def status():
        return local_status()

    @render.text
    def blink_count():
        result = _result()
        intervals = result.get("blink_intervals") if isinstance(result, dict) else None
        return f"{len(intervals):,}" if isinstance(intervals, pd.DataFrame) else "0"

    @render.text
    def flagged_pct():
        result = _result()
        audit = result.get("blink_audit") if isinstance(result, dict) else None
        summary = audit.get("summary") if isinstance(audit, dict) else None
        if isinstance(summary, pd.DataFrame) and not summary.empty and "prop_flagged" in summary:
            value = pd.to_numeric(summary["prop_flagged"], errors="coerce").mean()
            return f"{100 * value:.1f}%" if pd.notna(value) else "—"
        return "—"

    @render.text
    def interpolated_count():
        result = _result()
        data = result.get("processed_data") if isinstance(result, dict) else None
        if not isinstance(data, pd.DataFrame):
            return "0"
        flags = [c for c in data.columns if c.endswith("_was_interpolated")]
        if not flags:
            return "0"
        count = int(data[flags].fillna(False).astype(bool).any(axis=1).sum())
        return f"{count:,}"

    @render.text
    def event_count():
        result = _result()
        table = result.get("event_summary") if isinstance(result, dict) else None
        return f"{len(table):,}" if isinstance(table, pd.DataFrame) else "0"

    def _table(name: str, fallback: str):
        table = pupil_analysis_tables(_result()).get(name)
        if not isinstance(table, pd.DataFrame) or table.empty:
            table = pd.DataFrame({"status": [fallback]})
        return render.DataGrid(table, filters=True, height="340px")

    @render.data_frame
    def blink_summary():
        return _table("blink_summary", "Run Pupil Analysis to inspect invalid/blink samples.")

    @render.data_frame
    def blink_intervals():
        return _table("blink_intervals", "No blink intervals detected or analysis not run.")

    @render.data_frame
    def smoothing_summary():
        return _table("smoothing_summary", "Smoothing was not requested.")

    @render.data_frame
    def repair_flags():
        return _table("repair_flags", "No interpolation flags are present.")

    @render.data_frame
    def events_table():
        return _table("events", "Event-locked summarization was not requested.")

    @render.data_frame
    def event_summary_table():
        return _table("event_summary", "Event-locked summarization was not requested.")

    @render.plot(alt="Pupil missingness diagnostic")
    def missingness_plot():
        result = _result()
        processed = result.get("processed_data") if isinstance(result, dict) else None
        parameters = result.get("parameters") if isinstance(result, dict) else None
        if not isinstance(processed, pd.DataFrame) or not isinstance(parameters, dict):
            return _placeholder("Run Pupil Analysis to generate the missingness diagnostic.")
        raw = parameters.get("pupil_col")
        analysed = result.get("analysis_pupil_col")
        cols = [c for c in dict.fromkeys([raw, analysed]) if c in processed.columns]
        if not cols:
            return _placeholder("No pupil channel is available for missingness plotting.")
        try:
            return gp.plot_gazepoint_missingness(processed, cols=cols, time_col=parameters.get("time_col"))
        except Exception as exc:
            return _placeholder(f"Missingness plot unavailable: {exc}")

    @render.plot(alt="Raw and processed pupil time series")
    def pupil_trace():
        result = _result()
        processed = result.get("processed_data") if isinstance(result, dict) else None
        parameters = result.get("parameters") if isinstance(result, dict) else None
        if not isinstance(processed, pd.DataFrame) or not isinstance(parameters, dict):
            return _placeholder("Run Pupil Analysis to generate the pupil trace.")
        time_col = parameters.get("time_col")
        raw_col = parameters.get("pupil_col")
        analysis_col = result.get("analysis_pupil_col")
        if time_col not in processed or raw_col not in processed:
            return _placeholder("Selected pupil/time columns are unavailable.")
        n = len(processed)
        index = np.arange(n)
        if n > 6000:
            index = np.unique(np.rint(np.linspace(0, n - 1, 6000)).astype(int))
        x = pd.to_numeric(processed.iloc[index][time_col], errors="coerce")
        raw = pd.to_numeric(processed.iloc[index][raw_col], errors="coerce")
        fig, ax = plt.subplots()
        ax.plot(x, raw, label=f"Raw: {raw_col}", alpha=0.65)
        if analysis_col in processed and analysis_col != raw_col:
            analysed = pd.to_numeric(processed.iloc[index][analysis_col], errors="coerce")
            ax.plot(x, analysed, label=f"Analysis: {analysis_col}")
        ax.set_xlabel(str(time_col))
        ax.set_ylabel("Pupil diameter / exported pupil units")
        ax.legend(loc="best")
        return fig

    @render.text
    def script_preview():
        return pupil_reproducibility_script(_result())

    @render.download(filename="gpbiometricspy_pupil_blink_intervals.csv")
    def download_blinks():
        table = pupil_analysis_tables(_result()).get("blink_intervals", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_pupil_processed.csv")
    def download_processed():
        result = _result()
        table = result.get("processed_data") if isinstance(result, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame()
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_pupil_event_responses.csv")
    def download_events():
        table = pupil_analysis_tables(_result()).get("event_summary", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_pupil_reproduce.py")
    def download_script():
        yield pupil_reproducibility_script(_result())
