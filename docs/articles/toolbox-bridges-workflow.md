# External toolbox bridges workflow

**Frozen R source:** `reference/vignettes/articles/toolbox-bridges-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.assess_gazepoint_sampling_irregularity(...)`
- `gp.audit_gazepoint_gsr_units(...)`
- `gp.audit_gazepoint_ibi_quality(...)`
- `gp.audit_gazepoint_time_resets(...)`
- `gp.convert_gazepoint_gsr_to_conductance(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_pspm_glm_design(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.detect_active_biometric_channels(...)`
- `gp.detect_gazepoint_biometric_schema(...)`
- `gp.detect_gazepoint_biometric_timebase(...)`
- `gp.detect_gazepoint_ppg_peaks(...)`
- `gp.export_gazepoint_heartpy_input(...)`
- `gp.export_gazepoint_pyhrv_results(...)`
- `gp.export_gazepoint_rhrv_input(...)`
- `gp.extract_gazepoint_markerinfo_pspm_style(...)`
- `gp.extract_gazepoint_ppg_morphology(...)`
- `gp.extract_gazepoint_ppg_templates(...)`
- `gp.extract_gazepoint_pyhrv_nn_intervals(...)`
- `gp.extract_gazepoint_segments_pspm_style(...)`
- `gp.filter_gazepoint_ibi_implausible(...)`
- `gp.filter_gazepoint_ppg_signal(...)`
- `gp.import_gazepoint_pyhrv_results(...)`
- `gp.prepare_gazepoint_cvxeda_input(...)`
- `gp.prepare_gazepoint_heartpy_input(...)`
- `gp.prepare_gazepoint_ledalab_input(...)`
- `gp.prepare_gazepoint_neurokit_eda_input(...)`
- `gp.prepare_gazepoint_pspm_input(...)`
- `gp.prepare_gazepoint_pyppg_input(...)`
- `gp.prepare_gazepoint_rhrv_input(...)`
- `gp.process_gazepoint_ppg_heartpy_style(...)`
- `gp.run_gazepoint_biosppy_eda(...)`
- `gp.run_gazepoint_biosppy_ppg(...)`
- `gp.run_gazepoint_heartpy_crosscheck(...)`
- `gp.run_gazepoint_neurokit_eda_crosscheck(...)`
- `gp.run_gazepoint_pyhrv_style(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.standardise_gazepoint_biometric_names(...)`
- `gp.summarise_gazepoint_hrv_features(...)`
- `gp.summarize_gazepoint_feature_coverage(...)`
- `gp.trim_gazepoint_biometrics_pspm_style(...)`
- `gp.validate_gazepoint_biometrics(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.assess_gazepoint_sampling_irregularity(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/toolbox-bridges-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(300); hp=gp.prepare_gazepoint_heartpy_input(d,signal_col='HRP',time_col='TIME',group_cols=['participant_id'],sampling_rate_hz=60); pyppg=gp.prepare_gazepoint_pyppg_input(d,ppg_col='HRP',time_col='TIME',group_cols=['participant_id'],sampling_rate=60); nk=gp.prepare_gazepoint_neurokit_eda_input(d,eda_col='GSR_US',time_col='TIME',group_cols=['participant_id'],sampling_rate=60); led=gp.prepare_gazepoint_ledalab_input(d,eda_col='GSR_US',time_col='TIME',group_cols=['participant_id']); pspm=gp.prepare_gazepoint_pspm_input(d,eda_col='GSR_US',time_col='TIME',group_cols=['participant_id']); cvx=gp.prepare_gazepoint_cvxeda_input(d,eda_col='GSR_US',time_col='TIME',group_cols=['participant_id']); finish('toolbox-bridges-workflow',heartpy=hp,pyppg=pyppg,neurokit=nk,ledalab=led,pspm=pspm,cvxeda=cvx)
```
