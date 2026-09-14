# Interoperability examples

<div class="gp-page-intro">
Optional integrations are isolated from the core scientific install. Use them as explicit handoffs or cross-checks, not as silent substitutions for the package's declared processing semantics. Public CI exercises floor/current versions of the supported backends.
</div>

## Install the interoperability extras

```bash
python -m pip install "gpbiometricspy[interop]"
```

The core package remains usable without these dependencies.

## Physiology toolbox handoffs

```python
import gpbiometricspy as gp

dat = gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"]).iloc[:300].copy()

heartpy_input = gp.prepare_gazepoint_heartpy_input(
    dat,
    signal_col="HRP",
    time_col="TIME",
    group_cols=["participant_id"],
    sampling_rate_hz=60,
)

pyppg_input = gp.prepare_gazepoint_pyppg_input(
    dat,
    ppg_col="HRP",
    time_col="TIME",
    group_cols=["participant_id"],
    sampling_rate=60,
)

neurokit_eda = gp.prepare_gazepoint_neurokit_eda_input(
    dat,
    eda_col="GSR_US",
    time_col="TIME",
    group_cols=["participant_id"],
    sampling_rate=60,
)
```

Equivalent preparation helpers exist for Ledalab-, PsPM-, and cvxEDA-style exchange paths. The preparation step makes units, columns, sampling assumptions, and grouping structure explicit before another toolbox receives the data.

## MNE handoff

```python
mne_data = dat[["TIME", "GSR_US", "LPMM", "TTL0"]].rename(
    columns={"TIME": "time_s", "LPMM": "pupil"}
)

mne_input = gp.prepare_gazepoint_mne_input(
    mne_data,
    channel_cols=["GSR_US", "pupil", "TTL0"],
    time_col="time_s",
    sampling_rate_hz=60,
    missing="allow",
    irregular="allow",
)
```

Allowing missing or irregular samples is an explicit policy choice; it should not be interpreted as evidence that the stream is regular.

## LSL-style synchronization

```python
import pandas as pd

streams = {
    "gaze": pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "x": [0.2, 0.3, 0.4]}),
    "bio": pd.DataFrame({"time_s": [0.1, 1.1, 2.1], "gsr": [1.0, 2.0, 3.0]}),
}

synced = gp.sync_gazepoint_signals_via_lsl(
    streams,
    reference="gaze",
    clock_offsets_s={"gaze": 0.0, "bio": -0.1},
)
```

For empirical clock estimation rather than declared offsets, use the [timebase provenance](../methods/timebase-provenance.md) workflow.

## Supported CI matrix

The interoperability workflow currently covers:

- HeartPy;
- BioSPPy;
- pyHRV;
- NeuroKit2;
- MNE;
- `pylsl`;
- `pyxdf`.

The matrix checks both supported floor and current-version lanes where configured. A study should still report the exact backend version it used.

## Cross-toolbox interpretation

Agreement between toolboxes is metric- and preprocessing-specific. A successful bridge means the data structure and declared semantics can be handed off; it does not prove that two packages implement identical filters, detectors, artifact rules, or scientific constructs.

## Continue

- [Interoperability version testing](../articles/interoperability-version-testing.md)
- [MNE, EEG and LSL workflow](../articles/mne-eeg-lsl-workflow.md)
- [External toolbox bridges](../articles/toolbox-bridges-workflow.md)
- [BIDS export workflow](../articles/bids-export-workflow.md)
- [Integrations matrix](../integrations.md)
