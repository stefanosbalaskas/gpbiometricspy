from __future__ import annotations

import json
from pathlib import Path

import gpbiometricspy as gp
from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.playwright import controller
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _load_demo_participant(page: Page, app: ShinyAppProc) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    participant_path = Path(gp.kiosk_demo_files()[0])
    page.locator("#upload").set_input_files(str(participant_path))

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


def test_advanced_qc_renders_all_domains_and_records_provenance(
    page: Page,
    app: ShinyAppProc,
) -> None:
    _load_demo_participant(page, app)

    open_nav(page, "qc")
    expect(page.get_by_text("Advanced QC settings", exact=True)).to_be_visible()
    expect(
        page.get_by_text(
            "These checks identify data-quality and timing conditions. They do not convert physiological or gaze measures into psychological states.",
            exact=True,
        )
    ).to_be_visible()
    expect(page.locator("#qc-sampling_rate")).to_have_value("60")
    expect(page.locator("#qc-gsr_min")).to_have_value("0")
    expect(page.locator("#qc-gsr_max")).to_have_value("100")
    expect(page.locator("#qc-hr_min")).to_have_value("30")
    expect(page.locator("#qc-hr_max")).to_have_value("220")

    page.locator("#qc-run").click()
    expect(page.locator("#qc-status")).to_contain_text(
        "Advanced QC complete using public gpbiometricspy APIs.",
        timeout=120_000,
    )
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    expect(page.get_by_text("Time-reset diagnostics", exact=True)).to_be_visible()
    expect(page.locator("#qc-time_overview")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-time_segments")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-time_plot img")).to_be_visible(timeout=60_000)

    page.get_by_role("tab", name="Physiology", exact=True).click()
    expect(page.get_by_text("EDA / HR quality audit", exact=True)).to_be_visible()
    expect(page.locator("#qc-physiology_quality")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-physiology_plot img")).to_be_visible(timeout=60_000)

    page.get_by_role("tab", name="Gaze", exact=True).click()
    expect(page.get_by_text("Gaze summary", exact=True)).to_be_visible()
    expect(page.locator("#qc-gaze_summary")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-gaze_checks")).to_be_visible(timeout=60_000)
    expect(page.locator("#qc-gaze_groups")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    open_nav(page, "reporting")
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    page.get_by_text("Project recipe", exact=True).click()
    expect(page.get_by_text("Save project recipe", exact=True)).to_be_visible()

    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    path = download_info.value.path()
    assert path is not None
    recipe = json.loads(Path(path).read_text(encoding="utf-8"))

    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    operations = [event.get("operation") for event in recipe["provenance"]]
    assert "run_advanced_qc" in operations
