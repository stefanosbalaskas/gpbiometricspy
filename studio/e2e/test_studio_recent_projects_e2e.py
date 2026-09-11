from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, expect
from studio.e2e.navigation import open_nav
from shiny.pytest import create_app_fixture
from shiny.run import ShinyAppProc


APP_PATH = Path(__file__).resolve().parent / "apps" / "recent_projects_app.py"
recent_projects_app = create_app_fixture(APP_PATH, scope="module", timeout_secs=90)


def _download(page: Page, selector: str) -> Path:
    with page.expect_download(timeout=60_000) as download_info:
        page.locator(selector).click()
    path = download_info.value.path()
    assert path is not None
    return Path(path)


def test_local_recent_projects_are_opt_in_metadata_only_and_clearable(
    page: Page,
    recent_projects_app: ShinyAppProc,
) -> None:
    page.goto(recent_projects_app.url)
    expect(page.get_by_text("gpbiometricspy Studio", exact=True)).to_be_visible()

    page.locator("#load_demo").click()
    expect(page.locator("#dataset_name")).to_have_text(
        "Bundled synthetic kiosk demo",
        timeout=60_000,
    )
    page.locator("#project_name_input").fill("Recent projects browser validation")
    page.locator("#apply_project_name").click()
    expect(page.locator("#status")).to_contain_text("Project name set to", timeout=30_000)

    open_nav(page, "reporting")
    page.get_by_role("tab", name="Project recipe", exact=True).click()

    remember = page.locator("#reporting-remember_recent")
    expect(remember).to_be_visible()
    expect(remember).not_to_be_checked()

    recent_table = page.locator("#reporting-recent_projects-table")
    expect(recent_table).to_contain_text(
        "No recent project metadata is remembered on this device.",
        timeout=30_000,
    )

    # Saving with the opt-in disabled must preserve the existing recipe lifecycle
    # without writing any recent-project metadata.
    first_recipe = _download(page, "#reporting-download_recipe")
    expect(page.locator("#reporting-project_save_state")).to_have_text("Saved", timeout=30_000)
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "Current project metadata is saved.",
        timeout=30_000,
    )
    expect(recent_table).to_contain_text(
        "No recent project metadata is remembered on this device."
    )

    first_payload = json.loads(first_recipe.read_text(encoding="utf-8"))
    fingerprint = first_payload["dataset"]["sha256"]
    assert len(fingerprint) == 64

    # Opting in on the next recipe save records only the privacy-minimal locator.
    remember.check()
    _download(page, "#reporting-download_recipe")
    expect(page.locator("#reporting-recipe_status")).to_contain_text(
        "Recent-project metadata was remembered on this device.",
        timeout=30_000,
    )
    expect(recent_table).to_contain_text("Recent projects browser validation", timeout=30_000)
    expect(recent_table).to_contain_text("Match")
    expect(recent_table).to_contain_text("Recent-projects-browser-validation-project-recipe.json")
    expect(recent_table).to_contain_text(f"{fingerprint[:12]}…")

    visible_recent = recent_table.inner_text()
    assert fingerprint not in visible_recent
    assert "Bundled synthetic kiosk demo" not in visible_recent
    assert "GSR_US" not in visible_recent
    assert "participant" not in visible_recent.lower()
    assert "parameters" not in visible_recent.lower()
    assert "provenance" not in visible_recent.lower()

    # History can be removed independently of the current in-memory project.
    page.locator("#reporting-recent_projects-clear").click()
    expect(page.locator("#reporting-recent_projects-status")).to_contain_text(
        "Recent-project metadata cleared from this device.",
        timeout=30_000,
    )
    expect(recent_table).to_contain_text(
        "No recent project metadata is remembered on this device.",
        timeout=30_000,
    )
    expect(page.locator("#reporting-project_save_state")).to_have_text("Saved")
    expect(page.locator(".shiny-output-error:visible")).to_have_count(0)
    expect(page.locator(".shiny-notification-error:visible")).to_have_count(0)
