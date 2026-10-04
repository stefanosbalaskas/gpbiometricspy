# PPG pigmentation audit: external scientific evidence

<script>
window.MathJax = {tex: {inlineMath: [["\\(", "\\)"]], displayMath: [["\\[", "\\]"]], processEscapes: true}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<div class="gp-page-intro">
This page records the external-evidence programme for the Python-native PPG Pigmentation & Measurement-Equity Audit. Restricted PhysioNet source rows are **not redistributed** by gpbiometricspy. The release-facing evidence scope is intentionally **STEP-only**; ENCoDE remains implemented as future provenance/schema evidence but is not a prerequisite for the current stable release.
</div>

<div class="gp-actions">
<a class="md-button md-button--primary" href="../articles/python-native/ppg-measurement-equity/">Read the explanation article</a>
<a class="md-button" href="../examples/ppg-equity-synthetic/">Run the synthetic example</a>
<a class="md-button" href="../methods/ppg-pigmentation-equity/">Read the method specification</a>
</div>

## Evidence status

The repository distinguishes source verification, executable adapters, synthetic contract testing, and genuine restricted-data execution:

| Evidence layer | STEP | ENCoDE |
| --- | --- | --- |
| Official source/public schema verified | **Yes** | **Yes** |
| Reproducible local adapter implemented | **Yes** | **Yes** |
| Synthetic schema fixture exercised in CI | **Yes** | **Yes** |
| Authorized restricted-data execution completed | **Yes** | **Deferred** |
| Restricted participant rows committed or redistributed | **No** | **No** |

STEP was executed locally on an authorized PhysioNet copy under the applicable DUA. ENCoDE was not executed on restricted patient data and must not be described as empirically validated.

## BigIdeasLab_STEP: executed external evidence

The official PhysioNet STEP resource contains synchronized ECG reference HR and six wearable-device HR streams together with participant ID, Fitzpatrick phototype and activity.

Official source: [PhysioNet BigIdeasLab_STEP v1.0](https://physionet.org/content/bigideaslab-step-hr-smartwatch/1.0/)

Version DOI: [10.13026/cqfy-d860](https://doi.org/10.13026/cqfy-d860)

Associated study: Bent B, Goldstein BA, Kibbe WA, Dunn JP. *Investigating sources of inaccuracy in wearable optical heart rate sensors.* npj Digital Medicine. 2020;3:18. [doi:10.1038/s41746-020-0226-6](https://doi.org/10.1038/s41746-020-0226-6)

### Authorized execution record

The real-data adapter was executed against exact gpbiometricspy source:

```text
dc2b539154f65061a90d360f01503108ad1fd39f
```

The local execution used Python 3.11.9, gpbiometricspy package identity `0.1.7`, 1,000 participant-cluster bootstrap replicates and random seed `20261003`.

Observed real-data counts were:

| Quantity | Observed value |
| --- | ---: |
| Participants | 53 |
| Long-format device rows | 1,431,570 |
| Rows with ECG reference available | 1,328,850 |
| Paired wearable/ECG measurements | 361,675 |
| Wearable devices | 6 |
| Fitzpatrick range | 1–6 |

![Aggregate-only STEP external-evidence summary](assets/ppg-equity/step-aggregate-evidence.svg)

The figure above is built only from the DUA-safe aggregate counts retained in this public evidence record. It does not reproduce or encode participant-level rows.

All required derived output files were produced. The final local derived-only evidence archive was:

```text
gpbiometricspy_STEP_derived_evidence.zip
SHA256 65EF1DE84CF711F9E6753DB771E3E2386FD6926A104E0D4DC1618EE88E8744B1
```

The restricted `deidentified_data.csv` remained outside the repository and was not redistributed.

### What the STEP adapter evaluates

For synchronized wearable and ECG observations,

\[
e_{ijkt}=HR^{wearable}_{ijkt}-HR^{ECG}_{ijkt},
\]

with device \(j\), activity \(k\), participant \(i\), and synchronized observation \(t\).

The adapter reports paired-measurement agreement separately from row-level paired availability. Agreement outputs include:

\[
\text{Bias},\quad MAE,\quad RMSE,\quad \rho_c,\quad LoA,
\]

with participant-cluster bootstrap uncertainty.

### Fitzpatrick is categorical here

STEP records Fitzpatrick phototype, a **subjective** scale. gpbiometricspy therefore does not reinterpret Fitzpatrick as objective optical pigmentation, melanin index, ITA, race or ethnicity.

The derived files

```text
step-continuous-associations.csv
step-retention-association.csv
```

are intentionally empty for this run. Continuous pigmentation association models are restricted to objective pigmentation metrics by the public API. The real execution therefore produced the expected warning:

```text
continuous_association_models_not_run_for_nonobjective_pigmentation_metric
```

This is a scientific guardrail, not a failed estimator.

### Row-level availability is not generic device missingness

STEP devices have materially different native/reporting frequencies. The adapter denominator for `retention_rate` is all rows with an available ECG reference, so the resulting quantity strongly reflects reporting cadence and source-grid design.

For STEP, release-facing interpretation should therefore use **row-level paired availability** or **reporting density**, not generic dropout, device missingness, or a fairness score.

A low STEP row-level availability value does not by itself establish that a device failed more often, and cross-device values must not be compared as though all devices sampled on the same cadence.

### Unlabelled activity rows

The authorized source contained the four documented activity labels plus an unlabeled/NA stratum. Source-grid counts observed locally were:

| Activity label | Source-time rows |
| --- | ---: |
| Unlabelled / NA | 86,609 |
| Rest | 49,669 |
| Breathe | 12,008 |
| Activity | 77,585 |
| Type | 12,724 |

The unlabeled stratum is retained as unlabeled/NA. Its physiological meaning is **not inferred** from the dataset alone.

### Historical study results are anchors, not package oracles

The associated 2020 publication reported no overall skin-tone association with HR measurement error in its marginal mixed model (`p = 0.634`), alongside strong device/activity effects and a skin-tone-by-device interaction.

The gpbiometricspy evidence programme does not require reproduction of that single p-value. Its purpose is to exercise the current package contract: transparent device/activity stratification, paired-reference agreement, participant-cluster uncertainty, and explicit separation of availability from error.

### Reproduce STEP locally

After obtaining the data legitimately from PhysioNet:

```bash
python scripts/run_step_ppg_equity_evidence.py \
  --csv /secure/path/to/deidentified_data.csv \
  --output-dir external-evidence/step \
  --n-boot 1000 \
  --seed 20261003
```

The expected official column contract is:

```text
ECG
Apple Watch
Empatica
Garmin
Fitbit
Miband
Biovotion
ID
Skin Tone
Activity
```

Only derived summaries are written by the adapter. Review the applicable DUA before sharing even derived results.

## ENCoDE: implemented but deferred

ENCoDE remains scientifically useful because it contains substantially richer pigmentation provenance, including objective/instrumental and subjective skin-colour measurements, anatomical-site information and linked clinical data.

Official source: [PhysioNet ENCoDE v1.0.0](https://physionet.org/content/encode-skin-color/1.0.0/)

Public tutorial: [aiwonglab/ENCoDE_tutorial](https://github.com/aiwonglab/ENCoDE_tutorial)

The repository retains `scripts/run_encode_pigmentation_schema_stress.py`, its schema contract and synthetic fixtures. However, restricted ENCoDE data were **not** empirically executed for this release tranche. ENCoDE is therefore future optional evidence, not part of the present external empirical qualification.

No clinical SpO2 claim is made from the existence of the ENCoDE adapter.

## What STEP qualification does and does not support

The completed STEP run supports the claim that the package's wearable-HR reference-agreement workflow has been exercised on independently collected restricted data with repeated participant observations, multiple devices, activity strata and subjective Fitzpatrick categories.

It does **not** establish:

- objective-pigmentation performance across ITA, CIELAB or melanin-index gradients;
- a causal optical effect of pigmentation;
- clinical pulse-oximeter accuracy;
- device fairness, absence of bias, or correction for skin tone;
- equivalence of row-level availability across devices with different reporting cadences.

## Relationship to the synthetic example

The [synthetic worked example](examples/ppg-equity-synthetic.md) remains the fully reproducible public artifact for known mechanisms:

\[
\text{synthetic evidence} \Rightarrow \text{software behavior under known truth},
\]

while the authorized STEP execution provides:

\[
\text{external evidence} \Rightarrow \text{behavior on independently collected measurements}.
\]

The two evidence layers are complementary and are reported separately. The [PPG measurement-equity explanation article](articles/python-native/ppg-measurement-equity/index.md) connects them in one narrative without treating either as stronger evidence than it is.
