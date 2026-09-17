# Troubleshooting and diagnostics

<div class="gp-page-intro" data-troubleshooting-guide>
Use this guide when a workflow **runs but the evidence looks wrong**, when a validation step warns or fails, or when you are unsure whether the problem belongs to schema, timing, signal quality, event alignment, modelling, or reporting. The goal is to identify the earliest broken assumption and fix that layer before changing downstream parameters.
</div>

## Diagnose the earliest failing layer

<div class="gp-steps" data-troubleshooting-stages>
<div class="gp-step"><strong>1 · Source</strong>Confirm the file, export type, acquisition software, device, session, participant, and whether each channel is measured, vendor-derived, or reconstructed.</div>
<div class="gp-step"><strong>2 · Schema</strong>Check column identity, data types, units, grouping variables, and whether required fields are truly present rather than merely similarly named.</div>
<div class="gp-step"><strong>3 · Time</strong>Inspect timestamps/counters for resets, duplicates, gaps, non-monotonic rows, and unit ambiguity before resampling or event locking.</div>
<div class="gp-step"><strong>4 · Signal</strong>Quantify missingness, flat or zero channels, improbable ranges, dropouts, and validity evidence before tuning processing thresholds.</div>
<div class="gp-step"><strong>5 · Events</strong>Verify TTL/event semantics, duplicates, missing events, coverage, clock ownership, and matching before creating event-relative quantities.</div>
<div class="gp-step"><strong>6 · Model/report</strong>Only after the earlier layers are defensible should you diagnose grouping, convergence, prediction semantics, or report completeness.</div>
</div>

A downstream error is often only a symptom. For example, an empty event-locked table can originate from missing TTL edges, mismatched clocks, wrong time units, or grouping identifiers that do not overlap. Changing the event window first can hide the cause rather than solve it.

## Minimal triage scaffold

Start with a bounded copy of the same data that failed. Do not immediately rewrite the pipeline.

```python
import gpbiometricspy as gp

# `dat` should be the same standardized table that exposed the problem.
schema = gp.detect_gazepoint_biometric_schema(dat)
timebase = gp.detect_gazepoint_biometric_timebase(
    dat,
    time_col="TIME",
    counter_col="CNT",
)
missing = gp.summarize_gazepoint_missingness(
    dat,
    signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
)
activity = gp.audit_gazepoint_signal_activity(
    dat,
    signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
    group_cols=["participant_id"],
)
resets = gp.audit_gazepoint_time_resets(
    dat,
    time_col="TIME",
    group_cols=["participant_id"],
)
readiness = gp.run_gazepoint_biometrics_real_data_readiness(
    dat,
    min_rows=100,
)
```

Inspect the returned objects rather than reducing them to a single pass/fail label. In particular, `audit_gazepoint_signal_activity()` and `audit_gazepoint_time_resets()` return structured audit objects with detailed tables that explain the summary status.

## Symptom → diagnostic → action

| Symptom | Check first | Useful route | Do not do first |
|---|---|---|---|
| Expected channel is absent | schema and source export | `detect_gazepoint_biometric_schema()` + [new-dataset validation](validate-dataset.md) | rename an unrelated column to satisfy code |
| Channel exists but is unusable | missingness and signal activity | `summarize_gazepoint_missingness()` + `audit_gazepoint_signal_activity()` | tune detector thresholds |
| Timing looks irregular | observed time deltas/resets | `detect_gazepoint_biometric_timebase()` + `audit_gazepoint_time_resets()` | resample immediately |
| Event table is empty | marker values and edge semantics | `extract_gazepoint_ttl_events()` + [multimodal example](../examples/multimodal.md) | enlarge response windows |
| Event-locked rows are empty | event clock, signal clock, group overlap | [Timebase and alignment](timebase-alignment.md) | assume equal clocks from matching labels |
| PPG/HRV result looks implausible | interval source, units, accepted/rejected peaks | [PPG / HRV example](../examples/ppg-hrv.md) | treat sampled HR as RR/NN intervals |
| Pupil/gaze summary changes unexpectedly | validity, interpolation, AOI denominator | [Pupil / gaze / AOI example](../examples/pupil-gaze.md) | interpret change as attention or preference |
| Model fails or predictions look strange | analysis unit, grouping, outcome support | [Choose a modelling strategy](model-selection.md) | simplify grouping without scientific justification |
| Results cannot be reproduced later | settings, software identity, retained QC | [Reporting and reproducibility](reporting-reproducibility.md) | reconstruct settings from memory |

## Scenario 1 — a signal is present but effectively inactive

A column can exist while containing only zeros, a constant, too few non-zero values, or almost entirely missing observations. Diagnose activity by group before processing.

```python
activity = gp.audit_gazepoint_signal_activity(
    dat,
    signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
    group_cols=["participant_id"],
)

print(activity["overview"])
print(activity["signal_by_group"])
print(activity["inactive_groups"])
print(activity["inactive_signals"])
```

If a modality is inactive for an entire participant/session, downstream decomposition or feature extraction should not manufacture apparent evidence from the absence of signal variation. Preserve the inactive status as part of QC.

## Scenario 2 — timestamps reset or repeat

Use both a broad timebase detector and explicit row/segment diagnostics.

```python
timebase = gp.detect_gazepoint_biometric_timebase(
    dat,
    time_col="TIME",
    counter_col="CNT",
)

resets = gp.audit_gazepoint_time_resets(
    dat,
    time_col="TIME",
    group_cols=["participant_id"],
)

print(resets["overview"])
print(resets["segment_summary"])
print(resets["row_flags"].head())
```

A reset can indicate a new segment/session rather than a bad row. Keep the original clock evidence and determine the correct grouping/segment interpretation before creating a continuous time axis.

## Scenario 3 — TTL events are missing or duplicated

Extract the event evidence before alignment.

```python
events = gp.extract_gazepoint_ttl_events(
    dat,
    ttl_columns=["TTL0"],
    group_columns=["participant_id"],
)

print(events.head())
print(events[["participant_id", "event_order", "ttl_value"]])
```

Check whether the channel encodes rising edges, changes, sustained active periods, or another acquisition-specific convention. A technically valid numeric marker is not automatically a scientifically valid event label.

## Scenario 4 — event locking produces no rows

Diagnose four things in order:

1. the event table actually contains the intended events;
2. the event timestamps and signal timestamps use compatible units;
3. the event and signal rows refer to the same participant/session/trial groups;
4. the requested window overlaps recorded samples.

Only after those checks should you consider widening a window. If two streams come from different clocks, use explicit clock-alignment evidence rather than forcing them into one axis.

## Scenario 5 — a model fits but answers the wrong question

Successful optimization does not guarantee a defensible estimand. Verify:

- the row represents the intended scientific analysis unit;
- repeated observations retain participant/item/trial identifiers;
- crossed and nested structures are not silently collapsed;
- holdout units match the claimed generalisation target;
- conditional predictions for observed groups are not reported as population predictions for unseen groups;
- outcome support matches the selected family.

Use the [modelling decision guide](model-selection.md) before interpreting coefficients, feature importance, or predictive performance.

## Build a useful diagnostic report

When asking for help or filing an issue, provide a minimal evidence bundle rather than only the final exception text.

```text
diagnostic-report/
├── package-python-versions.txt
├── schema-summary.txt
├── timebase-summary.txt
├── signal-activity-overview.csv
├── signal-activity-by-group.csv
├── time-reset-overview.csv
├── time-reset-segments.csv
├── event-preview.csv
├── minimal-reproduction.py
└── error-traceback.txt
```

For private research data, do **not** attach participant-level raw exports merely to make a bug report complete. Prefer a minimal synthetic/reduced reproduction plus structural summaries unless the data can be shared under the applicable governance rules. See [Private real-data validation](../real-data-validation.md).

## What information makes a bug reproducible?

Include:

- `gpbiometricspy` version and Python version;
- operating system when the behavior may be platform-specific;
- exact function call and relevant parameter values;
- shape and column names of the minimal input;
- grouping/time/event column names and units;
- complete exception type and message;
- whether the issue reproduces with bundled synthetic data;
- the smallest code path that still triggers it;
- any QC warning that appeared before the failure.

Exclude secrets, credentials, participant identifiers, and private raw data unless you have a legitimate approved route to share them.

## Stop conditions

<div class="gp-science-boundary">
<strong>Stop rather than patch around missing evidence.</strong> Do not continue by silently changing units, inventing events, interpolating across unknown clock resets, relabelling sampled HR as HRV, replacing missing participant/item structure with row-level independence, or interpreting physiological/gaze outputs as latent psychological states. A failed diagnostic can be the scientifically correct result.
</div>

## Recovery routes

- **Unknown schema or channel identity:** [Validate a new dataset](validate-dataset.md)
- **Clock/reset/alignment problem:** [Timebase and alignment](timebase-alignment.md)
- **EDA/SCR problem:** [EDA / GSR / SCR example](../examples/eda-scr.md)
- **PPG/HRV problem:** [PPG / HRV example](../examples/ppg-hrv.md)
- **Pupil/gaze/AOI problem:** [Pupil / gaze / AOI example](../examples/pupil-gaze.md)
- **QC/reporting problem:** [Quality control + reporting example](../examples/quality-reporting.md)
- **Model/design problem:** [Choose a modelling strategy](model-selection.md)
- **Replay/reproducibility problem:** [Reporting and reproducibility](reporting-reproducibility.md)
- **Full frozen R-companion troubleshooting workflow:** [Troubleshooting readiness](../articles/troubleshooting-readiness.md)

!!! tip "Want a known-good baseline?"
    Reproduce the [synthetic demo](../demo.md) or the [runnable EDA example](../examples/end-to-end-eda.md) unchanged. If the bundled example works but the research export fails, the difference is evidence: compare schema, units, grouping, timing, event coverage, and signal activity before changing algorithms.
