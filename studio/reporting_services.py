from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import io
import inspect
import json
from pathlib import Path
import platform
import tempfile
from typing import Any, Iterable
import zipfile

from matplotlib.figure import Figure
import pandas as pd

import gpbiometricspy as gp

try:
    from studio.state import ProjectState
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from state import ProjectState


PROJECT_RECIPE_SCHEMA = "gpbiometricspy-studio-project-recipe"
PROJECT_RECIPE_VERSION = 1
MAX_PROJECT_RECIPE_BYTES = 5 * 1024 * 1024
REPOSITORY_URL = "https://github.com/stefanosbalaskas/gpbiometricspy"


def dataset_fingerprint(data: pd.DataFrame) -> str:
    """Return a deterministic SHA-256 identity without exposing raw values."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    digest = sha256()
    metadata = {
        "rows": len(data),
        "columns": [str(c) for c in data.columns],
        "dtypes": [str(dtype) for dtype in data.dtypes],
    }
    digest.update(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    try:
        hashed = pd.util.hash_pandas_object(data, index=True, categorize=True)
    except (TypeError, ValueError):
        hashed = pd.util.hash_pandas_object(data.astype(str), index=True, categorize=True)
    digest.update(hashed.to_numpy().tobytes())
    return digest.hexdigest()


def provenance_frame(state: ProjectState) -> pd.DataFrame:
    rows = [dict(row) for row in state.provenance]
    if not rows:
        return pd.DataFrame(columns=["timestamp_utc", "operation", "source", "n_rows", "n_columns", "status"])
    return pd.DataFrame(rows)


def annotations_frame(state: ProjectState) -> pd.DataFrame:
    rows = [dict(row) for row in state.annotations]
    if not rows:
        return pd.DataFrame(columns=["annotation_type", "signal_col", "time_col", "time", "start", "end", "note"])
    return pd.DataFrame(rows)


def _walk_objects(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            yield from _walk_objects(item, child)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            child = f"{path}[{index}]"
            yield from _walk_objects(item, child)
        return
    yield path, value


def result_table_catalog(analyses: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for analysis, result in analyses.items():
        for path, value in _walk_objects(result, str(analysis)):
            if isinstance(value, pd.DataFrame):
                rows.append(
                    {
                        "analysis": str(analysis),
                        "result_path": path,
                        "rows": len(value),
                        "columns": len(value.columns),
                    }
                )
    return pd.DataFrame(rows, columns=["analysis", "result_path", "rows", "columns"])


def analysis_inventory(analyses: dict[str, Any]) -> pd.DataFrame:
    table_catalog = result_table_catalog(analyses)
    rows: list[dict[str, Any]] = []
    for name, result in analyses.items():
        tables = table_catalog.loc[table_catalog["analysis"] == str(name)] if not table_catalog.empty else table_catalog
        figure_count = sum(isinstance(value, Figure) for _, value in _walk_objects(result, str(name)))
        parameters = {}
        if isinstance(result, dict):
            candidate = result.get("parameters") or result.get("studio_parameters") or {}
            if isinstance(candidate, dict):
                parameters = candidate
        status = None
        if isinstance(result, dict):
            status = result.get("status")
            overview = result.get("overview")
            if status is None and isinstance(overview, pd.DataFrame) and not overview.empty and "status" in overview:
                status = overview.iloc[0]["status"]
        rows.append(
            {
                "analysis": str(name),
                "status": "stored" if status is None else str(status),
                "table_count": len(tables),
                "table_rows_total": int(tables["rows"].sum()) if not tables.empty else 0,
                "figure_count": figure_count,
                "parameter_keys": ", ".join(sorted(map(str, parameters.keys()))),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["analysis", "status", "table_count", "table_rows_total", "figure_count", "parameter_keys"],
    )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return {
            "__type__": "dataframe_descriptor",
            "rows": len(value),
            "columns": [str(c) for c in value.columns],
        }
    if isinstance(value, pd.Series):
        return {"__type__": "series_descriptor", "length": len(value), "name": str(value.name)}
    if isinstance(value, Figure):
        return {"__type__": "matplotlib_figure"}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)


def _record_dicts(table: pd.DataFrame) -> list[dict[str, Any]]:
    if table.empty:
        return []
    return [_json_safe(record) for record in table.to_dict(orient="records")]


def project_recipe(state: ProjectState) -> dict[str, Any]:
    if state.data is None:
        raise ValueError("Load a dataset before creating a project recipe.")
    fingerprint = dataset_fingerprint(state.data)
    return {
        "schema": PROJECT_RECIPE_SCHEMA,
        "schema_version": PROJECT_RECIPE_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "gpbiometricspy_version": gp.__version__,
        "python_version": platform.python_version(),
        "source_name": state.source_name,
        "loaded_at": state.loaded_at,
        "dataset": {
            "sha256": fingerprint,
            "row_count": state.n_rows,
            "column_count": state.n_columns,
            "columns": [
                {"name": str(name), "dtype": str(dtype)} for name, dtype in zip(state.data.columns, state.data.dtypes)
            ],
        },
        "annotations": _json_safe(list(state.annotations)),
        "provenance": _json_safe(list(state.provenance)),
        "analysis_inventory": _record_dicts(analysis_inventory(state.analyses)),
        "result_table_catalog": _record_dicts(result_table_catalog(state.analyses)),
        "raw_data_included": False,
        "analysis_outputs_included": False,
        "restore_policy": (
            "Load the source dataset separately. Studio verifies its SHA-256 fingerprint before restoring annotations and "
            "provenance. Analysis outputs are intentionally not restored and must be recomputed."
        ),
    }


def project_recipe_json(state: ProjectState) -> str:
    return json.dumps(project_recipe(state), indent=2, sort_keys=True, ensure_ascii=False)


def _validate_recipe_shape(recipe: dict[str, Any]) -> None:
    if not isinstance(recipe, dict):
        raise TypeError("Project recipe must decode to a JSON object.")
    if recipe.get("schema") != PROJECT_RECIPE_SCHEMA:
        raise ValueError("The uploaded JSON is not a gpbiometricspy Studio project recipe.")
    if int(recipe.get("schema_version", -1)) != PROJECT_RECIPE_VERSION:
        raise ValueError("Unsupported Studio project recipe schema version.")
    dataset = recipe.get("dataset")
    if not isinstance(dataset, dict) or not dataset.get("sha256"):
        raise ValueError("Project recipe is missing its dataset fingerprint.")
    if recipe.get("raw_data_included") is not False:
        raise ValueError("Refusing a project recipe that claims to embed raw data.")


def load_project_recipe(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        recipe = source
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Project recipe not found: {path}")
        if path.suffix.lower() != ".json":
            raise ValueError("Studio project recipes must use the .json extension.")
        if path.stat().st_size > MAX_PROJECT_RECIPE_BYTES:
            raise ValueError("The Studio project recipe exceeds the 5 MB metadata limit.")
        recipe = json.loads(path.read_text(encoding="utf-8"))
    _validate_recipe_shape(recipe)
    return recipe


def load_project_recipe_upload(file_info: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not file_info:
        raise ValueError("Choose a Studio project recipe JSON file first.")
    if len(file_info) != 1:
        raise ValueError("Upload exactly one project recipe.")
    info = file_info[0]
    name = str(info.get("name") or "project_recipe.json")
    if Path(name).suffix.lower() != ".json":
        raise ValueError("Studio project recipes must use the .json extension.")
    size = info.get("size")
    if size is not None and int(size) > MAX_PROJECT_RECIPE_BYTES:
        raise ValueError("The Studio project recipe exceeds the 5 MB metadata limit.")
    datapath = info.get("datapath")
    if not datapath:
        raise ValueError("The project upload did not provide a readable temporary file path.")
    return load_project_recipe(datapath)


def recipe_validation_table(recipe: dict[str, Any], data: pd.DataFrame | None) -> pd.DataFrame:
    _validate_recipe_shape(recipe)
    expected = str(recipe["dataset"]["sha256"])
    checks = [
        {"check": "recognized_schema", "passed": True, "detail": PROJECT_RECIPE_SCHEMA},
        {"check": "raw_data_absent", "passed": recipe.get("raw_data_included") is False, "detail": "required"},
        {
            "check": "analysis_outputs_absent",
            "passed": recipe.get("analysis_outputs_included") is False,
            "detail": "recompute analyses after restore",
        },
    ]
    if data is None:
        checks.append({"check": "source_dataset_loaded", "passed": False, "detail": "load source data before restore"})
        checks.append({"check": "dataset_fingerprint_match", "passed": False, "detail": "not checked"})
    else:
        observed = dataset_fingerprint(data)
        checks.append({"check": "source_dataset_loaded", "passed": True, "detail": f"{len(data):,} rows"})
        checks.append(
            {
                "check": "dataset_fingerprint_match",
                "passed": observed == expected,
                "detail": f"expected {expected[:12]}…; observed {observed[:12]}…",
            }
        )
    return pd.DataFrame(checks)


def restore_project_recipe(state: ProjectState, recipe: dict[str, Any]) -> ProjectState:
    if state.data is None:
        raise ValueError("Load the source dataset before restoring a project recipe.")
    checks = recipe_validation_table(recipe, state.data)
    if not bool(checks["passed"].all()):
        failed = ", ".join(checks.loc[~checks["passed"], "check"].astype(str))
        raise ValueError(f"Project recipe restore blocked: {failed}.")
    return state.with_restored_session_metadata(
        annotations=recipe.get("annotations") or (),
        provenance=recipe.get("provenance") or (),
        recipe_fingerprint=str(recipe["dataset"]["sha256"]),
    )


def _decision_log(state: ProjectState) -> dict[str, pd.DataFrame]:
    provenance = provenance_frame(state)
    if provenance.empty:
        decisions = pd.DataFrame(columns=["stage", "decision", "rationale", "timestamp_utc"])
    else:
        decisions = pd.DataFrame(
            {
                "stage": provenance["operation"].astype(str),
                "decision": provenance["operation"].astype(str),
                "rationale": "Recorded automatically by gpbiometricspy Studio provenance.",
                "timestamp_utc": provenance.get("timestamp_utc", pd.Series([None] * len(provenance))),
            }
        )
    return {"decisions": decisions}


def _report_tables_from_objects(checklist: dict[str, Any], report: dict[str, Any], state: ProjectState) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {
        "studio_analysis_inventory": analysis_inventory(state.analyses),
        "studio_result_table_catalog": result_table_catalog(state.analyses),
        "studio_provenance": provenance_frame(state),
        "studio_annotations": annotations_frame(state),
    }
    for prefix, obj in (("checklist", checklist), ("report", report.get("tables", {}))):
        if not isinstance(obj, dict):
            continue
        for key, value in obj.items():
            if isinstance(value, pd.DataFrame):
                tables[f"{prefix}_{key}"] = value.copy()
    return tables


def _manifest(state: ProjectState, fingerprint: str) -> dict[str, Any]:
    outputs = {name: "Studio analysis result; recompute from source data and recorded parameters" for name in state.analyses}
    manifest = gp.create_gazepoint_analysis_manifest(
        files=None,
        settings={
            "studio": "gpbiometricspy Studio",
            "dataset_sha256": fingerprint,
            "dataset_rows": state.n_rows,
            "dataset_columns": state.n_columns,
            "analysis_names": list(state.analyses),
            "operation_count": len(state.provenance),
            "annotation_count": len(state.annotations),
        },
        outputs=outputs,
        exclusions=None,
        include_session=True,
    )
    if not isinstance(manifest, dict):
        raise TypeError("create_gazepoint_analysis_manifest() returned an unexpected object.")
    return manifest


def build_reporting_artifacts(
    state: ProjectState,
    *,
    title: str = "gpbiometricspy Studio analysis report",
    subtitle: str | None = None,
    repository_url: str | None = REPOSITORY_URL,
) -> dict[str, Any]:
    """Compose report artifacts through public gpbiometricspy reporting contracts."""
    if state.data is None:
        raise ValueError("Load a dataset before building reporting artifacts.")
    clean_title = str(title).strip()
    if not clean_title:
        raise ValueError("Report title must be non-empty.")
    clean_subtitle = None if subtitle is None or not str(subtitle).strip() else str(subtitle).strip()
    fingerprint = dataset_fingerprint(state.data)
    checklist = gp.create_gazepoint_biometrics_checklist(state.data, require_active_signal=False)
    methods_text = gp.create_gazepoint_biometrics_methods_text(checklist=checklist, include_cautions=True)
    decision_log = _decision_log(state)
    validation = {
        "studio_dataset_sha256": fingerprint,
        "studio_rows": state.n_rows,
        "studio_columns": state.n_columns,
        "studio_operations": len(state.provenance),
        "studio_analyses": len(state.analyses),
    }
    reproducibility = gp.create_gazepoint_reproducibility_statement(
        decision_log=decision_log,
        package_version=gp.__version__,
        repository_url=repository_url,
        validation=validation,
        data_statement=(
            "gpbiometricspy Studio project recipes do not embed raw biometric rows or cached analysis-result tables. "
            "Reproduction requires the separately managed source dataset and a matching SHA-256 fingerprint."
        ),
        include_guardrails=True,
    )
    methods_section = gp.create_gazepoint_methods_section(
        decision_log=decision_log,
        package_version=gp.__version__,
        validation=validation,
        include_guardrails=True,
    )
    qc_supplement = gp.create_gazepoint_qc_supplement(
        decision_log=decision_log,
        title="gpbiometricspy Studio workflow quality-control supplement",
    )
    report = gp.create_gazepoint_biometrics_report(
        data=state.data,
        methods_text=methods_text,
        checklist=checklist,
        title=clean_title,
        subtitle=clean_subtitle,
        format="markdown",
        include_timestamp=False,
    )
    if not isinstance(report, dict):
        raise TypeError("create_gazepoint_biometrics_report() returned an unexpected object.")
    manifest = _manifest(state, fingerprint)
    tables = _report_tables_from_objects(checklist, report, state)
    recipe = project_recipe(state)
    text = {
        "methods": str(methods_text),
        "methods_section": str(methods_section),
        "reproducibility": str(reproducibility),
        "qc_supplement": str(qc_supplement),
    }
    return {
        "title": clean_title,
        "subtitle": clean_subtitle,
        "dataset_fingerprint": fingerprint,
        "checklist": checklist,
        "methods_text": methods_text,
        "methods_section": methods_section,
        "reproducibility": reproducibility,
        "qc_supplement": qc_supplement,
        "report": report,
        "manifest": manifest,
        "tables": tables,
        "text": text,
        "recipe": recipe,
    }


def _table_text(table: pd.DataFrame, max_rows: int = 30) -> str:
    if not isinstance(table, pd.DataFrame) or table.empty:
        return "<no rows>"
    return table.head(max_rows).to_string(index=False)


def report_markdown(artifacts: dict[str, Any]) -> str:
    inventory = artifacts["tables"].get("studio_analysis_inventory", pd.DataFrame())
    catalog = artifacts["tables"].get("studio_result_table_catalog", pd.DataFrame())
    lines = [f"# {artifacts['title']}"]
    if artifacts.get("subtitle"):
        lines += ["", str(artifacts["subtitle"])]
    lines += [
        "",
        "## Reproducibility identity",
        "",
        f"- gpbiometricspy version: `{gp.__version__}`",
        f"- dataset SHA-256: `{artifacts['dataset_fingerprint']}`",
        f"- raw data embedded in project recipe: `False`",
        f"- cached analysis outputs embedded in project recipe: `False`",
        "",
        "## Package-native methods text",
        "",
        str(artifacts["methods_text"]),
        "",
        "## Reproducibility statement",
        "",
        str(artifacts["reproducibility"]),
        "",
        "## Studio analysis inventory",
        "",
        "```text",
        _table_text(inventory),
        "```",
        "",
        "## Stored result-table catalogue",
        "",
        "```text",
        _table_text(catalog),
        "```",
        "",
        "## Interpretation guardrail",
        "",
        "Derived biometric, gaze, pupil, event-locked, and statistical outputs remain measurement and workflow products. "
        "They do not by themselves establish emotion, stress, trust, cognition, preference, health status, diagnosis, mechanism, or precise temporal onset.",
    ]
    return "\n".join(lines).strip() + "\n"


def manifest_json(artifacts: dict[str, Any]) -> str:
    payload = {
        "studio": {
            "dataset_sha256": artifacts["dataset_fingerprint"],
            "gpbiometricspy_version": gp.__version__,
            "python_version": platform.python_version(),
            "raw_data_included": False,
            "analysis_outputs_included": False,
        },
        "package_manifest": _json_safe(artifacts["manifest"]),
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _latest_analysis_parameters(state: ProjectState) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for event in state.provenance:
        analysis = event.get("analysis")
        if not analysis:
            continue
        raw = event.get("parameters_json") or "{}"
        try:
            params = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            params = {}
        rows.append((str(analysis), params if isinstance(params, dict) else {}))
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for analysis, params in rows:
        if analysis not in latest:
            order.append(analysis)
        latest[analysis] = params
    return [(analysis, latest[analysis]) for analysis in order]


def workflow_replay_script(state: ProjectState) -> str:
    if state.data is None:
        raise ValueError("Load a dataset before generating a replay script.")
    fingerprint = dataset_fingerprint(state.data)
    plans = _latest_analysis_parameters(state)
    imports = {
        "eda_scr": "from studio.services import run_eda_scr_analysis",
        "ppg_hr_hrv": "from studio.ppg_services import run_ppg_hr_hrv_analysis",
        "pupil": "from studio.pupil_services import run_pupil_analysis",
        "gaze": "from studio.gaze_services import run_gaze_analysis",
        "event_alignment": "from studio.event_alignment_services import run_event_alignment",
        "multimodal": "from studio.multimodal_services import run_multimodal_analysis",
        "statistics_model": "from studio.statistics_services import run_lme_preparation, statistics_source_table",
        "statistics_cluster": "from studio.statistics_services import run_cluster_analysis, statistics_source_table",
    }
    selected_imports = []
    for name, _ in plans:
        line = imports.get(name)
        if line and line not in selected_imports:
            selected_imports.append(line)
    lines = [
        "from __future__ import annotations",
        "",
        "import inspect",
        "from pathlib import Path",
        "",
        "import gpbiometricspy as gp",
        "from studio.reporting_services import dataset_fingerprint",
        *selected_imports,
        "",
        "# Set this to the separately managed source Gazepoint CSV/TXT before running.",
        'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")',
        f'EXPECTED_SHA256 = "{fingerprint}"',
        "",
        "def call_filtered(function, *args, **parameters):",
        "    allowed = inspect.signature(function).parameters",
        "    clean = {key: value for key, value in parameters.items() if key in allowed}",
        "    return function(*args, **clean)",
        "",
        "data = gp.import_gazepoint_biometrics(DATA_PATH)",
        "observed = dataset_fingerprint(data)",
        "if observed != EXPECTED_SHA256:",
        '    raise RuntimeError(f"Dataset fingerprint mismatch: expected {EXPECTED_SHA256}, observed {observed}")',
        "",
        "analyses = {}",
    ]
    for analysis, params in plans:
        payload = repr(_json_safe(params))
        lines += ["", f"# Replay Studio analysis: {analysis}", f"parameters = {payload}"]
        if analysis == "eda_scr":
            lines.append('analyses["eda_scr"] = call_filtered(run_eda_scr_analysis, data, **parameters)')
        elif analysis == "ppg_hr_hrv":
            lines.append('analyses["ppg_hr_hrv"] = call_filtered(run_ppg_hr_hrv_analysis, data, **parameters)')
        elif analysis == "pupil":
            lines.append('analyses["pupil"] = call_filtered(run_pupil_analysis, data, **parameters)')
        elif analysis == "gaze":
            lines.append('analyses["gaze"] = call_filtered(run_gaze_analysis, data, **parameters)')
        elif analysis == "event_alignment":
            lines += [
                "# External event files/target streams are not embedded in the project recipe.",
                "# If this workflow used external resources, provide them explicitly before replay.",
                'analyses["event_alignment"] = call_filtered(run_event_alignment, data, **parameters)',
            ]
        elif analysis == "multimodal":
            lines.append('analyses["multimodal"] = call_filtered(run_multimodal_analysis, data, analyses, **parameters)')
        elif analysis == "statistics_model":
            lines += [
                'source_key = parameters.pop("source_key", "loaded_data")',
                "table = statistics_source_table(data, analyses, source_key)",
                'analyses["statistics_model"] = call_filtered(run_lme_preparation, table, **parameters)',
            ]
        elif analysis == "statistics_cluster":
            lines += [
                'source_key = parameters.pop("source_key", "loaded_data")',
                "table = statistics_source_table(data, analyses, source_key)",
                'analyses["statistics_cluster"] = call_filtered(run_cluster_analysis, table, **parameters)',
            ]
        else:
            lines.append(f'# No automatic Studio replay adapter is registered for "{analysis}"; rerun it explicitly.')
    lines += [
        "",
        "checklist = gp.create_gazepoint_biometrics_checklist(data, require_active_signal=False)",
        "methods = gp.create_gazepoint_biometrics_methods_text(checklist=checklist, include_cautions=True)",
        "print(methods)",
        "",
    ]
    return "\n".join(lines)


def bundle_zip_bytes(artifacts: dict[str, Any], state: ProjectState) -> bytes:
    """Create an in-memory ZIP; raw biometric rows are intentionally excluded."""
    with tempfile.TemporaryDirectory(prefix="gpbiometricspy-studio-report-") as tmp:
        root = Path(tmp) / "report_bundle"
        root.mkdir(parents=True, exist_ok=True)
        gp.export_gazepoint_biometrics_report_bundle(
            output_dir=root,
            prefix="gpbiometricspy_studio",
            tables=artifacts["tables"],
            text=artifacts["text"],
            include_readme=True,
            include_session_info=True,
            overwrite=True,
        )
        (root / "gpbiometricspy_studio_report.md").write_text(report_markdown(artifacts), encoding="utf-8")
        (root / "gpbiometricspy_studio_manifest.json").write_text(manifest_json(artifacts), encoding="utf-8")
        (root / "gpbiometricspy_studio_project_recipe.json").write_text(
            json.dumps(artifacts["recipe"], indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        (root / "gpbiometricspy_studio_replay.py").write_text(workflow_replay_script(state), encoding="utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(root))
        return buffer.getvalue()


def callable_accepts(function: Any, parameter: str) -> bool:
    """Small testable helper used by replay-generation hardening."""
    return parameter in inspect.signature(function).parameters
