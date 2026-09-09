from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav


INSTALLED_PUBLIC_URL = os.environ.get("GPBIOMETRICSPY_INSTALLED_PUBLIC_URL")
INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")

pytestmark = pytest.mark.skipif(
    not INSTALLED_PUBLIC_URL,
    reason="installed-distribution public Studio URL is not configured",
)


def test_installed_distribution_public_console_browser_path(page: Page) -> None:
    assert INSTALLED_PUBLIC_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    page.goto(INSTALLED_PUBLIC_URL)

    expect(page.get_by_text("Public synthetic demonstration.", exact=False)).to_be_visible()
    expect(page.get_by_text("Synthetic data only.", exact=True)).to_be_visible()
    assert page.locator("#load_upload").count() == 0
    assert page.locator('input[type="file"]:visible').count() == 0

    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )
    expect(page.get_by_role("status")).to_contain_text("Synthetic kiosk demo loaded")

    open_nav(page, "gaze", group="Analyze")
    expect(page.locator("#gaze-aoi_upload")).to_be_hidden()
    page.locator("#gaze-run").click()
    expect(page.locator("#gaze-status")).to_contain_text(
        "Gaze workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    assert int(page.locator("#gaze-saccade_count").inner_text().replace(",", "")) > 0

    open_nav(page, "reporting")
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-analysis_count")).to_have_text("1", timeout=60_000)
    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )

    page.get_by_role("tab", name="Project recipe", exact=True).click()
    expect(page.locator("#reporting-recipe_upload")).to_be_hidden()
    expect(page.locator("#reporting-validate_recipe")).to_be_hidden()
    expect(page.locator("#reporting-restore_recipe")).to_be_hidden()
    expect(page.locator("#reporting-download_recipe")).to_be_visible()
    assert page.locator('input[type="file"]:visible').count() == 0
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
