from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.gaze_services import (
        analysis_group_column_choices,
        aoi_column_choices,
        gaze_analysis_tables,
        gaze_reproducibility_script,
        gaze_time_choices,
        gaze_trial_choices,
        gaze_validity_choices,
        gaze_x_choices,
        gaze_y_choices,
        load_aoi_definitions,
        run_gaze_analysis,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from gaze_services import (
        analysis_group_column_choices,
        aoi_column_choices,
        gaze_analysis_tables,
        gaze_reproducibility_script,
        gaze_time_choices,
        gaze_trial_choices,
        gaze_validity_choices,
        gaze_x_choices,
        gaze_y_choices,
        load_aoi_definitions,
        run_gaze_analysis,
    )


def _placeholder(message: str):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


def _draw_aoi_rectangles(ax, definitions: pd.DataFrame | None) -> None:
    if not isinstance(definitions, pd.DataFrame) or definitions.empty:
        return
    required = {"aoi", "xmin", "xmax", "ymin", "ymax"}
    if not required.issubset(definitions.columns):
        return
    for _, row in definitions.iterrows():
        rect = Rectangle(
            (float(row.xmin), float(row.ymin)),
            float(row.xmax - row.xmin),
            float(row.ymax - row.ymin),
            fill=False,
            linewidth=1.2,
        )
        ax.add_patch(rect)
        ax.text(float(row.xmin), float(row.ymin), str(row.aoi), fontsize=8, va="bottom")


@module.ui
def gaze_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Gaze / fixation / saccade / AOI controls"),
                ui.input_radio_buttons(
                    "mode",
                    "Workflow mode",
                    choices={"guided": "Guided", "expert": "Expert"},
                    selected="guided",
                    inline=True,
                ),
                ui.layout_columns(
                    ui.input_select("x_col", "Gaze X", choices={"": "No X channel detected"}),
                    ui.input_select("y_col", "Gaze Y", choices={"": "No Y channel detected"}),
                    col_widths=(6, 6),
                ),
                ui.input_select("time_col", "Time column", choices={"": "No time column detected"}),
                ui.input_select("validity_col", "Gaze validity column", choices={"": "Automatic / none"}),
                ui.layout_columns(
                    ui.input_select("group_col", "Participant / grouping", choices={"": "No grouping"}),
                    ui.input_select("trial_col", "Trial / stimulus", choices={"": "No trial grouping"}),
                    col_widths=(6, 6),
                ),
                ui.hr(),
                ui.tags.strong("Coordinate and acquisition settings"),
                ui.input_select(
                    "coordinate_system",
                    "Coordinate system",
                    choices={"auto": "Auto", "normalized": "Normalized (0–1)", "pixels": "Pixels"},
                    selected="auto",
                ),
                ui.layout_columns(
                    ui.input_numeric("screen_width", "Screen width (px)", value=1920, min=1),
                    ui.input_numeric("screen_height", "Screen height (px)", value=1080, min=1),
                    col_widths=(6, 6),
                ),
                ui.input_numeric("sampling_rate", "Expected sampling rate (Hz)", value=60, min=1),
                ui.input_checkbox("filter_screen", "Flag/filter gaze outside screen bounds", value=True),
                ui.hr(),
                ui.tags.strong("Expert event-detection parameters"),
                ui.tags.small(
                    "Guided mode uses package validation plus screen-bound filtering, 100 ms minimum fixation duration, 10 ms minimum saccade duration, a 100 ms maximum event gap, and a coordinate-dependent operational velocity starting point. Confirm event thresholds against the acquisition protocol before inferential use.",
                    class_="text-secondary d-block mb-2",
                ),
                ui.input_checkbox("detect_events", "Detect fixations and saccades", value=True),
                ui.input_numeric("velocity_threshold", "Velocity threshold (coordinate units / s)", value=2.0, min=0.0001, step=0.1),
                ui.layout_columns(
                    ui.input_numeric("min_fixation", "Minimum fixation (ms)", value=100, min=1),
                    ui.input_numeric("min_saccade", "Minimum saccade (ms)", value=10, min=1),
                    col_widths=(6, 6),
                ),
                ui.input_numeric("max_gap", "Maximum event gap (ms)", value=100, min=0),
                ui.input_numeric("scanpath_distance", "Scanpath step threshold", value=0.02, min=0, step=0.01),
                ui.hr(),
                ui.tags.strong("AOI source"),
                ui.input_radio_buttons(
                    "aoi_source",
                    None,
                    choices={"none": "No AOI", "existing": "Existing AOI column", "upload": "Upload rectangular AOIs"},
                    selected="none",
                ),
                ui.input_select("aoi_col", "Existing AOI column", choices={"": "No AOI column selected"}),
                ui.input_file(
                    "aoi_upload",
                    "AOI definition CSV/TXT",
                    accept=[".csv", ".txt", "text/csv", "text/plain"],
                    multiple=False,
                ),
                ui.tags.small(
                    "Uploaded rectangle schema: aoi,xmin,xmax,ymin,ymax with optional priority. Coordinates must match the selected gaze coordinate system.",
                    class_="text-secondary d-block",
                ),
                ui.layout_columns(
                    ui.input_select(
                        "aoi_overlap",
                        "AOI overlap rule",
                        choices={"priority": "Priority / first", "smallest": "Smallest AOI", "all": "Keep all matches", "error": "Error on overlap"},
                        selected="priority",
                    ),
                    ui.input_select(
                        "aoi_boundary",
                        "Boundary points",
                        choices={"inside": "Inside AOI", "outside": "Outside AOI"},
                        selected="inside",
                    ),
                    col_widths=(6, 6),
                ),
                ui.input_task_button(
                    "run",
                    "Run Gaze Analysis",
                    label_busy="Analysing gaze...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Scientific interpretation"),
                ui.p(
                    "Studio delegates gaze validation, gaze filtering, fixation/saccade detection, AOI assignment, fixation summaries, AOI dwell metrics, and scanpath metrics to public gpbiometricspy APIs."
                ),
                ui.p(
                    "Velocity-based event classification depends on sampling rate, coordinate units, calibration quality, smoothing/filtering choices, and the threshold definition. Guided defaults are operational starting points, not universal ground truth.",
                    class_="text-secondary",
                ),
                ui.p(
                    "AOI dwell and transition summaries depend on defensible AOI geometry and stimulus alignment. Overlapping AOIs can materially change assignment and must be handled explicitly.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Gaze position, fixations, saccades and AOI measures describe observable oculomotor behaviour. They do not by themselves establish attention, comprehension, preference, intent, emotion, trust, or diagnosis.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.layout_column_wrap(
            ui.value_box("Gaze validation", ui.output_text("validation_status"), theme="primary"),
            ui.value_box("Usable gaze", ui.output_text("valid_pct")),
            ui.value_box("Fixations", ui.output_text("fixation_count")),
            ui.value_box("Saccades", ui.output_text("saccade_count")),
            ui.value_box("AOI assigned", ui.output_text("aoi_pct")),
            width=1 / 5,
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Overview",
                ui.layout_columns(
                    ui.card(ui.card_header("Gaze validation summary"), ui.output_data_frame("validation_summary"), full_screen=True),
                    ui.card(ui.card_header("Event-detection summary"), ui.output_data_frame("event_summary"), full_screen=True),
                    col_widths=(6, 6),
                ),
                ui.card(ui.card_header("Validation by participant / trial"), ui.output_data_frame("validation_groups"), full_screen=True),
            ),
            ui.nav_panel(
                "Gaze path",
                ui.card(
                    ui.card_header("Gaze trajectory and AOI geometry"),
                    ui.output_plot("gaze_path_plot", height="560px"),
                    full_screen=True,
                ),
                ui.p(
                    "The trajectory is a diagnostic visualization of the processed gaze coordinates. Dense recordings are downsampled for display only; exported analysis tables retain the full workflow output.",
                    class_="text-secondary small",
                ),
            ),
            ui.nav_panel(
                "Fixations & saccades",
                ui.layout_columns(
                    ui.card(ui.card_header("Detected fixations"), ui.output_data_frame("fixations"), full_screen=True),
                    ui.card(ui.card_header("Detected saccades"), ui.output_data_frame("saccades"), full_screen=True),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Fixation summary"), ui.output_data_frame("fixation_summary"), full_screen=True),
                    ui.card(
                        ui.card_header("Saccade main-sequence diagnostic"),
                        ui.output_plot("main_sequence_plot", height="440px"),
                        full_screen=True,
                    ),
                    col_widths=(6, 6),
                ),
            ),
            ui.nav_panel(
                "AOI",
                ui.layout_columns(
                    ui.card(ui.card_header("AOI assignment overview"), ui.output_data_frame("aoi_overview")),
                    ui.card(ui.card_header("AOI definitions"), ui.output_data_frame("aoi_definitions")),
                    col_widths=(5, 7),
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("AOI dwell / entry metrics"), ui.output_data_frame("aoi_dwell"), full_screen=True),
                    ui.card(ui.card_header("Fixations by AOI"), ui.output_data_frame("fixations_by_aoi"), full_screen=True),
                    col_widths=(6, 6),
                ),
                ui.card(ui.card_header("AOI dwell diagnostic"), ui.output_plot("aoi_dwell_plot", height="440px"), full_screen=True),
            ),
            ui.nav_panel(
                "Scanpath",
                ui.card(ui.card_header("Scanpath and transition metrics"), ui.output_data_frame("scanpath"), full_screen=True),
                ui.p(
                    "Scanpath summaries use the package-native path length, step length, saccade-like step count, regression-like count, AOI transition count, and transition entropy contract where the corresponding inputs are available.",
                    class_="text-secondary small",
                ),
            ),
            ui.nav_panel(
                "Export",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Tabular exports"),
                        ui.download_button("download_processed", "Download processed gaze CSV", class_="btn-success w-100"),
                        ui.download_button("download_fixations", "Download fixations CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_saccades", "Download saccades CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_aoi", "Download AOI dwell CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_scanpath", "Download scanpath CSV", class_="btn-outline-success w-100 mt-2"),
                    ),
                    ui.card(
                        ui.card_header("Reproducible code"),
                        ui.download_button("download_script", "Download Python script", class_="btn-primary w-100"),
                        ui.output_text_verbatim("script_preview"),
                    ),
                    col_widths=(5, 7),
                ),
            ),
            id="gaze_tabs",
            selected="Overview",
        ),
    )


@module.server
def gaze_server(input, output, session, state, status_text):
    local_status = reactive.Value("Load a dataset with gaze X/Y channels, then run the Guided workflow.")

    @reactive.effect
    def _sync_choices():
        data = state().data
        xs = gaze_x_choices(data)
        ys = gaze_y_choices(data)
        times = gaze_time_choices(data)
        validity = gaze_validity_choices(data)
        groups = analysis_group_column_choices(data)
        trials = gaze_trial_choices(data)
        aois = aoi_column_choices(data)
        ui.update_select("x_col", choices={"": "No X channel detected", **{c: c for c in xs}}, selected=xs[0] if xs else "")
        ui.update_select("y_col", choices={"": "No Y channel detected", **{c: c for c in ys}}, selected=ys[0] if ys else "")
        ui.update_select("time_col", choices={"": "No time column detected", **{c: c for c in times}}, selected=times[0] if times else "")
        ui.update_select("validity_col", choices={"": "Automatic / none", **{c: c for c in validity}}, selected=validity[0] if validity else "")
        ui.update_select("group_col", choices={"": "No grouping", **{c: c for c in groups}}, selected=groups[0] if groups else "")
        ui.update_select("trial_col", choices={"": "No trial grouping", **{c: c for c in trials}}, selected=trials[0] if trials else "")
        ui.update_select("aoi_col", choices={"": "No AOI column selected", **{c: c for c in aois}}, selected=aois[0] if aois else "")

    def _result():
        return state().analyses.get("gaze")

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a dataset before running gaze analysis.")
            return
        if not input.x_col() or not input.y_col() or not input.time_col():
            local_status.set("Select gaze X, gaze Y, and time columns before running gaze analysis.")
            return
        guided = input.mode() == "guided"
        aoi_definitions = None
        aoi_source_name = None
        existing_aoi_col = None
        try:
            if input.aoi_source() == "existing":
                existing_aoi_col = input.aoi_col() or None
                if not existing_aoi_col:
                    raise ValueError("Choose an existing AOI column or change the AOI source.")
            elif input.aoi_source() == "upload":
                aoi_definitions, aoi_source_name = load_aoi_definitions(input.aoi_upload())

            parameters = {
                "x_col": input.x_col(),
                "y_col": input.y_col(),
                "time_col": input.time_col(),
                "validity_col": input.validity_col() or None,
                "group_col": input.group_col() or None,
                "trial_col": input.trial_col() or None,
                "coordinate_system": input.coordinate_system(),
                "screen_width_px": float(input.screen_width()),
                "screen_height_px": float(input.screen_height()),
                "expected_sampling_rate_hz": float(input.sampling_rate()),
                "missing_threshold": 0.20,
                "filter_to_screen": bool(input.filter_screen()),
                "detect_events": bool(input.detect_events()),
                "velocity_threshold": None if guided else float(input.velocity_threshold()),
                "min_fixation_duration_ms": 100.0 if guided else float(input.min_fixation()),
                "min_saccade_duration_ms": 10.0 if guided else float(input.min_saccade()),
                "max_gap_ms": 100.0 if guided else float(input.max_gap()),
                "existing_aoi_col": existing_aoi_col,
                "aoi_source": input.aoi_source(),
                "aoi_source_name": aoi_source_name,
                "aoi_definition_rows": int(len(aoi_definitions)) if isinstance(aoi_definitions, pd.DataFrame) else 0,
                "aoi_overlap": input.aoi_overlap(),
                "aoi_boundary": input.aoi_boundary(),
                "min_saccade_distance": 0.02 if guided else float(input.scanpath_distance()),
                "mode": input.mode(),
            }
            result = run_gaze_analysis(
                current.data,
                x_col=parameters["x_col"],
                y_col=parameters["y_col"],
                time_col=parameters["time_col"],
                validity_col=parameters["validity_col"],
                group_col=parameters["group_col"],
                trial_col=parameters["trial_col"],
                coordinate_system=parameters["coordinate_system"],
                screen_width_px=parameters["screen_width_px"],
                screen_height_px=parameters["screen_height_px"],
                expected_sampling_rate_hz=parameters["expected_sampling_rate_hz"],
                missing_threshold=parameters["missing_threshold"],
                filter_to_screen=parameters["filter_to_screen"],
                detect_events=parameters["detect_events"],
                velocity_threshold=parameters["velocity_threshold"],
                min_fixation_duration_ms=parameters["min_fixation_duration_ms"],
                min_saccade_duration_ms=parameters["min_saccade_duration_ms"],
                max_gap_ms=parameters["max_gap_ms"],
                existing_aoi_col=parameters["existing_aoi_col"],
                aoi_definitions=aoi_definitions,
                aoi_overlap=parameters["aoi_overlap"],
                aoi_boundary=parameters["aoi_boundary"],
                min_saccade_distance=parameters["min_saccade_distance"],
            )
            result["parameters"]["mode"] = input.mode()
            result["parameters"]["aoi_source"] = input.aoi_source()
            result["parameters"]["aoi_source_name"] = aoi_source_name
            provenance = {**parameters, **{k: result["parameters"].get(k) for k in ["resolved_coordinate_mode", "analysis_x_col", "analysis_y_col", "analysis_aoi_col", "velocity_threshold"]}}
            state.set(current.with_analysis("gaze", result, parameters=provenance))
            local_status.set("Gaze workflow complete using public gpbiometricspy APIs.")
            status_text.set("Gaze analysis complete. Review validation, events, AOIs, scanpaths, and exports.")
        except Exception as exc:
            local_status.set(f"Gaze analysis failed: {exc}")

    @render.text
    def status():
        return local_status()

    @render.text
    def validation_status():
        result = _result()
        validation = result.get("validation") if isinstance(result, dict) else None
        summary = validation.get("summary") if isinstance(validation, dict) else None
        if isinstance(summary, pd.DataFrame) and not summary.empty:
            for column in ["status", "overall_status", "gaze_status"]:
                if column in summary:
                    return str(summary.iloc[0][column])
        return "Complete" if isinstance(validation, dict) else "Not run"

    @render.text
    def valid_pct():
        result = _result()
        data = result.get("processed_data") if isinstance(result, dict) else None
        if not isinstance(data, pd.DataFrame) or data.empty:
            return "—"
        x_col = result.get("analysis_x_col")
        y_col = result.get("analysis_y_col")
        if x_col not in data or y_col not in data:
            return "—"
        x = pd.to_numeric(data[x_col], errors="coerce")
        y = pd.to_numeric(data[y_col], errors="coerce")
        valid = x.notna() & y.notna()
        return f"{100 * float(valid.mean()):.1f}%"

    @render.text
    def fixation_count():
        tables = gaze_analysis_tables(_result())
        table = tables.get("fixations")
        return f"{len(table):,}" if isinstance(table, pd.DataFrame) else "0"

    @render.text
    def saccade_count():
        tables = gaze_analysis_tables(_result())
        table = tables.get("saccades")
        return f"{len(table):,}" if isinstance(table, pd.DataFrame) else "0"

    @render.text
    def aoi_pct():
        result = _result()
        data = result.get("processed_data") if isinstance(result, dict) else None
        aoi_col = result.get("analysis_aoi_col") if isinstance(result, dict) else None
        if not isinstance(data, pd.DataFrame) or not aoi_col or aoi_col not in data or data.empty:
            return "—"
        assigned = data[aoi_col].notna() & data[aoi_col].astype("string").fillna("").ne("")
        return f"{100 * float(assigned.mean()):.1f}%"

    def _table(name: str, fallback: str):
        table = gaze_analysis_tables(_result()).get(name)
        if not isinstance(table, pd.DataFrame) or table.empty:
            table = pd.DataFrame({"status": [fallback]})
        return render.DataGrid(table, filters=True, height="340px")

    @render.data_frame
    def validation_summary():
        return _table("validation_summary", "Run gaze analysis to inspect validation results.")

    @render.data_frame
    def validation_groups():
        return _table("validation_groups", "No grouped validation table is available.")

    @render.data_frame
    def event_summary():
        return _table("event_summary", "Fixation/saccade detection was not run or produced no grouped summary.")

    @render.data_frame
    def fixations():
        return _table("fixations", "No fixations were detected or event detection was disabled.")

    @render.data_frame
    def saccades():
        return _table("saccades", "No saccades were detected or event detection was disabled.")

    @render.data_frame
    def fixation_summary():
        return _table("fixation_summary", "No fixation summary is available.")

    @render.data_frame
    def aoi_overview():
        return _table("aoi_assignment_overview", "AOI assignment from uploaded definitions was not requested.")

    @render.data_frame
    def aoi_definitions():
        return _table("aoi_definitions", "No uploaded AOI definitions are active.")

    @render.data_frame
    def aoi_dwell():
        return _table("aoi_dwell", "No AOI dwell summary is available.")

    @render.data_frame
    def fixations_by_aoi():
        return _table("fixations_by_aoi", "Fixation-by-AOI summaries require uploaded AOI definitions and detected fixations.")

    @render.data_frame
    def scanpath():
        return _table("scanpath", "Run gaze analysis to calculate scanpath metrics.")

    @render.plot(alt="Gaze trajectory with optional AOI rectangles")
    def gaze_path_plot():
        result = _result()
        data = result.get("processed_data") if isinstance(result, dict) else None
        if not isinstance(data, pd.DataFrame) or data.empty:
            return _placeholder("Run gaze analysis to generate the trajectory diagnostic.")
        x_col = result.get("analysis_x_col")
        y_col = result.get("analysis_y_col")
        if x_col not in data or y_col not in data:
            return _placeholder("Processed gaze coordinates are unavailable.")
        index = np.arange(len(data))
        if len(index) > 5000:
            index = np.unique(np.rint(np.linspace(0, len(data) - 1, 5000)).astype(int))
        x = pd.to_numeric(data.iloc[index][x_col], errors="coerce").to_numpy(float)
        y = pd.to_numeric(data.iloc[index][y_col], errors="coerce").to_numpy(float)
        ok = np.isfinite(x) & np.isfinite(y)
        fig, ax = plt.subplots()
        if ok.any():
            ax.plot(x[ok], y[ok], linewidth=0.7, alpha=0.5)
            ax.scatter(x[ok], y[ok], s=7, alpha=0.45)
        _draw_aoi_rectangles(ax, result.get("aoi_definitions"))
        ax.set_xlabel(str(x_col))
        ax.set_ylabel(str(y_col))
        ax.set_title("Processed gaze trajectory")
        ax.invert_yaxis()
        return fig

    @render.plot(alt="Saccade amplitude and peak velocity main sequence")
    def main_sequence_plot():
        table = gaze_analysis_tables(_result()).get("saccades")
        if not isinstance(table, pd.DataFrame) or table.empty:
            return _placeholder("No detected saccades are available for the main-sequence diagnostic.")
        try:
            return gp.plot_gazepoint_saccade_main_sequence(table)
        except Exception as exc:
            return _placeholder(f"Main-sequence plot unavailable: {exc}")

    @render.plot(alt="AOI dwell-time diagnostic")
    def aoi_dwell_plot():
        table = gaze_analysis_tables(_result()).get("aoi_dwell")
        if not isinstance(table, pd.DataFrame) or table.empty or "AOI" not in table or "dwell_time_s" not in table:
            return _placeholder("No AOI dwell summary is available for plotting.")
        work = table.copy()
        work["dwell_time_s"] = pd.to_numeric(work["dwell_time_s"], errors="coerce")
        summary = work.groupby("AOI", dropna=False)["dwell_time_s"].sum(min_count=1).sort_values(ascending=False)
        fig, ax = plt.subplots()
        ax.bar(summary.index.astype(str), summary.to_numpy(float))
        ax.set_ylabel("Dwell time (s)")
        ax.set_xlabel("AOI")
        ax.tick_params(axis="x", labelrotation=45)
        fig.tight_layout()
        return fig

    @render.text
    def script_preview():
        return gaze_reproducibility_script(_result())

    @render.download(filename="gpbiometricspy_gaze_processed.csv")
    def download_processed():
        result = _result()
        table = result.get("processed_data") if isinstance(result, dict) else None
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame()
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_gaze_fixations.csv")
    def download_fixations():
        table = gaze_analysis_tables(_result()).get("fixations", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_gaze_saccades.csv")
    def download_saccades():
        table = gaze_analysis_tables(_result()).get("saccades", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_gaze_aoi_dwell.csv")
    def download_aoi():
        table = gaze_analysis_tables(_result()).get("aoi_dwell", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_gaze_scanpath.csv")
    def download_scanpath():
        table = gaze_analysis_tables(_result()).get("scanpath", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download(filename="gpbiometricspy_gaze_reproduce.py")
    def download_script():
        yield gaze_reproducibility_script(_result())
