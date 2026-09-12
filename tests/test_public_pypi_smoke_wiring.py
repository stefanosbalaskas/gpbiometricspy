from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "public-pypi-smoke.yml"
HARNESS = ROOT / "scripts" / "public_pypi_smoke.py"


def test_public_pypi_smoke_is_public_index_only_and_release_pinned() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "https://pypi.org/simple" in workflow
    assert 'PIP_EXTRA_INDEX_URL: ""' in workflow
    assert '"gpbiometricspy[studio]==0.1.6"' in workflow
    assert "087645e8fccd0885c0cd99fe1e0362f2d234f68f975b148cc9b8c64a2b8e2970" in workflow
    assert "c57ec464bbbb4b9444646e26e2abd02ff20e0a00e2b1ab8385bdf867eaa2eb25" in workflow
    assert "working-directory: ${{ runner.temp }}" in workflow


def test_public_pypi_smoke_checks_frozen_scientific_and_studio_contracts() -> None:
    harness = HARNESS.read_text(encoding="utf-8")
    assert "len(gp.R_EXPORTS) != 406" in harness
    assert "len(gp.IMPLEMENTED_EXPORTS) != 406" in harness
    assert "len(gp.PENDING_EXPORTS) != 0" in harness
    assert "len(demo_files) != 36" in harness
    assert 'int(overview["total_rows"]) != 69_120' in harness
    for script in (
        "gpbiometricspy-studio",
        "gpbiometricspy-studio-public",
        "gpbiometricspy-studio-desktop",
        "gpbiometricspy-studio-native",
        "gpbiometricspy-studio-doctor",
    ):
        assert script in harness
