from __future__ import annotations

import inspect
import re
from pathlib import Path

import gpbiometricspy as gp

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ART = DOCS / "articles"
ART.mkdir(parents=True, exist_ok=True)

# API reference
rows = []
for name in gp.R_EXPORTS:
    fn = getattr(gp, name)
    try:
        sig = str(inspect.signature(fn))
    except (TypeError, ValueError):
        sig = "(...)"
    rows.append((name, sig))

api_lines = [
    "# Frozen 406-function API reference",
    "",
    "Every function below is a member of the frozen `gpbiometrics 2.0.0` export contract and is registered as implemented in `gpbiometricspy`.",
    "",
    "The signature shown is the live Python signature. For exact R source/signature provenance see `reference/r-export-inventory.csv`.",
    "",
]
for name, sig in rows:
    api_lines += [f"## `{name}`", "", f"```python\n{name}{sig}\n```", ""]
(DOCS / "api" / "reference.md").write_text("\n".join(api_lines), encoding="utf-8")

# Curated article companions
#
# These pages are intentionally maintained as rich, executable documentation.
# Earlier versions of this generator rewrote them from the frozen R sources on
# every docs build, which stripped executable Python companions and rendered
# figures just before MkDocs deployment.  The frozen R corpus is immutable, so
# the build-time responsibility here is validation, not regeneration.
exports = sorted(gp.R_EXPORTS, key=len, reverse=True)
article_rows = []
for src in sorted((ROOT / "reference" / "vignettes").rglob("*.Rmd")):
    text = src.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'^title:\s*["\\\']?(.*?)["\\\']?\s*$', text, re.M)
    title = m.group(1).strip('"\\\'') if m else src.stem.replace("-", " ").title()
    found = []
    for name in exports:
        if re.search(rf"(?<![A-Za-z0-9_.]){re.escape(name)}\s*\(", text):
            found.append(name)
    found = sorted(set(found))

    dest = ART / f"{src.stem}.md"
    tutorial = ROOT / "examples" / "tutorials" / f"{src.stem}.py"
    if not dest.exists():
        raise RuntimeError(f"Missing curated article companion: {dest.relative_to(ROOT)}")
    if not tutorial.exists():
        raise RuntimeError(f"Missing executable article companion: {tutorial.relative_to(ROOT)}")

    curated = dest.read_text(encoding="utf-8")
    if "## Executable Python companion" not in curated:
        raise RuntimeError(
            f"Curated article lost executable-companion section: {dest.relative_to(ROOT)}"
        )

    article_rows.append(
        (
            title,
            dest.name,
            src.relative_to(ROOT / "reference" / "vignettes").as_posix(),
            len(found),
        )
    )

index_path = ART / "index.md"
if not index_path.exists():
    raise RuntimeError("Missing curated article index: docs/articles/index.md")
index_text = index_path.read_text(encoding="utf-8")
if "# Articles and tutorials" not in index_text:
    raise RuntimeError("Curated article index heading is missing or stale.")
if f"All **{len(article_rows)}** frozen R vignette/article sources" not in index_text:
    raise RuntimeError("Curated article index does not report the frozen article count.")

missing_links = [fn for _, fn, _, _ in article_rows if f"({fn})" not in index_text]
if missing_links:
    raise RuntimeError(f"Curated article index is missing links: {missing_links}")

print(f"API rows: {len(rows)}")
print(f"Curated article companions audited: {len(article_rows)}")
