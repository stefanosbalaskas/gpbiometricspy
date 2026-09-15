<div class="gp-landing-hero" markdown>

<span class="gp-kicker">Scientific Python + a guided research application</span>

# From recorded signals to auditable research results.

**gpbiometricspy** combines a validated Python scientific engine with **gpbiometricspy Studio**, a guided interface for Gazepoint eye-tracking, EDA/SCR, PPG/HRV, pupil, gaze, AOI, event-alignment and multimodal workflows.

Start from the research task you need to complete—not from a list of functions.

<div class="gp-actions">
<a class="md-button md-button--primary" href="start-here/">Start here</a>
<a class="md-button" href="studio/">Open the Studio guide</a>
<a class="md-button" href="workflows/">Choose a workflow</a>
<a class="md-button" href="plot-gallery/">Explore generated plots</a>
</div>

</div>

<div class="gp-status-grid gp-status-grid-home">
<div><span class="gp-status-value">0.1.6</span><span class="gp-status-label">stable release</span></div>
<div><span class="gp-status-value">0.1.7.dev0</span><span class="gp-status-label">development line</span></div>
<div><span class="gp-status-value">406 / 406</span><span class="gp-status-label">frozen R exports implemented</span></div>
<div><span class="gp-status-value">850 / 850</span><span class="gp-status-label">exact-main tests</span></div>
<div><span class="gp-status-value">99.7353%</span><span class="gp-status-label">exact-main raw branch coverage</span></div>
<div><span class="gp-status-value">14 / 14</span><span class="gp-status-label">exact-main workflow families green</span></div>
</div>

## Start from your research task

<div class="gp-route-grid">

<a class="gp-route-card" href="guides/first-analysis/">
<span class="gp-route-label">First analysis</span>
<h3>Learn the full path on synthetic data</h3>
<p>Install the package, inspect channels, run QC, generate plots and retain a reproducible record before bringing in study data.</p>
</a>

<a class="gp-route-card" href="guides/validate-dataset/">
<span class="gp-route-label">New dataset</span>
<h3>Validate measurement before analysis</h3>
<p>Audit schema, sampling, missingness, timing, provenance and event structure before deriving scientific features or models.</p>
</a>

<a class="gp-route-card" href="workflows/">
<span class="gp-route-label">Signal workflow</span>
<h3>Analyze what you recorded</h3>
<p>Choose EDA/SCR, PPG/HRV, pupil/gaze/AOI, multimodal alignment, QC/reporting or interoperability.</p>
</a>

<a class="gp-route-card" href="guides/timebase-alignment/">
<span class="gp-route-label">Multimodal study</span>
<h3>Align events and streams defensibly</h3>
<p>Separate clock correction from resampling, inspect drift and gaps, and retain explicit timing provenance.</p>
</a>

<a class="gp-route-card" href="guides/model-selection/">
<span class="gp-route-label">Statistics</span>
<h3>Choose a model that matches the design</h3>
<p>Compare grouped predictive models with hierarchical location–scale, robust, random-slope and crossed participant–item families.</p>
</a>

<a class="gp-route-card" href="deep-validation/">
<span class="gp-route-label">Reviewer / auditor</span>
<h3>Inspect the evidence behind the package</h3>
<p>Trace frozen parity, exact-main coverage, real-data smoke testing, cross-toolbox validation and interpretation boundaries.</p>
</a>

</div>

## One research path, two interfaces

Studio and the Python API call the same package implementation. Use the visual application when you want a guided workflow; use Python when you need scripts, notebooks, automation or custom integrations.

<div class="gp-flow gp-flow-product">
<div><strong>01</strong><span>Project</span><small>Import or generate data and identify channels.</small></div>
<div><strong>02</strong><span>Quality</span><small>Check schema, validity, missingness and provenance.</small></div>
<div><strong>03</strong><span>Analyze</span><small>Process EDA, cardiac, pupil, gaze, fixation and AOIs.</small></div>
<div><strong>04</strong><span>Align</span><small>Connect events, clocks, streams and experimental structure.</small></div>
<div><strong>05</strong><span>Model</span><small>Choose guarded statistics that respect the generalisation unit.</small></div>
<div><strong>06</strong><span>Report</span><small>Export results, diagnostics, provenance and replay information.</small></div>
</div>

<div class="gp-actions">
<a class="md-button md-button--primary" href="studio/">Use Studio</a>
<a class="md-button" href="getting-started/">Use the Python API</a>
</div>

## See the evidence, not only the output

Every figure below is generated from the checked-out Python package during documentation CI using bundled synthetic/public demonstration data.

<div class="gp-visual-grid">
<figure>
<img src="assets/generated/multimodal-timeline.png" alt="Aligned multimodal timeline showing EDA heart-rate pupil and event markers" loading="lazy" decoding="async">
<figcaption><strong>Multimodal alignment.</strong> Signals and events on an explicit shared analysis timebase.</figcaption>
</figure>
<figure>
<img src="assets/generated/eda-decomposition.png" alt="Electrodermal activity trace decomposed into tonic and phasic components" loading="lazy" decoding="async">
<figcaption><strong>EDA decomposition.</strong> Intermediate signal-processing evidence remains visible.</figcaption>
</figure>
<figure>
<img src="assets/generated/pupil-gaze-overview.png" alt="Pupil diameter and gaze coordinate overview for a synthetic participant" loading="lazy" decoding="async">
<figcaption><strong>Pupil and gaze.</strong> Measured and derived eye-tracking channels inspected together.</figcaption>
</figure>
<figure>
<img src="assets/generated/ppg-poincare.png" alt="Poincare plot of successive beat-to-beat intervals" loading="lazy" decoding="async">
<figcaption><strong>Beat-to-beat geometry.</strong> Cardiac variability visualisation with provenance-sensitive interpretation.</figcaption>
</figure>
</div>

<p class="gp-center-link"><a href="plot-gallery/"><strong>Browse all 17 deterministically generated figures →</strong></a></p>

## Choose the analysis layer

<div class="gp-card-grid gp-card-grid-compact">

<a class="gp-card gp-card-link" href="measurement-accountability/">
<span class="gp-card-icon">✓</span>
<h3>Measurement + provenance</h3>
<p>Sampling, timebase, cardiac-source identity, validity, missingness, QC and interpretation constraints come before modelling.</p>
<span class="gp-card-cta">Check measurement evidence →</span>
</a>

<a class="gp-card gp-card-link" href="workflows/">
<span class="gp-card-icon">∿</span>
<h3>Signal workflows</h3>
<p>EDA/SCR, PPG/HRV, pupil, gaze, fixation, AOIs, events, synchronization and multimodal summaries.</p>
<span class="gp-card-cta">Choose a signal workflow →</span>
</a>

<a class="gp-card gp-card-link" href="methods/grouped-mixed-boosting/">
<span class="gp-card-icon">↗</span>
<h3>Grouped prediction</h3>
<p>Continuous and ordinal grouped boosting with whole-group validation and explicit seen-versus-unseen group semantics.</p>
<span class="gp-card-cta">Explore predictive methods →</span>
</a>

<a class="gp-card gp-card-link" href="methods/">
<span class="gp-card-icon">Σ</span>
<h3>Distributional modelling</h3>
<p>Gaussian, robust Student-t, random-slope and crossed participant–item location–scale models with reproducibility certificates.</p>
<span class="gp-card-cta">Compare Python-native methods →</span>
</a>

</div>

## Validation is part of the product

<div class="gp-metric-grid">
<div class="gp-metric-card"><strong>850 / 850</strong><span>exact-main tests</span></div>
<div class="gp-metric-card"><strong>15,171 / 15,171</strong><span>statements exercised</span></div>
<div class="gp-metric-card"><strong>7,159 / 7,178</strong><span>raw branches covered = 99.7353%</span></div>
<div class="gp-metric-card"><strong>19</strong><span>audited structural/caller-dominated residual arcs</span></div>
<div class="gp-metric-card"><strong>0 / 0 / 0</strong><span>unexpected / stale / unaudited branch debt</span></div>
<div class="gp-metric-card"><strong>406 / 406</strong><span>frozen gpbiometrics 2.0.0 exports implemented</span></div>
<div class="gp-metric-card"><strong>12 / 12</strong><span>platform/Python test lanes green</span></div>
<div class="gp-metric-card"><strong>14 / 14</strong><span>optional-backend interoperability lanes green</span></div>
</div>

The current scientific development baseline is PR **#136**, exact-main SHA **`e761a931b00e646d6f12be3475a68cd524803893`**. It adds crossed participant–item **joint location and log-scale random slopes** while leaving the frozen R-parity surface unchanged. All **14/14 post-merge workflow families** are green; Branch Coverage #412 evidence is artifact **10389944415**, SHA-256 `9cc448013e4be26caf22de120089ba649c928aee0989728fdbf77e5409528abf`. Formal checkpoint: PR #136 comment **5678239576**.

[Inspect parity, exact-main evidence and validation layers →](deep-validation.md)

!!! info "Scientific boundary"
    Physiological and eye-tracking signals are measurements, not direct proof of emotion, stress, trust, preference, cognition, health status or diagnosis. Random effects and random slopes describe modelled heterogeneity; predictive importance is not causal importance; provenance certificates bind declared evidence rather than proving sensor validity. Scientific interpretation remains constrained by acquisition quality, study design and model assumptions.

## Stable release versus development line

Stable **gpbiometricspy 0.1.6** remains an immutable release line from **11 September 2026**, with **641 core tests**, **10,456/10,456 statements**, and **5,629/5,648 raw branches = 99.6636%** at release qualification. Development metrics above describe post-release work and do not retroactively change the 0.1.6 artifacts.

<div class="gp-mini-grid">
<a href="start-here/">Start here</a>
<a href="studio/">Studio application</a>
<a href="workflows/">Workflow map</a>
<a href="methods/">Methods</a>
<a href="articles/">Articles</a>
<a href="api/">API by domain</a>
<a href="plot-gallery/">Plot gallery</a>
<a href="integrations/">Integrations</a>
<a href="citation/">Citation + archival record</a>
<a href="development/">Development</a>
</div>