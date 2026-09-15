from __future__ import annotations

import json
import re
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

RAW_ROUTE_PAGES = {
    "index.md",
    "start-here.md",
    "getting-started.md",
    "workflows.md",
    "plot-gallery.md",
    "deep-validation.md",
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
    assert 'href="../parity/"' in start
    assert "validation-trust/parity-validation" not in start

    workflows = _text(DOCS / "workflows.md")
    assert "Recommended research pipeline" in workflows
    assert "Measurement-ready" in workflows
    assert "Analysis-ready" in workflows
    assert "Report-ready" in workflows

    for name in RAW_ROUTE_PAGES:
        route_page = DOCS / name
        _assert_html_images_have_alt(route_page)
        _assert_raw_internal_targets(route_page)

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
        f"{len(frozen_companions)} frozen R companions, "
        f"{len(RAW_ROUTE_PAGES)} raw-route pages)"
    )


if __name__ == "__main__":
    main()