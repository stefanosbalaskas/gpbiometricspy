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
def glossary_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "guides" / "index.html").exists(), site
    assert (site / "guides" / "signal-column-glossary" / "index.html").exists(), site
    assert (site / "examples" / "ppg-hrv" / "index.html").exists(), site
    assert (site / "guides" / "troubleshooting" / "index.html").exists(), site

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


def test_guides_map_routes_to_signal_glossary(
    page: Page, glossary_docs_base_url: str
) -> None:
    page.goto(f"{glossary_docs_base_url}/guides/")

    card = page.locator('[data-learning-route="signal-column-glossary"]')
    expect(card).to_be_visible()
    expect(card).to_contain_text("Signal and column glossary")
    card.get_by_role("link", name="Signal and column glossary").click()
    expect(page).to_have_url(f"{glossary_docs_base_url}/guides/signal-column-glossary/")


def test_signal_glossary_exposes_role_and_name_traps(
    page: Page, glossary_docs_base_url: str
) -> None:
    page.goto(f"{glossary_docs_base_url}/guides/signal-column-glossary/")

    expect(page.locator("[data-signal-column-glossary]")).to_be_visible()
    expect(page.locator("[data-column-role-grid] > .gp-guide-card")).to_have_count(4)
    article = page.get_by_role("article")
    expect(article).to_contain_text("HRV is not an HRV metric")
    expect(article).to_contain_text("Presence is not activity")
    expect(article).to_contain_text("heart_rate_validity_not_hrv_metric")
    expect(article).to_contain_text("interbeat_interval_seconds")


def test_signal_glossary_recovery_routes_are_navigable(
    page: Page, glossary_docs_base_url: str
) -> None:
    page.goto(f"{glossary_docs_base_url}/guides/signal-column-glossary/")
    article = page.get_by_role("article")

    article.get_by_role("link", name="PPG / HRV example").click()
    expect(page).to_have_url(f"{glossary_docs_base_url}/examples/ppg-hrv/")

    page.goto(f"{glossary_docs_base_url}/guides/signal-column-glossary/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Troubleshooting and diagnostics").click()
    expect(page).to_have_url(f"{glossary_docs_base_url}/guides/troubleshooting/")
