#!/usr/bin/env python3
"""Validate a canonical stable-release artifact bundle.

The bundle binds the exact release tag/source commit to the package files,
distribution checksum manifest, and validated production desktop handoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "gpbiometricspy-stable-release-artifact"
SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(path: str) -> bool:
    candidate = PurePosixPath(path)
    return not candidate.is_absolute() and ".." not in candidate.parts and "." not in candidate.parts


def _read_checksum_manifest(path: Path, errors: list[str]) -> dict[str, str]:
    entries: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"unable to read SHA256SUMS.txt: {exc}")
        return entries
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or SHA256_RE.fullmatch(parts[0]) is None:
            errors.append(f"SHA256SUMS.txt line {index} is malformed")
            continue
        rel = parts[1].lstrip("* ").replace("\\", "/")
        if not _safe_relative(rel):
            errors.append(f"SHA256SUMS.txt line {index} contains an unsafe path")
            continue
        if rel in entries:
            errors.append(f"SHA256SUMS.txt contains duplicate path {rel!r}")
            continue
        entries[rel] = parts[0].lower()
    return entries


def validate_stable_release_artifact(
    metadata: dict[str, Any],
    *,
    root: Path,
    expected_tag: str | None = None,
    expected_source_commit: str | None = None,
) -> list[str]:
    errors: list[str] = []
    root = root.resolve()

    if metadata.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA!r}")
    if metadata.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")

    tag = metadata.get("release_tag")
    match = TAG_RE.fullmatch(tag) if isinstance(tag, str) else None
    if match is None:
        errors.append("release_tag must be a stable vX.Y.Z tag")
        version = ""
    else:
        version = match.group(1)
        if expected_tag is not None and tag != expected_tag:
            errors.append(f"release_tag {tag!r} does not match expected tag {expected_tag!r}")

    source_commit = metadata.get("source_commit")
    if not isinstance(source_commit, str) or COMMIT_RE.fullmatch(source_commit) is None:
        errors.append("source_commit must be an exact 40-character Git SHA")
    elif expected_source_commit is not None and source_commit.lower() != expected_source_commit.lower():
        errors.append("source_commit does not match the expected exact release commit")

    handoff_run_id = metadata.get("production_handoff_run_id")
    if not isinstance(handoff_run_id, int) or isinstance(handoff_run_id, bool) or handoff_run_id <= 0:
        errors.append("production_handoff_run_id must be a positive integer")

    fixed_hashes = {
        "distribution_checksums_sha256": root / "SHA256SUMS.txt",
        "production_handoff_sha256": root
        / "release-handoff"
        / "desktop-production-release-evidence.json",
        "production_handoff_checksums_sha256": root
        / "release-handoff"
        / "DESKTOP-HANDOFF-SHA256SUMS.txt",
    }
    for key, path in fixed_hashes.items():
        expected = metadata.get(key)
        if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None:
            errors.append(f"{key} must be a 64-character SHA-256 hex digest")
            continue
        if not path.is_file():
            errors.append(f"required release artifact is missing: {path.relative_to(root)}")
            continue
        actual = _sha256(path)
        if actual != expected.lower():
            errors.append(f"{key} does not match {path.relative_to(root)}")

    packages = metadata.get("packages")
    if not isinstance(packages, list):
        errors.append("packages must be an array")
        packages = []

    expected_paths = set()
    if version:
        expected_paths = {
            f"dist/gpbiometricspy-{version}-py3-none-any.whl",
            f"dist/gpbiometricspy-{version}.tar.gz",
        }

    package_hashes: dict[str, str] = {}
    for index, package in enumerate(packages):
        path_name = f"packages[{index}]"
        if not isinstance(package, dict):
            errors.append(f"{path_name} must be an object")
            continue
        rel = package.get("path")
        digest = package.get("sha256")
        if not isinstance(rel, str) or not _safe_relative(rel) or not rel.startswith("dist/"):
            errors.append(f"{path_name}.path must be a safe relative path under dist/")
            continue
        if rel in package_hashes:
            errors.append(f"duplicate package path {rel!r}")
            continue
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            errors.append(f"{path_name}.sha256 must be a 64-character SHA-256 hex digest")
            continue
        package_hashes[rel] = digest.lower()
        artifact = root.joinpath(*PurePosixPath(rel).parts)
        if not artifact.is_file():
            errors.append(f"package artifact is missing: {rel}")
            continue
        if _sha256(artifact) != digest.lower():
            errors.append(f"package SHA-256 mismatch: {rel}")

    if expected_paths and set(package_hashes) != expected_paths:
        errors.append(
            "packages must contain exactly the stable wheel and sdist: "
            + ", ".join(sorted(expected_paths))
        )

    checksum_entries = _read_checksum_manifest(root / "SHA256SUMS.txt", errors)
    if checksum_entries and checksum_entries != package_hashes:
        errors.append("SHA256SUMS.txt entries do not exactly match metadata.packages")

    return errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-tag")
    parser.add_argument("--expected-source-commit")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        metadata = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"eligible": False, "errors": [f"unable to read manifest: {exc}"]}, indent=2))
        return 1
    if not isinstance(metadata, dict):
        errors = ["manifest root must be a JSON object"]
    else:
        errors = validate_stable_release_artifact(
            metadata,
            root=args.root,
            expected_tag=args.expected_tag,
            expected_source_commit=args.expected_source_commit,
        )
    print(json.dumps({"eligible": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
