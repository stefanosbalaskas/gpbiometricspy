from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlencode

import pytest
from playwright.sync_api import Page, expect


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def docs_base_url() -> str:
    site = Path("site").resolve()
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


def _api_url(base_url: str, *, domain: str | None = None, query: str | None = None) -> str:
    params = {}
    if domain:
        params["domain"] = domain
    if query:
        params["q"] = query
    suffix = f"?{urlencode(params)}" if params else ""
    return f"{base_url}/api/{suffix}"


def test_api_filter_restores_shareable_domain_and_query(page: Page, docs_base_url: str) -> None:
    domain = "EDA / GSR / SCR"
    page.goto(_api_url(docs_base_url, domain=domain, query="scr"))

    search = page.locator("[data-api-filter]")
    selected = page.locator(f'[data-api-domain-filter="{domain}"]')
    expect(search).to_have_value("scr")
    expect(selected).to_have_attribute("aria-pressed", "true")
    expect(page.locator("[data-api-share-note]")).to_contain_text("Bookmark or share")

    visible_rows = page.locator("[data-api-row]:visible")
    assert visible_rows.count() > 0
    for index in range(min(visible_rows.count(), 8)):
        expect(visible_rows.nth(index).locator("td").nth(1)).to_have_text(domain)

    url = page.url
    assert "domain=EDA+%2F+GSR+%2F+SCR" in url or "domain=EDA%20%2F%20GSR%20%2F%20SCR" in url
    assert "q=scr" in url


def test_api_filter_updates_url_and_restores_history(page: Page, docs_base_url: str) -> None:
    page.goto(_api_url(docs_base_url))
    search = page.locator("[data-api-filter]")

    page.keyboard.press("/")
    expect(search).to_be_focused()

    domain = "PPG / HR / IBI / HRV / respiration"
    ppg = page.locator(f'[data-api-domain-filter="{domain}"]')
    ppg.click()
    expect(ppg).to_have_attribute("aria-pressed", "true")
    assert "domain=PPG" in page.url

    search.fill("hrv")
    assert "q=hrv" in page.url
    assert page.locator("[data-api-row]:visible").count() > 0

    page.go_back()
    expect(page.locator('[data-api-domain-filter="all"]')).to_have_attribute("aria-pressed", "true")
    expect(search).to_have_value("")
    assert "domain=" not in page.url
    assert "q=" not in page.url


def test_api_filter_empty_state_and_escape_reset(page: Page, docs_base_url: str) -> None:
    page.goto(_api_url(docs_base_url))
    search = page.locator("[data-api-filter]")
    search.fill("definitely-no-such-export-zzzz")

    expect(page.locator("[data-api-result-count]")).to_have_text("0 functions")
    expect(page.locator("[data-api-empty]")).to_be_visible()
    expect(page.locator("[data-api-clear]")).to_be_visible()

    search.press("Escape")
    expect(search).to_have_value("")
    expect(search).to_be_focused()
    expect(page.locator("[data-api-domain-filter='all']")).to_have_attribute("aria-pressed", "true")
    expect(page.locator("[data-api-empty]")).to_be_hidden()
    assert "q=" not in page.url
    assert "domain=" not in page.url
