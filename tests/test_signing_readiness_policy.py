from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / ".github/scripts/test_studio_signing_readiness_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-signing-readiness.yml").read_text(encoding="utf-8")


def _executable_powershell(text: str) -> str:
    """Return non-comment PowerShell lines for command-policy assertions."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_signing_readiness_is_explicitly_test_only_and_hash_bound():
    assert 'test_only = $true' in SCRIPT
    assert 'release_artifact = $false' in SCRIPT
    assert 'certificate_ephemeral = $true' in SCRIPT
    assert 'certificate_persisted = $false' in SCRIPT
    assert 'unsigned_sha256 = $UnsignedSha256' in SCRIPT
    assert 'signed_sha256 = $SignedSha256' in SCRIPT
    assert 'production_digest_algorithm = "SHA256"' in SCRIPT
    assert 'production_timestamp_digest_algorithm = "SHA256"' in SCRIPT
    assert 'production_timestamp_required = $true' in SCRIPT


def test_signing_readiness_does_not_use_repository_signing_secrets():
    lowered = WORKFLOW.lower()
    assert "secrets." not in lowered
    assert ".pfx" not in lowered
    assert ".p12" not in lowered
    assert "private key" not in lowered


def test_signing_readiness_never_uploads_test_signed_executable_or_pfx():
    upload_section = WORKFLOW.split("Upload signing-readiness evidence only", 1)[1]
    upload_section = upload_section.split("Assert no signed executable is retained as evidence", 1)[0]
    assert "*.exe" not in upload_section
    assert ".exe" not in upload_section
    assert ".pfx" not in upload_section.lower()
    assert ".p12" not in upload_section.lower()
    assert "signing-provenance.json" in upload_section
    assert "signtool-verify.log" in upload_section


def test_signing_readiness_uses_noninteractive_bounded_signtool_sha256_path():
    executable_script = _executable_powershell(SCRIPT)
    assert "CertificateRequest" in executable_script
    assert "CreateSelfSigned" in executable_script
    assert '"1.3.6.1.5.5.7.3.3", "Code Signing"' in executable_script
    assert "New-SelfSignedCertificate" not in executable_script
    assert "Set-AuthenticodeSignature" not in executable_script
    assert "Get-AuthenticodeSignature" in executable_script
    assert "Invoke-BoundedProcess" in executable_script
    assert "Get-BoundedAuthenticodeSnapshot" in executable_script
    assert '@("sign", "/fd", "SHA256", "/f", $PfxPath, "/p", $PfxPassword, $Executable)' in executable_script
    assert '@("verify", "/pa", "/v", $Executable)' in executable_script
    assert "-TimeoutSeconds 60" in executable_script
    assert "-TimeoutSeconds 30" in executable_script
    assert "Remove-TestCertificate" in executable_script
    assert "Remove-Item -LiteralPath $PfxPath -Force" in executable_script
