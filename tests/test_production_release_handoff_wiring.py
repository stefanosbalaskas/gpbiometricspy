"""Static policy checks for optional desktop handoff and canonical package publication."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACKAGE_RELEASE_GATES = (
    "tests.yml",
    "docs.yml",
    "codeql.yml",
    "deep-parity.yml",
    "interoperability.yml",
    "branch-coverage.yml",
    "real-data-validation.yml",
    "studio.yml",
    "studio-e2e.yml",
    "studio-production.yml",
)

OPTIONAL_DESKTOP_GATES = (
    "studio-packaging.yml",
    "studio-signing-readiness.yml",
    "studio-installer-readiness.yml",
    "studio-windowed-readiness.yml",
    "studio-windowed-installer-readiness.yml",
    "studio-release-provenance-readiness.yml",
    "studio-release-orchestration-readiness.yml",
    "studio-desktop-release-handoff-readiness.yml",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_production_handoff_workflow_remains_manual_protected_and_exact_source_bound() -> None:
    workflow = _read(".github/workflows/studio-production-release-handoff.yml")
    assert "workflow_dispatch:" in workflow
    assert "release_tag:" in workflow
    assert "source_commit:" in workflow
    assert "evidence_json:" in workflow
    assert "environment: production-release" in workflow
    assert "git fetch origin main --force" in workflow
    assert "git rev-parse origin/main" in workflow
    assert '--expected-tag "$RELEASE_TAG"' in workflow
    assert '--expected-source-commit "$SOURCE_COMMIT"' in workflow
    assert "studio-production-release-handoff-evidence-${{ inputs.source_commit }}" in workflow
    assert "DESKTOP-HANDOFF-SHA256SUMS.txt" in workflow
    assert "secrets." not in workflow
    assert "id-token: write" not in workflow


def test_cut_release_requires_package_matrix_but_not_desktop_handoff() -> None:
    workflow = _read(".github/workflows/cut-release.yml")
    for gate in PACKAGE_RELEASE_GATES:
        assert gate in workflow
    for gate in OPTIONAL_DESKTOP_GATES:
        assert gate not in workflow
    assert "studio-production-release-handoff.yml" not in workflow
    assert "Final production handoff is not yet validated" not in workflow
    assert "steps.gates.outputs.ready == '1'" in workflow
    assert 'gh workflow run release.yml --ref "$TAG" -f tag="$TAG"' in workflow
    assert 'gh workflow run release.yml --ref main' not in workflow


def test_release_is_exact_tag_bound_and_emits_package_only_canonical_artifact() -> None:
    workflow = _read(".github/workflows/release.yml")
    for gate in PACKAGE_RELEASE_GATES:
        assert gate in workflow
    for gate in OPTIONAL_DESKTOP_GATES:
        assert gate not in workflow
    assert 'test "${GITHUB_SHA,,}" = "$TARGET_SHA"' in workflow
    assert 'test "$TARGET_SHA" = "$MAIN_SHA"' in workflow
    assert "studio-production-release-handoff.yml" not in workflow
    assert "desktop-production-release-evidence.json" not in workflow
    assert "DESKTOP-HANDOFF-SHA256SUMS.txt" not in workflow
    assert "validate_desktop_release_evidence.py" not in workflow
    assert "SOURCE_DATE_EPOCH" in workflow
    assert "RELEASE-METADATA.json" in workflow
    assert "'schema_version': 2" in workflow
    assert "validate_stable_release_artifact.py" in workflow
    assert "Create or verify immutable GitHub Release" in workflow
    assert "Existing immutable release asset differs" in workflow
    assert "Upload canonical release artifact for downstream trusted publication" in workflow
    assert "retention-days: 90" in workflow
    assert "gh workflow run pypi.yml" not in workflow
    metadata = workflow.index("Write and validate canonical stable-release metadata")
    github_release = workflow.index("Create or verify immutable GitHub Release")
    upload = workflow.index("Upload canonical release artifact for downstream trusted publication")
    assert metadata < github_release < upload


def test_pypi_can_only_publish_from_successful_canonical_package_artifact() -> None:
    workflow = _read(".github/workflows/pypi.yml")
    assert "workflow_run:" in workflow
    assert "- release" in workflow
    assert "types: [completed]" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "environment: pypi" in workflow
    assert "actions: read" in workflow
    assert "id-token: write" in workflow
    assert "Resolve successful canonical release run" in workflow
    assert "gh run list --workflow release.yml" in workflow
    assert "Download canonical release artifact from successful release run" in workflow
    assert "run-id: ${{ steps.release_run.outputs.run_id }}" in workflow
    assert "RELEASE-METADATA.json" in workflow
    assert "schema_version') != 2" in workflow
    assert "validate_stable_release_artifact.py" in workflow
    assert "validate_desktop_release_evidence.py" not in workflow
    assert "release-handoff" not in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "Verify GitHub Release still matches canonical artifact" in workflow
    assert "GitHub Release asset drift detected" in workflow
    assert "packages-dir: canonical-release/dist/" in workflow
    assert "gh release download" in workflow
    assert "release:\n    types: [published]" not in workflow
    canonical_validation = workflow.index("Revalidate canonical package artifact and main ancestry")
    release_match = workflow.index("Verify GitHub Release still matches canonical artifact")
    publish = workflow.index("Publish canonical distributions to PyPI")
    assert canonical_validation < release_match < publish


def test_readiness_gate_still_covers_package_release_wiring_changes() -> None:
    workflow = _read(".github/workflows/studio-desktop-release-handoff-readiness.yml")
    assert "push:" in workflow
    assert "- main" in workflow
    assert "tests/test_production_release_handoff_wiring.py" in workflow
    assert "tests/test_stable_release_artifact_contract.py" in workflow
    assert ".github/workflows/pypi.yml" in workflow
    assert "Exercise canonical stable-release artifact contract" in workflow
    assert "Exercise stable-release and PyPI wiring contract" in workflow


def main() -> int:
    test_production_handoff_workflow_remains_manual_protected_and_exact_source_bound()
    test_cut_release_requires_package_matrix_but_not_desktop_handoff()
    test_release_is_exact_tag_bound_and_emits_package_only_canonical_artifact()
    test_pypi_can_only_publish_from_successful_canonical_package_artifact()
    test_readiness_gate_still_covers_package_release_wiring_changes()
    print("optional desktop handoff and canonical package publication wiring policy PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
