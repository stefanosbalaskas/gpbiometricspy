# Getting started

This page takes you from installation to a validated, event-aware biometric workflow in a few minutes.

## 1. Install

=== "Stable from PyPI"

    ```bash
    python -m pip install gpbiometricspy
    ```

=== "Development from GitHub"

    ```bash
    python -m pip install \
      "gpbiometricspy @ git+https://github.com/stefanosbalaskas/gpbiometricspy.git@main"
    ```

The package requires **Python 3.11 or newer**. `0.1.3` is the stable public release; this documentation is frozen from the validated release source.

## 2. Load the packaged demo

```python
import gpbiometricspy as gp

data = gp.load_kiosk_demo()
print(data.shape)
```

The bundled kiosk dataset contains **36 synthetic participants**, four tasks per participant, and **69,120 Gazepoint-like rows at 60 Hz**. It is designed for tutorials, smoke tests, and reproducible examples—not for substantive empirical conclusions.

## 3. Audit before analysing

```python
active = gp.detect_gazepoint_active_channels(data)
validity = gp.summarise_gazepoint_biometric_validity(data)
events = gp.extract_gazepoint_ttl_events(data)

print(active)
print(validity)
print(events.head())
```

A useful default order is:

1. identify available channels;
2. validate timing and missingness;
3. recover events/TTL markers;
4. preprocess only the signals that passed the relevant checks;
5. align by event, trial, or AOI;
6. summarize and plot;
7. retain the QC/audit outputs with the analysis.

## 4. Pick a domain path

<div class="gp-card-grid gp-card-grid-compact">
<a class="gp-card gp-card-link" href="../examples/eda-scr/"><h3>EDA / SCR</h3><p>Artifacts, decomposition, SCR events and summaries.</p><span class="gp-card-cta">Start EDA →</span></a>
<a class="gp-card gp-card-link" href="../examples/ppg-hrv/"><h3>PPG / HRV</h3><p>Pulse detection, IBI, HRV and toolbox-style cross-checks.</p><span class="gp-card-cta">Start PPG →</span></a>
<a class="gp-card gp-card-link" href="../examples/pupil-gaze/"><h3>Pupil / gaze</h3><p>Pupil QC, gaze/AOI summaries and saccade diagnostics.</p><span class="gp-card-cta">Start gaze →</span></a>
</div>

## 5. A compact physiological example

```python
# pyHRV-style example from IBI in seconds
nni_ms = (
    data.loc[data["IBI"].notna(), "IBI"]
    .head(500)
    .to_numpy()
    * 1000
)
hrv = gp.run_gazepoint_pyhrv_style(nni_ms=nni_ms)

# HeartPy-style PPG processing
ppg = gp.process_gazepoint_ppg_heartpy_style(
    data,
    signal_col="HRP",
    time_col="TIME",
)
```

## 6. Add optional backends only when needed

```bash
pip install "gpbiometricspy[mne,lsl]"
pip install "gpbiometricspy[heartpy,neurokit]"
pip install "gpbiometricspy[biosppy,pyhrv]"
pip install "gpbiometricspy[stats]"
```

The core package does not require these external toolboxes. Interoperability functions report backend/version context so that optional-tool results remain auditable.

!!! tip "Where to go next"
    Use the [workflow map](../workflows/) if you know your data modality but not the exact function family. Use the [plot gallery](../plot-gallery/) if you want to see expected visual outputs first. Use the [API reference](../api/reference/) when you already know the function name.

!!! warning "Interpretation guardrail"
    Physiological and eye-tracking measurements support signal-level and task-context analyses. They do not, by themselves, establish emotion, stress, preference, cognition, comprehension, clinical state, or diagnosis. See [Interpretation guardrails](../interpretation/).
