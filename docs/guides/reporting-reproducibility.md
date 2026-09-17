# Reporting and reproducibility

<div class="gp-page-intro">
A reproducible analysis is more than code that runs once. This guide focuses on the evidence that should survive the analysis: input identity, QC, timing, preprocessing, modelling assumptions, software versions, generated figures, and scientific boundaries.
</div>

## The minimum reporting bundle

<div class="gp-metric-grid">
<div class="gp-metric-card"><strong>Input</strong><span>Source files, schema, units, participants/sessions, acquisition context.</span></div>
<div class="gp-metric-card"><strong>QC</strong><span>Missingness, validity, dropouts, timing, exclusions, review decisions.</span></div>
<div class="gp-metric-card"><strong>Methods</strong><span>Parameters, thresholds, windows, model formulae, prediction semantics.</span></div>
<div class="gp-metric-card"><strong>Software</strong><span>Package version, Python version, optional backend versions, certificates.</span></div>
</div>

## Run a reviewable evidence bundle

<div class="gp-page-intro" data-research-evidence-bundle>
The repository includes a checked, deterministic companion script that turns one bounded synthetic demonstration into a folder of **design, quality, event/alignment, derived-summary, visual, software, and reporting evidence**. Use it to learn what should survive a research analysis before replacing the synthetic input with private study exports.
</div>

From the repository root:

```bash
python examples/hands-on/research-evidence-bundle.py
```

A successful run ends with JSON containing:

```json
{"status": "PASS", "tutorial": "research-evidence-bundle"}
```

To retain the artifacts, choose an output directory.

=== "macOS / Linux"

    ```bash
    GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR=outputs/research-evidence \
      python examples/hands-on/research-evidence-bundle.py
    ```

=== "PowerShell"

    ```powershell
    $env:GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR = "outputs/research-evidence"
    python examples/hands-on/research-evidence-bundle.py
    ```

<div class="gp-guide-grid" data-evidence-bundle-stages>
<div class="gp-guide-card"><span class="gp-eyebrow">Input</span><h3>Recorded sample data</h3><p>Keep the bounded analysis input distinct from the study-design table and retain source/provenance information when adapting the example.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Design</span><h3>Condition and task structure</h3><p>Export the participant-by-task design rather than reconstructing conditions from filenames, row order, or downstream summaries.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Quality</span><h3>Signal activity and time resets</h3><p>Retain machine-readable QC tables before event locking or feature construction so exclusions and timing assumptions remain inspectable.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Events</span><h3>TTL identity and alignment</h3><p>Save the extracted TTL table, alignment overview, alignment event table, and event-relative sample rows instead of reporting only a window definition.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Derived</span><h3>Event-locked summaries</h3><p>Keep summary rows together with their event definitions, baseline/summary windows, recorded signal names, and grouping structure.</p></div>
<div class="gp-guide-card"><span class="gp-eyebrow">Report</span><h3>Figure, software and methods evidence</h3><p>Export the shared timeline, software identity, reporting checklist, methods starting text, and an evidence manifest alongside derived tables.</p></div>
</div>

The saved directory is designed to be inspected rather than merely archived. It includes the structured audit components rather than collapsing them into ambiguous files:

```text
outputs/research-evidence/
├── study_design.csv
├── signal_activity_overview.csv
├── signal_activity_by_group.csv
├── time_reset_overview.csv
├── time_reset_segments.csv
├── time_reset_flags.csv
├── ttl_events.csv
├── alignment_overview.csv
├── alignment_events.csv
├── aligned_data.csv
├── eventlocked_summary.csv
├── eventlocked_samples.csv
├── analysis_checklist_overview.csv
├── software.json
├── methods_text.txt
├── evidence_manifest.json
└── research-evidence-bundle-01.png
```

### How to review the bundle

| Artifact family | Question it should let you answer | Do not substitute |
|---|---|---|
| Design | Which participant/task/condition rows define the analysis context? | Filename or row-order inference |
| Signal activity | Which requested channels were active within each analysis group? | A single undocumented “quality passed” flag |
| Time-reset audit | Were resets, duplicate times, non-finite values, or segment boundaries visible? | A statement that timestamps were “checked” |
| TTL/event evidence | What marker changes were detected and where? | An undocumented event index |
| Alignment | Which rows entered each event-relative window and under which settings? | A claim of synchronization based only on successful code execution |
| Event-locked summaries | How were recorded channels summarized around explicit events? | A table detached from windows, events, and grouping |
| Software/reporting | Which software identity and reporting objects reproduce the run? | Package name without version or settings |

The example intentionally uses the bundled synthetic kiosk data. Before substituting a research export, first use [Validate a new dataset](validate-dataset.md), inspect the [synthetic demo guide](../demo.md), and resolve clock assumptions with [Timebase and alignment](timebase-alignment.md). The evidence bundle is a **retention pattern**, not a shortcut around modality-specific QC.

<div class="gp-science-boundary">
<strong>Evidence boundary.</strong> A complete evidence folder can show what was recorded, transformed, aligned, summarized, plotted, and reported. It does not by itself establish emotion, stress, attention, trust, preference, diagnosis, causal effects, sensor validity, or hardware-level synchronization. Those claims require appropriate measurement, acquisition, design, validation, and inference beyond file completeness.
</div>

## Capture software identity early

```python
import platform
import gpbiometricspy as gp

software = {
    "gpbiometricspy": gp.__version__,
    "python": platform.python_version(),
}
```

If an optional backend contributes to the scientific result, record its version too. The public interoperability matrix tests supported floor/current combinations, but a manuscript should still state what the study actually used.

## Retain QC as data

Do not reduce QC to “data were cleaned.” Keep the tables or objects that support each decision.

```python
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
```

Both calls return structured audit objects. Retain their named tables—for example `activity["overview"]`, `activity["signal_by_group"]`, `resets["overview"]`, `resets["segment_summary"]`, and `resets["row_flags"]`—rather than treating the outer object as one flat table.

![Missingness overview](../assets/generated/missingness.png)

The exact QC functions depend on modality, but the reporting principle is stable: retain the evidence that justified inclusion, exclusion, interpolation, or model readiness.

## Report transformations in scientific order

A methods section is easier to audit when it follows the order in which information was transformed:

1. acquisition/export and source identity;
2. schema standardisation;
3. timebase and signal QC;
4. preprocessing and artifact rules;
5. event/AOI alignment;
6. feature construction;
7. statistical or predictive modelling;
8. sensitivity checks;
9. software and reproducibility information.

This order prevents downstream model details from obscuring earlier measurement assumptions.

## What to report for modelling

For grouped or hierarchical models, state:

- outcome and predictor definitions;
- grouping factors and whether levels are crossed or nested;
- fixed effects;
- random-effect structure;
- distributional family;
- estimation/integration strategy where relevant;
- how unseen groups/items are handled;
- validation split unit;
- optimization/convergence diagnostics;
- uncertainty or the explicit absence of inferential intervals;
- sensitivity or known-truth validation used to bound claims.

For the Python-native method families, use the dedicated [Methods](../methods/index.md) pages rather than inferring semantics from class or function names.

## Figures are evidence, not decoration

Keep the figures used for decisions, including failed or borderline checks when they affected the analysis. The documentation gallery is generated from package functions and provides examples of the kinds of diagnostics worth retaining.

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr">
<img src="../assets/generated/eda-decomposition.png" alt="EDA decomposition showing observed tonic and phasic components">
<div class="gp-visual-card-body"><strong>Signal processing evidence</strong><span>Show what a transformation did rather than only reporting its name.</span></div>
</a>
<a class="gp-visual-card" href="../plot-gallery/#ppg-and-hrv">
<img src="../assets/generated/ppg-peak-detection.png" alt="PPG waveform with accepted pulse peaks">
<div class="gp-visual-card-body"><strong>Event-detection evidence</strong><span>Retain accepted/rejected event logic when derived intervals feed later analyses.</span></div>
</a>
</div>

## Reproducibility checklist

- [ ] Raw inputs are immutable or checksummed.
- [ ] Schema/renaming decisions are recorded.
- [ ] Sampling and timebase evidence is retained.
- [ ] QC outputs and warnings are saved.
- [ ] Exclusions have machine-readable reasons.
- [ ] Preprocessing settings are explicit.
- [ ] Random seeds are fixed where stochastic procedures are used.
- [ ] Optional backend versions are recorded.
- [ ] Figures used for QC are generated from code.
- [ ] Model specification and prediction target are explicit.
- [ ] Scientific interpretation is narrower than or equal to what the design supports.

## Where to go next

- [Reporting and reproducibility workflow](../articles/reporting-reproducibility-workflow.md) — frozen R-companion workflow.
- [Private real-data smoke testing](../articles/private-real-data-smoke-testing.md) — validate private data without committing it.
- [Citation and archival](../citation.md) — package citation and software archive information.
- [Validation & trust](../parity.md) — parity and certification evidence.
