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

# Article migration companions
exports = sorted(gp.R_EXPORTS, key=len, reverse=True)
article_rows = []
for src in sorted((ROOT / "reference" / "vignettes").rglob("*.Rmd")):
    text = src.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', text, re.M)
    title = m.group(1).strip('"\'') if m else src.stem.replace("-", " ").title()
    found = []
    for name in exports:
        if re.search(rf"(?<![A-Za-z0-9_.]){re.escape(name)}\s*\(", text):
            found.append(name)
    found = sorted(set(found))
    dest = ART / f"{src.stem}.md"
    rel = src.relative_to(ROOT)
    lines = [
        f"# {title}",
        "",
        f"**Frozen R source:** `{rel.as_posix()}`",
        "",
        "This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.",
        "",
        "## Python API crosswalk",
        "",
    ]
    if found:
        lines += ["The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:", ""]
        for name in found:
            lines.append(f"- `gp.{name}(...)`")
        lines += ["", "```python", "import gpbiometricspy as gp", "", f"# Example entry point from this workflow", f"# result = gp.{found[0]}(...)" if found else "", "```", ""]
    else:
        lines += ["No direct exported function calls were detected mechanically in this article. Use the frozen R source for narrative/design context and the main API reference for the corresponding Python functions.", ""]
    lines += [
        "## Interpretation",
        "",
        "Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    article_rows.append((title, dest.name, src.relative_to(ROOT / "reference" / "vignettes").as_posix(), len(found)))

idx = ["# Article migration catalog", "", f"All **{len(article_rows)}** frozen R vignette/article sources have a Python migration companion.", "", "| Article | Python companion | Frozen R source | Referenced exports |", "|---|---|---|---:|"]
for title, fn, src, n in article_rows:
    idx.append(f"| {title} | [{fn[:-3]}]({fn}) | `{src}` | {n} |")
(ART / "index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")

print(f"API rows: {len(rows)}")
print(f"Article companions: {len(article_rows)}")
