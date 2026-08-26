# Plot gallery

**Frozen R source:** `reference/vignettes/articles/plot-gallery.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.align_gazepoint_biometrics_to_ttl(...)`
- `gp.audit_gazepoint_signal_activity(...)`
- `gp.audit_gazepoint_time_resets(...)`
- `gp.convert_gazepoint_gsr_to_conductance(...)`
- `gp.create_gazepoint_quality_dashboard(...)`
- `gp.decompose_gazepoint_eda(...)`
- `gp.detect_gazepoint_ppg_peaks(...)`
- `gp.detect_gazepoint_scr_events(...)`
- `gp.estimate_gazepoint_respiration_from_ppg(...)`
- `gp.extract_gazepoint_hrv_features(...)`
- `gp.extract_gazepoint_ttl_events(...)`
- `gp.filter_gazepoint_ppg_signal(...)`
- `gp.plot_gazepoint_aoi_biometrics(...)`
- `gp.plot_gazepoint_biometric_quality(...)`
- `gp.plot_gazepoint_biometric_report_dashboard(...)`
- `gp.plot_gazepoint_biometric_signals(...)`
- `gp.plot_gazepoint_design_coverage(...)`
- `gp.plot_gazepoint_eda_decomposition(...)`
- `gp.plot_gazepoint_eda_gram(...)`
- `gp.plot_gazepoint_missingness(...)`
- `gp.plot_gazepoint_multimodal_timeline(...)`
- `gp.plot_gazepoint_ppg_breathing(...)`
- `gp.plot_gazepoint_ppg_peak_detection(...)`
- `gp.plot_gazepoint_ppg_poincare(...)`
- `gp.plot_gazepoint_ppg_segmentwise(...)`
- `gp.plot_gazepoint_pyhrv_hr_heatplot(...)`
- `gp.plot_gazepoint_pyhrv_radar_chart(...)`
- `gp.plot_gazepoint_pyhrv_tachogram(...)`
- `gp.plot_gazepoint_saccade_main_sequence(...)`
- `gp.plot_gazepoint_scr_events(...)`
- `gp.plot_gazepoint_scr_specification_curve(...)`
- `gp.plot_gazepoint_signal_activity(...)`
- `gp.plot_gazepoint_signal_quality(...)`
- `gp.plot_gazepoint_time_resets(...)`
- `gp.run_gazepoint_pyhrv_style(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.simulate_gazepoint_eye_data(...)`
- `gp.standardise_gazepoint_biometric_names(...)`
- `gp.standardize_gazepoint_column_names(...)`
- `gp.summarise_gazepoint_aoi_biometrics(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.summarize_gazepoint_signal_quality(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.align_gazepoint_biometrics_to_ttl(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
