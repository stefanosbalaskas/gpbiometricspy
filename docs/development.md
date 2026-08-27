# Development and validation gates

Run the core validation locally:

```bash
python -m compileall -q src tests scripts examples
python scripts/audit_r_contract.py
python -m pytest -q --cov=src/gpbiometricspy --cov-report=term-missing --cov-fail-under=90
```

Generate the Python side of the cross-runtime golden fixtures with:

```bash
python scripts/generate_python_golden.py --output artifacts/golden/python.json
```

When R is available, run the complete pair:

```bash
Rscript reference/golden/generate_r_golden.R artifacts/golden/r.json
python scripts/compare_golden_fixtures.py artifacts/golden/r.json artifacts/golden/python.json
```

Optional backend checks are implemented in `.github/workflows/interoperability.yml` and `scripts/interop_smoke.py`.

Private real-data validation must use data/output paths outside the repository:

```bash
python scripts/validate_real_data.py /secure/path/gazepoint_exports --output /secure/path/validation
```

Build distributions with:

```bash
python -m build
python -m twine check dist/*
```

The source distribution intentionally retains the frozen R implementation, documentation, tests and vignettes for auditability. The wheel contains only the Python runtime package and synthetic demo data.
