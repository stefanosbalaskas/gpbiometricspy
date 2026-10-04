from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, expect


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "workflows" / "index.html").exists(), site
    assert (site / "api" / "index.html").exists(), site

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


def test_workflow_map_exposes_all_api_domain_handoffs(page: Page, docs_base_url: str) -> None:
    page.goto(f"{docs_base_url}/workflows/")

    handoffs = page.locator("[data-workflow-api-handoffs] a[data-api-handoff]")
    expect(handoffs).to_have_count(8)

    expected = [
        "Interoperability / exchange formats",
        "Pupil / gaze / fixation / AOI",
        "EDA / GSR / SCR",
        "PPG / HR / IBI / HRV / respiration",
        "Events / alignment / multimodal",
        "QC / validation / reporting / governance",
        "Statistics / design / simulation",
        "Core I/O / schema / utilities",
    ]
    for index, label in enumerate(expected):
        handoff = handoffs.nth(index)
        expect(handoff).to_have_text(label)
        href = handoff.get_attribute("href")
        assert href is not None
        destination = urlparse(href)
        assert destination.path == "/api/"
        assert parse_qs(destination.query) == {"domain": [label]}


def test_workflow_api_handoff_opens_selected_shareable_facet(page: Page, docs_base_url: str) -> None:
    page.goto(f"{docs_base_url}/workflows/")

    page.locator('[data-api-handoff="eda"]').click()

    expect(page.locator('[data-api-domain-filter="EDA / GSR / SCR"]')).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.locator("[data-api-share-note]")).to_contain_text("Bookmark or share")
    expect(page.locator("[data-api-row]:visible").first).to_be_visible()
    assert "/api/" in page.url
    assert "domain=EDA" in page.url
