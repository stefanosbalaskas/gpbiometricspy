# Study metadata and data dictionary

<div class="gp-page-intro" data-study-metadata-dictionary>
A reproducible analysis needs more than a folder layout and renamed columns. Before substantive processing, record what each field is supposed to mean, where it came from, which clock owns it, which units are declared, which identifiers define the design, and which event codes have researcher-confirmed semantics.
</div>

This guide sits between [Research project scaffold](research-project-scaffold.md) and [Bring your own export safely](bring-your-own-export.md). The scaffold gives the study a durable structure; the dictionary gives the recorded fields and events an explicit contract; adaptation then maps source exports into that contract without silently changing scientific meaning.

## Why a dictionary is part of the evidence

A column name is only a label. `HR`, `HRV`, `GSR`, `TIME`, `TTL0`, `FPOGX`, or `MEDIA_ID` can be recognized lexically while still leaving important questions unresolved.

<div class="gp-guide-grid" data-dictionary-evidence-grid>
<div class="gp-guide-card"><span class="gp-eyebrow">Identity</span><h3>What does one row represent?</h3><p>State participant, session, run, trial, item, AOI, fixation, event, and sample identifiers explicitly instead of inferring them later from row order or filenames.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Measurement</span><h3>What quantity was recorded?</h3><p>Separate waveform samples, vendor-derived metrics, validity flags, event codes, identifiers, and later analysis variables.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Units</span><h3>What scale is declared?</h3><p>Record declared source units and any verified conversion. Do not infer milliseconds, seconds, microsiemens, beats/minute, millimetres, pixels, or normalized coordinates from a plausible numeric range alone.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Time</span><h3>Which clock owns the value?</h3><p>Document device/application clock, reset behavior, absolute versus relative time, counter relationships, and the evidence used for cross-stream alignment.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Provenance</span><h3>Raw, cleaned, derived, or vendor-computed?</h3><p>Retain the transformation/source boundary so a downstream variable cannot silently masquerade as a directly recorded channel.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Events</span><h3>What does an event code mean?</h3><p>Keep edge/state behavior, code labels, expected coverage, grouping unit, and clock ownership separate from the raw marker values.</p></div>
</div>

## Run the checked starter generator

The repository contains a deterministic example that inspects the bundled synthetic kiosk demonstration and creates **review-required templates**. It deliberately leaves scientific declarations blank rather than guessing them from column names.

```bash
python examples/hands-on/create-study-metadata-data-dictionary.py
```

A successful run ends with:

```json
{"status": "PASS", "tutorial": "study-metadata-data-dictionary"}
```

To retain the generated files:

=== "macOS / Linux"

    ```bash
    GPBIOMETRICSPY_DICTIONARY_DIR=outputs/study-dictionary \
      python examples/hands-on/create-study-metadata-data-dictionary.py
    ```

=== "PowerShell"

    ```powershell
    $env:GPBIOMETRICSPY_DICTIONARY_DIR = "outputs/study-dictionary"
    python examples/hands-on/create-study-metadata-data-dictionary.py
    ```

The example writes:

```text
outputs/study-dictionary/
├── study-metadata.json
├── variable-dictionary.csv
├── event-dictionary.csv
└── dictionary-manifest.json
```

The files are starters, not automatic validation results. The generator records observable properties such as dtype, missingness, distinct-value count, and a representative value, but `declared_role`, `declared_unit`, `clock_owner`, `derivation`, and event semantics remain researcher-reviewed fields.

## Minimum study metadata

Keep study-level metadata separate from the variable dictionary. A compact study record should cover at least:

| Field | What to record | Why it matters |
|---|---|---|
| study/project identifier | stable non-secret project label | joins evidence without exposing participant identity |
| source/export family | acquisition software, export type, version if known | constrains parser and schema assumptions |
| devices | device/model for each recorded stream | establishes measurement provenance |
| acquisition settings | configured rate, calibration, filters, vendor processing if known | separates configured settings from observed timing evidence |
| participant/session/run identifiers | exact source fields or explicit external mapping | defines grouping and repeated-measures structure |
| primary time field(s) | exact source fields and declared units | required before event locking or cross-stream alignment |
| clock owner | device/application/system responsible for each time field | prevents accidental same-clock assumptions |
| event source | TTL/task log/vendor marker field and edge/state behavior | establishes event provenance |
| privacy boundary | where direct identifiers/private mappings are stored | keeps public reproducibility material de-identified |
| analysis target | planned outcome/generalisation unit in neutral terms | helps detect later unit-of-analysis drift |

Do not put names, email addresses, consent identifiers, medical-record identifiers, or other direct participant identifiers into a public dictionary or repository. Keep private linkage material outside the analysis repository unless your approved governance process explicitly requires otherwise.

## Variable dictionary schema

A useful variable dictionary distinguishes **observed file properties** from **researcher declarations**.

| Field | Type | Meaning |
|---|---|---|
| `source_column` | observed | exact original field name |
| `dtype` | observed | parsed dtype in the inspected file |
| `missing_fraction` | observed | fraction missing in the inspected slice/file |
| `n_unique` | observed | observed distinct-value count |
| `example_value` | observed | bounded representative value for orientation |
| `declared_role` | declaration | identifier, time, waveform, validity, event, coordinate, derived metric, condition, etc. |
| `declared_unit` | declaration | source unit after verification |
| `clock_owner` | declaration | clock responsible for the value when time-dependent |
| `derivation` | declaration | raw/vendor-derived/recomputed/analysis-derived plus method reference |
| `validity_semantics` | declaration | meaning of validity/status values if applicable |
| `review_status` | governance | `REVIEW`, `ACCEPTED`, or `EXCLUDED` with rationale |
| `notes` | governance | source manual/page, uncertainty, conversion, known caveats |

<div class="gp-decision">
<strong>Observed is not declared.</strong> A dtype, numeric range, low missingness rate, or familiar field name can help you inspect a file; none of them establishes the physical quantity, unit, clock, validity meaning, or scientific interpretation.
</div>

## Event dictionary schema

Treat event semantics as a separate contract rather than embedding assumptions inside analysis code.

| Field | Meaning |
|---|---|
| `source_event_field` | original marker/log field |
| `event_code` | raw code/value/edge |
| `event_label` | researcher-confirmed meaning |
| `edge_or_state` | rising/falling/change/state/log-row semantics |
| `clock_owner` | clock that timestamps the event |
| `grouping_unit` | participant/session/run/trial scope |
| `expected_count_per_unit` | design expectation, if known |
| `tolerance_or_window` | allowed timing/count tolerance where pre-specified |
| `review_status` | review state and exception handling |
| `notes` | source protocol/manual and caveats |

Do not infer event labels from numerical order. `TTL0 == 1` is not automatically “stimulus onset,” and a marker transition is not automatically synchronized with another stream simply because both are stored in one table.

## High-risk fields that deserve explicit review

### `TIME`, counters, and timestamps

Record the exact unit and clock owner. Compare observed intervals, resets, duplicates, gaps, and counter relationships with [Timebase and alignment](timebase-alignment.md). A plausible sampling interval is evidence about the file, not proof of the acquisition clock.

### `HR`, `HRV`, `HRP`, `IBI`

Keep waveform-derived pulse intervals, vendor metrics, sampled heart-rate series, validity fields, and NN/RR/IBI concepts distinct. In common Gazepoint-style exports, a field named `HRV` may be a **heart-rate validity/status field rather than an HRV metric**. Use the [Signal and column glossary](signal-column-glossary.md) before assigning roles.

### `GSR`, `GSRV`

Separate conductance from validity metadata, and verify the source unit before applying range correction or decomposition. A nonzero channel is not necessarily usable.

### gaze/fixation fields

Record coordinate system, origin, display/stimulus geometry, validity semantics, fixation source, and whether the field is sample-level or event-level. Do not mix vendor fixations with sample-derived events without provenance.

### condition and design fields

State whether a field is randomized condition, measured covariate, item/stimulus identifier, trial order, block, session, or a later derived grouping. This distinction affects both design audits and model interpretation.

## Review workflow

1. **Preserve the source export.** Never overwrite it with standardized names.
2. **Generate the starter dictionary.** Record observable properties without assigning scientific meaning automatically.
3. **Consult acquisition documentation.** Confirm source field definitions, units, validity flags, and vendor-derived quantities.
4. **Fill researcher declarations.** Assign role, unit, clock owner, derivation, validity semantics, and review status.
5. **Create the event dictionary.** Confirm code meanings against the experiment protocol/logging implementation.
6. **Run dataset validation.** Use [Validate a new dataset](validate-dataset.md) for timing, activity, missingness, design, and event evidence.
7. **Map the export.** Apply [Bring your own export safely](bring-your-own-export.md) only after the mapping contract is reviewable.
8. **Freeze the dictionary with the analysis.** Retain it beside QC, event, model, and reporting evidence.

## Acceptance conditions before analysis

- [ ] every analysis-critical source column has a reviewed role;
- [ ] every measurement/time field has a verified or explicitly unresolved unit;
- [ ] every time/event field has a declared clock owner or an explicit unknown status;
- [ ] raw/vendor-derived/recomputed/analysis-derived fields are distinguishable;
- [ ] validity/status fields are not mislabeled as physiological metrics;
- [ ] event codes have researcher-confirmed labels and edge/state semantics;
- [ ] participant/session/run/trial/item/AOI identifiers are defined;
- [ ] private linkage fields are outside public artifacts;
- [ ] unresolved fields are marked `REVIEW` rather than silently accepted;
- [ ] the dictionary version/manifest is retained with the analysis evidence.

## Common dictionary failures

| Failure | Why it is unsafe | Better practice |
|---|---|---|
| Rename first, document later | source meaning can be lost | preserve source names and store explicit source→standard mapping |
| Guess units from magnitude | plausible ranges overlap across units/devices | verify from acquisition/export documentation and timing evidence |
| Use one “type” column for everything | identity, time, waveform, validity and derived roles collapse | use explicit role + provenance + unit + clock fields |
| Treat event value as event meaning | codes are implementation details | maintain a separate event dictionary tied to protocol evidence |
| Put participant linkage in the dictionary | reproducibility artifact becomes a privacy risk | keep direct linkage private and use study pseudonyms |
| Mark all fields accepted because parsing succeeded | parser success is not measurement validation | retain `REVIEW` until scientific declarations are checked |
| Edit the dictionary after results without versioning | analysis provenance becomes ambiguous | freeze/version the dictionary and include it in the evidence manifest |

## Handoff to the rest of the workflow

<div class="gp-flow">
<div><strong>01</strong><span>Scaffold</span><small>Create durable research directories and privacy boundaries.</small></div>
<div><strong>02</strong><span>Dictionary</span><small>Declare identities, roles, units, clocks, provenance and event semantics.</small></div>
<div><strong>03</strong><span>Adapt</span><small>Map source columns without hiding their original meaning.</small></div>
<div><strong>04</strong><span>Validate</span><small>Audit observed timing, signal activity, missingness, events and design.</small></div>
<div><strong>05</strong><span>Analyze</span><small>Derive measures only after the measurement contract is reviewable.</small></div>
<div><strong>06</strong><span>Report</span><small>Retain the dictionary and manifest with QC, methods and results evidence.</small></div>
</div>

<div class="gp-science-boundary">
<strong>Evidence boundary.</strong> A complete metadata record and data dictionary document declared meaning and provenance. They do not prove sensor validity, calibration quality, event synchronization, construct validity, causal identification, diagnostic accuracy, or psychological interpretation. Those require separate acquisition, validation, design, and inferential evidence.
</div>

## Next

- [Research project scaffold](research-project-scaffold.md) — establish directories, configuration and privacy boundaries.
- [Bring your own export safely](bring-your-own-export.md) — create a source-preserving column adaptation manifest.
- [Validate a new dataset](validate-dataset.md) — audit timing, signal activity, missingness, events and design.
- [Signal and column glossary](signal-column-glossary.md) — review common Gazepoint-style field roles and traps.
- [Reporting and reproducibility](reporting-reproducibility.md) — retain the dictionary with the full analysis evidence bundle.
