from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shiny import module, reactive, render, ui

try:
    from studio.event_alignment_services import (
        event_alignment_reproducibility_script,
        event_alignment_tables,
        event_group_choices,
        event_time_choices,
        load_event_log,
        load_target_stream,
        run_event_alignment,
        summary_signal_choices,
        ttl_column_choices,
        ttl_validity_choices,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from event_alignment_services import (
        event_alignment_reproducibility_script,
        event_alignment_tables,
        event_group_choices,
        event_time_choices,
        load_event_log,
        load_target_stream,
        run_event_alignment,
        summary_signal_choices,
        ttl_column_choices,
        ttl_validity_choices,
    )


def _placeholder(message: str):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


@module.ui
def event_alignment_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Events & alignment controls"),
                ui.input_radio_buttons(
                    "mode",
                    "Workflow mode",
                    choices={"guided": "Guided", "expert": "Expert"},
                    selected="guided",
                    inline=True,
                ),
                ui.input_radio_buttons(
                    "source_mode",
                    "Reference event source",
                    choices={"ttl": "TTL / marker column", "event_log": "External event log"},
                    selected="ttl",
                ),
                ui.input_select("time_col", "Reference time column", choices={"": "No time column detected"}),
                ui.layout_columns(
                    ui.input_select("ttl_col", "Reference TTL / marker", choices={"": "No TTL/marker detected"}),
                    ui.input_select("validity_col", "TTL validity", choices={"": "None / not available"}),
                    col_widths=(6, 6),
                ),
                ui.input_select("group_col", "Participant / grouping", choices={"": "No grouping"}),
                ui.input_file(
                    "event_upload",
                    "External event log CSV/TXT/TSV",
                    accept=[".csv", ".txt", ".tsv", "text/csv", "text/plain"],
                    multiple=False,
                ),
                ui.tags.small(
                    "Event logs should contain a recognizable event time column such as event_time, onset, time_s, time, or timestamp. Optional event_id/trial and event_label/condition columns are standardized through gpbiometricspy.",
                    class_="text-secondary d-block mb-2",
                ),
                ui.hr(),
                ui.tags.strong("Event windows"),
                ui.layout_columns(
                    ui.input_numeric("pre_s", "Pre-event window (s)", value=1.0, min=0, step=0.1),
                    ui.input_numeric("post_s", "Post-event window (s)", value=5.0, min=0.1, step=0.1),
                    col_widths=(6, 6),
                ),
                ui.input_select("summary_col", "Primary summary/plot signal", choices={"": "Automatic / none"}),
                ui.tags.strong("Expert TTL settings"),
                ui.layout_columns(
                    ui.input_select(
                        "extraction_mode",
                        "TTL extraction audit",
                        choices={"changes": "Value changes", "nonzero": "Non-zero rows"},
                        selected="changes",
                    ),
                    ui.input_select(
                        "event_edge",
                        "Alignment event edge",
                        choices={"rising": "Rising edge", "change": "Any change", "active": "Every active sample"},
                        selected="rising",
                    ),
                    col_widths=(6, 6),
                ),
                ui.input_numeric("collapse_ms", "Collapse nearby events (ms)", value=0, min=0, step=10),
                ui.hr(),
                ui.tags.strong("Optional second stream"),
                ui.input_checkbox("use_target", "Align a second Gazepoint stream by shared event anchors", value=False),
                ui.input_file(
                    "target_upload",
                    "Target stream CSV/TXT/TSV",
                    accept=[".csv", ".txt", ".tsv", "text/csv", "text/plain"],
                    multiple=False,
                ),
                ui.input_action_button("load_target", "Load target stream", class_="btn-outline-primary w-100"),
                ui.tags.small(ui.output_text("target_status"), class_="text-secondary d-block mt-1"),
                ui.layout_columns(
                    ui.input_select("target_time_col", "Target time", choices={"": "Load target first"}),
                    ui.input_select("target_ttl_col", "Target TTL / marker", choices={"": "Load target first"}),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.input_select("target_validity_col", "Target TTL validity", choices={"": "None"}),
                    ui.input_select("target_group_col", "Target grouping", choices={"": "No grouping"}),
                    col_widths=(6, 6),
                ),
                ui.input_select(
                    "stream_method",
                    "Cross-stream clock model",
                    choices={"linear": "Linear offset + drift", "offset": "Constant offset only"},
                    selected="linear",
                ),
                ui.input_task_button(
                    "run",
                    "Run Events & Alignment",
                    label_busy="Aligning events...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Scientific interpretation"),
                ui.p(
                    "The Studio workflow treats event timing as measurement infrastructure. TTL extraction, event-window matching, event-anchor clock fitting, and drift diagnostics are delegated to public gpbiometricspy APIs."
                ),
                ui.p(
                    "Guided mode uses a rising-edge TTL alignment, 1 s pre-event and 5 s post-event windows, and no nearby-event collapse. Expert mode exposes edge rules, extraction audit mode, collapse interval, and linear-versus-offset clock alignment.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Clock correction should be justified by shared anchors. A linear fit can estimate gradual relative clock drift, but sparse, misordered, duplicated, or semantically mismatched events can produce misleading alignment.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Event-locked windows quantify measurements relative to recorded event times; they do not establish causal responses or validate the semantic meaning of a marker without an appropriate experimental design.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.layout_column_wrap(
            ui.value_box("Reference events", ui.output_text("event_count"), theme="primary"),
            ui.value_box("Window rows", ui.output_text("window_count")),
            ui.value_box("Matched stream anchors", ui.output_text("pair_count")),
            ui.value_box("Median raw lag", ui.output_text("median_lag")),
            ui.value_box("Drift slope", ui.output_text("drift_slope")),
            width=1 / 5,
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Events",
                ui.layout_columns(
                    ui.card(ui.card_header("Standardized reference events"), ui.output_data_frame("events"), full_screen=True),
                    ui.card(ui.card_header("TTL extraction audit"), ui.output_data_frame("ttl_events"), full_screen=True),
                    col_widths=(7, 5),
                ),
            ),
            ui.nav_panel(
                "Event windows",
                ui.layout_columns(
                    ui.card(ui.card_header("Event-level summary"), ui.output_data_frame("event_summary"), full_screen=True),
                    ui.card(ui.card_header("Event-locked diagnostic"), ui.output_plot("event_plot", height="420px"), full_screen=True),
                    col_widths=(7, 5),
                ),
                ui.card(ui.card_header("Sample-level matched windows"), ui.output_data_frame("event_windows"), full_screen=True),
            ),
            ui.nav_panel(
                "TTL alignment",
                ui.layout_columns(
                    ui.card(ui.card_header("TTL alignment overview"), ui.output_data_frame("ttl_overview"), full_screen=True),
                    ui.card(ui.card_header("TTL-aligned events"), ui.output_data_frame("ttl_alignment_events"), full_screen=True),
                    col_widths=(5, 7),
                ),
            ),
            ui.nav_panel(
                "Cross-stream alignment",
                ui.layout_columns(
                    ui.card(ui.card_header("Clock-model diagnostics"), ui.output_data_frame("stream_diagnostics"), full_screen=True),
                    ui.card(ui.card_header("Anchor alignment table"), ui.output_data_frame("alignment_table"), full_screen=True),
                    col_widths=(5, 7),
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Lag/drift summary"), ui.output_data_frame("drift_summary"), full_screen=True),
                    ui.card(ui.card_header("Lag across event anchors"), ui.output_plot("drift_plot", height="420px"), full_screen=True),
                    col_widths=(5, 7),
                ),
            ),
            ui.nav_panel(
                "Export",
                ui.layout_column_wrap(
                    ui.download_button("download_events", "Reference events CSV"),
                    ui.download_button("download_windows", "Event windows CSV"),
                    ui.download_button("download_summary", "Event summary CSV"),
                    ui.download_button("download_aligned_target", "Aligned target CSV"),
                    ui.download_button("download_lag", "Lag table CSV"),
                    ui.download_button("download_script", "Python reproduction script"),
                    width=1 / 3,
                ),
                ui.output_text_verbatim("parameters"),
            ),
        ),
    )


@module.server
def event_alignment_server(input, output, session, state, global_status):
    target_stream = reactive.Value(None)
    target_name = reactive.Value("No target stream loaded")
    local_status = reactive.Value("Ready. Choose a reference event source and run the workflow.")

    @reactive.effect
    def _sync_reference_choices():
        data = state().data
        times = event_time_choices(data)
        ttls = ttl_column_choices(data)
        validity = ttl_validity_choices(data)
        groups = event_group_choices(data)
        signals = summary_signal_choices(data)
        ui.update_select("time_col", choices=times or {"": "No time column detected"}, selected=times[0] if times else "")
        ui.update_select("ttl_col", choices=ttls or {"": "No TTL/marker detected"}, selected=ttls[0] if ttls else "")
        ui.update_select("validity_col", choices={"": "None / not available", **{c: c for c in validity}}, selected=validity[0] if validity else "")
        ui.update_select("group_col", choices={"": "No grouping", **{c: c for c in groups}}, selected=groups[0] if groups else "")
        ui.update_select("summary_col", choices={"": "Automatic / none", **{c: c for c in signals}}, selected=signals[0] if signals else "")

    @reactive.effect
    @reactive.event(input.load_target)
    def _load_target():
        try:
            data, name = load_target_stream(input.target_upload())
            target_stream.set(data)
            target_name.set(name)
            times = event_time_choices(data)
            ttls = ttl_column_choices(data)
            validity = ttl_validity_choices(data)
            groups = event_group_choices(data)
            ui.update_select("target_time_col", choices=times or {"": "No time column detected"}, selected=times[0] if times else "")
            ui.update_select("target_ttl_col", choices=ttls or {"": "No TTL/marker detected"}, selected=ttls[0] if ttls else "")
            ui.update_select("target_validity_col", choices={"": "None", **{c: c for c in validity}}, selected=validity[0] if validity else "")
            ui.update_select("target_group_col", choices={"": "No grouping", **{c: c for c in groups}}, selected=groups[0] if groups else "")
            local_status.set(f"Target stream loaded: {name} ({len(data):,} rows).")
        except Exception as exc:
            target_stream.set(None)
            target_name.set("No target stream loaded")
            local_status.set(f"Target load failed: {exc}")

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a reference dataset before running event alignment.")
            return
        try:
            external = None
            if input.source_mode() == "event_log":
                external, _ = load_event_log(input.event_upload())
            expert = input.mode() == "expert"
            pre_s = float(input.pre_s()) if expert else 1.0
            post_s = float(input.post_s()) if expert else 5.0
            extraction_mode = input.extraction_mode() if expert else "changes"
            event_edge = input.event_edge() if expert else "rising"
            collapse = float(input.collapse_ms()) if expert else 0.0
            method = input.stream_method() if expert else "linear"
            summary_col = input.summary_col() or None
            use_target = bool(input.use_target())
            target = target_stream() if use_target else None
            result = run_event_alignment(
                current.data,
                source_mode=input.source_mode(),
                time_col=input.time_col(),
                ttl_col=input.ttl_col() or None,
                validity_col=input.validity_col() or None,
                group_col=input.group_col() or None,
                external_events=external,
                extraction_mode=extraction_mode,
                event_edge=event_edge,
                pre_s=pre_s,
                post_s=post_s,
                collapse_nearby_ms=collapse,
                summary_cols=[summary_col] if summary_col else None,
                target_stream=target,
                target_time_col=(input.target_time_col() or None) if use_target else None,
                target_ttl_col=(input.target_ttl_col() or None) if use_target else None,
                target_validity_col=(input.target_validity_col() or None) if use_target else None,
                target_group_col=(input.target_group_col() or None) if use_target else None,
                stream_method=method,
            )
            state.set(current.with_analysis("event_alignment", result, parameters=result.get("parameters")))
            n_events = len(result.get("events", []))
            local_status.set(f"Events & alignment complete: {n_events} reference events available.")
            global_status.set("Events & alignment analysis complete. Review timing diagnostics before downstream multimodal analysis.")
        except Exception as exc:
            local_status.set(f"Events & alignment failed: {exc}")
            global_status.set(f"Events & alignment failed: {exc}")

    @reactive.calc
    def _result():
        return state().analyses.get("event_alignment") if state().analyses else None

    @reactive.calc
    def _tables():
        return event_alignment_tables(_result())

    @render.text
    def status():
        return local_status()

    @render.text
    def target_status():
        return target_name()

    @render.text
    def event_count():
        result = _result()
        return "0" if not result else f"{len(result.get('events', [])):,}"

    @render.text
    def window_count():
        result = _result()
        return "0" if not result else f"{len(result.get('event_windows', [])):,}"

    @render.text
    def pair_count():
        result = _result()
        if not result or not isinstance(result.get("stream_alignment"), dict):
            return "—"
        diag = result["stream_alignment"].get("diagnostics")
        if not isinstance(diag, pd.DataFrame) or diag.empty:
            return "—"
        return str(int(diag.iloc[0].get("n_event_pairs", 0)))

    @render.text
    def median_lag():
        result = _result()
        drift = result.get("drift") if result else None
        summary = drift.get("summary") if isinstance(drift, dict) else None
        if not isinstance(summary, pd.DataFrame) or summary.empty:
            return "—"
        value = summary.iloc[0].get("median_lag_s")
        return "—" if pd.isna(value) else f"{float(value):.4f} s"

    @render.text
    def drift_slope():
        result = _result()
        drift = result.get("drift") if result else None
        summary = drift.get("summary") if isinstance(drift, dict) else None
        if not isinstance(summary, pd.DataFrame) or summary.empty:
            return "—"
        value = summary.iloc[0].get("drift_slope_s_per_s")
        return "—" if pd.isna(value) else f"{float(value):.6g} s/s"

    def _grid(key: str, empty_message: str):
        table = _tables().get(key)
        if not isinstance(table, pd.DataFrame) or table.empty:
            table = pd.DataFrame({"status": [empty_message]})
        return render.DataGrid(table, filters=True, height="380px")

    @render.data_frame
    def events():
        return _grid("events", "No event analysis has been run.")

    @render.data_frame
    def ttl_events():
        return _grid("ttl_events", "TTL extraction audit is available in TTL mode.")

    @render.data_frame
    def event_summary():
        return _grid("event_summary", "No event summary is available.")

    @render.data_frame
    def event_windows():
        return _grid("event_windows", "No event-window samples are available.")

    @render.data_frame
    def ttl_overview():
        return _grid("ttl_alignment_overview", "TTL alignment overview is available in TTL mode.")

    @render.data_frame
    def ttl_alignment_events():
        return _grid("ttl_alignment_events", "TTL-aligned events are available in TTL mode.")

    @render.data_frame
    def stream_diagnostics():
        return _grid("stream_diagnostics", "Load and enable a target stream for cross-stream diagnostics.")

    @render.data_frame
    def alignment_table():
        return _grid("stream_alignment_table", "No cross-stream anchor alignment is available.")

    @render.data_frame
    def drift_summary():
        return _grid("drift_summary", "At least two cross-stream anchors are required for drift diagnostics.")

    @render.plot(alt="Event-locked signal diagnostic")
    def event_plot():
        result = _result()
        if not result:
            return _placeholder("Run Events & Alignment to generate an event-locked diagnostic.")
        windows = result.get("event_windows")
        signal = result.get("parameters", {}).get("summary_cols", [])
        signal = signal[0] if signal else None
        if not isinstance(windows, pd.DataFrame) or windows.empty or not signal or signal not in windows.columns:
            return _placeholder("Choose a numeric summary signal to plot event-locked samples.")
        x = pd.to_numeric(windows["relative_time_s"], errors="coerce")
        y = pd.to_numeric(windows[signal], errors="coerce")
        fig, ax = plt.subplots()
        ax.scatter(x, y, s=7, alpha=0.25)
        finite = np.isfinite(x) & np.isfinite(y)
        if finite.any():
            frame = pd.DataFrame({"x": x[finite], "y": y[finite]})
            frame["bin"] = frame["x"].round(1)
            mean = frame.groupby("bin", sort=True)["y"].mean()
            ax.plot(mean.index, mean.values, linewidth=1.5)
        ax.axvline(0, linestyle="--", linewidth=1)
        ax.set_xlabel("Relative time (s)")
        ax.set_ylabel(str(signal))
        ax.set_title("Event-locked measurement diagnostic")
        return fig

    @render.plot(alt="Cross-stream lag and drift diagnostic")
    def drift_plot():
        result = _result()
        drift = result.get("drift") if result else None
        table = drift.get("lag_table") if isinstance(drift, dict) else None
        if not isinstance(table, pd.DataFrame) or table.empty:
            return _placeholder("Enable a second stream with at least two matched event anchors to estimate lag/drift.")
        fig, ax = plt.subplots()
        ax.scatter(table["reference_time"], table["lag_s"], s=28, label="Observed lag")
        ax.plot(table["reference_time"], table["fitted_lag_s"], linewidth=1.5, label="Linear fit")
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.set_xlabel("Reference event time (s)")
        ax.set_ylabel("Target - reference lag (s)")
        ax.set_title("Cross-stream clock lag diagnostic")
        ax.legend()
        return fig

    @render.text
    def parameters():
        result = _result()
        if not result:
            return "Run the workflow to record reproducibility parameters."
        return "\n".join(f"{k}: {v}" for k, v in result.get("parameters", {}).items())

    @render.download_button(filename="gpbiometricspy_reference_events.csv")
    def download_events():
        table = _tables().get("events", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_event_windows.csv")
    def download_windows():
        table = _tables().get("event_windows", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_event_summary.csv")
    def download_summary():
        table = _tables().get("event_summary", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_target_aligned.csv")
    def download_aligned_target():
        table = _tables().get("stream_target_aligned", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_alignment_lag.csv")
    def download_lag():
        table = _tables().get("drift_lag_table", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_event_alignment.py")
    def download_script():
        result = _result()
        yield event_alignment_reproducibility_script(result or {"parameters": {}})
