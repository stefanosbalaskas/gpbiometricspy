# Workflow map

Use this page as the shortest route from **what you recorded** to **what to do next**.

<div class="gp-workflow-intro">
Start with the row that matches your data. Each path links to executable examples, generated plots, and deeper articles.
</div>

| You have | Start with | Typical next steps | Go to |
|---|---|---|---|
| EDA / GSR | channel + artifact QC | tonic/phasic decomposition, SCR detection, event summaries | [EDA / GSR / SCR](examples/eda-scr.md) |
| PPG / pulse waveform | signal-quality + peak detection | IBI, HR, HRV, Poincaré/tachogram diagnostics | [PPG / HRV](examples/ppg-hrv.md) |
| IBI / RR intervals | interval validity | time/frequency/nonlinear HRV, toolbox cross-checks | [PPG / HRV](examples/ppg-hrv.md) |
| Pupil diameter | missingness/blink/pupil QC | baseline/change summaries, event windows, AOI linkage | [Pupil / gaze / AOI](examples/pupil-gaze.md) |
| Gaze coordinates / fixations | validity + timing QC | AOIs, transitions, saccades, linked physiology | [Pupil / gaze / AOI](examples/pupil-gaze.md) |
| TTL / event markers | event extraction + timebase audit | trial windows, event locking, multimodal synchronization | [Multimodal alignment](examples/multimodal.md) |
| Multiple synchronized streams | schema + timing audit | alignment, windowed features, dashboards, model-ready tables | [Multimodal alignment](examples/multimodal.md) |
| External neuro/physiology files | backend/version audit | MNE, LSL/XDF, BioSPPy, HeartPy, pyHRV, NeuroKit bridges | [Interoperability](examples/interoperability.md) |
| A completed analysis | QC evidence + manifest/reporting | visual audit, reproducibility, interpretation guardrails | [QC + reporting](examples/quality-reporting.md) |

## Recommended research pipeline

<div class="gp-flow">
<div><strong>1</strong><span>Ingest</span><small>Read exports and standardize schema.</small></div>
<div><strong>2</strong><span>Audit</span><small>Check channels, timing, missingness, dropouts and markers.</small></div>
<div><strong>3</strong><span>Process</span><small>Apply modality-specific preprocessing.</small></div>
<div><strong>4</strong><span>Align</span><small>Join trials, events, AOIs and external streams.</small></div>
<div><strong>5</strong><span>Summarize</span><small>Build features, plots and model-ready tables.</small></div>
<div><strong>6</strong><span>Report</span><small>Retain QC, provenance and cautious interpretation.</small></div>
</div>

## What makes a workflow complete?

A defensible workflow should usually leave behind **more than a final feature table**. For reproducibility, retain:

- the raw-to-standardized schema decisions;
- signal/timebase validity outputs;
- event and alignment diagnostics;
- preprocessing settings;
- exclusion or dropout evidence;
- software/backend versions for optional integrations;
- generated figures used for QC;
- the final reporting or reproducibility object.

## Cross-toolbox validation

`gpbiometricspy` can work with, or mirror workflows from, several established Python ecosystems. These bridges are for **interoperability and cross-checking**, not for silently changing the package's declared analysis contract.

<div class="gp-mini-grid">
<a href="articles/toolbox-bridges-workflow/">External toolbox bridges</a>
<a href="articles/mne-eeg-lsl-workflow/">MNE / EEG / LSL</a>
<a href="articles/interoperability-version-testing/">Version testing</a>
<a href="integrations/">Integration matrix</a>
</div>

## Need the evidence layer?

Go to [Parity & validation](parity.md) for the frozen R contract, [Deep validation](deep-validation.md) for cross-runtime checks, and [Private real-data validation](real-data-validation.md) for the privacy-safe real-data harness.
