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
