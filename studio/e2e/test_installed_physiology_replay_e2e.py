from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import gpbiometricspy as gp
import pytest
from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.playwright import controller


INSTALLED_LOCAL_URL = os.environ.get("GPBIOMETRICSPY_INSTALLED_LOCAL_URL")
INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")
INSTALLED_PYTHON = os.environ.get("GPBIOMETRICSPY_INSTALLED_PYTHON")

pytestmark = pytest.mark.skipif(
    not INSTALLED_LOCAL_URL,
    reason="installed-distribution local Studio URL is not configured",
)


def _set_input_file(page: Page, input_id: str, path: Path) -> None:
    controller.InputFile(page, input_id).set(
        path,
        expect_complete_timeout=30_000,
    )


def _load_uploaded_dataset(page: Page, path: Path) -> None:
    _set_input_file(page, "upload", path)
    status = page.locator("#status")
    previous_status = status.inner_text()
    page.locator("#load_upload").click()
    expect(status).not_to_have_text(previous_status, timeout=60_000)

    missing = "Import failed: Choose a Gazepoint CSV or TXT file first."
    if status.inner_text() == missing:
        page.locator("#load_upload").click()
        expect(status).not_to_have_text(missing, timeout=60_000)

    expect(status).to_contain_text(
        "Research file imported.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("1,920", timeout=60_000)


def _execute_replay(
    replay_text: str,
    *,
    participant_path: Path,
    script_path: Path,
) -> subprocess.CompletedProcess[str]:
    placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
    assert placeholder in replay_text
    script_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(participant_path)!r})",
            1,
        ),
        encoding="utf-8",
    )
    assert INSTALLED_PYTHON is not None
    return subprocess.run(
        [INSTALLED_PYTHON, str(script_path)],
        cwd=script_path.parent,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )


def test_installed_eda_and_ppg_replay_from_wheel_and_sdist(
    page: Page,
    tmp_path: Path,
) -> None:
    assert INSTALLED_LOCAL_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    assert INSTALLED_PYTHON is not None

    participant_files = [Path(path) for path in gp.kiosk_demo_files()]
    assert len(participant_files) >= 2
    participant_path = participant_files[0]
    mismatch_participant_path = participant_files[1]

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    _load_uploaded_dataset(page, participant_path)

    open_nav(page, "eda_scr", group="Analyze")
    expect(page.get_by_text("EDA / SCR analysis controls", exact=True)).to_be_visible()
    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    expect(page.locator("#eda_scr-decomposition_method")).not_to_have_text("Not run")
    assert int(page.locator("#eda_scr-event_count").inner_text().replace(",", "")) >= 0

    open_nav(page, "ppg_hr_hrv", group="Analyze")
    expect(
        page.get_by_text("PPG / HR / HRV analysis controls", exact=True)
    ).to_be_visible()
    page.locator("#ppg_hr_hrv-run").click()
    expect(page.locator("#ppg_hr_hrv-status")).to_contain_text(
        "PPG/HR/HRV workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    assert int(page.locator("#ppg_hr_hrv-peak_count").inner_text().replace(",", "")) > 0

    open_nav(page, "reporting")
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-analysis_count")).to_have_text("2", timeout=60_000)
    page.get_by_role("tab", name="Downloads", exact=True).click()

    with page.expect_download(timeout=60_000) as replay_download:
        page.locator("#reporting-download_replay").click()
    replay_path = replay_download.value.path()
    assert replay_path is not None
    replay_text = Path(replay_path).read_text(encoding="utf-8")

    assert "from studio.services import run_eda_scr_analysis" in replay_text
    assert "from studio.ppg_services import run_ppg_hr_hrv_analysis" in replay_text
    assert 'analyses["eda_scr"]' in replay_text
    assert 'analyses["ppg_hr_hrv"]' in replay_text
    assert "EXPECTED_ANALYSES = ['eda_scr', 'ppg_hr_hrv']" in replay_text
    assert "GPBIOMETRICSPY_STUDIO_REPLAY_SUMMARY=" in replay_text

    wrong_result = _execute_replay(
        replay_text,
        participant_path=mismatch_participant_path,
        script_path=tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-physiology-wrong.py",
    )
    assert wrong_result.returncode != 0
    wrong_output = f"{wrong_result.stdout}\n{wrong_result.stderr}"
    assert "Dataset fingerprint mismatch:" in wrong_output

    exact_result = _execute_replay(
        replay_text,
        participant_path=participant_path,
        script_path=tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-physiology-exact.py",
    )
    assert exact_result.returncode == 0, (
        "Installed EDA + PPG replay failed.\n"
        f"stdout:\n{exact_result.stdout}\n"
        f"stderr:\n{exact_result.stderr}"
    )

    summary_lines = [
        line
        for line in exact_result.stdout.splitlines()
        if line.startswith("GPBIOMETRICSPY_STUDIO_REPLAY_SUMMARY=")
    ]
    assert len(summary_lines) == 1
    summary = json.loads(summary_lines[0].split("=", 1)[1])
    assert summary["analysis_count"] == 2
    assert summary["analysis_names"] == ["eda_scr", "ppg_hr_hrv"]

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
