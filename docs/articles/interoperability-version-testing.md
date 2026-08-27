# Testing interoperability across external package versions

**Frozen R source:** `reference/vignettes/articles/interoperability-version-testing.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_interoperability_versions(...)`
- `gp.gazepoint_interoperability_manifest(...)`
- `gp.write_gazepoint_interoperability_audit(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_interoperability_versions(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/interoperability-version-testing.py
```

```python
from __future__ import annotations
from _shared import *
manifest=gp.gazepoint_interoperability_manifest(); audit=gp.audit_gazepoint_interoperability_versions(manifest=manifest)
with tempfile.TemporaryDirectory() as td: written=gp.write_gazepoint_interoperability_audit(audit,output_dir=td)
finish('interoperability-version-testing',manifest=manifest,audit=audit,written=written)
```
