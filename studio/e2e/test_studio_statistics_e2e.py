from __future__ import annotations

from pathlib import Path

import gpbiometricspy as gp
from playwright.sync_api import Page, expect
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

    def _participant_uploaded(value) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], dict)
            and value[0].get("name") == participant_path.name
        )

    controller.AppTestValues(page).expect_input("upload", _participant_uploaded, timeout=30.0)
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    assert int(page.locator("#row_count").inner_text().replace(",", "")) == 1_920


def _run_event_alignment(page: Page) -> None:
    page.get_by_text("Events & Alignment", exact=True).click()
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    page.locator("#event_alignment-run").click()
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )
    assert int(page.locator("#event_alignment-event_count").inner_text().replace(",", "")) > 0


def _run_multimodal_analysis(page: Page) -> None:
    page.get_by_text("Multimodal Analysis", exact=True).click()
    expect(page.get_by_text("Multimodal controls", exact=True)).to_be_visible()
    expect(page.locator("#multimodal-event_status")).to_contain_text(
        "Events & Alignment ready:",
        timeout=60_000,
    )
    page.locator("#multimodal-trial_col").select_option("")
    page.locator("#multimodal-cardiac_col").select_option("")
    page.locator("#multimodal-pupil_col").select_option("")
    page.locator("#multimodal-gaze_x_col").select_option("")
    page.locator("#multimodal-gaze_y_col").select_option("")
    page.locator("#multimodal-aoi_col").select_option("")
    page.locator("#multimodal-run").click()
    expect(page.locator("#multimodal-status")).to_contain_text(
        "Multimodal Analysis complete:",
        timeout=120_000,
    )
    assert int(page.locator("#multimodal-modality_count").inner_text().replace(",", "")) == 1
    assert int(page.locator("#multimodal-sample_count").inner_text().replace(",", "")) > 10


def test_statistics_model_preparation_from_multimodal_samples(page: Page, app: ShinyAppProc) -> None:
    _load_demo_participant(page, app)
    _run_event_alignment(page)
    _run_multimodal_analysis(page)

    page.get_by_text("Statistics & Modelling", exact=True).click()
    expect(page.get_by_text("Model controls", exact=True)).to_be_visible()

    source = page.locator("#statistics_modelling-model_source")
    event_samples = source.locator('option[value="multimodal_event_samples"]')
    expect(event_samples).to_have_count(1, timeout=60_000)
    source.select_option("multimodal_event_samples")
    expect(source).to_have_value("multimodal_event_samples")

    outcome = page.locator("#statistics_modelling-model_outcome")
    expect(outcome).to_have_value("value", timeout=60_000)
    participant = page.locator("#statistics_modelling-model_participant")
    expect(participant).to_have_value("participant_id", timeout=60_000)

    page.locator("#statistics_modelling-run_model").click()
    expect(page.locator("#statistics_modelling-model_status")).to_contain_text(
        "Model-data preparation complete:",
        timeout=120_000,
    )

    complete_rows = int(
        page.locator("#statistics_modelling-model_complete_rows").inner_text().replace(",", "")
    )
    model_rows = int(page.locator("#statistics_modelling-model_rows").inner_text().replace(",", ""))
    assert complete_rows >= 10
    assert model_rows >= 10

    formula = page.locator("#statistics_modelling-model_formula").inner_text()
    assert "value ~" in formula
    assert "participant_id" in formula
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    with page.expect_download(timeout=60_000) as data_download_info:
        page.locator("#statistics_modelling-download_model_data").click()
    data_download = data_download_info.value
    data_path = data_download.path()
    assert data_path is not None
    data_text = Path(data_path).read_text(encoding="utf-8")
    assert len(data_text.splitlines()) > 10

    with page.expect_download(timeout=60_000) as script_download_info:
        page.locator("#statistics_modelling-download_model_script").click()
    script_download = script_download_info.value
    script_path = script_download.path()
    assert script_path is not None
    script_text = Path(script_path).read_text(encoding="utf-8")
    assert "prepare_gazepoint_biometrics_lme_data" in script_text
    assert "outcome_col='value'" in script_text
    assert "participant_col='participant_id'" in script_text
