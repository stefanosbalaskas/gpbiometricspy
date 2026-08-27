# Quality-control workflow

**Frozen R source:** `reference/vignettes/articles/qc-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.check_gazepoint_bids(...)`
- `gp.classify_gazepoint_signal_quality(...)`
- `gp.compute_gazepoint_signal_quality(...)`
- `gp.create_gazepoint_analysis_manifest(...)`
- `gp.create_gazepoint_dictionary(...)`
- `gp.detect_gazepoint_blinks(...)`
- `gp.detect_gazepoint_nonwear(...)`
- `gp.pipeline_comparison_dashboard(...)`
- `gp.plot_gazepoint_missingness(...)`
- `gp.recommend_gazepoint_biometric_exclusions(...)`
- `gp.summarize_gazepoint_missingness(...)`
- `gp.summarize_gazepoint_signal_quality(...)`
- `gp.validate_gazepoint_metadata(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.check_gazepoint_bids(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/qc-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(900); active=gp.detect_active_biometric_channels(d); miss=gp.summarize_gazepoint_missingness(d,signal_cols=['GSR_US','HR','IBI','LPMM']); validity=gp.summarise_gazepoint_biometric_validity(d); quality=gp.audit_gazepoint_gsr_quality(d,value_column='GSR_US'); finish('qc-workflow',active=active,missingness=miss,validity=validity,quality=quality)
```
