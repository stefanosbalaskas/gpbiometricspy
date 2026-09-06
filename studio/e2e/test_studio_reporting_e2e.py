from __future__ import annotations

import json
from pathlib import Path
import zipfile

import gpbiometricspy as gp
from playwright.sync_api import Page, expect
from shiny.playwright import controller
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _upload_participant(page: Page, participant_path: Path) -> None:
    upload = page.locator("#upload")
    upload.set_input_files(str(participant_path))

    def _uploaded(value) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], dict)
            and value[0].get("name") == participant_path.name
        )

    controller.AppTestValues(page).expect_input("upload", _uploaded, timeout=30.0)
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    assert int(page.locator("#row_count").inner_text().replace(",", "")) == 1_920


def _load_participant(page: Page, app: ShinyAppProc) -> Path:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    participant_path = Path(gp.kiosk_demo_files()[0])
    _upload_participant(page, participant_path)
    return participant_path


def _run_eda(page: Page) -> None:
    page.get_by_text("EDA / SCR Analysis", exact=True).click()
    expect(page.get_by_text("EDA / SCR analysis controls", exact=True)).to_be_visible()
    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    expect(page.locator("#eda_scr-decomposition_method")).not_to_have_text("Not run")


def _open_reporting(page: Page) -> None:
    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")


def _reset_session(page: Page) -> None:
    page.locator("#reset").click()
    expect(page.locator("#status")).to_contain_text(
        "Session reset. No dataset is loaded.",
        timeout=30_000,
    )
    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#row_count")).to_have_text("0", timeout=30_000)


def _download(page: Page, selector: str) -> Path:
    with page.expect_download(timeout=60_000) as download_info:
        page.locator(selector).click()
    path = download_info.value.path()
    assert path is not None
    return Path(path)


def _set_recipe_upload(page: Page, recipe_path: Path) -> None:
    page.locator("#reporting-recipe_upload").set_input_files(str(recipe_path))

    def _uploaded(value) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], dict)
            and value[0].get("name") == recipe_path.name
        )

    controller.AppTestValues(page).expect_input(
        "reporting-recipe_upload",
        _uploaded,
        timeout=30.0,
    )


def test_reporting_artifacts_downloads_and_recipe_restore(
    page: Page,
    app: ShinyAppProc,
    tmp_path: Path,
) -> None:
    participant_path = _load_participant(page, app)
    _run_eda(page)
    _open_reporting(page)

    expect(page.locator("#reporting-analysis_count")).to_have_text("1", timeout=60_000)
    expect(page.locator("#reporting-result_table_count")).not_to_have_text("", timeout=60_000)
    assert int(page.locator("#reporting-result_table_count").inner_text()) > 0

    title = "Studio reporting browser validation"
    subtitle = "Real packaged participant; EDA/SCR workflow"
    page.locator("#reporting-report_title").fill(title)
    page.locator("#reporting-report_subtitle").fill(subtitle)
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
    expect(page.locator("#reporting-methods_text")).not_to_contain_text(
        "Build reporting artifacts first."
    )
    expect(page.locator("#reporting-reproducibility_text")).to_contain_text(
        "structured analysis decision log"
    )
    expect(page.locator("#reporting-qc_supplement")).not_to_contain_text(
        "Build reporting artifacts first."
    )

    page.get_by_role("tab", name="Inventory", exact=True).click()
    expect(page.locator("#reporting-analysis_inventory")).to_contain_text(
        "eda_scr",
        timeout=60_000,
    )
    expect(page.locator("#reporting-result_catalog")).to_contain_text("eda_scr")
    expect(page.locator("#reporting-provenance")).to_be_visible()

    page.get_by_role("tab", name="Manifest", exact=True).click()
    expect(page.locator("#reporting-manifest_preview")).to_contain_text(
        '"raw_data_included": false'
    )
    expect(page.locator("#reporting-manifest_preview")).to_contain_text(
        '"analysis_outputs_included": false'
    )
    expect(page.locator("#reporting-replay_summary")).to_contain_text(
        "Recorded analysis workflows: 1"
    )
    expect(page.locator("#reporting-replay_summary")).to_contain_text(
        "Source data embedded: False"
    )

    page.get_by_role("tab", name="Downloads", exact=True).click()
    report_text = _download(page, "#reporting-download_report").read_text(encoding="utf-8")
    assert title in report_text
    assert subtitle in report_text
    assert "dataset SHA-256" in report_text
    assert "raw data embedded in project recipe: `False`" in report_text

    methods_text = _download(page, "#reporting-download_methods").read_text(encoding="utf-8")
    assert methods_text.strip()
    reproducibility_text = _download(page, "#reporting-download_repro").read_text(encoding="utf-8")
    assert "structured analysis decision log" in reproducibility_text.lower()

    manifest = json.loads(
        _download(page, "#reporting-download_manifest").read_text(encoding="utf-8")
    )
    assert manifest["studio"]["raw_data_included"] is False
    assert manifest["studio"]["analysis_outputs_included"] is False
    assert len(manifest["studio"]["dataset_sha256"]) == 64

    replay = _download(page, "#reporting-download_replay").read_text(encoding="utf-8")
    assert "run_eda_scr_analysis" in replay
    assert "dataset_fingerprint" in replay
    assert "gp.import_gazepoint_biometrics" in replay

    bundle_path = _download(page, "#reporting-download_bundle")
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
        assert bundled_recipe["analysis_inventory"][0]["analysis"] == "eda_scr"

    page.get_by_role("tab", name="Project recipe", exact=True).click()
    recipe_download = _download(page, "#reporting-download_recipe")
    recipe = json.loads(recipe_download.read_text(encoding="utf-8"))
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    assert recipe["analysis_inventory"][0]["analysis"] == "eda_scr"
    assert len(recipe["dataset"]["sha256"]) == 64
    recipe_path = tmp_path / "reporting-project-recipe.json"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")

    # A different loaded dataset must fail the fingerprint gate.
    _reset_session(page)
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )
    _open_reporting(page)
    page.get_by_role("tab", name="Project recipe", exact=True).click()
    _set_recipe_upload(page, recipe_path)
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

    # Reloading the exact original participant validates and restores metadata only.
    _reset_session(page)
    page.locator("#upload").set_input_files([])
    _upload_participant(page, participant_path)
    _open_reporting(page)
    page.get_by_role("tab", name="Project recipe", exact=True).click()
    _set_recipe_upload(page, recipe_path)
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
    expect(page.locator("#reporting-identity_summary")).to_contain_text("Analyses: 0")
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)
