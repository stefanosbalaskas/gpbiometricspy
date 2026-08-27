# PPG, IBI, HRV, and respiration workflow

**Frozen R source:** `reference/vignettes/articles/ppg-hrv-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.assess_gazepoint_sampling_irregularity(...)`
- `gp.audit_gazepoint_ibi_quality(...)`
- `gp.check_gazepoint_ppg_binary_quality(...)`
- `gp.check_gazepoint_pyhrv_interval(...)`
- `gp.compute_gazepoint_pyhrv_frequency_domain(...)`
- `gp.compute_gazepoint_pyhrv_time_domain(...)`
- `gp.correct_gazepoint_beats(...)`
- `gp.correct_gazepoint_rri_artifacts_local(...)`
- `gp.create_gazepoint_analysis_decision_log(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.create_gazepoint_reproducibility_statement(...)`
- `gp.detect_active_biometric_channels(...)`
- `gp.detect_gazepoint_biometric_schema(...)`
- `gp.detect_gazepoint_biometric_timebase(...)`
- `gp.detect_gazepoint_ppg_onsets(...)`
- `gp.detect_gazepoint_ppg_peaks(...)`
- `gp.estimate_gazepoint_breathing_rate_from_ibi(...)`
- `gp.estimate_gazepoint_respiration_from_ppg(...)`
- `gp.extract_gazepoint_hrv_features(...)`
- `gp.extract_gazepoint_pyhrv_nn_intervals(...)`
- `gp.filter_gazepoint_ibi_implausible(...)`
- `gp.filter_gazepoint_ppg_signal(...)`
- `gp.flag_gazepoint_ppg_quality(...)`
- `gp.flag_gazepoint_rr_outliers(...)`
- `gp.plot_gazepoint_ppg_breathing(...)`
- `gp.plot_gazepoint_ppg_peak_detection(...)`
- `gp.plot_gazepoint_ppg_segmentwise(...)`
- `gp.prepare_gazepoint_heartpy_input(...)`
- `gp.prepare_gazepoint_pyppg_input(...)`
- `gp.prepare_gazepoint_rhrv_input(...)`
- `gp.remove_gazepoint_ppg_baseline_wander(...)`
- `gp.run_gazepoint_pyhrv_style(...)`
- `gp.simulate_gazepoint_biometrics(...)`
- `gp.standardise_gazepoint_biometric_names(...)`
- `gp.summarise_gazepoint_hr_windows(...)`
- `gp.summarise_gazepoint_hrv_features(...)`
- `gp.summarise_gazepoint_ibi_hrv_windows(...)`
- `gp.summarise_gazepoint_ibi_windows(...)`
- `gp.summarize_gazepoint_beat_corrections(...)`

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
python examples/tutorials/ppg-hrv-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=pulse_frame(100,30); process=gp.process_gazepoint_ppg_heartpy_style(d,'pulse','time_s','participant',100,high_precision=False); nni=800+30*np.sin(np.linspace(0,12*np.pi,300)); pyhrv=gp.run_gazepoint_pyhrv_style(nni_ms=nni); freq=gp.compute_gazepoint_pyhrv_frequency_domain(nni,method='welch'); finish('ppg-hrv-workflow',process=process,pyhrv=pyhrv,frequency=freq)
```
