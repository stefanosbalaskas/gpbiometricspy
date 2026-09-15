# Development and validation gates

<div class="gp-page-intro">
Use the same evidence layers locally that the repository enforces in CI. A successful test run is only one gate: export parity, statement/branch accounting, interoperability, generated documentation and release provenance are validated separately.
</div>

## Core source validation

Run the core source checks locally:

```bash
python -m compileall -q src tests scripts examples
ruff check src tests scripts examples
python scripts/audit_r_contract.py
python -m pytest -q --cov=src/gpbiometricspy --cov-report=term-missing --cov-fail-under=100
```

The frozen export audit must report **406 implemented, 0 pending**. The ordinary test workflow enforces **100% statement coverage**; branch coverage is governed separately so raw decision-path coverage and the reviewed structural-debt ledger remain visible rather than being collapsed into one rounded percentage.

## Cross-runtime golden fixtures

Generate the Python side with:

```bash
python scripts/generate_python_golden.py --output artifacts/golden/python.json
```

When R is available, run the complete independent pair:

```bash
Rscript reference/golden/generate_r_golden.R artifacts/golden/r.json
python scripts/compare_golden_fixtures.py artifacts/golden/r.json artifacts/golden/python.json
```

The CI `deep-parity` workflow performs the corresponding R ↔ Python golden-fixture comparison on the checked-out commit.

## Optional backends

Optional backend checks are implemented in `.github/workflows/interoperability.yml` and `scripts/interop_smoke.py`. They exercise real floor/current dependency combinations for HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf instead of validating only import-failure paths.

## Private real-data validation

Private real-data validation must use data/output paths outside the repository:

```bash
python scripts/validate_real_data.py /secure/path/gazepoint_exports --output /secure/path/validation
```

Do not copy participant recordings into the repository merely to reproduce this gate. The public record should retain the validation result and software evidence, not private study data.

## Build distributions

```bash
python -m build
python -m twine check dist/*
```

The source distribution intentionally retains the frozen R implementation, documentation, tests and vignettes for auditability. The wheel contains only the Python runtime package and synthetic demo data.

## Documentation and generated figures

The visual documentation is generated from package code rather than maintained as hand-edited screenshots.

```bash
PYTHONPATH=src python scripts/generate_reference_docs.py
PYTHONPATH=src python scripts/generate_docs_gallery.py
python scripts/validate_docs_site.py
mkdocs build --strict
```

The gallery generator writes `docs/assets/generated/manifest.json` plus **17 deterministic PNG figures** used by the homepage, domain examples, plot gallery and visual-heavy articles. Documentation CI regenerates the gallery, validates the site contract, and runs a strict MkDocs build before Pages deployment from `main`.

Executable article companions can also export any Matplotlib figures they produce:

```bash
GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR=artifacts/tutorial-figures \
  python examples/tutorials/eda-scr-visual-diagnostics.py
```

On PowerShell:

```powershell
$env:GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR = "artifacts/tutorial-figures"
python examples/tutorials/eda-scr-visual-diagnostics.py
```

## Before opening or merging a scientific PR

<div class="gp-steps">
<div class="gp-step"><strong>Freeze the candidate.</strong> Normalize the branch to the intended exact head and record its tree and sole parent.</div>
<div class="gp-step"><strong>Qualify the exact head.</strong> Require every applicable workflow family to finish on that SHA; do not substitute a tree-equivalent stale generation.</div>
<div class="gp-step"><strong>Audit the merge.</strong> Verify the merge tree, parent topology and GitHub signature against the qualified candidate.</div>
<div class="gp-step"><strong>Re-run on exact main.</strong> Treat post-merge push workflows as a fresh evidence generation rather than inheriting the PR result.</div>
<div class="gp-step"><strong>Record the checkpoint.</strong> Only after exact-main evidence is terminal green should documentation call the new scientific SHA certified.</div>
</div>

For the rationale behind these independent gates, see [Deep validation and interoperability](deep-validation.md).