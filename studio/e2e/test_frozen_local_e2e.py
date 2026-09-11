from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page, expect


FROZEN_LOCAL_URL = os.environ.get("GPBIOMETRICSPY_FROZEN_LOCAL_URL")

pytestmark = pytest.mark.skipif(
    not FROZEN_LOCAL_URL,
    reason="frozen local Studio URL is not configured",
)


def test_frozen_local_guided_physiology_reaches_report(page: Page) -> None:
    assert FROZEN_LOCAL_URL is not None
    page.goto(FROZEN_LOCAL_URL)

    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Teaching routes")).to_be_visible()
    expect(page.get_by_text("Physiology foundations", exact=True)).to_be_visible()
    expect(page.locator("#analysis_count")).to_have_text("0")
    expect(page.locator("#load_upload")).to_be_visible()

    page.locator("#guided_start").select_option("physiology")
    expect(page.locator("#guided_start_description")).to_contain_text(
        "Run EDA / SCR analysis → Run PPG / HR / HRV analysis → "
        "Build the reproducible report"
    )
    page.locator("#start_guided").click()

    expect(page.get_by_text("EDA / SCR analysis controls", exact=True)).to_be_visible(
        timeout=60_000
    )
    expect(page.locator("#status")).to_contain_text(
        "Foundation QC is complete",
        timeout=60_000,
    )
    expect(page.locator("#qc_state")).to_have_text("Complete", timeout=60_000)
    expect(page.locator("#project_name")).to_have_text(
        "Synthetic physiology walkthrough",
        timeout=30_000,
    )
    expect(page.locator("#eda_scr_readiness-module_readiness")).to_contain_text(
        "Ready for guided analysis",
        timeout=30_000,
    )
    expect(page.locator('[data-preset-key="eda-foundations"]')).to_be_visible()
    expect(page.locator('#eda_scr-mode input[value="guided"]')).to_be_checked()

    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#analysis_count")).to_have_text("1", timeout=30_000)
    expect(page.locator("#continue_guided")).to_have_text(
        "Continue: Run PPG / HR / HRV analysis"
    )
    page.locator("#continue_guided").click()

    expect(page.get_by_text("PPG / HR / HRV analysis controls", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.locator("#ppg_hr_hrv_readiness-module_readiness")).to_contain_text(
        "Ready for guided analysis",
        timeout=30_000,
    )
    page.locator("#ppg_hr_hrv-run").click()
    expect(page.locator("#ppg_hr_hrv-status")).to_contain_text(
        "PPG/HR/HRV workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#analysis_count")).to_have_text("2", timeout=30_000)
    expect(page.locator("#continue_guided")).to_have_text(
        "Continue: Build the reproducible report"
    )
    page.locator("#continue_guided").click()

    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.locator("#reporting-analysis_count")).to_have_text("2", timeout=30_000)
    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#guided_progress")).to_have_text(
        "EDA and cardiovascular walkthrough: 3/3 guided steps complete",
        timeout=30_000,
    )
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
