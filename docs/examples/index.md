# Examples

<div class="gp-page-intro">
These examples are the practical front door to `gpbiometricspy`. Every route uses bundled synthetic/public demonstration data or deterministic simulation, so you can inspect the workflow and rendered output before introducing private participant data.
</div>

<div class="gp-route-grid">
<a class="gp-route-card" data-learning-route="research-recipes" href="#worked-research-recipes"><span class="gp-route-label">Cookbook</span><h3>Worked research recipes</h3><p>Combine verified event, multimodal, AOI and visual-inspection calls into compact recipes you can adapt without skipping QC or provenance.</p></a>
<a class="gp-route-card" href="end-to-end-eda/"><span class="gp-route-label">Run first</span><h3>Complete EDA analysis bundle</h3><p>Execute one checked script from input through QC, decomposition, candidate events, figures, tables and methods text.</p></a>
<a class="gp-route-card" data-learning-route="research-evidence-bundle" href="../guides/reporting-reproducibility/#run-a-reviewable-evidence-bundle"><span class="gp-route-label">Reproduce</span><h3>Research evidence bundle</h3><p>Run a checked cross-domain example that retains design, structured QC, TTL/alignment, event-locked, visual, software and reporting evidence.</p></a>
<a class="gp-route-card" data-learning-route="bring-your-own-export" href="../guides/bring-your-own-export/"><span class="gp-route-label">Adapt</span><h3>Adapt an unfamiliar export</h3><p>Run a checked source-to-standard mapping workflow that preserves original names, verifies schema/time/event evidence, and writes an adaptation manifest.</p></a>
<a class="gp-route-card" href="eda-scr/"><span class="gp-route-label">EDA / SCR</span><h3>Conductance to response events</h3><p>Inspect quality, decompose EDA, detect candidate SCRs, and retain visual diagnostics.</p></a>
<a class="gp-route-card" href="ppg-hrv/"><span class="gp-route-label">PPG / HRV</span><h3>Waveform to beat intervals</h3><p>Detect pulse peaks, inspect RR/IBI geometry, and generate standard HRV diagnostics with source guardrails.</p></a>
<a class="gp-route-card" href="pupil-gaze/"><span class="gp-route-label">Eye tracking</span><h3>Pupil, gaze, AOI and saccades</h3><p>Inspect pupil/gaze channels, aggregate AOI-linked measures, and use gaze diagnostics without inferring latent states.</p></a>
<a class="gp-route-card" href="multimodal/"><span class="gp-route-label">Alignment</span><h3>Events and synchronized streams</h3><p>Extract markers, audit timebases, align multimodal channels, and build event-locked summaries.</p></a>
<a class="gp-route-card" href="quality-reporting/"><span class="gp-route-label">Evidence</span><h3>QC and reproducible reporting</h3><p>Make missingness, signal activity, timing issues, design coverage, and report-ready evidence visible.</p></a>
<a class="gp-route-card" href="interoperability/"><span class="gp-route-label">Ecosystem</span><h3>External toolbox handoffs</h3><p>Prepare explicit bridges for HeartPy, pyPPG, NeuroKit, MNE, LSL/XDF, BIDS-oriented workflows, and related tools.</p></a>
</div>

## Choose by what you have

| Starting data | Example | Primary evidence produced |
|---|---|---|
| I want short recipes that connect several stages | [Worked research recipes](#worked-research-recipes) | event tables, event-locked summaries, AOI summaries, shared-timeline figure |
| I want one complete working analysis first | [End-to-end EDA](end-to-end-eda.md) | QC, decomposition, event tables, figures, methods evidence |
| I want a reviewable cross-domain evidence folder | [Research evidence bundle](../guides/reporting-reproducibility.md#run-a-reviewable-evidence-bundle) | design, structured QC, events/alignment, summaries, figure, software and manifest |
| I have an unfamiliar CSV/export to map | [Bring your own export safely](../guides/bring-your-own-export.md) | source-to-standard map, schema/timebase evidence, TTL events, adaptation manifest |
| EDA/GSR waveform | [EDA / GSR / SCR](eda-scr.md) | quality, decomposition, candidate response events |
| PPG waveform or intervals | [PPG / HRV](ppg-hrv.md) | peak/interval diagnostics and HRV-ready series |
| Pupil/gaze/AOI columns | [Pupil / gaze / AOI](pupil-gaze.md) | missingness/validity, AOI summaries, gaze diagnostics |
| TTL/task events + signals | [Multimodal](multimodal.md) | event identity, timebase/alignment evidence, event windows |
| Any completed dataset | [QC + reporting](quality-reporting.md) | auditable QC, design coverage, figures, reporting inputs |
| External analysis ecosystem | [Interoperability](interoperability.md) | explicit backend-ready structures and version-aware handoffs |

## Worked research recipes

The recipes below use the same bundled demonstration and exported functions exercised elsewhere in the documentation. They are intentionally short: each recipe shows one defensible transition in the research workflow, not a claim that the returned object is scientifically interpretable without the surrounding QC and design evidence.

### 1. Load a bounded demonstration slice

```python
import gpbiometricspy as gp

# Synthetic/public demonstration data only.
dat = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)
```

Before adapting the recipes to research data, use the [bring-your-own-export guide](../guides/bring-your-own-export.md) to make the source-to-analysis mapping explicit, then use the [new-dataset validation guide](../guides/validate-dataset.md) to confirm schema, units, signal identity, timing and provenance.

### 2. TTL events → event-relative physiology windows

```python
events = gp.extract_gazepoint_ttl_events(
    dat,
    ttl_columns=["TTL0"],
    group_columns=["participant_id"],
)

aligned = gp.align_gazepoint_biometrics_to_ttl(
    dat,
    ttl_cols=["TTL0"],
    time_col="TIME",
    group_cols=["participant_id"],
    pre_window_ms=250,
    post_window_ms=500,
)
```

Inspect the extracted event table before treating TTL edges as task events. Event identity, duplicate/missing markers and group coverage remain part of the evidence chain.

### 3. Events + recorded channels → multimodal summaries

```python
summary = gp.summarize_gazepoint_eventlocked_multimodal(
    dat,
    events=events,
    time_col="TIME",
    event_time_col="TIME",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
)
```

This produces event-relative summaries for the requested recorded channels. Keep the event definition, baseline/summary window settings, missingness and group identifiers with the derived table.

### 4. AOI labels → dwell summaries

```python
aoi = gp.summarize_gazepoint_aoi_dwell(
    dat,
    aoi_col="AOI",
    group_cols=["participant_id"],
)
```

AOI summaries depend on the AOI definitions, gaze-validity rules and denominator. Preserve those inputs when moving the table into modelling or reporting.

### 5. Recorded channels → a shared visual timeline

```python
fig = gp.plot_gazepoint_multimodal_timeline(
    dat,
    time_col="TIME",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
    title="Multimodal Gazepoint timeline",
)
```

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#multimodal-alignment"><img src="../assets/generated/multimodal-timeline.png" alt="Multimodal timeline with physiology pupil and event markers"><div class="gp-visual-card-body"><strong>Shared timeline</strong><span>Inspect recorded channels and event markers before relying on event-relative summaries.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#pupil-gaze-and-aois"><img src="../assets/generated/aoi-biometrics.png" alt="AOI-linked biometric summary visualization"><div class="gp-visual-card-body"><strong>AOI-linked evidence</strong><span>Use AOI summaries together with explicit AOI definitions, validity rules and denominators.</span></div></a>
</div>

### What each object can support

| Object | Useful for | Inspect before reuse |
|---|---|---|
| `events` | event identity and coverage | marker semantics, duplicates, missing events, group coverage |
| `aligned` | event-relative rows/windows | clock identity, time units, window definition, overlap |
| `summary` | analysis-ready event/channel features | baseline/summary settings, missingness, group identifiers |
| `aoi` | AOI dwell summaries | AOI definitions, gaze validity, denominator and grouping |
| `fig` | visual temporal QC | scaling/standardisation, event markers, visible gaps and resets |

### Adapt the recipes to your data

Change inputs deliberately rather than mechanically:

1. preserve the original export and record the [source-to-standard mapping](../guides/bring-your-own-export.md);
2. map your real time, participant/session/trial, signal and event columns;
3. run QC before changing thresholds or deriving measures;
4. establish clock relationships before event locking multiple streams;
5. retain the settings used to produce every derived table or figure;
6. move to [model selection](../guides/model-selection.md) only after the analysis unit and grouping structure are explicit;
7. finish with [reporting and reproducibility](../guides/reporting-reproducibility.md).

<div class="gp-science-boundary">
<strong>Scientific boundary.</strong> These recipes transform and summarize recorded data. They do not by themselves identify emotion, stress, attention, trust, preference, diagnosis, causal effects, or hardware-level synchronization. Those interpretations require independent design, measurement and inferential justification.
</div>

!!! tip "Not sure which recipe belongs next?"
    Use the [workflow chooser](../guides/index.md#choose-your-workflow) to start from the evidence you have and identify the next defensible stage.

## Visual outputs generated in CI

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/eda-decomposition.png" alt="EDA tonic and phasic decomposition"><div class="gp-visual-card-body"><strong>EDA decomposition</strong><span>Observed, tonic and phasic components.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#ppg-and-hrv"><img src="../assets/generated/ppg-peak-detection.png" alt="PPG waveform with detected pulse peaks"><div class="gp-visual-card-body"><strong>PPG peak detection</strong><span>Waveform and accepted pulse events.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#pupil-gaze-and-aois"><img src="../assets/generated/pupil-gaze-overview.png" alt="Pupil and gaze signal overview"><div class="gp-visual-card-body"><strong>Pupil + gaze</strong><span>Standardised eye-tracking channels.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#multimodal-alignment"><img src="../assets/generated/multimodal-timeline.png" alt="Multimodal timeline with physiology pupil and event markers"><div class="gp-visual-card-body"><strong>Multimodal timeline</strong><span>Signals inspected on an explicit shared timeline.</span></div></a>
</div>

## From example to research workflow

1. Reproduce the [checked end-to-end example](end-to-end-eda.md) unchanged.
2. Preserve and map your source with [Bring your own export safely](../guides/bring-your-own-export.md).
3. Run the [new-dataset validation guide](../guides/validate-dataset.md).
4. Preserve QC/provenance evidence before preprocessing.
5. Move to the deeper article linked from the example.
6. Use the [API reference](../api/index.md) only when you need exact signatures or less common options.

For a visual survey first, open the [Plot gallery](../plot-gallery.md). For the 26 executable frozen R-companion workflows, browse [Articles and tutorials](../articles/index.md). For conceptual design guidance, use the [Python-native explanation articles](../articles/python-native/index.md).
