from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST = DOCS / "assets" / "generated" / "manifest.json"

EXPECTED_FIGURES = {
    "aoi-biometrics",
    "biometric-quality",
    "biometric-signals",
    "cluster-null-distribution",
    "cluster-permutation",
    "design-coverage",
    "eda-decomposition",
    "eda-gram",
    "hrv-tachogram",
    "missingness",
    "multimodal-timeline",
    "ppg-peak-detection",
    "ppg-poincare",
    "pupil-gaze-overview",
    "saccade-main-sequence",
    "scr-events",
    "signal-quality",
}

GUIDES = {
    "index.md",
    "hands-on-eda-research.md",
    "first-analysis.md",
    "validate-dataset.md",
    "timebase-alignment.md",
    "reporting-reproducibility.md",
    "model-selection.md",
}

PYTHON_NATIVE_ARTICLES = {
    "index.md",
    "measurement-before-modelling.md",
    "model-selection-location-scale.md",
    "reproducible-multimodal-study.md",
    "research-pipeline-blueprint.md",
}

EXAMPLES = {
    "end-to-end-eda.md",
    "eda-scr.md",
    "ppg-hrv.md",
    "pupil-gaze.md",
    "multimodal.md",
    "quality-reporting.md",
    "interoperability.md",
}

RAW_ROUTE_PAGES = {
    "index.md",
    "start-here.md",
    "getting-started.md",
    "workflows.md",
    "plot-gallery.md",
    "deep-validation.md",
}

SEARCH_META = {
    "guides/.meta.yml": "boost: 1.2",
    "methods/.meta.yml": "boost: 1.1",
}

HANDS_ON_WORKFLOW = DOCS / "workflows" / "end-to-end-eda-research.md"
HANDS_ON_SCRIPT = ROOT / "examples" / "tutorials" / "end-to-end-eda-research.py"
HANDS_ON_OUTPUTS = {
    "eda_decomposition.csv",
    "scr_events.csv",
    "scr_group_summary.csv",
    "analysis_checklist_overview.csv",
    "methods_text.txt",
    "end-to-end-eda-research-01.png",
    "end-to-end-eda-research-02.png",
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_html_images_have_alt(path: Path) -> None:
    text = _text(path)
    for match in re.finditer(r"<img\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        assert re.search(r"\balt\s*=\s*['\"][^'\"]+['\"]", tag, flags=re.IGNORECASE), (
            f"HTML image without non-empty alt text in {path.relative_to(ROOT)}: {tag}"
        )


def _output_dir_for_source(path: Path) -> str:
    rel = path.relative_to(DOCS)
    if rel.name == "index.md":
        parent = rel.parent.as_posix()
        return "/" if parent == "." else f"/{parent.strip('/')}/"
    return f"/{rel.with_suffix('').as_posix().strip('/')}/"


def _raw_target_exists(url_path: str) -> bool:
    rel = url_path.lstrip("/")
    if not rel:
        return (DOCS / "index.md").exists()

    raw = DOCS / rel
    candidates = [raw]
    if url_path.endswith("/"):
        stripped = rel.rstrip("/")
        candidates.extend(
            [
                DOCS / f"{stripped}.md",
                DOCS / stripped / "index.md",
            ]
        )
    elif not raw.suffix:
        candidates.extend([DOCS / f"{rel}.md", DOCS / rel / "index.md"])

    return any(candidate.exists() for candidate in candidates)


def _assert_raw_internal_targets(path: Path) -> None:
    text = _text(path)
    base = f"https://docs.invalid{_output_dir_for_source(path)}"
    pattern = re.compile(
        r"<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith("#"):
            continue
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        resolved = urlsplit(urljoin(base, target)).path
        assert _raw_target_exists(resolved), (
            f"Broken raw HTML target in {path.relative_to(ROOT)}: "
            f"{target!r} resolves to {resolved!r}"
        )


def _validate_hands_on_example() -> None:
    assert HANDS_ON_SCRIPT.exists(), HANDS_ON_SCRIPT
    source = _text(HANDS_ON_SCRIPT)
    for required in [
        "audit_gazepoint_gsr_units",
        "audit_gazepoint_gsr_quality",
        "decompose_gazepoint_eda",
        "detect_gazepoint_scr_events",
        "plot_gazepoint_eda_decomposition",
        "plot_gazepoint_scr_events",
        "create_gazepoint_biometrics_checklist",
        "create_gazepoint_biometrics_methods_text",
    ]:
        assert required in source, required

    with tempfile.TemporaryDirectory(prefix="gpbiometricspy-hands-on-") as tmp:
        env = os.environ.copy()
        env["GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR"] = tmp
        run = subprocess.run(
            [sys.executable, str(HANDS_ON_SCRIPT)],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        lines = [line for line in run.stdout.splitlines() if line.strip()]
        assert lines, "Hands-on example produced no stdout."
        result = json.loads(lines[-1])
        assert result["tutorial"] == "end-to-end-eda-research", result
        assert result["status"] == "PASS", result
        produced = {path.name for path in Path(tmp).iterdir()}
        assert HANDS_ON_OUTPUTS <= produced, (sorted(HANDS_ON_OUTPUTS), sorted(produced))


def main() -> None:
    assert MANIFEST.exists(), MANIFEST
    manifest = json.loads(_text(MANIFEST))
    figures = manifest.get("figures", [])
    slugs = {entry["slug"] for entry in figures}
    assert slugs == EXPECTED_FIGURES, (sorted(slugs), sorted(EXPECTED_FIGURES))
    assert len(figures) == 17

    generated = DOCS / "assets" / "generated"
    for entry in figures:
        filename = entry["file"]
        assert filename == f"{entry['slug']}.png", entry
        assert (generated / filename).exists(), filename

    gallery = DOCS / "plot-gallery.md"
    gallery_text = _text(gallery)
    assert "Stable 0.1.5 documentation." not in gallery_text
    assert "Current development documentation." in gallery_text
    for entry in figures:
        assert f"assets/generated/{entry['file']}" in gallery_text, entry["file"]
    _assert_html_images_have_alt(gallery)

    guides_dir = DOCS / "guides"
    assert {p.name for p in guides_dir.glob("*.md")} == GUIDES
    for path in guides_dir.glob("*.md"):
        assert path.stat().st_size > 500, path
        _assert_html_images_have_alt(path)

    native_dir = DOCS / "articles" / "python-native"
    assert {p.name for p in native_dir.glob("*.md")} == PYTHON_NATIVE_ARTICLES
    for path in native_dir.glob("*.md"):
        text = _text(path)
        assert len(text) > 700, path
        if path.name != "index.md":
            assert "Python-native explanation article" in text, path
        _assert_html_images_have_alt(path)

    examples_dir = DOCS / "examples"
    for name in EXAMPLES:
        path = examples_dir / name
        text = _text(path)
        assert "gpbiometricspy" in text, path
        assert len(text) > 1500, path
        _assert_html_images_have_alt(path)
    assert "Scientific boundary" in _text(examples_dir / "eda-scr.md")
    assert "Scientific boundary" in _text(examples_dir / "ppg-hrv.md")
    assert "Scientific boundary" in _text(examples_dir / "pupil-gaze.md")
    assert "Scientific boundary" in _text(examples_dir / "multimodal.md")
    assert "Scientific boundary" in _text(examples_dir / "quality-reporting.md")
    assert "What not to infer" in _text(examples_dir / "end-to-end-eda.md")

    assert HANDS_ON_WORKFLOW.exists(), HANDS_ON_WORKFLOW
    workflow_text = _text(HANDS_ON_WORKFLOW)
    assert "Completion criteria" in workflow_text
    assert "GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR" in workflow_text
    assert "Scientific boundary" not in workflow_text or "gp-science-boundary" in workflow_text
    _assert_html_images_have_alt(HANDS_ON_WORKFLOW)

    hands_on_guide = DOCS / "guides" / "hands-on-eda-research.md"
    hands_on_guide_text = _text(hands_on_guide)
    assert "Move from demonstration data to your own file" in hands_on_guide_text
    assert "Common mistakes" in hands_on_guide_text
    assert "GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR" in hands_on_guide_text

    start = _text(DOCS / "start-here.md")
    assert "# Start here" in start
    assert 'href="../parity/"' in start
    assert "validation-trust/parity-validation" not in start
    assert "boost: 1.5" in start
    assert "description:" in start

    workflows = _text(DOCS / "workflows.md")
    assert "Recommended research pipeline" in workflows
    assert "Measurement-ready" in workflows
    assert "Analysis-ready" in workflows
    assert "Report-ready" in workflows
    assert "end-to-end EDA research workflow" in workflows
    assert "boost: 1.4" in workflows
    assert "description:" in workflows

    recovery = DOCS / "404.md"
    recovery_text = _text(recovery)
    assert "# That page is not here" in recovery_text
    assert "search:" in recovery_text and "exclude: true" in recovery_text
    assert "<kbd>/</kbd>" in recovery_text
    for destination in ["start-here/", "workflows/", "methods/", "api/", "plot-gallery/"]:
        assert f"https://stefanosbalaskas.github.io/gpbiometricspy/{destination}" in recovery_text
    _assert_html_images_have_alt(recovery)

    for rel, expected in SEARCH_META.items():
        metadata = DOCS / rel
        assert metadata.exists(), metadata
        metadata_text = _text(metadata)
        assert "search:" in metadata_text
        assert expected in metadata_text

    for name in RAW_ROUTE_PAGES:
        route_page = DOCS / name
        _assert_html_images_have_alt(route_page)
        _assert_raw_internal_targets(route_page)

    mkdocs = _text(ROOT / "mkdocs.yml")
    for required in [
        "edit_uri: edit/main/docs/",
        "- Start here: start-here.md",
        "- Hands-on end-to-end EDA: workflows/end-to-end-eda-research.md",
        "- Hands-on EDA research guide: guides/hands-on-eda-research.md",
        "- End-to-end runnable EDA: examples/end-to-end-eda.md",
        "- Guides:",
        "- Python-native explanations:",
        "- navigation.instant.prefetch",
        "- navigation.instant.progress",
        "- navigation.path",
        "- search.share",
        "- content.action.view",
        "- search\n  - meta\n  - privacy",
        "https://orcid.org/0000-0003-2444-9796",
        "- content.code.annotate",
        "- stylesheets/experience.css",
        "- name: mermaid",
    ]:
        assert required in mkdocs, required

    _validate_hands_on_example()

    # Preserve the frozen R-companion documentation boundary.
    top_level_articles = sorted((DOCS / "articles").glob("*.md"))
    frozen_companions = [p for p in top_level_articles if p.name != "index.md"]
    assert len(frozen_companions) == 26, len(frozen_companions)
    assert all("## Executable Python companion" in _text(p) for p in frozen_companions)

    print(
        "docs-site validation: PASS "
        f"({len(figures)} figures, {len(GUIDES)} guides, "
        f"{len(EXAMPLES)} focused examples, 1 executable hands-on workflow, "
        f"{len(PYTHON_NATIVE_ARTICLES) - 1} Python-native explanation articles, "
        f"{len(frozen_companions)} frozen R companions, "
        f"{len(RAW_ROUTE_PAGES)} raw-route pages, "
        f"{len(SEARCH_META)} search-meta scopes, recovery 404)"
    )


if __name__ == "__main__":
    main()
