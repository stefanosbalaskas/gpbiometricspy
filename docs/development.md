# Development and release gates

Run the core validation locally:

```bash
python -m compileall -q src tests
python scripts/audit_r_contract.py
python -m pytest -q --cov=src/gpbiometricspy --cov-report=term-missing --cov-fail-under=90
```

Build distributions with:

```bash
python -m build
python -m twine check dist/*
```

The source distribution intentionally retains the frozen R implementation, documentation, tests and vignettes for auditability. The wheel contains only the Python runtime package and synthetic demo data.
