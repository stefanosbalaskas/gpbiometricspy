---
description: A practical step-by-step guide to using gpbiometricspy for a complete EDA/SCR analysis, including installation, data inspection, QC, processing, plots, exports, and adaptation to research data.
search:
  boost: 1.6
---

# Hands-on guide: use gpbiometricspy from data to report

<div class="gp-page-intro">
This is the **do-the-analysis-with-me** guide. You will run a complete `gpbiometricspy` workflow, inspect what each object means, save the outputs, and learn exactly what must change when you replace the bundled demonstration with your own Gazepoint export.
</div>

The worked path focuses on EDA/SCR because it illustrates the package's general pattern clearly: **load → audit → process → inspect → export → report**. The same discipline carries over to PPG/HRV, pupil/gaze/AOI and multimodal workflows.

## Before you start

You need Python 3.11–3.14 and a clean environment. For the stable release:

```bash
python -m pip install "gpbiometricspy==0.1.6"
```

When working from a repository checkout:

```bash
python -m pip install -e ".[dev,docs]"
```

Confirm the import before doing anything else:

```python
import gpbiometricspy as gp

print(gp.__version__)
```

If this fails, solve the environment/install problem first. Do not mix environment debugging with scientific data debugging.

## 1. Learn on the bundled demonstration

```python
import gpbiometricspy as gp

raw = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)

print(raw.shape)
print(raw.columns.tolist())
print(raw[["participant_id", "TIME", "GSR_US", "HR", "IBI", "LPMM"]].head())
```

Why begin here? The demonstration is deterministic and contains representative Gazepoint-style channels. You can therefore separate **learning the package** from **mapping an unfamiliar study export**.

!!! note "Synthetic demonstration"
    These rows are teaching/test data. They are not empirical evidence about human participants and should never be reported as such.

## 2. Identify the unit of analysis and timebase

For this demonstration:

```python
group_cols = ["participant_id"]
time_col = "TIME"
eda_col = "GSR_US"
```

Write those choices down before processing. In a real study, you may also have session, trial, item, condition, stimulus, AOI or event identifiers. The package cannot decide which of those defines your inferential unit.

### Questions to answer

- Is `TIME` monotonic within each recording unit?
- What are its units?
- Does it reset between participants, files, blocks or trials?
- Is `GSR_US` raw conductance, a vendor-derived value, or a transformed channel?
- Are repeated rows samples, events, trials, or something else?

These are measurement questions, not Python questions.

## 3. Audit before processing

### 3.1 Conductance units

```python
units = gp.audit_gazepoint_gsr_units(raw, gsr_col=eda_col)
```

Inspect the returned evidence instead of assuming the column name is sufficient proof of units.

### 3.2 Signal activity

```python
activity = gp.audit_gazepoint_signal_activity(
    raw,
    signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
    group_cols=group_cols,
)
```

This tells you which recorded channels contain usable activity. A column existing in a CSV does not mean it contains informative measurements.

### 3.3 Time resets

```python
time_resets = gp.audit_gazepoint_time_resets(
    raw,
    time_col=time_col,
    group_cols=group_cols,
)
```

A reset may be legitimate—such as a new recording—or evidence that rows should not be treated as one continuous signal. Decide that before event-window analysis.

### 3.4 EDA quality and artifacts

```python
quality = gp.audit_gazepoint_gsr_quality(
    raw,
    value_column=eda_col,
)

artifacts = gp.audit_gazepoint_eda_artifacts(
    raw,
    signal_col=eda_col,
    time_col=time_col,
    group_cols=group_cols,
)
```

At this point, stop and review the outputs. Your scientific workflow should contain an explicit rule for what happens when quality is insufficient.

!!! warning "Do not process by reflex"
    If units, timing, missingness, flatline behavior, signal activity or artifacts are not understood, do not continue simply because the next function can execute.

## 4. Inspect the raw channel visually

```python
raw_plot = gp.plot_gazepoint_biometric_signals(
    raw,
    signal_cols=[eda_col],
    time_col=time_col,
    standardize=False,
    main="Raw EDA/GSR signal",
)
```

Plotting here is a QC step. Look for discontinuities, impossible ranges, long constant sections, abrupt jumps and gaps that deserve explanation.

## 5. Decompose the EDA signal

```python
decomposition = gp.decompose_gazepoint_eda(
    raw,
    signal_col=eda_col,
    time_col=time_col,
    group_cols=group_cols,
    window_size=31,
    output_prefix="eda",
)
```

Inspect the new columns:

```python
print(
    decomposition[
        ["participant_id", "TIME", "GSR_US", "eda_tonic", "eda_phasic"]
    ].head()
)
```

The decomposition object remains a `pandas.DataFrame`. Metadata about the operation are attached to the frame:

```python
print(decomposition.attrs["overview"])
print(decomposition.attrs["settings"])
```

This matters because `gpbiometricspy` is designed to keep intermediate scientific decisions visible rather than returning only a final score.

### What the decomposition means

- `GSR_US`: observed conductance channel used as input.
- `eda_tonic`: slower component produced by the declared decomposition.
- `eda_phasic`: residual faster component used by the descriptive event detector.
- `eda_decomposition_method`: method provenance stored row-wise.

The default deterministic workflow is useful for transparent descriptive processing. It is not a claim that one decomposition is universally optimal for confirmatory psychophysiology.

## 6. Detect candidate SCR-like events

```python
scr = gp.detect_gazepoint_scr_events(
    decomposition,
    phasic_col="eda_phasic",
    signal_col=eda_col,
    time_col=time_col,
    group_cols=group_cols,
    threshold=None,
    min_peak_distance=10,
)
```

Inspect all parts of the result:

```python
print(scr["overview"])
print(scr["events"].head())
print(scr["group_summary"])
print(scr["settings"])
```

The object separates **event rows**, **group-level summaries**, and **settings**. That is preferable to silently collapsing everything into a single count.

When `threshold=None`, the detector chooses a local descriptive threshold from the phasic signal. If your scientific claim depends on event counts or latency, define and justify the detector settings prospectively and assess sensitivity where appropriate.

## 7. Inspect the decomposition and event placement

```python
decomposition_plot = gp.plot_gazepoint_eda_decomposition(
    decomposition,
    time_col=time_col,
    signal_cols=["GSR_US", "eda_tonic", "eda_phasic"],
    group_cols=group_cols,
    title="Observed, tonic and phasic EDA",
)

scr_plot = gp.plot_gazepoint_scr_events(
    decomposition,
    scr["events"],
    time_col=time_col,
    signal_col=eda_col,
    phasic_col="eda_phasic",
    group_cols=group_cols,
    title="Candidate SCR events",
)
```

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/eda-decomposition.png" alt="Observed tonic and phasic EDA decomposition"><div class="gp-visual-card-body"><strong>Check the transformation</strong><span>Do the tonic and phasic components look plausible relative to the observed waveform?</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/scr-events.png" alt="EDA waveform with candidate SCR event markers"><div class="gp-visual-card-body"><strong>Check the detector</strong><span>Do candidate event markers correspond to the intended waveform features?</span></div></a>
</div>

Do not skip this because the code returned without an exception. Numerical execution is not scientific validation.

## 8. Create a reporting checklist and methods starting point

```python
checklist = gp.create_gazepoint_biometrics_checklist(raw)
methods_text = gp.create_gazepoint_biometrics_methods_text(
    checklist=checklist,
)

print(checklist["overview"])
print(checklist["channels"])
print(checklist["missingness"].head())
print(methods_text)
```

The generated methods text is deliberately conservative. Extend it with the study-specific information that software cannot infer automatically: acquisition setup, participant/sample design, sampling evidence, event definitions, exclusion rules, preprocessing settings, statistical model and sensitivity analyses.

## 9. Run the repository example and save an analysis bundle

The complete executable version is:

`examples/tutorials/end-to-end-eda-research.py`

Run it from the repository root.

=== "macOS / Linux"

    ```bash
    GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR=outputs/eda-research \
      python examples/tutorials/end-to-end-eda-research.py
    ```

=== "PowerShell"

    ```powershell
    $env:GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR = "outputs/eda-research"
    python examples/tutorials/end-to-end-eda-research.py
    ```

The folder will contain the decomposition table, event table, group summary, checklist overview, methods text and diagnostic figures. The program also prints a JSON record with `"status": "PASS"` when it reaches the end successfully.

## 10. Move from demonstration data to your own file

Do **not** replace every line at once. Change one layer at a time.

### Step A — load the export

Use the appropriate package importer or `pandas` reader, then preserve the untouched source file separately.

```python
# Example only: choose the importer that matches your actual export.
data = gp.import_gazepoint_biometrics("data/participant_001.csv")
```

### Step B — map your columns

```python
group_cols = ["participant_id"]
time_col = "TIME"
eda_col = "GSR_US"
```

If your actual names differ, change the variables. Do not change the scientific meaning.

### Step C — rerun only the audits

Run unit, activity, timing, quality and artifact checks. Compare the output with what you observed in the demonstration. This is where most dataset-specific problems should be discovered.

### Step D — declare exclusions before condition comparisons

Decide what constitutes unusable recording, invalid timebase, excessive missingness or artifact burden. Save the decision and reason for each excluded unit.

### Step E — process with explicit settings

Only after the audits are acceptable should you decompose, detect events, align experimental markers or compute summaries.

### Step F — add your experimental design

A study usually needs trial, item, condition or stimulus structure that the signal alone does not provide. Join those identifiers using validated event/timing information rather than row position guesses.

### Step G — model the correct unit

Do not treat thousands of time samples as thousands of independent participants. Choose aggregation, repeated-measures modelling or grouped/crossed models according to the design and target of inference.

## 11. A sensible project layout

```text
my-study/
├── data_raw/                 # untouched exports; read-only in practice
├── data_derived/             # cleaned/decomposed/event tables
├── figures/                  # QC and analysis plots
├── reports/                  # methods text, QC summaries, provenance
├── scripts/
│   ├── 01_import_audit.py
│   ├── 02_process_eda.py
│   └── 03_analysis.py
└── environment/              # requirements/lock/environment record
```

Keep raw data separate from generated outputs. A rerun should be able to recreate `data_derived/`, `figures/` and `reports/` from the raw inputs and scripts.

## 12. What to report in a paper or supplement

At minimum record:

- `gpbiometricspy` version and Python version;
- source/export identity and participant/session scope;
- EDA channel and units;
- observed timing evidence and any corrections;
- missingness/artifact/exclusion rules;
- decomposition method and settings;
- SCR detector threshold rule and minimum peak distance;
- event/stimulus alignment method if used;
- figures/QC evidence inspected;
- statistical unit and model;
- sensitivity or cross-toolbox checks where conclusions depend on processing choices.

## Common mistakes

| Mistake | Better practice |
|---|---|
| Starting with event counts | Audit units, timing and signal quality first. |
| Treating a successful function call as validation | Inspect returned QC evidence and plots. |
| Mixing raw and derived columns without labels | Keep explicit names such as `eda_tonic` and `eda_phasic`. |
| Selecting thresholds after seeing the desired condition difference | Define the rule prospectively or report sensitivity analyses. |
| Interpreting EDA as a direct emotion label | Describe the measured waveform and derived features conservatively. |
| Overwriting raw exports | Keep raw input immutable and write derived artifacts elsewhere. |
| Copying methods text without study-specific details | Use generated text as a starting point, then report acquisition/design/settings fully. |

<div class="gp-science-boundary">
`gpbiometricspy` helps process, audit, visualise and document physiological/eye-tracking measurements. The software output does not on its own identify latent psychological states or establish causal effects. Interpretation must follow the measurement validity, experimental design and inferential model of the study.
</div>

## Next routes

- [End-to-end EDA workflow](../workflows/end-to-end-eda-research.md) — compact research pipeline and completion gates.
- [Runnable example](../examples/end-to-end-eda.md) — copy-paste execution and expected outputs.
- [Validate a new dataset](validate-dataset.md) — use before analysing a private export.
- [Timebase and alignment](timebase-alignment.md) — when you need task/stimulus locking or multiple streams.
- [Reporting and reproducibility](reporting-reproducibility.md) — build the publication evidence bundle.
