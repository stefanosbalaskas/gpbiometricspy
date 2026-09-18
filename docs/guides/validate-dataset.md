# Validate a new dataset

<div class="gp-page-intro">
Use this guide when moving from bundled demonstrations to a new Gazepoint or multimodal research dataset. The purpose is to establish what the recorded data can support before preprocessing, feature extraction, or modelling.
</div>

## Validation sequence

<div class="gp-steps">
<div class="gp-step"><strong>Identify the source</strong>Record file type, acquisition software, device, session, participant, and whether each channel is raw, cleaned, derived, or vendor-precomputed.</div>
<div class="gp-step"><strong>Check schema</strong>Confirm required columns, data types, grouping variables, units, and duplicate or missing identifiers.</div>
<div class="gp-step"><strong>Audit timing</strong>Inspect observed timestamps, sampling intervals, resets, duplicates, gaps, and any counter-derived timebase before event locking or multimodal fusion.</div>
<div class="gp-step"><strong>Audit signal availability</strong>Quantify missingness, flatlines, implausible ranges, dropouts, and channel-specific validity evidence.</div>
<div class="gp-step"><strong>Audit design and events</strong>Check participant/trial balance, expected event coverage, condition cells, and event-to-signal matching.</div>
<div class="gp-step"><strong>Freeze the evidence</strong>Retain settings, warnings, QC tables, figures, software identity, and any fail-closed decisions before downstream transformation.</div>
</div>

## A compact validation scaffold

```python
import gpbiometricspy as gp

# Replace `dat` with your standardized research table.
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

missing = gp.plot_gazepoint_missingness(
    dat,
    cols=["GSR_US", "HR", "IBI", "LPMM"],
    time_col="TIME",
)
```

Adapt the column names to your export rather than renaming a scientifically different quantity merely to satisfy an example.

## What to verify by modality

| Modality | Minimum evidence before analysis | Common mistake to avoid |
|---|---|---|
| EDA / GSR | units, range, missingness, flatlines, sampling/timing, decomposition settings | treating conductance changes as direct emotion labels |
| PPG waveform | observed sampling, waveform quality, accepted/rejected peaks, interval construction | computing HRV from a sampled HR series |
| RR / NN / IBI | source identity, units, cleaning status, interval plausibility | silently calling all intervals NN-HRV |
| Pupil | eye/channel identity, validity, missingness/blinks, units, baseline design | interpreting pupil change without luminance/task context |
| Gaze / fixation | coordinate space, validity, timebase, AOI definitions, event detector source | mixing vendor fixations and sample-derived events without provenance |
| TTL / events | edge definition, event identity, duplicates, event coverage, clock relation | assuming event and signal clocks are identical because labels match |
| External streams | clock identity, observed rate, offset/drift evidence, overlap | resampling before documenting original timing evidence |

## Design audit before modelling

When participant, trial, condition, or item structure matters, inspect it explicitly before fitting a model.

```python
design = gp.audit_gazepoint_experiment_design(
    dat,
    participant_col="participant_id",
    trial_col="MEDIA_ID",
    condition_col="interface_complexity",
)

fig = gp.plot_gazepoint_design_coverage(design)
```

The generated documentation includes a design-coverage example in the [Plot gallery](../plot-gallery.md#design-and-inference).

## QC findings are not automatic exclusions

Validation can produce warnings, failed checks, dropout flags, invalid samples, missing events, or sparse design cells. Preserve those findings before deciding what they mean for a specific analysis. A local channel problem does not automatically justify participant-wide removal, and a warning label should not silently change the denominator.

Use the [QC and exclusion decision ledger](../qc-exclusion-decision-ledger.md) to separate four things explicitly: the observed QC evidence, the decision criterion, the reviewed `RETAIN` / `EXCLUDE` / `REVIEW` state, and the before/after denominator consequence. Its checked synthetic example deliberately creates known QC issues and confirms that **zero automatic exclusions** are applied.

<div class="gp-decision">
<strong>Safe default:</strong> route unresolved QC findings to review. Apply exclusions only in a separate reproducible step with an explicit scope, reason, and denominator audit.
</div>

## Fail-closed decisions are valid outcomes

Validation is not a ritual that every dataset automatically passes. Stop or narrow the analysis when:

- the recorded timebase cannot support the requested event precision;
- source identity is insufficient to distinguish HRV, PRV, sampled HR, or vendor metrics;
- required conditions or events are systematically absent;
- grouping or item structure is too sparse for the intended model;
- preprocessing would require reconstructing information that was never sampled;
- the only way forward is to silently change units, labels, or scientific meaning.

## Evidence to retain

- original filename/source metadata;
- package and Python versions;
- schema/column map;
- observed timing audit;
- modality-specific QC tables;
- design/event coverage tables;
- generated QC figures;
- explicit warnings and accepted exceptions;
- exclusion-decision ledger with scope and rationale where exclusions are considered or applied;
- analysis-specific before/after denominator audit;
- downstream preprocessing settings.

!!! tip "Next"
    If the dataset contains multiple clocks or streams, continue with [Timebase and alignment](timebase-alignment.md). If QC findings require inclusion/exclusion decisions, continue with the [QC and exclusion decision ledger](../qc-exclusion-decision-ledger.md). Otherwise choose the appropriate [domain example](../examples/index.md).
