# Diagnosing common Gazepoint export and workflow problems

**Frozen R source:** `reference/vignettes/articles/troubleshooting-readiness.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.assess_gazepoint_sampling_irregularity(...)`
- `gp.audit_gazepoint_biometrics_file(...)`
- `gp.detect_gazepoint_time_columns(...)`
- `gp.diagnose_gazepoint_sync_drift(...)`
- `gp.run_gazepoint_biometrics_real_data_readiness(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.validate_gazepoint_biometrics(...)`
- `gp.validate_gazepoint_gaze(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.assess_gazepoint_sampling_irregularity(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/troubleshooting-readiness.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(600); schema=gp.detect_gazepoint_biometric_schema(d); timebase=gp.detect_gazepoint_biometric_timebase(d,time_col='TIME',counter_col='CNT'); readiness=gp.run_gazepoint_biometrics_real_data_readiness(d,min_rows=100); missing=gp.summarize_gazepoint_missingness(d,signal_cols=['GSR_US','HR','IBI','LPMM']); finish('troubleshooting-readiness',schema=schema,timebase=timebase,readiness=readiness,missingness=missing)
```
