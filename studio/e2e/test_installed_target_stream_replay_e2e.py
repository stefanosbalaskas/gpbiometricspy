from __future__ import annotations

import os
from pathlib import Path
import subprocess

import gpbiometricspy as gp
import pytest
from playwright.sync_api import Page, expect
from shiny.playwright import controller


INSTALLED_LOCAL_URL = os.environ.get("GPBIOMETRICSPY_INSTALLED_LOCAL_URL")
INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")
INSTALLED_PYTHON = os.environ.get("GPBIOMETRICSPY_INSTALLED_PYTHON")
REPLAY_TARGET_STREAM_ENV = "GPBIOMETRICSPY_STUDIO_TARGET_STREAM"

pytestmark = pytest.mark.skipif(
    not INSTALLED_LOCAL_URL,
    reason="installed-distribution local Studio URL is not configured",
)


def test_installed_target_stream_replay_is_identity_bound(
    page: Page,
    tmp_path: Path,
) -> None:
    assert INSTALLED_LOCAL_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    assert INSTALLED_PYTHON is not None

    participant_files = [Path(path) for path in gp.kiosk_demo_files()]
    assert len(participant_files) >= 2
    reference_path = participant_files[0]
    target_path = participant_files[1]

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    controller.InputFile(page, "upload").set(
        reference_path,
        expect_complete_timeout=30_000,
    )
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("1,920", timeout=60_000)

    page.get_by_text("Events & Alignment", exact=True).click()
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    controller.InputFile(page, "event_alignment-target_upload").set(
        target_path,
        expect_complete_timeout=30_000,
    )
    page.locator("#event_alignment-load_target").click()
    expect(page.locator("#event_alignment-target_status")).to_contain_text(
        target_path.name,
        timeout=60_000,
    )
    page.get_by_label(
        "Align a second Gazepoint stream by shared event anchors",
        exact=True,
    ).check()
    page.locator("#event_alignment-run").click()
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )
    assert int(page.locator("#event_alignment-event_count").inner_text().replace(",", "")) >= 2
    assert int(page.locator("#event_alignment-pair_count").inner_text().replace(",", "")) >= 2

    page.get_by_text("Reporting & Reproducibility", exact=True).click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-analysis_count")).to_have_text("1", timeout=60_000)
    page.get_by_role("tab", name="Downloads", exact=True).click()

    with page.expect_download(timeout=60_000) as replay_download:
        page.locator("#reporting-download_replay").click()
    download_path = replay_download.value.path()
    assert download_path is not None
    replay_text = Path(download_path).read_text(encoding="utf-8")
    assert "from studio.event_alignment_services import run_event_alignment" in replay_text
    assert 'analyses["event_alignment"]' in replay_text
    assert "target_stream_used" in replay_text
    assert "target_stream_sha256" in replay_text
    assert str(target_path) not in replay_text
    assert target_path.name not in replay_text

    placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
    assert placeholder in replay_text
    replay_path = tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-target-stream-replay.py"
    replay_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(reference_path)!r})",
            1,
        ),
        encoding="utf-8",
    )

    wrong_env = os.environ.copy()
    wrong_env[REPLAY_TARGET_STREAM_ENV] = str(reference_path)
    wrong_result = subprocess.run(
        [INSTALLED_PYTHON, str(replay_path)],
        cwd=tmp_path,
        env=wrong_env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert wrong_result.returncode != 0
    wrong_output = f"{wrong_result.stdout}\n{wrong_result.stderr}"
    assert "Target stream fingerprint mismatch:" in wrong_output

    exact_env = os.environ.copy()
    exact_env[REPLAY_TARGET_STREAM_ENV] = str(target_path)
    exact_result = subprocess.run(
        [INSTALLED_PYTHON, str(replay_path)],
        cwd=tmp_path,
        env=exact_env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert exact_result.returncode == 0, (
        "Installed target-stream replay failed.\n"
        f"stdout:\n{exact_result.stdout}\n"
        f"stderr:\n{exact_result.stderr}"
    )
    assert exact_result.stdout.strip()
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
