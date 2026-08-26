# Quality-control workflow

**Frozen R source:** `reference/vignettes/articles/qc-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.check_gazepoint_bids(...)`
- `gp.classify_gazepoint_signal_quality(...)`
- `gp.compute_gazepoint_signal_quality(...)`
- `gp.create_gazepoint_analysis_manifest(...)`
- `gp.create_gazepoint_dictionary(...)`
- `gp.detect_gazepoint_blinks(...)`
- `gp.detect_gazepoint_nonwear(...)`
- `gp.pipeline_comparison_dashboard(...)`
- `gp.plot_gazepoint_missingness(...)`
- `gp.recommend_gazepoint_biometric_exclusions(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.summarize_gazepoint_signal_quality(...)`
- `gp.validate_gazepoint_metadata(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.check_gazepoint_bids(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
