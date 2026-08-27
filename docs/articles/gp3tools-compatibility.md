# gp3tools compatibility and cross-package handoff

**Frozen R source:** `reference/vignettes/articles/gp3tools-compatibility.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.join_gazepoint_biometrics_to_gp3tools(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.join_gazepoint_biometrics_to_gp3tools(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/gp3tools-compatibility.py
```

```python
from __future__ import annotations
from _shared import *
bio=pd.DataFrame({'participant':['P01','P01'],'time':[0.,1.],'GSR_US':[1.,1.2]}); gaze=pd.DataFrame({'participant':['P01','P01'],'time':[0.,1.],'FPOGX':[.2,.3],'FPOGY':[.4,.5]})
try: joined=gp.join_gazepoint_biometrics_to_gp3tools(bio,gaze,by=['participant','time'])
except TypeError: joined=gp.join_gazepoint_biometrics_to_gp3tools(bio,gaze)
finish('gp3tools-compatibility',joined=joined)
```
