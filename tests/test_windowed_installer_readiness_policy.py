from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / ".github/scripts/test_studio_windowed_installer_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-windowed-installer-readiness.yml").read_text(encoding="utf-8")
ISS = (ROOT / "tools/installer/gpbiometricspy_studio.iss").read_text(encoding="utf-8")
ENGINEERING_SPEC = (ROOT / "tools/pyinstaller/gpbiometricspy_studio_native.spec").read_text(encoding="utf-8")
WINDOWED_SPEC = (ROOT / "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec").read_text(encoding="utf-8")


def test_windowed_installer_uses_same_stable_per_user_installer_contract():
    assert "AppId=fd3ca1af-0ebb-5061-9c59-f7ab1079252e" in ISS
    assert "PrivilegesRequired=lowest" in ISS
    assert "ArchitecturesAllowed=x64compatible" in ISS
    assert "Uninstallable=yes" in ISS
    assert "ChangesEnvironment=no" in ISS
    assert "ChangesAssociations=no" in ISS
    assert "[Run]" not in ISS
    assert "SignTool=" not in ISS


def test_windowed_installer_builds_windowed_spec_and_preserves_engineering_spec():
    assert "console=True" in ENGINEERING_SPEC
    assert "console=False" in WINDOWED_SPEC
    assert "gpbiometricspy_studio_native_windowed.spec" in SCRIPT
    assert 'source_bundle_mode = "onedir-native-windowed-webview2"' in SCRIPT
    assert 'engineering_console_build_preserved = $true' in SCRIPT


def test_windowed_installer_proves_gui_subsystem_before_and_after_install():
    assert "$PeOffset + 92" in SCRIPT
    assert "$SourcePeSubsystem = Get-PeSubsystem -Executable $SourceExecutable" in SCRIPT
    assert "$SourcePeSubsystem -ne 2" in SCRIPT
    assert "$InstalledPeSubsystem = Get-PeSubsystem -Executable $InstalledExecutable" in SCRIPT
    assert "$InstalledPeSubsystem -ne 2" in SCRIPT
    assert 'pe_subsystem_name = "IMAGE_SUBSYSTEM_WINDOWS_GUI"' in SCRIPT
    assert 'console = $false' in SCRIPT
    assert 'console_attached = $false' in SCRIPT


def test_windowed_installer_binds_exact_installed_bytes_and_identity():
    assert "$SourceExecutableSha256 = Get-Sha256 $SourceExecutable" in SCRIPT
    assert "$InstalledSha256 = Get-Sha256 $InstalledExecutable" in SCRIPT
    assert "$InstalledSha256 -ne $SourceExecutableSha256" in SCRIPT
    assert "$IdentityVerifier -Executable $SourceExecutable" in SCRIPT
    assert "$IdentityVerifier -Executable $InstalledExecutable" in SCRIPT
    assert 'installed_executable_identity_match = $true' in SCRIPT


def test_windowed_installer_runs_installed_local_and_public_without_external_python():
    assert 'Invoke-InstalledWindowedBoundarySmoke -Executable $InstalledExecutable -Name "local"' in SCRIPT
    assert 'Invoke-InstalledWindowedBoundarySmoke -Executable $InstalledExecutable -Name "public"' in SCRIPT
    assert "-PublicDemo" in SCRIPT
    assert '"Windowed release bootstrap: console_attached=false"' in SCRIPT
    assert '"Native renderer requested: edgechromium"' in SCRIPT
    assert '"Native DOM loaded\\."' in SCRIPT
    assert "Get-Command python -CommandType Application" in SCRIPT
    assert 'external_python_required = $false' in SCRIPT


def test_windowed_installer_preserves_webview2_fail_closed_prerequisite():
    assert "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" in SCRIPT
    assert "GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING" in SCRIPT
    assert "$MissingProcess.ExitCode -ne 7" in SCRIPT
    assert '"WebView2 Runtime missing"' in SCRIPT
    assert 'webview2_runtime_strategy = "evergreen-prerequisite-detect-and-remediate"' in SCRIPT
    assert 'webview2_runtime_payload_bundled = $false' in SCRIPT
    assert 'webview2_runtime_downloaded_in_ci = $false' in SCRIPT
    assert "BYPASS_WEBVIEW2" not in SCRIPT


def test_windowed_installer_requires_clean_uninstall():
    assert "$UninstallProcess.ExitCode -ne 0" in SCRIPT
    assert "Installed executable survived uninstall." in SCRIPT
    assert "Uninstall registration survived uninstall." in SCRIPT
    assert "Start Menu shortcut survived uninstall." in SCRIPT
    assert 'uninstall_registration_removed = $true' in SCRIPT
    assert 'shortcuts_removed = $true' in SCRIPT
    assert 'payload_files_removed = $true' in SCRIPT


def test_windowed_installer_ci_is_diagnostics_only_and_secret_free():
    lowered = WORKFLOW.lower()
    assert "secrets." not in lowered
    assert "github.token" not in lowered
    assert "permissions:\n  contents: read" in lowered
    assert "timeout-minutes: 30" in lowered
    assert 'release_artifact = $false' in SCRIPT
    assert 'installer_published = $false' in SCRIPT
    assert 'installer_signed = $false' in SCRIPT
    assert 'production_signing_required = $true' in SCRIPT
    assert 'production_timestamp_required = $true' in SCRIPT
    assert '"*.exe", "*.pfx", "*.p12"' in SCRIPT

    upload = WORKFLOW.split("Upload windowed-installer evidence only", 1)[1]
    assert "/evidence/" in upload
    assert "installer-output" not in upload
    assert "dist" not in upload.lower()
    assert "installed" not in upload.lower()
    assert "*.exe" not in upload.lower()
    assert ".pfx" not in upload.lower()
    assert ".p12" not in upload.lower()
