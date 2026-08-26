# Design audit workflow

**Frozen R source:** `reference/vignettes/articles/design-audit-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.assert_gazepoint_columns(...)`
- `gp.assess_gazepoint_sampling_irregularity(...)`
- `gp.audit_gazepoint_condition_balance(...)`
- `gp.audit_gazepoint_dataset_structure(...)`
- `gp.audit_gazepoint_event_coverage(...)`
- `gp.audit_gazepoint_experiment_design(...)`
- `gp.audit_gazepoint_export_schema(...)`
- `gp.audit_gazepoint_pipeline_steps(...)`
- `gp.audit_gazepoint_release_readiness(...)`
- `gp.audit_gazepoint_session_comparability(...)`
- `gp.audit_gazepoint_time_resets(...)`
- `gp.audit_gazepoint_timecourse_grid(...)`
- `gp.compare_gazepoint_export_profiles(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_audit_index(...)`
- `gp.create_gazepoint_audit_report_section(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.detect_active_biometric_channels(...)`
- `gp.detect_gazepoint_biometric_timebase(...)`
- `gp.extract_gazepoint_ttl_events(...)`
- `gp.match_gazepoint_events_to_biometrics(...)`
- `gp.plot_gazepoint_design_coverage(...)`
- `gp.profile_gazepoint_export_folder(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.simulate_gazepoint_eye_data(...)`
- `gp.standardise_gazepoint_biometric_names(...)`
- `gp.standardize_gazepoint_column_names(...)`
- `gp.summarize_gazepoint_export_inventory(...)`
- `gp.validate_gazepoint_biometrics(...)`
- `gp.validate_gazepoint_format(...)`
- `gp.validate_gazepoint_metadata(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.assert_gazepoint_columns(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
