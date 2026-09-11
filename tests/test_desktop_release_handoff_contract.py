from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "release" / "validate_desktop_release_evidence.py"
TEMPLATE_PATH = ROOT / "tools" / "release" / "desktop_release_evidence.template.json"

spec = importlib.util.spec_from_file_location("desktop_release_validator", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def valid_evidence() -> dict:
    machine = {
        "label": "windows-11-x64-a",
        "windows_version": "Windows 11 24H2",
        "architecture": "x64",
        "webview2_version": "140.0.3485.94",
        "install": "pass",
        "repair_reinstall": "pass",
        "upgrade_0_1_5_to_0_1_6": "pass",
        "downgrade_block": "pass",
        "uninstall": "pass",
        "first_session_ux": "pass",
    }
    second = dict(machine)
    second["label"] = "windows-10-x64-b"
    second["windows_version"] = "Windows 10 22H2"
    return {
        "schema": validator.SCHEMA,
        "schema_version": validator.SCHEMA_VERSION,
        "release_tag": "v0.1.6",
        "source_commit": "a" * 40,
        "branding": {
            "final_icon_approved": True,
            "approved_by": "human-reviewer",
            "approved_at_utc": "2026-09-11T18:00:00Z",
        },
        "signing": {
            "provider": "production-signing-service",
            "signer_subject": "CN=Example Production Signer",
            "certificate_thumbprint": "b" * 40,
            "trusted_chain_verified": True,
            "digest_algorithm": "SHA256",
            "rfc3161_timestamp_verified": True,
            "timestamp_digest_algorithm": "SHA256",
            "timestamp_authority": "https://timestamp.example.invalid",
            "executable_sha256": "c" * 64,
            "installer_sha256": "d" * 64,
        },
        "release_environment": {
            "protected": True,
            "attestation_present": True,
            "attestation_sha256": "e" * 64,
            "sbom_present": True,
            "sbom_sha256": "f" * 64,
            "checksums_present": True,
            "checksums_sha256": "1" * 64,
        },
        "human_windows_validation": {
            "reviewed_by": "human-reviewer",
            "reviewed_at_utc": "2026-09-11T19:00:00+00:00",
            "minimum_machine_count": 2,
            "machines": [machine, second],
        },
    }


class DesktopReleaseEvidenceContractTests(unittest.TestCase):
    def test_repository_template_is_deliberately_ineligible(self) -> None:
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        errors = validator.validate_release_evidence(template, expected_tag="v0.1.6")
        self.assertTrue(errors)
        joined = "\n".join(errors)
        self.assertIn("source_commit", joined)
        self.assertIn("trusted_chain_verified", joined)
        self.assertIn("rfc3161_timestamp_verified", joined)
        self.assertIn("final_icon_approved", joined)
        self.assertIn("first_session_ux", joined)

    def test_complete_synthetic_record_satisfies_contract(self) -> None:
        evidence = valid_evidence()
        errors = validator.validate_release_evidence(
            evidence,
            expected_tag="v0.1.6",
            expected_source_commit="a" * 40,
        )
        self.assertEqual(errors, [])

    def test_exact_source_binding_is_fail_closed(self) -> None:
        evidence = valid_evidence()
        errors = validator.validate_release_evidence(
            evidence,
            expected_tag="v0.1.6",
            expected_source_commit="2" * 40,
        )
        self.assertIn("source_commit does not match the expected exact release commit", errors)

    def test_representative_machine_requirement_is_fail_closed(self) -> None:
        evidence = valid_evidence()
        evidence["human_windows_validation"]["machines"] = evidence["human_windows_validation"]["machines"][:1]
        errors = validator.validate_release_evidence(evidence)
        self.assertTrue(any("at least 2 representative machines" in item for item in errors))

    def test_timestamp_and_scenario_requirements_are_fail_closed(self) -> None:
        evidence = valid_evidence()
        evidence["branding"]["approved_at_utc"] = "2026-09-11T18:00:00"
        evidence["human_windows_validation"]["machines"][0]["upgrade_0_1_5_to_0_1_6"] = "pending"
        errors = validator.validate_release_evidence(evidence)
        self.assertTrue(any("timezone-aware" in item for item in errors))
        self.assertTrue(any("upgrade_0_1_5_to_0_1_6" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
