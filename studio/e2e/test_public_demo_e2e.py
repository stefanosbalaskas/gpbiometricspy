from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


PUBLIC_APP_PATH = Path(__file__).resolve().parents[2] / "app.py"
public_app = create_app_fixture(PUBLIC_APP_PATH, scope="module", timeout_secs=90)


def test_public_demo_is_synthetic_only_and_sanitized_in_browser(page: Page, public_app: ShinyAppProc) -> None:
    page.goto(public_app.url)

    expect(page.get_by_text("Public synthetic demonstration.", exact=False)).to_be_visible()
    expect(page.get_by_text("Synthetic data only.", exact=True)).to_be_visible()
    expect(page.locator("#load_demo")).to_be_visible()
    assert page.locator("#load_upload").count() == 0
    assert page.locator('input[type="file"]:visible').count() == 0
    assert page.locator('[id$="-load_target"]:visible').count() == 0
    assert page.locator('[id$="-validate_recipe"]:visible').count() == 0
    assert page.locator('[id$="-restore_recipe"]:visible').count() == 0

    status = page.get_by_role("status")
    expect(status).to_contain_text("External uploads are disabled")

    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text("Bundled synthetic kiosk demo", timeout=60_000)
    expect(status).to_contain_text("Synthetic kiosk demo loaded")


def test_public_demo_has_keyboard_skip_link_and_mobile_no_horizontal_page_overflow(
    page: Page,
    public_app: ShinyAppProc,
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(public_app.url)

    skip = page.get_by_text("Skip to content", exact=True)
    expect(skip).to_have_attribute("href", "#studio-main")
    skip.focus()
    expect(skip).to_be_focused()

    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert float(overflow) <= 4.0

    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    expect(page.get_by_text("Public synthetic demonstration.", exact=False)).to_be_visible()
