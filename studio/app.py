from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from shiny import App, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.modules.annotation import annotation_server, annotation_ui
    from studio.modules.eda_scr import eda_scr_server, eda_scr_ui
    from studio.modules.event_alignment import event_alignment_server, event_alignment_ui
    from studio.modules.gaze import gaze_server, gaze_ui
    from studio.modules.ppg_hr_hrv import ppg_hr_hrv_server, ppg_hr_hrv_ui
    from studio.modules.pupil import pupil_server, pupil_ui
    from studio.modules.qc import qc_server, qc_ui
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
    from modules.annotation import annotation_server, annotation_ui
    from modules.eda_scr import eda_scr_server, eda_scr_ui
    from modules.event_alignment import event_alignment_server, event_alignment_ui
    from modules.gaze import gaze_server, gaze_ui
    from modules.ppg_hr_hrv import ppg_hr_hrv_server, ppg_hr_hrv_ui
    from modules.pupil import pupil_server, pupil_ui
    from modules.qc import qc_server, qc_ui
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


def _project_sidebar():
    return ui.sidebar(
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
        ui.input_task_button(
            "run_qc",
            "Run foundation QC",
            label_busy="Running QC...",
            type="success",
            width="100%",
        ),
        ui.input_action_button("reset", "Reset session", class_="btn-outline-secondary w-100 mt-2"),
        ui.hr(),
        ui.tags.small(ui.output_text("status"), class_="text-secondary"),
        width=330,
    )


def _home_panel():
    return ui.div(
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
        ui.p(ui.tags.strong("Interpretation guardrail: "), GUARDRAIL, class_="text-secondary small"),
    )


def _reproducibility_panel():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Session provenance"),
                ui.output_data_frame("provenance"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("Reproducibility policy"),
                ui.p(
                    "Studio records workflow operations and delegates scientific calculations to the installed gpbiometricspy package."
                ),
                ui.p(
                    "Raw uploaded data are not intentionally written to the repository or application assets. Annotation and analysis downloads are generated from current session state.",
                    class_="text-secondary",
                ),
                ui.output_text_verbatim("session_summary"),
            ),
            col_widths=(8, 4),
        ),
        ui.p(ui.tags.strong("Interpretation guardrail: "), GUARDRAIL, class_="text-secondary small"),
    )


app_ui = ui.page_navbar(
    ui.nav_panel("Home", _home_panel(), value="home"),
    ui.nav_panel("Quality Control", qc_ui("qc"), value="qc"),
    ui.nav_panel("Annotation", annotation_ui("annotation"), value="annotation"),
    ui.nav_panel("EDA / SCR Analysis", eda_scr_ui("eda_scr"), value="eda_scr"),
    ui.nav_panel("PPG / HR / HRV Analysis", ppg_hr_hrv_ui("ppg_hr_hrv"), value="ppg_hr_hrv"),
    ui.nav_panel("Pupil Analysis", pupil_ui("pupil"), value="pupil"),
    ui.nav_panel("Gaze / Fixation / AOI Analysis", gaze_ui("gaze"), value="gaze"),
    ui.nav_panel("Events & Alignment", event_alignment_ui("event_alignment"), value="event_alignment"),
    ui.nav_panel("Reproducibility", _reproducibility_panel(), value="reproducibility"),
    title="gpbiometricspy Studio",
    id="main_nav",
    selected="home",
    sidebar=_project_sidebar(),
    fillable=False,
    window_title="gpbiometricspy Studio",
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
            status_text.set("Synthetic kiosk demo loaded. Run QC or open an analysis workflow when ready.")
        except Exception as exc:  # UI boundary: surface a concise error instead of crashing the session.
            status_text.set(f"Load failed: {exc}")

    @reactive.effect
    @reactive.event(input.load_upload)
    def _load_upload():
        try:
            data, source_name = load_uploaded_dataset(input.upload())
            set_dataset(data, source_name, "load_upload")
            status_text.set("Upload imported through gpbiometricspy. Run QC or analysis when ready.")
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
            status_text.set("Foundation QC complete. Open Quality Control for deeper diagnostics.")
        except Exception as exc:
            status_text.set(f"QC failed: {exc}")

    @reactive.effect
    @reactive.event(input.reset)
    def _reset():
        state.set(ProjectState())
        status_text.set("Session reset. No dataset is loaded.")

    qc_server("qc", state, status_text)
    annotation_server("annotation", state, status_text)
    eda_scr_server("eda_scr", state, status_text)
    ppg_hr_hrv_server("ppg_hr_hrv", state, status_text)
    pupil_server("pupil", state, status_text)
    gaze_server("gaze", state, status_text)
    event_alignment_server("event_alignment", state, status_text)

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

    @render.plot(alt="Gazepoint biometric signal activity quality-control plot")
    def activity_plot():
        current = state()
        if current.data is None or current.qc is None or "activity" not in current.qc:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Run foundation QC to generate the signal-activity plot.", ha="center", va="center")
            ax.set_axis_off()
            return fig
        return gp.plot_gazepoint_signal_activity(current.qc["activity"])

    @render.data_frame
    def provenance():
        rows = list(state().provenance)
        table = pd.DataFrame(rows) if rows else pd.DataFrame({"status": ["No operations recorded yet"]})
        return render.DataGrid(table, filters=True, height="430px")

    @render.text
    def session_summary():
        current = state()
        return (
            f"gpbiometricspy: {gp.__version__}\n"
            f"Dataset: {current.source_name}\n"
            f"Rows: {current.n_rows:,}\n"
            f"Columns: {current.n_columns:,}\n"
            f"Annotations: {len(current.annotations)}\n"
            f"Analyses: {len(current.analyses)}\n"
            f"Recorded operations: {len(current.provenance)}"
        )


app = App(app_ui, server)
