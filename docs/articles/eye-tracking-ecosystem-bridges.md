# Using gpbiometrics with eyetrackingR, PupillometryR, and gazeR

**Frozen R source:** `reference/vignettes/articles/eye-tracking-ecosystem-bridges.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.prepare_gazepoint_eyetrackingr_input(...)`
- `gp.prepare_gazepoint_gazer_input(...)`
- `gp.prepare_gazepoint_pupillometryr_input(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.prepare_gazepoint_eyetrackingr_input(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
