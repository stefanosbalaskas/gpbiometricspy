---
description: Goal-oriented learning paths for gpbiometricspy tutorials, task guides, reference material, explanations, modality workflows, and validation evidence.
search:
  boost: 1.4
---

# Learning paths

<div class="gp-page-intro">
Use this page when you know **what kind of help you need** but not which gpbiometricspy page to open. The documentation intentionally separates worked learning, task completion, factual reference, and scientific explanation so a tutorial does not have to double as an API manual and a reference page does not pretend to be a research workflow.
</div>

<div class="gp-chip-row">
<span class="gp-chip">Learn by doing</span>
<span class="gp-chip">Solve a task</span>
<span class="gp-chip">Look up facts</span>
<span class="gp-chip">Understand why</span>
<span class="gp-chip">Evidence first</span>
</div>

## Choose the kind of help you need

<div class="gp-route-grid" data-learning-intent-grid>

<a class="gp-route-card" data-learning-intent="tutorial" href="../guides/first-analysis/">
<span class="gp-route-label">Learn by doing</span>
<h3>Follow a worked path</h3>
<p>Start with bundled synthetic data, complete a successful analysis, then move to the full hands-on workflow and generated outputs.</p>
</a>

<a class="gp-route-card" data-learning-intent="how-to" href="../guides/">
<span class="gp-route-label">Solve a task</span>
<h3>Use a goal-oriented guide</h3>
<p>Set up a project, define metadata, adapt an export, validate a dataset, align clocks, troubleshoot problems, choose a model, or prepare reproducible reporting.</p>
</a>

<a class="gp-route-card" data-learning-intent="reference" href="../api/">
<span class="gp-route-label">Look up facts</span>
<h3>Use concise reference material</h3>
<p>Find function signatures, domain APIs, signal and column semantics, integration surfaces, citation details, and the complete frozen export reference.</p>
</a>

<a class="gp-route-card" data-learning-intent="explanation" href="../articles/python-native/">
<span class="gp-route-label">Understand why</span>
<h3>Read the reasoning behind the workflow</h3>
<p>Understand measurement-before-modelling, research-pipeline design, reproducible multimodal studies, model choice, and the scientific boundaries behind package decisions.</p>
</a>

</div>

## New to the package

Use this sequence when the immediate goal is to become productive without starting from the 406-function reference.

1. **[First analysis](guides/first-analysis.md)** — get a small, successful synthetic workflow running.
2. **[Hands-on EDA research guide](guides/hands-on-eda-research.md)** — see QC, signal processing, event candidates, plots, exports and reporting evidence in one connected analysis.
3. **[Workflow map](workflows.md)** — switch from the teaching example to the modality or task you actually recorded.
4. **[Plot gallery](plot-gallery.md)** — inspect generated outputs and the analyses that create them.
5. **[API by domain](api/index.md)** — move to exact function-level reference only when implementation detail is needed.

<div class="gp-decision">
<strong>Learning rule:</strong> reproduce the bundled example before replacing inputs. A successful run on your own file is not evidence that units, clocks, channel activity, event meaning or provenance were interpreted correctly.
</div>

## Starting a real research project

For new or unfamiliar data, use the provenance-first onboarding sequence rather than jumping directly into preprocessing.

<div class="gp-steps" data-real-data-learning-path>
<div class="gp-step"><strong>1 · Project</strong><a href="../guides/research-project-scaffold/">Create the project scaffold</a> so raw data, metadata, mappings, QC, events, derived outputs, models and reports remain separate.</div>
<div class="gp-step"><strong>2 · Define</strong><a href="../guides/study-metadata-data-dictionary/">Define study metadata and the data dictionary</a>, including roles, units, identifiers, clocks, provenance and event semantics.</div>
<div class="gp-step"><strong>3 · Adapt</strong><a href="../guides/bring-your-own-export/">Adapt the export without hiding provenance</a> and preserve the source-to-standard mapping.</div>
<div class="gp-step"><strong>4 · Validate</strong><a href="../guides/validate-dataset/">Validate the dataset</a> for schema, timing, activity, missingness, resets and event coverage.</div>
<div class="gp-step"><strong>5 · Decide</strong><a href="../qc-exclusion-decision-ledger/">Review QC and exclusion decisions</a> with explicit scope and denominator consequences.</div>
<div class="gp-step"><strong>6 · Analyze</strong><a href="../workflows/">Choose the modality workflow</a> only after the evidence required by the next claim is defensible.</div>
<div class="gp-step"><strong>7 · Report</strong><a href="../guides/reporting-reproducibility/">Retain settings, diagnostics, provenance and replay information</a> with the scientific results.</div>
</div>

## Choose by research domain

| You are working on… | Start here | Then inspect | Before interpretation |
|---|---|---|---|
| EDA / GSR / SCR | [EDA / GSR / SCR example](examples/eda-scr.md) | [Hands-on EDA research](guides/hands-on-eda-research.md) | [Measurement accountability](measurement-accountability.md) |
| PPG / HR / IBI / HRV | [PPG / HRV example](examples/ppg-hrv.md) | [Cardiac source provenance](methods/cardiac-source-provenance.md) | [Interpretation guardrails](interpretation.md) |
| Pupil / gaze / fixation / AOI | [Pupil / gaze / AOI example](examples/pupil-gaze.md) | [Eye-tracking ecosystem bridges](articles/eye-tracking-ecosystem-bridges.md) | [Measurement accountability](measurement-accountability.md) |
| Event-linked multimodal data | [Multimodal example](examples/multimodal.md) | [Timebase and alignment guide](guides/timebase-alignment.md) | [Timebase provenance](methods/timebase-provenance.md) |
| External tool interoperability | [Interoperability example](examples/interoperability.md) | [Integrations](integrations.md) | [Interoperability version testing](articles/interoperability-version-testing.md) |
| Grouped prediction | [Modelling strategy guide](guides/model-selection.md) | [Grouped mixed-effects boosting](methods/grouped-mixed-boosting.md) | [Interpretation guardrails](interpretation.md) |
| Hierarchical variability models | [Methods overview](methods/index.md) | [Choosing a location–scale model](articles/python-native/model-selection-location-scale.md) | [Interpretation guardrails](interpretation.md) |

## Choose by role

### Researcher bringing new data

Use **Project → Define → Adapt → Validate → Decide → Analyze → Report**. Keep source files immutable, write down field meaning before code depends on it, and separate QC evidence from exclusion decisions.

### Researcher reproducing or extending an analysis

Start from the **[end-to-end runnable EDA example](examples/end-to-end-eda.md)** and **[reporting/reproducibility guide](guides/reporting-reproducibility.md)**. Reuse explicit settings and manifests instead of reconstructing analysis choices from figures alone.

### Reviewer, collaborator or auditor

Read **[Parity & validation](parity.md)**, **[Deep validation](deep-validation.md)**, **[Private real-data validation](real-data-validation.md)**, **[QC & exclusion decision ledger](qc-exclusion-decision-ledger.md)**, **[Measurement accountability](measurement-accountability.md)** and **[Interpretation guardrails](interpretation.md)**. These pages are the shortest path to what the package claims, how those claims are tested, and where they stop.

### Developer or advanced integrator

Use **[API by domain](api/index.md)**, **[Complete 406-function reference](api/reference.md)**, **[Integrations](integrations.md)** and **[Development](development.md)**. The tutorial layer is useful for context, but implementation work should be anchored to the reference and validation contracts.

## Common question → best page

| Question | Best page |
|---|---|
| “What should I do first?” | [Start here](start-here.md) |
| “How should I structure a new study project?” | [Research project scaffold](guides/research-project-scaffold.md) |
| “What does this field mean?” | [Signal and column glossary](guides/signal-column-glossary.md) |
| “How do I document units, clocks and event labels?” | [Study metadata and data dictionary](guides/study-metadata-data-dictionary.md) |
| “How do I adapt an unfamiliar export?” | [Bring your own export safely](guides/bring-your-own-export.md) |
| “Is this dataset ready to analyze?” | [Validate a new dataset](guides/validate-dataset.md) |
| “A QC check failed—what now?” | [Troubleshooting and diagnostics](guides/troubleshooting.md) |
| “Should I remove these rows or participants?” | [QC & exclusion decision ledger](qc-exclusion-decision-ledger.md) |
| “How do I align events or modalities?” | [Timebase and alignment](guides/timebase-alignment.md) |
| “Which model family fits my design?” | [Choose a modelling strategy](guides/model-selection.md) |
| “How should I report this analysis?” | [Reporting and reproducibility](guides/reporting-reproducibility.md) |
| “Which exact function do I need?” | [API by domain](api/index.md) |
| “What evidence supports package parity?” | [Deep validation](deep-validation.md) |
| “What claims should I avoid?” | [Interpretation guardrails](interpretation.md) |

## Do not treat the documentation types as interchangeable

A **tutorial** is allowed to make choices for a controlled teaching example. A **how-to guide** assumes you already have a concrete goal. **Reference** describes the software and its interfaces. **Explanation** discusses why the scientific workflow is designed as it is. Crossing those purposes carelessly creates two common errors: copying tutorial defaults into a study without review, or treating a concise API description as scientific justification for a measurement claim.

<div class="gp-science-boundary">
No documentation route changes the evidence requirement. Column names do not establish units; parser success does not establish clock ownership; non-missing values do not establish signal quality; detected events do not establish psychological meaning; model fit does not establish causality; and software validation does not substitute for study-level measurement validity.
</div>
