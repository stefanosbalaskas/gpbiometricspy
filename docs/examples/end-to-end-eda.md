---
description: Runnable gpbiometricspy EDA example that produces QC evidence, decomposition, candidate SCR events, figures, tables, and methods text from bundled demonstration data.
search:
  boost: 1.4
---

# Runnable example: EDA from input to analysis bundle

<div class="gp-page-intro">
Use this page when you want the **shortest working example** of a complete `gpbiometricspy` analysis. The companion script is executable, deterministic, and checked in documentation CI.
</div>

## What you will produce

The example uses one bundled synthetic kiosk participant and creates:

- conductance-unit evidence;
- signal-activity, timing, quality and artifact audits;
- tonic and phasic EDA columns;
- a table of candidate SCR-like events;
- a group event summary;
- decomposition and event-diagnostic figures;
- a biometric reporting checklist;
- conservative methods text;
- a JSON `PASS` record on successful completion.

!!! note
    The demonstration is synthetic teaching data. The workflow is real; the rows are not empirical participant observations.

## Run the checked script

From the repository root:

```bash
python examples/hands-on/end-to-end-eda-research.py
```

A successful run ends with JSON containing:

```json
{"status": "PASS", "tutorial": "end-to-end-eda-research"}
```

The actual record also describes the object types/rows created by the run.

## Save all outputs

=== "macOS / Linux"

    ```bash
    GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR=outputs/eda-research \
      python examples/hands-on/end-to-end-eda-research.py
    ```

=== "PowerShell"

    ```powershell
    $env:GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR = "outputs/eda-research"
    python examples/hands-on/end-to-end-eda-research.py
    ```

Expected bundle:

```text
outputs/eda-research/
├── eda_decomposition.csv
├── scr_events.csv
├── scr_group_summary.csv
├── analysis_checklist_overview.csv
├── methods_text.txt
├── end-to-end-eda-research-01.png
└── end-to-end-eda-research-02.png
```

## The same workflow in readable Python

```python
import gpbiometricspy as gp

# Load deterministic demonstration data.
data = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)
groups = ["participant_id"]

# Audit measurement/timing before processing.
units = gp.audit_gazepoint_gsr_units(data, gsr_col="GSR_US")
activity = gp.audit_gazepoint_signal_activity(
    data,
    signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
    group_cols=groups,
)
time_resets = gp.audit_gazepoint_time_resets(
    data,
    time_col="TIME",
    group_cols=groups,
)
quality = gp.audit_gazepoint_gsr_quality(data, value_column="GSR_US")
artifacts = gp.audit_gazepoint_eda_artifacts(
    data,
    signal_col="GSR_US",
    time_col="TIME",
    group_cols=groups,
)

# Derive explicit tonic/phasic components.
decomposition = gp.decompose_gazepoint_eda(
    data,
    signal_col="GSR_US",
    time_col="TIME",
    group_cols=groups,
    window_size=31,
    output_prefix="eda",
)

# Detect candidate events from the phasic component.
scr = gp.detect_gazepoint_scr_events(
    decomposition,
    phasic_col="eda_phasic",
    signal_col="GSR_US",
    time_col="TIME",
    group_cols=groups,
    threshold=None,
    min_peak_distance=10,
)

# Inspect the transformation and event placement.
decomposition_plot = gp.plot_gazepoint_eda_decomposition(
    decomposition,
    time_col="TIME",
    signal_cols=["GSR_US", "eda_tonic", "eda_phasic"],
    group_cols=groups,
    title="Observed, tonic and phasic EDA",
)

scr_plot = gp.plot_gazepoint_scr_events(
    decomposition,
    scr["events"],
    time_col="TIME",
    signal_col="GSR_US",
    phasic_col="eda_phasic",
    group_cols=groups,
    title="Candidate SCR events",
)

# Create reporting evidence.
checklist = gp.create_gazepoint_biometrics_checklist(data)
methods_text = gp.create_gazepoint_biometrics_methods_text(checklist=checklist)
```

## Inspect the important outputs

```python
print(decomposition.attrs["overview"])
print(decomposition.attrs["settings"])
print(scr["overview"])
print(scr["events"].head())
print(scr["group_summary"])
print(scr["settings"])
print(checklist["overview"])
print(methods_text)
```

Do not jump directly to `scr["events"]`. The QC and settings objects are part of the scientific result because they explain whether and how the derived table was produced.

## Visual result

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/eda-decomposition.png" alt="Observed tonic and phasic EDA components"><div class="gp-visual-card-body"><strong>EDA decomposition</strong><span>Observed signal and derived components remain visually reviewable.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr"><img src="../assets/generated/scr-events.png" alt="EDA signal with candidate SCR events"><div class="gp-visual-card-body"><strong>Candidate SCR events</strong><span>Detector output is checked against the waveform before summarisation.</span></div></a>
</div>

## Why this is more than a code snippet

The example enforces the package's intended workflow order:

1. **Measurement evidence first.** Units, activity, timing, quality and artifacts are audited before deriving features.
2. **Transformations are named.** Tonic and phasic outputs remain explicit columns rather than hidden intermediate arrays.
3. **Detection settings are retained.** The SCR object includes its settings and group summaries.
4. **Plots are evidence.** Diagnostic figures are exported with the tabular outputs.
5. **Reporting is part of the workflow.** A checklist and methods starting point are produced before the analysis is considered finished.

## Adapt it to a research export

Replace only the input and column mapping first. Then rerun the audits before changing any processing settings.

```python
data = gp.import_gazepoint_biometrics("data/my_export.csv")

groups = ["participant_id"]  # map to your actual participant/session structure
time_col = "TIME"            # verify the actual clock and units
eda_col = "GSR_US"           # verify the actual channel and units
```

For study data, also retain explicit exclusion decisions and experimental event/condition mappings. If you need stimulus-locked EDA, establish clock/event validity before constructing response windows.

## What not to infer

<div class="gp-science-boundary">
Candidate SCR events and tonic/phasic EDA summaries are physiological waveform features. They are not direct labels of emotion, stress, attention, preference, deception, clinical state, or treatment effect. Those interpretations require valid measurement, design and inferential evidence beyond this processing example.
</div>

## Go deeper

- [Hands-on EDA research guide](../guides/hands-on-eda-research.md) explains every step and how to substitute your own export.
- [End-to-end research workflow](../workflows/end-to-end-eda-research.md) shows the continue/review gates and report-ready completion criteria.
- [EDA / GSR / SCR example](eda-scr.md) provides domain-specific diagnostics and deeper links.
- [Reporting and reproducibility](../guides/reporting-reproducibility.md) covers publication evidence.
