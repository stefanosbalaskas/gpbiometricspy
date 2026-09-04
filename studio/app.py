from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from shiny import App, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.services import (
        active_channels_table,
        inspect_dataset,
        issues_table,
        load_demo_dataset,
        load_uploaded_dataset,
        missingness_table,
        run_qc,
    )
    from studio.state import ProjectState
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import (
        active_channels_table,
        inspect_dataset,
        issues_table,
        load_demo_dataset,
        load_uploaded_dataset,
        missingness_table,
        run_qc,
    )
    from state import ProjectState


GUARDRAIL = (
    "Signals and derived features are measurements, not direct evidence of emotion, stress, "
    "trust, preference, cognition, or diagnosis."
)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h5("Project intake"),
        ui.input_action_button("load_demo", "Load synthetic demo", class_="btn-primary w-100"),
        ui.hr(),
        ui.input_file(
            "upload",
            "Upload Gazepoint CSV/TXT",
            accept=[".csv", ".txt", "text/csv", "text/plain"],
            multiple=False,
        ),
        ui.input_action_button("load_upload", "Import uploaded file", class_="btn-outline-primary w-100"),
        ui.hr(),
        ui.input_action_button("run_qc", "Run package-native QC", class_="btn-success w-100"),
        ui.input_action_button("reset", "Reset session", class_="btn-outline-secondary w-100 mt-2"),
        ui.hr(),
        ui.small(ui.output_text("status")),
        width=330,
    ),
    ui.layout_column_wrap(
        ui.value_box("Dataset", ui.output_text("dataset_name"), theme="primary"),
        ui.value_box("Rows", ui.output_text("row_count")),
        ui.value_box("Columns", ui.output_text("column_count")),
        ui.value_box("Active biometric signals", ui.output_text("active_count")),
        width=1 / 4,
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Data preview"),
            ui.output_data_frame("preview"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Detected channels"),
            ui.output_data_frame("active_channels"),
            full_screen=True,
        ),
        col_widths=(7, 5),
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Missingness and zero-value audit"),
            ui.output_data_frame("missingness"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Validation issues"),
            ui.output_data_frame("issues"),
            full_screen=True,
        ),
        col_widths=(7, 5),
    ),
    ui.card(
        ui.card_header("Signal activity QC"),
        ui.output_plot("activity_plot", height="420px"),
        full_screen=True,
    ),
    ui.card(
        ui.card_header("Reproducibility trail"),
        ui.output_data_frame("provenance"),
    ),
    ui.p(ui.tags.strong("Interpretation guardrail: "), GUARDRAIL, class_="text-secondary small"),
    title="gpbiometricspy Studio",
    window_title="gpbiometricspy Studio",
    fillable=False,
)


def server(input, output, session):
    state = reactive.Value(ProjectState())
    status_text = reactive.Value("Ready. Load the bundled demo or upload a Gazepoint export.")

    def set_dataset(data: pd.DataFrame, source_name: str, operation: str) -> None:
        validation = inspect_dataset(data)
        state.set(
            state().with_dataset(
                data,
                source_name=source_name,
                validation=validation,
                operation=operation,
            )
        )

    @reactive.effect
    @reactive.event(input.load_demo)
    def _load_demo():
        try:
            data, source_name = load_demo_dataset()
            set_dataset(data, source_name, "load_demo")
            status_text.set("Synthetic kiosk demo loaded. Run QC when ready.")
        except Exception as exc:  # UI boundary: surface a concise error instead of crashing the session.
            status_text.set(f"Load failed: {exc}")

    @reactive.effect
    @reactive.event(input.load_upload)
    def _load_upload():
        try:
            data, source_name = load_uploaded_dataset(input.upload())
            set_dataset(data, source_name, "load_upload")
            status_text.set("Upload imported through gpbiometricspy. Run QC when ready.")
        except Exception as exc:
            status_text.set(f"Import failed: {exc}")

    @reactive.effect
    @reactive.event(input.run_qc)
    def _run_qc():
        current = state()
        if current.data is None:
            status_text.set("Load a dataset before running QC.")
            return
        try:
            qc = run_qc(current.data)
            state.set(current.with_qc(qc))
            status_text.set("QC complete. Results below were produced by public gpbiometricspy APIs.")
        except Exception as exc:
            status_text.set(f"QC failed: {exc}")

    @reactive.effect
    @reactive.event(input.reset)
    def _reset():
        state.set(ProjectState())
        status_text.set("Session reset. No dataset is loaded.")

    @render.text
    def status():
        return status_text()

    @render.text
    def dataset_name():
        return state().source_name

    @render.text
    def row_count():
        return f"{state().n_rows:,}"

    @render.text
    def column_count():
        return f"{state().n_columns:,}"

    @render.text
    def active_count():
        table = active_channels_table(state().validation)
        if table.empty or "active" not in table:
            return "0"
        biological = table[table["signal"].isin(["gsr_eda", "heart_rate", "engagement_dial"])]
        return str(int(biological["active"].fillna(False).astype(bool).sum()))

    @render.data_frame
    def preview():
        data = state().data
        if data is None:
            return render.DataGrid(pd.DataFrame({"status": ["No dataset loaded"]}))
        return render.DataGrid(data.head(250), filters=True, height="360px")

    @render.data_frame
    def active_channels():
        return render.DataGrid(active_channels_table(state().validation), filters=True)

    @render.data_frame
    def missingness():
        return render.DataGrid(missingness_table(state().qc), filters=True)

    @render.data_frame
    def issues():
        validation = state().qc.get("validation") if state().qc else state().validation
        table = issues_table(validation)
        if table.empty:
            table = pd.DataFrame({"status": ["No validation issues detected"]})
        return render.DataGrid(table, filters=True)

    @render.plot
    def activity_plot():
        current = state()
        if current.data is None or current.qc is None:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Run QC to generate the signal-activity plot.", ha="center", va="center")
            ax.set_axis_off()
            return fig
        return gp.plot_gazepoint_signal_activity(current.data)

    @render.data_frame
    def provenance():
        rows = list(state().provenance)
        table = pd.DataFrame(rows) if rows else pd.DataFrame({"status": ["No operations recorded yet"]})
        return render.DataGrid(table, filters=True)


app = App(app_ui, server)
