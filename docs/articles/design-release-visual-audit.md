# Design release visual audit

**Frozen R source:** `reference/vignettes/articles/design-release-visual-audit.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_biometric_sampling(...)`
- `gp.audit_gazepoint_condition_balance(...)`
- `gp.audit_gazepoint_dataset_structure(...)`
- `gp.audit_gazepoint_event_coverage(...)`
- `gp.audit_gazepoint_export_schema(...)`
- `gp.audit_gazepoint_release_readiness(...)`
- `gp.audit_gazepoint_time_resets(...)`
- `gp.create_gazepoint_biometrics_report_tables(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_release_checklist(...)`
- `gp.match_gazepoint_events_to_biometrics(...)`
- `gp.plot_gazepoint_design_coverage(...)`
- `gp.profile_gazepoint_export_folder(...)`
- `gp.summarize_gazepoint_feature_coverage(...)`
- `gp.validate_gazepoint_biometrics(...)`
- `gp.validate_gazepoint_metadata(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_biometric_sampling(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
