from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import gpbiometricspy as gp


def test_governance_audit_index_includes_checks_and_summary():
    audit = {
        "checks": pd.DataFrame(
            [{"check": "schema", "item": "GSR_US", "status": "pass", "message": "present"}]
        ),
        "summary": pd.DataFrame(
            [{"check": "overall", "status": "warn", "message": "review"}]
        ),
    }
    out = gp.create_gazepoint_audit_index(
        audit,
        include_summary_rows=True,
    )
    assert set(out["source_table"]) == {"checks", "summary"}
    assert set(out["status"]) == {"pass", "warn"}


def test_governance_markdown_handles_empty_summary():
    empty_index = gp.create_gazepoint_audit_index(None)
    text = gp.export_gazepoint_audit_trail_markdown(
        empty_index,
        summary=pd.DataFrame(),
        include_details=False,
    )
    assert "_No records._" in text
    assert "## Details" not in text


def test_governance_inventory_validation_and_classifier_returns(tmp_path: Path):
    with pytest.raises(ValueError, match="recursive"):
        gp.summarize_gazepoint_export_inventory(tmp_path, recursive="yes")
    with pytest.raises(ValueError, match="path"):
        gp.summarize_gazepoint_export_inventory([])

    biometric = tmp_path / "biometric_export.csv"
    biometric.write_text("GSR_US\n1.0\n", encoding="utf-8")
    event_file = tmp_path / "event_export.csv"
    event_file.write_text("event_id,time\n1,0\n", encoding="utf-8")
    sidecar = tmp_path / "metadata.json"
    sidecar.write_text("{}", encoding="utf-8")
    unknown = tmp_path / "mystery.bin"
    unknown.write_bytes(b"abc")

    inv = gp.summarize_gazepoint_export_inventory(
        [biometric, event_file, sidecar, unknown],
        recursive=False,
    )
    kinds = dict(zip(inv["file_name"], inv["likely_export_type"]))
    assert kinds[biometric.name] == "biometrics"
    assert kinds[event_file.name] == "events"
    assert kinds[sidecar.name] == "sidecar"
    assert kinds[unknown.name] == "unknown"


def test_governance_dataset_structure_validation_paths(tmp_path: Path):
    missing_root = tmp_path / "missing"
    with pytest.raises(ValueError, match="existing directory"):
        gp.audit_gazepoint_dataset_structure(missing_root)

    root = tmp_path / "dataset"
    root.mkdir()
    (root / "events.csv").write_text("event_id,time\n1,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="require_sidecars"):
        gp.audit_gazepoint_dataset_structure(root, require_sidecars="yes")
    with pytest.raises(ValueError, match="expected_dirs"):
        gp.audit_gazepoint_dataset_structure(root, expected_dirs=123)
    with pytest.raises(ValueError, match="expected_files"):
        gp.audit_gazepoint_dataset_structure(root, expected_files=123)

    out = gp.audit_gazepoint_dataset_structure(
        root,
        expected_dirs=None,
        expected_files=None,
        expected_patterns=None,
        allowed_extensions=None,
        require_sidecars=False,
    )
    assert len(out["inventory"]) == 1
    assert out["checks"].empty
    assert bool(out["summary"].iloc[0]["audit_pass"])


def test_governance_sidecar_template_validation_and_no_custom_fields():
    with pytest.raises(ValueError, match="single value"):
        gp.create_gazepoint_sidecar_template(dataset_id=["dataset"])
    with pytest.raises(ValueError, match="include_optional"):
        gp.create_gazepoint_sidecar_template(include_optional="yes")
    with pytest.raises(ValueError, match="custom_fields"):
        gp.create_gazepoint_sidecar_template(
            custom_fields=pd.DataFrame({"field": ["extra"]})
        )

    out = gp.create_gazepoint_sidecar_template(
        dataset_id="dataset-1",
        export_type="events",
        include_optional=False,
        custom_fields=None,
    )
    assert len(out) == 9
    assert out["required"].all()
    assert out.loc[out["field"] == "dataset_id", "value"].iloc[0] == "dataset-1"
