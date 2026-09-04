from __future__ import annotations

import json
from typing import Any

import pandas as pd
from shiny import module, reactive, render, ui

try:
    from studio.reporting_services import (
        analysis_inventory,
        annotations_frame,
        build_reporting_artifacts,
        bundle_zip_bytes,
        dataset_fingerprint,
        load_project_recipe_upload,
        manifest_json,
        project_recipe_json,
        provenance_frame,
        recipe_validation_table,
        report_markdown,
        restore_project_recipe,
        result_table_catalog,
        workflow_replay_script,
    )
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from reporting_services import (
        analysis_inventory,
        annotations_frame,
        build_reporting_artifacts,
        bundle_zip_bytes,
        dataset_fingerprint,
        load_project_recipe_upload,
        manifest_json,
        project_recipe_json,
        provenance_frame,
        recipe_validation_table,
        report_markdown,
        restore_project_recipe,
        result_table_catalog,
        workflow_replay_script,
    )


def _grid(table: pd.DataFrame | None, message: str, *, height: str = "360px"):
    if not isinstance(table, pd.DataFrame) or table.empty:
        table = pd.DataFrame({"status": [message]})
    return render.DataGrid(table, filters=True, height=height)


@module.ui
def reporting_ui():
    return ui.div(
        ui.layout_column_wrap(
            ui.value_box("Dataset fingerprint", ui.output_text("fingerprint"), theme="primary"),
            ui.value_box("Recorded operations", ui.output_text("operation_count")),
            ui.value_box("Stored analyses", ui.output_text("analysis_count")),
            ui.value_box("Result tables", ui.output_text("result_table_count")),
            width=1 / 4,
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Build reporting artifacts"),
                ui.input_text("report_title", "Report title", value="gpbiometricspy Studio analysis report"),
                ui.input_text("report_subtitle", "Subtitle", value=""),
                ui.input_task_button(
                    "build_report",
                    "Build Report Artifacts",
                    label_busy="Building reporting artifacts...",
                    type="success",
                    width="100%",
                ),
                ui.tags.small(ui.output_text("report_status"), class_="text-secondary d-block mt-2"),
            ),
            ui.card(
                ui.card_header("Privacy-preserving project model"),
                ui.p(
                    "Studio project files are metadata recipes, not copies of biometric datasets. They contain a SHA-256 dataset fingerprint, schema, annotations, provenance, analysis inventory, and recorded parameters."
                ),
                ui.p(
                    "Raw rows and cached analysis-result tables are intentionally excluded. To restore a recipe, load the source dataset separately; Studio blocks restoration unless its fingerprint matches exactly.",
                    class_="text-secondary",
                ),
                ui.p(
                    "This makes the project file useful for reproducibility without turning the application into an unannounced biometric-data store.",
                    class_="text-secondary",
                ),
            ),
            col_widths=(5, 7),
        ),
        ui.navset_card_tab(
            ui.nav_panel(
                "Report",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Package report status"),
                        ui.output_data_frame("package_report_overview"),
                        full_screen=True,
                    ),
                    ui.card(
                        ui.card_header("Reproducibility identity"),
                        ui.output_text_verbatim("identity_summary"),
                    ),
                    col_widths=(7, 5),
                ),
                ui.card(
                    ui.card_header("Studio report preview"),
                    ui.output_text_verbatim("report_preview"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Methods & reproducibility",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Package-native methods text"),
                        ui.output_text_verbatim("methods_text"),
                        full_screen=True,
                    ),
                    ui.card(
                        ui.card_header("Package-native reproducibility statement"),
                        ui.output_text_verbatim("reproducibility_text"),
                        full_screen=True,
                    ),
                    col_widths=(6, 6),
                ),
                ui.card(
                    ui.card_header("QC/reporting supplement"),
                    ui.output_text_verbatim("qc_supplement"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Inventory",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Analysis inventory"),
                        ui.output_data_frame("analysis_inventory"),
                        full_screen=True,
                    ),
                    ui.card(
                        ui.card_header("Result-table catalogue"),
                        ui.output_data_frame("result_catalog"),
                        full_screen=True,
                    ),
                    col_widths=(5, 7),
                ),
                ui.navset_card_tab(
                    ui.nav_panel("Provenance", ui.output_data_frame("provenance")),
                    ui.nav_panel("Annotations", ui.output_data_frame("annotations")),
                ),
            ),
            ui.nav_panel(
                "Manifest",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Manifest preview"),
                        ui.output_text_verbatim("manifest_preview"),
                        full_screen=True,
                    ),
                    ui.card(
                        ui.card_header("Replay policy"),
                        ui.p(
                            "The generated Python script verifies the dataset fingerprint before replay and uses the recorded Studio analysis parameters."
                        ),
                        ui.p(
                            "External event files, secondary streams, or other resources are never embedded silently. Where a workflow depended on them, the replay script marks that dependency explicitly.",
                            class_="text-secondary",
                        ),
                        ui.output_text_verbatim("replay_summary"),
                    ),
                    col_widths=(8, 4),
                ),
            ),
            ui.nav_panel(
                "Project recipe",
                ui.layout_columns(
                    ui.card(
                        ui.card_header("Save project recipe"),
                        ui.p(
                            "Download session metadata and analysis parameters without raw biometric samples. Analysis outputs are deliberately recomputed rather than restored from a cache."
                        ),
                        ui.download_button("download_recipe", "Download Project Recipe JSON", class_="btn-primary w-100"),
                    ),
                    ui.card(
                        ui.card_header("Restore project recipe"),
                        ui.input_file(
                            "recipe_upload",
                            "Project recipe JSON",
                            accept=[".json", "application/json"],
                            multiple=False,
                        ),
                        ui.layout_columns(
                            ui.input_action_button("validate_recipe", "Validate Recipe", class_="btn-outline-primary w-100"),
                            ui.input_action_button("restore_recipe", "Restore Metadata", class_="btn-outline-success w-100"),
                            col_widths=(6, 6),
                        ),
                        ui.tags.small(ui.output_text("recipe_status"), class_="text-secondary d-block mt-2"),
                    ),
                    col_widths=(5, 7),
                ),
                ui.card(
                    ui.card_header("Recipe validation checks"),
                    ui.output_data_frame("recipe_checks"),
                    full_screen=True,
                ),
            ),
            ui.nav_panel(
                "Downloads",
                ui.p(
                    "The report bundle contains report-ready summaries, QC/reporting tables, methods text, reproducibility statement, manifest, recipe, and replay script. It intentionally excludes the loaded raw biometric table.",
                    class_="text-secondary",
                ),
                ui.layout_column_wrap(
                    ui.download_button("download_bundle", "Report Bundle ZIP"),
                    ui.download_button("download_report", "Report Markdown"),
                    ui.download_button("download_methods", "Methods TXT"),
                    ui.download_button("download_repro", "Reproducibility TXT"),
                    ui.download_button("download_manifest", "Manifest JSON"),
                    ui.download_button("download_replay", "Replay Python Script"),
                    width=1 / 3,
                ),
            ),
        ),
    )


@module.server
def reporting_server(input, output, session, state, global_status):
    artifacts_value: reactive.Value[Any] = reactive.Value(None)
    recipe_value: reactive.Value[Any] = reactive.Value(None)
    recipe_checks_value: reactive.Value[Any] = reactive.Value(None)
    report_status_value = reactive.Value("Ready. Load data, run the desired workflows, then build reporting artifacts.")
    recipe_status_value = reactive.Value("No project recipe loaded.")
    dataset_identity_value: reactive.Value[Any] = reactive.Value(None)

    @reactive.effect
    def _invalidate_when_dataset_changes():
        current = state()
        identity = (current.source_name, current.loaded_at, current.n_rows, current.n_columns)
        if dataset_identity_value() != identity:
            dataset_identity_value.set(identity)
            artifacts_value.set(None)
            recipe_value.set(None)
            recipe_checks_value.set(None)

    def _artifact_or_build() -> dict[str, Any]:
        current = state()
        existing = artifacts_value()
        if existing is not None:
            return existing
        return build_reporting_artifacts(
            current,
            title=input.report_title(),
            subtitle=input.report_subtitle() or None,
        )

    @reactive.effect
    @reactive.event(input.build_report)
    def _build_report():
        current = state()
        if current.data is None:
            report_status_value.set("Load a dataset before building reporting artifacts.")
            return
        try:
            recorded = current.with_operation(
                "build_reporting_artifacts",
                report_title=input.report_title(),
                report_subtitle=input.report_subtitle() or None,
                raw_data_embedded=False,
            )
            artifacts = build_reporting_artifacts(
                recorded,
                title=input.report_title(),
                subtitle=input.report_subtitle() or None,
            )
            state.set(recorded)
            artifacts_value.set(artifacts)
            report_status_value.set("Reporting artifacts built through public gpbiometricspy reporting APIs.")
            global_status.set("Reporting artifacts complete. Review methods, manifest, project recipe, and downloads.")
        except Exception as exc:
            report_status_value.set(f"Reporting failed: {exc}")

    @reactive.effect
    @reactive.event(input.validate_recipe)
    def _validate_recipe():
        try:
            recipe = load_project_recipe_upload(input.recipe_upload())
            checks = recipe_validation_table(recipe, state().data)
            recipe_value.set(recipe)
            recipe_checks_value.set(checks)
            if bool(checks["passed"].all()):
                recipe_status_value.set("Recipe valid and dataset fingerprint matches. Metadata can be restored.")
            else:
                failed = ", ".join(checks.loc[~checks["passed"], "check"].astype(str))
                recipe_status_value.set(f"Recipe validation did not pass: {failed}.")
        except Exception as exc:
            recipe_value.set(None)
            recipe_checks_value.set(None)
            recipe_status_value.set(f"Recipe validation failed: {exc}")

    @reactive.effect
    @reactive.event(input.restore_recipe)
    def _restore_recipe():
        current = state()
        if current.data is None:
            recipe_status_value.set("Load the source dataset before restoring project metadata.")
            return
        try:
            recipe = recipe_value() or load_project_recipe_upload(input.recipe_upload())
            restored = restore_project_recipe(current, recipe)
            checks = recipe_validation_table(recipe, restored.data)
            state.set(restored)
            artifacts_value.set(None)
            recipe_value.set(recipe)
            recipe_checks_value.set(checks)
            recipe_status_value.set(
                "Project metadata restored. Analysis outputs were intentionally not restored; rerun analyses or use the replay script."
            )
            global_status.set("Project recipe restored after exact dataset fingerprint verification.")
        except Exception as exc:
            recipe_status_value.set(f"Project restore blocked: {exc}")

    @render.text
    def fingerprint():
        data = state().data
        if data is None:
            return "—"
        return dataset_fingerprint(data)[:16] + "…"

    @render.text
    def operation_count():
        return str(len(state().provenance))

    @render.text
    def analysis_count():
        return str(len(state().analyses))

    @render.text
    def result_table_count():
        return str(len(result_table_catalog(state().analyses)))

    @render.text
    def report_status():
        return report_status_value()

    @render.text
    def recipe_status():
        return recipe_status_value()

    @render.data_frame
    def package_report_overview():
        artifacts = artifacts_value()
        if artifacts is None:
            return _grid(None, "Build reporting artifacts to create the package report.")
        overview = artifacts["report"].get("overview")
        return _grid(overview, "Package report did not expose an overview table.")

    @render.text
    def identity_summary():
        current = state()
        if current.data is None:
            return "No dataset loaded."
        return (
            f"Dataset: {current.source_name}\n"
            f"SHA-256: {dataset_fingerprint(current.data)}\n"
            f"Rows: {current.n_rows:,}\n"
            f"Columns: {current.n_columns:,}\n"
            f"Operations: {len(current.provenance)}\n"
            f"Analyses: {len(current.analyses)}\n"
            f"Annotations: {len(current.annotations)}\n"
            "Raw rows embedded in recipe: False\n"
            "Analysis outputs embedded in recipe: False"
        )

    @render.text
    def report_preview():
        artifacts = artifacts_value()
        if artifacts is None:
            return "Build reporting artifacts to generate the report preview."
        return report_markdown(artifacts)

    @render.text
    def methods_text():
        artifacts = artifacts_value()
        return "Build reporting artifacts first." if artifacts is None else str(artifacts["methods_text"])

    @render.text
    def reproducibility_text():
        artifacts = artifacts_value()
        return "Build reporting artifacts first." if artifacts is None else str(artifacts["reproducibility"])

    @render.text
    def qc_supplement():
        artifacts = artifacts_value()
        return "Build reporting artifacts first." if artifacts is None else str(artifacts["qc_supplement"])

    @render.data_frame
    def analysis_inventory():
        return _grid(analysis_inventory(state().analyses), "No analysis results are stored in this session.")

    @render.data_frame
    def result_catalog():
        return _grid(result_table_catalog(state().analyses), "No analysis result tables are stored in this session.")

    @render.data_frame
    def provenance():
        return _grid(provenance_frame(state()), "No provenance operations have been recorded.", height="430px")

    @render.data_frame
    def annotations():
        return _grid(annotations_frame(state()), "No manual annotations have been recorded.")

    @render.text
    def manifest_preview():
        artifacts = artifacts_value()
        if artifacts is None:
            return "Build reporting artifacts to generate the manifest."
        text = manifest_json(artifacts)
        return text if len(text) <= 16000 else text[:16000] + "\n… preview truncated; download the complete manifest JSON."

    @render.text
    def replay_summary():
        current = state()
        if current.data is None:
            return "No dataset loaded."
        script = workflow_replay_script(current)
        return (
            f"Replay script lines: {len(script.splitlines())}\n"
            f"Recorded analysis workflows: {len(current.analyses)}\n"
            f"Fingerprint gate: {dataset_fingerprint(current.data)[:16]}…\n"
            "Source data embedded: False"
        )

    @render.data_frame
    def recipe_checks():
        return _grid(recipe_checks_value(), "Validate a project recipe to see restore checks.")

    @render.download_button(filename="gpbiometricspy_studio_project_recipe.json")
    def download_recipe():
        yield project_recipe_json(state())

    @render.download_button(filename="gpbiometricspy_studio_report_bundle.zip")
    def download_bundle():
        artifacts = _artifact_or_build()
        yield bundle_zip_bytes(artifacts, state())

    @render.download_button(filename="gpbiometricspy_studio_report.md")
    def download_report():
        yield report_markdown(_artifact_or_build())

    @render.download_button(filename="gpbiometricspy_studio_methods.txt")
    def download_methods():
        yield str(_artifact_or_build()["methods_text"])

    @render.download_button(filename="gpbiometricspy_studio_reproducibility.txt")
    def download_repro():
        yield str(_artifact_or_build()["reproducibility"])

    @render.download_button(filename="gpbiometricspy_studio_manifest.json")
    def download_manifest():
        yield manifest_json(_artifact_or_build())

    @render.download_button(filename="gpbiometricspy_studio_replay.py")
    def download_replay():
        yield workflow_replay_script(state())
