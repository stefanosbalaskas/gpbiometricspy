# Guides

<div class="gp-page-intro">
The guides are organized by user need rather than package module. Tutorials help you learn by completing a safe workflow; how-to guides help you accomplish a concrete research task; explanation pages connect the scientific design decisions behind the API.
</div>

<div class="gp-guide-grid">

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
| I want to use the package end to end | Hands-on tutorial | [Data to report](hands-on-eda-research.md) |
| I want a shorter first tour | Tutorial | [First analysis](first-analysis.md) |
| I have a research task to complete | How-to | [Workflow map](../workflows.md) and the guides above |
| I need exact function behavior | Reference | [API browser](../api/index.md) |
| I need to understand why the workflow is structured this way | Explanation | [Python-native articles](../articles/python-native/index.md) |
| I need validation evidence | Evidence | [Parity & validation](../parity.md) and [Deep validation](../deep-validation.md) |

## Safe defaults

- Start from bundled synthetic/public demonstration data when learning or testing a pipeline.
- Treat QC and provenance as evidence-producing stages, not hidden preprocessing details.
- Hold out whole groups when the scientific target is generalisation to unseen groups.
- Keep conditional predictions for observed participants/items separate from population predictions for unseen levels.
- Report timing uncertainty and source identity explicitly when multimodal or cardiac measures depend on them.
- Prefer a simpler model whose assumptions you can defend over a richer model whose latent structure is weakly identified.
