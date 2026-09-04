from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.services import annotation_signal_choices, annotations_frame, time_column_choices
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import annotation_signal_choices, annotations_frame, time_column_choices


@module.ui
def annotation_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Annotation controls"),
                ui.input_select("signal_col", "EDA signal", choices=[]),
                ui.input_select("time_col", "Time column", choices=[]),
                ui.input_text("note", "Annotation note", value=""),
                ui.input_action_button("add_peak", "Add clicked peak", class_="btn-primary w-100"),
                ui.input_action_button("add_artifact", "Add brushed artifact interval", class_="btn-outline-primary w-100 mt-2"),
                ui.hr(),
                ui.input_numeric("remove_row", "Annotation row to remove", value=1, min=1),
                ui.input_action_button("remove", "Remove row", class_="btn-outline-danger w-100"),
                ui.input_action_button("clear", "Clear annotations", class_="btn-outline-secondary w-100 mt-2"),
                ui.hr(),
                ui.download_button("download_annotations", "Download annotations CSV", class_="btn-success w-100"),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("How to annotate"),
                ui.p("Click the signal plot to position a manual peak, then choose Add clicked peak."),
                ui.p("Drag a rectangular brush across the x-axis interval you want to mark as an artifact, then choose Add brushed artifact interval."),
                ui.p(
                    "Annotations are expert-review metadata. They do not infer emotion, stress, cognition, trust, preference, or diagnosis.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.card(
            ui.card_header("Interactive EDA annotation"),
            ui.output_plot("signal_plot", height="480px", click=True, brush=True),
            full_screen=True,
        ),
        ui.layout_columns(
            ui.card(ui.card_header("Current pointer / brush"), ui.output_text_verbatim("selection_info")),
            ui.card(ui.card_header("Annotations"), ui.output_data_frame("annotations"), full_screen=True),
            col_widths=(4, 8),
        ),
    )


@module.server
def annotation_server(input, output, session, state, status_text):
    local_status = reactive.Value("Load a dataset with an EDA channel to begin annotation.")

    @reactive.effect
    def _sync_choices():
        data = state().data
        signals = annotation_signal_choices(data)
        times = time_column_choices(data)
        ui.update_select("signal_col", choices=signals, selected=signals[0] if signals else None)
        ui.update_select("time_col", choices=times, selected=times[0] if times else None)

    @reactive.effect
    @reactive.event(input.add_peak)
    def _add_peak():
        current = state()
        click = input.signal_plot_click()
        if current.data is None:
            local_status.set("Load a dataset before annotating.")
            return
        if not click or click.get("x") is None:
            local_status.set("Click the signal plot first, then add the peak.")
            return
        if not input.signal_col() or not input.time_col():
            local_status.set("A supported EDA signal and time column are required.")
            return
        annotation = {
            "annotation_type": "manual_peak",
            "signal_col": input.signal_col(),
            "time_col": input.time_col(),
            "time": float(click["x"]),
            "start": None,
            "end": None,
            "note": input.note(),
        }
        state.set(current.with_annotation(annotation))
        local_status.set("Manual peak added.")
        status_text.set("Annotation added. The reproducibility trail has been updated.")

    @reactive.effect
    @reactive.event(input.add_artifact)
    def _add_artifact():
        current = state()
        brush = input.signal_plot_brush()
        if current.data is None:
            local_status.set("Load a dataset before annotating.")
            return
        if not brush or brush.get("xmin") is None or brush.get("xmax") is None:
            local_status.set("Brush an interval on the signal plot first.")
            return
        if not input.signal_col() or not input.time_col():
            local_status.set("A supported EDA signal and time column are required.")
            return
        start = float(min(brush["xmin"], brush["xmax"]))
        end = float(max(brush["xmin"], brush["xmax"]))
        annotation = {
            "annotation_type": "artifact_interval",
            "signal_col": input.signal_col(),
            "time_col": input.time_col(),
            "time": None,
            "start": start,
            "end": end,
            "note": input.note(),
        }
        state.set(current.with_annotation(annotation))
        local_status.set("Artifact interval added.")
        status_text.set("Artifact annotation added. The reproducibility trail has been updated.")

    @reactive.effect
    @reactive.event(input.remove)
    def _remove():
        current = state()
        try:
            row_number = int(input.remove_row())
            state.set(current.without_annotation(row_number))
            local_status.set(f"Annotation row {row_number} removed.")
        except (TypeError, ValueError) as exc:
            local_status.set(f"Remove failed: {exc}")

    @reactive.effect
    @reactive.event(input.clear)
    def _clear():
        current = state()
        if not current.annotations:
            local_status.set("There are no annotations to clear.")
            return
        state.set(current.without_annotations())
        local_status.set("All annotations cleared.")

    @render.text
    def status():
        return local_status()

    @render.text
    def selection_info():
        click = input.signal_plot_click()
        brush = input.signal_plot_brush()
        click_text = "No click yet." if not click else f"Click x={click.get('x')!s}, y={click.get('y')!s}"
        brush_text = "No brush yet." if not brush else f"Brush x=[{brush.get('xmin')!s}, {brush.get('xmax')!s}]"
        return f"{click_text}\n{brush_text}"

    @render.plot(alt="EDA signal with manual peak and artifact annotations")
    def signal_plot():
        current = state()
        data = current.data
        signal_col = input.signal_col()
        time_col = input.time_col()
        if data is None or not signal_col or not time_col or signal_col not in data or time_col not in data:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Load a dataset with EDA and time columns to annotate.", ha="center", va="center")
            ax.set_axis_off()
            return fig

        fig = gp.plot_gazepoint_biometric_signals(
            data,
            signal_cols=[signal_col],
            time_col=time_col,
            max_points=8000,
            legend=False,
            main=f"Manual annotation: {signal_col}",
        )
        ax = fig.axes[0]
        for ann in current.annotations:
            if ann.get("signal_col") != signal_col or ann.get("time_col") != time_col:
                continue
            if ann.get("annotation_type") == "manual_peak" and ann.get("time") is not None:
                ax.axvline(float(ann["time"]), linestyle="--", alpha=0.8)
            elif ann.get("annotation_type") == "artifact_interval":
                if ann.get("start") is not None and ann.get("end") is not None:
                    ax.axvspan(float(ann["start"]), float(ann["end"]), alpha=0.18)
        return fig

    @render.data_frame
    def annotations():
        table = annotations_frame(state().annotations)
        if table.empty:
            table = pd.DataFrame({"status": ["No annotations recorded."]})
        return render.DataGrid(table, filters=True, height="360px")

    @render.download_button(filename="gpbiometricspy_manual_annotations.csv")
    def download_annotations():
        table = annotations_frame(state().annotations)
        yield table.to_csv(index=False)
