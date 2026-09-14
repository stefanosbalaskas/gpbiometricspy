# Workflow map

<div class="gp-page-intro">
Use this page as the shortest route from **what you recorded** to **what to do next**. Start from the measurement, establish the evidence needed for the next step, then follow the domain-specific example or article.
</div>

<div class="gp-workflow-intro">
A workflow is complete only when its measurement assumptions, QC, timing, transformations, analysis settings, and reporting evidence remain traceable—not merely when it produces a final feature table.
</div>

## Choose by recorded data

| You have | Establish first | Typical next steps | Go to |
|---|---|---|---|
| EDA / GSR | units, activity, missingness, timing | tonic/phasic decomposition, SCR detection, event summaries | [EDA / GSR / SCR](examples/eda-scr.md) |
| PPG waveform | source + observed sampling + pulse quality | peak detection, intervals, PRV/HRV-ready diagnostics | [PPG / HRV](examples/ppg-hrv.md) |
| IBI / RR / NN intervals | source identity, units, cleaning status | time/frequency/nonlinear variability, agreement checks | [PPG / HRV](examples/ppg-hrv.md) |
| Pupil diameter | eye/channel, validity, blinks, timing | baseline/change summaries, event windows, AOI linkage | [Pupil / gaze / AOI](examples/pupil-gaze.md) |
| Gaze coordinates / fixations | coordinate space, validity, event source, timebase | AOIs, transitions, saccades, linked physiology | [Pupil / gaze / AOI](examples/pupil-gaze.md) |
| TTL / event markers | event identity, edge semantics, clock | trial windows, event locking, cross-stream alignment | [Multimodal alignment](examples/multimodal.md) |
| Multiple streams | clock identity + overlap + anchors | offset/drift correction, alignment, windowed features | [Timebase guide](guides/timebase-alignment.md) |
| External neuro/physiology files | backend/version + exchange semantics | MNE, LSL/XDF, BioSPPy, HeartPy, pyHRV, NeuroKit bridges | [Interoperability](examples/interoperability.md) |
| Completed analysis | QC evidence + software identity + settings | visual audit, reproducibility, interpretation guardrails | [QC + reporting](examples/quality-reporting.md) |
| Repeated/crossed outcome data | grouping structure + prediction target | grouped prediction or hierarchical location–scale modelling | [Model selection](guides/model-selection.md) |

## Recommended research pipeline

```mermaid
graph LR
  A[1 · Ingest] --> B[2 · Audit]
  B --> C[3 · Process]
  C --> D[4 · Align]
  D --> E[5 · Summarise]
  E --> F[6 · Model]
  F --> G[7 · Report]
  B -. evidence insufficient .-> R[Review / narrow claim]
  D -. timing unsupported .-> R
  F -. design unsupported .-> R
```

<div class="gp-flow">
<div><strong>01</strong><span>Ingest</span><small>Read exports, preserve source identity, standardize schema.</small></div>
<div><strong>02</strong><span>Audit</span><small>Check timing, missingness, signal activity, events and design.</small></div>
<div><strong>03</strong><span>Process</span><small>Apply modality-specific transformations with explicit settings.</small></div>
<div><strong>04</strong><span>Align</span><small>Relate clocks, events, trials, AOIs and secondary streams.</small></div>
<div><strong>05</strong><span>Model</span><small>Match validation unit and random structure to the scientific target.</small></div>
<div><strong>06</strong><span>Report</span><small>Retain QC, provenance, plots, software identity and guardrails.</small></div>
</div>

## Three workflow checkpoints

<div class="gp-guide-grid">
<div class="gp-guide-card"><span class="gp-eyebrow">Checkpoint 1</span><h3>Measurement-ready</h3><p>Source identity, units, timebase, channel validity, event coverage, and grouping variables are sufficiently documented for processing.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Checkpoint 2</span><h3>Analysis-ready</h3><p>Transformations are explicit, alignment is defensible, exclusions are traceable, and the model-ready table reflects the intended scientific unit.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Checkpoint 3</span><h3>Report-ready</h3><p>Results are accompanied by QC evidence, settings, figures, versions, prediction semantics, sensitivity checks, and restrained interpretation.</p></div>
</div>

## What makes a workflow complete?

Retain at least:

- raw-to-standardized schema decisions;
- source/provenance declarations where scientific identity matters;
- observed timebase evidence and any clock mapping;
- signal validity, missingness, dropout, and artifact evidence;
- preprocessing/filter/detection settings;
- event, trial, condition, and AOI coverage;
- optional backend/software versions;
- generated figures used for review;
- exclusion decisions with reasons;
- model specification and validation unit;
- final reporting/reproducibility object or evidence bundle.

## Visual workflow evidence

<div class="gp-visual-grid">
<a class="gp-visual-card" href="plot-gallery/#signal-overview-and-quality"><img src="assets/generated/biometric-signals.png" alt="Standardised EDA and heart-rate signal overview"><div class="gp-visual-card-body"><strong>Inspect before deriving</strong><span>Signal overview and quality evidence come before feature extraction.</span></div></a>
<a class="gp-visual-card" href="plot-gallery/#multimodal-alignment"><img src="assets/generated/multimodal-timeline.png" alt="Multimodal EDA heart-rate pupil and event timeline"><div class="gp-visual-card-body"><strong>Align before windowing</strong><span>Define event windows only after the relevant timebases are defensible.</span></div></a>
</div>

## Cross-toolbox validation

`gpbiometricspy` can work with or prepare workflows for several established ecosystems. These bridges are for **interoperability and cross-checking**, not for silently changing the package's declared analysis contract.

<div class="gp-mini-grid">
<a href="articles/toolbox-bridges-workflow/">External toolbox bridges</a>
<a href="articles/mne-eeg-lsl-workflow/">MNE / EEG / LSL</a>
<a href="articles/interoperability-version-testing/">Version testing</a>
<a href="integrations/">Integration matrix</a>
</div>

## Need a guided path?

- New to the package: [First analysis](guides/first-analysis.md)
- New research dataset: [Validate a new dataset](guides/validate-dataset.md)
- Multiple clocks/streams: [Timebase and alignment](guides/timebase-alignment.md)
- Statistical structure: [Choose a modelling strategy](guides/model-selection.md)
- Paper/supplement preparation: [Reporting and reproducibility](guides/reporting-reproducibility.md)
- Validation evidence: [Parity & validation](parity.md), [Deep validation](deep-validation.md), and [Private real-data validation](real-data-validation.md)
