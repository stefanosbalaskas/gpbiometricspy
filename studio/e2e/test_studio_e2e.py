from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _load_demo(page: Page, app: ShinyAppProc) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text("Bundled synthetic kiosk demo", timeout=60_000)
    rows_text = page.locator("#row_count").inner_text()
    cols_text = page.locator("#column_count").inner_text()
    assert int(rows_text.replace(",", "")) > 0
    assert int(cols_text.replace(",", "")) > 0


def _open_reporting(page: Page) -> None:
    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")


def test_studio_shell_loads_demo_and_exposes_reporting(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _open_reporting(page)
    expect(page.get_by_text("Raw rows and cached analysis-result tables are intentionally excluded.", exact=False)).to_be_visible()
    expect(page.locator("#reporting-operation_count")).not_to_have_text("0")


def test_reporting_build_and_recipe_download_preserve_privacy(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _open_reporting(page)

    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")

    page.get_by_text("Project recipe", exact=True).click()
    expect(page.get_by_text("Save project recipe", exact=True)).to_be_visible()

    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    recipe = json.loads(Path(path).read_text(encoding="utf-8"))

    assert recipe["schema"] == "gpbiometricspy-studio-project-recipe"
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    assert len(recipe["dataset"]["sha256"]) == 64
    assert recipe["dataset"]["row_count"] > 0
    assert recipe["dataset"]["column_count"] > 0
