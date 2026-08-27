# Using gpbiometrics with eyetrackingR, PupillometryR, and gazeR

**Frozen R source:** `reference/vignettes/articles/eye-tracking-ecosystem-bridges.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.prepare_gazepoint_eyetrackingr_input(...)`
- `gp.prepare_gazepoint_gazer_input(...)`
- `gp.prepare_gazepoint_pupillometryr_input(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.prepare_gazepoint_eyetrackingr_input(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/eye-tracking-ecosystem-bridges.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(300); e=gp.prepare_gazepoint_eyetrackingr_input(d,participant_col='participant_id',trial_col='MEDIA_ID',time_col='TIME',x_col='FPOGX',y_col='FPOGY',aoi_col='AOI',validity_col='FPOGV',irregular='allow')
p=gp.prepare_gazepoint_pupillometryr_input(d,participant_col='participant_id',trial_col='MEDIA_ID',time_col='TIME',pupil_col='LPMM',validity_cols=['LPMMV'],irregular='allow'); g=gp.prepare_gazepoint_gazer_input(d,participant_col='participant_id',trial_col='MEDIA_ID',time_col='TIME',x_col='FPOGX',y_col='FPOGY',pupil_col='LPMM',validity_col='FPOGV',irregular='allow'); finish('eye-tracking-ecosystem-bridges',eyetrackingr=e,pupillometryr=p,gazer=g)
```
