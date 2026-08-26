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
