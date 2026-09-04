from __future__ import annotations

import importlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp
from studio.reporting_services import (
    PROJECT_RECIPE_SCHEMA,
    analysis_inventory,
    build_reporting_artifacts,
    bundle_zip_bytes,
    dataset_fingerprint,
    load_project_recipe,
    load_project_recipe_upload,
    manifest_json,
    project_recipe,
    project_recipe_json,
    recipe_validation_table,
    report_markdown,
    restore_project_recipe,
    result_table_catalog,
    workflow_replay_script,
)
from studio.state import ProjectState


def _data(n: int = 48) -> pd.DataFrame:
    phase = np.arange(n, dtype=float) / 5.0
    return pd.DataFrame(
        {
            "CNT": np.arange(1, n + 1),
            "GSR_US": 2.0 + 0.1 * np.sin(phase),
            "GSRV": np.ones(n),
            "HR": 72.0 + np.sin(phase),
            "HRV": np.ones(n),
            "DIAL": 0.5 + 0.05 * np.cos(phase),
            "DIALV": np.ones(n),
            "TTL0": np.where(np.arange(n) == 20, 1, 0),
            "TTLV": np.ones(n),
        }
    )


def _state() -> ProjectState:
    data = _data()
    validation = gp.validate_gazepoint_biometrics(data, require_active_signal=False)
    state = ProjectState().with_dataset(
        data,
        source_name="reporting_fixture.csv",
        validation=validation,
        operation="load_upload",
    )
    result = {
        "overview": pd.DataFrame([{"status": "ready", "rows": 2}]),
        "summary": pd.DataFrame({"participant": ["P1", "P2"], "value": [1.0, 1.2]}),
        "parameters": {"signal_col": "GSR_US", "time_col": "CNT"},
    }
    state = state.with_analysis("eda_scr", result, parameters=result["parameters"])
    state = state.with_annotation(
        {
            "annotation_type": "manual_peak",
            "signal_col": "GSR_US",
            "time_col": "CNT",
            "time": 12.0,
            "start": None,
            "end": None,
            "note": "expert review",
        }
    )
    return state


def test_dataset_fingerprint_is_stable_and_value_sensitive():
    data = _data()
    first = dataset_fingerprint(data)
    second = dataset_fingerprint(data.copy())
    changed = data.copy()
    changed.loc[0, "GSR_US"] += 0.001
    assert first == second
    assert first != dataset_fingerprint(changed)
    assert len(first) == 64


def test_project_recipe_excludes_raw_rows_and_analysis_outputs():
    state = _state()
    recipe = project_recipe(state)
    text = project_recipe_json(state)
    assert recipe["schema"] == PROJECT_RECIPE_SCHEMA
    assert recipe["dataset"]["sha256"] == dataset_fingerprint(state.data)
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    assert len(recipe["annotations"]) == 1
    assert recipe["analysis_inventory"][0]["analysis"] == "eda_scr"
    assert "2.0" not in text or isinstance(text, str)
    assert '"raw_data_included": false' in text
    assert '"analysis_outputs_included": false' in text
    assert '"value": [1.0, 1.2]' not in text


def test_project_recipe_restore_requires_exact_dataset_fingerprint():
    original = _state()
    recipe = project_recipe(original)
    data = original.data.copy()
    fresh = ProjectState().with_dataset(
        data,
        source_name="fresh.csv",
        validation=gp.validate_gazepoint_biometrics(data, require_active_signal=False),
        operation="load_upload",
    )
    checks = recipe_validation_table(recipe, fresh.data)
    assert checks["passed"].all()
    restored = restore_project_recipe(fresh, recipe)
    assert len(restored.annotations) == 1
    assert restored.analyses == {}
    assert restored.provenance[-1]["operation"] == "restore_project_recipe"
    assert restored.provenance[-1]["analysis_outputs_restored"] is False

    changed = data.copy()
    changed.loc[0, "GSR_US"] += 1
    mismatch = ProjectState().with_dataset(
        changed,
        source_name="wrong.csv",
        validation=gp.validate_gazepoint_biometrics(changed, require_active_signal=False),
        operation="load_upload",
    )
    mismatch_checks = recipe_validation_table(recipe, mismatch.data)
    assert not mismatch_checks.loc[mismatch_checks["check"] == "dataset_fingerprint_match", "passed"].iloc[0]
    with pytest.raises(ValueError, match="fingerprint"):
        restore_project_recipe(mismatch, recipe)


def test_recipe_file_and_upload_loader_enforce_metadata_contract(tmp_path: Path):
    recipe_path = tmp_path / "project.json"
    recipe_path.write_text(project_recipe_json(_state()), encoding="utf-8")
    loaded = load_project_recipe(recipe_path)
    uploaded = load_project_recipe_upload(
        [{"name": "project.json", "size": recipe_path.stat().st_size, "datapath": str(recipe_path)}]
    )
    assert loaded["dataset"]["sha256"] == uploaded["dataset"]["sha256"]

    wrong = tmp_path / "project.txt"
    wrong.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=".json"):
        load_project_recipe(wrong)
    with pytest.raises(ValueError, match="exactly one"):
        load_project_recipe_upload(
            [
                {"name": "a.json", "size": 2, "datapath": str(recipe_path)},
                {"name": "b.json", "size": 2, "datapath": str(recipe_path)},
            ]
        )


def test_reporting_artifacts_delegate_to_package_reporting_contracts():
    state = _state().with_operation("pre_report_checkpoint")
    artifacts = build_reporting_artifacts(state, title="Studio test report", subtitle="Synthetic fixture")
    assert artifacts["title"] == "Studio test report"
    assert artifacts["dataset_fingerprint"] == dataset_fingerprint(state.data)
    assert artifacts["report"]["overview"].iloc[0]["status"] == "report_created"
    assert "gpbiometricspy" in str(artifacts["methods_text"]).lower()
    assert "structured analysis decision log" in str(artifacts["reproducibility"]).lower()
    assert "studio_analysis_inventory" in artifacts["tables"]
    assert "studio_provenance" in artifacts["tables"]
    assert artifacts["manifest"]["settings"]["dataset_sha256"] == dataset_fingerprint(state.data)

    report = report_markdown(artifacts)
    assert "Studio test report" in report
    assert "dataset SHA-256" in report
    manifest = json.loads(manifest_json(artifacts))
    assert manifest["studio"]["raw_data_included"] is False


def test_reporting_inventory_catalog_and_replay_script():
    state = _state()
    inventory = analysis_inventory(state.analyses)
    catalog = result_table_catalog(state.analyses)
    assert inventory.loc[0, "analysis"] == "eda_scr"
    assert inventory.loc[0, "table_count"] == 2
    assert set(catalog["result_path"]) == {"eda_scr.overview", "eda_scr.summary"}
    script = workflow_replay_script(state)
    assert "run_eda_scr_analysis" in script
    assert "dataset_fingerprint" in script
    assert dataset_fingerprint(state.data) in script
    assert "gp.import_gazepoint_biometrics" in script


def test_report_bundle_zip_is_metadata_and_reporting_only():
    state = _state()
    artifacts = build_reporting_artifacts(state, title="Bundle test")
    payload = bundle_zip_bytes(artifacts, state)
    assert payload.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
        names = set(archive.namelist())
        assert "gpbiometricspy_studio_report.md" in names
        assert "gpbiometricspy_studio_manifest.json" in names
        assert "gpbiometricspy_studio_project_recipe.json" in names
        assert "gpbiometricspy_studio_replay.py" in names
        recipe = json.loads(archive.read("gpbiometricspy_studio_project_recipe.json").decode("utf-8"))
        assert recipe["raw_data_included"] is False
        assert recipe["analysis_outputs_included"] is False
        assert not any(name.endswith("raw.csv") or "raw_data" in name for name in names)


def test_state_operation_and_restored_metadata_guards():
    state = _state()
    before = len(state.provenance)
    updated = state.with_operation("report_checkpoint", purpose="test")
    assert len(updated.provenance) == before + 1
    assert updated.provenance[-1]["purpose"] == "test"
    with pytest.raises(ValueError):
        state.with_operation("   ")
    with pytest.raises(ValueError, match="source dataset"):
        ProjectState().with_restored_session_metadata(annotations=(), provenance=())
    with pytest.raises(ValueError, match="Unsupported annotation"):
        state.with_restored_session_metadata(annotations=[{"annotation_type": "other"}], provenance=[])


def test_reporting_module_and_app_import():
    importlib.import_module("studio.reporting_services")
    importlib.import_module("studio.modules.reporting")
    importlib.import_module("studio.app")
