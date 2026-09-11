from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / ".github/scripts/test_studio_release_provenance_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-release-provenance-readiness.yml").read_text(encoding="utf-8")
RELEASE_REQUIREMENTS = (ROOT / "tools/release/requirements.txt").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_release_provenance_tooling_is_pinned_and_isolated_from_runtime_dependencies():
    assert "cyclonedx-bom==7.3.1" in RELEASE_REQUIREMENTS
    assert "cyclonedx-bom" not in PYPROJECT
    assert 'Join-Path $ArtifactsDir "provenance-tool-venv"' in SCRIPT
    assert "-m pip install -r $ReleaseRequirements" in SCRIPT
    assert "$CycloneDxVersion -ne \"7.3.1\"" in SCRIPT


def test_release_provenance_builds_the_windowed_installer_without_publishing_it():
    assert "gpbiometricspy_studio_native_windowed.spec" in SCRIPT
    assert "gpbiometricspy_studio.iss" in SCRIPT
    assert "$SourcePeSubsystem -ne 2" in SCRIPT
    assert '[string](Get-AuthenticodeSignature -LiteralPath $Installer).Status -ne "NotSigned"' in SCRIPT
    assert 'release_artifact = $false' in SCRIPT
    assert 'published = $false' in SCRIPT
    assert 'signed = $false' in SCRIPT
    assert 'attested = $false' in SCRIPT
    assert 'binary_retained_as_evidence = $false' in SCRIPT


def test_release_provenance_sbom_targets_actual_build_venv_with_pollution_mitigation():
    assert "-m cyclonedx_py environment" in SCRIPT
    assert "--spec-version 1.6" in SCRIPT
    assert "--output-format JSON" in SCRIPT
    assert "--output-reproducible" in SCRIPT
    assert "--validate" in SCRIPT
    assert "--pyproject $PyprojectPath" in SCRIPT
    assert "$BuildPython" in SCRIPT
    assert "Remove-Item Env:PYTHONPATH" in SCRIPT
    assert "Remove-Item Env:PYTHONHOME" in SCRIPT
    assert "Remove-Item Env:VIRTUAL_ENV" in SCRIPT
    assert 'sbom_target = "actual-build-venv"' in SCRIPT
    assert '"PYTHONPATH-cleared", "PYTHONHOME-cleared", "VIRTUAL_ENV-cleared"' in SCRIPT
    assert '[string]$Sbom.bomFormat -ne "CycloneDX"' in SCRIPT
    assert '[string]$Sbom.specVersion -ne "1.6"' in SCRIPT
    assert '"shiny", "pywebview", "PyInstaller"' in SCRIPT


def test_release_provenance_records_sha256_checksums_and_build_inputs():
    assert 'checksums_algorithm = "SHA256"' in SCRIPT
    assert "SHA256SUMS.txt" in SCRIPT
    assert "$InstallerSha256" in SCRIPT
    assert "$SourceExecutableSha256" in SCRIPT
    assert "$IdentityManifestSha256" in SCRIPT
    assert "$SbomSha256" in SCRIPT
    assert "$FreezeSha256" in SCRIPT
    assert "$PipListSha256" in SCRIPT
    for expected in (
        "$PyprojectPath",
        "$SpecPath",
        "$InstallerScript",
        "$PackagingRequirements",
        "$ReleaseRequirements",
        "$IdentityGenerator",
        "$IdentityVerifier",
        "$ThisScript",
    ):
        assert expected in SCRIPT
    assert "build_input_sha256 = $InputHashes" in SCRIPT


def test_release_provenance_binds_source_and_execution_identity_without_conflating_them():
    assert "SourceCommit must be an exact 40-character Git SHA." in SCRIPT
    assert "source_commit = $SourceCommit.ToLowerInvariant()" in SCRIPT
    assert "checkout_sha = $CheckoutSha.ToLowerInvariant()" in SCRIPT
    assert "github_run_id = $env:GITHUB_RUN_ID" in SCRIPT
    assert "github_run_attempt = $env:GITHUB_RUN_ATTEMPT" in SCRIPT
    assert 'SOURCE_COMMIT: ${{ github.event.pull_request.head.sha || github.sha }}' in WORKFLOW
    assert "source_commit -ne $env:SOURCE_COMMIT.ToLowerInvariant()" in WORKFLOW


def test_release_provenance_uses_authoritative_inno_version_source_not_zero_file_version():
    assert "DisplayVersion" in SCRIPT
    assert 'Source = "uninstall-registry"' in SCRIPT
    assert 'Source = "iscc-help-banner"' in SCRIPT
    assert '$DisplayVersion.Trim() -ne "0.0.0.0"' in SCRIPT
    assert "installer_tool_version_source = $InnoEvidence.Source" in SCRIPT
    assert "installer_compiler_sha256 = $InnoCompilerSha256" in SCRIPT
    assert ".VersionInfo.FileVersion" not in SCRIPT


def test_readiness_workflow_is_secret_free_non_attesting_and_diagnostics_only():
    lowered = WORKFLOW.lower()
    assert "permissions:\n  contents: read" in lowered
    assert "secrets." not in lowered
    assert "github.token" not in lowered
    assert "id-token: write" not in lowered
    assert "attestations: write" not in lowered
    assert "actions/attest" not in lowered
    assert "timeout-minutes: 25" in lowered
    assert 'production_release_attestation_required = $true' in SCRIPT
    assert 'readiness_oidc_used = $false' in SCRIPT
    assert 'readiness_attestation_permissions_used = $false' in SCRIPT
    assert 'slsa_claimed = $false' in SCRIPT

    upload = WORKFLOW.split("Upload release-provenance evidence only", 1)[1]
    assert "/evidence/" in upload
    assert "installer-output" not in upload
    assert "/dist" not in upload.lower()
    assert "build-venv" not in upload.lower()
    assert "provenance-tool-venv" not in upload.lower()
    assert "*.exe" not in upload.lower()
    assert ".pfx" not in upload.lower()
    assert ".p12" not in upload.lower()


def test_release_provenance_cleanup_is_fail_closed():
    for transient in ("$InstallerOutput", "$DistRoot", "$BuildRoot", "$BuildVenv", "$ToolVenv"):
        assert f"Remove-Item -LiteralPath {transient}" in SCRIPT
    assert '"*.exe", "*.pfx", "*.p12"' in SCRIPT
    assert "Transient release-provenance path survived cleanup" in SCRIPT
    assert "Release-provenance evidence must not retain executables or signing-key material." in SCRIPT
