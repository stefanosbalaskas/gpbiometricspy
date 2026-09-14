# Measurement before modelling

> **Python-native explanation article.** This page explains a development-line principle; it is not one of the 26 frozen R vignette companions.

Statistical sophistication cannot recover measurement information that was never recorded. Before asking which model is most powerful, first ask whether the input variables, clocks, grouping structure, and physiological source identity support the intended scientific meaning.

## Four measurement questions

### What quantity is this?

A value called `HR`, `IBI`, `RR`, `pupil`, or `time` can refer to materially different quantities. Scientific identity depends on units, acquisition route, preprocessing history, and device/export semantics—not the column label alone.

The cardiac-source provenance layer makes this explicit by distinguishing ECG NN intervals, ECG RR intervals, PPG pulse intervals, sampled heart-rate series, undocumented device intervals, and vendor-precomputed variability metrics.

### When was it measured?

Nominal sampling rate is a device specification. Event locking and multimodal fusion depend on observed timing behavior: timestamp intervals, jitter, gaps, resets, duplicates, clock identity, and matched anchors.

The timebase-provenance layer exists because a nominal “60 Hz” stream and a recorded stream with gaps or drift do not support identical temporal claims.

### At what unit does it vary?

A predictor may vary between participants, within participants, between items, within items, or at several levels. This determines whether a random slope is estimable and what a validation split actually tests.

A row-wise train/test split can look excellent while leaking participant-specific information. Whole-group validation asks a different and often more relevant question.

### What evidence was excluded or transformed?

Interpolation, filtering, artifact rules, peak rejection, baseline correction, and trial exclusion all change the data entering a model. Their settings and burden should therefore remain visible in the evidence trail.

## Why residual scale is not “noise quality” by default

Location–scale models estimate how the conditional distribution changes. A log-scale effect can describe greater or lower residual dispersion under the model, but it does not identify why that dispersion changed.

Possible contributors can include genuine behavioral heterogeneity, omitted predictors, task structure, measurement noise, participant variability, item variability, or other processes. Without external evidence, the scale equation should not be relabelled as a sensor-validity or artifact equation.

## Why heavy tails are not artifact detection

A Student-t outcome model can reduce sensitivity to unusually large residuals relative to a Gaussian model. That is a distributional robustness choice. It does not tell you which observations are artifacts, whether the sensor failed, or whether the large values should be removed.

## Why provenance belongs in software

Researchers often document provenance in prose after analysis. Encoding it in machine-readable objects adds three safeguards:

1. incompatible operations can fail closed;
2. reproducibility certificates can bind the scientific identity of inputs;
3. downstream analyses can state exactly which upstream evidence they consumed.

This is particularly important for multimodal studies, where timing and source assumptions can otherwise be distributed across scripts, acquisition notes, and analyst memory.

## A useful rule

<div class="gp-decision">
<strong>Do not ask the model to decide what the measurement was.</strong> Establish source identity, timing, units, validity evidence, and grouping structure first; then choose a model whose assumptions match that evidence.
</div>

See [Validate a new dataset](../../guides/validate-dataset.md), [Timebase and alignment](../../guides/timebase-alignment.md), [Cardiac source provenance](../../methods/cardiac-source-provenance.md), and [Measurement accountability](../../measurement-accountability.md).
