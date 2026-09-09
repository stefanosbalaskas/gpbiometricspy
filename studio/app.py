from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from shiny import App, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.config import studio_runtime_config
    from studio.modules.annotation import annotation_server, annotation_ui
    from studio.modules.eda_scr import eda_scr_server, eda_scr_ui
    from studio.modules.event_alignment import event_alignment_server, event_alignment_ui
    from studio.modules.gaze import gaze_server, gaze_ui
    from studio.modules.multimodal import multimodal_server, multimodal_ui
    from studio.modules.ppg_hr_hrv import ppg_hr_hrv_server, ppg_hr_hrv_ui
    from studio.modules.pupil import pupil_server, pupil_ui
    from studio.modules.qc import qc_server, qc_ui
    from studio.modules.reporting import reporting_server, reporting_ui
    from studio.modules.statistics_modelling import statistics_modelling_server, statistics_modelling_ui
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
    from config import studio_runtime_config
    from modules.annotation import annotation_server, annotation_ui
    from modules.eda_scr import eda_scr_server, eda_scr_ui
    from modules.event_alignment import event_alignment_server, event_alignment_ui
    from modules.gaze import gaze_server, gaze_ui
    from modules.multimodal import multimodal_server, multimodal_ui
    from modules.ppg_hr_hrv import ppg_hr_hrv_server, ppg_hr_hrv_ui
    from modules.pupil import pupil_server, pupil_ui
    from modules.qc import qc_server, qc_ui
    from modules.reporting import reporting_server, reporting_ui
    from modules.statistics_modelling import statistics_modelling_server, statistics_modelling_ui
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


RUNTIME_CONFIG = studio_runtime_config()
STUDIO_DIR = Path(__file__).resolve().parent

GUARDRAIL = (
    "Signals and derived features are measurements, not direct evidence of emotion, stress, "
    "trust, preference, cognition, or diagnosis."
)


def _safe_error(prefix: str, exc: Exception) -> str:
    """Return a concise UI-safe local error without losing the actionable message."""
    detail = str(exc).strip() or exc.__class__.__name__
    if len(detail) > 220:
        detail = f"{detail[:217]}..."
    return f"{prefix} — {detail}"


def _workflow_step(number: str, title: str, detail: str):
    return ui.div(
        ui.tags.span(number, class_="studio-step-number"),
        ui.tags.strong(title),
        ui.tags.small(detail),
        class_="studio-workflow-step",
    )


def _project_sidebar():
    intake_items = [
        ui.div(
            ui.tags.span("PROJECT", class_="studio-sidebar-kicker"),
            ui.h5("Start with your data", class_="mb-1"),
            ui.p("Load the synthetic demo first, or import a local Gazepoint export.", class_="small text-secondary mb-3"),
        ),
        ui.input_text("project_name_input", "Project name", value="Untitled project"),
        ui.input_action_button("apply_project_name", "Apply project name", class_="btn-outline-secondary w-100 mb-2"),
        ui.input_action_button("load_demo", "Load synthetic demo", class_="btn-primary w-100"),
    ]
    if RUNTIME_CONFIG.allow_external_uploads:
        intake_items.extend(
            [
                ui.div(class_="studio-sidebar-divider"),
                ui.input_file(
                    "upload",
                    "Gazepoint CSV/TXT",
                    accept=[".csv", ".txt", "text/csv", "text/plain"],
                    multiple=False,
                ),
                ui.p("Research files are processed in this local/private Studio session.", class_="small text-secondary"),
                ui.input_action_button("load_upload", "Import uploaded file", class_="btn-outline-primary w-100"),
            ]
        )
    else:
        intake_items.append(
            ui.div(
                ui.tags.strong("Synthetic data only."),
                ui.p(
                    "External uploads are disabled on this public deployment. Use the local or authenticated Studio for research data.",
                    class_="mb-0 small",
                ),
                class_="studio-public-demo-note",
                role="note",
            )
        )

    intake_items.extend(
        [
            ui.div(class_="studio-sidebar-divider"),
            ui.div(
                ui.tags.span("FOUNDATION", class_="studio-sidebar-kicker"),
                ui.h5("Establish data quality", class_="mb-1"),
                ui.p("Run the baseline checks before signal-specific analysis.", class_="small text-secondary mb-3"),
            ),
            ui.input_task_button(
                "run_qc",
                "Run foundation QC",
                label_busy="Running QC...",
                type="success",
                width="100%",
            ),
            ui.div(class_="studio-sidebar-divider"),
            ui.div(
                ui.tags.span("SESSION", class_="studio-sidebar-kicker"),
                ui.output_text("session_summary"),
                class_="studio-session-summary",
            ),
            ui.input_action_button("reset", "Reset session", class_="btn-outline-secondary w-100 mt-3"),
            ui.div(class_="studio-sidebar-divider"),
            ui.tags.div(
                {"role": "status", "aria-live": "polite", "aria-atomic": "true", "class": "studio-status-line"},
                ui.output_text("status"),
            ),
        ]
    )
    return ui.sidebar(*intake_items, width=340)


def _home_panel():
    return ui.div(
        ui.div(
            ui.tags.span(
                "PUBLIC SYNTHETIC DEMO" if RUNTIME_CONFIG.is_public_demo else "LOCAL RESEARCH STUDIO",
                class_="studio-runtime-chip",
            ),
            ui.h2("From raw data to a reproducible result", class_="studio-home-title"),
            ui.p(
                "Follow a visible research path instead of guessing which analysis comes next. "
                "Studio uses the same tested gpbiometricspy functions available in Python.",
                class_="studio-home-lead",
            ),
            ui.div(
                _workflow_step("01", "Project", "Load data and inspect channels"),
                _workflow_step("02", "Quality", "Run foundation and signal QC"),
                _workflow_step("03", "Analyze", "EDA, HRV, pupil, gaze and AOIs"),
                _workflow_step("04", "Align", "Events, TTL and secondary streams"),
                _workflow_step("05", "Model", "Prepare and test defensible models"),
                _workflow_step("06", "Report", "Export provenance and replay"),
                class_="studio-workflow-strip",
            ),
            class_="studio-home-hero",
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Next recommended step"),
                ui.tags.div(ui.output_text("next_step"), class_="studio-next-step"),
            ),
            ui.card(
                ui.card_header("Project readiness"),
                ui.tags.div(ui.output_text("readiness_summary"), class_="studio-readiness"),
            ),
            col_widths=(7, 5),
        ),
        ui.layout_column_wrap(
            ui.value_box("Dataset", ui.output_text("dataset_name"), theme="primary"),
            ui.value_box("Rows", ui.output_text("row_count")),
            ui.value_box("QC", ui.output_text("qc_state")),
            ui.value_box("Analyses", ui.output_text("analysis_count")),
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
        ui.div(
            ui.tags.strong("Interpretation guardrail"),
            ui.p(GUARDRAIL, class_="mb-0"),
            class_="studio-guardrail",
            role="note",
        ),
        class_="studio-home-panel",
    )


def _page_title():
    return ui.TagList(
        ui.tags.a("Skip to content", href="#studio-main", class_="studio-skip-link"),
        ui.tags.span("gpbiometricspy Studio"),
        ui.tags.small("research workspace", class_="studio-brand-subtitle"),
    )


def _page_header():
    items = [ui.include_css(STUDIO_DIR / "www" / "studio.css")]
    if RUNTIME_CONFIG.is_public_demo:
        items.append(ui.include_css(STUDIO_DIR / "www" / "public-demo.css"))
        items.append(
            ui.div(
                ui.tags.strong("Public synthetic demonstration."),
                " External uploads are disabled and application errors are sanitized. No participant data should be submitted.",
                class_="studio-runtime-banner",
                role="note",
            )
        )
    else:
        items.append(
            ui.div(
                ui.tags.strong("Runtime: "),
                RUNTIME_CONFIG.mode_label,
                class_="visually-hidden",
                role="note",
            )
        )
    items.append(ui.div(id="studio-main", tabindex="-1"))
    return ui.TagList(*items)


app_ui = ui.page_navbar(
    ui.nav_panel("Home", _home_panel(), value="home"),
    ui.nav_panel("Quality Control", qc_ui("qc"), value="qc"),
    ui.nav_panel("Annotation", annotation_ui("annotation"), value="annotation"),
    ui.nav_panel("EDA / SCR Analysis", eda_scr_ui("eda_scr"), value="eda_scr"),
    ui.nav_panel("PPG / HR / HRV Analysis", ppg_hr_hrv_ui("ppg_hr_hrv"), value="ppg_hr_hrv"),
    ui.nav_panel("Pupil Analysis", pupil_ui("pupil"), value="pupil"),
    ui.nav_panel("Gaze / Fixation / AOI Analysis", gaze_ui("gaze"), value="gaze"),
    ui.nav_panel("Events & Alignment", event_alignment_ui("event_alignment"), value="event_alignment"),
    ui.nav_panel("Multimodal Analysis", multimodal_ui("multimodal"), value="multimodal"),
    ui.nav_panel("Statistics & Modelling", statistics_modelling_ui("statistics_modelling"), value="statistics_modelling"),
    ui.nav_panel("Reporting & Reproducibility", reporting_ui("reporting"), value="reporting"),
    title=_page_title(),
    id="main_nav",
    selected="home",
    sidebar=_project_sidebar(),
    header=_page_header(),
    fillable=False,
    window_title="gpbiometricspy Studio",
    lang="en",
)


def server(input, output, session):
    state = reactive.Value(ProjectState())
    initial_status = (
        "Public synthetic demonstration ready. Load the bundled demo to begin. External uploads are disabled."
        if RUNTIME_CONFIG.is_public_demo
        else "Ready. Load the synthetic demo or import a local Gazepoint export."
    )
    status_text = reactive.Value(initial_status)

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
    @reactive.event(input.apply_project_name)
    def _apply_project_name():
        try:
            state.set(state().with_project_name(input.project_name_input()))
            status_text.set(f"Project name set to {state().project_name!r}.")
        except Exception as exc:
            status_text.set(_safe_error("Project name not updated", exc))

    @reactive.effect
    @reactive.event(input.load_demo)
    def _load_demo():
        try:
            data, source_name = load_demo_dataset()
            set_dataset(data, source_name, "load_demo")
            status_text.set("Synthetic kiosk demo loaded. Next: run foundation QC.")
        except Exception as exc:  # UI boundary: surface a concise error instead of crashing the session.
            status_text.set(_safe_error("Demo load failed", exc))

    @reactive.effect
    @reactive.event(input.load_upload)
    def _load_upload():
        try:
            data, source_name = load_uploaded_dataset(input.upload())
            set_dataset(data, source_name, "load_upload")
            status_text.set("Research file imported. Next: run foundation QC before analysis.")
        except Exception as exc:
            status_text.set(_safe_error("Import failed", exc))

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
            status_text.set("Foundation QC complete. Review Quality Control, then choose a signal analysis workflow.")
        except Exception as exc:
            status_text.set(_safe_error("Foundation QC failed", exc))

    @reactive.effect
    @reactive.event(input.reset)
    def _reset():
        state.set(ProjectState())
        status_text.set(
            "Session reset. Load the bundled synthetic demo to continue."
            if RUNTIME_CONFIG.is_public_demo
            else "Session reset. Load a dataset to begin a new project."
        )

    qc_server("qc", state, status_text)
    annotation_server("annotation", state, status_text)
    eda_scr_server("eda_scr", state, status_text)
    ppg_hr_hrv_server("ppg_hr_hrv", state, status_text)
    pupil_server("pupil", state, status_text)
    gaze_server("gaze", state, status_text)
    event_alignment_server("event_alignment", state, status_text)
    multimodal_server("multimodal", state, status_text)
    statistics_modelling_server("statistics_modelling", state, status_text)
    reporting_server("reporting", state, status_text)

    @render.text
    def status():
        return status_text()

    @render.text
    def session_summary():
        current = state()
        if not current.loaded:
            return "No project data loaded"
        qc_label = "QC complete" if current.qc is not None else "QC pending"
        return f"{current.project_name} · {qc_label} · {len(current.analyses)} analyses · {len(current.annotations)} annotations"

    @render.text
    def next_step():
        current = state()
        if not current.loaded:
            return "Load the synthetic demo to learn the workflow, or import a local Gazepoint CSV/TXT file."
        if current.qc is None:
            return "Run foundation QC. This establishes the baseline quality checks before signal-specific interpretation."
        if not current.analyses:
            return "Review Quality Control, then open EDA/SCR, PPG/HRV, Pupil, or Gaze/AOI based on the channels you recorded."
        if len(current.analyses) == 1:
            return "You have one saved analysis. Add another signal or alignment workflow, or review Reporting & Reproducibility."
        return "Your project has multiple analyses. Review alignment/modelling as needed, then export provenance and replay outputs in Reporting & Reproducibility."

    @render.text
    def readiness_summary():
        current = state()
        if not current.loaded:
            return "Project not started · dataset required"
        quality = "QC ✓" if current.qc is not None else "QC pending"
        analyses = f"{len(current.analyses)} analyses"
        annotations = f"{len(current.annotations)} annotations"
        return f"Dataset ✓ · {quality} · {analyses} · {annotations}"

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
    def qc_state():
        return "Complete" if state().qc is not None else "Pending"

    @render.text
    def analysis_count():
        return str(len(state().analyses))

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
            return render.DataGrid(pd.DataFrame({"status": ["No dataset loaded — start with the synthetic demo"]}))
        return render.DataGrid(data.head(250), filters=True, height="360px")

    @render.data_frame
    def active_channels():
        table = active_channels_table(state().validation)
        if table.empty:
            table = pd.DataFrame({"status": ["Load a dataset to detect channels"]})
        return render.DataGrid(table, filters=True)

    @render.data_frame
    def missingness():
        table = missingness_table(state().qc)
        if table.empty:
            table = pd.DataFrame({"status": ["Run foundation QC to audit missingness and zero values"]})
        return render.DataGrid(table, filters=True)

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


app = App(app_ui, server)
if RUNTIME_CONFIG.sanitize_errors:
    app.sanitize_errors = True
