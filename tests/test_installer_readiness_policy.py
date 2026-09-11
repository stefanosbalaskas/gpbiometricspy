from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ISS = (ROOT / "tools/installer/gpbiometricspy_studio.iss").read_text(encoding="utf-8")
SCRIPT = (ROOT / ".github/scripts/test_studio_installer_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-installer-readiness.yml").read_text(encoding="utf-8")


def test_installer_is_stable_per_user_non_elevating_and_uninstallable():
    assert "AppId=fd3ca1af-0ebb-5061-9c59-f7ab1079252e" in ISS
    assert "AppName=gpbiometricspy Studio" in ISS
    assert r"DefaultDirName={localappdata}\Programs\gpbiometricspy Studio" in ISS
    assert "PrivilegesRequired=lowest" in ISS
    assert "PrivilegesRequiredOverridesAllowed" not in ISS
    assert "ArchitecturesAllowed=x64compatible" in ISS
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in ISS
    assert "Uninstallable=yes" in ISS
    assert "UsePreviousAppDir=yes" in ISS
    assert "UsePreviousGroup=yes" in ISS
    assert "UsePreviousTasks=yes" in ISS
    assert "UsePreviousPrivileges=no" in ISS
    assert "ChangesEnvironment=no" in ISS
    assert "ChangesAssociations=no" in ISS


def test_installer_keeps_display_version_and_pe_versions_separate():
    assert "AppVersion={#AppVersion}" in ISS
    assert "VersionInfoProductVersion={#FileVersion}" in ISS
    assert "VersionInfoVersion={#FileVersion}" in ISS
    assert "VersionInfoProductVersion={#AppVersion}" not in ISS


def test_installer_never_auto_runs_and_desktop_shortcut_is_opt_in():
    assert "[Run]" not in ISS
    assert "[UninstallRun]" not in ISS
    assert 'Name: "desktopicon"' in ISS
    assert "Flags: unchecked" in ISS
    assert r'{autoprograms}\gpbiometricspy Studio' in ISS
    assert r'{autodesktop}\gpbiometricspy Studio' in ISS


def test_installer_ci_definition_contains_no_signing_hook_or_secret():
    assert "SignTool=" not in ISS
    lowered = WORKFLOW.lower()
    assert "secrets." not in lowered
    assert "github.token" not in lowered
    assert "permissions:\n  contents: read" in lowered
    assert "timeout-minutes: 25" in lowered


def test_installer_enforces_evergreen_webview2_prerequisite_without_bypass():
    product_id = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    assert product_id in ISS
    assert product_id in SCRIPT
    assert "RegQueryStringValue(HKLM32" in ISS
    assert "RegQueryStringValue(HKCU" in ISS
    assert "'pv'" in ISS
    assert "PrepareToInstall(var NeedsRestart: Boolean): String" in ISS
    assert "WebView2 Runtime missing; setup cannot continue." in ISS
    assert "Evergreen WebView2 Runtime" in ISS
    assert "GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING" in ISS
    assert "GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING" in SCRIPT
    assert "BYPASS_WEBVIEW2" not in ISS
    assert "BYPASS_WEBVIEW2" not in SCRIPT
    assert "DownloadTemporaryFile" not in ISS
    assert "Exec(" not in ISS


def test_installer_harness_independently_detects_runtime_and_proves_missing_path():
    assert "Get-WebView2RuntimeEvidence" in SCRIPT
    assert "HKEY_LOCAL_MACHINE\\SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients" in SCRIPT
    assert "HKEY_CURRENT_USER\\Software\\Microsoft\\EdgeUpdate\\Clients" in SCRIPT
    assert 'Get-ItemPropertyValue -LiteralPath $Candidate.Path -Name "pv"' in SCRIPT
    assert '$Version.Trim() -ne "0.0.0.0"' in SCRIPT
    assert "$MissingInstallProcess.ExitCode -ne 7" in SCRIPT
    assert '"WebView2 Runtime missing"' in SCRIPT
    assert "Missing-WebView2 prerequisite failure still installed the native executable." in SCRIPT
    assert "Missing-WebView2 prerequisite failure created an uninstall registration." in SCRIPT
    assert "Missing-WebView2 prerequisite failure created a Start Menu shortcut." in SCRIPT
    assert '"WebView2 Runtime detected"' in SCRIPT


def test_installer_proof_binds_installed_bytes_and_windows_identity():
    assert "$SourceExecutableSha256 = Get-Sha256 $SourceExecutable" in SCRIPT
    assert "$InstalledSha256 = Get-Sha256 $InstalledExecutable" in SCRIPT
    assert "$InstalledSha256 -ne $SourceExecutableSha256" in SCRIPT
    assert "$IdentityVerifier -Executable $InstalledExecutable" in SCRIPT
    assert 'installer_signed = $false' in SCRIPT
    assert 'installed_executable_identity_match = $true' in SCRIPT
    assert 'external_python_required = $false' in SCRIPT


def test_installer_proof_exercises_local_and_public_native_boundaries():
    assert 'Invoke-InstalledBoundarySmoke -Executable $InstalledExecutable -Name "local"' in SCRIPT
    assert 'Invoke-InstalledBoundarySmoke -Executable $InstalledExecutable -Name "public"' in SCRIPT
    assert "-PublicDemo" in SCRIPT
    assert '"Native renderer requested: edgechromium"' in SCRIPT
    assert '"Native DOM loaded\\."' in SCRIPT
    assert "Get-Command python -CommandType Application" in SCRIPT


def test_installer_proof_requires_clean_uninstall_and_current_user_cleanup():
    assert "$UninstallKey" in SCRIPT
    assert "$StartMenuShortcut" in SCRIPT
    assert "$Uninstaller" in SCRIPT
    assert 'uninstall_registration_removed = $true' in SCRIPT
    assert 'shortcuts_removed = $true' in SCRIPT
    assert 'payload_files_removed = $true' in SCRIPT
    assert "Installed executable survived uninstall." in SCRIPT
    assert "Current-user uninstall registration survived uninstall." in SCRIPT
    assert "Start Menu shortcut survived uninstall." in SCRIPT


def test_installer_evidence_is_diagnostics_only_and_runtime_payload_free():
    assert 'schema_version = 2' in SCRIPT
    assert 'release_artifact = $false' in SCRIPT
    assert 'installer_published = $false' in SCRIPT
    assert 'webview2_runtime_strategy = "evergreen-prerequisite-detect-and-remediate"' in SCRIPT
    assert 'webview2_runtime_required = $true' in SCRIPT
    assert 'webview2_missing_install_exit_code = $MissingInstallProcess.ExitCode' in SCRIPT
    assert 'webview2_missing_install_blocked = $true' in SCRIPT
    assert 'webview2_runtime_payload_bundled = $false' in SCRIPT
    assert 'webview2_runtime_downloaded_in_ci = $false' in SCRIPT
    assert 'webview2_evergreen_policy = $true' in SCRIPT
    assert 'production_signing_required = $true' in SCRIPT
    assert 'production_timestamp_required = $true' in SCRIPT
    assert 'Remove-Item -LiteralPath $InstallerOutput -Recurse -Force' in SCRIPT
    assert '"*.exe", "*.pfx", "*.p12"' in SCRIPT

    upload = WORKFLOW.split("Upload installer-readiness evidence only", 1)[1]
    assert "installer-output" not in upload
    assert "native-build/dist" not in upload
    assert "installed" not in upload
    assert "*.exe" not in upload
    assert ".pfx" not in upload.lower()
    assert "/evidence/" in upload
