# Toolbox crosscheck visuals

**Frozen R source:** `reference/vignettes/articles/toolbox-crosscheck-visuals.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.compare_gazepoint_pyhrv_psd_methods(...)`
- `gp.create_gazepoint_biometrics_report_tables(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.export_gazepoint_heartpy_input(...)`
- `gp.export_gazepoint_rhrv_input(...)`
- `gp.pipeline_comparison_dashboard(...)`
- `gp.plot_gazepoint_ppg_peak_detection(...)`
- `gp.plot_gazepoint_ppg_poincare(...)`
- `gp.plot_gazepoint_scr_events(...)`
- `gp.prepare_gazepoint_heartpy_input(...)`
- `gp.prepare_gazepoint_pyppg_input(...)`
- `gp.prepare_gazepoint_rhrv_input(...)`
- `gp.run_gazepoint_biosppy_eda(...)`
- `gp.run_gazepoint_biosppy_ppg(...)`
- `gp.run_gazepoint_heartpy_crosscheck(...)`
- `gp.run_gazepoint_neurokit_eda_crosscheck(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.compare_gazepoint_pyhrv_psd_methods(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/toolbox-crosscheck-visuals.py
```

```python
from __future__ import annotations
from _shared import *
d=pulse_frame(100,20); det=gp.detect_gazepoint_ppg_peaks(d,'pulse','time_s',['participant'],100,high_precision=False); heart=gp.run_gazepoint_heartpy_crosscheck(d,'pulse','time_s','participant',100,high_precision=False); bio=gp.run_gazepoint_biosppy_ppg(d.rename(columns={'pulse':'ppg'}),'ppg','time_s','participant',100); fig1=gp.plot_gazepoint_ppg_peak_detection(det); finish('toolbox-crosscheck-visuals',heartpy=heart,biosppy=bio,figure=fig1)
```
