from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import Page, expect


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def onboarding_docs_base_url() -> str:
    site = Path("site").resolve()
    for rel in [
        "index.html",
        "start-here/index.html",
        "guides/research-project-scaffold/index.html",
        "guides/study-metadata-data-dictionary/index.html",
        "guides/bring-your-own-export/index.html",
        "guides/validate-dataset/index.html",
        "guides/hands-on-eda-research/index.html",
    ]:
        assert (site / rel).exists(), rel

    handler = partial(_QuietHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_homepage_exposes_four_step_research_onboarding(
    page: Page, onboarding_docs_base_url: str
) -> None:
    page.goto(f"{onboarding_docs_base_url}/")
    path = page.locator("[data-research-onboarding-path]")
    expect(path).to_be_visible()
    steps = path.locator("[data-onboarding-step]")
    expect(steps).to_have_count(4)
    expect(path).to_contain_text("Create a reviewable project structure")
    expect(path).to_contain_text("Map your own export without hiding provenance")
    expect(path).to_contain_text("Establish measurement readiness")
    expect(path).to_contain_text("Run a complete checked workflow")


def test_homepage_project_entry_routes_to_scaffold(
    page: Page, onboarding_docs_base_url: str
) -> None:
    page.goto(f"{onboarding_docs_base_url}/")
    page.get_by_role("link", name="Set up a research project").click()
    expect(page).to_have_url(
        f"{onboarding_docs_base_url}/guides/research-project-scaffold/"
    )


def test_start_here_exposes_five_stage_bring_your_own_data_path(
    page: Page, onboarding_docs_base_url: str
) -> None:
    page.goto(f"{onboarding_docs_base_url}/start-here/")
    card = page.locator('[data-learning-route="research-project-onboarding"]')
    expect(card).to_be_visible()
    expect(card).to_contain_text("Set up, define, adapt, validate, then analyze")
    sequence = page.locator("[data-research-onboarding-sequence]")
    expect(sequence).to_be_visible()
    expect(sequence.locator(".gp-step")).to_have_count(5)
    expect(sequence).to_contain_text("Study metadata and data dictionary")
    expect(sequence).to_contain_text("Bring your own export safely")
    expect(sequence).to_contain_text("new-dataset validation")


def test_start_here_dictionary_route_is_navigable(
    page: Page, onboarding_docs_base_url: str
) -> None:
    page.goto(f"{onboarding_docs_base_url}/start-here/")
    page.get_by_role("link", name="Define variables, clocks and events explicitly").click()
    expect(page).to_have_url(
        f"{onboarding_docs_base_url}/guides/study-metadata-data-dictionary/"
    )


def test_start_here_existing_export_route_is_navigable(
    page: Page, onboarding_docs_base_url: str
) -> None:
    page.goto(f"{onboarding_docs_base_url}/start-here/")
    page.get_by_role("link", name="Adapt an unfamiliar file safely").click()
    expect(page).to_have_url(
        f"{onboarding_docs_base_url}/guides/bring-your-own-export/"
    )
