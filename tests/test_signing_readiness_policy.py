from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / ".github/scripts/test_studio_signing_readiness_windows.ps1").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/studio-signing-readiness.yml").read_text(encoding="utf-8")


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


def test_signing_readiness_never_uploads_test_signed_executable():
    upload_section = WORKFLOW.split("Upload signing-readiness evidence only", 1)[1]
    upload_section = upload_section.split("Assert no signed executable is retained as evidence", 1)[0]
    assert "*.exe" not in upload_section
    assert ".exe" not in upload_section
    assert "signing-provenance.json" in upload_section
    assert "signtool-verify.log" in upload_section


def test_signing_readiness_uses_authenticode_and_sha256():
    assert "Get-AuthenticodeSignature" in SCRIPT
    assert "Set-AuthenticodeSignature" in SCRIPT
    assert "-HashAlgorithm SHA256" in SCRIPT
    assert "verify /pa /v" in SCRIPT
    assert "New-SelfSignedCertificate" in SCRIPT
    assert "Remove-TestCertificate" in SCRIPT
