from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def test_home_exposes_nonexecuting_teaching_routes(page: Page, app: ShinyAppProc) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    routes = page.locator(".studio-teaching-routes")
    expect(routes).to_be_visible()
    expect(routes).to_contain_text("Teaching routes")
    expect(routes).to_contain_text("They are not automated analysis pipelines")

    for key, label in (
        ("physiology", "Physiology foundations"),
        ("eye_tracking", "Eye-tracking foundations"),
        ("multimodal", "Event-linked multimodal workflow"),
        ("modelling", "From measurements to a defensible model"),
    ):
        card = page.locator(f'[data-route-key="{key}"]')
        expect(card).to_be_visible()
        expect(card).to_contain_text(label)
        expect(card).to_contain_text("Route:")
        expect(card).to_contain_text("Evidence focus:")
        expect(card).to_contain_text("Stop and check:")

    expect(page.locator("#analysis_count")).to_have_text("0")
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)


def test_preset_guidance_matches_controls_without_running_analysis(
    page: Page,
    app: ShinyAppProc,
) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )
    expect(page.locator("#analysis_count")).to_have_text("0")

    open_nav(page, "eda_scr", group="Analyze")
    eda_preset = page.locator('[data-preset-key="eda-foundations"]')
    expect(eda_preset).to_be_visible()
    expect(eda_preset).to_contain_text("EDA/SCR foundations")
    expect(eda_preset).to_contain_text("Tonic window: 31 samples")
    expect(eda_preset).to_contain_text("Automatic SCR threshold")
    expect(eda_preset).to_contain_text("Minimum peak distance: 10 samples")
    expect(eda_preset).to_contain_text("do not by themselves identify emotion, stress, trust")
    expect(page.get_by_text("Advisory only.", exact=False)).to_be_visible()

    expect(page.locator('#eda_scr-mode input[value="guided"]')).to_be_checked()
    expect(page.locator("#eda_scr-window_size")).to_have_value("31")
    expect(page.locator("#eda_scr-auto_threshold")).to_be_checked()
    expect(page.locator("#eda_scr-min_peak_distance")).to_have_value("10")
    expect(page.locator("#eda_scr-analysis_status")).to_have_text("Not run")

    open_nav(page, "statistics_modelling")
    model_preset = page.locator('[data-preset-key="model-preparation-foundations"]')
    cluster_preset = page.locator('[data-preset-key="cluster-permutation-foundations"]')
    expect(model_preset).to_be_visible()
    expect(cluster_preset).to_be_visible()
    expect(model_preset).to_contain_text("Minimum complete rows: 10")
    expect(model_preset).to_contain_text("not evidence that a model was fitted")
    expect(cluster_preset).to_contain_text("Permutations: 1000")
    expect(cluster_preset).to_contain_text("Two-sided test; seed: 2026")
    expect(cluster_preset).to_contain_text("validated two-condition within-subject")

    expect(page.locator('#statistics_modelling-model_mode input[value="guided"]')).to_be_checked()
    expect(page.locator("#statistics_modelling-model_min_rows")).to_have_value("10")

    page.get_by_role("tab", name="Cluster permutation", exact=True).click()
    expect(page.locator('#statistics_modelling-cluster_mode input[value="guided"]')).to_be_checked()
    expect(page.locator("#statistics_modelling-cluster_bin_width")).to_have_value("0.1")
    expect(page.locator("#statistics_modelling-cluster_permutations")).to_have_value("1000")
    expect(page.locator("#statistics_modelling-cluster_forming_alpha")).to_have_value("0.05")
    expect(page.locator("#statistics_modelling-cluster_alpha")).to_have_value("0.05")
    expect(page.locator("#statistics_modelling-cluster_tail")).to_have_value("two.sided")
    expect(page.locator("#statistics_modelling-cluster_seed")).to_have_value("2026")
    expect(page.locator("#statistics_modelling-cluster_sensitivity")).not_to_be_checked()

    open_nav(page, "home")
    expect(page.locator("#analysis_count")).to_have_text("0")
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
