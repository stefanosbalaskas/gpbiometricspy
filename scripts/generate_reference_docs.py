from __future__ import annotations

import inspect
import re
from pathlib import Path

import gpbiometricspy as gp

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
API = DOCS / "api"
ART = DOCS / "articles"
API.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)

DOMAINS = {
    "eda-scr": {
        "title": "EDA / GSR / SCR",
        "summary": "Electrodermal preprocessing, artifacts, decomposition, response detection, event windows, and EDA-oriented toolbox bridges.",
        "workflow": "../examples/eda-scr/",
        "articles": [
            ("EDA, GSR, and SCR workflow", "../articles/eda-scr-workflow.md"),
            ("EDA and SCR visual diagnostics", "../articles/eda-scr-visual-diagnostics.md"),
            ("External toolbox bridges", "../articles/toolbox-bridges-workflow.md"),
        ],
        "tokens": (
            "eda", "gsr", "scr", "skin_potential", "susceptance", "cvxeda",
            "ledalab", "pspm", "kleckner",
        ),
    },
    "ppg-hrv": {
        "title": "PPG / HR / IBI / HRV / respiration",
        "summary": "Pulse processing, beat and interval cleaning, time/frequency/nonlinear HRV, respiration, and cardiac toolbox-compatible workflows.",
        "workflow": "../examples/ppg-hrv/",
        "articles": [
            ("PPG, IBI, HRV, and respiration", "../articles/ppg-hrv-workflow.md"),
            ("PPG and HRV visual diagnostics", "../articles/ppg-hrv-visual-diagnostics.md"),
            ("Toolbox crosscheck visuals", "../articles/toolbox-crosscheck-visuals.md"),
        ],
        "tokens": (
            "ppg", "hrv", "ibi", "rri", "heartpy", "pyhrv", "rhrv", "rsa",
            "respiration", "breathing", "cardiorespiratory", "pulse", "beat",
            "hr_", "_hr", "pdr",
        ),
    },
    "pupil-gaze-aoi": {
        "title": "Pupil / gaze / fixation / AOI",
        "summary": "Pupil cleaning, blink handling, gaze validation, fixation/saccade processing, AOI assignment, scanpaths, and eye-tracking ecosystem bridges.",
        "workflow": "../examples/pupil-gaze/",
        "articles": [
            ("Pupil and gaze QC", "../articles/pupil-qc-workflow.md"),
            ("Eye-tracking ecosystem bridges", "../articles/eye-tracking-ecosystem-bridges.md"),
            ("Event alignment and AOI-linked biometrics", "../articles/event-alignment-aoi-workflow.md"),
        ],
        "tokens": (
            "pupil", "gaze", "aoi", "fixation", "saccade", "scanpath",
            "eyetrackingr", "gazer", "pupillometryr", "_eye", "eye_",
        ),
    },
    "alignment-multimodal": {
        "title": "Events / alignment / multimodal",
        "summary": "TTL extraction, event matching, cross-stream synchronization, shared timebases, multimodal windows, and trial-level alignment.",
        "workflow": "../examples/multimodal/",
        "articles": [
            ("Event alignment and AOI-linked biometrics", "../articles/event-alignment-aoi-workflow.md"),
            ("Multimodal event dashboard", "../articles/multimodal-event-dashboard.md"),
            ("Cluster-permutation workflow", "../articles/cluster-permutation.md"),
        ],
        "tokens": (
            "ttl", "event", "align", "sync", "multimodal", "timebase",
            "signal_lag", "sync_drift", "trial_regressor", "chunk_",
        ),
    },
    "qc-reporting": {
        "title": "QC / validation / reporting / governance",
        "summary": "Signal-quality audits, missingness and dropout checks, exclusions, reproducibility, preregistration, audit trails, dashboards, and reports.",
        "workflow": "../examples/quality-reporting/",
        "articles": [
            ("Quality-control workflow", "../articles/qc-workflow.md"),
            ("Reporting and reproducibility", "../articles/reporting-reproducibility-workflow.md"),
            ("Visual QC dashboard", "../articles/visual-qc-dashboard-workflow.md"),
        ],
        "tokens": (
            "audit", "quality", "missing", "dropout", "nonwear", "artifact",
            "validate", "report", "reproducibility", "preregistration", "decision",
            "readiness", "check_", "check", "exclusion", "pipeline", "release",
            "profile", "privacy", "methods_text", "feature_inventory",
        ),
    },
    "statistics-design": {
        "title": "Statistics / design / simulation",
        "summary": "Cluster permutation, bootstrap comparisons, model-ready data, sensitivity analyses, simulations, preprocessing transforms, and design diagnostics.",
        "workflow": "../workflows/",
        "articles": [
            ("Cluster-permutation workflow", "../articles/cluster-permutation.md"),
            ("Design audit workflow", "../articles/design-audit-workflow.md"),
            ("Synthetic data showcase", "../articles/synthetic-data-showcase.md"),
        ],
        "tokens": (
            "cluster", "bootstrap", "automated_statistics", "model_", "fit_",
            "simulate", "sensitivity", "multiverse", "experiment_design",
            "condition_balance", "standardise", "standardize", "baseline_correct",
            "detrend", "downsample", "upsample", "smooth_", "filter_",
            "normalize", "regress_", "changepoint", "point_process",
        ),
    },
    "interoperability": {
        "title": "Interoperability / exchange formats",
        "summary": "BIDS, MNE, EEG/LSL, XDF, external package manifests, cross-package handoffs, and export/import bridges.",
        "workflow": "../examples/interoperability/",
        "articles": [
            ("MNE, EEG, and LSL workflow", "../articles/mne-eeg-lsl-workflow.md"),
            ("BIDS export workflow", "../articles/bids-export-workflow.md"),
            ("Interoperability version testing", "../articles/interoperability-version-testing.md"),
        ],
        "tokens": (
            "bids", "mne", "lsl", "xdf", "interoperability", "permuco",
            "permutes", "gp3tools", "external", "sidecar",
        ),
    },
    "core-io": {
        "title": "Core I/O / schema / utilities",
        "summary": "Import, schema detection, column standardization, manifests, metadata, general utilities, and functions that span multiple scientific domains.",
        "workflow": "../getting-started/",
        "articles": [
            ("gpbiometrics workflow", "../articles/gpbiometrics-workflow.md"),
            ("Troubleshooting readiness", "../articles/troubleshooting-readiness.md"),
            ("Private real-data smoke testing", "../articles/private-real-data-smoke-testing.md"),
        ],
        "tokens": (),
    },
}

DOMAIN_ORDER = (
    "interoperability",
    "pupil-gaze-aoi",
    "eda-scr",
    "ppg-hrv",
    "alignment-multimodal",
    "qc-reporting",
    "statistics-design",
    "core-io",
)


def classify_api(name: str) -> str:
    lowered = name.lower()
    for slug in DOMAIN_ORDER:
        tokens = DOMAINS[slug]["tokens"]
        if tokens and any(token in lowered for token in tokens):
            return slug
    return "core-io"


# API reference and domain browser.
rows = []
for name in gp.R_EXPORTS:
    fn = getattr(gp, name)
    try:
        sig = str(inspect.signature(fn))
    except (TypeError, ValueError):
        sig = "(...)"
    rows.append((name, sig, classify_api(name)))

if len(rows) != 406:
    raise RuntimeError(f"Expected 406 frozen exports, found {len(rows)}")

api_lines = [
    "# Complete frozen 406-function API reference",
    "",
    "Every function below is a member of the frozen `gpbiometrics 2.0.0` export contract and is registered as implemented in `gpbiometricspy`.",
    "",
    "Prefer the [domain browser](index.md) when you know the scientific task but not the function name. This page remains the complete alphabetical contract.",
    "",
    "The signature shown is the live Python signature. For exact R source/signature provenance see `reference/r-export-inventory.csv`.",
    "",
]
for name, sig, _ in rows:
    api_lines += [
        f'<a id="{name}"></a>',
        f"## `{name}`",
        "",
        f"```python\n{name}{sig}\n```",
        "",
    ]
(API / "reference.md").write_text("\n".join(api_lines), encoding="utf-8")

domain_rows = {slug: [] for slug in DOMAINS}
for name, sig, slug in rows:
    domain_rows[slug].append((name, sig))

api_index = [
    "# API by scientific domain",
    "",
    "The complete Python surface contains **406 implemented exports**. Use the domain cards when you know the research task, or filter the function finder when you know part of a function name.",
    "",
    '<div class="gp-api-toolbar">',
    '<label for="gp-api-filter"><strong>Find a function</strong></label>',
    '<input id="gp-api-filter" data-api-filter type="search" placeholder="Try: scr, hrv, pupil, ttl, bids, quality…" autocomplete="off">',
    '<span class="gp-api-result-count" data-api-result-count>406 functions</span>',
    "</div>",
    "",
    '<div class="gp-card-grid gp-api-domain-grid">',
]
for slug in DOMAIN_ORDER:
    meta = DOMAINS[slug]
    count = len(domain_rows[slug])
    api_index.extend(
        [
            f'<a class="gp-card gp-card-link gp-api-domain-card" href="{slug}/">',
            f'<span class="gp-domain-count">{count}</span>',
            f"<h3>{meta['title']}</h3>",
            f"<p>{meta['summary']}</p>",
            '<span class="gp-card-cta">Browse functions →</span>',
            "</a>",
        ]
    )
api_index += [
    "</div>",
    "",
    "## Function finder",
    "",
    '<div class="gp-api-table-wrap">',
    '<table class="gp-api-table">',
    "<thead><tr><th>Function</th><th>Domain</th></tr></thead>",
    "<tbody>",
]
for name, _, slug in sorted(rows):
    title = DOMAINS[slug]["title"]
    api_index.append(
        f'<tr data-api-row><td><a href="{slug}/#{name}"><code>{name}</code></a></td><td>{title}</td></tr>'
    )
api_index += [
    "</tbody>",
    "</table>",
    "</div>",
    "",
    "No match? Use the site-wide search in the header, or open the [complete alphabetical reference](reference.md).",
    "",
]
(API / "index.md").write_text("\n".join(api_index), encoding="utf-8")

for slug in DOMAIN_ORDER:
    meta = DOMAINS[slug]
    funcs = domain_rows[slug]
    lines = [
        f"# {meta['title']}",
        "",
        meta["summary"],
        "",
        f"**{len(funcs)} functions** from the frozen 406-function contract are routed here by the documentation classifier.",
        "",
        '<div class="gp-api-domain-links">',
        f'<a class="md-button md-button--primary" href="{meta["workflow"]}">Open workflow</a>',
        '<a class="md-button" href="../">All API domains</a>',
        '<a class="md-button" href="../reference/">Complete reference</a>',
        "</div>",
        "",
        "## Recommended articles",
        "",
    ]
    for label, href in meta["articles"]:
        lines.append(f"- [{label}]({href})")
    lines += ["", "## Functions", ""]
    for name, sig in funcs:
        lines += [
            f'<a id="{name}"></a>',
            f"### `{name}`",
            "",
            f"```python\n{name}{sig}\n```",
            "",
        ]
    (API / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")

# Curated article companions
#
# These pages are intentionally maintained as rich, executable documentation.
# Earlier versions of this generator rewrote them from the frozen R sources on
# every docs build, which stripped executable Python companions and rendered
# figures just before MkDocs deployment. The frozen R corpus is immutable, so
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
print("API domain counts:")
for slug in DOMAIN_ORDER:
    print(f"  {slug}: {len(domain_rows[slug])}")
print(f"Curated article companions audited: {len(article_rows)}")
