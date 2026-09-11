from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def test_multimodal_guided_start_advances_from_alignment_to_multimodal(
    page: Page,
    app: ShinyAppProc,
) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    page.locator("#guided_start").select_option("multimodal")
    expect(page.locator("#guided_start_description")).to_contain_text(
        "Align events and streams → Run multimodal analysis → Build the reproducible report"
    )
    page.locator("#start_guided").click()

    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible(
        timeout=60_000
    )
    expect(page.locator("#status")).to_contain_text(
        "First step: Align events and streams.",
        timeout=60_000,
    )
    expect(page.locator("#qc_state")).to_have_text("Complete", timeout=60_000)

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#project_name")).to_have_text(
        "Synthetic multimodal walkthrough",
        timeout=30_000,
    )
    expect(page.locator("#guided_progress")).to_have_text(
        "Multimodal research walkthrough: 0/3 guided steps complete",
        timeout=30_000,
    )
    expect(page.locator("#continue_guided")).to_have_text(
        "Continue: Align events and streams"
    )

    page.locator("#continue_guided").click()
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.locator("#status")).to_contain_text(
        "Guided next step: Align events and streams.",
        timeout=30_000,
    )

    page.locator("#event_alignment-run").click()
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#guided_progress")).to_have_text(
        "Multimodal research walkthrough: 1/3 guided steps complete",
        timeout=30_000,
    )
    expect(page.locator("#continue_guided")).to_have_text(
        "Continue: Run multimodal analysis"
    )

    page.locator("#continue_guided").click()
    expect(page.get_by_text("Multimodal controls", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.locator("#status")).to_contain_text(
        "Guided next step: Run multimodal analysis.",
        timeout=30_000,
    )

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)


def test_built_report_cache_invalidates_after_project_rename(
    page: Page,
    app: ShinyAppProc,
) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )

    open_nav(page, "reporting")
    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )
    expect(page.locator("#reporting-report_preview")).not_to_contain_text(
        "Build reporting artifacts to generate the report preview."
    )

    page.locator("#project_name_input").fill("Renamed after report build")
    page.locator("#apply_project_name").click()
    expect(page.locator("#status")).to_contain_text(
        "Project name set to 'Renamed after report build'.",
        timeout=30_000,
    )
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Project state changed. Rebuild reporting artifacts",
        timeout=30_000,
    )
    expect(page.locator("#reporting-report_preview")).to_have_text(
        "Build reporting artifacts to generate the report preview.",
        timeout=30_000,
    )
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Project: Renamed after report build"
    )

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
