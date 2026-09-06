from __future__ import annotations

import json
from pathlib import Path

import gpbiometricspy as gp
from playwright.sync_api import Page, expect
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _load_demo(page: Page, app: ShinyAppProc) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text("Bundled synthetic kiosk demo", timeout=60_000)
    rows_text = page.locator("#row_count").inner_text()
    cols_text = page.locator("#column_count").inner_text()
    assert int(rows_text.replace(",", "")) > 0
    assert int(cols_text.replace(",", "")) > 0


def _load_demo_participant(page: Page, app: ShinyAppProc) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    participant_path = gp.kiosk_demo_files()[0]
    page.locator("#upload").set_input_files(str(participant_path))
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    rows_text = page.locator("#row_count").inner_text()
    cols_text = page.locator("#column_count").inner_text()
    assert int(rows_text.replace(",", "")) == 1_920
    assert int(cols_text.replace(",", "")) > 0


def _open_reporting(page: Page) -> None:
    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")


def _run_gaze_analysis(page: Page) -> None:
    page.get_by_text("Gaze / Fixation / AOI Analysis", exact=True).click()
    expect(page.get_by_text("Gaze / fixation / saccade / AOI controls", exact=True)).to_be_visible()
    page.locator("#gaze-run").click()
    expect(page.locator("#gaze-status")).to_contain_text(
        "Gaze workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    saccade_count = int(page.locator("#gaze-saccade_count").inner_text().replace(",", ""))
    assert saccade_count > 0


def _run_pupil_analysis(page: Page) -> None:
    page.get_by_text("Pupil Analysis", exact=True).click()
    expect(page.get_by_text("Pupil analysis controls", exact=True)).to_be_visible()
    page.locator("#pupil-run").click()
    expect(page.locator("#pupil-status")).to_contain_text(
        "Pupil workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    blink_count = int(page.locator("#pupil-blink_count").inner_text().replace(",", ""))
    assert blink_count >= 0


def _run_eda_scr_analysis(page: Page) -> None:
    page.get_by_text("EDA / SCR Analysis", exact=True).click()
    expect(page.get_by_text("EDA / SCR analysis controls", exact=True)).to_be_visible()
    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    expect(page.locator("#eda_scr-decomposition_method")).not_to_have_text("Not run")
    event_count = int(page.locator("#eda_scr-event_count").inner_text().replace(",", ""))
    assert event_count >= 0


def _run_ppg_hr_hrv_analysis(page: Page) -> None:
    page.get_by_text("PPG / HR / HRV Analysis", exact=True).click()
    expect(page.get_by_text("PPG / HR / HRV analysis controls", exact=True)).to_be_visible()
    page.locator("#ppg_hr_hrv-run").click()
    expect(page.locator("#ppg_hr_hrv-status")).to_contain_text(
        "PPG/HR/HRV workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    peak_count = int(page.locator("#ppg_hr_hrv-peak_count").inner_text().replace(",", ""))
    assert peak_count > 0


def _run_event_alignment(page: Page) -> None:
    page.get_by_text("Events & Alignment", exact=True).click()
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    page.locator("#event_alignment-run").click()
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )
    event_count = int(page.locator("#event_alignment-event_count").inner_text().replace(",", ""))
    window_count = int(page.locator("#event_alignment-window_count").inner_text().replace(",", ""))
    assert event_count > 0
    assert window_count > 0


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
    modality_count = int(page.locator("#multimodal-modality_count").inner_text().replace(",", ""))
    summary_count = int(page.locator("#multimodal-summary_count").inner_text().replace(",", ""))
    assert modality_count == 1
    assert summary_count > 0


def test_studio_shell_loads_demo_and_exposes_reporting(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _open_reporting(page)
    expect(page.get_by_text("Raw rows and cached analysis-result tables are intentionally excluded.", exact=False)).to_be_visible()
    expect(page.locator("#reporting-operation_count")).not_to_have_text("0")


def test_reporting_build_and_recipe_download_preserve_privacy(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _open_reporting(page)

    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )
    expect(page.locator("#reporting-fingerprint")).not_to_have_text("—")

    page.get_by_text("Project recipe", exact=True).click()
    expect(page.get_by_text("Save project recipe", exact=True)).to_be_visible()

    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    recipe = json.loads(Path(path).read_text(encoding="utf-8"))

    assert recipe["schema"] == "gpbiometricspy-studio-project-recipe"
    assert recipe["raw_data_included"] is False
    assert recipe["analysis_outputs_included"] is False
    assert len(recipe["dataset"]["sha256"]) == 64
    assert recipe["dataset"]["row_count"] > 0
    assert recipe["dataset"]["column_count"] > 0


def test_gaze_main_sequence_renders_and_saccades_download(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _run_gaze_analysis(page)

    page.get_by_text("Fixations & saccades", exact=True).click()
    expect(page.get_by_text("Saccade main-sequence diagnostic", exact=True)).to_be_visible()
    expect(page.locator("#gaze-main_sequence_plot img")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    page.locator('#gaze-gaze_tabs [data-value="Export"]').click()
    expect(page.locator("#gaze-download_saccades")).to_be_visible()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#gaze-download_saccades").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    csv_text = Path(path).read_text(encoding="utf-8")
    assert len(csv_text.splitlines()) > 1


def test_pupil_missingness_renders_and_processed_download(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _run_pupil_analysis(page)

    expect(page.get_by_text("Package-native pupil missingness diagnostic", exact=True)).to_be_visible()
    expect(page.locator("#pupil-missingness_plot img")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    page.locator('#pupil-pupil_tabs [data-value="Export"]').click()
    expect(page.locator("#pupil-download_processed")).to_be_visible()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#pupil-download_processed").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    csv_text = Path(path).read_text(encoding="utf-8")
    assert len(csv_text.splitlines()) > 1


def test_eda_decomposition_renders_and_downloads(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _run_eda_scr_analysis(page)

    page.get_by_role("tab", name="Decomposition", exact=True).click()
    expect(page.get_by_text("Observed, tonic, and phasic EDA", exact=True)).to_be_visible()
    expect(page.locator("#eda_scr-decomposition_plot img")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    page.locator('#eda_scr-eda_tabs [data-value="Export"]').click()
    expect(page.locator("#eda_scr-download_decomposition")).to_be_visible()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#eda_scr-download_decomposition").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    csv_text = Path(path).read_text(encoding="utf-8")
    assert len(csv_text.splitlines()) > 1


def test_ppg_peak_detection_renders_and_peaks_download(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _run_ppg_hr_hrv_analysis(page)

    page.get_by_role("tab", name="Pulse / PPG", exact=True).click()
    expect(page.get_by_text("Pulse waveform and detected peaks", exact=True)).to_be_visible()
    expect(page.locator("#ppg_hr_hrv-peak_plot img")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    page.locator('#ppg_hr_hrv-cardiac_tabs [data-value="Export"]').click()
    expect(page.locator("#ppg_hr_hrv-download_peaks")).to_be_visible()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#ppg_hr_hrv-download_peaks").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    csv_text = Path(path).read_text(encoding="utf-8")
    assert len(csv_text.splitlines()) > 1


def test_event_alignment_tables_and_events_download(page: Page, app: ShinyAppProc) -> None:
    _load_demo(page, app)
    _run_event_alignment(page)

    page.get_by_role("tab", name="TTL alignment", exact=True).click()
    expect(page.get_by_text("TTL alignment overview", exact=True)).to_be_visible()
    expect(page.get_by_text("TTL-aligned events", exact=True)).to_be_visible()
    expect(page.locator("#event_alignment-ttl_overview")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    page.locator('a[data-value="Export"]:visible').click()
    expect(page.locator("#event_alignment-download_events")).to_be_visible()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#event_alignment-download_events").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    csv_text = Path(path).read_text(encoding="utf-8")
    assert len(csv_text.splitlines()) > 1


def test_multimodal_timeline_and_response_download(page: Page, app: ShinyAppProc) -> None:
    _load_demo_participant(page, app)
    _run_event_alignment(page)
    _run_multimodal_analysis(page)

    page.get_by_role("tab", name="Timeline", exact=True).click()
    expect(page.get_by_text("Package-native multimodal timeline", exact=True)).to_be_visible()
    expect(page.locator("#multimodal-timeline_plot img")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    page.locator('a[data-value="Export"]:visible').click()
    expect(page.locator("#multimodal-download_response")).to_be_visible()
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#multimodal-download_response").click()
    download = download_info.value
    path = download.path()
    assert path is not None
    csv_text = Path(path).read_text(encoding="utf-8")
    assert len(csv_text.splitlines()) > 1
