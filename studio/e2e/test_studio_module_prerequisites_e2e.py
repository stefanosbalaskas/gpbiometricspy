from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


PUBLIC_APP_PATH = Path(__file__).resolve().parents[2] / "app.py"
public_app = create_app_fixture(PUBLIC_APP_PATH, scope="module", timeout_secs=90)


def test_module_readiness_progresses_through_real_project_state(
    page: Page,
    public_app: ShinyAppProc,
) -> None:
    page.goto(public_app.url)
    expect(page.get_by_text("Public synthetic demonstration.", exact=False)).to_be_visible()
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )

    open_nav(page, "eda_scr", group="Analyze")
    expect(page.locator("#eda_scr-module_readiness")).to_contain_text(
        "Foundation QC pending",
        timeout=30_000,
    )
    expect(page.locator("#eda_scr-module_readiness")).to_contain_text(
        "Expert controls remain available"
    )

    page.get_by_role("tab", name="Home", exact=True).click()
    page.locator("#run_qc").click()
    expect(page.locator("#status")).to_contain_text(
        "Foundation QC complete.",
        timeout=90_000,
    )

    open_nav(page, "eda_scr", group="Analyze")
    expect(page.locator("#eda_scr-module_readiness")).to_contain_text(
        "Ready for guided analysis",
        timeout=30_000,
    )
    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    expect(page.locator("#eda_scr-module_readiness")).to_contain_text(
        "EDA / SCR result stored",
        timeout=30_000,
    )

    open_nav(page, "event_alignment", group="Integrate")
    expect(page.locator("#event_alignment-module_readiness")).to_contain_text(
        "Ready for guided analysis",
        timeout=30_000,
    )
    expect(page.locator("#event_alignment-module_readiness")).to_contain_text(
        "TTL/marker source"
    )

    open_nav(page, "multimodal", group="Integrate")
    expect(page.locator("#multimodal-module_readiness")).to_contain_text(
        "Events & Alignment required",
        timeout=30_000,
    )
    expect(page.locator("#multimodal-module_readiness")).to_contain_text(
        "Complete Events & Alignment"
    )

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
