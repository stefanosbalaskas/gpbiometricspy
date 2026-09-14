from __future__ import annotations

import json
import re
from pathlib import Path

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
    "eda-scr.md",
    "ppg-hrv.md",
    "pupil-gaze.md",
    "multimodal.md",
    "quality-reporting.md",
    "interoperability.md",
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

    start = _text(DOCS / "start-here.md")
    assert "# Start here" in start
    assert 'href="parity/"' in start
    assert "validation-trust/parity-validation" not in start

    workflows = _text(DOCS / "workflows.md")
    assert "Recommended research pipeline" in workflows
    assert "Measurement-ready" in workflows
    assert "Analysis-ready" in workflows
    assert "Report-ready" in workflows

    mkdocs = _text(ROOT / "mkdocs.yml")
    for required in [
        "- Start here: start-here.md",
        "- Guides:",
        "- Python-native explanations:",
        "- navigation.instant.progress",
        "- content.code.annotate",
        "- stylesheets/experience.css",
        "- name: mermaid",
    ]:
        assert required in mkdocs, required

    # Preserve the frozen R-companion documentation boundary.
    top_level_articles = sorted((DOCS / "articles").glob("*.md"))
    frozen_companions = [p for p in top_level_articles if p.name != "index.md"]
    assert len(frozen_companions) == 26, len(frozen_companions)
    assert all("## Executable Python companion" in _text(p) for p in frozen_companions)

    print(
        "docs-site validation: PASS "
        f"({len(figures)} figures, {len(GUIDES)} guides, "
        f"{len(PYTHON_NATIVE_ARTICLES) - 1} Python-native explanation articles, "
        f"{len(frozen_companions)} frozen R companions)"
    )


if __name__ == "__main__":
    main()
