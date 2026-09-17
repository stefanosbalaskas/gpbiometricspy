# Bring your own export safely

<div class="gp-page-intro" data-bring-your-own-export-guide>
Use this guide when your CSV has unfamiliar or project-specific column names and you want to adapt it to `gpbiometricspy` without erasing provenance. The goal is not to make every file look like the bundled demo. The goal is to make **every mapping decision visible, reviewable, and reversible** before analysis.
</div>

<div class="gp-guide-grid" data-export-adaptation-stages>
<div class="gp-guide-card"><span class="gp-eyebrow">1 · Preserve</span><h3>Keep the source untouched</h3><p>Retain the original file, original column names, source path/checksum when appropriate, and acquisition documentation.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">2 · Inspect</span><h3>Map names before renaming</h3><p>Ask the package what aliases it recognises and review the proposed standard names rather than silently replacing labels.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">3 · Verify</span><h3>Check units, time and activity</h3><p>A recognised name is only a hypothesis about the field. Verify units, signal activity, validity, resets, event semantics and clock ownership.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">4 · Standardise</span><h3>Rename deliberately</h3><p>Apply standard names only after you have reviewed the mapping and preserved the source-to-standard correspondence.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">5 · Audit</span><h3>Run schema and event checks</h3><p>Confirm the resulting table contains the evidence required by your intended workflow before deriving measures.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">6 · Record</span><h3>Export the adaptation evidence</h3><p>Keep the mapping, schema, timebase, event table, warnings and software identity with the analysis.</p></div>
</div>

## Run the checked adaptation example

A complete synthetic stand-in is shipped at:

```text
examples/hands-on/bring-your-own-export.py
```

Run it from the repository root:

```bash
python examples/hands-on/bring-your-own-export.py
```

Or direct outputs to a separate folder:

```bash
GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR=artifacts/my-export-adaptation \
python examples/hands-on/bring-your-own-export.py
```

The example deliberately starts with project-style names such as `subject_id`, `timestamp_s`, `eda_us`, `heart_rate`, `interbeat_interval`, `event_marker`, and `ttl_validity`. It then records the proposed mapping before standardising anything.

Expected outputs include:

```text
source_like_export.csv
column_name_map.csv
standardized_preview.csv
schema_overview.csv
schema_columns.csv
timebase_overview.csv
timebase_interval_summary.csv
ttl_events.csv
adaptation_manifest.json
```

The bundled values are synthetic. The workflow demonstrates **how to adapt evidence**, not what your own file means.

## 1. Load without rewriting the source

For a normal CSV, start with pandas or the package importer appropriate to the source format. Keep the original object separate from the analysis copy.

```python
import pandas as pd
import gpbiometricspy as gp

raw = pd.read_csv("my_export.csv")
print(raw.shape)
print(raw.columns.tolist())
```

Do not begin by replacing names based only on an abbreviation. First preserve enough source context to answer:

- which software/hardware produced the file;
- which participant/session/trial the rows belong to;
- which clock or counter each time field represents;
- what units are documented for each recorded signal;
- what validity flags mean;
- what event/TTL values encode;
- whether columns are measured, vendor-derived, or analyst-derived.

## 2. Preview the package's name mapping

`standardise_gazepoint_biometric_names()` can recognise a conservative set of common aliases. Use `rename=False` first:

```python
name_map = gp.standardise_gazepoint_biometric_names(raw, rename=False)
print(name_map)
```

A project-style table might produce mappings such as:

| Original name | Standard name | Meaning still requiring verification |
|---|---|---|
| `subject_id` | `USER` | whether this is the intended participant/group identifier |
| `timestamp_s` | `TIME` | unit and clock ownership |
| `eda_us` | `GSR_US` | whether values are truly conductance in µS |
| `heart_rate` | `HR` | source and temporal resolution of the BPM series |
| `interbeat_interval` | `IBI` | unit, beat provenance, cleaning/rejection rules |
| `event_marker` | `TTL` | event values and edge/state semantics |
| `ttl_validity` | `TTLV` | how marker validity was encoded |

!!! warning "Recognition is not validation"
    Alias recognition is intentionally lexical. It does not inspect the acquisition system and cannot prove a unit, sampling frequency, event definition, sensor identity, synchronization accuracy, or scientific interpretation.

For exact field roles, keep the [Signal and column glossary](signal-column-glossary.md) open while mapping.

## 3. Standardise only after reviewing the map

Once the mapping is defensible:

```python
standard = gp.standardise_gazepoint_biometric_names(raw, rename=True)
```

Retain `name_map` as an analysis artifact. Avoid deleting the source columns from the only copy of the data.

If two source columns collapse to the same standard name, the standardiser keeps names unique. Treat that as a prompt to inspect the duplicate roles rather than choosing one automatically.

## 4. Audit the resulting schema

Run schema detection on the standardised table:

```python
schema = gp.detect_gazepoint_biometric_schema(standard)
print(schema["overview"])
print(schema["columns"])
print(schema["notes"])
```

Inspect at least:

- whether a usable timing field exists;
- whether the signal families you expect are present and active;
- whether `IBI` is genuinely an interval source;
- whether `HRV` is being treated as a validity/vendor field rather than an HRV statistic;
- whether GSR/EDA unit interpretation is documented;
- whether identity/trial/media columns preserve your design structure.

Presence is not activity. A column filled with zero, missing, constant, or invalid values should not be treated as usable merely because it exists.

## 5. Verify the timebase explicitly

```python
timebase = gp.detect_gazepoint_biometric_timebase(
    standard,
    time_col="TIME",
)
print(timebase["overview"])
print(timebase["interval_summary"])
print(timebase["warnings"])
```

Then inspect resets or discontinuities with the [Timebase and alignment guide](timebase-alignment.md).

Do not infer seconds, milliseconds, ticks, or sampling rate solely from the column name when acquisition documentation or observed intervals disagree.

## 6. Treat event markers as data, not labels

If your mapped event field becomes `TTL`, inspect changes before using it for event locking:

```python
events = gp.extract_gazepoint_ttl_events(
    standard,
    ttl_columns=["TTL"],
    group_columns=["USER"],
    validity_column="TTLV",
    require_validity=True,
)
print(events.head())
```

Check:

- what each marker value means;
- whether the event is represented by a change, rising edge, non-zero state, or another convention;
- whether expected events are missing or duplicated;
- whether the validity field applies to the marker;
- whether the event and signal timestamps belong to the same clock.

A successful event extraction does not prove correct synchronization.

## 7. Create a small adaptation manifest

A lightweight manifest makes the mapping reproducible:

```python
import json

manifest = {
    "source_file": "my_export.csv",
    "column_mapping": dict(
        zip(name_map["original_name"], name_map["standard_name"])
    ),
    "participant_column": "USER",
    "time_column": "TIME",
    "eda_column": "GSR_US",
    "event_column": "TTL",
    "notes": "Units and event semantics verified against acquisition documentation.",
}

with open("adaptation_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
```

For a manuscript or shared analysis, also retain software version, acquisition settings, exclusion decisions, QC outputs and timing evidence. Continue with [Reporting and reproducibility](reporting-reproducibility.md).

## A minimum acceptance checklist

Before moving from adaptation to substantive processing, confirm all of the following:

- [ ] the original file is preserved and identifiable;
- [ ] the source-to-standard column map is saved;
- [ ] participant/session/trial/media identifiers match the study design;
- [ ] time units and clock ownership are known or uncertainty is explicitly recorded;
- [ ] sampling-rate claims agree with observed timing evidence;
- [ ] signal units and validity flags have documented meanings;
- [ ] channels are active rather than merely present;
- [ ] IBI/RR provenance is known before HRV/PRV analysis;
- [ ] event values and edge/state semantics are verified;
- [ ] cross-stream alignment is justified before multimodal event locking;
- [ ] derived variables remain traceable to their measured/vendor source columns.

## Common adaptation mistakes

| Mistake | Why it fails | Better action |
|---|---|---|
| Rename everything immediately | destroys the visible source vocabulary | save and review the mapping first |
| Assume `HRV` means HRV metric | in this contract it is treated as a validity/vendor field | use genuine interval data for HRV calculations |
| Use `HR` as RR/NN input | sampled BPM is not an interval series | establish interval provenance from `IBI`/RR or waveform peaks |
| Treat `eda` as µS automatically | the same label can represent differently scaled sources | verify units from export/acquisition documentation |
| Convert every timestamp to seconds by guess | can hide resets and clock mismatches | inspect time columns and observed intervals first |
| Treat every non-zero marker as the same event | loses event semantics | inspect marker transitions, values and task documentation |
| Join conditions by row order | breaks when rows are dropped/reordered | join using explicit participant/trial/media keys and validate cardinality |
| Continue after ambiguous provenance | creates apparently clean but scientifically unsupported outputs | stop and resolve the evidence gap |

## When automatic aliases are not enough

If your export uses a genuinely different schema, keep an explicit project mapping rather than forcing names into a misleading standard label:

```python
project_mapping = {
    "P_CODE": "participant_id",
    "CLOCK_SEC": "recording_seconds",
    "EDA_CHANNEL_2": "conductance_channel_2",
}
```

You can then create an analysis frame with the names your code expects while preserving the original columns or a source-to-analysis dictionary. The package does not require you to pretend an uncertain field is a canonical Gazepoint field.

<div class="gp-science-boundary">
<strong>Evidence boundary.</strong> Standardising names is an organizational operation. It does not establish sensor validity, physiological meaning, psychological constructs, diagnosis, causality, timing accuracy, or hardware synchronization. Those claims require separate acquisition, measurement, design and validation evidence.
</div>

!!! tip "Something still looks wrong?"
    Use [Troubleshooting and diagnostics](troubleshooting.md) to locate the earliest failed assumption, or return to [Validate a new dataset](validate-dataset.md) for the full pre-analysis audit path.
