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
def troubleshooting_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "guides" / "index.html").exists(), site
    assert (site / "guides" / "troubleshooting" / "index.html").exists(), site
    assert (site / "guides" / "validate-dataset" / "index.html").exists(), site
    assert (site / "guides" / "timebase-alignment" / "index.html").exists(), site

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


def test_guides_map_routes_to_troubleshooting(
    page: Page, troubleshooting_docs_base_url: str
) -> None:
    page.goto(f"{troubleshooting_docs_base_url}/guides/")

    card = page.locator('[data-learning-route="troubleshooting"]')
    expect(card).to_be_visible()
    expect(card).to_contain_text("Troubleshoot a workflow")
    card.get_by_role("link", name="Troubleshoot a workflow").click()
    expect(page).to_have_url(f"{troubleshooting_docs_base_url}/guides/troubleshooting/")


def test_troubleshooting_guide_exposes_diagnostic_sequence(
    page: Page, troubleshooting_docs_base_url: str
) -> None:
    page.goto(f"{troubleshooting_docs_base_url}/guides/troubleshooting/")

    expect(page.locator("[data-troubleshooting-guide]")).to_be_visible()
    expect(page.locator("[data-troubleshooting-stages] > .gp-step")).to_have_count(6)
    expect(page.locator("main")).to_contain_text("Symptom → diagnostic → action")
    expect(page.locator("main")).to_contain_text("Minimal triage scaffold")
    expect(page.locator("main")).to_contain_text("Build a useful diagnostic report")
    expect(page.locator("main")).to_contain_text("Stop rather than patch around missing evidence")


def test_troubleshooting_recovery_routes_are_navigable(
    page: Page, troubleshooting_docs_base_url: str
) -> None:
    page.goto(f"{troubleshooting_docs_base_url}/guides/troubleshooting/")

    page.get_by_role("link", name="Validate a new dataset").first.click()
    expect(page).to_have_url(f"{troubleshooting_docs_base_url}/guides/validate-dataset/")

    page.goto(f"{troubleshooting_docs_base_url}/guides/troubleshooting/")
    page.get_by_role("link", name="Timebase and alignment").first.click()
    expect(page).to_have_url(f"{troubleshooting_docs_base_url}/guides/timebase-alignment/")
