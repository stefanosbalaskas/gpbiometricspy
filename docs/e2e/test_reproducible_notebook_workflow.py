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
NOTEBOOK_SCRIPT = ROOT / "examples" / "hands-on" / "reproducible-notebook-pattern.py"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def notebook_docs_base_url() -> str:
    site = Path("site").resolve()
    for rel in [
        "reproducible-notebook-workflow/index.html",
        "learning-paths/index.html",
        "research-faq/index.html",
        "guides/bring-your-own-export/index.html",
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


def test_notebook_guide_exposes_restartable_workflow(
    page: Page, notebook_docs_base_url: str
) -> None:
    page.goto(f"{notebook_docs_base_url}/reproducible-notebook-workflow/")
    stages = page.locator("[data-notebook-stages]")
    expect(stages).to_be_visible()
    expect(stages.locator(".gp-step")).to_have_count(7)
    expect(stages).to_contain_text("1 · Environment")
    expect(stages).to_contain_text("2 · Parameters")
    expect(stages).to_contain_text("4 · Functions")
    expect(stages).to_contain_text("6 · Manifest")
    expect(stages).to_contain_text("7 · Restart")


def test_notebook_guide_warns_against_hidden_state(
    page: Page, notebook_docs_base_url: str
) -> None:
    page.goto(f"{notebook_docs_base_url}/reproducible-notebook-workflow/")
    article = page.get_by_role("article")
    expect(article).to_contain_text("Avoid hidden state")
    expect(article).to_contain_text("Restart and run all is a minimum test")
    expect(article).to_contain_text("Keep private data out of notebook output cells")
    expect(article).to_contain_text("Reproducible execution makes the computational path inspectable")


def test_reproducible_notebook_script_writes_reviewable_artifacts(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR"] = str(tmp_path)
    run = subprocess.run(
        [sys.executable, str(NOTEBOOK_SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert '"status": "PASS"' in run.stdout

    expected = {
        "analysis_parameters.json",
        "software.json",
        "signal_activity_overview.csv",
        "signal_activity_by_group.csv",
        "time_reset_overview.csv",
        "time_reset_segments.csv",
        "notebook_manifest.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})

    manifest = json.loads((tmp_path / "notebook_manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow"] == "reproducible-notebook-pattern"
    assert manifest["synthetic_demo"] is True
    assert manifest["rows_loaded"] == manifest["rows_requested"] == 900
    assert "hidden notebook state" in manifest["execution_contract"]

    parameters = json.loads((tmp_path / "analysis_parameters.json").read_text(encoding="utf-8"))
    assert parameters["participant"] == "synthetic_kiosk_p001"
    assert parameters["signal_cols"] == ["GSR_US", "HR", "IBI", "LPMM"]


def test_notebook_guide_links_to_reporting_route(
    page: Page, notebook_docs_base_url: str
) -> None:
    page.goto(f"{notebook_docs_base_url}/reproducible-notebook-workflow/")
    page.get_by_role("article").get_by_role(
        "link", name="Reporting and reproducibility"
    ).last.click()
    expect(page).to_have_url(
        f"{notebook_docs_base_url}/guides/reporting-reproducibility/"
    )
