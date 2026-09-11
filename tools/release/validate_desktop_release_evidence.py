#!/usr/bin/env python3
"""Validate the production desktop release handoff evidence record.

This validator is intentionally fail-closed. It validates the completeness and
internal consistency of a release handoff record; it does not create trust,
sign binaries, or replace human approval.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "gpbiometricspy-studio-production-release-evidence"
SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
THUMBPRINT_RE = re.compile(r"^[0-9a-fA-F]{40,128}$")
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
REQUIRED_SCENARIOS = (
    "install",
    "repair_reinstall",
    "upgrade_0_1_5_to_0_1_6",
    "downgrade_block",
    "uninstall",
    "first_session_ux",
)


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _require_text(container: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key} must be a non-empty string")
        return ""
    return value.strip()


def _require_true(container: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    if container.get(key) is not True:
        errors.append(f"{path}.{key} must be true")


def _require_sha256(container: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = _require_text(container, key, path, errors)
    if value and SHA256_RE.fullmatch(value) is None:
        errors.append(f"{path}.{key} must be a 64-character SHA-256 hex digest")
    return value.lower()


def validate_release_evidence(
    evidence: dict[str, Any],
    *,
    expected_tag: str | None = None,
    expected_source_commit: str | None = None,
) -> list[str]:
    errors: list[str] = []

    if evidence.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA!r}")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")

    tag = evidence.get("release_tag")
    if not isinstance(tag, str) or TAG_RE.fullmatch(tag) is None:
        errors.append("release_tag must be a stable vX.Y.Z tag")
    elif expected_tag is not None and tag != expected_tag:
        errors.append(f"release_tag {tag!r} does not match expected tag {expected_tag!r}")

    source_commit = evidence.get("source_commit")
    if not isinstance(source_commit, str) or COMMIT_RE.fullmatch(source_commit) is None:
        errors.append("source_commit must be an exact 40-character Git SHA")
    elif expected_source_commit is not None and source_commit.lower() != expected_source_commit.lower():
        errors.append("source_commit does not match the expected exact release commit")

    branding = evidence.get("branding")
    if not isinstance(branding, dict):
        errors.append("branding must be an object")
    else:
        _require_true(branding, "final_icon_approved", "branding", errors)
        _require_text(branding, "approved_by", "branding", errors)
        approved_at = branding.get("approved_at_utc")
        if not _utc_timestamp(approved_at):
            errors.append("branding.approved_at_utc must be a timezone-aware ISO-8601 timestamp")

    signing = evidence.get("signing")
    if not isinstance(signing, dict):
        errors.append("signing must be an object")
    else:
        _require_text(signing, "provider", "signing", errors)
        _require_text(signing, "signer_subject", "signing", errors)
        thumbprint = _require_text(signing, "certificate_thumbprint", "signing", errors)
        if thumbprint and THUMBPRINT_RE.fullmatch(thumbprint) is None:
            errors.append("signing.certificate_thumbprint must be hexadecimal")
        _require_true(signing, "trusted_chain_verified", "signing", errors)
        if str(signing.get("digest_algorithm", "")).upper() != "SHA256":
            errors.append("signing.digest_algorithm must equal SHA256")
        _require_true(signing, "rfc3161_timestamp_verified", "signing", errors)
        if str(signing.get("timestamp_digest_algorithm", "")).upper() != "SHA256":
            errors.append("signing.timestamp_digest_algorithm must equal SHA256")
        _require_text(signing, "timestamp_authority", "signing", errors)
        _require_sha256(signing, "executable_sha256", "signing", errors)
        _require_sha256(signing, "installer_sha256", "signing", errors)

    release_environment = evidence.get("release_environment")
    if not isinstance(release_environment, dict):
        errors.append("release_environment must be an object")
    else:
        _require_true(release_environment, "protected", "release_environment", errors)
        _require_true(release_environment, "attestation_present", "release_environment", errors)
        _require_sha256(release_environment, "attestation_sha256", "release_environment", errors)
        _require_true(release_environment, "sbom_present", "release_environment", errors)
        _require_sha256(release_environment, "sbom_sha256", "release_environment", errors)
        _require_true(release_environment, "checksums_present", "release_environment", errors)
        _require_sha256(release_environment, "checksums_sha256", "release_environment", errors)

    human = evidence.get("human_windows_validation")
    if not isinstance(human, dict):
        errors.append("human_windows_validation must be an object")
    else:
        _require_text(human, "reviewed_by", "human_windows_validation", errors)
        reviewed_at = human.get("reviewed_at_utc")
        if not _utc_timestamp(reviewed_at):
            errors.append("human_windows_validation.reviewed_at_utc must be a timezone-aware ISO-8601 timestamp")
        minimum = human.get("minimum_machine_count")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 2:
            errors.append("human_windows_validation.minimum_machine_count must be an integer >= 2")
            minimum = 2
        machines = human.get("machines")
        if not isinstance(machines, list):
            errors.append("human_windows_validation.machines must be an array")
            machines = []
        if len(machines) < minimum:
            errors.append(
                f"human_windows_validation.machines must contain at least {minimum} representative machines"
            )
        labels: set[str] = set()
        for index, machine in enumerate(machines):
            path = f"human_windows_validation.machines[{index}]"
            if not isinstance(machine, dict):
                errors.append(f"{path} must be an object")
                continue
            label = _require_text(machine, "label", path, errors)
            if label:
                if label in labels:
                    errors.append(f"{path}.label must be unique")
                labels.add(label)
            _require_text(machine, "windows_version", path, errors)
            architecture = _require_text(machine, "architecture", path, errors)
            if architecture and architecture.lower() not in {"x64", "arm64"}:
                errors.append(f"{path}.architecture must be x64 or arm64")
            _require_text(machine, "webview2_version", path, errors)
            for scenario in REQUIRED_SCENARIOS:
                if machine.get(scenario) != "pass":
                    errors.append(f"{path}.{scenario} must equal 'pass'")

    return errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-tag")
    parser.add_argument("--expected-source-commit")
    parser.add_argument(
        "--expect-ineligible",
        action="store_true",
        help="Succeed only when the manifest is correctly rejected as incomplete/ineligible.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        evidence = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"eligible": False, "errors": [f"unable to read manifest: {exc}"]}, indent=2))
        return 0 if args.expect_ineligible else 1
    if not isinstance(evidence, dict):
        errors = ["manifest root must be a JSON object"]
    else:
        errors = validate_release_evidence(
            evidence,
            expected_tag=args.expected_tag,
            expected_source_commit=args.expected_source_commit,
        )

    eligible = not errors
    print(json.dumps({"eligible": eligible, "errors": errors}, indent=2, sort_keys=True))
    if args.expect_ineligible:
        return 0 if not eligible else 1
    return 0 if eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
