from __future__ import annotations

from pathlib import Path

import gpbiometricspy as gp
from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.playwright import controller
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _cluster_fixture(tmp_path: Path) -> Path:
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
        seed=7,
    )
    path = tmp_path / "cluster_timecourse.csv"
    table.to_csv(path, index=False)
    return path


def _load_cluster_timecourse(page: Page, app: ShinyAppProc, path: Path) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()
    page.locator("#upload").set_input_files(str(path))

    def _uploaded(value) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], dict)
            and value[0].get("name") == path.name
        )

    controller.AppTestValues(page).expect_input("upload", _uploaded, timeout=30.0)
    page.locator("#load_upload").click()
    expect(page.locator("#status")).to_contain_text(
        "Upload imported through gpbiometricspy.",
        timeout=60_000,
    )
    assert int(page.locator("#row_count").inner_text().replace(",", "")) == 432


def test_cluster_permutation_valid_design_renders_and_exports(
    page: Page,
    app: ShinyAppProc,
    tmp_path: Path,
) -> None:
    fixture = _cluster_fixture(tmp_path)
    _load_cluster_timecourse(page, app, fixture)

    open_nav(page, "statistics_modelling")
    expect(page.get_by_text("Model controls", exact=True)).to_be_visible()
    page.get_by_role("tab", name="Cluster permutation", exact=True).click()
    expect(page.get_by_text("Cluster controls", exact=True)).to_be_visible()

    source = page.locator("#statistics_modelling-cluster_source")
    expect(source.locator('option[value="loaded_data"]')).to_have_count(1, timeout=60_000)
    source.select_option("loaded_data")
    expect(source).to_have_value("loaded_data")

    expect(page.locator("#statistics_modelling-cluster_outcome")).to_have_value("value", timeout=60_000)
    expect(page.locator("#statistics_modelling-cluster_time")).to_have_value("time", timeout=60_000)
    expect(page.locator("#statistics_modelling-cluster_condition")).to_have_value("condition", timeout=60_000)
    expect(page.locator("#statistics_modelling-cluster_participant")).to_have_value("subject", timeout=60_000)
    expect(page.locator("#statistics_modelling-cluster_a")).to_have_value("control", timeout=60_000)
    expect(page.locator("#statistics_modelling-cluster_b")).to_have_value("warning", timeout=60_000)

    page.locator("#statistics_modelling-run_cluster").click()
    expect(page.locator("#statistics_modelling-cluster_status")).to_contain_text(
        "Cluster permutation complete:",
        timeout=240_000,
    )

    assert int(page.locator("#statistics_modelling-cluster_participants").inner_text()) == 12
    assert int(page.locator("#statistics_modelling-cluster_time_bins").inner_text()) == 18
    assert int(page.locator("#statistics_modelling-cluster_count").inner_text()) >= 1
    assert int(page.locator("#statistics_modelling-cluster_sig_count").inner_text()) >= 1
    expect(page.get_by_text("Application error", exact=False)).to_have_count(0)

    expect(page.get_by_text("Package-native cluster plot", exact=True)).to_be_visible()
    expect(page.locator("#statistics_modelling-cluster_plot img")).to_be_visible(timeout=60_000)
    report = page.locator("#statistics_modelling-cluster_report").inner_text().lower()
    assert "global null" in report

    page.get_by_role("tab", name="Null distribution", exact=True).click()
    expect(page.get_by_text("Maximum-cluster null distribution", exact=True)).to_be_visible()
    expect(page.locator("#statistics_modelling-cluster_null_plot img")).to_be_visible(timeout=60_000)

    with page.expect_download(timeout=60_000) as clusters_download_info:
        page.locator("#statistics_modelling-download_clusters").click()
    clusters_path = clusters_download_info.value.path()
    assert clusters_path is not None
    assert len(Path(clusters_path).read_text(encoding="utf-8").splitlines()) > 1

    with page.expect_download(timeout=60_000) as timewise_download_info:
        page.locator("#statistics_modelling-download_timewise").click()
    timewise_path = timewise_download_info.value.path()
    assert timewise_path is not None
    assert len(Path(timewise_path).read_text(encoding="utf-8").splitlines()) > 10

    with page.expect_download(timeout=60_000) as grid_download_info:
        page.locator("#statistics_modelling-download_cluster_grid").click()
    grid_path = grid_download_info.value.path()
    assert grid_path is not None
    assert len(Path(grid_path).read_text(encoding="utf-8").splitlines()) > 100

    with page.expect_download(timeout=60_000) as script_download_info:
        page.locator("#statistics_modelling-download_cluster_script").click()
    script_path = script_download_info.value.path()
    assert script_path is not None
    script = Path(script_path).read_text(encoding="utf-8")
    assert "prepare_gazepoint_timecourse_test_data" in script
    assert "diagnose_gazepoint_cluster_design" in script
    assert "run_gazepoint_cluster_permutation" in script
    assert "participant_col='subject'" in script
    assert "condition_a='control'" in script
    assert "condition_b='warning'" in script
    assert "n_permutations=1000" in script
    assert "seed=2026" in script
