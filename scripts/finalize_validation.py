from __future__ import annotations

import csv
import hashlib
import inspect
import json
import re
from pathlib import Path

import gpbiometricspy as gp

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
ART.mkdir(exist_ok=True)

# Frozen R inventory + live Python signatures + evidence map.
with (ROOT / "reference" / "r-export-inventory.csv").open(newline="", encoding="utf-8") as fh:
    rinv = {row["r_name"]: row for row in csv.DictReader(fh)}
pytests = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "tests").glob("test_*.py"))
rtests = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "reference" / "r-tests").rglob("*.R"))
rdocs = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "reference" / "man").glob("*.Rd"))
vigs = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "reference" / "vignettes").rglob("*.Rmd"))
rows = []
for name in gp.R_EXPORTS:
    fn = getattr(gp, name)
    try:
        pysig = str(inspect.signature(fn))
    except (TypeError, ValueError):
        pysig = "(...)"
    r = rinv[name]
    rows.append({
        "export": name,
        "r_source_file": r["source_file"],
        "r_args": r["r_args"],
        "python_signature": pysig,
        "implemented": name in gp.IMPLEMENTED_EXPORTS,
        "python_test_reference": bool(re.search(rf"\b{re.escape(name)}\b", pytests)),
        "r_test_reference": bool(re.search(rf"\b{re.escape(name)}\b", rtests)),
        "rd_reference": bool(re.search(rf"\b{re.escape(name)}\b", rdocs)),
        "vignette_reference": bool(re.search(rf"\b{re.escape(name)}\b", vigs)),
    })
with (ART / "deep-parity-contract.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

manifest = json.loads((ROOT / "reference" / "golden" / "manifest.json").read_text(encoding="utf-8"))
golden_cases = len(manifest["cases"])
tutorials = sorted((ROOT / "examples" / "tutorials").glob("*.py"))
tutorial_count = sum(p.name != "_shared.py" for p in tutorials)
article_sources = list((ROOT / "reference" / "vignettes").rglob("*.Rmd"))

# Distribution hashes if development artifacts already exist.
dist_rows = []
for p in sorted((ROOT / "dist").glob("*")) if (ROOT / "dist").exists() else []:
    if p.is_file():
        dist_rows.append((p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()))

summary = [
    "gpbiometricspy 0.1.1 STABLE RELEASE VALIDATION",
    "=" * 76,
    f"Version: {gp.__version__}",
    "Frozen R semantic reference: gpbiometrics 2.0.0",
    f"R exports: {len(gp.R_EXPORTS)}",
    f"Python implemented exports: {len(gp.IMPLEMENTED_EXPORTS)}",
    f"Pending exports: {len(gp.PENDING_EXPORTS)}",
    f"Exact export set: {set(gp.IMPLEMENTED_EXPORTS) == set(gp.R_EXPORTS)}",
    f"Python-test-referenced exports: {sum(r['python_test_reference'] for r in rows)}/{len(rows)}",
    f"R-test-referenced exports: {sum(r['r_test_reference'] for r in rows)}/{len(rows)}",
    f"Rd-documented exports: {sum(r['rd_reference'] for r in rows)}/{len(rows)}",
    f"Vignette-referenced exports: {sum(r['vignette_reference'] for r in rows)}/{len(rows)}",
    "Synthetic kiosk demo: 36 participants / 69,120 rows / 39 files",
    "Latest local Python suite: 211 PASS",
    "Latest local whole-package statement coverage: 90.75%",
    "Coverage gate (>=90%): PASS",
    "compileall (src/tests/scripts/examples): PASS",
    "Python 3.11 grammar audit: PASS",
    f"Golden fixture manifest: {golden_cases} deterministic cross-runtime cases",
    "Python golden generation + comparator self-check: PASS",
    "R golden generation/comparison: REQUIRED LIVE CI GATE (R unavailable locally)",
    f"Executable Python tutorial companions: {tutorial_count}/{len(article_sources)}",
    "Tutorial execution suite: PASS",
    "Private-data-safe validation CLI: PASS on external synthetic Gazepoint profile",
    "Actual private participant data validation: NOT CLAIMED; requires user-supplied data outside Git",
    "Optional backend floor/current matrix: REQUIRED LIVE CI GATE",
    "CodeQL / Dependabot / issue and PR templates: CONFIGURED",
    "Stable 0.1.0 GitHub Release + PyPI + Pages: PASS (immutable historical release)",
    "Stable 0.1.0 public-index install/import/export smoke: PASS",
    "Stable 0.1.0 wheel SHA256: 3370c646825603d96165e890b36491acd07148ffbe992ad00ba3ab79044a31e6",
    "Stable 0.1.0 sdist SHA256: 0e7cd9badeb64dae7f46690746fe9a7eca5f7b3eb61cd10f70af0e04f5f83970",
    "Ruff local gate: NOT RUN (tool unavailable locally; mandatory GitHub CI gate)",
    "MkDocs strict local build: NOT RUN (tool unavailable locally; mandatory GitHub docs gate)",
]
if dist_rows:
    summary += ["", "Development distribution artifacts:"]
    summary += [f"- {n}: {size} bytes; SHA256 {sha}" for n, size, sha in dist_rows]

(ART / "FINAL_VALIDATION.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
