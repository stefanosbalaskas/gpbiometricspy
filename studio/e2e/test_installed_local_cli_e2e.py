from __future__ import annotations

import os
from pathlib import Path

import gpbiometricspy as gp
import pytest
from playwright.sync_api import Page, expect


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
    assert page.locator('input[type="file"]:visible').count() == 1

    participant_path = Path(gp.kiosk_demo_files()[0])
    page.locator("#upload").set_input_files(str(participant_path))
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

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
