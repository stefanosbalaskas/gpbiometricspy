"""Contract tests for canonical stable Python-package release metadata."""

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "release" / "validate_stable_release_artifact.py"

spec = importlib.util.spec_from_file_location("stable_release_validator", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

TAG = "v0.1.6"
VERSION = "0.1.6"
SOURCE = "1" * 40


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path) -> dict[str, object]:
    dist = root / "dist"
    dist.mkdir(parents=True)

    wheel = dist / f"gpbiometricspy-{VERSION}-py3-none-any.whl"
    sdist = dist / f"gpbiometricspy-{VERSION}.tar.gz"
    wheel.write_bytes(b"wheel-candidate")
    sdist.write_bytes(b"sdist-candidate")

    packages = [
        {"path": f"dist/{wheel.name}", "sha256": _sha256(wheel)},
        {"path": f"dist/{sdist.name}", "sha256": _sha256(sdist)},
    ]
    (root / "SHA256SUMS.txt").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in packages),
        encoding="utf-8",
    )

    return {
        "schema": "gpbiometricspy-stable-release-artifact",
        "schema_version": 2,
        "release_tag": TAG,
        "source_commit": SOURCE,
        "distribution_checksums_sha256": _sha256(root / "SHA256SUMS.txt"),
        "packages": packages,
    }


def test_valid_bundle_is_eligible() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata = _fixture(root)
        errors = validator.validate_stable_release_artifact(
            metadata,
            root=root,
            expected_tag=TAG,
            expected_source_commit=SOURCE,
        )
        assert errors == []


def test_package_tampering_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata = _fixture(root)
        wheel = root / "dist" / f"gpbiometricspy-{VERSION}-py3-none-any.whl"
        wheel.write_bytes(b"tampered")
        errors = validator.validate_stable_release_artifact(metadata, root=root)
        assert any("package SHA-256 mismatch" in error for error in errors)


def test_checksum_manifest_must_match_package_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata = _fixture(root)
        (root / "SHA256SUMS.txt").write_text("0" * 64 + "  dist/unexpected.whl\n", encoding="utf-8")
        metadata["distribution_checksums_sha256"] = _sha256(root / "SHA256SUMS.txt")
        errors = validator.validate_stable_release_artifact(metadata, root=root)
        assert any("do not exactly match" in error for error in errors)


def test_wrong_tag_or_source_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata = _fixture(root)
        errors = validator.validate_stable_release_artifact(
            metadata,
            root=root,
            expected_tag="v9.9.9",
            expected_source_commit="2" * 40,
        )
        assert any("expected tag" in error for error in errors)
        assert any("expected exact release commit" in error for error in errors)


def test_package_path_traversal_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata = _fixture(root)
        metadata["packages"] = [{"path": "dist/../escape.whl", "sha256": "0" * 64}]
        errors = validator.validate_stable_release_artifact(metadata, root=root)
        assert any("safe relative path" in error for error in errors)


def test_stale_desktop_handoff_metadata_is_not_part_of_package_schema() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        metadata = _fixture(root)
        metadata["production_handoff_run_id"] = 123
        errors = validator.validate_stable_release_artifact(metadata, root=root)
        assert any("unexpected metadata keys" in error for error in errors)


def main() -> int:
    test_valid_bundle_is_eligible()
    test_package_tampering_fails_closed()
    test_checksum_manifest_must_match_package_metadata()
    test_wrong_tag_or_source_fails_closed()
    test_package_path_traversal_is_rejected()
    test_stale_desktop_handoff_metadata_is_not_part_of_package_schema()
    print("stable Python-package release artifact contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
