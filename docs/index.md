<div class="gp-landing-hero" markdown>

<span class="gp-kicker">Scientific Python for multimodal physiology + eye tracking</span>

# Measure. Align. Validate. Report.

**gpbiometricspy** brings the complete **406-function gpbiometrics 2.0.0 surface** into Python for EDA/GSR/SCR, PPG/IBI/HRV, pupil, gaze, AOIs, event alignment, quality control, reporting, and research-tool interoperability — with **gpbiometricspy Studio** as a Shiny for Python application layer over the same public scientific API.

<div class="gp-actions">
<a class="md-button md-button--primary" href="getting-started/">Get started</a>
<a class="md-button" href="studio/">Open Studio guide</a>
<a class="md-button" href="workflows/">Choose a workflow</a>
<a class="md-button" href="plot-gallery/">See real plots</a>
</div>

</div>

<div class="gp-status-grid">
<div><span class="gp-status-value">0.1.2</span><span class="gp-status-label">stable release</span></div>
<div><span class="gp-status-value">0.1.3.dev0</span><span class="gp-status-label">development docs</span></div>
<div><span class="gp-status-value">406 / 406</span><span class="gp-status-label">R exports implemented</span></div>
<div><span class="gp-status-value">100%</span><span class="gp-status-label">statement coverage</span></div>
<div><span class="gp-status-value">3.11–3.14</span><span class="gp-status-label">Python CI matrix</span></div>
</div>

!!! info "Development documentation"
    This site tracks `main` (`0.1.3.dev0`). The latest stable release is `0.1.2`, archived at DOI [10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873). The evolving software concept DOI is [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872).

## Code or Studio

Use the Python API when you want scripts, notebooks, pipelines, or direct integration into a larger analysis stack. Use Studio when you want one stateful research interface over the same package functions.

<div class="gp-card-grid">

<a class="gp-card gp-card-link" href="getting-started/">
<span class="gp-card-icon">⌨</span>
<h3>Python API</h3>
<p>Install the package and build explicit scripts around the complete 406-function scientific surface.</p>
<span class="gp-card-cta">Start coding →</span>
</a>

<a class="gp-card gp-card-link" href="studio/">
<span class="gp-card-icon">▣</span>
<h3>gpbiometricspy Studio</h3>
<p>Run QC, annotation, EDA/SCR, PPG/HRV, pupil, gaze/AOI, alignment, multimodal, modelling and reproducibility workflows in Shiny for Python.</p>
<span class="gp-card-cta">Open Studio guide →</span>
</a>

</div>

The Studio public-deployment boundary is **synthetic-only and fail-closed for external file uploads**. Research data belong in the full local Studio or an appropriately authenticated/private deployment.

## Install and move

=== "Stable"

    ```bash
    python -m pip install gpbiometricspy
    ```

=== "Development"

    ```bash
    python -m pip install \
      "gpbiometricspy @ git+https://github.com/stefanosbalaskas/gpbiometricspy.git@main"
    ```

=== "Development + Studio"

    ```bash
    git clone https://github.com/stefanosbalaskas/gpbiometricspy.git
    cd gpbiometricspy
    python -m pip install -e ".[studio]"
    gpbiometricspy-studio
    ```

```python
import gpbiometricspy as gp

data = gp.load_kiosk_demo()
validity = gp.summarise_gazepoint_biometric_validity(data)
events = gp.extract_gazepoint_ttl_events(data)
```

<div class="gp-callout-line">
<strong>Bundled demo:</strong> 36 synthetic participants · 4 tasks each · 69,120 Gazepoint-like rows at 60 Hz.
</div>

## Choose your workflow

<div class="gp-card-grid">

<a class="gp-card gp-card-link" href="examples/eda-scr/">
<span class="gp-card-icon">∿</span>
<h3>EDA / GSR / SCR</h3>
<p>Clean electrodermal signals, inspect artifacts, decompose tonic/phasic activity, detect responses, and build event-linked summaries.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/ppg-hrv/">
<span class="gp-card-icon">♥</span>
<h3>PPG / IBI / HRV</h3>
<p>Detect pulses, derive beat-to-beat intervals, compute HRV families, and cross-check pyHRV, HeartPy, BioSPPy, and NeuroKit-style paths.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/pupil-gaze/">
<span class="gp-card-icon">◎</span>
<h3>Pupil / gaze / AOI</h3>
<p>Audit pupil and gaze quality, summarize AOI-linked biometrics, inspect saccades, and connect eye-tracking behavior to physiology.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/multimodal/">
<span class="gp-card-icon">↔</span>
<h3>Multimodal alignment</h3>
<p>Align Gazepoint streams, TTL/event markers, trials, AOIs, and external recordings on defensible shared timebases.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/quality-reporting/">
<span class="gp-card-icon">✓</span>
<h3>QC + reporting</h3>
<p>Turn raw signal diagnostics into explicit validity audits, exclusion evidence, visual QC, and reproducible reporting outputs.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

<a class="gp-card gp-card-link" href="examples/interoperability/">
<span class="gp-card-icon">⌘</span>
<h3>Interoperability</h3>
<p>Bridge into MNE, EEG/LSL, pyxdf, BioSPPy, HeartPy, pyHRV, and NeuroKit-style workflows without hiding backend assumptions.</p>
<span class="gp-card-cta">Open workflow →</span>
</a>

</div>

## Built for research you can audit

<div class="gp-pillar-grid">
<div class="gp-pillar">
<h3>Parity with provenance</h3>
<p>The frozen R reference is retained alongside the Python implementation, with 406/406 exports registered and 26 article companions preserved.</p>
<a href="parity/">Inspect parity →</a>
</div>
<div class="gp-pillar">
<h3>Validation as a first-class output</h3>
<p>Current CI enforces 100% statement coverage across Ubuntu, Windows, and macOS on Python 3.11–3.14, plus deep parity, interoperability, Studio smoke, Chromium E2E and production-deployment checks.</p>
<a href="deep-validation/">See validation →</a>
</div>
<div class="gp-pillar">
<h3>Conservative interpretation</h3>
<p>Signal processing and descriptive summaries are kept distinct from unsupported claims about emotion, stress, preference, cognition, or diagnosis.</p>
<a href="interpretation/">Read guardrails →</a>
</div>
</div>

## From raw export to defensible result

```text
Gazepoint / external streams
  → schema + channel audit
  → timing / TTL / dropout QC
  → EDA / PPG / IBI / pupil / gaze preprocessing
  → event / AOI / multimodal alignment
  → feature extraction + model-ready tables
  → plots + reports + reproducibility outputs
  → optional external-toolbox cross-checks
```

<p class="gp-center-link"><a class="md-button md-button--primary" href="workflows/">Explore the workflow map</a></p>

## Generated by the package, not drawn for the website

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

Every gallery image is regenerated from the current Python API during the documentation workflow. Browse all [13 generated figures](plot-gallery.md).

## Documentation paths

<div class="gp-mini-grid">
<a href="getting-started/">5-minute start</a>
<a href="studio/">Studio application</a>
<a href="workflows/">Workflow map</a>
<a href="articles/">26 articles</a>
<a href="integrations/">Integrations</a>
<a href="citation/">Citation + DOI</a>
<a href="api/reference/">406-function API</a>
</div>
