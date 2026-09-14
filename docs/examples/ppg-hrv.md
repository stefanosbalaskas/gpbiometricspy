# PPG and HRV example

<div class="gp-page-intro">
Use this route when you have a pulse waveform or beat-to-beat intervals. The key scientific distinction is between waveform-derived pulse-rate variability, ECG-derived HRV, sampled heart rate, and vendor-precomputed metrics; source identity should be established before computing or naming variability measures.
</div>

## Waveform-to-interval path

```python
import gpbiometricspy as gp

sim = gp.simulate_gazepoint_biometrics(
    n_seconds=30,
    sampling_rate=60,
    seed=42,
)["data"]

peaks = gp.detect_gazepoint_ppg_peaks(
    sim,
    signal_col="HRP",
    time_col="CNT",
    group_cols=["participant_id"],
    sampling_rate_hz=60,
)

fig = gp.plot_gazepoint_ppg_peak_detection(peaks)
```

![PPG waveform with detected pulse peaks](../assets/generated/ppg-peak-detection.png)

The diagnostic should be inspected before deriving intervals. Peak detection errors propagate directly into beat-to-beat variability measures.

## Interval diagnostics

The bundled kiosk demonstration includes an interval channel that can be visualised after its source and units are understood:

```python
dat = gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"]).copy()
rr_ms = (dat["IBI"].dropna().iloc[::60] * 1000.0).to_numpy()

poincare = gp.plot_gazepoint_ppg_poincare(rr_ms=rr_ms)
tachogram = gp.plot_gazepoint_pyhrv_tachogram(rr_ms)
```

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#ppg-and-hrv"><img src="../assets/generated/ppg-poincare.png" alt="Poincare plot of successive beat intervals"><div class="gp-visual-card-body"><strong>Poincaré geometry</strong><span>Inspect successive-interval structure and obvious outliers before reporting nonlinear summaries.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#ppg-and-hrv"><img src="../assets/generated/hrv-tachogram.png" alt="Beat-to-beat interval tachogram"><div class="gp-visual-card-body"><strong>Tachogram</strong><span>Inspect the interval trajectory rather than relying only on aggregate HRV metrics.</span></div></a>
</div>

## Source provenance comes first

Before calling a result “HRV,” establish whether the input is:

- ECG NN intervals after artifact/ectopic handling;
- ECG RR intervals that have not been qualified as NN;
- PPG pulse intervals / PRV;
- a sampled heart-rate series;
- an undocumented device interval series;
- a vendor-precomputed variability metric.

The [cardiac variability source provenance](../methods/cardiac-source-provenance.md) layer encodes this distinction and fails closed for scientifically incompatible operations.

## Practical QC checklist

- Verify waveform sampling from observed timing when possible.
- Inspect accepted and rejected pulse events.
- Check interval units before converting or thresholding.
- Retain interval-cleaning rules and the proportion removed/corrected.
- Avoid reconstructing beat-to-beat information from sampled HR values.
- Report PPG-derived variability as PRV unless the study has evidence supporting a different interpretation.
- Use metric-specific agreement rather than global claims of interchangeability when comparing sources.

## Scientific boundary

<div class="gp-science-boundary">
HRV/PRV metrics summarize variability in cardiac or pulse timing under declared source semantics. They do not by themselves identify stress, emotion, autonomic state, diagnosis, or sensor validity, and PPG-PRV should not be silently relabelled ECG-HRV.
</div>

## Continue

- [PPG, IBI, HRV and respiration workflow](../articles/ppg-hrv-workflow.md)
- [PPG and HRV visual diagnostics](../articles/ppg-hrv-visual-diagnostics.md)
- [Cardiac source provenance](../methods/cardiac-source-provenance.md)
- [Interoperability example](interoperability.md)
