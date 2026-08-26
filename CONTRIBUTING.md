# Contributing to gpbiometricspy

`gpbiometricspy` is parity-driven scientific software. Changes should preserve both Python usability and the frozen `gpbiometrics 2.0.0` semantic reference unless a later reference version is explicitly adopted.

## Development gates

Before submitting a change:

```bash
python -m compileall -q src tests
python scripts/audit_r_contract.py
python -m pytest -q --cov=src/gpbiometricspy --cov-report=term-missing --cov-fail-under=90
ruff check src tests scripts
```

When changing an R-parity function, cite the frozen source file/test that defines the behavior and add a regression test for defaults, validation, grouping, missingness and edge cases that matter scientifically.

Do not weaken physiological interpretation guardrails or silently replace an intentionally unsupported R method with an unrelated approximation.
