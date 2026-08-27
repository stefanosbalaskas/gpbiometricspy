# Exporting Gazepoint eye-tracking and physiology to BIDS

**Frozen R source:** `reference/vignettes/articles/bids-export-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.check_gazepoint_bids(...)`
- `gp.export_gazepoint_to_bids(...)`
- `gp.prepare_gazepoint_bids_eye(...)`
- `gp.prepare_gazepoint_bids_physio(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.check_gazepoint_bids(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/bids-export-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(240)[['TIME','FPOGX','FPOGY','LPMM','participant_id']].rename(columns={'TIME':'timestamp','FPOGX':'x','FPOGY':'y','LPMM':'pupil'})
with tempfile.TemporaryDirectory() as td:
    plan=gp.export_gazepoint_to_bids(d,td,subject='01',task='kiosk',timestamp_col='timestamp',x_col='x',y_col='y',pupil_col='pupil',dry_run=True)
finish('bids-export-workflow',plan=plan)
```
