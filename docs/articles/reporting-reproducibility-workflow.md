# Reporting and reproducibility workflow

**Frozen R source:** `reference/vignettes/articles/reporting-reproducibility-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.add_gazepoint_decision(...)`
- `gp.audit_gazepoint_preregistration_consistency(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_analysis_manifest(...)`
- `gp.create_gazepoint_audit_index(...)`
- `gp.create_gazepoint_audit_report_section(...)`
- `gp.create_gazepoint_biometrics_checklist(...)`
- `gp.create_gazepoint_biometrics_methods_text(...)`
- `gp.create_gazepoint_biometrics_report_tables(...)`
- `gp.create_gazepoint_methods_section(...)`
- `gp.create_gazepoint_preregistration_checklist(...)`
- `gp.create_gazepoint_preregistration_template(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_release_checklist(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.create_gazepoint_sidecar_template(...)`
- `gp.export_gazepoint_audit_trail_markdown(...)`
- `gp.export_gazepoint_biometrics_report_bundle(...)`
- `gp.generate_gazepoint_manifest(...)`
- `gp.summarise_gazepoint_decision_log(...)`
- `gp.summarize_gazepoint_preregistration_readiness(...)`
- `gp.write_gazepoint_biometrics_report_tables(...)`
- `gp.write_gazepoint_decision_log(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.add_gazepoint_decision(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
