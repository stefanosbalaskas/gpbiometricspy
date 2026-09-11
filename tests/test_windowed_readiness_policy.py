from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING_SPEC = (ROOT / "tools/pyinstaller/gpbiometricspy_studio_native.spec").read_text(encoding="utf-8")
WINDOWED_SPEC = (ROOT / "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "studio/native_windowed.py").read_text(encoding="utf-8")
HARNESS = (ROOT / ".github/scripts/test_studio_pyinstaller_native_windowed_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-windowed-readiness.yml").read_text(encoding="utf-8")


def test_engineering_console_build_is_preserved_while_release_build_is_windowed():
    assert "console=True" in ENGINEERING_SPEC
    assert "studio/native_frozen.py" in ENGINEERING_SPEC
    assert "console=False" in WINDOWED_SPEC
    assert 'ENTRY = ROOT / "studio" / "native_windowed.py"' in WINDOWED_SPEC
    assert 'name="gpbiometricspy-studio-native"' in WINDOWED_SPEC


def test_windowed_bootstrap_repairs_streams_before_importing_native_application():
    main_index = BOOTSTRAP.index("def main")
    stabilize_index = BOOTSTRAP.index("_stabilize_standard_streams()", main_index)
    import_index = BOOTSTRAP.index("from studio.native_frozen import main as native_main", main_index)
    assert stabilize_index < import_index
    prefix = BOOTSTRAP[:main_index]
    assert "from shiny" not in prefix
    assert "import studio.native_frozen" not in prefix
    assert 'WINDOWED_LOG_ENV = "GPBIOMETRICSPY_WINDOWED_LOG_PATH"' in BOOTSTRAP
    assert "sys.stdin is None" in BOOTSTRAP
    assert "sys.stdout is None or sys.stderr is None" in BOOTSTRAP
    assert "os.devnull" in BOOTSTRAP


def test_windowed_harness_proves_gui_subsystem_no_console_and_native_readiness():
    assert "$PeOffset + 92" in HARNESS
    assert "$PeSubsystem -ne 2" in HARNESS
    assert "IMAGE_SUBSYSTEM_WINDOWS_GUI" in HARNESS
    assert '"Windowed release bootstrap: console_attached=false"' in HARNESS
    assert '"Native renderer requested: edgechromium"' in HARNESS
    assert '"Native DOM loaded\\."' in HARNESS
    assert 'console = $false' in HARNESS
    assert 'console_attached = $false' in HARNESS
    assert 'engineering_console_build_preserved = $true' in HARNESS
    assert 'external_python_required = $false' in HARNESS
    assert "Get-Command python -CommandType Application" in HARNESS


def test_windowed_proof_is_diagnostics_only_and_contains_no_signing_secret():
    assert 'release_artifact = $false' in HARNESS
    assert 'Remove-Item -LiteralPath $DistRoot -Recurse -Force' in HARNESS
    assert '"*.exe", "*.pfx", "*.p12"' in HARNESS

    lowered = WORKFLOW.lower()
    assert "secrets." not in lowered
    assert "github.token" not in lowered
    assert "permissions:\n  contents: read" in lowered
    assert "timeout-minutes: 20" in lowered

    upload = WORKFLOW.split("Upload windowed-readiness evidence only", 1)[1]
    assert "/evidence/" in upload
    assert "dist" not in upload.lower()
    assert "*.exe" not in upload.lower()
    assert ".pfx" not in upload.lower()
    assert ".p12" not in upload.lower()
