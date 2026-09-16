# Guides

<div class="gp-page-intro">
The guides are organized by user need rather than package module. Tutorials help you learn by completing a safe workflow; how-to guides help you accomplish a concrete research task; explanation pages connect the scientific design decisions behind the API.
</div>

<div class="gp-guide-grid">

<div class="gp-guide-card" data-learning-route="workflow-selection">
<span class="gp-eyebrow">Decision guide</span>
<h3><a href="#choose-your-workflow">Choose a research workflow</a></h3>
<p>Start from the evidence you actually have, identify the next defensible stage, and move into the relevant guide, example, method page, or API lens.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">Hands-on tutorial</span>
<h3><a href="hands-on-eda-research/">Use the package from data to report</a></h3>
<p>Run a complete EDA/SCR analysis with real package calls, inspect every QC and processing object, save tables and figures, and learn how to substitute your own export.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">Tutorial</span>
<h3><a href="first-analysis/">First analysis</a></h3>
<p>Go from installation to QC, generated figures, and a reproducible workflow using bundled synthetic data.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">How-to</span>
<h3><a href="validate-dataset/">Validate a new dataset</a></h3>
<p>Run schema, timing, missingness, signal, event, and provenance checks before substantive analysis.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">How-to</span>
<h3><a href="timebase-alignment/">Timebase and alignment</a></h3>
<p>Separate nominal sampling claims from observed timing evidence and align streams without overstating synchronization accuracy.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">How-to</span>
<h3><a href="reporting-reproducibility/">Reporting and reproducibility</a></h3>
<p>Retain the settings, QC evidence, software identity, figures, and provenance needed to reproduce and review an analysis.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">Decision guide</span>
<h3><a href="model-selection/">Choose a modelling strategy</a></h3>
<p>Match continuous or ordinal outcomes, grouping structures, heavy tails, random slopes, and prediction targets to the current method families.</p>
</div>

<div class="gp-guide-card">
<span class="gp-eyebrow">Reference route</span>
<h3><a href="../api/">Browse the API</a></h3>
<p>Use the domain browser when you already know the operation you need and want precise signatures rather than a workflow narrative.</p>
</div>

</div>

## Documentation map

| Need | Documentation type | Start here |
|---|---|---|
| I do not yet know which workflow fits | Decision guide | [Choose your workflow](#choose-your-workflow) |
| I want to use the package end to end | Hands-on tutorial | [Data to report](hands-on-eda-research.md) |
| I want a shorter first tour | Tutorial | [First analysis](first-analysis.md) |
| I have a research task to complete | How-to | [Workflow map](../workflows.md) and the guides above |
| I need exact function behavior | Reference | [API browser](../api/index.md) |
| I need to understand why the workflow is structured this way | Explanation | [Python-native articles](../articles/python-native/index.md) |
| I need validation evidence | Evidence | [Parity & validation](../parity.md) and [Deep validation](../deep-validation.md) |

## Choose your workflow

<div class="gp-decision">
<strong>Choose from evidence, not from a function name.</strong> Start with what is physically recorded and what the research question requires. Move forward only when the current stage has produced enough evidence to justify the next one.
</div>

| What you have now | First question | Recommended route | Evidence to retain |
|---|---|---|---|
| A new or unfamiliar Gazepoint export | Are schema, units, timing, missingness and channel identity defensible? | [Validate a new dataset](validate-dataset.md) | schema/QC tables, source identity, timebase evidence |
| EDA/GSR waveform | Is the conductance signal usable before decomposition or event detection? | [EDA / GSR / SCR example](../examples/eda-scr.md) | unit audit, signal QC, decomposition settings, candidate-event criteria |
| PPG waveform or IBI/RR series | What is the source of each interval and are rejected beats visible? | [PPG / HRV example](../examples/ppg-hrv.md) | source provenance, peak/interval QC, rejection rules |
| Pupil, gaze, fixation or AOI fields | Which columns are measured, derived, validity-coded or interpolated? | [Pupil / gaze / AOI example](../examples/pupil-gaze.md) | validity/missingness evidence, preprocessing choices, AOI definitions |
| TTL/task events or multiple sensor streams | Which clock owns each timestamp and what alignment evidence exists? | [Timebase and alignment](timebase-alignment.md) then [Multimodal example](../examples/multimodal.md) | event identity, clock mapping, offsets/drift, overlap and residuals |
| Analysis-ready repeated observations | What is the scientific generalisation unit and prediction target? | [Choose a modelling strategy](model-selection.md) | grouping structure, holdout unit, model assumptions, uncertainty |
| Completed analysis | Can another researcher replay the decisions and inspect QC? | [Reporting and reproducibility](reporting-reproducibility.md) | software identity, settings, exclusions, figures, tables, provenance |
| An external analysis ecosystem | What representation and metadata does the downstream tool require? | [Interoperability example](../examples/interoperability.md) | explicit conversion, version identity, retained source columns |

### Seven-stage decision sequence

<div class="gp-steps" data-research-decision-flow>
<div class="gp-step" data-research-decision-stage="project"><strong>Project</strong>Identify the study unit, files, channels, events, participants/items and intended inferential target.</div>
<div class="gp-step" data-research-decision-stage="quality"><strong>Quality</strong>Establish schema, units, missingness, signal activity, timebase and provenance before deriving measures.</div>
<div class="gp-step" data-research-decision-stage="analyze"><strong>Analyze</strong>Use modality-specific processing only after the recorded source and QC evidence are explicit.</div>
<div class="gp-step" data-research-decision-stage="align"><strong>Align</strong>Resolve event identity and clock relationships before creating event-relative or multimodal quantities.</div>
<div class="gp-step" data-research-decision-stage="summarise"><strong>Summarise</strong>Create analysis-ready features while retaining denominators, event coverage and QC context.</div>
<div class="gp-step" data-research-decision-stage="model"><strong>Model</strong>Match the design, grouping structure, prediction target and uncertainty model to the scientific question.</div>
<div class="gp-step" data-research-decision-stage="report"><strong>Report</strong>Export results together with diagnostics, settings, provenance and replay information.</div>
</div>

### Visual checkpoints

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#signal-overview-and-quality"><img src="../assets/generated/biometric-signals.png" alt="Standardised biometric signal overview"><div class="gp-visual-card-body"><strong>Before analysis</strong><span>Confirm that recorded channels are visible and inspectable before deriving features.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#multimodal-alignment"><img src="../assets/generated/multimodal-timeline.png" alt="Aligned multimodal timeline with event markers"><div class="gp-visual-card-body"><strong>Before event-locked inference</strong><span>Inspect streams and event markers on an explicit shared timeline.</span></div></a>
</div>

### Stop rather than guess

Do not advance a workflow merely because a function can run. Stop and resolve the evidence gap when the timebase is ambiguous, the signal source is unknown, event coverage is incomplete, a denominator has changed silently, or the grouping structure does not support the intended generalisation. The package should make those decisions inspectable rather than conceal them behind a successful return value.

!!! tip "Need a concrete starting script?"
    Open [Examples](../examples/index.md#worked-research-recipes) for short, verified research recipes that connect TTL events, multimodal summaries, AOI dwell and visual timeline checks.

## Safe defaults

- Start from bundled synthetic/public demonstration data when learning or testing a pipeline.
- Treat QC and provenance as evidence-producing stages, not hidden preprocessing details.
- Hold out whole groups when the scientific target is generalisation to unseen groups.
- Keep conditional predictions for observed participants/items separate from population predictions for unseen levels.
- Report timing uncertainty and source identity explicitly when multimodal or cardiac measures depend on them.
- Prefer a simpler model whose assumptions you can defend over a richer model whose latent structure is weakly identified.
