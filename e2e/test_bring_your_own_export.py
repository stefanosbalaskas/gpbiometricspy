from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import Page, expect


ROOT = Path(__file__).resolve().parents[2]
ADAPTATION_SCRIPT = ROOT / "examples" / "hands-on" / "bring-your-own-export.py"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def adaptation_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "guides" / "index.html").exists(), site
    assert (site / "guides" / "bring-your-own-export" / "index.html").exists(), site
    assert (site / "examples" / "index.html").exists(), site
    assert (site / "guides" / "signal-column-glossary" / "index.html").exists(), site

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


def test_bring_your_own_export_script_runs_and_exports(tmp_path: Path) -> None:
    assert ADAPTATION_SCRIPT.exists(), ADAPTATION_SCRIPT
    env = os.environ.copy()
    env["GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR"] = str(tmp_path)

    run = subprocess.run(
        [sys.executable, str(ADAPTATION_SCRIPT)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    assert lines, "Export adaptation example produced no stdout."
    result = json.loads(lines[-1])
    assert result["tutorial"] == "bring-your-own-export", result
    assert result["status"] == "PASS", result

    required = {
        "source_like_export.csv",
        "column_name_map.csv",
        "standardized_preview.csv",
        "schema_overview.csv",
        "schema_columns.csv",
        "timebase_overview.csv",
        "timebase_interval_summary.csv",
        "ttl_events.csv",
        "adaptation_manifest.json",
    }
    produced = {path.name for path in tmp_path.iterdir()}
    assert required <= produced, (sorted(required), sorted(produced))

    manifest = json.loads(
        (tmp_path / "adaptation_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["workflow"] == "bring-your-own-export"
    assert manifest["synthetic_demo"] is True
    assert manifest["mapping"]["subject_id"] == "USER"
    assert manifest["mapping"]["timestamp_s"] == "TIME"
    assert manifest["mapping"]["eda_us"] == "GSR_US"
    assert manifest["mapping"]["event_marker"] == "TTL"
    assert set(manifest["artifacts"]) <= produced


def test_guides_map_routes_to_export_adaptation(
    page: Page, adaptation_docs_base_url: str
) -> None:
    page.goto(f"{adaptation_docs_base_url}/guides/")
    card = page.locator('[data-learning-route="bring-your-own-export"]')
    expect(card).to_be_visible()
    expect(card).to_contain_text("Bring your own export safely")
    card.get_by_role("link", name="Bring your own export safely").click()
    expect(page).to_have_url(
        f"{adaptation_docs_base_url}/guides/bring-your-own-export/"
    )


def test_examples_page_surfaces_export_adaptation(
    page: Page, adaptation_docs_base_url: str
) -> None:
    page.goto(f"{adaptation_docs_base_url}/examples/")
    card = page.locator('[data-learning-route="bring-your-own-export"]')
    expect(card).to_be_visible()
    expect(card).to_contain_text("Adapt an unfamiliar export")
    card.click()
    expect(page).to_have_url(
        f"{adaptation_docs_base_url}/guides/bring-your-own-export/"
    )


def test_export_adaptation_guide_exposes_evidence_sequence(
    page: Page, adaptation_docs_base_url: str
) -> None:
    page.goto(f"{adaptation_docs_base_url}/guides/bring-your-own-export/")
    expect(page.locator("[data-bring-your-own-export-guide]")).to_be_visible()
    expect(page.locator("[data-export-adaptation-stages] > .gp-guide-card")).to_have_count(6)
    article = page.get_by_role("article")
    expect(article).to_contain_text("Recognition is not validation")
    expect(article).to_contain_text("A minimum acceptance checklist")
    expect(article).to_contain_text("Common adaptation mistakes")
    expect(article).to_contain_text("standardise_gazepoint_biometric_names")
    expect(article).to_contain_text("adaptation_manifest.json")


def test_export_adaptation_recovery_routes_are_navigable(
    page: Page, adaptation_docs_base_url: str
) -> None:
    page.goto(f"{adaptation_docs_base_url}/guides/bring-your-own-export/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Signal and column glossary").click()
    expect(page).to_have_url(
        f"{adaptation_docs_base_url}/guides/signal-column-glossary/"
    )

    page.goto(f"{adaptation_docs_base_url}/guides/bring-your-own-export/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Validate a new dataset").click()
    expect(page).to_have_url(
        f"{adaptation_docs_base_url}/guides/validate-dataset/"
    )
