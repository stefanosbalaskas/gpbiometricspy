"""Static policy checks for the production desktop handoff release wiring."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUTOMATED_RELEASE_GATES = (
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


def test_production_handoff_workflow_is_manual_protected_and_exact_source_bound() -> None:
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


def test_cut_release_requires_full_exact_main_matrix_and_manual_handoff() -> None:
    workflow = _read(".github/workflows/cut-release.yml")
    for gate in AUTOMATED_RELEASE_GATES:
        assert gate in workflow
    assert "- studio-production-release-handoff" in workflow
    assert "studio-production-release-handoff.yml" in workflow
    assert "github.event.workflow_run.event == 'workflow_dispatch'" in workflow
    assert '.event == "workflow_dispatch" and .conclusion == "success"' in workflow
    assert "Final production handoff is not yet validated" in workflow
    assert "steps.gates.outputs.ready == '1'" in workflow


def test_release_revalidates_and_attaches_handoff_before_publication() -> None:
    workflow = _read(".github/workflows/release.yml")
    for gate in AUTOMATED_RELEASE_GATES:
        assert gate in workflow
    assert "studio-production-release-handoff.yml" in workflow
    assert 'gh run download "$HANDOFF_RUN_ID"' in workflow
    assert "desktop-production-release-evidence.json" in workflow
    assert "DESKTOP-HANDOFF-SHA256SUMS.txt" in workflow
    assert "sha256sum -c DESKTOP-HANDOFF-SHA256SUMS.txt" in workflow
    assert '--expected-tag "$RELEASE_TAG"' in workflow
    assert '--expected-source-commit "$TARGET_SHA"' in workflow
    handoff_validation = workflow.index("Download and revalidate production desktop handoff")
    github_release = workflow.index("Create immutable GitHub Release if absent")
    pypi_dispatch = workflow.index("Dispatch protected PyPI Trusted Publishing")
    assert handoff_validation < github_release < pypi_dispatch


def test_readiness_gate_runs_on_main_release_wiring_changes() -> None:
    workflow = _read(".github/workflows/studio-desktop-release-handoff-readiness.yml")
    assert "push:" in workflow
    assert "- main" in workflow
    assert "tests/test_production_release_handoff_wiring.py" in workflow
    assert ".github/workflows/studio-production-release-handoff.yml" in workflow
    assert "Exercise stable-release handoff wiring contract" in workflow


def main() -> int:
    test_production_handoff_workflow_is_manual_protected_and_exact_source_bound()
    test_cut_release_requires_full_exact_main_matrix_and_manual_handoff()
    test_release_revalidates_and_attaches_handoff_before_publication()
    test_readiness_gate_runs_on_main_release_wiring_changes()
    print("production release handoff wiring policy PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
