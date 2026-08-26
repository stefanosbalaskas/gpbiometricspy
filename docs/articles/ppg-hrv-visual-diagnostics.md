# PPG and HRV visual diagnostics

**Frozen R source:** `reference/vignettes/articles/ppg-hrv-visual-diagnostics.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_ibi_quality(...)`
- `gp.correct_gazepoint_beats(...)`
- `gp.create_gazepoint_biometrics_report_tables(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.detect_gazepoint_ppg_peaks(...)`
- `gp.estimate_gazepoint_respiration_from_ppg(...)`
- `gp.extract_gazepoint_hrv_features(...)`
- `gp.filter_gazepoint_ibi_implausible(...)`
- `gp.filter_gazepoint_ppg_signal(...)`
- `gp.plot_gazepoint_ppg_breathing(...)`
- `gp.plot_gazepoint_ppg_peak_detection(...)`
- `gp.plot_gazepoint_ppg_poincare(...)`
- `gp.remove_gazepoint_ppg_baseline_wander(...)`
- `gp.summarise_gazepoint_hrv_features(...)`
- `gp.summarize_gazepoint_beat_corrections(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_ibi_quality(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
