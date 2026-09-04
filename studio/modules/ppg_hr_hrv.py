from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.ppg_services import (
        analysis_group_column_choices,
        crosscheck_status_table,
        hr_signal_choices,
        ibi_signal_choices,
        ppg_hr_hrv_reproducibility_script,
        ppg_hr_hrv_tables,
        ppg_signal_choices,
        run_ppg_hr_hrv_analysis,
        time_column_choices,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from ppg_services import (
        analysis_group_column_choices,
        crosscheck_status_table,
        hr_signal_choices,
        ibi_signal_choices,
        ppg_hr_hrv_reproducibility_script,
        ppg_hr_hrv_tables,
        ppg_signal_choices,
        run_ppg_hr_hrv_analysis,
        time_column_choices,
    )


def _placeholder(message: str):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


@module.ui
def ppg_hr_hrv_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("PPG / HR / HRV analysis controls"),
                ui.input_radio_buttons(
                    "mode",
                    "Workflow mode",
                    choices={"guided": "Guided", "expert": "Expert"},
                    selected="guided",
                    inline=True,
                ),
                ui.input_select("ppg_col", "Pulse / PPG waveform", choices={"": "Not used"}),
                ui.input_select("hr_col", "Heart-rate column", choices={"": "Not used"}),
                ui.input_select("ibi_col", "IBI / RR column", choices={"": "Not used"}),
                ui.input_select("time_col", "Time column", choices={"": "No time column"}),
                ui.input_select("group_col", "Grouping column", choices={"": "No grouping"}),
                ui.input_numeric("sampling_rate", "Sampling rate (Hz)", value=60, min=1),
                ui.hr(),
                ui.tags.strong("Expert parameters"),
                ui.tags.small(
                    "Guided mode uses 40–180 bpm, RR tolerance 0.30, 300–2000 ms IBI limits, a 500 ms jump threshold, and no spline peak refinement or optional cross-checks.",
                    class_="text-secondary d-block mb-2",
                ),
                ui.layout_columns(
                    ui.input_numeric("bpm_min", "Minimum BPM", value=40, min=1),
                    ui.input_numeric("bpm_max", "Maximum BPM", value=180, min=2),
                    col_widths=(6, 6),
                ),
                ui.input_numeric("rr_tolerance", "RR rejection tolerance", value=0.30, min=0.01, step=0.05),
                ui.layout_columns(
                    ui.input_numeric("min_ibi", "Minimum IBI (ms)", value=300, min=1),
                    ui.input_numeric("max_ibi", "Maximum IBI (ms)", value=2000, min=2),
                    col_widths=(6, 6),
                ),
                ui.input_numeric("max_jump", "Maximum IBI jump (ms)", value=500, min=1),
                ui.input_numeric("min_valid_ibi", "Minimum valid IBI values", value=3, min=2),
                ui.input_checkbox("high_precision", "Spline-refine PPG peak timing", value=False),
                ui.input_checkbox("crosschecks", "Run HeartPy / BioSPPy / pyHRV-style cross-checks", value=False),
                ui.input_task_button(
                    "run",
                    "Run PPG / HR / HRV analysis",
                    label_busy="Analysing cardiac signals...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Scientific interpretation"),
                ui.p(
                    "Studio uses the public gpbiometricspy PPG, heart-rate, IBI-quality, and HRV APIs. Available signal families are analysed independently and retained in one reproducible session result."
                ),
                ui.p(
                    "HRV estimates require genuine beat-to-beat intervals or intervals derived from accepted pulse peaks. Vendor HRV validity fields are not treated as RR intervals.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Frequency-domain values from short or sparse recordings are exploratory diagnostics. Appropriate segment duration, stationarity, artifact control, and protocol-specific validation remain the researcher's responsibility.",
                    class_="text-secondary",
                ),
                ui.p(
                    "Cardiac and pulse features are physiological measurements; they do not by themselves establish emotion, stress, trust, preference, cognition, disease, or diagnosis.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.layout_column_wrap(
            ui.value_box("Waveform QC", ui.output_text("waveform_status"), theme="primary"),
            ui.value_box("Accepted pulse peaks", ui.output_text("peak_count")),
            ui.value_box("Mean BPM", ui.output_text("mean_bpm")),
            ui.value_box("HRV status", ui.output_text("hrv_status")),
            width=1 / 4,
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Overview",
                ui.layout_columns(
                    ui.card(ui.card_header("PPG waveform quality"), ui.output_data_frame("waveform_quality")),
                    ui.card(ui.card_header("Peak-detection diagnostics"), ui.output_data_frame("detection_diagnostics")),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Heart-rate quality"), ui.output_data_frame("hr_quality")),
                    ui.card(ui.card_header("IBI quality overview"), ui.output_data_frame("ibi_quality_overview")),
                    col_widths=(6, 6),
                ),
            ),
            ui.nav_panel(
                "Pulse / PPG",
                ui.card(
                    ui.card_header("Pulse waveform and detected peaks"),
                    ui.output_plot("peak_plot", height="500px"),
                    full_screen=True,
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Accepted / rejected peaks"), ui.output_data_frame("peaks_table"), full_screen=True),
                    ui.card(ui.card_header("PPG-derived measures"), ui.output_data_frame("ppg_measures"), full_screen=True),
                    col_widths=(7, 5),
                ),
            ),
            ui.nav_panel(
                "Heart rate",
                ui.card(
                    ui.card_header("Heart-rate trace"),
                    ui.output_plot("hr_plot", height="440px"),
                    full_screen=True,
                ),
                ui.card(ui.card_header("Heart-rate windows"), ui.output_data_frame("hr_windows"), full_screen=True),
            ),
            ui.nav_panel(
                "IBI / HRV",
                ui.layout_columns(
                    ui.card(ui.card_header("IBI group quality"), ui.output_data_frame("ibi_group_quality")),
                    ui.card(ui.card_header("IBI windows"), ui.output_data_frame("ibi_windows")),
                    col_widths=(6, 6),
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Exported-IBI HRV features"), ui.output_data_frame("ibi_hrv_features"), full_screen=True),
                    ui.card(ui.card_header("PPG-derived HRV features"), ui.output_data_frame("ppg_hrv_features"), full_screen=True),
                    col_widths=(6, 6),
                ),
                ui.card(
                    ui.card_header("Poincaré diagnostic"),
                    ui.output_plot("poincare_plot", height="480px"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Cross-checks",
                ui.card(
                    ui.card_header("Optional backend / style cross-checks"),
                    ui.output_data_frame("crosschecks_table"),
                    full_screen=True,
                ),
                ui.p(
                    "Cross-checks are supplementary comparisons. They do not override gpbiometricspy QC, create ground truth, or guarantee equivalence across algorithms.",
                    class_="text-secondary small",
                ),
            ),
            ui.nav_panel(
                "Export",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Tabular exports"),
                        ui.download_button("download_peaks", "Download pulse peaks CSV", class_="btn-success w-100"),
                        ui.download_button("download_ppg_measures", "Download PPG measures CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_hr", "Download HR windows CSV", class_="btn-outline-success w-100 mt-2"),
                        ui.download_button("download_hrv", "Download HRV features CSV", class_="btn-outline-success w-100 mt-2"),
                    ),
                    ui.card(
                        ui.card_header("Reproducible code"),
                        ui.p("Export the equivalent public gpbiometricspy calls used by the current workflow."),
                        ui.download_button("download_script", "Download Python script", class_="btn-primary w-100"),
                        ui.output_text_verbatim("script_preview"),
                    ),
                    col_widths=(5, 7),
                ),
            ),
            id="cardiac_tabs",
            selected="Overview",
        ),
    )


@module.server
def ppg_hr_hrv_server(input, output, session, state, status_text):
    local_status = reactive.Value("Load a dataset, confirm available cardiac channels, then run the Guided workflow.")

    @reactive.effect
    def _sync_choices():
        data = state().data
        ppg = ppg_signal_choices(data)
        hr = hr_signal_choices(data)
        ibi = ibi_signal_choices(data)
        times = time_column_choices(data)
        groups = analysis_group_column_choices(data)
        ui.update_select("ppg_col", choices={"": "Not used", **{c: c for c in ppg}}, selected=ppg[0] if ppg else "")
        ui.update_select("hr_col", choices={"": "Not used", **{c: c for c in hr}}, selected=hr[0] if hr else "")
        ui.update_select("ibi_col", choices={"": "Not used", **{c: c for c in ibi}}, selected=ibi[0] if ibi else "")
        ui.update_select("time_col", choices={"": "No time column", **{c: c for c in times}}, selected=times[0] if times else "")
        ui.update_select("group_col", choices={"": "No grouping", **{c: c for c in groups}}, selected=groups[0] if groups else "")

    def _result():
        return state().analyses.get("ppg_hr_hrv")

    @reactive.effect
    @reactive.event(input.run)
    def _run():
        current = state()
        if current.data is None:
            local_status.set("Load a dataset before running PPG/HR/HRV analysis.")
            return
        guided = input.mode() == "guided"
        parameters = {
            "ppg_col": input.ppg_col() or None,
            "hr_col": input.hr_col() or None,
            "ibi_col": input.ibi_col() or None,
            "time_col": input.time_col() or None,
            "group_col": input.group_col() or None,
            "sampling_rate_hz": float(input.sampling_rate()),
            "bpm_min": 40.0 if guided else float(input.bpm_min()),
            "bpm_max": 180.0 if guided else float(input.bpm_max()),
            "rr_tolerance": 0.30 if guided else float(input.rr_tolerance()),
            "min_ibi_ms": 300.0 if guided else float(input.min_ibi()),
            "max_ibi_ms": 2000.0 if guided else float(input.max_ibi()),
            "max_jump_ms": 500.0 if guided else float(input.max_jump()),
            "min_valid_ibi": 3 if guided else int(input.min_valid_ibi()),
            "high_precision": False if guided else bool(input.high_precision()),
            "run_crosschecks": False if guided else bool(input.crosschecks()),
            "mode": input.mode(),
        }
        try:
            result = run_ppg_hr_hrv_analysis(
                current.data,
                ppg_col=parameters["ppg_col"],
                hr_col=parameters["hr_col"],
                ibi_col=parameters["ibi_col"],
                time_col=parameters["time_col"],
                group_col=parameters["group_col"],
                sampling_rate_hz=parameters["sampling_rate_hz"],
                bpm_min=parameters["bpm_min"],
                bpm_max=parameters["bpm_max"],
                rr_tolerance=parameters["rr_tolerance"],
                min_ibi_ms=parameters["min_ibi_ms"],
                max_ibi_ms=parameters["max_ibi_ms"],
                max_jump_ms=parameters["max_jump_ms"],
                min_valid_ibi=parameters["min_valid_ibi"],
                high_precision=parameters["high_precision"],
                run_crosschecks=parameters["run_crosschecks"],
            )
            result["parameters"]["mode"] = input.mode()
            state.set(current.with_analysis("ppg_hr_hrv", result, parameters=parameters))
            local_status.set("PPG/HR/HRV workflow complete using public gpbiometricspy APIs.")
            status_text.set("Cardiac analysis complete. Review PPG, HR, IBI/HRV, and export tabs.")
        except Exception as exc:
            local_status.set(f"PPG/HR/HRV analysis failed: {exc}")

    @render.text
    def status():
        return local_status()

    @render.text
    def waveform_status():
        result = _result()
        obj = result.get("waveform_quality") if isinstance(result, dict) else None
        overview = obj.get("overview") if isinstance(obj, dict) else None
        if isinstance(overview, pd.DataFrame) and not overview.empty and "status" in overview:
            return str(overview.iloc[0]["status"])
        return "Not run"

    @render.text
    def peak_count():
        result = _result()
        peaks = result.get("cleaned_peaks") if isinstance(result, dict) else None
        if not isinstance(peaks, pd.DataFrame) or peaks.empty:
            return "0"
        accepted = peaks["accepted"].fillna(False).astype(bool) if "accepted" in peaks else pd.Series(True, index=peaks.index)
        return f"{int(accepted.sum()):,}"

    @render.text
    def mean_bpm():
        result = _result()
        measures = result.get("ppg_measures") if isinstance(result, dict) else None
        if isinstance(measures, pd.DataFrame) and not measures.empty and "bpm" in measures:
            value = pd.to_numeric(measures["bpm"], errors="coerce").mean()
            if pd.notna(value):
                return f"{value:.1f}"
        hr_windows = result.get("hr_windows") if isinstance(result, dict) else None
        if isinstance(hr_windows, pd.DataFrame):
            for column in ["mean", "mean_value", "mean_hr", "value_mean"]:
                if column in hr_windows:
                    value = pd.to_numeric(hr_windows[column], errors="coerce").mean()
                    if pd.notna(value):
                        return f"{value:.1f}"
        return "—"

    @render.text
    def hrv_status():
        result = _result()
        for key in ["ibi_hrv", "ppg_hrv"]:
            obj = result.get(key) if isinstance(result, dict) else None
            overview = obj.get("overview") if isinstance(obj, dict) else None
            if isinstance(overview, pd.DataFrame) and not overview.empty and "status" in overview:
                return str(overview.iloc[0]["status"])
        return "Not available"

    def _table(name: str, fallback: str) -> pd.DataFrame:
        table = ppg_hr_hrv_tables(_result()).get(name)
        if isinstance(table, pd.DataFrame) and not table.empty:
            return table
        return pd.DataFrame({"status": [fallback]})

    @render.data_frame
    def waveform_quality():
        return render.DataGrid(_table("waveform_quality_overview", "No PPG waveform-quality result is available."), filters=True)

    @render.data_frame
    def detection_diagnostics():
        return render.DataGrid(_table("detection_diagnostics", "No PPG peak-detection diagnostics are available."), filters=True)

    @render.data_frame
    def hr_quality():
        return render.DataGrid(_table("hr_quality", "No heart-rate quality result is available."), filters=True)

    @render.data_frame
    def ibi_quality_overview():
        return render.DataGrid(_table("ibi_quality_overview", "No IBI quality result is available."), filters=True)

    @render.data_frame
    def peaks_table():
        return render.DataGrid(_table("cleaned_peaks", "No pulse peaks are available."), filters=True, height="360px")

    @render.data_frame
    def ppg_measures():
        return render.DataGrid(_table("ppg_measures", "No PPG-derived measures are available."), filters=True, height="360px")

    @render.data_frame
    def hr_windows():
        return render.DataGrid(_table("hr_windows", "No heart-rate windows are available."), filters=True, height="360px")

    @render.data_frame
    def ibi_group_quality():
        return render.DataGrid(_table("ibi_quality_group_summary", "No group-level IBI quality result is available."), filters=True)

    @render.data_frame
    def ibi_windows():
        return render.DataGrid(_table("ibi_windows_windows", "No IBI window summaries are available."), filters=True)

    @render.data_frame
    def ibi_hrv_features():
        return render.DataGrid(_table("ibi_hrv_features", "No exported-IBI HRV features are available."), filters=True, height="360px")

    @render.data_frame
    def ppg_hrv_features():
        return render.DataGrid(_table("ppg_hrv_features", "No PPG-derived HRV features are available."), filters=True, height="360px")

    @render.data_frame
    def crosschecks_table():
        table = crosscheck_status_table(_result())
        if table.empty:
            table = pd.DataFrame({"status": ["Cross-checks were not requested or no eligible signal was available."]})
        return render.DataGrid(table, filters=True)

    @render.plot(alt="Pulse or PPG waveform with detected pulse peaks")
    def peak_plot():
        result = _result()
        detection = result.get("detection") if isinstance(result, dict) else None
        if isinstance(detection, dict):
            try:
                fig = gp.plot_gazepoint_ppg_peak_detection(detection)
                if fig is not None:
                    return fig
            except (TypeError, ValueError):
                pass
        return _placeholder("Run PPG analysis to generate the pulse-peak diagnostic.")

    @render.plot(alt="Heart-rate signal trace")
    def hr_plot():
        result = _result()
        p = result.get("parameters") if isinstance(result, dict) else None
        data = state().data
        if isinstance(p, dict) and data is not None and p.get("hr_col") in data.columns:
            return gp.plot_gazepoint_biometric_signals(
                data,
                signal_cols=[p["hr_col"]],
                time_col=p.get("time_col"),
                max_points=8000,
                legend=False,
                main="gpbiometricspy Studio: heart rate",
            )
        return _placeholder("Select an HR column and run analysis to generate the heart-rate trace.")

    @render.plot(alt="Poincare plot of successive accepted RR or IBI intervals")
    def poincare_plot():
        result = _result()
        rr = None
        if isinstance(result, dict):
            ibi_quality = result.get("ibi_quality")
            samples = ibi_quality.get("samples") if isinstance(ibi_quality, dict) else None
            if isinstance(samples, pd.DataFrame) and {"ibi_ms", "valid_ibi"}.issubset(samples.columns):
                valid = samples["valid_ibi"].fillna(False).astype(bool)
                rr = pd.to_numeric(samples.loc[valid, "ibi_ms"], errors="coerce").dropna().to_numpy()
            if rr is None or len(rr) < 2:
                ppg_rr = result.get("ppg_rr")
                if isinstance(ppg_rr, pd.DataFrame) and "rr_ms" in ppg_rr:
                    rr = pd.to_numeric(ppg_rr["rr_ms"], errors="coerce").dropna().to_numpy()
        if rr is not None and len(rr) >= 2:
            try:
                return gp.plot_gazepoint_ppg_poincare(rr_ms=rr)
            except (TypeError, ValueError):
                pass
        return _placeholder("At least two accepted RR/IBI intervals are required for a Poincaré diagnostic.")

    @render.text
    def script_preview():
        script = ppg_hr_hrv_reproducibility_script(_result())
        lines = script.splitlines()
        return "\n".join(lines[:22]) + ("\n..." if len(lines) > 22 else "")

    @render.download_button(filename="gpbiometricspy_ppg_peaks.csv")
    def download_peaks():
        yield ppg_hr_hrv_tables(_result()).get("cleaned_peaks", pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_ppg_measures.csv")
    def download_ppg_measures():
        yield ppg_hr_hrv_tables(_result()).get("ppg_measures", pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_hr_windows.csv")
    def download_hr():
        yield ppg_hr_hrv_tables(_result()).get("hr_windows", pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_hrv_features.csv")
    def download_hrv():
        tables = ppg_hr_hrv_tables(_result())
        table = tables.get("ibi_hrv_features")
        if not isinstance(table, pd.DataFrame) or table.empty:
            table = tables.get("ppg_hrv_features", pd.DataFrame())
        yield table.to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_ppg_hr_hrv_analysis.py")
    def download_script():
        yield ppg_hr_hrv_reproducibility_script(_result())
