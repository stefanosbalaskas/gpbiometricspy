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
def learning_paths_docs_base_url() -> str:
    site = Path("site").resolve()
    for rel in [
        "learning-paths/index.html",
        "guides/first-analysis/index.html",
        "guides/index.html",
        "api/index.html",
        "articles/python-native/index.html",
        "guides/research-project-scaffold/index.html",
        "guides/study-metadata-data-dictionary/index.html",
        "guides/bring-your-own-export/index.html",
        "guides/validate-dataset/index.html",
        "qc-exclusion-decision-ledger/index.html",
        "guides/reporting-reproducibility/index.html",
        "interpretation/index.html",
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


def test_learning_paths_exposes_four_documentation_intents(
    page: Page, learning_paths_docs_base_url: str
) -> None:
    page.goto(f"{learning_paths_docs_base_url}/learning-paths/")
    grid = page.locator("[data-learning-intent-grid]")
    expect(grid).to_be_visible()
    intents = grid.locator("[data-learning-intent]")
    expect(intents).to_have_count(4)
    expect(grid).to_contain_text("Learn by doing")
    expect(grid).to_contain_text("Solve a task")
    expect(grid).to_contain_text("Look up facts")
    expect(grid).to_contain_text("Understand why")


def test_learning_paths_real_data_sequence_is_explicit(
    page: Page, learning_paths_docs_base_url: str
) -> None:
    page.goto(f"{learning_paths_docs_base_url}/learning-paths/")
    sequence = page.locator("[data-real-data-learning-path]")
    expect(sequence).to_be_visible()
    expect(sequence.locator(".gp-step")).to_have_count(7)
    expect(sequence).to_contain_text("1 · Project")
    expect(sequence).to_contain_text("2 · Define")
    expect(sequence).to_contain_text("3 · Adapt")
    expect(sequence).to_contain_text("4 · Validate")
    expect(sequence).to_contain_text("5 · Decide")
    expect(sequence).to_contain_text("6 · Analyze")
    expect(sequence).to_contain_text("7 · Report")


def test_learning_paths_intent_links_are_navigable(
    page: Page, learning_paths_docs_base_url: str
) -> None:
    page.goto(f"{learning_paths_docs_base_url}/learning-paths/")
    page.locator('[data-learning-intent="tutorial"]').click()
    expect(page).to_have_url(
        f"{learning_paths_docs_base_url}/guides/first-analysis/"
    )

    page.goto(f"{learning_paths_docs_base_url}/learning-paths/")
    page.locator('[data-learning-intent="reference"]').click()
    expect(page).to_have_url(f"{learning_paths_docs_base_url}/api/")


def test_learning_paths_keeps_scientific_boundary_visible(
    page: Page, learning_paths_docs_base_url: str
) -> None:
    page.goto(f"{learning_paths_docs_base_url}/learning-paths/")
    boundary = page.locator(".gp-science-boundary")
    expect(boundary).to_be_visible()
    expect(boundary).to_contain_text("Column names do not establish units")
    expect(boundary).to_contain_text("model fit does not establish causality")
