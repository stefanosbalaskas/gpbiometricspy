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
SCAFFOLD_SCRIPT = ROOT / "examples" / "hands-on" / "create-research-project-scaffold.py"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def scaffold_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "guides" / "research-project-scaffold" / "index.html").exists(), site
    assert (site / "guides" / "bring-your-own-export" / "index.html").exists(), site
    assert (site / "guides" / "reporting-reproducibility" / "index.html").exists(), site

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


def test_research_project_scaffold_script_runs(tmp_path: Path) -> None:
    assert SCAFFOLD_SCRIPT.exists(), SCAFFOLD_SCRIPT
    env = os.environ.copy()
    env["GPBIOMETRICSPY_PROJECT_DIR"] = str(tmp_path)

    run = subprocess.run(
        [sys.executable, str(SCAFFOLD_SCRIPT)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    assert lines, "Project scaffold produced no stdout."
    result = json.loads(lines[-1])
    assert result["tutorial"] == "research-project-scaffold", result
    assert result["status"] == "PASS", result
    assert result["directory_count"] == 11, result

    required_dirs = {
        "raw",
        "metadata",
        "mappings",
        "qc",
        "events",
        "derived",
        "models",
        "figures",
        "reports",
        "manifests",
        "logs",
    }
    assert required_dirs <= {p.name for p in tmp_path.iterdir() if p.is_dir()}
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "raw" / "README.md").exists()
    assert (tmp_path / "metadata" / "analysis-config.json").exists()
    assert (tmp_path / "mappings" / "column-mapping-template.csv").exists()
    assert (tmp_path / "manifests" / "project-scaffold.json").exists()

    config = json.loads(
        (tmp_path / "metadata" / "analysis-config.json").read_text(encoding="utf-8")
    )
    assert config["time_column"] is None
    assert config["sampling_rate_hz"] is None

    manifest = json.loads(
        (tmp_path / "manifests" / "project-scaffold.json").read_text(encoding="utf-8")
    )
    assert manifest["workflow"] == "research-project-scaffold"
    assert manifest["synthetic_or_template_only"] is True
    assert set(manifest["directories"]) == required_dirs


def test_scaffold_guide_exposes_structure_and_boundaries(
    page: Page, scaffold_docs_base_url: str
) -> None:
    page.goto(f"{scaffold_docs_base_url}/guides/research-project-scaffold/")
    expect(page.locator("[data-research-project-scaffold]")).to_be_visible()
    expect(page.locator("[data-project-scaffold-stages] > .gp-guide-card")).to_have_count(6)
    article = page.get_by_role("article")
    expect(article).to_contain_text("Private-data boundary")
    expect(article).to_contain_text("Common project-structure failures")
    expect(article).to_contain_text("analysis-config.json")
    expect(article).to_contain_text("project-scaffold.json")
    expect(article).to_contain_text("What the scaffold does not solve")


def test_scaffold_routes_into_adaptation_and_reporting(
    page: Page, scaffold_docs_base_url: str
) -> None:
    page.goto(f"{scaffold_docs_base_url}/guides/research-project-scaffold/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Bring your own export safely").click()
    expect(page).to_have_url(
        f"{scaffold_docs_base_url}/guides/bring-your-own-export/"
    )

    page.goto(f"{scaffold_docs_base_url}/guides/research-project-scaffold/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Reporting and reproducibility").click()
    expect(page).to_have_url(
        f"{scaffold_docs_base_url}/guides/reporting-reproducibility/"
    )
