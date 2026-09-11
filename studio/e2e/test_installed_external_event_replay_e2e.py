from __future__ import annotations

import os
from pathlib import Path
import subprocess

import gpbiometricspy as gp
import numpy as np
import pytest
from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.playwright import controller


INSTALLED_LOCAL_URL = os.environ.get("GPBIOMETRICSPY_INSTALLED_LOCAL_URL")
INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")
INSTALLED_PYTHON = os.environ.get("GPBIOMETRICSPY_INSTALLED_PYTHON")
REPLAY_EVENT_LOG_ENV = "GPBIOMETRICSPY_STUDIO_EVENT_LOG"
REPLAY_TARGET_STREAM_ENV = "GPBIOMETRICSPY_STUDIO_TARGET_STREAM"

pytestmark = pytest.mark.skipif(
    not INSTALLED_LOCAL_URL,
    reason="installed-distribution local Studio URL is not configured",
)


def _write_event_logs(participant_path: Path, tmp_path: Path) -> tuple[Path, Path]:
    data = gp.import_gazepoint_biometrics(participant_path)
    ttl = data["TTL0"].to_numpy(dtype=float)
    valid = data["TTLV"].to_numpy(dtype=float)
    time = data["TIME"].to_numpy(dtype=float)
    active = np.isfinite(ttl) & (ttl != 0) & np.isfinite(valid) & (valid == 1)
    rising = active & ~np.concatenate(([False], active[:-1]))
    event_times = time[rising & np.isfinite(time)]
    assert len(event_times) >= 2
    participant_id = str(data["participant_id"].iloc[0])

    event_path = tmp_path / "installed-replay-events.csv"
    event_path.write_text(
        "trial,onset,condition,participant_id\n"
        f"E1,{float(event_times[0])},stimulus,{participant_id}\n"
        f"E2,{float(event_times[1])},stimulus,{participant_id}\n",
        encoding="utf-8",
    )
    wrong_event_path = tmp_path / "installed-replay-wrong-events.csv"
    wrong_event_path.write_text(
        "trial,onset,condition,participant_id\n"
        f"E1,{float(event_times[0])},stimulus,{participant_id}\n"
        f"E2,{float(event_times[1]) + 0.25},stimulus,{participant_id}\n",
        encoding="utf-8",
    )
    return event_path, wrong_event_path


def _set_input_file(page: Page, input_id: str, path: Path) -> None:
    controller.InputFile(page, input_id).set(
        path,
        expect_complete_timeout=30_000,
    )


def _click_with_upload_retry(
    page: Page,
    *,
    action_id: str,
    status_id: str,
    missing_upload_fragment: str,
    timeout: int,
) -> None:
    action = page.locator(f"#{action_id}")
    status = page.locator(f"#{status_id}")
    previous_status = status.inner_text()

    action.click()
    expect(status).not_to_have_text(previous_status, timeout=timeout)
    current_status = status.inner_text()
    if missing_upload_fragment.casefold() in current_status.casefold():
        previous_status = current_status
        action.click()
        expect(status).not_to_have_text(previous_status, timeout=timeout)


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
    _set_input_file(page, "upload", participant_path)
    _click_with_upload_retry(
        page,
        action_id="load_upload",
        status_id="status",
        missing_upload_fragment="Choose a Gazepoint CSV or TXT file first",
        timeout=60_000,
    )
    expect(page.locator("#status")).to_contain_text(
        "Research file imported.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("1,920", timeout=60_000)

    open_nav(page, "event_alignment", group="Integrate")
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    page.get_by_label("External event log", exact=True).check()
    _set_input_file(page, "event_alignment-event_upload", event_path)
    _click_with_upload_retry(
        page,
        action_id="event_alignment-run",
        status_id="event_alignment-status",
        missing_upload_fragment="event log CSV/TXT/TSV file first",
        timeout=120_000,
    )
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )
    assert int(page.locator("#event_alignment-event_count").inner_text().replace(",", "")) == 2

    open_nav(page, "reporting")
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
    _set_input_file(page, "upload", reference_path)
    _click_with_upload_retry(
        page,
        action_id="load_upload",
        status_id="status",
        missing_upload_fragment="Choose a Gazepoint CSV or TXT file first",
        timeout=60_000,
    )
    expect(page.locator("#status")).to_contain_text(
        "Research file imported.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("1,920", timeout=60_000)

    open_nav(page, "event_alignment", group="Integrate")
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    _set_input_file(page, "event_alignment-target_upload", target_path)
    _click_with_upload_retry(
        page,
        action_id="event_alignment-load_target",
        status_id="event_alignment-status",
        missing_upload_fragment="target stream CSV/TXT/TSV file first",
        timeout=60_000,
    )
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

    open_nav(page, "reporting")
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


def test_installed_dual_secondary_resource_replay_is_identity_bound(
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
    event_path, wrong_event_path = _write_event_logs(reference_path, tmp_path)

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    _set_input_file(page, "upload", reference_path)
    _click_with_upload_retry(
        page,
        action_id="load_upload",
        status_id="status",
        missing_upload_fragment="Choose a Gazepoint CSV or TXT file first",
        timeout=60_000,
    )
    expect(page.locator("#status")).to_contain_text(
        "Research file imported.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("1,920", timeout=60_000)

    open_nav(page, "event_alignment", group="Integrate")
    expect(page.get_by_text("Events & alignment controls", exact=True)).to_be_visible()
    page.get_by_label("External event log", exact=True).check()
    _set_input_file(page, "event_alignment-event_upload", event_path)
    _set_input_file(page, "event_alignment-target_upload", target_path)
    _click_with_upload_retry(
        page,
        action_id="event_alignment-load_target",
        status_id="event_alignment-status",
        missing_upload_fragment="target stream CSV/TXT/TSV file first",
        timeout=60_000,
    )
    expect(page.locator("#event_alignment-target_status")).to_contain_text(
        target_path.name,
        timeout=60_000,
    )
    page.get_by_label(
        "Align a second Gazepoint stream by shared event anchors",
        exact=True,
    ).check()
    _click_with_upload_retry(
        page,
        action_id="event_alignment-run",
        status_id="event_alignment-status",
        missing_upload_fragment="event log CSV/TXT/TSV file first",
        timeout=120_000,
    )
    expect(page.locator("#event_alignment-status")).to_contain_text(
        "Events & alignment complete:",
        timeout=120_000,
    )
    assert int(page.locator("#event_alignment-event_count").inner_text().replace(",", "")) == 2
    assert int(page.locator("#event_alignment-pair_count").inner_text().replace(",", "")) >= 2

    open_nav(page, "reporting")
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
    assert "target_stream_used" in replay_text
    assert "target_stream_sha256" in replay_text
    assert str(event_path) not in replay_text
    assert event_path.name not in replay_text
    assert str(target_path) not in replay_text
    assert target_path.name not in replay_text

    placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
    assert placeholder in replay_text
    replay_path = tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-dual-resource-replay.py"
    replay_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(reference_path)!r})",
            1,
        ),
        encoding="utf-8",
    )

    wrong_event_env = os.environ.copy()
    wrong_event_env[REPLAY_EVENT_LOG_ENV] = str(wrong_event_path)
    wrong_event_env[REPLAY_TARGET_STREAM_ENV] = str(target_path)
    wrong_event_result = subprocess.run(
        [INSTALLED_PYTHON, str(replay_path)],
        cwd=tmp_path,
        env=wrong_event_env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert wrong_event_result.returncode != 0
    wrong_event_output = f"{wrong_event_result.stdout}\n{wrong_event_result.stderr}"
    assert "External event log fingerprint mismatch:" in wrong_event_output

    wrong_target_env = os.environ.copy()
    wrong_target_env[REPLAY_EVENT_LOG_ENV] = str(event_path)
    wrong_target_env[REPLAY_TARGET_STREAM_ENV] = str(reference_path)
    wrong_target_result = subprocess.run(
        [INSTALLED_PYTHON, str(replay_path)],
        cwd=tmp_path,
        env=wrong_target_env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert wrong_target_result.returncode != 0
    wrong_target_output = f"{wrong_target_result.stdout}\n{wrong_target_result.stderr}"
    assert "Target stream fingerprint mismatch:" in wrong_target_output

    exact_env = os.environ.copy()
    exact_env[REPLAY_EVENT_LOG_ENV] = str(event_path)
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
        "Installed dual-resource replay failed.\n"
        f"stdout:\n{exact_result.stdout}\n"
        f"stderr:\n{exact_result.stderr}"
    )
    assert exact_result.stdout.strip()
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
