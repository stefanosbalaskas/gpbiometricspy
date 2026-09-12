from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ISS = (ROOT / "tools/installer/gpbiometricspy_studio.iss").read_text(encoding="utf-8")
SCRIPT = (ROOT / ".github/scripts/test_studio_upgrade_policy_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-windowed-installer-readiness.yml").read_text(encoding="utf-8")


def test_upgrade_policy_uses_numeric_windows_file_version_and_stable_app_identity():
    assert "AppId=fd3ca1af-0ebb-5061-9c59-f7ab1079252e" in ISS
    assert "PrivilegesRequired=lowest" in ISS
    assert "TargetFileVersion = '{#FileVersion}'" in ISS
    assert "StrToVersion(TargetFileVersion, TargetVersion)" in ISS
    assert "ComparePackedVersion(InstalledVersion, TargetVersion)" in ISS
    assert "GetPackedVersion(Executable, Version)" in ISS
    assert "GetVersionNumbersString(Executable, VersionText)" in ISS
    assert "AppVersion" in ISS
    assert "0.1.6" not in ISS


def test_upgrade_policy_preserves_previous_install_location_and_choices():
    assert "UsePreviousAppDir=yes" in ISS
    assert "UsePreviousGroup=yes" in ISS
    assert "UsePreviousTasks=yes" in ISS
    assert "UsePreviousPrivileges=no" in ISS
    assert 'install_scope = "current-user"' in SCRIPT
    assert 'elevation_required = $false' in SCRIPT
    assert SCRIPT.count("-Directory $InstallRoot") == 1
    assert 'custom_install_path_preserved = $true' in SCRIPT


def test_upgrade_policy_persists_private_numeric_marker_with_uninstall_cleanup():
    assert '[Registry]' in ISS
    assert 'Software\\StefanosBalaskas\\gpbiometricspy Studio' in ISS
    assert 'ValueName: "InstalledFileVersion"' in ISS
    assert 'ValueData: "{#FileVersion}"' in ISS
    assert "uninsdeletevalue" in ISS
    assert "uninsdeletekeyifempty" in ISS
    assert 'UpgradePolicyValue = \'InstalledFileVersion\'' in ISS
    assert '$UpgradePolicyValue = "InstalledFileVersion"' in SCRIPT
    assert 'upgrade_registry_removed_on_uninstall = $true' in SCRIPT
    assert 'Private upgrade-policy registry key survived uninstall.' in SCRIPT


def test_upgrade_policy_supports_previous_installer_migration_fallback():
    assert "DetectInstalledStudioVersion" in ISS
    assert "RegQueryStringValue(HKCU, UpgradePolicyKey, UpgradePolicyValue, Marker)" in ISS
    assert "GetPackedVersion(Executable, Version)" in ISS
    assert "source=executable" in SCRIPT
    assert "migration fallback" in SCRIPT.lower()
    assert 'migration_fallback = "installed-executable-fixed-version"' in SCRIPT
    assert 'migration_fallback_repair_allowed = $true' in SCRIPT
    assert 'migration_fallback_repair_restored_bytes = $true' in SCRIPT


def test_upgrade_policy_allows_repair_and_upgrade_but_blocks_downgrade_fail_closed():
    assert "Upgrade policy: first install allowed" in ISS
    assert "Upgrade policy: same-version repair allowed" in ISS
    assert "Upgrade policy: in-place upgrade allowed" in ISS
    assert "Upgrade policy: downgrade blocked" in ISS
    assert "existing installation has indeterminate version; setup blocked fail-closed" in ISS
    assert "RegKeyExists(HKCU, UninstallRegistrationKey)" in ISS
    assert '$PreviousFileVersion = "0.1.6.0"' in SCRIPT
    assert '$TargetFileVersion -ne "0.1.7.0"' in SCRIPT
    assert '$FutureFileVersion = "0.1.8.0"' in SCRIPT
    assert "$DowngradeProcess.ExitCode -ne 7" in SCRIPT
    assert "Blocked downgrade mutated the installed executable." in SCRIPT
    assert "Blocked downgrade mutated the installed version marker." in SCRIPT
    assert 'upgrade_policy = "numeric-file-version-fail-closed"' in SCRIPT
    assert 'version_authority = "windows-fixed-file-version"' in SCRIPT
    assert 'same_version_repair_allowed = $true' in SCRIPT
    assert 'upgrade_allowed = $true' in SCRIPT
    assert 'downgrade_blocked = $true' in SCRIPT
    assert 'downgrade_payload_unchanged = $true' in SCRIPT
    assert 'downgrade_marker_unchanged = $true' in SCRIPT
    assert "BYPASS_DOWNGRADE" not in ISS
    assert "GPBIOMETRICSPY_CI_FORCE_DOWNGRADE" not in ISS


def test_upgrade_policy_runs_before_webview2_prerequisite_and_before_payload_mutation():
    prepare = ISS.split("function PrepareToInstall", 1)[1]
    assert prepare.index("CheckUpgradePolicy(UpgradeError)") < prepare.index("DetectWebView2Runtime")
    assert "[Files]" in ISS
    assert "PrepareToInstall" in ISS
    assert 'downgrade_exit_code = $DowngradeProcess.ExitCode' in SCRIPT


def test_upgrade_policy_live_proof_is_in_existing_diagnostics_only_workflow():
    lowered = WORKFLOW.lower()
    assert "test_studio_upgrade_policy_windows.ps1" in WORKFLOW
    assert "Exercise repair, upgrade and downgrade policy" in WORKFLOW
    assert '"upgrade-policy-work"' in WORKFLOW
    assert '"*.exe", "*.dll", "*.pfx", "*.p12"' in WORKFLOW
    assert "secrets." not in lowered
    assert "github.token" not in lowered
    assert "permissions:\n  contents: read" in lowered
    assert "timeout-minutes: 30" in lowered

    upload = WORKFLOW.split("Upload windowed-installer evidence only", 1)[1]
    assert "/evidence/" in upload
    assert "upgrade-policy-work" not in upload
    assert "*.exe" not in upload.lower()
    assert ".pfx" not in upload.lower()
    assert ".p12" not in upload.lower()


def test_upgrade_policy_proof_remains_unsigned_and_nonpublishing():
    assert 'release_artifact = $false' in SCRIPT
    assert 'installer_published = $false' in SCRIPT
    assert 'installer_signed = $false' in SCRIPT
    assert "Get-AuthenticodeSignature" in SCRIPT
    assert 'Status -ne "NotSigned"' in SCRIPT
    assert "Remove-Item -LiteralPath $WorkRoot -Recurse -Force" in SCRIPT
    assert "Upgrade-policy transient work root survived cleanup." in SCRIPT
