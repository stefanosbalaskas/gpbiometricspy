# Auditing PPG measurement equity: separating signal quality, availability, and reference agreement

<div class="gp-page-intro">
Optical PPG performance can vary with acquisition context, device design, motion, perfusion, anatomical site, contact, signal processing, and skin-pigmentation measurement. A defensible audit should therefore avoid collapsing every difference into one error statistic. This article explains the measurement-equity architecture introduced in `gpbiometricspy 0.1.8`: preserve pigmentation provenance, inspect raw signal quality, analyse paired availability separately, then evaluate agreement with an appropriate reference.
</div>

<div class="gp-version-note">
<strong>Added in 0.1.8.</strong> The public method is documented at <a href="../../../methods/ppg-pigmentation-equity/">PPG pigmentation & measurement equity</a>, the fully reproducible known-truth demonstration is the <a href="../../../examples/ppg-equity-synthetic/">synthetic worked example</a>, and the independent restricted-data stress test is recorded in the <a href="../../../ppg-equity-external-evidence/">STEP external-evidence record</a>.
</div>

## Why one number is not enough

Suppose a wearable produces heart-rate estimates that agree reasonably well with ECG whenever a value is available. That does not establish that the device retained the same amount of usable data across the acquisition space. Conversely, lower waveform amplitude does not automatically imply poorer reference accuracy.

The audit therefore keeps four layers distinct:

\[
\text{pigmentation provenance}
\rightarrow
\text{raw PPG quality}
\rightarrow
\text{paired availability}
\rightarrow
\text{reference agreement}.
\]

These layers can diverge. The synthetic example intentionally demonstrates exactly that property.

<div class="gp-gallery">
<figure>
<img src="../../../assets/ppg-equity/ppg-equity-synthetic-waveforms.svg" alt="Synthetic PPG waveforms illustrating acquisition-quality differences" loading="lazy" decoding="async">
<figcaption><strong>Acquisition quality.</strong> Raw waveform amplitude and SQI evidence are inspected before reference-error summaries.</figcaption>
</figure>
<figure>
<img src="../../../assets/ppg-equity/ppg-equity-synthetic-retention.svg" alt="Synthetic candidate-heart-rate retention across ITA values" loading="lazy" decoding="async">
<figcaption><strong>Availability.</strong> The known-truth synthetic mechanism changes candidate-HR retention across the observed ITA range.</figcaption>
</figure>
<figure>
<img src="../../../assets/ppg-equity/ppg-equity-synthetic-reference-error.svg" alt="Synthetic reference error across ITA values" loading="lazy" decoding="async">
<figcaption><strong>Reference agreement.</strong> The synthetic HR-error mechanism is intentionally ITA-neutral even though retention changes.</figcaption>
</figure>
</div>

The central lesson is therefore:

\[
\boxed{\text{amplitude} \neq \text{quality} \neq \text{availability} \neq \text{accuracy}}.
\]

## Step 1 — preserve what was actually measured

Pigmentation variables are not interchangeable. `gpbiometricspy` distinguishes:

| Evidence class | Examples | Default analytical use |
| --- | --- | --- |
| Objective / instrumental | CIELAB, ITA, melanin index | continuous descriptive association plus optional strata |
| Subjective scales | Fitzpatrick, Monk, Pantone, von Luschan | descriptive categorical strata |
| Demographic proxy | race, ethnicity | **not treated as pigmentation** |

When CIELAB values are available, Individual Typology Angle is

\[
ITA^\circ=\arctan\left(\frac{L^*-50}{b^*}\right)\frac{180}{\pi}.
\]

The continuous ITA value is retained as the primary quantitative measure. Categories can be useful for presentation, but they do not turn a subjective scale into an objective optical measurement.

The metadata validator also keeps measurement site, PPG sensor site, instrument, assessor, missingness provenance, and source method visible. This matters because apparent pigmentation-associated differences can be entangled with anatomical site, device geometry, contact, motion, or other acquisition factors.

## Step 2 — inspect raw PPG quality before modelling downstream outcomes

The PPG quality layer exposes descriptive signal-quality evidence rather than declaring one universal validity score. Useful quantities include robust AC amplitude,

\[
AC=\frac{Q_{0.95}(PPG)-Q_{0.05}(PPG)}{2},
\]

DC level,

\[
DC=\operatorname{median}(PPG),
\]

relative pulsatility,

\[
AC/DC=\frac{AC}{|DC|},
\]

and a spectral signal-to-noise statistic,

\[
SNR_{dB}=10\log_{10}\left(\frac{P_{pulse}}{P_{noise}}\right).
\]

These are diagnostics. None automatically proves scientific validity, and none should be used as a surrogate outcome simply because it is easy to compute.

## Step 3 — treat availability as its own outcome

Reference-error analyses condition on observations where both the candidate and reference values exist. That denominator can hide systematic differences in whether the candidate value was available in the first place.

For objective pigmentation measures, a descriptive retention model can be written conceptually as

\[
\operatorname{logit}\{P(R_{ij}=1)\}
=\gamma_0+\gamma_1 X_i,
\]

with participant-cluster uncertainty for repeated rows. The implementation reports the association descriptively; it is not interpreted as a causal optical mechanism.

A critical caveat is denominator meaning. In datasets whose devices report at different cadences, row-level `retention_rate` can primarily describe **paired reporting density on the source grid**. It must not automatically be relabelled as device dropout, failure rate, or fairness.

## Step 4 — evaluate reference agreement separately

For paired observations, let

\[
d_k=Y_k-X_k,
\]

where `Y` is the candidate wearable value and `X` the reference. The agreement layer reports complementary quantities rather than one winner:

\[
\text{Bias}=\frac{1}{n}\sum d_k,
\qquad
MAE=\frac{1}{n}\sum |d_k|,
\]

\[
RMSE=\sqrt{\frac{1}{n}\sum d_k^2},
\]

Bland–Altman limits

\[
\bar d\pm1.96s_d,
\]

and Lin's concordance correlation coefficient

\[
\rho_c=
\frac{2\operatorname{cov}(X,Y)}
{\operatorname{var}(X)+\operatorname{var}(Y)+(\mu_X-\mu_Y)^2}.
\]

Because wearable studies usually contain many repeated rows per participant, uncertainty is estimated by resampling participants rather than individual samples.

## The STEP external-evidence tranche

The release was also exercised on an authorized local copy of **BigIdeasLab_STEP v1.0** under the applicable PhysioNet DUA. Restricted participant-level rows were not committed or redistributed.

![Aggregate-only STEP evidence summary](../../../assets/ppg-equity/step-aggregate-evidence.svg)

The authorized run involved **53 participants**, **six wearable devices**, Fitzpatrick categories **1–6**, and **361,675 paired wearable–ECG measurements**. The source also contained the four documented activity labels plus an unlabeled/NA stratum; that stratum remains unknown rather than being assigned a physiological meaning.

STEP is useful precisely because it stresses several real-world boundaries at once:

- repeated observations within participants;
- multiple consumer/wearable devices;
- activity-dependent measurement conditions;
- subjective Fitzpatrick phototype rather than objective colorimetry;
- device-specific reporting cadence;
- independent ECG reference heart rate.

### Why STEP does not justify a continuous pigmentation regression

Fitzpatrick phototype is subjective categorical provenance. The package therefore intentionally skips continuous pigmentation-association models for the STEP run and records the warning

```text
continuous_association_models_not_run_for_nonobjective_pigmentation_metric
```

The corresponding continuous-association CSVs are intentionally empty. That is a scientific guardrail, not an estimator failure.

### Why STEP availability is not a fairness score

The devices report at materially different frequencies. Cross-device row-level paired availability therefore reflects reporting density/cadence as well as missingness. A lower value cannot, by itself, establish more hardware failure or worse fairness.

The release-facing interpretation is consequently narrower: compare device/activity-specific agreement and paired availability while retaining their denominators and acquisition context.

## Synthetic evidence and external evidence answer different questions

The two evidence layers should not be collapsed:

\[
\text{synthetic evidence}
\Rightarrow
\text{software behavior under known truth},
\]

whereas

\[
\text{external evidence}
\Rightarrow
\text{software behavior on independently collected measurements}.
\]

The synthetic generator lets us know the data-generating mechanism. STEP does not. STEP therefore tests ergonomics, schema handling, repeated-measure uncertainty, stratified reporting, provenance, and interpretation boundaries rather than proving a causal pigmentation mechanism.

## What the 0.1.8 evidence supports

The 0.1.8 evidence supports the narrower claims that:

- the PPG measurement-equity API separates pigmentation provenance, signal quality, availability, and reference agreement;
- objective and subjective pigmentation measures are handled differently;
- repeated observations can use participant-cluster uncertainty;
- the workflow has been exercised on deterministic known-truth data and on an independently collected restricted wearable–ECG dataset;
- the software preserves reporting and interpretation guardrails when continuous objective pigmentation is not available.

It does **not** establish:

- a causal effect of pigmentation or melanin on PPG performance;
- equivalence of Fitzpatrick with ITA, CIELAB, melanin index, race, or ethnicity;
- generic device fairness;
- a universal pigmentation correction;
- clinical pulse-oximeter or SpO₂ validation;
- empirical ENCoDE validation in this release.

## Reproducible route through the package

Use the following sequence when adapting the method to another dataset:

1. preserve the original pigmentation variable and its measurement provenance;
2. record pigmentation-measurement site and PPG sensor site;
3. inspect raw PPG waveform quality and missingness;
4. define the candidate/reference denominator explicitly;
5. report paired availability separately from paired error;
6. stratify by device/activity/acquisition context when scientifically required;
7. use participant-level resampling for repeated observations;
8. describe associations without converting them into causal optical claims;
9. retain warnings and provenance text with manuscript-ready outputs.

<div class="gp-actions">
<a class="md-button md-button--primary" href="../../../examples/ppg-equity-synthetic/">Run the synthetic worked example</a>
<a class="md-button" href="../../../methods/ppg-pigmentation-equity/">Read the method specification</a>
<a class="md-button" href="../../../ppg-equity-external-evidence/">Inspect STEP evidence</a>
<a class="md-button" href="../../../plot-gallery/">Open the plot gallery</a>
</div>
