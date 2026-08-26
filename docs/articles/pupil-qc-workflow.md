# Pupil and gaze quality-control workflow

**Frozen R source:** `reference/vignettes/articles/pupil-qc-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.baseline_correct_gazepoint_pupil(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.detect_gazepoint_blinks(...)`
- `gp.detect_gazepoint_pupil_blinks(...)`
- `gp.filter_gazepoint_gaze(...)`
- `gp.interpolate_gazepoint_pupil_blinks(...)`
- `gp.pipeline_comparison_dashboard(...)`
- `gp.plot_gazepoint_missingness(...)`
- `gp.profile_gazepoint_export_folder(...)`
- `gp.recommend_gazepoint_biometric_exclusions(...)`
- `gp.simulate_gazepoint_eye_data(...)`
- `gp.smooth_gazepoint_pupil(...)`
- `gp.standardize_gazepoint_column_names(...)`
- `gp.summarize_gazepoint_export_inventory(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.summarize_gazepoint_pupil_events(...)`
- `gp.summarize_gazepoint_qc_overview(...)`
- `gp.validate_gazepoint_format(...)`
- `gp.validate_gazepoint_metadata(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.baseline_correct_gazepoint_pupil(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
