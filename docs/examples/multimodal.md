# Multimodal event-alignment example

<div class="gp-page-intro">
Use this route when eye tracking, physiology, task events, TTL markers, or external streams need to be interpreted on a common timeline. The workflow makes timing evidence explicit before event-locked summaries are created.
</div>

## 1. Load the demonstration

```python
import gpbiometricspy as gp

dat = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)
```

## 2. Extract task/TTL events

```python
events = gp.extract_gazepoint_ttl_events(
    dat,
    ttl_columns=["TTL0"],
    group_columns=["participant_id"],
)
```

Inspect event identity and coverage before using the event table as a timing truth source.

## 3. Audit the signal timebase

```python
resets = gp.audit_gazepoint_time_resets(
    dat,
    time_col="TIME",
    group_cols=["participant_id"],
)
```

For multiple clock domains, continue with the [timebase provenance and multimodal alignment](../methods/timebase-provenance.md) layer rather than assuming equal clocks from matching labels.

## 4. Build event-locked summaries

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

## 5. Inspect the shared timeline

```python
fig = gp.plot_gazepoint_multimodal_timeline(
    dat,
    time_col="TIME",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
    title="Multimodal Gazepoint timeline",
)
```

![Multimodal physiology and pupil timeline](../assets/generated/multimodal-timeline.png)

## When another clock is involved

A second stream should bring its own timing evidence. A defensible alignment record includes:

- original timestamps/counters for each stream;
- clock identity;
- matched anchors or declared offsets;
- offset/drift mapping;
- residuals after alignment;
- corrected overlap interval;
- any interpolation/resampling performed after clock correction.

The [Timebase and alignment guide](../guides/timebase-alignment.md) gives the complete order of operations.

## Practical checklist

- Verify TTL edge/event semantics.
- Audit duplicate/missing events and participant/trial coverage.
- Confirm which clock each timestamp belongs to.
- Estimate rather than assume offsets when anchors exist.
- Keep clock correction separate from interpolation.
- Check that corrected streams have positive temporal overlap.
- Define event windows only at a precision supported by the timing evidence.

## Scientific boundary

<div class="gp-science-boundary">
Alignment establishes a declared temporal relation among recorded streams. It does not by itself prove hardware synchronization, causal order, sensor validity, or psychological meaning of any channel.
</div>

## Continue

- [Timebase and alignment guide](../guides/timebase-alignment.md)
- [Timebase provenance method](../methods/timebase-provenance.md)
- [Multimodal event dashboard](../articles/multimodal-event-dashboard.md)
- [MNE, EEG and LSL workflow](../articles/mne-eeg-lsl-workflow.md)
