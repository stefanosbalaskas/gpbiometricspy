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
def learning_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "guides" / "index.html").exists(), site
    assert (site / "examples" / "index.html").exists(), site

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


def test_guides_workflow_chooser_is_reachable_and_complete(
    page: Page, learning_docs_base_url: str
) -> None:
    page.goto(f"{learning_docs_base_url}/guides/")

    route = page.locator('[data-learning-route="workflow-selection"]')
    expect(route).to_have_count(1)
    route.get_by_role("link", name="Choose a research workflow").click()

    expect(page.locator("h2#choose-your-workflow")).to_be_visible()
    stages = page.locator(
        '[data-research-decision-flow] > [data-research-decision-stage]'
    )
    expect(stages).to_have_count(7)
    expect(page.locator("main")).to_contain_text("Stop rather than guess")


def test_examples_research_recipes_are_reachable_and_use_verified_calls(
    page: Page, learning_docs_base_url: str
) -> None:
    page.goto(f"{learning_docs_base_url}/examples/")

    route = page.locator('[data-learning-route="research-recipes"]')
    expect(route).to_have_count(1)
    route.click()

    expect(page.locator("h2#worked-research-recipes")).to_be_visible()
    main = page.locator("main")
    expect(main).to_contain_text("extract_gazepoint_ttl_events")
    expect(main).to_contain_text("summarize_gazepoint_eventlocked_multimodal")
    expect(main).to_contain_text("summarize_gazepoint_aoi_dwell")
    expect(main).to_contain_text("plot_gazepoint_multimodal_timeline")
    expect(page.locator(".gp-science-boundary")).to_be_visible()
