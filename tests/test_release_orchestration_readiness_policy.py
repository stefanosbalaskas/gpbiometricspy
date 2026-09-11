from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / ".github/scripts/test_studio_release_orchestration_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-release-orchestration-readiness.yml").read_text(encoding="utf-8")


def test_orchestration_is_exact_source_bound_and_uses_windowed_installer_inputs():
    assert "SourceCommit must be an exact 40-character Git SHA." in SCRIPT
    assert "git -C $RepoRoot rev-parse HEAD" in SCRIPT
    assert "source commit does not match checked-out HEAD" in SCRIPT
    assert "gpbiometricspy_studio_native_windowed.spec" in SCRIPT
    assert "gpbiometricspy_studio.iss" in SCRIPT
    assert "$PeSubsystem -ne 2" not in SCRIPT  # direct function result comparison is used
    assert "IMAGE_SUBSYSTEM_WINDOWS_GUI (2)" in SCRIPT
    assert 'SOURCE_COMMIT: ${{ github.event.pull_request.head.sha || github.sha }}' in WORKFLOW


def test_orchestration_signs_executable_before_compiling_and_signs_installer_after_compile():
    exe_sign = SCRIPT.index("Invoke-SignToolSign -SignTool $SignTool -Target $SourceExecutable")
    compile_installer = SCRIPT.index('Write-Host "Compiling installer from the already-signed GUI bundle..."')
    installer_sign = SCRIPT.index("Invoke-SignToolSign -SignTool $SignTool -Target $Installer")
    assert exe_sign < compile_installer < installer_sign
    assert '@("sign", "/fd", "SHA256"' in SCRIPT
    assert "executable_signed_before_installer_compile = $true" in SCRIPT
    assert "installer_signed_after_compile = $true" in SCRIPT


def test_orchestration_installs_signed_chain_and_requires_byte_and_signer_identity():
    assert "Start-Process -FilePath $Installer" in SCRIPT
    assert "Installed executable is not byte-identical to the signed source executable." in SCRIPT
    assert "Assert-EphemeralSignature -Path $InstalledExecutable" in SCRIPT
    assert "installed_executable_matches_signed_source = $true" in SCRIPT
    assert "signer_identity_consistent" in SCRIPT
    assert "uninstall_verified = $true" in SCRIPT
    assert "Installed payload files survived signed-chain uninstall" in SCRIPT
    assert "Application shortcut survived signed-chain uninstall" in SCRIPT


def test_orchestration_preserves_real_production_signing_timestamp_and_attestation_boundary():
    assert "certificate_ephemeral = $true" in SCRIPT
    assert "certificate_persisted = $false" in SCRIPT
    assert "trust_store_mutated = $false" in SCRIPT
    assert "timestamped = $false" in SCRIPT
    assert "production_trusted_certificate_required = $true" in SCRIPT
    assert "production_timestamp_required = $true" in SCRIPT
    assert 'production_timestamp_digest_algorithm = "SHA256"' in SCRIPT
    assert "production_release_attestation_required = $true" in SCRIPT
    assert "production_protected_environment_required = $true" in SCRIPT
    assert "X509Store" not in SCRIPT
    assert "New-SelfSignedCertificate" not in SCRIPT


def test_orchestration_binds_to_provenance_contract_and_sha256_checksums():
    assert "test_studio_release_provenance_windows.ps1" in SCRIPT
    assert "test_release_provenance_readiness_policy.py" in SCRIPT
    assert "tools/release/requirements.txt" in SCRIPT
    assert 'sbom_contract = "CycloneDX 1.6 via studio-release-provenance-readiness"' in SCRIPT
    assert 'checksums_algorithm = "SHA256"' in SCRIPT
    assert "provenance_contract_sha256 = $ContractHashes" in SCRIPT
    assert "SHA256SUMS.txt" in SCRIPT


def test_orchestration_workflow_is_secret_free_nonpublishing_and_diagnostics_only():
    lowered = WORKFLOW.lower()
    assert "permissions:\n  contents: read" in lowered
    assert "secrets." not in lowered
    assert "github.token" not in lowered
    assert "id-token: write" not in lowered
    assert "attestations: write" not in lowered
    assert "actions/attest" not in lowered
    assert "timeout-minutes: 30" in lowered

    upload = WORKFLOW.split("Upload release-orchestration evidence only", 1)[1]
    assert "/evidence/" in upload
    assert "installer-output" not in upload
    assert "/dist" not in upload.lower()
    assert "*.exe" not in upload.lower()
    assert ".pfx" not in upload.lower()


def test_orchestration_cleanup_is_fail_closed_and_retains_no_binary_or_key_material():
    for transient in ("$InstallerOutput", "$DistRoot", "$BuildRoot", "$VenvRoot", "$SigningRoot"):
        assert transient in SCRIPT
        assert "Remove-Item -LiteralPath $Transient -Recurse -Force" in SCRIPT
    assert '"*.exe", "*.dll", "*.pfx", "*.p12", "*.pem", "*.key"' in SCRIPT
    assert "Ephemeral signing PFX survived cleanup." in SCRIPT
    assert "Uninstall registration survived final cleanup." in SCRIPT
