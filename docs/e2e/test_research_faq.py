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
def research_faq_docs_base_url() -> str:
    site = Path("site").resolve()
    for rel in [
        "research-faq/index.html",
        "learning-paths/index.html",
        "guides/troubleshooting/index.html",
        "guides/validate-dataset/index.html",
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


def test_research_faq_surfaces_evidence_first_decision_rules(
    page: Page, research_faq_docs_base_url: str
) -> None:
    page.goto(f"{research_faq_docs_base_url}/research-faq/")
    article = page.get_by_role("article")
    expect(page.locator("[data-research-faq]")).to_be_visible()
    expect(article).to_contain_text("syntax evidence only")
    expect(article).to_contain_text("mapping hypothesis")
    expect(article).to_contain_text("do not automatically delete observations")
    expect(article).to_contain_text("model fit")


def test_research_faq_keeps_common_claim_boundaries_visible(
    page: Page, research_faq_docs_base_url: str
) -> None:
    page.goto(f"{research_faq_docs_base_url}/research-faq/")
    article = page.get_by_role("article")
    expect(article).to_contain_text("Can AOI dwell time be interpreted as attention?")
    expect(article).to_contain_text("Does a pupil increase mean cognitive load or arousal?")
    expect(article).to_contain_text("I have an `HR` column. Can I compute HRV from it?")
    expect(article).to_contain_text("A result is statistically significant. Can I make a causal claim?")


def test_research_faq_recovery_routes_are_navigable(
    page: Page, research_faq_docs_base_url: str
) -> None:
    page.goto(f"{research_faq_docs_base_url}/research-faq/")
    routes = page.locator("[data-faq-next-routes]")
    expect(routes.locator(".gp-route-card")).to_have_count(4)

    routes.get_by_role("link", name="Choose a learning path").click()
    expect(page).to_have_url(f"{research_faq_docs_base_url}/learning-paths/")

    page.goto(f"{research_faq_docs_base_url}/research-faq/")
    page.locator("[data-faq-next-routes]").get_by_role(
        "link", name="Use the troubleshooting playbook"
    ).click()
    expect(page).to_have_url(f"{research_faq_docs_base_url}/guides/troubleshooting/")


def test_research_faq_scientific_boundary_is_explicit(
    page: Page, research_faq_docs_base_url: str
) -> None:
    page.goto(f"{research_faq_docs_base_url}/research-faq/")
    boundary = page.locator(".gp-science-boundary")
    expect(boundary).to_be_visible()
    expect(boundary).to_contain_text("cannot infer undocumented acquisition facts")
    expect(boundary).to_contain_text("make a study design causal")
