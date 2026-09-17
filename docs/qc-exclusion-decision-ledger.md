# QC and exclusion decision ledger

<div class="gp-page-intro" data-qc-exclusion-ledger>
Quality-control findings and exclusions are different objects. QC describes evidence about recorded data; an exclusion is a reviewed analysis decision with a defined scope and downstream consequence. Keep both so a collaborator, reviewer, or future you can reconstruct why the analysis denominator changed.
</div>

This page complements [Validate a new dataset](guides/validate-dataset.md) and [Reporting and reproducibility](guides/reporting-reproducibility.md). It is especially useful when missing runs, flatlines, timing irregularities, invalid gaze, absent events, or design imbalance could lead to participant-, session-, trial-, event-, channel-, or row-level exclusions.

<div class="gp-decision">
<strong>Candidate flag is not exclusion.</strong> A QC function may identify an issue worth reviewing. Do not automatically delete observations merely because a flag is true, a threshold is crossed, or a status contains `warn`.
</div>

## Run the checked example

The repository contains a deterministic synthetic example that creates two known QC problems, audits them with public `gpbiometricspy` functions, and writes a review-only exclusion ledger. It intentionally applies **zero automatic exclusions**.

```bash
python examples/hands-on/create-qc-exclusion-ledger.py
```

To retain the outputs:

=== "macOS / Linux"

    ```bash
    GPBIOMETRICSPY_EXCLUSION_DIR=outputs/qc-exclusion-ledger \
      python examples/hands-on/create-qc-exclusion-ledger.py
    ```

=== "PowerShell"

    ```powershell
    $env:GPBIOMETRICSPY_EXCLUSION_DIR = "outputs/qc-exclusion-ledger"
    python examples/hands-on/create-qc-exclusion-ledger.py
    ```

A successful run ends with:

```json
{"status": "PASS", "tutorial": "qc-exclusion-decision-ledger"}
```

The output folder contains:

```text
outputs/qc-exclusion-ledger/
├── qc-signal-activity.csv
├── qc-time-reset-overview.csv
├── qc-dropout-summary.csv
├── exclusion-decision-ledger.csv
├── denominator-audit.csv
└── exclusion-manifest.json
```

## Separate four layers

<div class="gp-guide-grid" data-exclusion-evidence-grid>
<div class="gp-guide-card"><span class="gp-eyebrow">1 · Observation</span><h3>What did QC detect?</h3><p>Save the raw QC object or table: missing runs, flatlines, timing resets, event gaps, invalid samples, sparse cells, or other observable conditions.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">2 · Rule</span><h3>What criterion was pre-specified?</h3><p>Record the threshold, protocol rule, or analysis-plan criterion separately from the observed value.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">3 · Decision</span><h3>What was retained, excluded, or escalated?</h3><p>Use an explicit state such as `RETAIN`, `EXCLUDE`, or `REVIEW`, plus the reason and scope.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">4 · Consequence</span><h3>What denominator changed?</h3><p>Record rows, participants, sessions, trials, events, items, AOIs, or channels before and after applied decisions.</p></div>
</div>

## The unit of exclusion matters

Do not treat every QC finding as a participant exclusion. Choose the narrowest scientifically defensible scope.

| Candidate issue | Possible scope | Questions before deciding |
|---|---|---|
| brief missing sensor run | rows/window/channel | Is the affected interval needed for the target feature? Can the method tolerate or explicitly model missingness? |
| one inactive channel | channel × participant/session | Are other modalities still valid? Is that channel required for the stated analysis? |
| timing reset | segment/session/run | Can segments be identified without inventing cross-reset timing? Does event locking cross the reset? |
| missing event marker | event/trial | Is the event reconstructable from an independent, validated log? |
| failed calibration/invalid gaze | trial/session/participant | What did the acquisition protocol specify and which gaze analyses depend on it? |
| sparse condition cell | participant/item/cell or model scope | Is the issue measurement, design coverage, or model identifiability? |
| corrupted source file | file/session | Is a clean source copy available and auditable? |

A participant-wide exclusion should not be the default response to a local channel or event problem.

## Minimum ledger schema

Keep one row per decision candidate or applied decision.

| Field | Meaning |
|---|---|
| `decision_id` | stable unique identifier |
| `analysis_stage` | ingest, QC, event alignment, feature construction, modelling, etc. |
| `unit_type` | row/window/channel/event/trial/session/participant/item/AOI/file |
| `unit_id` | pseudonymous identifier or bounded locator |
| `signal` | affected signal when relevant |
| `issue` | concise observable QC finding |
| `evidence_artifact` | file/table/figure containing the evidence |
| `evidence_value` | observed value/status supporting review |
| `criterion` | pre-specified or documented rule, if one exists |
| `decision` | `REVIEW`, `RETAIN`, or `EXCLUDE` |
| `reason` | decision rationale; blank while under review |
| `downstream_effect` | what analysis/table/window is affected |
| `reviewer` | reviewer/role if governance requires it |
| `notes` | uncertainty, exceptions, or linked protocol reference |

<div class="gp-science-boundary">
<strong>Evidence boundary.</strong> A QC status can justify review. It does not, by itself, establish that data are unusable, that a participant should be removed, or that an exclusion is unbiased. Exclusion rules should follow the acquisition protocol, analysis plan, measurement requirements, and design rather than be selected to improve a result.
</div>

## Denominator audit

Every applied exclusion should have a denominator consequence that can be inspected. At minimum retain counts before and after decisions for the relevant unit.

| Scope | Useful denominator evidence |
|---|---|
| sample/row | rows before, rows removed, rows retained, retained fraction |
| event/trial | expected events/trials, observed, excluded, retained |
| participant/session | eligible, QC-reviewed, excluded, retained |
| signal/channel | requested channels, usable channels, unavailable/excluded channels |
| model | candidate observations/groups, complete/model-eligible observations/groups, final fitted set |

If different analyses use different denominators, report them separately. Do not let a single final `N` conceal analysis-specific exclusions.

## Use package QC as evidence, not as deletion logic

```python
import gpbiometricspy as gp

activity = gp.audit_gazepoint_signal_activity(
    dat,
    signal_cols=["GSR_US", "HR"],
    group_cols=["participant_id"],
)

time_qc = gp.audit_gazepoint_time_resets(
    dat,
    time_col="TIME",
    group_cols=["participant_id"],
)

dropout = gp.flag_gazepoint_biometric_dropouts(
    dat,
    signal_cols=["GSR_US", "HR"],
    group_cols=["participant_id"],
    time_col="TIME",
)
```

Retain `activity["signal_by_group"]`, `time_qc["overview"]`, the relevant time-reset tables, and `dropout.attrs["dropout_summary"]`. Review them against the analysis requirements before changing the analysis set.

## Decision states

### `REVIEW`

Use when QC evidence exists but the scientific action has not been resolved. This is the safe default for automatically generated candidate rows.

### `RETAIN`

Use when the issue was reviewed and the data remain admissible for a specified analysis. Document why the issue does not invalidate the target quantity.

### `EXCLUDE`

Use only when a reviewed rule or measurement/design requirement supports removal. State the exact scope and downstream effect.

Do not encode ambiguous states such as `bad`, `drop`, or `cleaned` without a reason and scope.

## Review sequence

1. **Run QC without deleting data.** Save signal, timing, validity, event, and design evidence.
2. **Create candidate ledger rows.** Point each row to the evidence artifact and observed status/value.
3. **Attach the decision criterion.** Distinguish pre-specified rules from post-hoc judgments.
4. **Choose the narrowest scope.** Prefer channel/event/trial/segment decisions when participant-wide removal is not justified.
5. **Record `RETAIN`, `EXCLUDE`, or unresolved `REVIEW`.** Never infer the action solely from a warning label.
6. **Apply exclusions in a separate reproducible step.** Keep the unfiltered analysis input intact.
7. **Recompute denominators.** Save before/after counts at each affected unit.
8. **Run sensitivity checks when judgment matters.** Compare reasonable inclusion/exclusion alternatives without selecting the one that produces a preferred result.
9. **Report the flow.** Methods/results should state eligible, reviewed, excluded, retained, and analysis-specific denominators.

## Common failures

| Failure | Why it weakens the evidence | Better practice |
|---|---|---|
| `dropna()` before QC | missingness disappears from the evidence trail | audit first, then apply documented analysis-specific handling |
| participant exclusion for one bad channel | discards unaffected data and changes all downstream analyses | use channel-/analysis-specific scope unless protocol supports participant removal |
| thresholds chosen after viewing effects | exclusion becomes outcome-sensitive | pre-specify where possible; label exploratory changes and run sensitivity analyses |
| overwrite the source table | excluded rows become unrecoverable | retain immutable input and create a filtered derivative |
| only report final `N` | review cannot reconstruct attrition | save denominator audit and exclusion ledger |
| warning automatically means exclude | software status substitutes for scientific judgment | route warnings to `REVIEW` by default |
| free-text reasons only | inconsistent decisions are hard to audit | use controlled decision states plus structured issue/criterion/scope fields |

## Reporting template

A compact methods/reporting statement should answer four questions: what was checked, which criteria governed decisions, what was excluded at which unit, and how the denominator changed. Keep the machine-readable ledger as supplementary evidence rather than forcing every detail into prose.

> Signal activity, timing, and dropout evidence were audited before feature construction. QC flags generated review candidates rather than automatic removals. Exclusions were applied at the narrowest pre-specified analysis unit, and analysis-specific before/after denominators were retained in a decision ledger.

Adapt that wording to the study; do not claim exclusions were pre-specified if they were not.

## Handoff

<div class="gp-flow">
<div><strong>01</strong><span>Validate</span><small>Generate inspectable QC, timing, event, and design evidence.</small></div>
<div><strong>02</strong><span>Review</span><small>Create candidate decisions without deleting source data.</small></div>
<div><strong>03</strong><span>Decide</span><small>Assign a scoped retain/exclude/review state with rationale.</small></div>
<div><strong>04</strong><span>Apply</span><small>Materialize a filtered derivative in a separate reproducible step.</small></div>
<div><strong>05</strong><span>Count</span><small>Audit denominator changes for every affected analysis unit.</small></div>
<div><strong>06</strong><span>Report</span><small>Retain the ledger, QC evidence, denominator flow, and sensitivity results.</small></div>
</div>

## Next

- [Validate a new dataset](guides/validate-dataset.md) — produce the QC evidence feeding the ledger.
- [Troubleshooting and diagnostics](guides/troubleshooting.md) — diagnose unexpected QC findings before deciding.
- [Reporting and reproducibility](guides/reporting-reproducibility.md) — carry exclusions and denominator evidence into the research bundle.
- [Choose a modelling strategy](guides/model-selection.md) — verify that the retained grouping structure still supports the intended analysis.
