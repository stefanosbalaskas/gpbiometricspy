# Synthetic kiosk demo

<div class="gp-page-intro" data-demo-data-guide>
The package ships an unchanged, fully synthetic Gazepoint-like kiosk dataset from the frozen `gpbiometrics 2.0.0` source distribution. Use it to learn the package, reproduce documentation workflows, inspect expected object shapes, and test analysis code before introducing private participant data.
</div>

<div class="gp-metric-grid">
<div class="gp-metric-card"><strong>36</strong><span>synthetic participants</span></div>
<div class="gp-metric-card"><strong>4</strong><span>tasks per participant</span></div>
<div class="gp-metric-card"><strong>60 Hz</strong><span>nominal sample rate</span></div>
<div class="gp-metric-card"><strong>69,120</strong><span>all-gaze rows in the complete demo</span></div>
</div>

## What the demo represents

The synthetic scenario is a public-service touchscreen kiosk study. The task design crosses two interface factors:

- **interface complexity:** `simple` vs `dense`;
- **feedback clarity:** `clear` vs `ambiguous`.

Each participant has four eight-second tasks, one for each factor combination, with 480 rows per task at the nominal 60 Hz sampling rate. Task order varies across participants. The trial-design table retains `participant_id`, `task_order`, `MEDIA_ID`, `MEDIA_NAME`, the two design factors, sampling rate, task duration, row count, and the synthetic scenario label.

The exports contain synthetic gaze/AOI, pupil, EDA/GSR, heart-rate/interval, pulse-waveform, engagement-dial and TTL/event channels. These are deliberately broad enough to exercise the package's multimodal workflows; they are not measurements from real people.

## Load the data deliberately

For most tutorials, start with one participant or a bounded slice rather than loading the complete dataset:

```python
import gpbiometricspy as gp

one = gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
small = one.iloc[:1800].copy().reset_index(drop=True)

print(small.shape)
print(small.attrs["source"])
print(small.attrs["synthetic"])
```

Load the complete demonstration only when you need all participants:

```python
all_demo = gp.load_kiosk_demo()
assert len(all_demo) == 69_120
assert len(gp.kiosk_demo_files()) == 36
```

`load_kiosk_demo()` records provenance in the returned frame attributes: the source identifies the frozen `gpbiometrics 2.0.0` synthetic kiosk demo and `synthetic` is `True`.

## Inspect the study design before analysing signals

The package exposes both a one-row overview and the participant-by-task design table:

```python
overview = gp.kiosk_demo_overview()
design = gp.kiosk_demo_trial_design()

print(overview)
print(design.head())
print(design[["interface_complexity", "feedback_clarity"]].value_counts())
```

When you need design factors beside sample-level data, join them explicitly rather than inferring condition from filenames or row order:

```python
analysis = one.merge(
    design[
        [
            "participant_id",
            "MEDIA_ID",
            "task_order",
            "interface_complexity",
            "feedback_clarity",
        ]
    ],
    on=["participant_id", "MEDIA_ID"],
    how="left",
    validate="many_to_one",
)
```

Keep that join logic visible in research code. Participant, task and media identity are part of the analysis provenance.

## Choose a workflow from the recorded evidence

| What you want to inspect | Start with | Continue to |
|---|---|---|
| Dataset structure, units, missingness and channel identity | `load_kiosk_demo()` + overview/design | [Validate a new dataset](guides/validate-dataset.md) |
| EDA/GSR and candidate SCR structure | conductance channel + task/event context | [EDA / SCR example](examples/eda-scr.md) |
| PPG, HR, IBI and variability inputs | waveform/interval source + units | [PPG / HRV example](examples/ppg-hrv.md) |
| Pupil, gaze and AOI summaries | gaze validity + AOI definitions | [Pupil / gaze / AOI example](examples/pupil-gaze.md) |
| TTL/event timing across channels | explicit event markers + timebase | [Multimodal example](examples/multimodal.md) |
| Missingness, activity and report-ready diagnostics | complete analysis frame | [QC + reporting example](examples/quality-reporting.md) |
| External-tool handoff | verified source object + backend assumptions | [Interoperability example](examples/interoperability.md) |

!!! tip "Want one continuous walkthrough?"
    Start with the [hands-on research guide](guides/hands-on-eda-research.md) or the [worked research recipes](examples/index.md#worked-research-recipes), then return here whenever you need to inspect the synthetic design or provenance.

## A compact reproducible starting pattern

Use a small, explicit sequence that you can later replace with real-data import and mapping:

```python
import gpbiometricspy as gp

# 1. Load bounded synthetic data.
dat = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)

# 2. Keep the design available as a separate provenance object.
design = gp.kiosk_demo_trial_design()

# 3. Inspect event identity before event-locking signals.
events = gp.extract_gazepoint_ttl_events(
    dat,
    ttl_columns=["TTL0"],
    group_columns=["participant_id"],
)

# 4. Produce a visual checkpoint before modelling.
fig = gp.plot_gazepoint_multimodal_timeline(
    dat,
    time_col="TIME",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
    title="Synthetic kiosk multimodal timeline",
)
```

This pattern intentionally keeps **data**, **design**, **events**, and **visual evidence** as separate objects. That makes it easier to audit what changed when you adapt the workflow to real exports.

## What to retain when adapting an example

<div class="gp-guide-grid" data-demo-evidence-checklist>
<div class="gp-guide-card"><span class="gp-eyebrow">Input</span><h3>Source and schema</h3><p>File identity, importer settings, column mapping, units, sample rate and participant/session/task identifiers.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Design</span><h3>Condition mapping</h3><p>Trial definitions, event semantics, task order, grouping variables and the exact keys used to join design to samples.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Processing</span><h3>Parameters and exclusions</h3><p>QC decisions, thresholds, filters, interpolation, baseline/window settings and every exclusion rule.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Output</span><h3>Derived evidence</h3><p>Event tables, analysis-ready summaries, figures, diagnostics and the settings required to reproduce them.</p></div>
</div>

## Before replacing synthetic data with real exports

Use the demo to learn object shapes and workflow order—not to choose scientific thresholds blindly. Before switching inputs:

1. validate the real export schema and units;
2. confirm signal identity and source provenance;
3. establish participant/session/trial grouping explicitly;
4. audit missingness and signal activity before preprocessing;
5. establish clock relationships before multimodal event locking;
6. document every transformation that changes an analysis denominator;
7. preserve raw inputs and reproducible derived outputs separately.

Then follow the [workflow chooser](guides/index.md#choose-your-workflow) from the evidence you actually have.

<div class="gp-science-boundary">
<strong>Synthetic-data boundary.</strong> The kiosk data are artificial and are intended for examples, tests and reproducible workflow demonstrations. Do not interpret their values or generated figures as real human physiology, emotion, stress, cognition, attention, trust, preference, health status, diagnosis, causal effects or evidence of hardware-level synchronization.
</div>
