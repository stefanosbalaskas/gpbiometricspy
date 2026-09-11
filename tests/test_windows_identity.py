from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from PIL import Image

from tools.pyinstaller.generate_windows_identity import PRODUCT_NAME, TARGETS, generate_identity, windows_fixed_version


ROOT = Path(__file__).resolve().parents[1]


def _project() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]


def _project_version() -> str:
    return str(_project()["version"])


def _license_copyright() -> str:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    match = re.search(r"^Copyright \(c\) .+$", text, flags=re.MULTILINE)
    assert match is not None
    return match.group(0).strip()


def test_windows_fixed_version_maps_dev_suffix_into_fourth_component():
    assert windows_fixed_version("0.1.6.dev0") == (0, 1, 6, 0)
    assert windows_fixed_version("1.2.3.dev4") == (1, 2, 3, 4)
    assert windows_fixed_version("2.5") == (2, 5, 0, 0)


def test_generate_windows_identity_uses_project_and_license_sources(tmp_path):
    identity = generate_identity(ROOT, tmp_path, "native")
    project = _project()
    project_version = str(project["version"])
    fixed = windows_fixed_version(project_version)
    repository = str(project["urls"]["Repository"]).rstrip("/")

    assert identity["package_version"] == project_version
    assert identity["product_version"] == project_version
    assert identity["file_version"] == ".".join(str(part) for part in fixed)
    assert identity["fixed_file_version"] == list(fixed)
    assert identity["product_name"] == PRODUCT_NAME
    assert identity["file_description"] == "gpbiometricspy Studio Desktop"
    assert identity["legal_copyright"] == _license_copyright()
    assert identity["company_name"] == project["authors"][0]["name"]
    assert identity["homepage_url"] == project["urls"]["Homepage"]
    assert identity["repository_url"] == repository
    assert identity["support_url"] == project["urls"]["Issues"]
    assert identity["updates_url"] == repository + "/releases"
    assert len(identity["version_resource_sha256"]) == 64
    assert len(identity["icon_sha256"]) == 64

    manifest = json.loads((tmp_path / "windows-identity.json").read_text(encoding="utf-8"))
    assert manifest == identity

    version_text = (tmp_path / "version-info.txt").read_text(encoding="utf-8")
    assert "ProductName" in version_text
    assert "gpbiometricspy Studio" in version_text
    assert "CompanyName" in version_text
    assert str(project["authors"][0]["name"]) in version_text

    with Image.open(tmp_path / "gpbiometricspy-studio.ico") as icon:
        assert icon.format == "ICO"
        assert icon.size == (256, 256)


def test_identity_targets_keep_product_name_and_truthful_filenames(tmp_path):
    for target, expected in TARGETS.items():
        output = tmp_path / target
        identity = generate_identity(ROOT, output, target)
        assert identity["product_name"] == PRODUCT_NAME
        assert identity["internal_name"] == expected["internal_name"]
        assert identity["original_filename"] == expected["original_filename"]
        assert identity["original_filename"].endswith(".exe")