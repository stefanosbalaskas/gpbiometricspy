# Visual QC dashboard workflow

**Frozen R source:** `reference/vignettes/articles/visual-qc-dashboard-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_signal_activity(...)`
- `gp.audit_gazepoint_time_resets(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_quality_dashboard(...)`
- `gp.plot_gazepoint_biometric_report_dashboard(...)`
- `gp.plot_gazepoint_missingness(...)`
- `gp.plot_gazepoint_signal_activity(...)`
- `gp.plot_gazepoint_signal_quality(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.summarize_gazepoint_signal_quality(...)`
- `gp.write_gazepoint_decision_log(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_signal_activity(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
