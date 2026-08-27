# Running private real-data smoke tests safely

**Frozen R source:** `reference/vignettes/articles/private-real-data-smoke-testing.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_smoke_privacy(...)`
- `gp.run_gazepoint_biometrics_workflow(...)`
- `gp.run_gazepoint_real_data_smoke(...)`
- `gp.write_gazepoint_real_data_smoke(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_smoke_privacy(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/private-real-data-smoke-testing.py
```

```python
from __future__ import annotations
from _shared import *
with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as od:
    p=Path(td)/'synthetic_gazepoint.csv'; demo(300).to_csv(p,index=False); smoke=gp.run_gazepoint_real_data_smoke(td,output_dir=od,write_results=True,overwrite=True,protect_repository=True); privacy=gp.audit_gazepoint_smoke_privacy(smoke)
finish('private-real-data-smoke-testing',smoke=smoke,privacy=privacy)
```
