# MNE, EEG, and LSL interoperability workflow

**Frozen R source:** `reference/vignettes/articles/mne-eeg-lsl-workflow.Rmd`

This page is the Python migration companion for the corresponding `gpbiometrics 2.0.0` article. The original R article is retained verbatim in `reference/vignettes/`; this companion identifies the matching Python API so the scientific workflow can be reproduced without hiding the reference implementation.

## Python API crosswalk

The frozen R article calls the following exported functions; all are available under the same names in `gpbiometricspy`:

- `gp.align_gazepoint_to_eeg(...)`
- `gp.estimate_gazepoint_lsl_clock_offsets(...)`
- `gp.prepare_gazepoint_mne_events(...)`
- `gp.prepare_gazepoint_mne_input(...)`
- `gp.sync_gazepoint_signals_via_lsl(...)`
- `gp.write_gazepoint_mne_fif(...)`

```python
import gpbiometricspy as gp

# Example entry point from this workflow
# result = gp.align_gazepoint_to_eeg(...)
```

## Interpretation

Use the same conservative physiological interpretation as the R package: derived biometric features are signal-processing outputs and do not directly establish emotion, stress, cognition, preference, health status, or diagnosis.

## Executable Python companion

The frozen R call crosswalk above is retained for completeness. The following companion is an executable end-to-end Python workflow using synthetic/public data and the same scientific domain. It is also executed by the test suite.

Run from the repository root:

```bash
python examples/tutorials/mne-eeg-lsl-workflow.py
```

```python
from __future__ import annotations
from _shared import *
d=demo(240)[['TIME','GSR_US','LPMM','TTL0']].rename(columns={'TIME':'time_s','LPMM':'pupil'}); mne_in=gp.prepare_gazepoint_mne_input(d,channel_cols=['GSR_US','pupil','TTL0'],time_col='time_s',sampling_rate_hz=60,missing='allow',irregular='allow')
events=gp.prepare_gazepoint_mne_events(pd.DataFrame({'event_time_s':[1.,2.],'event_label':['stimulus','response']}),sampling_rate_hz=60); synced=gp.sync_gazepoint_signals_via_lsl({'gaze':pd.DataFrame({'time_s':[0,1,2],'x':[.2,.3,.4]}),'bio':pd.DataFrame({'time_s':[.1,1.1,2.1],'gsr':[1,2,3]})},reference='gaze',clock_offsets_s={'gaze':0,'bio':-.1}); finish('mne-eeg-lsl-workflow',mne=mne_in,events=events,synced=synced)
```
