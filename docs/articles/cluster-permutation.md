# Cluster-permutation workflow

**Frozen R source:** `reference/vignettes/articles/cluster-permutation.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.audit_gazepoint_timecourse_grid(...)`
- `gp.diagnose_gazepoint_cluster_design(...)`
- `gp.export_gazepoint_cluster_results(...)`
- `gp.export_gazepoint_mne_cluster_input(...)`
- `gp.plot_gazepoint_cluster_null_distribution(...)`
- `gp.plot_gazepoint_cluster_permutation(...)`
- `gp.prepare_gazepoint_timecourse_test_data(...)`
- `gp.report_gazepoint_cluster_permutation(...)`
- `gp.run_gazepoint_cluster_permutation(...)`
- `gp.run_gazepoint_cluster_threshold_sensitivity(...)`
- `gp.run_gazepoint_tfce(...)`
- `gp.simulate_gazepoint_cluster_timecourse_data(...)`
- `gp.summarize_gazepoint_time_clusters(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.audit_gazepoint_timecourse_grid(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/cluster-permutation.py
```

```python
from __future__ import annotations
from _shared import *
d=gp.simulate_gazepoint_cluster_timecourse_data(n_subjects=8,n_time=24,effect_start=8,effect_end=14,seed=7).rename(columns={'subject':'participant'})
res=gp.run_gazepoint_cluster_permutation(d,participant_col='participant',n_permutations=99,seed=7)
report=gp.report_gazepoint_cluster_permutation(res); finish('cluster-permutation',result=res,report=report)
```
