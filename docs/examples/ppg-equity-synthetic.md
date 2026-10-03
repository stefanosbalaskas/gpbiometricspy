# PPG pigmentation audit: synthetic worked example

<script>
window.MathJax = {tex: {inlineMath: [["\\(", "\\)"]], displayMath: [["\\[", "\\]"]], processEscapes: true}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<div class="gp-page-intro">
This worked example is a **deterministic synthetic stress test** for the Python-native PPG Pigmentation & Measurement-Equity Audit. It is designed to teach the difference between signal quality, retention, and reference accuracy. It is not a biological model and it is not evidence that pigmentation causes any particular PPG failure mode.
</div>

## What the example is constructed to show

The synthetic data deliberately create a case in which:

- the optical waveform becomes harder to retain at lower synthetic ITA values;
- motion makes both waveform quality and candidate-HR retention worse;
- the candidate HR error distribution depends on activity;
- **ITA is not part of the candidate-HR error equation**.

That gives the audit a known target: it should be able to reveal a retention difference without converting that result into a claim that reference accuracy is pigmentation-driven.

![Synthetic candidate-HR retention over ITA](../assets/ppg-equity/ppg-equity-synthetic-retention.svg)

![Synthetic HR reference error over ITA](../assets/ppg-equity/ppg-equity-synthetic-reference-error.svg)

## 1. Pigmentation measurement

The example generates CIELAB \(L^*\) and \(b^*\) values and derives Individual Typology Angle (ITA) using the same public helper used by the audit:

\[
ITA^\circ = \arctan\!\left(\frac{L^* - 50}{b^*}\right)\frac{180}{\pi}.
\]

The inverse relationship used only to construct internally consistent synthetic CIELAB values is

\[
L^* = 50 + b^* \tan\!\left(ITA^\circ\frac{\pi}{180}\right).
\]

The continuous ITA value is the analytical variable. Presentation bins are secondary and are never treated as interchangeable with Monk, Fitzpatrick, race, or ethnicity.

## 2. Reference heart rate

For participant \(i\), activity \(a\), and sample \(t\), the synthetic reference heart rate is

\[
HR^{ref}_{iat}
= b_i + \delta_a + 1.8\sin\left(2\pi t/T\right),
\]

where \(b_i\) is a participant-specific baseline and \(\delta_a\) is an activity effect. In the default generator:

| Activity | \(\delta_a\) |
| --- | ---: |
| Rest | 0 bpm |
| Typing | 8 bpm |
| Walk | 34 bpm |

The pulse frequency is

\[
f_{iat}=\frac{HR^{ref}_{iat}}{60}.
\]

The phase of the synthetic waveform accumulates this instantaneous frequency over the sampling grid.

## 3. Synthetic PPG waveform

The recorded optical waveform is generated as

\[
PPG_{iat}
= 1 + A_i\sin(\phi_{iat})
+0.30A_i\sin(2\phi_{iat}+0.4)
+\epsilon_{iat},
\]

where the amplitude term \(A_i\) is deliberately allowed to vary with the synthetic ITA value. This is **only a software stress mechanism**. The package does not claim that this equation describes human tissue optics.

Motion increases the waveform noise term during walking. The resulting traces are used to exercise finite-data proportion, AC amplitude, DC level, AC/DC ratio, spectral SNR, flatness, and beat-template correlation.

![Synthetic raw PPG waveforms](../assets/ppg-equity/ppg-equity-synthetic-waveforms.svg)

## 4. Retention mechanism

The probability that a synthetic waveform sample is missing is created from a logistic model:

\[
\operatorname{logit}\{P(M_{iat}=1)\}
= \alpha_0 + \alpha_1 ITA_i + \alpha_2 I(a=\text{Typing}) + \alpha_3 I(a=\text{Walk}).
\]

The signs are chosen so lower synthetic ITA and more motion produce more missing observations. The candidate-HR measurement has a similar retention mechanism.

The audit does **not** fit this exact generating model. Instead, when an objective pigmentation metric is supplied it estimates a participant-clustered descriptive association such as

\[
\operatorname{logit}\{P(R_{ij}=1)\}
= \gamma_0 + \gamma_1 ITA_i,
\]

with participant-level bootstrap resampling. Here \(R_{ij}=1\) means the reference is available and the candidate measurement is retained.

## 5. Accuracy mechanism

Candidate HR is generated as

\[
HR^{cand}_{iat}
= HR^{ref}_{iat} + e_{iat},
\]

with

\[
e_{iat}\sim\mathcal{N}(0,\sigma_a^2).
\]

Crucially, \(ITA_i\) is not included in \(\sigma_a\) or in the mean error. Activity drives the synthetic error distribution. This creates the intended demonstration: **retention can vary even when the accuracy-generating mechanism is ITA-neutral**.

For paired measurements the audit reports

\[
\text{Bias}=\frac{1}{n}\sum_{k=1}^n(HR^{cand}_k-HR^{ref}_k),
\]

\[
MAE=\frac{1}{n}\sum_{k=1}^n\left|HR^{cand}_k-HR^{ref}_k\right|,
\]

\[
RMSE=\sqrt{\frac{1}{n}\sum_{k=1}^n(HR^{cand}_k-HR^{ref}_k)^2},
\]

and Bland--Altman limits

\[
\bar d \pm 1.96s_d.
\]

Lin's concordance correlation coefficient is also reported:

\[
\rho_c = \frac{2\operatorname{cov}(X,Y)}{\operatorname{var}(X)+\operatorname{var}(Y)+(\mu_X-\mu_Y)^2}.
\]

These error statistics use paired observations. Retention uses all rows for which the reference measurement is available, so missing candidate values cannot silently disappear from the denominator.

## 6. PPG signal-quality indicators

The Python-native audit extends the existing waveform-quality path with PPG-specific descriptive SQIs.

A robust AC amplitude is constructed from the central waveform range:

\[
AC = \frac{Q_{0.95}(PPG)-Q_{0.05}(PPG)}{2},
\]

with

\[
DC = \operatorname{median}(PPG),
\qquad
AC/DC = \frac{AC}{|DC|}.
\]

The spectral SNR is

\[
SNR_{dB}=10\log_{10}\left(\frac{P_{pulse}}{P_{noise}}\right),
\]

where the pulse band is centered on the dominant component within the 0.5--5 Hz analysis region and remaining in-band power forms the noise term.

No individual SQI automatically determines whether a participant is scientifically valid. The retained/not-retained status reuses the package's declared waveform-QC rules.

## 7. Participant-cluster bootstrap

Rows from the same participant are not independent. The uncertainty calculations therefore resample participants rather than individual signal samples.

For bootstrap replicate \(b\):

\[
\mathcal{I}^{(b)} = \{i^{(b)}_1,\ldots,i^{(b)}_N\},
\]

where the participant IDs are sampled with replacement. Every row belonging to a sampled participant is carried into that replicate. The 2.5th and 97.5th percentiles of the bootstrap distribution form the default 95% interval.

This matters because treating tens of thousands of waveform rows as independent would create unrealistically narrow intervals.

## 8. Run the complete example

From a repository checkout:

```bash
python scripts/generate_ppg_equity_synthetic_demo.py \
  --output-dir docs/assets/ppg-equity \
  --seed 20261003 \
  --participants 36 \
  --n-boot 400
```

The script generates the synthetic data in memory, runs `ppg_pigmentation_audit()`, writes manuscript-ready derived tables, and regenerates the SVG figures shown on this page. Row-level synthetic data are **not** written unless `--write-data` is explicitly supplied.

For a fast figure-only rebuild:

```bash
python scripts/generate_ppg_equity_synthetic_demo.py \
  --output-dir docs/assets/ppg-equity \
  --render-only
```

## 9. Equivalent direct API workflow

```python
from gpbiometricspy.ppg_equity import ppg_pigmentation_audit

result = ppg_pigmentation_audit(
    data,
    participant_col="participant",
    ppg_col="HRP",
    pigmentation_metric="cielab",
    l_star_col="skin_L_star",
    a_star_col="skin_a_star",
    b_star_col="skin_b_star",
    pigmentation_method="synthetic_colorimetry",
    pigmentation_site="pigmentation_site",
    sensor_site="sensor_site",
    instrument_manufacturer="instrument_vendor",
    instrument_model="instrument_model",
    time_col="time_s",
    group_cols=["activity"],
    sampling_rate_hz=60,
    reference_col="ecg_hr",
    candidate_col="ppg_hr",
    metric_name="heart_rate",
    device_col="device",
    condition_col="activity",
    n_boot=1000,
    random_state=20261003,
)
```

The principal result objects are:

```text
metadata
acquisition_quality
reference_agreement
warnings
reporting_text
provenance
settings
```

The most important reading order is:

1. metadata provenance;
2. raw acquisition quality;
3. retention/missingness;
4. paired reference agreement;
5. only then, any pigmentation-associated descriptive model.

## 10. What a correct conclusion looks like

The synthetic example is intentionally constructed so a statement like this can be correct:

> Candidate-HR retention varied across the synthetic ITA range, while the generating mechanism for paired HR error depended on activity rather than ITA.

That is very different from:

> Pigmentation caused inaccurate heart-rate measurements.

The second statement is not supported by this synthetic design and is not generated by the package.

## Reproducibility assets

The page uses deterministic SVG and CSV outputs generated by `scripts/generate_ppg_equity_synthetic_demo.py`:

- [`ppg-equity-synthetic-retention.svg`](../assets/ppg-equity/ppg-equity-synthetic-retention.svg)
- [`ppg-equity-synthetic-reference-error.svg`](../assets/ppg-equity/ppg-equity-synthetic-reference-error.svg)
- [`ppg-equity-synthetic-waveforms.svg`](../assets/ppg-equity/ppg-equity-synthetic-waveforms.svg)
- [`ppg-equity-synthetic-bin-summary.csv`](../assets/ppg-equity/ppg-equity-synthetic-bin-summary.csv)
- [`ppg-equity-synthetic-participant-summary.csv`](../assets/ppg-equity/ppg-equity-synthetic-participant-summary.csv)

Continue with the [external-evidence protocol](../ppg-equity-external-evidence/) for the STEP and ENCoDE adapters and with the [method note](../methods/ppg-pigmentation-equity/) for the scientific interpretation boundary.
