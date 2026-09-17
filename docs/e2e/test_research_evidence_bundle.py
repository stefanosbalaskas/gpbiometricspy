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
EVIDENCE_SCRIPT = ROOT / "examples" / "hands-on" / "research-evidence-bundle.py"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def evidence_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "examples" / "index.html").exists(), site
    assert (site / "guides" / "reporting-reproducibility" / "index.html").exists(), site
    assert (site / "guides" / "validate-dataset" / "index.html").exists(), site
    assert (site / "demo" / "index.html").exists(), site

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


def test_research_evidence_bundle_script_runs_and_exports(tmp_path: Path) -> None:
    assert EVIDENCE_SCRIPT.exists(), EVIDENCE_SCRIPT
    env = os.environ.copy()
    env["GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR"] = str(tmp_path)

    run = subprocess.run(
        [sys.executable, str(EVIDENCE_SCRIPT)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    assert lines, "Research evidence bundle produced no stdout."
    result = json.loads(lines[-1])
    assert result["tutorial"] == "research-evidence-bundle", result
    assert result["status"] == "PASS", result

    required = {
        "study_design.csv",
        "signal_activity_overview.csv",
        "signal_activity_by_group.csv",
        "time_reset_overview.csv",
        "time_reset_segments.csv",
        "time_reset_flags.csv",
        "ttl_events.csv",
        "alignment_overview.csv",
        "alignment_events.csv",
        "aligned_data.csv",
        "eventlocked_summary.csv",
        "eventlocked_samples.csv",
        "analysis_checklist_overview.csv",
        "software.json",
        "methods_text.txt",
        "evidence_manifest.json",
        "research-evidence-bundle-01.png",
    }
    produced = {path.name for path in tmp_path.iterdir()}
    assert required <= produced, (sorted(required), sorted(produced))

    manifest = json.loads((tmp_path / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow"] == "research-evidence-bundle"
    assert manifest["synthetic_demo"] is True
    assert manifest["participant"] == "synthetic_kiosk_p001"
    assert set(manifest["artifacts"]) <= produced
    assert "research-evidence-bundle-01.png" in manifest["artifacts"]


def test_examples_page_routes_to_research_evidence_bundle(
    page: Page, evidence_docs_base_url: str
) -> None:
    page.goto(f"{evidence_docs_base_url}/examples/")
    card = page.locator('[data-learning-route="research-evidence-bundle"]')
    expect(card).to_be_visible()
    expect(card).to_contain_text("Research evidence bundle")
    card.click()
    expect(page).to_have_url(
        f"{evidence_docs_base_url}/guides/reporting-reproducibility/#run-a-reviewable-evidence-bundle"
    )


def test_reporting_guide_exposes_runnable_evidence_bundle(
    page: Page, evidence_docs_base_url: str
) -> None:
    page.goto(f"{evidence_docs_base_url}/guides/reporting-reproducibility/")

    expect(page.locator("[data-research-evidence-bundle]")).to_be_visible()
    expect(page.locator("[data-evidence-bundle-stages] > .gp-guide-card")).to_have_count(6)
    expect(page.locator("main")).to_contain_text("research-evidence-bundle.py")
    expect(page.locator("main")).to_contain_text("evidence_manifest.json")
    expect(page.locator("main")).to_contain_text("Evidence boundary")


def test_evidence_bundle_routes_to_validation_and_demo_guidance(
    page: Page, evidence_docs_base_url: str
) -> None:
    page.goto(f"{evidence_docs_base_url}/guides/reporting-reproducibility/")
    article = page.get_by_role("article")

    article.get_by_role("link", name="Validate a new dataset").click()
    expect(page).to_have_url(f"{evidence_docs_base_url}/guides/validate-dataset/")

    page.goto(f"{evidence_docs_base_url}/guides/reporting-reproducibility/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="synthetic demo guide").click()
    expect(page).to_have_url(f"{evidence_docs_base_url}/demo/")
