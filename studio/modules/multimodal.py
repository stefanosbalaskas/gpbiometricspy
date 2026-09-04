from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.multimodal_services import (
        event_alignment_available,
        multimodal_group_choices,
        multimodal_reproducibility_script,
        multimodal_signal_choices,
        multimodal_tables,
        multimodal_time_choices,
        multimodal_trial_choices,
        run_multimodal_analysis,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from multimodal_services import (
        event_alignment_available,
        multimodal_group_choices,
        multimodal_reproducibility_script,
        multimodal_signal_choices,
        multimodal_tables,
        multimodal_time_choices,
        multimodal_trial_choices,
        run_multimodal_analysis,
    )


def _placeholder(message: str):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center", wrap=True)
    ax.set_axis_off()
    return fig


def _grid(table: pd.DataFrame | None, message: str, *, height: str = "360px"):
    if not isinstance(table, pd.DataFrame) or table.empty:
        table = pd.DataFrame({"status": [message]})
    return render.DataGrid(table, filters=True, height=height)


@module.ui
def multimodal_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Multimodal controls"),
                ui.input_radio_buttons(
                    "mode",
                    "Workflow mode",
                    choices={"guided": "Guided", "expert": "Expert"},
                    selected="guided",
                    inline=True,
                ),
                ui.tags.strong("Event infrastructure"),
                ui.tags.small(ui.output_text("event_status"), class_="text-secondary d-block mb-2"),
                ui.input_select("time_col", "Reference time column", choices={"": "No time column detected"}),
                ui.layout_columns(
                    ui.input_select("group_col", "Participant / grouping", choices={"": "No grouping"}),
                    ui.input_select("trial_col", "Trial / stimulus", choices={"": "No trial grouping"}),
                    col_widths=(6, 6),
                ),
                ui.input_checkbox(
                    "prefer_processed",
                    "Prefer prior processed Studio analyses when available",
                    value=True,
                ),
                ui.hr(),
                ui.tags.strong("Signals"),
                ui.input_select("eda_col", "EDA / SCR signal", choices={"": "None"}),
                ui.input_select("cardiac_col", "Cardiac signal", choices={"": "None"}),
                ui.input_select("pupil_col", "Pupil signal", choices={"": "None"}),
                ui.layout_columns(
                    ui.input_select("gaze_x_col", "Gaze X", choices={"": "None"}),
                    ui.input_select("gaze_y_col", "Gaze Y", choices={"": "None"}),
                    col_widths=(6, 6),
                ),
                ui.input_select("aoi_col", "AOI column", choices={"": "No AOI integration"}),
                ui.hr(),
                ui.tags.strong("Expert event-locked windows"),
                ui.layout_columns(
                    ui.input_numeric("pre_s", "Pre-event (s)", value=1.0, min=0, step=0.1),
                    ui.input_numeric("post_s", "Post-event (s)", value=3.0, min=0.1, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.input_numeric("baseline_start", "Baseline start (s)", value=-1.0, step=0.1),
                    ui.input_numeric("baseline_end", "Baseline end (s)", value=0.0, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.input_numeric("summary_start", "Summary start (s)", value=0.0, step=0.1),
                    ui.input_numeric("summary_end", "Summary end (s)", value=3.0, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.input_checkbox("standardise_timeline", "Standardise signals in timeline plot", value=True),
                ui.input_task_button(
                    "run",
                    "Run Multimodal Analysis",
                    label_busy="Combining modalities...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Scientific interpretation"),
                ui.p(
                    "Multimodal Analysis consumes the standardized event table produced by Events & Alignment. Event-locked extraction, baseline/summary metrics, grouped biometric windows, model-ready tables, AOI-linked biometric summaries, and the multimodal timeline delegate to public gpbiometricspy APIs."
                ),
                ui.p(
                    "Prior processed EDA, pupil, and gaze outputs are reused when requested and compatible. Studio reports the resolved source for every modality so preprocessing is not hidden.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Different modalities have different response dynamics, sampling properties, artifacts, and valid inferential windows. A shared event clock makes comparison possible; it does not make the measures physiologically equivalent.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Cross-modal co-occurrence or correlated change does not by itself establish a latent psychological state. Gaze, pupil, EDA, cardiac, and AOI measures remain measurement channels that require design-specific interpretation.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.layout_column_wrap(
            ui.value_box("Events", ui.output_text("event_count"), theme="primary"),
            ui.value_box("Modalities", ui.output_text("modality_count")),
            ui.value_box("Event-locked samples", ui.output_text("sample_count")),
            ui.value_box("Response rows", ui.output_text("summary_count")),
            ui.value_box("AOI summary rows", ui.output_text("aoi_count")),
            width=1 / 5,
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Overview",
                ui.layout_columns(
                    ui.card(ui.card_header("Resolved modality sources"), ui.output_data_frame("stream_sources"), full_screen=True),
                    ui.card(ui.card_header("Event-locked response summary"), ui.output_data_frame("response_summary"), full_screen=True),
                    col_widths=(5, 7),
                ),
                ui.card(ui.card_header("Event × modality response matrix"), ui.output_data_frame("response_matrix"), full_screen=True),
            ),
            ui.nav_panel(
                "Event-locked",
                ui.card(
                    ui.card_header("Event-relative multimodal traces"),
                    ui.output_plot("eventlocked_plot", height="560px"),
                    full_screen=True,
                ),
                ui.card(ui.card_header("Event-locked samples"), ui.output_data_frame("eventlocked_samples"), full_screen=True),
            ),
            ui.nav_panel(
                "Timeline",
                ui.card(
                    ui.card_header("Package-native multimodal timeline"),
                    ui.output_plot("timeline_plot", height="640px"),
                    full_screen=True,
                ),
                ui.p(
                    "The underlying signal timeline is produced by plot_gazepoint_multimodal_timeline(); standardized event times are overlaid as timing references.",
                    class_="text-secondary small",
                ),
            ),
            ui.nav_panel(
                "AOI integration",
                ui.layout_columns(
                    ui.card(ui.card_header("AOI-linked biometric summary"), ui.output_data_frame("aoi_summary"), full_screen=True),
                    ui.card(ui.card_header("AOI biometric diagnostic"), ui.output_plot("aoi_plot", height="460px"), full_screen=True),
                    col_widths=(7, 5),
                ),
            ),
            ui.nav_panel(
                "Participant / trial",
                ui.layout_columns(
                    ui.card(ui.card_header("Multimodal window summaries"), ui.output_data_frame("window_summary"), full_screen=True),
                    ui.card(ui.card_header("Model-ready multimodal table"), ui.output_data_frame("model_data"), full_screen=True),
                    col_widths=(6, 6),
                ),
            ),
            ui.nav_panel(
                "Export",
                ui.layout_column_wrap(
                    ui.download_button("download_response", "Event response CSV"),
                    ui.download_button("download_samples", "Event samples CSV"),
                    ui.download_button("download_matrix", "Response matrix CSV"),
                    ui.download_button("download_windows", "Participant/trial windows CSV"),
                    ui.download_button("download_model", "Model-ready table CSV"),
                    ui.download_button("download_aoi", "AOI biometric summary CSV"),
                    ui.download_button("download_script", "Python reproduction script"),
                    width=1 / 3,
                ),
                ui.output_text_verbatim("parameters"),
            ),
        ),
    )


@module.server
def multimodal_server(input, output, session, state, global_status):
    local_status = reactive.Value("Ready. Run Events & Alignment first, then choose multimodal signals.")

    @reactive.effect
    def _sync_choices():
        current = state()
        data = current.data
        analyses = current.analyses
        times = multimodal_time_choices(data)
        groups = multimodal_group_choices(data)
        trials = multimodal_trial_choices(data)
        choices = multimodal_signal_choices(data, analyses, prefer_processed=True)
        ui.update_select("time_col", choices=times or {"": "No time column detected"}, selected=times[0] if times else "")
        ui.update_select("group_col", choices={"": "No grouping", **{c: c for c in groups}}, selected=groups[0] if groups else "")
        ui.update_select("trial_col", choices={"": "No trial grouping", **{c: c for c in trials}}, selected=trials[0] if trials else "")
        for input_id, key in [
            ("eda_col", "eda"),
            ("cardiac_col", "cardiac"),
            ("pupil_col", "pupil"),
            ("gaze_x_col", "gaze_x"),
            ("gaze_y_col", "gaze_y"),
            ("aoi_col", "aoi"),
        ]:
            vals = choices[key]
            ui.update_select(
                input_id,
                choices={"": "None", **{c: c for c in vals}},
                selected=vals[0] if vals else "",
            )

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a dataset before running Multimodal Analysis.")
            return
        if not event_alignment_available(current.analyses):
            local_status.set("Run Events & Alignment first; no standardized event table is available.")
            global_status.set("Multimodal Analysis requires a completed Events & Alignment workflow.")
            return
        try:
            expert = input.mode() == "expert"
            pre_s = float(input.pre_s()) if expert else 1.0
            post_s = float(input.post_s()) if expert else 3.0
            baseline = (
                float(input.baseline_start()),
                float(input.baseline_end()),
            ) if expert else (-1.0, 0.0)
            summary = (
                float(input.summary_start()),
                float(input.summary_end()),
            ) if expert else (0.0, 3.0)
            prefer_processed = bool(input.prefer_processed()) if expert else True
            standardise = bool(input.standardise_timeline()) if expert else True
            result = run_multimodal_analysis(
                current.data,
                current.analyses,
                time_col=input.time_col(),
                group_col=input.group_col() or None,
                trial_col=input.trial_col() or None,
                eda_col=input.eda_col() or None,
                cardiac_col=input.cardiac_col() or None,
                pupil_col=input.pupil_col() or None,
                gaze_x_col=input.gaze_x_col() or None,
                gaze_y_col=input.gaze_y_col() or None,
                aoi_col=input.aoi_col() or None,
                pre_s=pre_s,
                post_s=post_s,
                baseline_window_s=baseline,
                summary_window_s=summary,
                prefer_processed=prefer_processed,
                standardise_timeline=standardise,
            )
            state.set(current.with_analysis("multimodal", result, parameters=result.get("parameters")))
            summary_rows = len(result.get("eventlocked", {}).get("summary", []))
            local_status.set(f"Multimodal Analysis complete: {summary_rows:,} event-response rows.")
            global_status.set("Multimodal Analysis complete. Review modality sources and timing assumptions before interpretation.")
        except Exception as exc:
            local_status.set(f"Multimodal Analysis failed: {exc}")
            global_status.set(f"Multimodal Analysis failed: {exc}")

    @reactive.calc
    def _result():
        return state().analyses.get("multimodal") if state().analyses else None

    @reactive.calc
    def _tables():
        return multimodal_tables(_result())

    @render.text
    def event_status():
        current = state()
        if current.data is None:
            return "No dataset loaded."
        if event_alignment_available(current.analyses):
            result = current.analyses.get("event_alignment")
            return f"Events & Alignment ready: {len(result.get('events', [])):,} standardized events available."
        return "Events & Alignment has not been run for the current dataset."

    @render.text
    def status():
        return local_status()

    @render.text
    def event_count():
        result = _result()
        return "0" if not result else f"{len(result.get('events', [])):,}"

    @render.text
    def modality_count():
        result = _result()
        if not result:
            return "0"
        sources = result.get("stream_sources")
        return str(len(sources)) if isinstance(sources, pd.DataFrame) else "0"

    @render.text
    def sample_count():
        result = _result()
        samples = result.get("eventlocked", {}).get("samples") if result else None
        return f"{len(samples):,}" if isinstance(samples, pd.DataFrame) else "0"

    @render.text
    def summary_count():
        result = _result()
        summary = result.get("eventlocked", {}).get("summary") if result else None
        return f"{len(summary):,}" if isinstance(summary, pd.DataFrame) else "0"

    @render.text
    def aoi_count():
        table = _tables().get("aoi_summary")
        return f"{len(table):,}" if isinstance(table, pd.DataFrame) else "0"

    @render.data_frame
    def stream_sources():
        return _grid(_tables().get("stream_sources"), "Run Multimodal Analysis to resolve modality sources.")

    @render.data_frame
    def response_summary():
        return _grid(_tables().get("eventlocked_summary"), "No event-locked response summary is available.", height="430px")

    @render.data_frame
    def response_matrix():
        return _grid(_tables().get("response_matrix"), "No response matrix is available.")

    @render.data_frame
    def eventlocked_samples():
        return _grid(_tables().get("eventlocked_samples"), "No event-locked samples are available.", height="460px")

    @render.data_frame
    def aoi_summary():
        tables = _tables()
        table = tables.get("aoi_summary")
        if not isinstance(table, pd.DataFrame) or table.empty:
            table = tables.get("aoi_signal_summary")
        return _grid(table, "Select an AOI column and run the workflow to create AOI-linked biometric summaries.")

    @render.data_frame
    def window_summary():
        return _grid(_tables().get("multimodal_windows"), "Select participant/trial grouping to create grouped multimodal windows.")

    @render.data_frame
    def model_data():
        return _grid(_tables().get("model_data"), "Select participant/trial grouping to create a model-ready multimodal table.")

    @render.plot(alt="Event-relative multimodal traces")
    def eventlocked_plot():
        samples = _tables().get("eventlocked_samples")
        if not isinstance(samples, pd.DataFrame) or samples.empty:
            return _placeholder("Run Multimodal Analysis to display event-relative traces.")
        required = {"relative_time_s", "value", "event_id", "modality", "signal"}
        if not required.issubset(samples.columns):
            return _placeholder("Event-locked sample table does not contain the expected plotting columns.")
        fig, ax = plt.subplots()
        work = samples.dropna(subset=["relative_time_s", "value"]).copy()
        for _, frame in work.groupby(["modality", "signal", "event_id"], sort=False):
            frame = frame.sort_values("relative_time_s")
            ax.plot(frame["relative_time_s"], frame["value"], alpha=0.18, linewidth=0.8)
        ax.axvline(0, linestyle="--", linewidth=1)
        ax.set_xlabel("Time relative to event (s)")
        ax.set_ylabel("Measured value")
        ax.set_title("Event-relative multimodal traces (individual events)")
        return fig

    @render.plot(alt="Package-native multimodal signal timeline with standardized event markers")
    def timeline_plot():
        result = _result()
        if not result:
            return _placeholder("Run Multimodal Analysis to display the synchronized timeline.")
        data = result.get("timeline_data")
        signals = result.get("timeline_signal_cols") or []
        p = result.get("parameters") or {}
        if not isinstance(data, pd.DataFrame) or not signals:
            return _placeholder("No compatible timeline signals are available.")
        groups = [c for c in [p.get("group_col"), p.get("trial_col")] if c and c in data.columns]
        fig = gp.plot_gazepoint_multimodal_timeline(
            data,
            time_col=p.get("time_col"),
            signal_cols=signals,
            group_cols=groups or None,
            standardise=bool(p.get("standardise_timeline", True)),
            show_event_markers=False,
            title="gpbiometricspy Studio multimodal timeline",
        )
        events = result.get("events")
        if isinstance(events, pd.DataFrame) and "event_time" in events.columns:
            event_times = pd.to_numeric(events["event_time"], errors="coerce").dropna().unique()
            for axis in fig.axes:
                for event_time in event_times[:100]:
                    axis.axvline(float(event_time), linestyle=":", linewidth=0.6, alpha=0.35)
        return fig

    @render.plot(alt="AOI-linked biometric summary plot")
    def aoi_plot():
        result = _result()
        aoi = result.get("aoi_biometrics") if result else None
        if not isinstance(aoi, dict):
            return _placeholder("Select an AOI column and run Multimodal Analysis to display AOI-linked biometrics.")
        summary = aoi.get("summary")
        if not isinstance(summary, pd.DataFrame) or summary.empty:
            return _placeholder("No AOI-linked biometric summary rows are available.")
        try:
            return gp.plot_gazepoint_aoi_biometrics(summary)
        except (TypeError, ValueError) as exc:
            return _placeholder(f"AOI plot unavailable for this summary: {exc}")

    @render.text
    def parameters():
        result = _result()
        if not result:
            return "Run Multimodal Analysis to record parameters."
        p = result.get("parameters") or {}
        return "\n".join(f"{key}: {value}" for key, value in p.items())

    @render.download_button(filename="gpbiometricspy_multimodal_event_responses.csv")
    def download_response():
        table = _tables().get("eventlocked_summary")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_multimodal_event_samples.csv")
    def download_samples():
        table = _tables().get("eventlocked_samples")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_multimodal_response_matrix.csv")
    def download_matrix():
        table = _tables().get("response_matrix")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_multimodal_windows.csv")
    def download_windows():
        table = _tables().get("multimodal_windows")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_multimodal_model_data.csv")
    def download_model():
        table = _tables().get("model_data")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_multimodal_aoi_biometrics.csv")
    def download_aoi():
        table = _tables().get("aoi_summary")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_multimodal_reproduce.py")
    def download_script():
        yield multimodal_reproducibility_script(_result())
