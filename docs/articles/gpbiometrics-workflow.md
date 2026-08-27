# gpbiometrics workflow

**Frozen R source:** `reference/vignettes/gpbiometrics-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.align_gazepoint_biometrics_to_ttl(...)`
- `gp.audit_gazepoint_gsr_units(...)`
- `gp.correct_gazepoint_eda_temperature(...)`
- `gp.create_gazepoint_biometrics_feature_inventory(...)`
- `gp.export_gazepoint_biometrics_report_bundle(...)`
- `gp.extract_gazepoint_beats_kmeans(...)`
- `gp.extract_gazepoint_hrv_features(...)`
- `gp.extract_gazepoint_hrv_fuzzy_csi(...)`
- `gp.extract_gazepoint_hrv_nonlinear(...)`
- `gp.extract_gazepoint_hrv_rcmse(...)`
- `gp.extract_gazepoint_scr_recovery_times(...)`
- `gp.extract_gazepoint_ttl_events(...)`
- `gp.format_gazepoint_biometrics_feature_inventory(...)`
- `gp.import_gazepoint_biometric_folder(...)`
- `gp.import_gazepoint_biometrics(...)`
- `gp.prepare_gazepoint_biometrics_lme_data(...)`
- `gp.run_gazepoint_biometrics_real_data_readiness(...)`
- `gp.run_gazepoint_biometrics_workflow(...)`
- `gp.standardise_gazepoint_adaptive_ema(...)`
- `gp.summarise_gazepoint_biometrics_feature_inventory(...)`
- `gp.summarise_gazepoint_biometrics_workflow(...)`
- `gp.summarise_gazepoint_hrv_features(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.align_gazepoint_biometrics_to_ttl(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/gpbiometrics-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(900); active=gp.detect_active_biometric_channels(d); schema=gp.detect_gazepoint_biometric_schema(d); readiness=gp.run_gazepoint_biometrics_real_data_readiness(d,min_rows=100); inv=gp.create_gazepoint_biometrics_feature_inventory(); finish('gpbiometrics-workflow',active=active,schema=schema,readiness=readiness,inventory=inv)
```
