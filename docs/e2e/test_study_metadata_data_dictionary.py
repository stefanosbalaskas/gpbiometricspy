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
DICTIONARY_SCRIPT = (
    ROOT / "examples" / "hands-on" / "create-study-metadata-data-dictionary.py"
)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def dictionary_docs_base_url() -> str:
    site = Path("site").resolve()
    assert (site / "guides" / "study-metadata-data-dictionary" / "index.html").exists(), site
    assert (site / "guides" / "research-project-scaffold" / "index.html").exists(), site
    assert (site / "guides" / "bring-your-own-export" / "index.html").exists(), site
    assert (site / "guides" / "validate-dataset" / "index.html").exists(), site

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


def test_study_dictionary_script_runs_without_inventing_semantics(tmp_path: Path) -> None:
    assert DICTIONARY_SCRIPT.exists(), DICTIONARY_SCRIPT
    env = os.environ.copy()
    env["GPBIOMETRICSPY_DICTIONARY_DIR"] = str(tmp_path)

    run = subprocess.run(
        [sys.executable, str(DICTIONARY_SCRIPT)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    assert lines, "Study dictionary example produced no stdout."
    result = json.loads(lines[-1])
    assert result["tutorial"] == "study-metadata-data-dictionary", result
    assert result["status"] == "PASS", result
    assert result["artifact_count"] == 4, result

    required = {
        "study-metadata.json",
        "variable-dictionary.csv",
        "event-dictionary.csv",
        "dictionary-manifest.json",
    }
    assert required <= {path.name for path in tmp_path.iterdir()}

    metadata = json.loads((tmp_path / "study-metadata.json").read_text(encoding="utf-8"))
    assert metadata["review_status"] == "REVIEW"
    assert metadata["declared_time_unit"] is None
    assert metadata["clock_owner"] is None
    assert metadata["configured_sampling_rate_hz"] is None

    variables = pd.read_csv(tmp_path / "variable-dictionary.csv", keep_default_na=False)
    assert len(variables) > 0
    assert set(
        [
            "source_column",
            "dtype",
            "missing_fraction",
            "declared_role",
            "declared_unit",
            "clock_owner",
            "derivation",
            "review_status",
        ]
    ) <= set(variables.columns)
    assert set(variables["review_status"]) == {"REVIEW"}
    assert (variables["declared_role"] == "").all()
    assert (variables["declared_unit"] == "").all()
    assert (variables["clock_owner"] == "").all()

    events = pd.read_csv(tmp_path / "event-dictionary.csv", keep_default_na=False)
    assert set(events["review_status"]) == {"REVIEW"}
    assert (events["event_label"] == "").all()
    assert (events["clock_owner"] == "").all()

    manifest = json.loads(
        (tmp_path / "dictionary-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["workflow"] == "study-metadata-data-dictionary"
    assert manifest["status"] == "REVIEW"
    assert manifest["synthetic_or_template_only"] is True
    assert manifest["scientific_declarations_autofilled"] is False
    assert set(manifest["artifacts"]) == {
        "study-metadata.json",
        "variable-dictionary.csv",
        "event-dictionary.csv",
    }


def test_dictionary_guide_exposes_contract_and_boundaries(
    page: Page, dictionary_docs_base_url: str
) -> None:
    page.goto(f"{dictionary_docs_base_url}/guides/study-metadata-data-dictionary/")
    expect(page.locator("[data-study-metadata-dictionary]")).to_be_visible()
    expect(page.locator("[data-dictionary-evidence-grid] > .gp-guide-card")).to_have_count(6)
    article = page.get_by_role("article")
    expect(article).to_contain_text("Observed is not declared")
    expect(article).to_contain_text("HRV may be a")
    expect(article).to_contain_text("Acceptance conditions before analysis")
    expect(article).to_contain_text("Common dictionary failures")
    expect(article).to_contain_text("dictionary-manifest.json")
    expect(article).to_contain_text("Evidence boundary")


def test_dictionary_guide_routes_across_research_onboarding(
    page: Page, dictionary_docs_base_url: str
) -> None:
    page.goto(f"{dictionary_docs_base_url}/guides/study-metadata-data-dictionary/")
    article = page.get_by_role("article")

    article.get_by_role("link", name="Research project scaffold").first.click()
    expect(page).to_have_url(
        f"{dictionary_docs_base_url}/guides/research-project-scaffold/"
    )

    page.goto(f"{dictionary_docs_base_url}/guides/study-metadata-data-dictionary/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Bring your own export safely").first.click()
    expect(page).to_have_url(f"{dictionary_docs_base_url}/guides/bring-your-own-export/")

    page.goto(f"{dictionary_docs_base_url}/guides/study-metadata-data-dictionary/")
    article = page.get_by_role("article")
    article.get_by_role("link", name="Validate a new dataset").first.click()
    expect(page).to_have_url(f"{dictionary_docs_base_url}/guides/validate-dataset/")
