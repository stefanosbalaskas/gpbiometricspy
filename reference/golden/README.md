# R ↔ Python golden fixtures

This directory defines deterministic cross-runtime parity cases for `gpbiometrics 2.0.0` and `gpbiometricspy`.

The ordinary Python suite proves Python behavior and the exact 406-export contract. These fixtures add an **independent R runtime** layer for numerical families where direct tolerance comparison is meaningful.

Run locally when R is available:

```bash
python scripts/generate_python_golden.py --output artifacts/golden/python.json
Rscript reference/golden/generate_r_golden.R artifacts/golden/r.json
python scripts/compare_golden_fixtures.py artifacts/golden/r.json artifacts/golden/python.json
```

CI runs the same sequence on Ubuntu with R and Python. Non-finite values are normalized to JSON `null`. Numeric comparison uses case-specific or default tolerances recorded in `manifest.json`.
