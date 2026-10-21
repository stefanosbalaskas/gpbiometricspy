from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pandas as pd
import pytest
from playwright.sync_api import Page, expect


ROOT = Path(__file__).resolve().parents[2]
LEDGER_SCRIPT = ROOT / "examples" / "hands-on" / "create-qc-exclusion-ledger.py"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def exclusion_docs_base_url() -> str:
    site = Path("site").resolve()
    for rel in [
        "qc-exclusion-decision-ledger/index.html",
        "guides/validate-dataset/index.html",
        "guides/troubleshooting/index.html",
        "guides/reporting-reproducibility/index.html",
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


def test_qc_exclusion_ledger_script_keeps_candidates_review_only(tmp_path: Path) -> None:
    assert LEDGER_SCRIPT.exists(), LEDGER_SCRIPT
    env = os.environ.copy()
    env["GPBIOMETRICSPY_EXCLUSION_DIR"] = str(tmp_path)

    run = subprocess.run(
        [sys.executable, str(LEDGER_SCRIPT)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    assert lines, "QC/exclusion ledger example produced no stdout."
    result = json.loads(lines[-1])
    assert result["tutorial"] == "qc-exclusion-decision-ledger", result
    assert result["status"] == "PASS", result
    assert result["automatic_exclusions_applied"] is False
    assert result["review_candidate_count"] >= 2
    assert result["artifact_count"] == 6

    required = {
        "qc-signal-activity.csv",
        "qc-time-reset-overview.csv",
        "qc-dropout-summary.csv",
        "exclusion-decision-ledger.csv",
        "denominator-audit.csv",
        "exclusion-manifest.json",
    }
    assert required <= {path.name for path in tmp_path.iterdir()}

    ledger = pd.read_csv(tmp_path / "exclusion-decision-ledger.csv", keep_default_na=False)
    assert len(ledger) >= 2
    assert set(ledger["decision"]) == {"REVIEW"}
    assert set(ledger["downstream_effect"]) == {"not_applied"}
    assert (ledger["reason"] == "").all()
    assert {"GSR_US", "HR"} <= set(ledger["signal"])

    denominator = pd.read_csv(tmp_path / "denominator-audit.csv")
    assert set(denominator["excluded"]) == {0}
    assert (denominator["before"] == denominator["after"]).all()
    assert set(denominator["status"]) == {"NO_AUTOMATIC_EXCLUSIONS_APPLIED"}

    manifest = json.loads((tmp_path / "exclusion-manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow"] == "qc-exclusion-decision-ledger"
    assert manifest["status"] == "REVIEW"
    assert manifest["automatic_exclusions_applied"] is False
    assert manifest["excluded_rows"] == 0
    assert manifest["excluded_participants"] == 0
    assert manifest["decision_states"] == ["REVIEW"]


def test_exclusion_page_separates_qc_flags_from_decisions(
    page: Page, exclusion_docs_base_url: str
) -> None:
    page.goto(f"{exclusion_docs_base_url}/qc-exclusion-decision-ledger/")
    expect(page.locator("[data-qc-exclusion-ledger]")).to_be_visible()
    expect(page.locator("[data-exclusion-evidence-grid] > .gp-guide-card")).to_have_count(4)
    article = page.get_by_role("article")
    expect(article).to_contain_text("Candidate flag is not exclusion")
    expect(article).to_contain_text("The unit of exclusion matters")
    expect(article).to_contain_text("Denominator audit")
    expect(article).to_contain_text("REVIEW")
    expect(article).to_contain_text("Common failures")
    expect(article).to_contain_text("Evidence boundary")


def test_exclusion_page_routes_to_validation_and_reporting(
    page: Page, exclusion_docs_base_url: str
) -> None:
    page.goto(f"{exclusion_docs_base_url}/qc-exclusion-decision-ledger/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Validate a new dataset").first.click()
    expect(page).to_have_url(f"{exclusion_docs_base_url}/guides/validate-dataset/")

    page.goto(f"{exclusion_docs_base_url}/qc-exclusion-decision-ledger/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Reporting and reproducibility").first.click()
    expect(page).to_have_url(
        f"{exclusion_docs_base_url}/guides/reporting-reproducibility/"
    )
