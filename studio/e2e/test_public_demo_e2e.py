from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


PUBLIC_APP_PATH = Path(__file__).resolve().parents[2] / "app.py"
public_app = create_app_fixture(PUBLIC_APP_PATH, scope="module", timeout_secs=90)


def _load_public_demo(page: Page, public_app: ShinyAppProc) -> None:
    page.goto(public_app.url)
    expect(page.get_by_text("Public synthetic demonstration.", exact=False)).to_be_visible()
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )
    expect(page.get_by_role("status")).to_contain_text("Synthetic kiosk demo loaded")


def _download(page: Page, selector: str) -> Path:
    with page.expect_download(timeout=60_000) as download_info:
        page.locator(selector).click()
    path = download_info.value.path()
    assert path is not None
    return Path(path)


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


def test_public_demo_runs_synthetic_gaze_and_reporting_with_external_sources_hidden(
    page: Page,
    public_app: ShinyAppProc,
) -> None:
    _load_public_demo(page, public_app)

    # The deployed root entrypoint must keep external AOI uploads non-visible while
    # preserving the package-backed synthetic Gaze workflow and its downloads.
    open_nav(page, "gaze", group="Analyze")
    expect(page.get_by_text("Gaze / fixation / saccade / AOI controls", exact=True)).to_be_visible()
    expect(page.locator("#gaze-aoi_upload")).to_be_hidden()
    assert page.locator('input[type="file"]:visible').count() == 0

    page.locator("#gaze-run").click()
    expect(page.locator("#gaze-status")).to_contain_text(
        "Gaze workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    assert int(page.locator("#gaze-saccade_count").inner_text().replace(",", "")) > 0

    page.get_by_text("Fixations & saccades", exact=True).click()
    expect(page.get_by_text("Saccade main-sequence diagnostic", exact=True)).to_be_visible()
    expect(page.locator("#gaze-main_sequence_plot img")).to_be_visible(timeout=60_000)

    page.locator('#gaze-gaze_tabs [data-value="Export"]').click()
    saccades_text = _download(page, "#gaze-download_saccades").read_text(encoding="utf-8")
    assert len(saccades_text.splitlines()) > 1

    # Event-log and secondary-stream inputs are present in the full Studio contract
    # but must remain non-visible in the public synthetic deployment.
    open_nav(page, "event_alignment", group="Integrate")
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    expect(page.locator("#event_alignment-event_upload")).to_be_hidden()
    expect(page.locator("#event_alignment-target_upload")).to_be_hidden()
    expect(page.locator("#event_alignment-load_target")).to_be_hidden()
    assert page.locator('input[type="file"]:visible').count() == 0

    # Reporting remains usable for the synthetic analysis, while restore controls
    # that could consume an external project recipe stay hidden.
    open_nav(page, "reporting")
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-analysis_count")).to_have_text("1", timeout=60_000)
    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )
    page.get_by_role("tab", name="Report", exact=True).click()
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Raw rows embedded in recipe: False",
        timeout=60_000,
    )
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Analysis outputs embedded in recipe: False"
    )

    page.get_by_role("tab", name="Manifest", exact=True).click()
    expect(page.locator("#reporting-manifest_preview")).to_contain_text(
        '"raw_data_included": false',
        timeout=60_000,
    )
    expect(page.locator("#reporting-manifest_preview")).to_contain_text(
        '"analysis_outputs_included": false'
    )

    page.get_by_role("tab", name="Project recipe", exact=True).click()
    expect(page.locator("#reporting-recipe_upload")).to_be_hidden()
    expect(page.locator("#reporting-validate_recipe")).to_be_hidden()
    expect(page.locator("#reporting-restore_recipe")).to_be_hidden()
    assert page.locator('input[type="file"]:visible').count() == 0

    recipe = json.loads(
        _download(page, "#reporting-download_recipe").read_text(encoding="utf-8")
    )
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    assert recipe["analysis_inventory"][0]["analysis"] == "gaze"
    assert len(recipe["dataset"]["sha256"]) == 64
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)


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
