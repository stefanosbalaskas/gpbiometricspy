# EDA, GSR and SCR example

<div class="gp-page-intro">
Use this route when you have a conductance waveform and want an auditable path from channel inspection to decomposition and candidate skin-conductance responses. The example uses bundled synthetic/public demonstration data.
</div>

## What this example does

<div class="gp-steps">
<div class="gp-step"><strong>Inspect EDA quality</strong>Check missingness, range, activity, and whether the signal is usable before decomposition.</div>
<div class="gp-step"><strong>Separate tonic and phasic structure</strong>Apply an explicit decomposition rather than treating the raw waveform as an event series.</div>
<div class="gp-step"><strong>Detect candidate responses</strong>Use declared threshold and peak-distance settings.</div>
<div class="gp-step"><strong>Keep visual evidence</strong>Inspect decomposition, event placement, and time-frequency behavior before summarising.</div>
</div>

## Run it

```python
import gpbiometricspy as gp

dat = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)

quality = gp.audit_gazepoint_gsr_quality(dat, value_column="GSR_US")

scr = gp.detect_gazepoint_scr_events(
    dat,
    phasic_col="GSR_US_PHASIC",
    signal_col="GSR_US",
    time_col="TIME",
    group_cols=["participant_id"],
    threshold=0.02,
    min_peak_distance=30,
)

fig = gp.plot_gazepoint_scr_events(
    dat,
    scr["events"],
    time_col="TIME",
    signal_col="GSR_US",
    phasic_col="GSR_US_PHASIC",
    group_cols=["participant_id"],
    title="Detected SCR events",
)
```

For a separate decomposition step:

```python
decomposition = gp.decompose_gazepoint_eda(
    dat,
    signal_col="GSR_US",
    time_col="TIME",
    group_cols=["participant_id"],
    window_size=31,
)
```

## Read the outputs

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/eda-decomposition.png" alt="EDA observed tonic and phasic decomposition"><div class="gp-visual-card-body"><strong>EDA decomposition</strong><span>Check whether the tonic/phasic separation is plausible for the recorded waveform.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/scr-events.png" alt="EDA waveform with detected skin conductance response events"><div class="gp-visual-card-body"><strong>SCR events</strong><span>Inspect where the declared detector placed candidate responses.</span></div></a>
</div>

![EDA time-frequency diagnostic](../assets/generated/eda-gram.png)

The EDA-gram is a diagnostic view of slower electrodermal dynamics. It does not convert spectral power into a psychological label.

## Checks before using event summaries

- Confirm the conductance units and whether the export is raw or already transformed.
- Quantify missingness and flatline behavior.
- Confirm the observed timebase before interpreting response latency.
- Report decomposition and detection settings.
- Inspect sensitivity to thresholds or windows when conclusions depend on candidate response counts.
- Keep excluded intervals or participants traceable to explicit QC evidence.

## Scientific boundary

<div class="gp-science-boundary">
EDA/SCR processing describes electrodermal measurements and detected waveform features. It does not by itself identify emotion, stress, arousal, preference, deception, diagnosis, or causal responses to a stimulus.
</div>

## Continue

- [EDA and SCR visual diagnostics](../articles/eda-scr-visual-diagnostics.md)
- [EDA, GSR and SCR workflow](../articles/eda-scr-workflow.md)
- [External toolbox bridges](../articles/toolbox-bridges-workflow.md)
- [QC and reporting example](quality-reporting.md)
