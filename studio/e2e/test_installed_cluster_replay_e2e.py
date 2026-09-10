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


def _cluster_fixture(tmp_path: Path, *, seed: int, name: str) -> Path:
    table = gp.simulate_gazepoint_cluster_timecourse_data(
        n_subjects=12,
        n_time=18,
        conditions=("control", "warning"),
        effect_start=7,
        effect_end=11,
        effect_size=1.2,
        noise_sd=0.25,
        subject_sd=0.15,
        effect_condition="warning",
        seed=seed,
    )
    path = tmp_path / name
    table.to_csv(path, index=False)
    return path


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

    missing_upload_message = "Choose a Gazepoint CSV or TXT file first."
    if missing_upload_message in status.inner_text():
        missing_status = status.inner_text()
        page.locator("#load_upload").click()
        expect(status).not_to_have_text(missing_status, timeout=60_000)

    expect(status).to_contain_text(
        "Research file imported.",
        timeout=60_000,
    )
    expect(page.locator("#row_count")).to_have_text("432", timeout=60_000)


def _execute_replay(
    replay_text: str,
    *,
    data_path: Path,
    script_path: Path,
) -> subprocess.CompletedProcess[str]:
    placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
    assert placeholder in replay_text
    script_path.write_text(
        replay_text.replace(
            placeholder,
            f"DATA_PATH = Path({str(data_path)!r})",
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


def test_installed_cluster_permutation_replay_from_wheel_and_sdist(
    page: Page,
    tmp_path: Path,
) -> None:
    assert INSTALLED_LOCAL_URL is not None
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    assert INSTALLED_PYTHON is not None

    fixture = _cluster_fixture(
        tmp_path,
        seed=7,
        name="cluster_timecourse.csv",
    )
    mismatch_fixture = _cluster_fixture(
        tmp_path,
        seed=8,
        name="cluster_timecourse_wrong.csv",
    )

    page.goto(INSTALLED_LOCAL_URL)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    _load_uploaded_dataset(page, fixture)

    open_nav(page, "statistics_modelling")
    expect(page.get_by_text("Model controls", exact=True)).to_be_visible()
    page.get_by_role("tab", name="Cluster permutation", exact=True).click()
    expect(page.get_by_text("Cluster controls", exact=True)).to_be_visible()

    source = page.locator("#statistics_modelling-cluster_source")
    expect(source.locator('option[value="loaded_data"]')).to_have_count(
        1,
        timeout=60_000,
    )
    source.select_option("loaded_data")
    expect(source).to_have_value("loaded_data")

    expect(page.locator("#statistics_modelling-cluster_outcome")).to_have_value(
        "value",
        timeout=60_000,
    )
    expect(page.locator("#statistics_modelling-cluster_time")).to_have_value(
        "time",
        timeout=60_000,
    )
    expect(page.locator("#statistics_modelling-cluster_condition")).to_have_value(
        "condition",
        timeout=60_000,
    )
    expect(page.locator("#statistics_modelling-cluster_participant")).to_have_value(
        "subject",
        timeout=60_000,
    )
    expect(page.locator("#statistics_modelling-cluster_a")).to_have_value(
        "control",
        timeout=60_000,
    )
    expect(page.locator("#statistics_modelling-cluster_b")).to_have_value(
        "warning",
        timeout=60_000,
    )

    permutations = page.locator("#statistics_modelling-cluster_permutations")
    permutations.fill("100")
    expect(permutations).to_have_value("100")

    page.locator("#statistics_modelling-run_cluster").click()
    expect(page.locator("#statistics_modelling-cluster_status")).to_contain_text(
        "Cluster permutation complete:",
        timeout=180_000,
    )

    assert int(page.locator("#statistics_modelling-cluster_participants").inner_text()) == 12
    assert int(page.locator("#statistics_modelling-cluster_time_bins").inner_text()) == 18
    assert int(page.locator("#statistics_modelling-cluster_count").inner_text()) >= 1
    assert int(page.locator("#statistics_modelling-cluster_sig_count").inner_text()) >= 1
    report = page.locator("#statistics_modelling-cluster_report").inner_text().lower()
    assert "global null" in report
    expect(page.locator("#statistics_modelling-cluster_plot img")).to_be_visible(
        timeout=60_000,
    )

    open_nav(page, "reporting")
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible()
    expect(page.locator("#reporting-analysis_count")).to_have_text("1", timeout=60_000)
    page.get_by_role("tab", name="Downloads", exact=True).click()

    with page.expect_download(timeout=60_000) as replay_download:
        page.locator("#reporting-download_replay").click()
    replay_path = replay_download.value.path()
    assert replay_path is not None
    replay_text = Path(replay_path).read_text(encoding="utf-8")

    assert (
        "from studio.statistics_services import run_cluster_analysis, statistics_source_table"
        in replay_text
    )
    assert 'analyses["statistics_cluster"]' in replay_text
    assert 'source_key = parameters.pop("source_key", "loaded_data")' in replay_text
    assert "EXPECTED_ANALYSES = ['statistics_cluster']" in replay_text
    assert "'n_permutations': 100" in replay_text
    assert "'seed': 2026" in replay_text
    assert "GPBIOMETRICSPY_STUDIO_REPLAY_SUMMARY=" in replay_text

    wrong_result = _execute_replay(
        replay_text,
        data_path=mismatch_fixture,
        script_path=tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-cluster-wrong.py",
    )
    assert wrong_result.returncode != 0
    wrong_output = f"{wrong_result.stdout}\n{wrong_result.stderr}"
    assert "Dataset fingerprint mismatch:" in wrong_output

    exact_result = _execute_replay(
        replay_text,
        data_path=fixture,
        script_path=tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-cluster-exact.py",
    )
    assert exact_result.returncode == 0, (
        "Installed cluster-permutation replay failed.\n"
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
    assert summary["analysis_count"] == 1
    assert summary["analysis_names"] == ["statistics_cluster"]

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
