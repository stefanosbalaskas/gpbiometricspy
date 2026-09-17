---
description: Turn exploratory notebook work into a restartable gpbiometricspy research workflow with explicit inputs, parameters, outputs, software identity, and reviewable evidence.
search:
  boost: 1.25
---

# Reproducible notebook workflow

<div class="gp-page-intro" data-notebook-workflow>
Notebooks are useful for exploration and communication, but research results should not depend on the order in which a kernel happened to execute cells. This guide uses one rule throughout: **a clean restart and top-to-bottom execution must be able to reconstruct the analysis from declared inputs and parameters**.
</div>

<div class="gp-chip-row">
<span class="gp-chip">Restartable</span>
<span class="gp-chip">Explicit parameters</span>
<span class="gp-chip">No hidden state</span>
<span class="gp-chip">Reviewable outputs</span>
<span class="gp-chip">Software identity</span>
</div>

## The pattern

<div class="gp-steps" data-notebook-stages>
<div class="gp-step"><strong>1 · Environment</strong><span>Record the Python and gpbiometricspy version used for the run.</span></div>
<div class="gp-step"><strong>2 · Parameters</strong><span>Declare participant selection, columns, windows, thresholds and grouping in one visible block.</span></div>
<div class="gp-step"><strong>3 · Input</strong><span>Load or construct data explicitly; do not rely on a dataframe left over from an earlier cell.</span></div>
<div class="gp-step"><strong>4 · Functions</strong><span>Move stable transformations into functions with explicit arguments and return values.</span></div>
<div class="gp-step"><strong>5 · Evidence</strong><span>Write QC, settings, denominators and intermediate summaries before only the final figure/table.</span></div>
<div class="gp-step"><strong>6 · Manifest</strong><span>Bind parameters, software identity and generated artifacts into a small machine-readable record.</span></div>
<div class="gp-step"><strong>7 · Restart</strong><span>Restart the kernel and run from the first cell; the outputs should reconstruct without manual repair.</span></div>
</div>

## Run the checked companion example

The repository includes the checked script `examples/hands-on/reproducible-notebook-pattern.py`. It is an ordinary Python file, so CI can execute it directly, but its `# %%` sections also map cleanly to notebook-style cells in editors that support cell markers.

```bash
python examples/hands-on/reproducible-notebook-pattern.py
```

To retain the evidence artifacts used by the browser regression test:

```bash
GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR=notebook-evidence \
python examples/hands-on/reproducible-notebook-pattern.py
```

On Windows PowerShell:

```powershell
$env:GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR = "notebook-evidence"
python examples/hands-on/reproducible-notebook-pattern.py
```

The checked synthetic example writes:

- `analysis_parameters.json`;
- `software.json`;
- `signal_activity_overview.csv`;
- `signal_activity_by_group.csv`;
- `time_reset_overview.csv`;
- `time_reset_segments.csv`;
- `notebook_manifest.json`.

The point is not the particular QC functions. The important part is that the result is reconstructed from a declared parameter block through explicit function calls and return values.

## Keep one visible parameter block

Avoid scattering scientific choices across unrelated cells. A small configuration object makes the analysis easier to inspect, rerun and compare.

```python
PARAMETERS = {
    "participant": "synthetic_kiosk_p001",
    "rows": 900,
    "signal_cols": ["GSR_US", "HR", "IBI", "LPMM"],
    "group_cols": ["participant_id"],
    "time_col": "TIME",
}
```

For research data, extend the same idea to choices such as baseline windows, interpolation rules, event codes, AOI definitions, exclusion criteria, preprocessing parameters, model formulas and validation splits. If a choice affects the scientific result, it should not be discoverable only by reading an old cell output.

## Separate exploration from stable analysis

Early notebook work often contains temporary expressions such as:

```python
subset = data[data["participant_id"] == "p001"]
subset["GSR_US"].describe()
```

That is useful during exploration. Once the operation becomes part of the study workflow, move it into a named function or checked package call whose inputs and outputs are explicit.

```python
def run_analysis(data, *, signal_cols, group_cols):
    activity = gp.audit_gazepoint_signal_activity(
        data,
        signal_cols=signal_cols,
        group_cols=group_cols,
    )
    return {"activity": activity}
```

The notebook then becomes an orchestration/reporting surface rather than the only place where the scientific logic exists.

## Avoid hidden state

| Hidden-state pattern | Why it is risky | Safer pattern |
|---|---|---|
| Redefining a variable several cells later | The visible notebook order no longer guarantees the value used | One parameter block or a function argument |
| Mutating a dataframe in place across cells | Results depend on which cells ran and how many times | Return a new object from a named transformation |
| Loading data from a machine-specific implicit working directory | Another machine cannot reconstruct the input | Use an explicit project-relative/source path |
| Manually editing a dataframe after import | The change may never appear in the recorded code | Encode the mapping/correction and retain its evidence |
| Copying a final table into another cell | Provenance from source to result is broken | Recreate the table from returned analysis objects |
| Keeping a threshold only in a plot title or note | The computation cannot be audited from settings | Store the threshold with parameters/manifest |
| Depending on an already-imported local package checkout | Software identity becomes ambiguous | Record `gp.__version__` and the environment/commit used |

## Restart and run all is a minimum test, not full validation

A successful clean execution answers a software-reproducibility question: **can this document reconstruct its outputs from its declared state?** It does not establish that the scientific inputs or choices are valid.

After a clean run, still verify:

- source provenance and the data dictionary;
- units and signal identity;
- sampling and clock semantics;
- event/AOI definitions;
- QC and missingness;
- reviewed exclusions and denominators;
- analysis unit and grouping;
- model assumptions and validation target;
- interpretation boundaries.

Use [Validate a new dataset](guides/validate-dataset.md), [Study metadata and data dictionary](guides/study-metadata-data-dictionary.md), and the [QC & exclusion decision ledger](qc-exclusion-decision-ledger.md) for those layers.

## Keep private data out of notebook output cells

Notebook files can retain outputs even after the source cell has changed. For private participant data:

1. avoid displaying direct identifiers or unnecessary raw rows;
2. do not commit private data or participant-level exports to the repository;
3. prefer aggregate/synthetic outputs in documentation;
4. clear sensitive cell output before sharing a notebook;
5. keep private ID mappings outside the analysis artifact;
6. retain reproducibility through settings, manifests and protected source references rather than copied private values.

The [Research project scaffold](guides/research-project-scaffold.md) provides a directory pattern for keeping raw/private inputs distinct from shareable derived evidence.

## Make outputs boring and predictable

A reproducible research notebook should produce files whose names and roles are stable enough that collaborators and future-you do not have to inspect the kernel history to understand them.

Prefer:

```text
analysis_parameters.json
software.json
qc_overview.csv
event_summary.csv
model_diagnostics.csv
figure_01.png
analysis_manifest.json
```

Avoid relying on unnamed objects such as “the dataframe in cell 23” or “the figure currently visible above.”

## Before moving from exploration to modelling

Use this checkpoint:

- [ ] The notebook runs from a clean kernel in top-to-bottom order.
- [ ] Every external input has an explicit source/path or deterministic generator.
- [ ] Scientific choices are collected in visible parameters/configuration.
- [ ] Stable transformations use functions or exported package calls.
- [ ] QC and timing evidence exist before feature/model outputs.
- [ ] Exclusion decisions and denominators are retained separately from QC flags.
- [ ] Package/Python identity is recorded.
- [ ] Important outputs are written to deterministic paths.
- [ ] A manifest identifies the run’s parameters and artifacts.
- [ ] Private identifiers/data are not embedded in a shareable notebook.
- [ ] Restart-and-run-all reproduces the artifacts.
- [ ] Scientific interpretation is no stronger than the measurement/design evidence.

## Notebook, script, or package function?

Use a **notebook** when interactive inspection, narrative explanation, or visual exploration is central. Use a **script** when the whole workflow should run unattended and produce a fixed artifact set. Move logic into a **function/module** when it is reused, tested independently, or becomes part of the stable research pipeline.

You do not need to choose only one. A useful pattern is:

```text
notebook/report
    ↓ calls
small analysis functions / gpbiometricspy API
    ↓ write
versioned tables, figures, diagnostics, manifest
```

This keeps the narrative surface flexible while the analysis contract remains testable.

## Where to go next

- Unsure which documentation type you need → [Learning paths](learning-paths.md)
- Repeated research-workflow questions → [Research FAQ & decision clinic](research-faq.md)
- Bringing an unfamiliar export → [Bring your own export safely](guides/bring-your-own-export.md)
- Need a full runnable analysis → [Hands-on EDA research](guides/hands-on-eda-research.md)
- Preparing a manuscript/review bundle → [Reporting and reproducibility](guides/reporting-reproducibility.md)

<div class="gp-science-boundary">
<strong>Boundary.</strong> Reproducible execution makes the computational path inspectable. It does not validate undocumented units, sensors, clocks or event meanings; it does not justify automatic exclusions; and it does not convert associations or physiological/eye-tracking measures into causal or latent-state evidence.
</div>
