# gp3tools compatibility and cross-package handoff

**Frozen R source:** `reference/vignettes/articles/gp3tools-compatibility.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.join_gazepoint_biometrics_to_gp3tools(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.join_gazepoint_biometrics_to_gp3tools(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
