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
def demo_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "demo" / "index.html").exists(), site
    assert (site / "examples" / "eda-scr" / "index.html").exists(), site

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


def test_demo_data_guide_exposes_design_workflow_and_boundaries(
    page: Page, demo_docs_base_url: str
) -> None:
    page.goto(f"{demo_docs_base_url}/demo/")

    expect(page.locator("[data-demo-data-guide]")).to_be_visible()
    expect(page.locator("main")).to_contain_text("69,120")
    expect(page.locator("main")).to_contain_text("interface complexity")
    expect(page.locator("main")).to_contain_text("feedback clarity")
    expect(page.locator("[data-demo-evidence-checklist] > .gp-guide-card")).to_have_count(4)
    expect(page.locator(".gp-science-boundary")).to_be_visible()


def test_demo_data_guide_links_to_worked_signal_example(
    page: Page, demo_docs_base_url: str
) -> None:
    page.goto(f"{demo_docs_base_url}/demo/")

    page.get_by_role("link", name="EDA / SCR example").click()
    expect(page).to_have_url(f"{demo_docs_base_url}/examples/eda-scr/")
    expect(page.locator("main")).to_contain_text("EDA")
