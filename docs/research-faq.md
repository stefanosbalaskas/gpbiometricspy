---
description: Evidence-first answers to common gpbiometricspy research workflow questions about imports, units, clocks, QC, events, exclusions, modelling, interpretation, and reporting.
search:
  boost: 1.35
---

# Research FAQ & decision clinic

<div class="gp-page-intro" data-research-faq>
Use this page for the questions that often appear **between** software success and scientific readiness. Each answer gives a short decision rule and then points to the deeper workflow that owns the evidence. It is intentionally not a substitute for acquisition documentation, study design, measurement validation, or domain expertise.
</div>

<div class="gp-chip-row">
<span class="gp-chip">Imports</span>
<span class="gp-chip">Units + clocks</span>
<span class="gp-chip">QC + exclusions</span>
<span class="gp-chip">Events + alignment</span>
<span class="gp-chip">Models</span>
<span class="gp-chip">Reporting</span>
</div>

## Start with the shortest decision rule

| Situation | Decision rule | Go next |
|---|---|---|
| The CSV loads successfully | Treat parser success as **syntax evidence only** | [Bring your own export safely](guides/bring-your-own-export.md) |
| A column name looks familiar | Treat the name as a **mapping hypothesis**, not field meaning | [Signal and column glossary](guides/signal-column-glossary.md) |
| Time values are numeric | Establish unit, clock ownership, resets and monotonicity before timing claims | [Timebase and alignment](guides/timebase-alignment.md) |
| A sensor column is present | Verify activity, missingness, validity and acquisition provenance | [Validate a new dataset](guides/validate-dataset.md) |
| A QC function flags rows | Record evidence first; do not automatically delete observations | [QC & exclusion decision ledger](qc-exclusion-decision-ledger.md) |
| TTL/event values are detected | Verify the event codebook and clock relationship before assigning experimental meaning | [Timebase provenance](methods/timebase-provenance.md) |
| A model converges | Check analysis unit, grouping, estimand, diagnostics and generalisation target | [Choose a modelling strategy](guides/model-selection.md) |
| A biomarker changes by condition | Report the measured/derived feature; do not jump directly to a latent psychological state | [Interpretation guardrails](interpretation.md) |
| The results look publishable | Retain provenance, QC, settings, denominators, diagnostics and software identity | [Reporting and reproducibility](guides/reporting-reproducibility.md) |

## Importing and adapting data

### My file loads. Can I start analysing it?

**Not yet on that fact alone.** Successful import establishes that the file could be parsed into a table. It does not establish units, signal identity, participant/session structure, clock ownership, sampling behavior, event semantics, or sensor activity.

Use this sequence:

1. preserve the untouched source export;
2. define the study metadata and data dictionary;
3. record the source-to-standard column mapping;
4. validate timing, signal activity, missingness and events;
5. retain adaptation evidence with the analysis.

See [Study metadata and data dictionary](guides/study-metadata-data-dictionary.md), [Bring your own export safely](guides/bring-your-own-export.md), and [Validate a new dataset](guides/validate-dataset.md).

### Can gpbiometricspy infer what an unfamiliar column means from its name?

It can recognise documented aliases and help standardise names, but **recognition is not validation**. A field called `HR`, `IBI`, `GSR`, `TIME`, `TTL`, `FPOGX`, or similar still needs source documentation and empirical checks appropriate to the measurement.

The especially risky case is a familiar-looking label whose source meaning differs from the package convention. Review the [Signal and column glossary](guides/signal-column-glossary.md) before standardising.

### Should I rename columns in the original export?

Prefer **no**. Keep the raw/source export immutable and store the mapping separately. Standardised analysis tables can use package-friendly names, but the mapping must remain reviewable and reversible.

The checked [Bring your own export](guides/bring-your-own-export.md) example writes both source-like data and a mapping artifact rather than overwriting the original representation.

## Time, sampling and synchronization

### The time column increases. Is the timebase valid?

An increasing numeric column is useful evidence, but it is not enough. Confirm at least:

- the unit of the values;
- whether time is absolute, session-relative, trial-relative, device-relative, or reconstructed;
- whether it resets between segments;
- the relationship between time and row/sample counters;
- gaps, duplicate timestamps, negative steps and irregular intervals;
- the clock relationship when multiple devices or streams are aligned.

Use [Timebase and alignment](guides/timebase-alignment.md) and [Timebase provenance and multimodal alignment](methods/timebase-provenance.md).

### Can I assume the nominal hardware sampling rate is the observed sampling rate?

No. A nominal device rate is acquisition context, not proof of the realized intervals in a particular export. Audit the recorded timebase and report what was observed. If timing evidence is absent, state that limitation rather than reconstructing precision you cannot verify.

### Can I merge two streams because they both have seconds in a `TIME` column?

No. Matching units do not establish a shared clock origin, offset, drift, reset behavior, or synchronization event. Establish the clock relationship first, then decide whether correction, alignment and/or resampling is justified.

## Signal quality and QC

### A channel contains numbers and no missing values. Is it usable?

Not necessarily. A channel can be all zero, nearly constant, saturated, duplicated, stale, physiologically implausible, incorrectly scaled, or valid numerically but unrelated to the intended sensor. Check activity, variation, missingness/validity and source provenance before feature extraction.

Use [Validate a new dataset](guides/validate-dataset.md) and the relevant modality example under [Examples](examples/index.md).

### A QC check flagged a participant. Should I exclude them?

A QC flag is **evidence for review**, not automatically an exclusion rule. A defensible decision should state:

- what the issue was;
- which participant/session/trial/channel/window/rows it affected;
- the pre-specified or justified decision criterion;
- the action (`REVIEW`, `RETAIN`, or `EXCLUDE`);
- the denominator before and after the decision;
- the evidence artifact supporting it.

Use the [QC & exclusion decision ledger](qc-exclusion-decision-ledger.md).

### Should I interpolate every short dropout?

No universal rule is appropriate. Interpolation changes the data and its defensibility depends on the modality, gap duration, analysis target, neighboring evidence, acquisition context, and downstream method. Preserve the missingness evidence, state the interpolation rule explicitly, and perform sensitivity checks when the decision can affect inference.

### Can I drop all rows with any missing signal?

Usually that is too blunt for multimodal data. A missing channel may invalidate one modality-specific analysis without requiring deletion from every other analysis. Define the required evidence at the **analysis unit** you are actually modelling and retain modality-specific denominators.

## Events, AOIs and experimental meaning

### The package detected TTL transitions. Are those my experimental events?

They are candidate event records until you verify the acquisition codebook and the meaning of the values. Detection can establish where values changed; it does not establish what the experiment intended each code to mean.

### Can AOI dwell time be interpreted as attention?

AOI measures describe gaze behavior under the operational definitions used by the analysis. Stronger constructs such as attention, engagement, preference, credibility or persuasion require independent theoretical and measurement justification. Keep the reported claim at the level supported by the recorded and derived measure.

### Does a pupil increase mean cognitive load or arousal?

Not by itself. Pupil diameter is affected by multiple processes and acquisition conditions. Report the pupil measure, preprocessing, luminance/stimulus context where relevant, validity/QC, time window, baseline definition and statistical contrast. Any latent-state interpretation needs additional design and evidence.

See [Interpretation guardrails](interpretation.md).

## Cardiac and EDA questions

### I have an `HR` column. Can I compute HRV from it?

Do not assume so. HRV inference depends on an appropriate beat-to-beat interval source and provenance. A sampled heart-rate series is not interchangeable with verified IBI/RR intervals or a validated pulse waveform-derived interval series.

Use [Cardiac variability source provenance](methods/cardiac-source-provenance.md) before selecting an HRV workflow.

### I have a column named `HRV`. Is that already an HRV metric?

Do not infer metric meaning from the label alone. In some Gazepoint-style exports, familiar field names can represent validity/status information rather than the physiological metric suggested by the acronym. Verify source documentation and the [Signal and column glossary](guides/signal-column-glossary.md).

### Does an SCR candidate equal an emotional response?

No. A detected response is a signal-processing event under defined thresholds/algorithms. Linking it to a psychological construct or a specific stimulus requires temporal, experimental and theoretical evidence beyond the detection step.

## Modelling and inference

### Which row is my independent observation?

Often it is **not** the raw sample row. The inferential unit depends on the design and estimand: participant, trial, event, item, participant×item observation, window, or another defined unit. Samples nested within the same person or trial generally do not become independent simply because they occupy separate rows.

Before modelling, define:

1. the outcome and its measurement level;
2. the unit that contributes independent information to the target estimand;
3. repeated/nested/crossed grouping structures;
4. whether prediction is for seen or unseen participants/items/groups;
5. the validation split that matches that generalisation target.

Use [Choose a modelling strategy](guides/model-selection.md).

### Can I use random train/test row splits for participant data?

Only if row-level generalisation within already-seen groups is genuinely the target. If the intended claim concerns unseen participants, trials, sessions or items, the split must keep that generalisation unit disjoint. Otherwise leakage can make validation performance optimistic.

### A model has the best metric. Is it the best scientific explanation?

No. Predictive performance, model fit, variable importance and scientific explanation answer different questions. A model can predict well without identifying a causal mechanism, and an important predictor can reflect correlation, grouping, measurement structure or confounding.

### A result is statistically significant. Can I make a causal claim?

Significance does not create causal identification. Causal wording depends on design, randomization/intervention, estimand, assumptions and threats to identification—not the p-value alone.

## Reporting, review and reproducibility

### What should I save besides the final table and figure?

At minimum, retain the evidence needed to reconstruct important decisions:

- source/provenance information and mappings;
- study metadata and variable/event dictionaries;
- QC and timing diagnostics;
- exclusion/inclusion decisions and denominators;
- preprocessing and feature settings;
- event/AOI definitions;
- model formula/configuration and grouping structure;
- validation/split definition for predictive work;
- software/package identity;
- generated result tables/figures and a manifest tying them together.

Use [Reporting and reproducibility](guides/reporting-reproducibility.md).

### What should a reviewer inspect first?

A concise route is:

1. [Parity & validation](parity.md);
2. [Deep validation](deep-validation.md);
3. [Private real-data validation](real-data-validation.md);
4. [Measurement accountability](measurement-accountability.md);
5. [QC & exclusion decision ledger](qc-exclusion-decision-ledger.md);
6. [Interpretation guardrails](interpretation.md).

These pages separate software-validation evidence from study-level scientific claims.

### How should I cite the package?

Use the stable archival/software citation information on [Citation & archival](citation.md). When reporting a study, also record the exact package version/commit used for the analysis if reproducibility depends on a development snapshot.

## If you are still unsure

<div class="gp-route-grid" data-faq-next-routes>
<a class="gp-route-card" href="../learning-paths/"><span class="gp-route-label">Route me</span><h3>Choose a learning path</h3><p>Pick tutorial, how-to, reference or explanation routes by task and role.</p></a>
<a class="gp-route-card" href="../guides/troubleshooting/"><span class="gp-route-label">Diagnose</span><h3>Use the troubleshooting playbook</h3><p>Move from symptom to evidence before changing scientific parameters.</p></a>
<a class="gp-route-card" href="../guides/validate-dataset/"><span class="gp-route-label">Validate</span><h3>Audit a new dataset</h3><p>Check schema, timing, activity, validity, missingness and events before analysis.</p></a>
<a class="gp-route-card" href="../interpretation/"><span class="gp-route-label">Interpret</span><h3>Check claim boundaries</h3><p>Separate measured signals, derived features, statistical associations and stronger substantive claims.</p></a>
</div>

<div class="gp-science-boundary">
<strong>Boundary.</strong> gpbiometricspy can help make transformations, diagnostics, settings and provenance explicit. It cannot infer undocumented acquisition facts, validate a sensor from column names alone, convert physiological or gaze measures into direct proof of latent psychological states, or make a study design causal by software operation.
</div>
