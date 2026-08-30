# Articles and tutorials

All **26** frozen R vignette/article sources have a Python companion **and an executable Python workflow** under `examples/tutorials/`. The test suite executes every companion so examples cannot silently rot.

Use the topic groups below when you know the scientific task. Use the [API domain browser](../api/index.md) when you know the operation or function family, and the [Plot gallery](../plot-gallery.md) when you want to start from rendered outputs.

<div class="gp-card-grid gp-card-grid-compact">

<a class="gp-card gp-card-link" href="#eda-scr">
<span class="gp-card-icon">∿</span>
<h3>EDA / SCR</h3>
<p>Electrodermal preprocessing, response detection, visual diagnostics, and toolbox cross-checks.</p>
<span class="gp-card-cta">4 articles →</span>
</a>

<a class="gp-card gp-card-link" href="#ppg-ibi-hrv">
<span class="gp-card-icon">♥</span>
<h3>PPG / HRV</h3>
<p>Pulse processing, IBI/HRV analysis, respiration, and visual diagnostics.</p>
<span class="gp-card-cta">2 articles →</span>
</a>

<a class="gp-card gp-card-link" href="#pupil-gaze-aoi">
<span class="gp-card-icon">◎</span>
<h3>Pupil / gaze / AOI</h3>
<p>Eye-tracking QC, ecosystem bridges, and AOI-linked physiology.</p>
<span class="gp-card-cta">3 articles →</span>
</a>

<a class="gp-card gp-card-link" href="#alignment-design-multimodal">
<span class="gp-card-icon">↔</span>
<h3>Alignment + design</h3>
<p>Multimodal dashboards, cluster inference, design audits, and event alignment.</p>
<span class="gp-card-cta">4 articles →</span>
</a>

<a class="gp-card gp-card-link" href="#quality-reporting-reproducibility">
<span class="gp-card-icon">✓</span>
<h3>QC + reporting</h3>
<p>Quality-control evidence, visual dashboards, real-data smoke testing, and reproducibility.</p>
<span class="gp-card-cta">6 articles →</span>
</a>

<a class="gp-card gp-card-link" href="#interoperability-exchange">
<span class="gp-card-icon">⌘</span>
<h3>Interoperability</h3>
<p>BIDS, MNE/EEG/LSL, external toolboxes, gp3tools, and version-aware bridges.</p>
<span class="gp-card-cta">5 articles →</span>
</a>

</div>

## Start with the overview

- [Article roadmap](article-roadmap.md) — maps the complete article set and major research paths.
- [gpbiometrics workflow](gpbiometrics-workflow.md) — end-to-end Python companion to the central R workflow.
- [Synthetic data showcase](synthetic-data-showcase.md) — reproducible signals and workflows without private data.
- [Plot gallery](plot-gallery.md) — original article companion for the generated visual surface.

## EDA / SCR

- [EDA, GSR, and SCR workflow](eda-scr-workflow.md) — preprocessing, decomposition, detection, summaries.
- [EDA and SCR visual diagnostics](eda-scr-visual-diagnostics.md) — signal and event-level visual checks.
- [External toolbox bridges workflow](toolbox-bridges-workflow.md) — BioSPPy/NeuroKit/PsPM/cvxEDA-style handoffs and cross-checks.
- [Toolbox crosscheck visuals](toolbox-crosscheck-visuals.md) — comparison-oriented diagnostics across analysis paths.

## PPG / IBI / HRV

- [PPG, IBI, HRV, and respiration workflow](ppg-hrv-workflow.md) — pulse to intervals, HRV, respiration, and model-ready summaries.
- [PPG and HRV visual diagnostics](ppg-hrv-visual-diagnostics.md) — peak, interval, Poincaré, and spectral diagnostics.

## Pupil / gaze / AOI

- [Pupil and gaze quality-control workflow](pupil-qc-workflow.md) — missingness, blinks, smoothing, gaze validity, and fixation summaries.
- [Using gpbiometrics with eyetrackingR, PupillometryR, and gazeR](eye-tracking-ecosystem-bridges.md) — structured cross-ecosystem handoffs.
- [Event alignment and AOI-linked biometric workflow](event-alignment-aoi-workflow.md) — connect gaze/AOI behavior with event-locked physiology.

## Alignment / design / multimodal

- [Multimodal event dashboard](multimodal-event-dashboard.md) — synchronized signal and event inspection.
- [Cluster-permutation workflow](cluster-permutation.md) — time-resolved inference and cluster diagnostics.
- [Design audit workflow](design-audit-workflow.md) — event coverage, balance, comparability, and design checks.
- [Design release visual audit](design-release-visual-audit.md) — visual release-oriented design QA.

## Quality / reporting / reproducibility

- [Quality-control workflow](qc-workflow.md) — signal activity, missingness, dropouts, and exclusion evidence.
- [Visual QC dashboard workflow](visual-qc-dashboard-workflow.md) — compact visual inspection across channels and sessions.
- [Reporting and reproducibility workflow](reporting-reproducibility-workflow.md) — methods text, manifests, tables, and reporting bundles.
- [Diagnosing common Gazepoint export and workflow problems](troubleshooting-readiness.md) — failure modes and readiness checks.
- [Running private real-data smoke tests safely](private-real-data-smoke-testing.md) — privacy-safe validation outside the repository.
- [gp3tools compatibility and cross-package handoff](gp3tools-compatibility.md) — connect biometrics outputs to the broader Gazepoint analysis stack.

## Interoperability / exchange

- [Exporting Gazepoint eye-tracking and physiology to BIDS](bids-export-workflow.md) — BIDS-oriented eye and physiology exports.
- [MNE, EEG, and LSL interoperability workflow](mne-eeg-lsl-workflow.md) — events, streams, timing, and MNE handoffs.
- [Testing interoperability across external package versions](interoperability-version-testing.md) — backend/version evidence.
- [External toolbox bridges workflow](toolbox-bridges-workflow.md) — analysis-toolbox cross-checks and preparation.
- [gp3tools compatibility and cross-package handoff](gp3tools-compatibility.md) — cross-package Gazepoint handoff.

## Complete frozen article inventory

The inventory below preserves the original R-source provenance and the number of frozen exports referenced by each source.

| Article | Python companion | Frozen R source | Referenced exports |
|---|---|---|---:|
| Article roadmap | [article-roadmap](article-roadmap.md) | `articles/article-roadmap.Rmd` | 85 |
| Exporting Gazepoint eye-tracking and physiology to BIDS | [bids-export-workflow](bids-export-workflow.md) | `articles/bids-export-workflow.Rmd` | 4 |
| Cluster-permutation workflow | [cluster-permutation](cluster-permutation.md) | `articles/cluster-permutation.Rmd` | 13 |
| Design audit workflow | [design-audit-workflow](design-audit-workflow.md) | `articles/design-audit-workflow.Rmd` | 32 |
| Design release visual audit | [design-release-visual-audit](design-release-visual-audit.md) | `articles/design-release-visual-audit.Rmd` | 16 |
| EDA and SCR visual diagnostics | [eda-scr-visual-diagnostics](eda-scr-visual-diagnostics.md) | `articles/eda-scr-visual-diagnostics.Rmd` | 13 |
| EDA, GSR, and SCR workflow | [eda-scr-workflow](eda-scr-workflow.md) | `articles/eda-scr-workflow.Rmd` | 25 |
| Event alignment and AOI-linked biometric workflow | [event-alignment-aoi-workflow](event-alignment-aoi-workflow.md) | `articles/event-alignment-aoi-workflow.Rmd` | 29 |
| Using gpbiometrics with eyetrackingR, PupillometryR, and gazeR | [eye-tracking-ecosystem-bridges](eye-tracking-ecosystem-bridges.md) | `articles/eye-tracking-ecosystem-bridges.Rmd` | 3 |
| gp3tools compatibility and cross-package handoff | [gp3tools-compatibility](gp3tools-compatibility.md) | `articles/gp3tools-compatibility.Rmd` | 1 |
| Testing interoperability across external package versions | [interoperability-version-testing](interoperability-version-testing.md) | `articles/interoperability-version-testing.Rmd` | 3 |
| MNE, EEG, and LSL interoperability workflow | [mne-eeg-lsl-workflow](mne-eeg-lsl-workflow.md) | `articles/mne-eeg-lsl-workflow.Rmd` | 6 |
| Multimodal event dashboard | [multimodal-event-dashboard](multimodal-event-dashboard.md) | `articles/multimodal-event-dashboard.Rmd` | 15 |
| Plot gallery | [plot-gallery](plot-gallery.md) | `articles/plot-gallery.Rmd` | 42 |
| PPG and HRV visual diagnostics | [ppg-hrv-visual-diagnostics](ppg-hrv-visual-diagnostics.md) | `articles/ppg-hrv-visual-diagnostics.Rmd` | 15 |
| PPG, IBI, HRV, and respiration workflow | [ppg-hrv-workflow](ppg-hrv-workflow.md) | `articles/ppg-hrv-workflow.Rmd` | 39 |
| Running private real-data smoke tests safely | [private-real-data-smoke-testing](private-real-data-smoke-testing.md) | `articles/private-real-data-smoke-testing.Rmd` | 4 |
| Pupil and gaze quality-control workflow | [pupil-qc-workflow](pupil-qc-workflow.md) | `articles/pupil-qc-workflow.Rmd` | 21 |
| Quality-control workflow | [qc-workflow](qc-workflow.md) | `articles/qc-workflow.Rmd` | 13 |
| Reporting and reproducibility workflow | [reporting-reproducibility-workflow](reporting-reproducibility-workflow.md) | `articles/reporting-reproducibility-workflow.Rmd` | 23 |
| Synthetic data showcase | [synthetic-data-showcase](synthetic-data-showcase.md) | `articles/synthetic-data-showcase.Rmd` | 50 |
| External toolbox bridges workflow | [toolbox-bridges-workflow](toolbox-bridges-workflow.md) | `articles/toolbox-bridges-workflow.Rmd` | 43 |
| Toolbox crosscheck visuals | [toolbox-crosscheck-visuals](toolbox-crosscheck-visuals.md) | `articles/toolbox-crosscheck-visuals.Rmd` | 16 |
| Diagnosing common Gazepoint export and workflow problems | [troubleshooting-readiness](troubleshooting-readiness.md) | `articles/troubleshooting-readiness.Rmd` | 8 |
| Visual QC dashboard workflow | [visual-qc-dashboard-workflow](visual-qc-dashboard-workflow.md) | `articles/visual-qc-dashboard-workflow.Rmd` | 11 |
| gpbiometrics workflow | [gpbiometrics-workflow](gpbiometrics-workflow.md) | `gpbiometrics-workflow.Rmd` | 22 |
