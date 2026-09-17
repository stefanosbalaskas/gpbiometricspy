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
def homepage_docs_base_url() -> str:
    site = Path("site").resolve()
    for path in [
        site / "index.html",
        site / "guides" / "research-project-scaffold" / "index.html",
        site / "guides" / "bring-your-own-export" / "index.html",
        site / "guides" / "validate-dataset" / "index.html",
        site / "guides" / "reporting-reproducibility" / "index.html",
        site / "workflows" / "index.html",
    ]:
        assert path.exists(), path

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


def test_homepage_surfaces_project_and_export_entrypoints(
    page: Page, homepage_docs_base_url: str
) -> None:
    page.goto(f"{homepage_docs_base_url}/")

    expect(page.locator('[data-home-route="new-project"]')).to_be_visible()
    expect(page.locator('[data-home-route="own-export"]')).to_be_visible()
    expect(page.get_by_role("link", name="Bring your own export", exact=True).first).to_be_visible()

    journey = page.locator("[data-home-research-journey]")
    expect(journey).to_be_visible()
    expect(journey.locator(":scope > div")).to_have_count(5)
    for label in ["Scaffold", "Adapt", "Validate", "Analyze", "Report"]:
        expect(journey.get_by_role("link", name=label, exact=True)).to_be_visible()


def test_homepage_research_journey_routes_to_guides(
    page: Page, homepage_docs_base_url: str
) -> None:
    page.goto(f"{homepage_docs_base_url}/")
    page.locator('[data-home-route="new-project"]').click()
    expect(page).to_have_url(
        f"{homepage_docs_base_url}/guides/research-project-scaffold/"
    )

    page.goto(f"{homepage_docs_base_url}/")
    page.locator('[data-home-route="own-export"]').click()
    expect(page).to_have_url(f"{homepage_docs_base_url}/guides/bring-your-own-export/")

    page.goto(f"{homepage_docs_base_url}/")
    page.locator("[data-home-research-journey]").get_by_role(
        "link", name="Report", exact=True
    ).click()
    expect(page).to_have_url(
        f"{homepage_docs_base_url}/guides/reporting-reproducibility/"
    )
