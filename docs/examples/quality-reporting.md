# Quality control and reporting example

<div class="gp-page-intro">
Quality control should leave visible evidence. This example combines signal activity, timing checks, missingness, design coverage, and generated figures so downstream exclusions and reporting decisions remain auditable.
</div>

## Core QC objects

```python
import gpbiometricspy as gp

dat = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)

gsr_quality = gp.audit_gazepoint_gsr_quality(dat, value_column="GSR_US")

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

## Visual evidence

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#signal-overview-and-quality"><img src="../assets/generated/missingness.png" alt="Missingness overview for EDA heart-rate IBI and pupil channels"><div class="gp-visual-card-body"><strong>Missingness</strong><span>Inspect channel availability across the recorded interval.</span></div></a>
<a class="gp-visual-card" href="../plot-gallery/#signal-overview-and-quality"><img src="../assets/generated/signal-quality.png" alt="EDA signal quality diagnostic"><div class="gp-visual-card-body"><strong>Signal quality</strong><span>Keep modality-specific quality evidence separate from model residuals.</span></div></a>
</div>

The expanded gallery also includes a general biometric-quality panel and design/inference diagnostics generated from package functions.

## Audit the experimental design

When the dataset contains participant, trial, and condition structure, inspect coverage before modelling:

```python
design = gp.audit_gazepoint_experiment_design(
    dat.rename(
        columns={
            "participant_id": "participant",
            "MEDIA_ID": "trial",
            "interface_complexity": "condition",
        }
    ),
    participant_col="participant",
    trial_col="trial",
    condition_col="condition",
)

coverage_plot = gp.plot_gazepoint_design_coverage(design)
```

This catches imbalance and sparse cells before they are hidden inside a downstream model.

## Build a report-ready evidence set

A useful QC bundle usually contains:

| Evidence | Why retain it |
|---|---|
| schema/input identity | shows what was actually analyzed |
| missingness/activity | documents available data and flat/dropout patterns |
| time resets/gaps | constrains event and alignment claims |
| modality-specific QC | records signal-level acceptance/review evidence |
| event/design coverage | shows whether intended conditions/trials were observed |
| QC figures | makes review decisions visually auditable |
| thresholds/windows | makes preprocessing reproducible |
| exclusions + reasons | prevents silent sample-size changes |
| package/backend versions | binds analysis to software identity |

## Do not turn QC into a hidden score

A single composite “quality” number can obscure why a recording failed. Prefer explicit dimensions—missingness, timing, peak plausibility, interval source, event coverage, interpolation burden—unless a validated composite score is scientifically justified.

## Scientific boundary

<div class="gp-science-boundary">
QC describes properties of the recorded data and the declared analysis pipeline. Passing QC does not prove construct validity, psychological interpretation, causal identification, or equivalence between different sensors.
</div>

## Continue

- [Validate a new dataset](../guides/validate-dataset.md)
- [Visual QC dashboard workflow](../articles/visual-qc-dashboard-workflow.md)
- [Reporting and reproducibility](../articles/reporting-reproducibility-workflow.md)
- [Reporting guide](../guides/reporting-reproducibility.md)
