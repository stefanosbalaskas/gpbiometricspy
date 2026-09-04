from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from shiny import module, reactive, render, ui

import gpbiometricspy as gp

try:
    from studio.statistics_services import (
        categorical_column_choices,
        cluster_report_text,
        cluster_reproducibility_script,
        cluster_tables,
        condition_levels,
        lme_reproducibility_script,
        lme_tables,
        numeric_column_choices,
        participant_column_choices,
        run_cluster_analysis,
        run_lme_preparation,
        statistics_source_choices,
        statistics_source_inventory,
        statistics_source_table,
        time_column_choices,
        trial_column_choices,
        unsupported_cluster_guardrails,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from statistics_services import (
        categorical_column_choices,
        cluster_report_text,
        cluster_reproducibility_script,
        cluster_tables,
        condition_levels,
        lme_reproducibility_script,
        lme_tables,
        numeric_column_choices,
        participant_column_choices,
        run_cluster_analysis,
        run_lme_preparation,
        statistics_source_choices,
        statistics_source_inventory,
        statistics_source_table,
        time_column_choices,
        trial_column_choices,
        unsupported_cluster_guardrails,
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


def _choice_dict(values: list[str], empty_label: str = "None") -> dict[str, str]:
    return {"": empty_label, **{value: value for value in values}}


def _preferred_source(choices: dict[str, str], preferred: list[str]) -> str:
    for key in preferred:
        if key in choices:
            return key
    return next(iter(choices), "")


def _first_table(tables: dict[str, pd.DataFrame], prefix: str) -> pd.DataFrame | None:
    for key, value in tables.items():
        if key.startswith(prefix) and isinstance(value, pd.DataFrame):
            return value
    return None


@module.ui
def statistics_modelling_ui():
    return ui.div(
        ui.layout_columns(
            ui.card(
                ui.card_header("Statistical workflow scope"),
                ui.p(
                    "Studio separates model-data preparation from supported inferential procedures. "
                    "The mixed-effects workspace prepares auditable model tables and formulas; it does not invent a model fitter that the public package does not provide."
                ),
                ui.p(
                    "Cluster permutation is limited to the validated two-condition, within-subject, one-dimensional time-course implementation. "
                    "A package-native grid/design diagnostic is mandatory before permutations are run.",
                    class_="text-secondary",
                ),
            ),
            ui.card(
                ui.card_header("Available statistical sources"),
                ui.output_data_frame("source_inventory"),
                full_screen=True,
            ),
            col_widths=(5, 7),
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Model preparation",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Model controls"),
                        ui.input_radio_buttons(
                            "model_mode",
                            "Workflow mode",
                            choices={"guided": "Guided", "expert": "Expert"},
                            selected="guided",
                            inline=True,
                        ),
                        ui.input_select("model_source", "Source table", choices={"": "No source available"}),
                        ui.input_select("model_outcome", "Numeric outcome", choices={"": "No numeric outcome"}),
                        ui.input_selectize(
                            "model_fixed",
                            "Fixed effects",
                            choices=[],
                            multiple=True,
                            options={"placeholder": "Select condition/design predictors"},
                        ),
                        ui.input_selectize(
                            "model_covariates",
                            "Covariates",
                            choices=[],
                            multiple=True,
                            options={"placeholder": "Optional numeric covariates"},
                        ),
                        ui.layout_columns(
                            ui.input_select("model_participant", "Participant", choices={"": "None"}),
                            ui.input_select("model_trial", "Trial / stimulus", choices={"": "None"}),
                            col_widths=(6, 6),
                        ),
                        ui.input_checkbox("model_baseline_correct", "Baseline-correct outcome", value=False),
                        ui.input_select("model_baseline", "Baseline column", choices={"": "None"}),
                        ui.input_selectize(
                            "model_factors",
                            "Treat as factors",
                            choices=[],
                            multiple=True,
                            options={"placeholder": "Categorical model terms"},
                        ),
                        ui.input_selectize(
                            "model_continuous",
                            "Continuous terms",
                            choices=[],
                            multiple=True,
                            options={"placeholder": "Numeric predictors to scale/retain"},
                        ),
                        ui.input_checkbox("model_scale", "Z-standardise selected continuous terms", value=False),
                        ui.input_numeric("model_min_rows", "Minimum complete rows", value=10, min=1, step=1),
                        ui.input_task_button(
                            "run_model",
                            "Prepare Model Data",
                            label_busy="Preparing model data...",
                            type="success",
                            width="100%",
                        ),
                        ui.tags.small(ui.output_text("model_status"), class_="text-secondary d-block mt-2"),
                    ),
                    ui.card(
                        ui.card_header("Why preparation is separate"),
                        ui.p(
                            "prepare_gazepoint_biometrics_lme_data() resolves complete cases, factor/random-effect roles, optional baseline correction, optional scaling, and a reproducible formula specification."
                        ),
                        ui.p(
                            "The generated formula is a design specification, not evidence that a mixed model has been fitted or that its assumptions are satisfied.",
                            class_="text-secondary",
                        ),
                        ui.output_text_verbatim("model_formula"),
                    ),
                    col_widths=(5, 7),
                ),
                ui.layout_column_wrap(
                    ui.value_box("Input rows", ui.output_text("model_input_rows"), theme="primary"),
                    ui.value_box("Complete rows", ui.output_text("model_complete_rows")),
                    ui.value_box("Model rows", ui.output_text("model_rows")),
                    ui.value_box("Random effects", ui.output_text("model_random_count")),
                    width=1 / 4,
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Preparation overview"), ui.output_data_frame("model_overview"), full_screen=True),
                    ui.card(ui.card_header("Variable audit"), ui.output_data_frame("model_variables"), full_screen=True),
                    col_widths=(5, 7),
                ),
                ui.card(ui.card_header("Model-ready data"), ui.output_data_frame("model_data"), full_screen=True),
                ui.layout_column_wrap(
                    ui.download_button("download_model_data", "Model data CSV"),
                    ui.download_button("download_model_variables", "Variable audit CSV"),
                    ui.download_button("download_model_script", "Python preparation script"),
                    width=1 / 3,
                ),
            ),
            ui.nav_panel(
                "Cluster permutation",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Cluster controls"),
                        ui.input_radio_buttons(
                            "cluster_mode",
                            "Workflow mode",
                            choices={"guided": "Guided", "expert": "Expert"},
                            selected="guided",
                            inline=True,
                        ),
                        ui.input_select("cluster_source", "Time-course source", choices={"": "No source available"}),
                        ui.input_select("cluster_outcome", "Numeric outcome", choices={"": "No numeric outcome"}),
                        ui.layout_columns(
                            ui.input_select("cluster_time", "Time", choices={"": "No time column"}),
                            ui.input_select("cluster_condition", "Condition", choices={"": "No condition column"}),
                            col_widths=(6, 6),
                        ),
                        ui.input_select("cluster_participant", "Participant", choices={"": "No participant column"}),
                        ui.layout_columns(
                            ui.input_select("cluster_a", "Condition A", choices={"": "Auto"}),
                            ui.input_select("cluster_b", "Condition B", choices={"": "Auto"}),
                            col_widths=(6, 6),
                        ),
                        ui.hr(),
                        ui.tags.strong("Expert controls"),
                        ui.input_checkbox("cluster_bin", "Bin time before testing", value=True),
                        ui.input_numeric("cluster_bin_width", "Time-bin width", value=0.1, min=0.000001, step=0.05),
                        ui.input_select(
                            "cluster_aggregation",
                            "Within-cell aggregation",
                            choices={"mean": "Mean", "median": "Median"},
                            selected="mean",
                        ),
                        ui.input_numeric("cluster_min_subjects", "Diagnostic participant target", value=10, min=3, step=1),
                        ui.input_numeric("cluster_permutations", "Permutations", value=1000, min=1, step=100),
                        ui.layout_columns(
                            ui.input_numeric("cluster_forming_alpha", "Cluster-forming alpha", value=0.05, min=0.0001, max=0.5, step=0.005),
                            ui.input_numeric("cluster_alpha", "Cluster alpha", value=0.05, min=0.0001, max=0.5, step=0.005),
                            col_widths=(6, 6),
                        ),
                        ui.input_select(
                            "cluster_tail",
                            "Tail",
                            choices={"two.sided": "Two-sided", "positive": "Positive", "negative": "Negative"},
                            selected="two.sided",
                        ),
                        ui.input_numeric("cluster_seed", "Random seed", value=2026, min=0, step=1),
                        ui.input_checkbox("cluster_sensitivity", "Run threshold-sensitivity analysis", value=False),
                        ui.input_task_button(
                            "run_cluster",
                            "Run Cluster Permutation",
                            label_busy="Running permutations...",
                            type="success",
                            width="100%",
                        ),
                        ui.tags.small(ui.output_text("cluster_status"), class_="text-secondary d-block mt-2"),
                    ),
                    ui.card(
                        ui.card_header("Inferential guardrail"),
                        ui.p(
                            "The current validated runner uses within-subject sign-flip permutations for exactly two conditions on a one-dimensional common time grid."
                        ),
                        ui.p(
                            "Studio first aggregates repeated participant × condition × time observations through prepare_gazepoint_timecourse_test_data(), then runs diagnose_gazepoint_cluster_design(). Error-level design failures block inference.",
                            class_="text-secondary",
                        ),
                        ui.p(
                            "A significant cluster supports cluster-level evidence against the global null over the tested time course. Its start and end times are descriptive and are not precise estimates of effect onset or offset.",
                            class_="text-secondary",
                        ),
                    ),
                    col_widths=(5, 7),
                ),
                ui.layout_column_wrap(
                    ui.value_box("Participants", ui.output_text("cluster_participants"), theme="primary"),
                    ui.value_box("Time bins", ui.output_text("cluster_time_bins")),
                    ui.value_box("Clusters", ui.output_text("cluster_count")),
                    ui.value_box("Significant clusters", ui.output_text("cluster_sig_count")),
                    width=1 / 4,
                ),
                ui.layout_columns(
                    ui.card(ui.card_header("Design checks"), ui.output_data_frame("cluster_checks"), full_screen=True),
                    ui.card(ui.card_header("Grid audit"), ui.output_data_frame("cluster_grid"), full_screen=True),
                    col_widths=(7, 5),
                ),
                ui.navset_card_tab(
                    ui.nav_panel(
                        "Result",
                        ui.card(ui.card_header("Package-native cluster plot"), ui.output_plot("cluster_plot", height="520px"), full_screen=True),
                        ui.card(ui.card_header("Cluster-level results"), ui.output_data_frame("cluster_results"), full_screen=True),
                        ui.card(ui.card_header("Package-native result statement"), ui.output_text_verbatim("cluster_report")),
                    ),
                    ui.nav_panel(
                        "Timewise",
                        ui.card(ui.card_header("Timewise statistics"), ui.output_data_frame("cluster_timewise"), full_screen=True),
                        ui.card(ui.card_header("Condition summary"), ui.output_data_frame("cluster_condition_summary"), full_screen=True),
                    ),
                    ui.nav_panel(
                        "Null distribution",
                        ui.card(ui.card_header("Maximum-cluster null distribution"), ui.output_plot("cluster_null_plot", height="480px"), full_screen=True),
                    ),
                    ui.nav_panel(
                        "Sensitivity",
                        ui.card(ui.card_header("Threshold sensitivity"), ui.output_data_frame("cluster_sensitivity_table"), full_screen=True),
                        ui.p(
                            "Sensitivity is optional because it repeats the permutation test across several cluster-forming thresholds and can be substantially more expensive.",
                            class_="text-secondary small",
                        ),
                    ),
                    ui.nav_panel(
                        "Prepared grid",
                        ui.card(ui.card_header("Participant × condition × time data"), ui.output_data_frame("cluster_prepared"), full_screen=True),
                    ),
                ),
                ui.layout_column_wrap(
                    ui.download_button("download_clusters", "Clusters CSV"),
                    ui.download_button("download_timewise", "Timewise CSV"),
                    ui.download_button("download_cluster_grid", "Prepared grid CSV"),
                    ui.download_button("download_cluster_script", "Python cluster script"),
                    width=1 / 4,
                ),
            ),
            ui.nav_panel(
                "Guardrails",
                ui.card(
                    ui.card_header("Methods intentionally not exposed"),
                    ui.output_data_frame("unsupported_methods"),
                    full_screen=True,
                ),
                ui.p(
                    "These are public package exports whose purpose is to stop unsupported analytical claims. Studio preserves those boundaries rather than presenting them as working statistical options.",
                    class_="text-secondary",
                ),
            ),
        ),
    )


@module.server
def statistics_modelling_server(input, output, session, state, global_status):
    model_status_value = reactive.Value("Ready. Choose a statistical source and prepare a model table.")
    cluster_status_value = reactive.Value("Ready. Choose a repeated-measures time-course source.")

    @reactive.effect
    def _sync_sources():
        current = state()
        choices = statistics_source_choices(current.data, current.analyses)
        model_default = _preferred_source(
            choices,
            ["multimodal_model_data", "multimodal_event_responses", "multimodal_windows", "loaded_data"],
        )
        cluster_default = _preferred_source(
            choices,
            ["multimodal_event_samples", "pupil_processed", "eda_decomposition", "gaze_processed", "loaded_data"],
        )
        ui.update_select("model_source", choices=choices or {"": "No source available"}, selected=model_default)
        ui.update_select("cluster_source", choices=choices or {"": "No source available"}, selected=cluster_default)

    @reactive.calc
    def _model_source_table():
        current = state()
        source = input.model_source()
        if current.data is None or not source:
            return None
        try:
            return statistics_source_table(current.data, current.analyses, source)
        except ValueError:
            return None

    @reactive.calc
    def _cluster_source_table():
        current = state()
        source = input.cluster_source()
        if current.data is None or not source:
            return None
        try:
            return statistics_source_table(current.data, current.analyses, source)
        except ValueError:
            return None

    @reactive.effect
    def _sync_model_columns():
        table = _model_source_table()
        numeric = numeric_column_choices(table)
        categorical = categorical_column_choices(table)
        participants = participant_column_choices(table)
        trials = trial_column_choices(table)
        all_columns = list(table.columns) if isinstance(table, pd.DataFrame) else []
        outcome_default = next(
            (c for c in ["summary_mean", "mean_value", "response_amplitude", "value", "GSR_US", "HR", "LPMM"] if c in numeric),
            numeric[0] if numeric else "",
        )
        fixed_default = [c for c in ["condition", "event_label", "modality", "signal", "aoi_label"] if c in all_columns][:2]
        ui.update_select("model_outcome", choices=_choice_dict(numeric, "No numeric outcome"), selected=outcome_default)
        ui.update_selectize("model_fixed", choices=all_columns, selected=fixed_default)
        ui.update_selectize("model_covariates", choices=numeric, selected=[])
        ui.update_select("model_participant", choices=_choice_dict(participants), selected=participants[0] if participants else "")
        ui.update_select("model_trial", choices=_choice_dict(trials), selected=trials[0] if trials else "")
        ui.update_select("model_baseline", choices=_choice_dict(numeric), selected="")
        ui.update_selectize("model_factors", choices=all_columns, selected=fixed_default)
        ui.update_selectize("model_continuous", choices=numeric, selected=[])

    @reactive.effect
    def _sync_cluster_columns():
        table = _cluster_source_table()
        numeric = numeric_column_choices(table)
        times = time_column_choices(table)
        categories = categorical_column_choices(table)
        participants = participant_column_choices(table)
        outcome_default = next(
            (c for c in ["value", "studio_eda_phasic", "GSR_US_PHASIC", "GSR_US", "HR", "LPD", "LPMM"] if c in numeric),
            numeric[0] if numeric else "",
        )
        time_default = times[0] if times else ""
        condition_default = next(
            (c for c in ["condition", "event_label"] if c in categories),
            categories[0] if categories else "",
        )
        participant_default = participants[0] if participants else ""
        ui.update_select("cluster_outcome", choices=_choice_dict(numeric, "No numeric outcome"), selected=outcome_default)
        ui.update_select("cluster_time", choices=_choice_dict(times, "No time column"), selected=time_default)
        ui.update_select("cluster_condition", choices=_choice_dict(categories, "No condition column"), selected=condition_default)
        ui.update_select("cluster_participant", choices=_choice_dict(participants, "No participant column"), selected=participant_default)

    @reactive.effect
    def _sync_condition_levels():
        table = _cluster_source_table()
        levels = condition_levels(table, input.cluster_condition())
        choices = {"": "Auto", **{level: level for level in levels}}
        ui.update_select("cluster_a", choices=choices, selected=levels[0] if len(levels) >= 1 else "")
        ui.update_select("cluster_b", choices=choices, selected=levels[1] if len(levels) >= 2 else "")

    @reactive.effect
    @reactive.event(input.run_model)
    def _run_model():
        current = state()
        table = _model_source_table()
        if current.data is None or not isinstance(table, pd.DataFrame):
            model_status_value.set("Load data and choose an available source table first.")
            return
        try:
            expert = input.model_mode() == "expert"
            fixed = list(input.model_fixed() or ())
            covariates = list(input.model_covariates() or ()) if expert else []
            factors = list(input.model_factors() or ()) if expert else [c for c in fixed if c in categorical_column_choices(table)]
            continuous = list(input.model_continuous() or ()) if expert else []
            participant = input.model_participant() or None
            trial = input.model_trial() or None
            baseline_correct = bool(input.model_baseline_correct()) if expert else False
            baseline = (input.model_baseline() or None) if baseline_correct else None
            scale = bool(input.model_scale()) if expert else False
            min_rows = int(input.model_min_rows()) if expert else 10
            result = run_lme_preparation(
                table,
                outcome_col=input.model_outcome(),
                fixed_effect_cols=fixed,
                covariate_cols=covariates,
                participant_col=participant,
                trial_col=trial,
                baseline_col=baseline,
                baseline_correct=baseline_correct,
                factor_cols=factors,
                continuous_cols=continuous,
                scale_continuous=scale,
                min_rows=min_rows,
            )
            result["source_key"] = input.model_source()
            params = {"source_key": input.model_source(), **(result.get("studio_parameters") or {})}
            state.set(current.with_analysis("statistics_model", result, parameters=params))
            overview = result.get("overview")
            rows = int(overview.iloc[0].get("model_rows", 0)) if isinstance(overview, pd.DataFrame) and not overview.empty else 0
            model_status_value.set(f"Model-data preparation complete: {rows:,} rows available for modelling.")
            global_status.set("Statistical model-data preparation complete. Review the formula, complete cases, and variable roles before fitting a model externally.")
        except Exception as exc:
            model_status_value.set(f"Model preparation failed: {exc}")
            global_status.set(f"Model preparation failed: {exc}")

    @reactive.effect
    @reactive.event(input.run_cluster)
    def _run_cluster():
        current = state()
        table = _cluster_source_table()
        if current.data is None or not isinstance(table, pd.DataFrame):
            cluster_status_value.set("Load data and choose an available time-course source first.")
            return
        try:
            expert = input.cluster_mode() == "expert"
            if expert:
                bin_width = float(input.cluster_bin_width()) if bool(input.cluster_bin()) else None
                aggregation = input.cluster_aggregation()
                min_subjects = int(input.cluster_min_subjects())
                n_permutations = int(input.cluster_permutations())
                forming_alpha = float(input.cluster_forming_alpha())
                cluster_alpha = float(input.cluster_alpha())
                tail = input.cluster_tail()
                seed = int(input.cluster_seed())
                sensitivity = bool(input.cluster_sensitivity())
            else:
                bin_width = 0.1
                aggregation = "mean"
                min_subjects = 10
                n_permutations = 1000
                forming_alpha = 0.05
                cluster_alpha = 0.05
                tail = "two.sided"
                seed = 2026
                sensitivity = False
            result = run_cluster_analysis(
                table,
                outcome_col=input.cluster_outcome(),
                time_col=input.cluster_time(),
                condition_col=input.cluster_condition(),
                participant_col=input.cluster_participant(),
                condition_a=input.cluster_a() or None,
                condition_b=input.cluster_b() or None,
                time_bin_width=bin_width,
                aggregation=aggregation,
                min_subjects=min_subjects,
                n_permutations=n_permutations,
                cluster_forming_alpha=forming_alpha,
                cluster_alpha=cluster_alpha,
                tail=tail,
                seed=seed,
                run_sensitivity=sensitivity,
            )
            result["source_key"] = input.cluster_source()
            params = {"source_key": input.cluster_source(), **(result.get("parameters") or {})}
            state.set(current.with_analysis("statistics_cluster", result, parameters=params))
            if result.get("status") == "design_blocked":
                cluster_status_value.set("Cluster inference blocked by package design diagnostics. Review the design checks and grid audit.")
                global_status.set("Cluster permutation was not run because error-level design diagnostics did not pass.")
            else:
                clusters = result.get("cluster_summary")
                n_clusters = len(clusters) if isinstance(clusters, pd.DataFrame) else 0
                cluster_status_value.set(f"Cluster permutation complete: {n_clusters} observed cluster(s).")
                global_status.set("Cluster permutation complete. Interpret cluster-level evidence and timing guardrails together.")
        except Exception as exc:
            cluster_status_value.set(f"Cluster permutation failed: {exc}")
            global_status.set(f"Cluster permutation failed: {exc}")

    @reactive.calc
    def _model_result():
        return state().analyses.get("statistics_model") if state().analyses else None

    @reactive.calc
    def _cluster_result():
        return state().analyses.get("statistics_cluster") if state().analyses else None

    @reactive.calc
    def _model_tables():
        return lme_tables(_model_result())

    @reactive.calc
    def _cluster_tables():
        return cluster_tables(_cluster_result())

    @render.data_frame
    def source_inventory():
        current = state()
        return _grid(
            statistics_source_inventory(current.data, current.analyses),
            "Load a dataset to populate statistical sources.",
            height="260px",
        )

    @render.data_frame
    def unsupported_methods():
        return render.DataGrid(unsupported_cluster_guardrails(), filters=True, height="360px")

    @render.text
    def model_status():
        return model_status_value()

    @render.text
    def model_formula():
        result = _model_result()
        if not isinstance(result, dict):
            return "Run Model Preparation to generate a package-native model formula."
        return str(result.get("model_formula") or "No formula was generated.")

    def _model_overview_value(column: str) -> str:
        table = _model_tables().get("overview")
        if not isinstance(table, pd.DataFrame) or table.empty or column not in table.columns:
            return "0"
        value = table.iloc[0][column]
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value)

    @render.text
    def model_input_rows():
        return _model_overview_value("input_rows")

    @render.text
    def model_complete_rows():
        return _model_overview_value("complete_model_rows")

    @render.text
    def model_rows():
        return _model_overview_value("model_rows")

    @render.text
    def model_random_count():
        return _model_overview_value("random_effect_count")

    @render.data_frame
    def model_overview():
        return _grid(_model_tables().get("overview"), "Run Model Preparation to inspect model readiness.")

    @render.data_frame
    def model_variables():
        return _grid(_model_tables().get("variable_summary"), "No variable audit is available.")

    @render.data_frame
    def model_data():
        return _grid(_model_tables().get("model_data"), "No model-ready table is available.", height="500px")

    @render.text
    def cluster_status():
        return cluster_status_value()

    def _cluster_setting(name: str) -> Any:
        result = _cluster_result()
        cluster = result.get("cluster") if isinstance(result, dict) else None
        settings = cluster.get("settings") if isinstance(cluster, dict) else None
        return settings.get(name) if isinstance(settings, dict) else None

    @render.text
    def cluster_participants():
        value = _cluster_setting("n_participants")
        return "0" if value is None else str(value)

    @render.text
    def cluster_time_bins():
        value = _cluster_setting("n_times")
        if value is not None:
            return str(value)
        prepared = _cluster_tables().get("prepared_data")
        return str(prepared["time"].nunique()) if isinstance(prepared, pd.DataFrame) and "time" in prepared else "0"

    @render.text
    def cluster_count():
        table = _cluster_tables().get("cluster_summary")
        return str(len(table)) if isinstance(table, pd.DataFrame) else "0"

    @render.text
    def cluster_sig_count():
        table = _cluster_tables().get("cluster_summary")
        if not isinstance(table, pd.DataFrame) or "significant" not in table.columns:
            return "0"
        return str(int(table["significant"].fillna(False).astype(bool).sum()))

    @render.data_frame
    def cluster_checks():
        return _grid(_cluster_tables().get("design_checks"), "Run Cluster Permutation to execute package design diagnostics.")

    @render.data_frame
    def cluster_grid():
        return _grid(_cluster_tables().get("grid_summary"), "No grid audit is available.")

    @render.data_frame
    def cluster_results():
        return _grid(_cluster_tables().get("cluster_summary"), "No cluster-level results are available.")

    @render.data_frame
    def cluster_timewise():
        return _grid(_cluster_tables().get("cluster_timewise"), "No timewise statistics are available.", height="480px")

    @render.data_frame
    def cluster_condition_summary():
        return _grid(_cluster_tables().get("cluster_condition_summary"), "No condition summary is available.")

    @render.data_frame
    def cluster_prepared():
        return _grid(_cluster_tables().get("prepared_data"), "No prepared participant × condition × time grid is available.", height="500px")

    @render.data_frame
    def cluster_sensitivity_table():
        return _grid(_first_table(_cluster_tables(), "sensitivity"), "Threshold sensitivity was not requested or produced.")

    @render.text
    def cluster_report():
        return cluster_report_text(_cluster_result())

    @render.plot(alt="Package-native cluster permutation time course")
    def cluster_plot():
        result = _cluster_result()
        cluster = result.get("cluster") if isinstance(result, dict) else None
        if not isinstance(cluster, dict):
            return _placeholder("Run a design-valid cluster permutation to display the time-course result.")
        return gp.plot_gazepoint_cluster_permutation(cluster)

    @render.plot(alt="Cluster permutation maximum-mass null distribution")
    def cluster_null_plot():
        result = _cluster_result()
        cluster = result.get("cluster") if isinstance(result, dict) else None
        if not isinstance(cluster, dict):
            return _placeholder("Run a design-valid cluster permutation to display the null distribution.")
        try:
            return gp.plot_gazepoint_cluster_null_distribution(cluster)
        except (ValueError, TypeError) as exc:
            return _placeholder(f"Null-distribution plot unavailable: {exc}")

    @render.download_button(filename="gpbiometricspy_model_data.csv")
    def download_model_data():
        table = _model_tables().get("model_data")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_model_variable_audit.csv")
    def download_model_variables():
        table = _model_tables().get("variable_summary")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_model_preparation.py")
    def download_model_script():
        yield lme_reproducibility_script(_model_result())

    @render.download_button(filename="gpbiometricspy_cluster_results.csv")
    def download_clusters():
        table = _cluster_tables().get("cluster_summary")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_cluster_timewise.csv")
    def download_timewise():
        table = _cluster_tables().get("cluster_timewise")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_cluster_prepared_grid.csv")
    def download_cluster_grid():
        table = _cluster_tables().get("prepared_data")
        yield (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(index=False)

    @render.download_button(filename="gpbiometricspy_cluster_reproduce.py")
    def download_cluster_script():
        yield cluster_reproducibility_script(_cluster_result())
