# EDA, GSR, and SCR workflow

**Frozen R source:** `reference/vignettes/articles/eda-scr-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_eda_artifacts(...)`
- `gp.audit_gazepoint_gsr_quality(...)`
- `gp.audit_gazepoint_gsr_units(...)`
- `gp.baseline_correct_gazepoint_gsr(...)`
- `gp.classify_gazepoint_eda_response_pattern(...)`
- `gp.convert_gazepoint_gsr_to_conductance(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.decompose_gazepoint_eda(...)`
- `gp.detect_gazepoint_scr_events(...)`
- `gp.detect_gazepoint_scr_peaks(...)`
- `gp.normalize_gazepoint_scr(...)`
- `gp.plot_gazepoint_eda_decomposition(...)`
- `gp.plot_gazepoint_scr_events(...)`
- `gp.plot_gazepoint_scr_specification_curve(...)`
- `gp.prepare_gazepoint_scr_hurdle_model_data(...)`
- `gp.run_gazepoint_scr_multiverse(...)`
- `gp.run_gazepoint_scr_threshold_sensitivity(...)`
- `gp.screen_gazepoint_eda_nonresponders(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.standardise_gazepoint_biometric_names(...)`
- `gp.summarise_gazepoint_gsr_tonic_phasic(...)`
- `gp.summarise_gazepoint_gsr_windows(...)`
- `gp.summarise_gazepoint_scr_event_windows(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_eda_artifacts(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
