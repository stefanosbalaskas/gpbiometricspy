from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def test_reporting_project_timeline_summarises_recorded_work_without_source_names(
    page: Page,
    app: ShinyAppProc,
) -> None:
    page.goto(app.url)
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )

    page.locator("#run_qc").click()
    expect(page.get_by_role("status")).to_contain_text(
        "Foundation QC complete",
        timeout=90_000,
    )

    open_nav(page, "eda_scr", group="Analyze")
    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )

    open_nav(page, "reporting")
    page.get_by_role("tab", name="Inventory", exact=True).click()
    page.get_by_role("tab", name="Timeline", exact=True).click()

    timeline = page.locator("#reporting-project_timeline")
    expect(timeline).to_contain_text("Synthetic dataset loaded", timeout=60_000)
    expect(timeline).to_contain_text("Foundation QC completed")
    expect(timeline).to_contain_text("EDA / SCR completed")
    expect(timeline).to_contain_text("Project")
    expect(timeline).to_contain_text("Quality")
    expect(timeline).to_contain_text("Analyze")
    expect(timeline).not_to_contain_text("Bundled synthetic kiosk demo")
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
