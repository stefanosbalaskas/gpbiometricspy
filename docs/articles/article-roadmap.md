# Article roadmap

**Frozen R source:** `reference/vignettes/articles/article-roadmap.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.align_gazepoint_biometrics_to_ttl(...)`
- `gp.align_gazepoint_streams_by_events(...)`
- `gp.audit_gazepoint_condition_balance(...)`
- `gp.audit_gazepoint_dataset_structure(...)`
- `gp.audit_gazepoint_eda_artifacts(...)`
- `gp.audit_gazepoint_event_coverage(...)`
- `gp.audit_gazepoint_experiment_design(...)`
- `gp.audit_gazepoint_export_schema(...)`
- `gp.audit_gazepoint_gsr_quality(...)`
- `gp.audit_gazepoint_gsr_units(...)`
- `gp.audit_gazepoint_ibi_quality(...)`
- `gp.audit_gazepoint_preregistration_consistency(...)`
- `gp.audit_gazepoint_session_comparability(...)`
- `gp.baseline_correct_gazepoint_gsr(...)`
- `gp.baseline_correct_gazepoint_pupil(...)`
- `gp.convert_gazepoint_gsr_to_conductance(...)`
- `gp.correct_gazepoint_beats(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_analysis_manifest(...)`
- `gp.create_gazepoint_biometrics_methods_text(...)`
- `gp.create_gazepoint_dictionary(...)`
- `gp.create_gazepoint_methods_section(...)`
- `gp.create_gazepoint_preregistration_checklist(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.decompose_gazepoint_eda(...)`
- `gp.detect_gazepoint_blinks(...)`
- `gp.detect_gazepoint_ppg_onsets(...)`
- `gp.detect_gazepoint_ppg_peaks(...)`
- `gp.detect_gazepoint_pupil_blinks(...)`
- `gp.detect_gazepoint_scr_events(...)`
- `gp.detect_gazepoint_scr_peaks(...)`
- `gp.diagnose_gazepoint_biometrics_workflow(...)`
- `gp.estimate_gazepoint_respiration_from_ppg(...)`
- `gp.export_gazepoint_biometrics_report_bundle(...)`
- `gp.export_gazepoint_heartpy_input(...)`
- `gp.export_gazepoint_rhrv_input(...)`
- `gp.extract_gazepoint_hrv_features(...)`
- `gp.extract_gazepoint_ttl_events(...)`
- `gp.filter_gazepoint_gaze(...)`
- `gp.filter_gazepoint_ppg_signal(...)`
- `gp.generate_gazepoint_manifest(...)`
- `gp.interpolate_gazepoint_pupil_blinks(...)`
- `gp.match_gazepoint_events_to_biometrics(...)`
- `gp.normalize_gazepoint_scr(...)`
- `gp.plot_gazepoint_aoi_biometrics(...)`
- `gp.plot_gazepoint_biometric_quality(...)`
- `gp.plot_gazepoint_biometric_report_dashboard(...)`
- `gp.plot_gazepoint_biometric_signals(...)`
- `gp.plot_gazepoint_eda_decomposition(...)`
- `gp.plot_gazepoint_missingness(...)`
- `gp.plot_gazepoint_multimodal_timeline(...)`
- `gp.plot_gazepoint_ppg_breathing(...)`
- `gp.plot_gazepoint_ppg_peak_detection(...)`
- `gp.plot_gazepoint_ppg_segmentwise(...)`
- `gp.plot_gazepoint_scr_events(...)`
- `gp.plot_gazepoint_signal_activity(...)`
- `gp.plot_gazepoint_signal_quality(...)`
- `gp.plot_gazepoint_time_resets(...)`
- `gp.prepare_gazepoint_cvxeda_input(...)`
- `gp.prepare_gazepoint_heartpy_input(...)`
- `gp.prepare_gazepoint_ledalab_input(...)`
- `gp.prepare_gazepoint_neurokit_eda_input(...)`
- `gp.prepare_gazepoint_pspm_input(...)`
- `gp.prepare_gazepoint_pyppg_input(...)`
- `gp.prepare_gazepoint_rhrv_input(...)`
- `gp.remove_gazepoint_ppg_baseline_wander(...)`
- `gp.run_gazepoint_biometrics_workflow(...)`
- `gp.simulate_gazepoint_artifact(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.simulate_gazepoint_eye_data(...)`
- `gp.simulate_gazepoint_multimodal_data(...)`
- `gp.smooth_gazepoint_pupil(...)`
- `gp.summarise_gazepoint_aoi_biometrics(...)`
- `gp.summarise_gazepoint_biometrics_workflow(...)`
- `gp.summarise_gazepoint_gsr_tonic_phasic(...)`
- `gp.summarise_gazepoint_hrv_features(...)`
- `gp.summarise_gazepoint_scr_event_windows(...)`
- `gp.summarize_gazepoint_aoi_dwell(...)`
- `gp.summarize_gazepoint_beat_corrections(...)`
- `gp.summarize_gazepoint_eventlocked_multimodal(...)`
- `gp.summarize_gazepoint_pupil_events(...)`
- `gp.summarize_gazepoint_qc_overview(...)`
- `gp.sync_gazepoint_biometrics_with_gaze(...)`
- `gp.write_gazepoint_decision_log(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.align_gazepoint_biometrics_to_ttl(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.
