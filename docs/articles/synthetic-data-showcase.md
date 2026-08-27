# Synthetic data showcase

**Frozen R source:** `reference/vignettes/articles/synthetic-data-showcase.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.align_gazepoint_biometrics_to_ttl(...)`
- `gp.audit_gazepoint_gsr_quality(...)`
- `gp.audit_gazepoint_gsr_units(...)`
- `gp.audit_gazepoint_ibi_quality(...)`
- `gp.build_gazepoint_aoi_timecourse(...)`
- `gp.convert_gazepoint_gsr_to_conductance(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_biometrics_report_tables(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.decompose_gazepoint_eda(...)`
- `gp.detect_active_biometric_channels(...)`
- `gp.detect_gazepoint_biometric_schema(...)`
- `gp.detect_gazepoint_biometric_timebase(...)`
- `gp.detect_gazepoint_ppg_peaks(...)`
- `gp.detect_gazepoint_pupil_blinks(...)`
- `gp.detect_gazepoint_scr_events(...)`
- `gp.estimate_gazepoint_respiration_from_ppg(...)`
- `gp.extract_gazepoint_hrv_features(...)`
- `gp.extract_gazepoint_ttl_events(...)`
- `gp.filter_gazepoint_gaze(...)`
- `gp.filter_gazepoint_ppg_signal(...)`
- `gp.flag_gazepoint_ppg_quality(...)`
- `gp.join_gazepoint_biometrics_to_master(...)`
- `gp.prepare_gazepoint_aoi_biometrics_model_data(...)`
- `gp.prepare_gazepoint_multimodal_model_data(...)`
- `gp.profile_gazepoint_export_folder(...)`
- `gp.recommend_gazepoint_biometric_exclusions(...)`
- `gp.run_gazepoint_biometrics_real_data_readiness(...)`
- `gp.run_gazepoint_biometrics_workflow(...)`
- `gp.simulate_gazepoint_artifact(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.simulate_gazepoint_eye_data(...)`
- `gp.simulate_gazepoint_multimodal_data(...)`
- `gp.smooth_gazepoint_pupil(...)`
- `gp.standardise_gazepoint_biometric_names(...)`
- `gp.standardize_gazepoint_column_names(...)`
- `gp.summarise_gazepoint_aoi_biometrics(...)`
- `gp.summarise_gazepoint_ibi_windows(...)`
- `gp.summarise_gazepoint_multimodal_windows(...)`
- `gp.summarise_gazepoint_scr_event_windows(...)`
- `gp.summarize_gazepoint_export_inventory(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.summarize_gazepoint_pupil_events(...)`
- `gp.summarize_gazepoint_qc_overview(...)`
- `gp.sync_gazepoint_biometrics_with_gaze(...)`
- `gp.validate_gazepoint_biometrics(...)`
- `gp.validate_gazepoint_format(...)`
- `gp.validate_gazepoint_metadata(...)`
- `gp.write_gazepoint_export_profile(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.align_gazepoint_biometrics_to_ttl(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/synthetic-data-showcase.py
```

```python
from __future__ import annotations
from _shared import *
bio=gp.simulate_gazepoint_biometrics(n_seconds=5,sampling_rate=20,seed=1); eye=gp.simulate_gazepoint_eye_data({'n_samples':100,'seed':2}); multi=gp.simulate_gazepoint_multimodal_data(duration_s=5,sampling_rate_hz=20,seed=3); artifact=gp.simulate_gazepoint_artifact(bio,signal_cols=['GSR_US'],artifact='spike',seed=4); finish('synthetic-data-showcase',biometrics=bio,eye=eye,multimodal=multi,artifact=artifact)
```
