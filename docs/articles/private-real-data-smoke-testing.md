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
