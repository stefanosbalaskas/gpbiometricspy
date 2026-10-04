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
def docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "index.html").exists(), site
    assert (site / "start-here" / "index.html").exists(), site

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


def _assert_seven_stage_journey(stages) -> None:
    expect(stages).to_have_count(7)
    expected = [
        ("01", "Project"),
        ("02", "Quality"),
        ("03", "Analyze"),
        ("04", "Align"),
        ("05", "Summarise"),
        ("06", "Model"),
        ("07", "Report"),
    ]
    for index, (number, label) in enumerate(expected):
        stage = stages.nth(index)
        expect(stage.locator("strong")).to_have_text(number)
        expect(stage.locator("span")).to_have_text(label)


def test_homepage_research_journey_is_seven_stage(page: Page, docs_base_url: str) -> None:
    page.goto(f"{docs_base_url}/")
    _assert_seven_stage_journey(page.locator(".gp-flow-product > div"))


def test_start_here_research_journey_is_semantic_and_visible(page: Page, docs_base_url: str) -> None:
    page.goto(f"{docs_base_url}/start-here/")

    stages = page.locator(".gp-flow-start-here > [data-research-stage]")
    _assert_seven_stage_journey(stages)

    studio_route = page.locator(".gp-route-card", has_text="Use gpbiometricspy Studio")
    expect(studio_route).to_have_count(1)
    expect(studio_route).to_contain_text("summarisation")
