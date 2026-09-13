<div class="gp-landing-hero" markdown>

<span class="gp-kicker">Scientific Python + a guided research application</span>

# From raw Gazepoint data to reproducible analysis.

**gpbiometricspy** gives researchers two ways to work with the same validated scientific engine: use **gpbiometricspy Studio** for a guided visual workflow, or use the **Python API** for scripts, notebooks, pipelines and custom integrations.

<div class="gp-actions">
<a class="md-button md-button--primary" href="studio/">Start with Studio</a>
<a class="md-button" href="getting-started/">Use the Python API</a>
<a class="md-button" href="workflows/">Choose a workflow</a>
<a class="md-button" href="methods/">Explore methods</a>
<a class="md-button" href="plot-gallery/">See generated plots</a>
</div>

</div>

<div class="gp-status-grid">
<div><span class="gp-status-value">0.1.6</span><span class="gp-status-label">stable release</span></div>
<div><span class="gp-status-value">0.1.7.dev0</span><span class="gp-status-label">development head</span></div>
<div><span class="gp-status-value">406 / 406</span><span class="gp-status-label">frozen R exports implemented</span></div>
<div><span class="gp-status-value">694 / 694</span><span class="gp-status-label">exact-main tests</span></div>
<div><span class="gp-status-value">100%</span><span class="gp-status-label">exact-main statement coverage</span></div>
<div><span class="gp-status-value">99.6795%</span><span class="gp-status-label">exact-main raw branch coverage</span></div>
<div><span class="gp-status-value">90 / 90</span><span class="gp-status-label">random-slope module branches</span></div>
<div><span class="gp-status-value">19</span><span class="gp-status-label">audited structural arcs</span></div>
<div><span class="gp-status-value">0 / 0 / 0</span><span class="gp-status-label">unexpected / stale / unaudited branch debt</span></div>
<div><span class="gp-status-value">3.11–3.14</span><span class="gp-status-label">supported Python</span></div>
</div>

## Choose how you want to work

<div class="gp-card-grid gp-card-grid-compact">

<a class="gp-card gp-card-link gp-card-product" href="studio/">
<span class="gp-card-icon">▣</span>
<h3>gpbiometricspy Studio</h3>
<p>Load data, run quality checks, analyze physiology and eye tracking, align events and streams, model results, and export reproducible outputs through one stateful interface.</p>
<span class="gp-card-cta">Open the Studio guide →</span>
</a>

<a class="gp-card gp-card-link" href="getting-started/">
<span class="gp-card-icon">⌨</span>
<h3>Python API</h3>
<p>Use the complete 406-function frozen-parity scientific surface from scripts, notebooks, packages, pipelines, or custom research applications.</p>
<span class="gp-card-cta">Start coding →</span>
</a>

<a class="gp-card gp-card-link" href="workflows/">
<span class="gp-card-icon">→</span>
<h3>Workflow map</h3>
<p>Start from the signals you recorded and follow a defensible path through validation, preprocessing, analysis, alignment and reporting.</p>
<span class="gp-card-cta">Choose a workflow →</span>
</a>

<a class="gp-card gp-card-link" href="methods/">
<span class="gp-card-icon">Σ</span>
<h3>Methods</h3>
<p>Explore additive Python-native Gaussian, robust Student-t and random-slope hierarchical location–scale methods without blurring the frozen R-parity contract.</p>
<span class="gp-card-cta">Open methods →</span>
</a>

</div>

## Current Python-native methods

The development line contains three explicitly separate location–scale modelling paths.

### Gaussian hierarchical location–scale model

The Gaussian method jointly models outcome location and log residual scale with correlated participant/group random intercepts. It uses two-dimensional adaptive Gauss–Hermite quadrature, empirical-Bayes group-effect summaries, explicit unseen-group prediction semantics, immutable fitted metadata and SHA-256 reproducibility certificates.

[Open the Gaussian hierarchical location–scale guide →](methods/hierarchical-location-scale.md)

### Robust Student-t hierarchical location–scale model

The robust extension keeps the same location/log-scale architecture but replaces the conditional Gaussian outcome model with a symmetric Student-t distribution and estimates its degrees of freedom jointly with the remaining parameters. Fitting and known-truth simulation share the same `2.05 ≤ ν ≤ 200` domain. Reproducibility certificates also bind a canonical, row-order-invariant fingerprint of the empirical-Bayes random-effects table used for conditional prediction.

[Open the robust Student-t location–scale guide →](methods/robust-hierarchical-location-scale.md)

### Gaussian random-slope hierarchical location–scale model

The random-slope extension adds one participant/group-specific numeric slope to the Gaussian location equation while retaining the log-scale random intercept. The latent state is `(location intercept, location slope, log-scale intercept)` with a full positive-definite **3 × 3 covariance matrix** and **three-dimensional adaptive Gauss–Hermite quadrature**. The random-slope variable must also be present as a fixed mean effect and must vary within every group.

[Open the random-slope location–scale guide →](methods/random-slope-location-scale.md)

The latest merged methods baseline is PR **#119**, merge SHA `0245dd99d2ca8aa44b26c3740f332628f9ba83e4`, whose merge tree exactly matches the qualified PR head tree. The candidate completed **14/14 exact-head workflow families successfully**. Fresh exact-main software evidence passes **694/694 tests**, **11,504/11,504 statements = 100.00%**, retains **406/406 frozen exports with 0 pending**, and records **5,909/5,928 raw branches = 99.6795%**. The random-slope module itself passes **353/353 statements** and **90/90 branches**; all **19** uncovered branch arcs are audited structural debt with zero unexpected, stale or unaudited branch debt.

Full exact-main certification remains stricter than source, test, and coverage success: it is declared only when every required post-merge push workflow for the exact merge SHA is terminal green.

!!! info "Scientific boundary"
    These are distributional heterogeneity models. The Student-t extension adds heavy-tailed robustness, but a low fitted degrees-of-freedom parameter is **not** an artifact score. The random-slope extension estimates association heterogeneity, not a causal effect or an error-free participant trait. None of these implementations identifies motion or physiological artifacts, performs artifact correction or sensor-validity weighting, establishes causal effects, or infers latent psychological or clinical states. Additional random slopes, random slopes in the log-scale equation, crossed random effects, skewed heavy-tail families, mixture models and Bayesian priors remain outside the current family.

## Studio: the end-user research product

Studio is not a separate statistical implementation. It calls the same public `gpbiometricspy` scientific functions used by the Python API, so visual workflows remain connected to the tested package contract.

<div class="gp-flow gp-flow-product">
<div><strong>01</strong><span>Project</span><small>Load synthetic or local research data and inspect channels.</small></div>
<div><strong>02</strong><span>Quality</span><small>Run foundation and signal-specific QC before interpretation.</small></div>
<div><strong>03</strong><span>Analyze</span><small>EDA/SCR, PPG/HRV, pupil, gaze, fixation and AOIs.</small></div>
<div><strong>04</strong><span>Align</span><small>Connect events, TTL markers, AOIs and secondary streams.</small></div>
<div><strong>05</strong><span>Model</span><small>Prepare model-ready summaries and guarded statistical workflows.</small></div>
<div><strong>06</strong><span>Report</span><small>Export results, provenance, project recipes and replay code.</small></div>
</div>

### Install Studio

```bash
python -m pip install "gpbiometricspy[studio]==0.1.6"
```

Normal launcher:

```bash
gpbiometricspy-studio
```

PATH-independent launcher, especially useful on Windows Store Python installations:

```bash
python -m studio.cli --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765`.

!!! warning "Research data stay in the full local/private Studio"
    The anonymous public demonstration is synthetic-only and fail-closed for external uploads. Use the full local Studio or an appropriately authenticated/private deployment for participant data.

## What can you analyze?

<div class="gp-card-grid">

<a class="gp-card gp-card-link" href="examples/eda-scr/">
<span class="gp-card-icon">∿</span>
<h3>EDA / GSR / SCR</h3>
<p>Quality checks, artifacts, tonic/phasic decomposition, response detection, event summaries and diagnostics.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/ppg-hrv/">
<span class="gp-card-icon">♥</span>
<h3>PPG / IBI / HRV</h3>
<p>Pulse/interval quality, HRV families, morphology descriptors, metric-specific agreement and optional toolbox bridges.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/pupil-gaze/">
<span class="gp-card-icon">◎</span>
<h3>Pupil / gaze / AOI</h3>
<p>Pupil QC, gaze and fixation summaries, AOI-linked measures, saccades and interpretation guardrails.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/multimodal/">
<span class="gp-card-icon">↔</span>
<h3>Events + multimodal</h3>
<p>TTL markers, event logs, drift, secondary streams, AOI timing and multimodal alignment on explicit shared timebases.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/quality-reporting/">
<span class="gp-card-icon">✓</span>
<h3>QC + reporting</h3>
<p>Turn diagnostics into explicit validity evidence, exclusions, plots, provenance and reproducible reporting outputs.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/interoperability/">
<span class="gp-card-icon">⌘</span>
<h3>Interoperability</h3>
<p>Bridge to MNE, LSL/XDF, BIDS-oriented workflows, BioSPPy, HeartPy, pyHRV and NeuroKit-style paths.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

</div>

## Built for research you can audit

<div class="gp-pillar-grid">
<div class="gp-pillar">
<h3>One scientific engine</h3>
<p>Studio and Python code call the same public package API. The application does not maintain a hidden second implementation of the scientific methods.</p>
<a href="studio/">See the architecture →</a>
</div>
<div class="gp-pillar">
<h3>Validation is part of the product</h3>
<p>The latest merged methods tree passes 694 exact-main tests, 11,504/11,504 statements, and 5,909/5,928 raw branches. All 19 uncovered branch arcs are audited structural debt, with zero unexpected, stale or unaudited debt. PR #119 itself completed all 14 exact-head workflow families before merge; full exact-main certification additionally requires every post-merge workflow to finish green.</p>
<a href="deep-validation/">Inspect validation →</a>
</div>
<div class="gp-pillar">
<h3>Conservative interpretation</h3>
<p>Physiological and eye-tracking signals are measurements, not direct proof of emotion, stress, trust, preference, cognition, health status or diagnosis. Heavy-tailed robustness and random-slope heterogeneity are not automatic artifact classification or causal evidence.</p>
<a href="interpretation/">Read the guardrails →</a>
</div>
</div>

!!! success "Stable archival record"
    Stable `gpbiometricspy 0.1.6` was released on **2026-09-11**. Its frozen release qualification remains separate from development work: **641 tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**. Its version DOI remains pending until Zenodo ingests `v0.1.6`; the software concept DOI is [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872), and the previous 0.1.5 version DOI is [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823).

## Generated by the package

<div class="gp-feature-gallery">
<figure class="gp-feature-gallery-main">
<img src="assets/generated/multimodal-timeline.png" alt="Multimodal timeline with aligned EDA, heart-rate, pupil and event markers">
<figcaption><strong>Multimodal timeline.</strong> EDA, heart-rate and pupil channels on a shared event-aligned time axis.</figcaption>
</figure>
<figure>
<img src="assets/generated/eda-decomposition.png" alt="EDA tonic and phasic decomposition">
<figcaption><strong>EDA decomposition.</strong> Observed, tonic and phasic components.</figcaption>
</figure>
<figure>
<img src="assets/generated/ppg-poincare.png" alt="Poincare plot of successive beat-to-beat intervals">
<figcaption><strong>Poincaré geometry.</strong> Beat-to-beat structure for HRV inspection.</figcaption>
</figure>
</div>

Every gallery image is regenerated from the Python API during the documentation workflow. Browse the full [plot gallery](plot-gallery.md).

## Go deeper

<div class="gp-mini-grid">
<a href="studio/">Studio application</a>
<a href="getting-started/">5-minute Python start</a>
<a href="workflows/">Workflow map</a>
<a href="methods/">Python-native methods</a>
<a href="methods/robust-hierarchical-location-scale/">Robust Student-t location–scale</a>
<a href="methods/random-slope-location-scale/">Random-slope location–scale</a>
<a href="measurement-accountability/">Measurement accountability</a>
<a href="articles/">26 article companions</a>
<a href="integrations/">Integrations</a>
<a href="citation/">Citation + DOI</a>
<a href="api/reference/">406-function frozen-parity API</a>
<a href="development/">Development</a>
</div>
