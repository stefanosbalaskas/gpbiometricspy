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

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/eda-scr-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(900); units=gp.audit_gazepoint_gsr_units(d,gsr_col='GSR_US'); quality=gp.audit_gazepoint_gsr_quality(d,value_column='GSR_US'); artifacts=gp.audit_gazepoint_eda_artifacts(d,signal_col='GSR_US',time_col='TIME',group_cols=['participant_id'])
dec=gp.decompose_gazepoint_eda(d,signal_col='GSR_US',time_col='TIME',group_cols=['participant_id'],window_size=31); events=gp.detect_gazepoint_scr_events(dec,phasic_col='eda_phasic',time_col='TIME',group_cols=['participant_id'],min_peak_distance=10)
finish('eda-scr-workflow',units=units,quality=quality,artifacts=artifacts,decomposition=dec,events=events)
```
