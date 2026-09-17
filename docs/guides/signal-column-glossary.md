# Signal and column glossary

<div class="gp-page-intro" data-signal-column-glossary>
Use this page when you know a Gazepoint-style column name but are unsure what role the package assigns to it. The glossary mirrors the package's conservative column inventory and separates **signal values**, **validity fields**, **time/identity fields**, and **fixation fields** so similarly named columns are not treated as scientifically interchangeable.
</div>

!!! warning "Names are evidence, not proof"
    A familiar column name does not prove that a channel is active, correctly scaled, synchronized, or suitable for the intended analysis. Verify the actual export, units, validity flags, timebase, acquisition configuration, and signal activity before analysis.

## Inspect your own table programmatically

The safest starting point is the package inventory rather than a handwritten assumption:

```python
import gpbiometricspy as gp

inventory = gp.check_gazepoint_biometric_columns(dat)
print(inventory[inventory["present"]])
```

`check_gazepoint_biometric_columns()` reports the expected column name, signal family, package role, and whether the field is present. Presence alone does **not** mean the channel is active.

```python
active = gp.detect_active_biometric_channels(dat)
print(active)
```

For participant/session-level activity, continue with `audit_gazepoint_signal_activity()` rather than relying only on file-level presence.

## EDA / GSR fields

| Column | Package role | Treat as | Important boundary |
|---|---|---|---|
| `GSR` | `gsr_raw_or_resistance` | recorded GSR/resistance-like source | verify the device/export units before transforming it |
| `GSR_US` | `gsr_conductance_microsiemens` | conductance in µS according to the package contract | audit units and ranges before EDA/SCR processing |
| `GSR_US_TONIC` | `gsr_tonic_component` | tonic conductance component | a derived component, not a separate sensor |
| `GSR_US_PHASIC` | `gsr_phasic_component` | phasic conductance component | useful for response detection only after provenance/QC are established |
| `GSRV` | `gsr_validity` | GSR validity field | validity metadata is not a physiological signal |

A conductance waveform or derived phasic response is not a direct label of emotion, stress, arousal, preference, deception, or diagnosis.

## Cardiac / pulse fields

| Column | Package role | Treat as | Important boundary |
|---|---|---|---|
| `HR` | `heart_rate_bpm` | heart-rate series in beats/minute under the package contract | sampled HR values are not RR/NN intervals |
| `HRV` | `heart_rate_validity_not_hrv_metric` | **validity field** | despite the name, do not treat this field as a heart-rate-variability metric |
| `HRP` | `pulse_signal` | pulse waveform/source channel | establish waveform sampling and peak provenance before deriving intervals |
| `IBI` | `interbeat_interval_seconds` | interbeat intervals in seconds under the package contract | verify source/cleaning before calling intervals RR, NN, HRV, or PRV inputs |

<div class="gp-science-boundary">
<strong>Cardiac provenance boundary.</strong> `HR`, `HRP`, `IBI`, and `HRV` have different roles. Never substitute one for another because a downstream function accepts numeric input. In particular, `HRV` is treated by the package as a validity field, not an HRV statistic.
</div>

## Engagement-dial fields

| Column | Package role | Treat as | Important boundary |
|---|---|---|---|
| `DIAL` | `dial_value` | engagement-dial value | interpret according to the task/instrument definition, not as an intrinsic psychological state |
| `DIALV` | `dial_validity` | dial validity field | use it to qualify the dial source rather than as an outcome itself |

## TTL / synchronization fields

| Column | Package role | Treat as | Important boundary |
|---|---|---|---|
| `TTL0` … `TTL6` | `ttl_channel` | marker/synchronization channels | establish edge semantics and event meaning before alignment |
| `TTLV` | `ttl_validity` | TTL validity field | a valid marker value still requires correct event semantics and clock provenance |

TTL channels can encode rising edges, changes, sustained states, or acquisition-specific marker conventions. Inspect the actual event values with `extract_gazepoint_ttl_events()` before treating them as experimental events.

## Time, counter, participant, and media identity

| Column | Package role | Typical use | Important boundary |
|---|---|---|---|
| `CNT` | `sample_counter` | row/sample ordering | a counter is not automatically elapsed seconds |
| `TIME` | `recording_time` | primary recording-time candidate | verify units, resets, duplicates, and clock ownership |
| `TIME_TICK` | `recording_tick` | tick/timing metadata | do not assume a unit or relation to `TIME` without evidence |
| `USER` | `user_label` | user/participant label | retain as provenance; do not silently replace study identifiers |
| `USERID` | `user_identifier` | user identifier | confirm the experimental grouping represented by this field |
| `MEDIA_ID` | `media_identifier` | stimulus/media identifier | useful for trial/stimulus joins only when mapping is verified |
| `MEDIA_NAME` | `media_name` | stimulus/media label | labels are not guaranteed unique experimental-condition keys |

For timing problems, use both `detect_gazepoint_biometric_timebase()` and `audit_gazepoint_time_resets()`. For design joins, use explicit participant/trial/media keys and validate join cardinality.

## Fixation fields

| Column | Package role | Treat as | Important boundary |
|---|---|---|---|
| `FPOGX` | `fixation_x` | fixation X coordinate | coordinate meaning depends on export/stimulus space |
| `FPOGY` | `fixation_y` | fixation Y coordinate | keep coordinate space and stimulus geometry with AOI analyses |
| `FPOGS` | `fixation_start_time` | fixation start time | verify timebase/units before linking to events |
| `FPOGD` | `fixation_duration` | fixation duration | confirm vendor/event-detector provenance and units |
| `FPOGID` | `fixation_identifier` | fixation identifier | an identifier does not establish validity or event quality |

Vendor fixation fields and fixations derived from sample-level gaze are different provenance paths. Do not combine them without recording the detector/source and relevant settings.

## Other gaze and pupil fields

Gazepoint exports can contain additional gaze, pupil, validity, and binocular fields beyond the conservative biometric inventory above. Do not infer their units or semantics from abbreviations alone. Use the [Pupil / gaze / AOI example](../examples/pupil-gaze.md), inspect the actual export documentation, and retain coordinate space, eye identity, validity coding, calibration context, and detector provenance.

## Measured, validity, identity, and derived are different roles

<div class="gp-guide-grid" data-column-role-grid>
<div class="gp-guide-card"><span class="gp-eyebrow">Signal</span><h3>Recorded values</h3><p>Examples include conductance, pulse, heart-rate, interval, dial, or gaze values. Verify units and acquisition source.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Validity</span><h3>Quality metadata</h3><p>Fields such as `GSRV`, `HRV`, `DIALV`, and `TTLV` qualify a source. They are not substitutes for the source signal.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Identity</span><h3>Grouping and provenance</h3><p>User, media, participant, trial, file, or session identifiers define joins and analysis structure rather than physiology.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Derived</span><h3>Processed quantities</h3><p>Tonic/phasic components, detected events, AOI summaries, baselines, and model-ready features inherit assumptions from earlier processing.</p></div>
</div>

## A safe column-mapping pattern

Do not rename first and investigate later. Build a mapping after inspecting the export:

```python
columns = gp.check_gazepoint_biometric_columns(dat)
known = columns.loc[columns["present"]].copy()
print(known[["column", "signal", "role"]])

# Only after verification:
participant_col = "participant_id"
time_col = "TIME"
eda_col = "GSR_US"
event_col = "TTL0"
```

Record that mapping in the analysis configuration or methods evidence so downstream code does not silently reinterpret fields.

## Common name traps

- **`HRV` is not an HRV metric in this contract.** It is a heart-rate validity field.
- **`HR` is not an interval series.** Do not use sampled BPM values as RR/NN intervals.
- **`IBI` does not automatically mean cleaned NN intervals.** Verify how the intervals were produced and cleaned.
- **`GSR_US_TONIC` / `GSR_US_PHASIC` are derived components.** Preserve the method/provenance used to obtain them.
- **TTL values are not self-describing events.** Verify edge rules, labels, coverage, and clock ownership.
- **Coordinates are incomplete without coordinate space.** AOI/gaze results require stimulus geometry and validity rules.
- **Presence is not activity.** A column can be present but all-zero, constant, invalid, or missing.

## Where to go next

- Unknown or unfamiliar export → [Validate a new dataset](validate-dataset.md)
- Warning, empty output, or contradictory fields → [Troubleshooting and diagnostics](troubleshooting.md)
- EDA/GSR → [EDA / GSR / SCR example](../examples/eda-scr.md)
- Cardiac/pulse → [PPG / HRV example](../examples/ppg-hrv.md)
- Pupil/gaze/AOI → [Pupil / gaze / AOI example](../examples/pupil-gaze.md)
- TTL/multiple clocks → [Timebase and alignment](timebase-alignment.md)
- Exact API behavior → [API reference](../api/index.md)

!!! note "Scientific interpretation"
    Column roles describe data provenance and package semantics. They do not establish construct validity, psychological meaning, clinical interpretation, causal effects, or sensor accuracy. Those require study-specific measurement and validation evidence.
