from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ISS = (ROOT / "tools/installer/gpbiometricspy_studio.iss").read_text(encoding="utf-8")
GENERATOR = (ROOT / "tools/pyinstaller/generate_windows_identity.py").read_text(encoding="utf-8")
VERIFIER = (ROOT / ".github/scripts/assert_studio_windows_identity.ps1").read_text(encoding="utf-8")


def _project() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]


def test_installer_metadata_matches_authoritative_project_urls():
    project = _project()
    repository = str(project["urls"]["Repository"]).rstrip("/")
    support = str(project["urls"]["Issues"])
    updates = repository + "/releases"
    publisher = str(project["authors"][0]["name"])

    assert f"AppPublisher={publisher}" in ISS
    assert f"AppPublisherURL={repository}" in ISS
    assert f"AppSupportURL={support}" in ISS
    assert f"AppUpdatesURL={updates}" in ISS
    assert f"VersionInfoCompany={publisher}" in ISS


def test_webview2_url_is_only_prerequisite_remediation_not_product_support():
    webview = "https://developer.microsoft.com/microsoft-edge/webview2/"
    assert f"AppSupportURL={webview}" not in ISS
    assert "WebView2DownloadUrl = 'https://developer.microsoft.com/microsoft-edge/webview2/'" in ISS
    assert ISS.count(webview) == 1


def test_executable_identity_sources_publisher_and_urls_from_pyproject():
    assert "def _project_application_metadata" in GENERATOR
    assert 'project.get("authors")' in GENERATOR
    assert 'urls.get("Repository"' in GENERATOR
    assert 'urls.get("Homepage"' in GENERATOR
    assert 'urls.get("Issues"' in GENERATOR
    assert '"company_name"' in GENERATOR
    assert '"homepage_url"' in GENERATOR
    assert '"repository_url"' in GENERATOR
    assert '"support_url"' in GENERATOR
    assert '"updates_url"' in GENERATOR
    assert '("CompanyName", identity["company_name"])' in GENERATOR


def test_compiled_executable_verifier_requires_company_name():
    assert 'Assert-Equal "CompanyName" $Expected.company_name $Actual.CompanyName' in VERIFIER


def test_icon_remains_explicitly_evaluation_generated_asset():
    assert "deterministic, dependency-light evaluation icon" in GENERATOR
    assert "_draw_icon" in GENERATOR
