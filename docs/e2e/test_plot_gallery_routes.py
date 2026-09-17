from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urljoin, urlparse

import pytest
from playwright.sync_api import Page, expect


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def gallery_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "plot-gallery" / "index.html").exists(), site
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


def test_plot_gallery_exposes_six_workflow_handoffs(
    page: Page, gallery_docs_base_url: str
) -> None:
    page.goto(f"{gallery_docs_base_url}/plot-gallery/")

    cards = page.locator("[data-gallery-handoffs] > [data-gallery-handoff]")
    expect(cards).to_have_count(6)
    assert cards.evaluate_all(
        "els => els.map(el => el.getAttribute('data-gallery-handoff'))"
    ) == ["quality", "eda", "cardiac", "eye", "alignment", "inference"]
    expect(page.locator(".gp-science-boundary")).to_be_visible()


def test_plot_gallery_filtered_api_handoffs_keep_domain_state(
    page: Page, gallery_docs_base_url: str
) -> None:
    page.goto(f"{gallery_docs_base_url}/plot-gallery/")

    expected = {
        "quality": "QC / validation / reporting / governance",
        "eda": "EDA / GSR / SCR",
        "cardiac": "PPG / HR / IBI / HRV / respiration",
        "eye": "Pupil / gaze / fixation / AOI",
        "alignment": "Events / alignment / multimodal",
        "inference": "Statistics / design / simulation",
    }

    for key, domain in expected.items():
        link = page.locator(f'[data-gallery-handoff="{key}"] a[href*="/api/?domain="]')
        expect(link).to_have_count(1)
        href = link.get_attribute("href")
        assert href is not None
        parsed = urlparse(urljoin(page.url, href))
        assert parsed.path == "/api/"
        assert parse_qs(parsed.query) == {"domain": [domain]}

    page.locator('[data-gallery-handoff="eda"] a[href*="/api/?domain="]').click()
    expect(page.locator('[data-api-domain-filter="EDA / GSR / SCR"]')).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.locator("main")).to_contain_text("Bookmark or share")
