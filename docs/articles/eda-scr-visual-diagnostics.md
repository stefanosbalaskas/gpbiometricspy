# EDA and SCR visual diagnostics

**Frozen R source:** `reference/vignettes/articles/eda-scr-visual-diagnostics.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_gsr_units(...)`
- `gp.compute_gazepoint_scr_latency(...)`
- `gp.convert_gazepoint_gsr_to_conductance(...)`
- `gp.create_gazepoint_biometrics_report_tables(...)`
- `gp.create_gazepoint_qc_supplement(...)`
- `gp.decompose_gazepoint_eda(...)`
- `gp.detect_gazepoint_scr_events(...)`
- `gp.detect_gazepoint_scr_peaks(...)`
- `gp.extract_gazepoint_scr_recovery_times(...)`
- `gp.plot_gazepoint_eda_decomposition(...)`
- `gp.plot_gazepoint_scr_events(...)`
- `gp.plot_gazepoint_scr_specification_curve(...)`
- `gp.run_gazepoint_scr_threshold_sensitivity(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_gsr_units(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/eda-scr-visual-diagnostics.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(900); dec=gp.decompose_gazepoint_eda(d,signal_col='GSR_US',time_col='TIME',group_cols=['participant_id'],window_size=31)
ev=gp.detect_gazepoint_scr_events(dec,phasic_col='eda_phasic',time_col='TIME',group_cols=['participant_id'],min_peak_distance=10)
fig1=gp.plot_gazepoint_eda_decomposition(dec,time_col='TIME',signal_cols=['GSR_US','eda_tonic','eda_phasic'],group_cols=['participant_id']); finish('eda-scr-visual-diagnostics',decomposition=dec,events=ev,figure=fig1)
```


## Rendered Python output

These figures are generated from bundled synthetic/public data by `scripts/generate_docs_gallery.py` using the current Python plotting API.

### EDA decomposition

![EDA decomposition](../assets/generated/eda-decomposition.png)

### Detected SCR events

![Detected SCR events](../assets/generated/scr-events.png)

### EDA-gram

![EDA-gram](../assets/generated/eda-gram.png)
