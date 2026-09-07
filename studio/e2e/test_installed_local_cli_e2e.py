from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import zipfile

import gpbiometricspy as gp
import pytest
from playwright.sync_api import Page, expect
from shiny.playwright import controller


INSTALLED_LOCAL_URL = os.environ.get("GPBIOMETRICSPY_INSTALLED_LOCAL_URL")
INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")
INSTALLED_PYTHON = os.environ.get("GPBIOMETRICSPY_INSTALLED_PYTHON")

pytestmark = pytest.mark.skipif(
    not INSTALLED_LOCAL_URL,
    reason="installed-distribution local Studio URL is not configured",
)


def _reset_session(page: Page) -> None:
    page.locator("#reset").click()
    expect(page.locator("#status")).to_contain_text(
        "Session reset. No dataset is loaded.",
        timeout=30_000,
    )
    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#row_count")).to_have_text("0", timeout=30_000)


def _open_reporting_recipe(page: Page) -> None:
    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    page.get_by_role("tab", name="Project recipe", exact=True).click()


def _upload_recipe(page: Page, recipe_path: Path) -> None:
    controller.InputFile(page, "reporting-recipe_upload").set(
        recipe_path,
        expect_complete_timeout=30_000,
    )


def test_installed_distribution_local_console_browser_path(page: Page) -> None:
    assert INSTALLED_LOCAL_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    assert INSTALLED_PYTHON is not None

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    assert page.get_by_text("Public synthetic demonstration.", exact=False).count() == 0
    expect(page.locator("#load_upload")).to_be_visible()
    expect(page.locator("#upload")).to_be_attached()

    participant_files = gp.kiosk_demo_files()
    assert len(participant_files) >= 2
    participant_path = Path(participant_files[0])
    mismatch_participant_path = Path(participant_files[1])
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

    page.get_by_text("Gaze / Fixation / AOI Analysis", exact=True).click()
    expect(page.get_by_text("Gaze / fixation / saccade / AOI controls", exact=True)).to_be_visible()
    page.locator("#gaze-run").click()
    expect(page.locator("#gaze-status")).to_contain_text(
        "Gaze workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    assert int(page.locator("#gaze-saccade_count").inner_text().replace(",", "")) > 0

    page.get_by_text("Pupil Analysis", exact=True).click()
    expect(page.get_by_text("Pupil analysis controls", exact=True)).to_be_visible()
    page.locator("#pupil-run").click()
    expect(page.locator("#pupil-status")).to_contain_text(
        "Pupil workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    assert int(page.locator("#pupil-blink_count").inner_text().replace(",", "")) >= 0

    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")
    expect(page.locator("#reporting-analysis_count")).to_have_text("2", timeout=60_000)

    title = f"Installed {INSTALLED_ARTIFACT_KIND} local gaze + pupil replay report"
    page.locator("#reporting-report_title").fill(title)
    page.locator("#reporting-report_subtitle").fill(
        "Packaged participant; Foundation QC, Advanced QC, Gaze, and Pupil analyses"
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
    replay_path = Path(bundle_path).with_name(
        f"gpbiometricspy_studio_{INSTALLED_ARTIFACT_KIND}_replay.py"
    )
    mismatch_replay_path = Path(bundle_path).with_name(
        f"gpbiometricspy_studio_{INSTALLED_ARTIFACT_KIND}_mismatch_replay.py"
    )
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
        replay_text = archive.read("gpbiometricspy_studio_replay.py").decode("utf-8")
        assert bundled_recipe["raw_data_included"] is False
        assert bundled_recipe["analysis_outputs_included"] is False
        bundled_analyses = {
            item.get("analysis") for item in bundled_recipe["analysis_inventory"]
        }
        assert bundled_analyses == {"gaze", "pupil"}
        assert "from studio.gaze_services import run_gaze_analysis" in replay_text
        assert "from studio.pupil_services import run_pupil_analysis" in replay_text
        assert 'analyses["gaze"]' in replay_text
        assert 'analyses["pupil"]' in replay_text

    placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
    assert placeholder in replay_text

    mismatch_replay_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(mismatch_participant_path)!r})",
            1,
        ),
        encoding="utf-8",
    )
    mismatch_result = subprocess.run(
        [INSTALLED_PYTHON, str(mismatch_replay_path)],
        cwd=mismatch_replay_path.parent,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert mismatch_result.returncode != 0
    mismatch_output = f"{mismatch_result.stdout}\n{mismatch_result.stderr}"
    assert "Dataset fingerprint mismatch:" in mismatch_output

    replay_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(participant_path)!r})",
            1,
        ),
        encoding="utf-8",
    )
    replay_result = subprocess.run(
        [INSTALLED_PYTHON, str(replay_path)],
        cwd=replay_path.parent,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert replay_result.returncode == 0, (
        "Installed replay script failed.\n"
        f"stdout:\n{replay_result.stdout}\n"
        f"stderr:\n{replay_result.stderr}"
    )
    assert replay_result.stdout.strip()

    page.get_by_role("tab", name="Project recipe", exact=True).click()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    download_path = download_info.value.path()
    assert download_path is not None
    downloaded_recipe_path = Path(download_path)
    recipe = json.loads(downloaded_recipe_path.read_text(encoding="utf-8"))
    recipe_path = downloaded_recipe_path.with_suffix(".json")
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    recipe_analyses = {item.get("analysis") for item in recipe["analysis_inventory"]}
    assert recipe_analyses == {"gaze", "pupil"}
    operations = [event.get("operation") for event in recipe["provenance"]]
    assert "run_advanced_qc" in operations

    # A different loaded dataset must fail the installed fingerprint gate.
    _reset_session(page)
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )
    _open_reporting_recipe(page)
    _upload_recipe(page, recipe_path)
    page.locator("#reporting-validate_recipe").click()
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "dataset_fingerprint_match",
        timeout=30_000,
    )
    page.locator("#reporting-restore_recipe").click()
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "Project restore blocked:",
        timeout=30_000,
    )
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "dataset_fingerprint_match"
    )

    # The exact original participant validates and restores metadata only.
    _reset_session(page)
    page.locator("#upload").set_input_files([])
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

    _open_reporting_recipe(page)
    _upload_recipe(page, recipe_path)
    page.locator("#reporting-validate_recipe").click()
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "Recipe valid and dataset fingerprint matches. Metadata can be restored.",
        timeout=30_000,
    )
    expect(page.locator("#reporting-recipe_checks")).to_contain_text(
        "dataset_fingerprint_match",
        timeout=30_000,
    )
    page.locator("#reporting-restore_recipe").click()
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "Project metadata restored. Analysis outputs were intentionally not restored",
        timeout=30_000,
    )
    expect(page.locator("#status")).to_contain_text(
        "Project recipe restored after exact dataset fingerprint verification."
    )
    expect(page.locator("#reporting-analysis_count")).to_have_text("0")
    expect(page.locator("#reporting-result_table_count")).to_have_text("0")
    page.get_by_role("tab", name="Report", exact=True).click()
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Analyses: 0",
        timeout=30_000,
    )

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
