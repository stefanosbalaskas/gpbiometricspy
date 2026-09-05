from __future__ import annotations

import pandas as pd
import pytest

import gpbiometricspy as gp


def test_preregistration_option_and_evidence_guardrails():
    with pytest.raises(ValueError, match="include_optional"):
        gp.create_gazepoint_preregistration_checklist(include_optional="yes")

    with pytest.raises(ValueError, match="require_required_fields"):
        gp.audit_gazepoint_preregistration_consistency(
            require_required_fields="yes"
        )

    with pytest.raises(ValueError, match="named list"):
        gp.audit_gazepoint_preregistration_consistency(evidence=["not", "named"])


def test_preregistration_readiness_group_guardrail():
    audit = pd.DataFrame(
        {
            "required": [True],
            "audit_status": ["missing_required"],
            "audit_pass": [False],
            "item_id": ["x"],
        }
    )
    with pytest.raises(ValueError, match="columns not found"):
        gp.summarize_gazepoint_preregistration_readiness(audit, by="missing_group")


def test_interoperability_manifest_and_flag_guardrails():
    with pytest.raises(ValueError, match="include_support"):
        gp.gazepoint_interoperability_manifest(include_support="yes")

    with pytest.raises(ValueError, match="flags"):
        gp.audit_gazepoint_interoperability_versions(include_python="yes")

    with pytest.raises(ValueError, match="invalid contract"):
        gp.audit_gazepoint_interoperability_versions(
            pd.DataFrame({"target": ["incomplete"]})
        )


def test_interoperability_strict_failure_is_publicly_reachable():
    manifest = pd.DataFrame(
        {
            "target": ["Deliberate missing bridge"],
            "ecosystem": ["Standard"],
            "dependency": ["synthetic-standard"],
            "dependency_type": ["standard"],
            "minimum_tested_version": ["1.0.0"],
            "version_policy": ["specification"],
            "test_group": ["branch-test"],
            "bridge_functions": ["definitely_not_a_frozen_export"],
            "optional": [False],
        }
    )
    with pytest.raises(RuntimeError, match="Interoperability audit failed"):
        gp.audit_gazepoint_interoperability_versions(manifest, strict=True)


def test_interoperability_writer_guardrails(tmp_path):
    with pytest.raises(TypeError, match="interoperability audit"):
        gp.write_gazepoint_interoperability_audit({}, tmp_path)

    audit = gp.audit_gazepoint_interoperability_versions(include_python=False)
    with pytest.raises(ValueError, match="filename prefix"):
        gp.write_gazepoint_interoperability_audit(
            audit,
            tmp_path,
            prefix="bad/prefix",
        )
