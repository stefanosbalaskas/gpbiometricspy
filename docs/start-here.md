# Start here

<div class="gp-page-intro">
Choose the path that matches what you are trying to do. This page is intentionally task-first: it routes new users to a successful first analysis, experienced researchers to the right workflow, and reviewers or collaborators to the validation evidence behind the package.
</div>

<div class="gp-chip-row">
<span class="gp-chip">Stable 0.1.6</span>
<span class="gp-chip">Development 0.1.7.dev0</span>
<span class="gp-chip">406 / 406 frozen exports</span>
<span class="gp-chip">Python 3.11–3.14</span>
<span class="gp-chip">Synthetic-first examples</span>
</div>

## Pick your route

<div class="gp-route-grid">

<a class="gp-route-card" href="guides/first-analysis/">
<span class="gp-route-label">New user</span>
<h3>Run a complete first analysis</h3>
<p>Install the package, load the bundled synthetic dataset, inspect signals, run QC, create plots, and keep a reproducible record.</p>
</a>

<a class="gp-route-card" href="workflows/">
<span class="gp-route-label">Research workflow</span>
<h3>Start from the data you recorded</h3>
<p>Choose EDA/SCR, PPG/HRV, pupil/gaze/AOI, multimodal alignment, QC/reporting, or interoperability and follow the shortest defensible path.</p>
</a>

<a class="gp-route-card" href="studio/">
<span class="gp-route-label">Visual workflow</span>
<h3>Use gpbiometricspy Studio</h3>
<p>Work through project, quality, analysis, alignment, modelling, and reporting in a guided application backed by the same scientific package functions.</p>
</a>

<a class="gp-route-card" href="guides/validate-dataset/">
<span class="gp-route-label">Bring your own data</span>
<h3>Validate a new dataset before analysis</h3>
<p>Check schema, sampling, missingness, resets, source provenance, event structure, and cross-stream timing before deriving substantive results.</p>
</a>

<a class="gp-route-card" href="guides/model-selection/">
<span class="gp-route-label">Statistics</span>
<h3>Choose a modelling strategy</h3>
<p>Compare grouped predictive models with hierarchical location–scale families, robust variants, random slopes, and crossed participant–item structures.</p>
</a>

<a class="gp-route-card" href="parity/">
<span class="gp-route-label">Reviewer / auditor</span>
<h3>Inspect validation and scientific boundaries</h3>
<p>Trace frozen R parity, deep validation, private real-data smoke testing, measurement accountability, and explicit interpretation guardrails.</p>
</a>

</div>

!!! note "One scientific engine, several interfaces"
    Studio, the Python API, executable tutorials, generated figures, and documentation examples all point back to the same package implementation. The visual application is not a second statistical codebase.

## The research path in one view

```mermaid
graph LR
  A[Acquire / export] --> B[Ingest + schema]
  B --> C[Quality + provenance]
  C --> D[Process signals]
  D --> E[Align events / streams]
  E --> F[Summarise / model]
  F --> G[Report + archive]
  C -. fail closed .-> H[Review acquisition or preprocessing]
  E -. timing uncertainty .-> H
```

<div class="gp-decision">
<strong>Default rule:</strong> do not move downstream merely because a function returns a result. Move downstream when the evidence needed for the next scientific claim has been checked and retained.
</div>

## What should I read next?

| Goal | Best next page | Why |
|---|---|---|
| Learn by doing | [First analysis](guides/first-analysis.md) | A short successful path using bundled synthetic data. |
| Work with a specific signal | [Workflow map](workflows.md) | Routes by EDA, PPG/HRV, pupil/gaze, events, or external tools. |
| See outputs before reading code | [Plot gallery](plot-gallery.md) | Generated figures from the package's plotting surface. |
| Understand the design philosophy | [Research pipeline blueprint](articles/python-native/research-pipeline-blueprint.md) | Explains why QC, provenance, processing, modelling, and reporting are separate layers. |
| Find a function | [API browser](api/index.md) | Domain-organized entry point to the complete 406-function reference. |
| Choose a hierarchical model | [Modelling strategy guide](guides/model-selection.md) | Compares the current Python-native modelling families and their boundaries. |
| Prepare a paper or supplement | [Reporting and reproducibility](guides/reporting-reproducibility.md) | Lists the evidence worth retaining and reporting. |

## Three principles that prevent most workflow mistakes

<div class="gp-guide-grid">
<div class="gp-guide-card">
<span class="gp-eyebrow">1 · Measurement</span>
<h3>Validate before transforming</h3>
<p>Sampling rate, timebase, missingness, interval identity, event coverage, and source provenance constrain what later analyses can mean.</p>
</div>
<div class="gp-guide-card">
<span class="gp-eyebrow">2 · Design</span>
<h3>Respect the unit of generalisation</h3>
<p>Repeated observations, participants, items, trials, and unseen groups require different validation splits and different model semantics.</p>
</div>
<div class="gp-guide-card">
<span class="gp-eyebrow">3 · Reporting</span>
<h3>Keep the evidence trail</h3>
<p>Retain QC outputs, settings, software versions, plots, exclusions, timing evidence, and model certificates rather than only a final feature table.</p>
</div>
</div>

## Scientific boundary

<div class="gp-science-boundary">
The package measures, processes, audits, aligns, summarises, predicts, and models recorded signals. Those operations do not by themselves establish emotion, stress, trust, preference, cognition, diagnosis, sensor validity, or causal effects. Use the interpretation supported by the study design and measurement evidence, not the label of a software function.
</div>
