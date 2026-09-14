# Pupil, gaze and AOI example

<div class="gp-page-intro">
Use this route when your export contains pupil diameter, gaze coordinates, fixations, or areas of interest. The workflow keeps eye-tracking and physiology in a compatible table while preserving separate validity and interpretation requirements for each signal.
</div>

## Start with the channels

```python
import gpbiometricspy as gp

dat = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .copy()
    .iloc[:1800]
    .reset_index(drop=True)
)

overview = gp.plot_gazepoint_biometric_signals(
    dat,
    signal_cols=["LPMM", "FPOGX", "FPOGY"],
    time_col="TIME",
    standardize=True,
    main="Pupil diameter and gaze-position overview",
)
```

![Pupil diameter and gaze-position overview](../assets/generated/pupil-gaze-overview.png)

Before deriving features, verify which eye/channel the pupil measure represents, validity coding, missingness/blinks, coordinate space, and whether fixation events come from Gazepoint or a separate detector.

## AOI-linked summaries

```python
aoi = gp.summarise_gazepoint_aoi_biometrics(
    dat,
    aoi_col="AOI",
    signal_cols=["GSR_US", "HR", "LPMM"],
    group_cols=["participant_id"],
)

fig = gp.plot_gazepoint_aoi_biometrics(
    aoi["summary"],
    value_col="mean_value",
    aoi_col="aoi_label",
    signal_col="signal",
    title="AOI-linked biometric summaries",
)
```

![AOI-linked biometric summaries](../assets/generated/aoi-biometrics.png)

AOI-linked physiology is meaningful only when both sides of the join are defensible: gaze/AOI assignment and physiological timing/quality.

## Saccade diagnostics

The package also exposes gaze-event diagnostics such as a saccade main-sequence view:

![Saccade amplitude versus peak velocity](../assets/generated/saccade-main-sequence.png)

Use the relationship as a diagnostic of detected gaze events. It is not an automatic pass/fail certificate for calibration or participant data quality.

## Practical QC checklist

- Quantify pupil/gaze missingness and validity before smoothing or interpolation.
- Preserve blink/artifact flags and interpolation burden.
- Keep baseline windows tied to the experimental design.
- Document coordinate system and AOI definitions.
- Distinguish sample-level gaze from vendor fixation exports and algorithmically detected events.
- Verify event and gaze timebases before AOI/event-locked summaries.
- Treat pupil responses in the context of luminance, task, baseline, and measurement conditions.

## Scientific boundary

<div class="gp-science-boundary">
Pupil diameter, gaze allocation, fixation, saccade, and AOI-linked summaries are recorded or derived behavioral/physiological measures. They do not by themselves establish attention, comprehension, preference, emotion, trust, cognitive load, or diagnosis.
</div>

## Continue

- [Pupil and gaze QC](../articles/pupil-qc-workflow.md)
- [Eye-tracking ecosystem bridges](../articles/eye-tracking-ecosystem-bridges.md)
- [Event alignment and AOI-linked biometrics](../articles/event-alignment-aoi-workflow.md)
- [Multimodal example](multimodal.md)
