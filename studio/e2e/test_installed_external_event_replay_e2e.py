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
REPLAY_EVENT_LOG_ENV = "GPBIOMETRICSPY_STUDIO_EVENT_LOG"

pytestmark = pytest.mark.skipif(
    not INSTALLED_LOCAL_URL,
    reason="installed-distribution local Studio URL is not configured",
)


def _write_event_logs(participant_path: Path, tmp_path: Path) -> tuple[Path, Path]:
    data = gp.import_gazepoint_biometrics(participant_path)
    alignment = gp.align_gazepoint_biometrics_to_ttl(
        data,
        ttl_cols=["TTL0"],
        ttl_valid_col="TTLV",
        time_col="TIME",
        group_cols=["participant_id"],
        event_edge="rising",
        pre_window_ms=1_000.0,
        post_window_ms=5_000.0,
        require_valid_ttl=True,
    )
    events = alignment["events"]
    assert len(events) >= 2
    assert "event_time_ms" in events.columns
    participant_id = str(data["participant_id"].iloc[0])
    event_times = [float(value) / 1_000.0 for value in events["event_time_ms"].iloc[:2]]

    event_path = tmp_path / "installed-replay-events.csv"
    event_path.write_text(
        "trial,onset,condition,participant_id\n"
        f"E1,{event_times[0]},stimulus,{participant_id}\n"
        f"E2,{event_times[1]},stimulus,{participant_id}\n",
        encoding="utf-8",
    )
    wrong_event_path = tmp_path / "installed-replay-wrong-events.csv"
    wrong_event_path.write_text(
        "trial,onset,condition,participant_id\n"
        f"E1,{event_times[0]},stimulus,{participant_id}\n"
        f"E2,{event_times[1] + 0.25},stimulus,{participant_id}\n",
        encoding="utf-8",
    )
    return event_path, wrong_event_path


def test_installed_external_event_log_replay_is_identity_bound(
    page: Page,
    tmp_path: Path,
) -> None:
    assert INSTALLED_LOCAL_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    assert INSTALLED_PYTHON is not None

    participant_path = Path(gp.kiosk_demo_files()[0])
    event_path, wrong_event_path = _write_event_logs(participant_path, tmp_path)

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    controller.InputFile(page, "upload").set(
        participant_path,
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
    page.get_by_label("External event log", exact=True).check()
    controller.InputFile(page, "event_alignment-event_upload").set(
        event_path,
        expect_complete_timeout=30_000,
    )
    page.locator("#event_alignment-run").click()
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )
    assert int(page.locator("#event_alignment-event_count").inner_text().replace(",", "")) == 2

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
    assert "external_events_sha256" in replay_text
    assert str(event_path) not in replay_text
    assert event_path.name not in replay_text

    placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
    assert placeholder in replay_text
    replay_path = tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-external-event-replay.py"
    replay_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(participant_path)!r})",
            1,
        ),
        encoding="utf-8",
    )

    wrong_env = os.environ.copy()
    wrong_env[REPLAY_EVENT_LOG_ENV] = str(wrong_event_path)
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
    assert "External event log fingerprint mismatch:" in wrong_output

    exact_env = os.environ.copy()
    exact_env[REPLAY_EVENT_LOG_ENV] = str(event_path)
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
        "Installed external-event replay failed.\n"
        f"stdout:\n{exact_result.stdout}\n"
        f"stderr:\n{exact_result.stderr}"
    )
    assert exact_result.stdout.strip()
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
