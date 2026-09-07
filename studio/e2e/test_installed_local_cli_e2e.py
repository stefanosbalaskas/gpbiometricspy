from __future__ import annotations

import json
import os
from pathlib import Path
import zipfile

import gpbiometricspy as gp
import pytest
from playwright.sync_api import Page, expect
from shiny.playwright import controller


INSTALLED_LOCAL_URL = os.environ.get("GPBIOMETRICSPY_INSTALLED_LOCAL_URL")
INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")

pytestmark = pytest.mark.skipif(
    not INSTALLED_LOCAL_URL,
    reason="installed-distribution local Studio URL is not configured",
)


def test_installed_distribution_local_console_browser_path(page: Page) -> None:
    assert INSTALLED_LOCAL_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    assert page.get_by_text("Public synthetic demonstration.", exact=False).count() == 0
    expect(page.locator("#load_upload")).to_be_visible()
    expect(page.locator("#upload")).to_be_attached()

    participant_path = Path(gp.kiosk_demo_files()[0])
    controller.InputFile(page, "upload").set(
        participant_path,
        expect_complete_timeout=30_000,
    )
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("1,920", timeout=60_000)
    expect(page.locator("#dataset_name")).not_to_have_text("No dataset")

    page.locator("#run_qc").click()
    expect(page.locator("#status")).to_contain_text(
        "Foundation QC complete.",
        timeout=90_000,
    )

    page.get_by_text("Quality Control", exact=True).click()
    expect(page.get_by_text("Advanced QC settings", exact=True)).to_be_visible()
    page.locator("#qc-run").click()
    expect(page.locator("#qc-status")).to_contain_text(
        "Advanced QC complete using public gpbiometricspy APIs.",
        timeout=120_000,
    )
    expect(page.locator("#qc-time_overview")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-time_plot img")).to_be_visible(timeout=60_000)

    page.get_by_role("tab", name="Physiology", exact=True).click()
    expect(page.locator("#qc-physiology_quality")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-physiology_plot img")).to_be_visible(timeout=60_000)

    page.get_by_role("tab", name="Gaze", exact=True).click()
    expect(page.locator("#qc-gaze_summary")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-gaze_checks")).to_be_visible(timeout=60_000)

    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")
    expect(page.locator("#reporting-analysis_count")).to_have_text("0", timeout=60_000)

    title = f"Installed {INSTALLED_ARTIFACT_KIND} local QC report"
    page.locator("#reporting-report_title").fill(title)
    page.locator("#reporting-report_subtitle").fill(
        "Packaged participant; Foundation and Advanced QC"
    )
    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )
    expect(page.locator("#reporting-package_report_overview")).to_contain_text(
        "report_created",
        timeout=60_000,
    )
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Raw rows embedded in recipe: False"
    )
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Analysis outputs embedded in recipe: False"
    )
    expect(page.locator("#reporting-report_preview")).to_contain_text(title)
    expect(page.locator("#reporting-report_preview")).to_contain_text("dataset SHA-256")

    page.get_by_role("tab", name="Methods & reproducibility", exact=True).click()
    expect(page.locator("#reporting-qc_supplement")).not_to_contain_text(
        "Build reporting artifacts first."
    )

    page.get_by_role("tab", name="Manifest", exact=True).click()
    expect(page.locator("#reporting-manifest_preview")).to_contain_text(
        '"raw_data_included": false'
    )
    expect(page.locator("#reporting-manifest_preview")).to_contain_text(
        '"analysis_outputs_included": false'
    )
    expect(page.locator("#reporting-replay_summary")).to_contain_text(
        "Source data embedded: False"
    )

    page.get_by_role("tab", name="Downloads", exact=True).click()
    with page.expect_download(timeout=60_000) as manifest_download:
        page.locator("#reporting-download_manifest").click()
    manifest_path = manifest_download.value.path()
    assert manifest_path is not None
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert manifest["studio"]["raw_data_included"] is False
    assert manifest["studio"]["analysis_outputs_included"] is False
    assert len(manifest["studio"]["dataset_sha256"]) == 64

    with page.expect_download(timeout=60_000) as bundle_download:
        page.locator("#reporting-download_bundle").click()
    bundle_path = bundle_download.value.path()
    assert bundle_path is not None
    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())
        assert "gpbiometricspy_studio_report.md" in names
        assert "gpbiometricspy_studio_manifest.json" in names
        assert "gpbiometricspy_studio_project_recipe.json" in names
        assert "gpbiometricspy_studio_replay.py" in names
        assert not any(name.endswith("raw.csv") or "raw_data" in name for name in names)
        bundled_recipe = json.loads(
            archive.read("gpbiometricspy_studio_project_recipe.json").decode("utf-8")
        )
        assert bundled_recipe["raw_data_included"] is False
        assert bundled_recipe["analysis_outputs_included"] is False

    page.get_by_role("tab", name="Project recipe", exact=True).click()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    download_path = download_info.value.path()
    assert download_path is not None
    recipe = json.loads(Path(download_path).read_text(encoding="utf-8"))
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    operations = [event.get("operation") for event in recipe["provenance"]]
    assert "run_advanced_qc" in operations

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
