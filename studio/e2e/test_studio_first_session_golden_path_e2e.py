from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def test_first_session_physiology_walkthrough_reaches_saved_reporting_checkpoint(
    page: Page,
    app: ShinyAppProc,
) -> None:
    page.goto(app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    # The first session begins with explanatory routes, not an automatically run analysis.
    expect(page.get_by_role("heading", name="Teaching routes")).to_be_visible()
    expect(page.get_by_text("Physiology foundations", exact=True)).to_be_visible()
    expect(page.locator("#analysis_count")).to_have_text("0")

    # Choose the physiology walkthrough. Guided start loads only bundled synthetic data
    # and completes foundation QC before opening the first signal workflow.
    page.locator("#guided_start").select_option("physiology")
    expect(page.locator("#guided_start_description")).to_contain_text(
        "Run EDA / SCR analysis → Run PPG / HR / HRV analysis → "
        "Build the reproducible report"
    )
    page.locator("#start_guided").click()

    expect(page.get_by_text("EDA / SCR analysis controls", exact=True)).to_be_visible(
        timeout=60_000
    )
    expect(page.locator("#status")).to_contain_text(
        "EDA and cardiovascular walkthrough ready. Foundation QC is complete. "
        "First step: Run EDA / SCR analysis.",
        timeout=60_000,
    )
    expect(page.locator("#qc_state")).to_have_text("Complete", timeout=60_000)
    expect(page.locator("#project_name")).to_have_text(
        "Synthetic physiology walkthrough",
        timeout=30_000,
    )

    eda_readiness = page.locator("#eda_scr_readiness-module_readiness")
    expect(eda_readiness).to_contain_text("Ready for guided analysis", timeout=30_000)

    # The teaching card must describe the live Guided defaults without changing them.
    eda_preset = page.locator('[data-preset-key="eda-foundations"]')
    expect(eda_preset).to_be_visible()
    expect(eda_preset).to_contain_text("Tonic window: 31 samples")
    expect(eda_preset).to_contain_text("Automatic SCR threshold")
    expect(page.locator('#eda_scr-mode input[value="guided"]')).to_be_checked()
    expect(page.locator("#eda_scr-window_size")).to_have_value("31")
    expect(page.locator("#eda_scr-auto_threshold")).to_be_checked()

    page.locator("#eda_scr-run").click()
    expect(page.locator("#eda_scr-status")).to_contain_text(
        "EDA/SCR workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    expect(eda_readiness).to_contain_text("EDA / SCR result stored", timeout=30_000)

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#analysis_count")).to_have_text("1", timeout=30_000)
    expect(page.locator("#guided_progress")).to_have_text(
        "EDA and cardiovascular walkthrough: 1/3 guided steps complete",
        timeout=30_000,
    )
    expect(page.locator("#continue_guided")).to_have_text(
        "Continue: Run PPG / HR / HRV analysis"
    )

    # Continue through the second signal workflow rather than jumping to Reporting.
    page.locator("#continue_guided").click()
    expect(
        page.get_by_text("PPG / HR / HRV analysis controls", exact=True)
    ).to_be_visible(timeout=30_000)
    ppg_readiness = page.locator("#ppg_hr_hrv_readiness-module_readiness")
    expect(ppg_readiness).to_contain_text("Ready for guided analysis", timeout=30_000)
    expect(page.locator('[data-preset-key="cardiac-foundations"]')).to_be_visible()

    page.locator("#ppg_hr_hrv-run").click()
    expect(page.locator("#ppg_hr_hrv-status")).to_contain_text(
        "PPG/HR/HRV workflow complete using public gpbiometricspy APIs.",
        timeout=90_000,
    )
    expect(ppg_readiness).to_contain_text(
        "PPG / HR / HRV result stored",
        timeout=30_000,
    )

    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#analysis_count")).to_have_text("2", timeout=30_000)
    expect(page.locator("#guided_progress")).to_have_text(
        "EDA and cardiovascular walkthrough: 2/3 guided steps complete",
        timeout=30_000,
    )
    expect(page.locator("#continue_guided")).to_have_text(
        "Continue: Build the reproducible report"
    )

    # Reporting is reached through the same guided Continue action a first-time user sees.
    page.locator("#continue_guided").click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.locator("#reporting-identity_summary")).to_contain_text(
        "Project: Synthetic physiology walkthrough",
        timeout=30_000,
    )
    expect(page.locator("#reporting-analysis_count")).to_have_text("2", timeout=30_000)

    page.locator("#reporting-build_report").click()
    expect(page.locator("#reporting-report_status")).to_contain_text(
        "Reporting artifacts built through public gpbiometricspy reporting APIs.",
        timeout=90_000,
    )

    # Completing the report must close the three-step guided loop and keep Reporting
    # directly reopenable from the first-session Continue affordance.
    page.get_by_role("tab", name="Home", exact=True).click()
    expect(page.locator("#guided_progress")).to_have_text(
        "EDA and cardiovascular walkthrough: 3/3 guided steps complete",
        timeout=30_000,
    )
    expect(page.locator("#continue_guided")).to_have_text("Open completed project report")
    page.locator("#continue_guided").click()
    expect(page.get_by_text("Privacy-preserving project model", exact=True)).to_be_visible(
        timeout=30_000
    )

    page.get_by_role("tab", name="Inventory", exact=True).click()
    page.get_by_role("tab", name="Timeline", exact=True).click()
    timeline = page.locator("#reporting-project_timeline")
    expect(timeline).to_contain_text("Foundation QC completed", timeout=60_000)
    expect(timeline).to_contain_text("EDA / SCR completed")
    expect(timeline).to_contain_text("Analyze")
    expect(timeline).to_contain_text("Report")

    page.get_by_role("tab", name="Project recipe", exact=True).click()
    expect(page.locator("#reporting-project_save_state")).to_have_text(
        "Unsaved",
        timeout=30_000,
    )
    with page.expect_download(timeout=60_000) as download_info:
        page.locator("#reporting-download_recipe").click()
    assert download_info.value.path() is not None
    expect(page.locator("#reporting-project_save_state")).to_have_text(
        "Saved",
        timeout=30_000,
    )

    # A later metadata edit must visibly dirty the saved checkpoint.
    page.locator("#project_name_input").fill("First-session physiology revised")
    page.locator("#apply_project_name").click()
    expect(page.locator("#status")).to_contain_text(
        "Project name set to 'First-session physiology revised'.",
        timeout=30_000,
    )
    expect(page.locator("#reporting-project_save_state")).to_have_text(
        "Unsaved changes",
        timeout=30_000,
    )

    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
