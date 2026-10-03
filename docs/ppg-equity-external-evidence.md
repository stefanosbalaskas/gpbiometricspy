# PPG pigmentation audit: external scientific evidence

<script>
window.MathJax = {tex: {inlineMath: [["\\(", "\\)"]], displayMath: [["\\[", "\\]"]], processEscapes: true}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<div class="gp-page-intro">
This page records the pre-release external-evidence programme for the Python-native PPG Pigmentation & Measurement-Equity Audit. The source datasets are credentialed PhysioNet resources and are **not redistributed** by gpbiometricspy.
</div>

## Evidence status

The repository distinguishes four states that must not be conflated:

| Evidence layer | STEP | ENCoDE |
| --- | --- | --- |
| Official source/public schema verified | **Yes** | **Yes** |
| Reproducible local adapter implemented | **Yes** | **Yes** |
| Synthetic schema fixture exercised in CI | **Yes** | **Yes** |
| Restricted source rows empirically executed in this public repository | **No** | **No** |

The last row is intentionally **No** until an authorized local copy is run under the applicable PhysioNet agreement. A public repository must not turn a restricted-data access requirement into an implied validation result.

## BigIdeasLab_STEP

The official PhysioNet STEP resource contains synchronized ECG reference HR and six wearable-device HR streams together with participant ID, Fitzpatrick skin type, and activity. The public resource description reports 53 participants with approximately equal representation across Fitzpatrick types 1--6 and the activity states Rest, Activity, Breathe, and Type.

Official source: [PhysioNet BigIdeasLab_STEP v1.0](https://physionet.org/content/bigideaslab-step-hr-smartwatch/1.0/)

Associated study: Bent B, Goldstein BA, Kibbe WA, Dunn JP. *Investigating sources of inaccuracy in wearable optical heart rate sensors.* npj Digital Medicine. 2020;3:18. [doi:10.1038/s41746-020-0226-6](https://doi.org/10.1038/s41746-020-0226-6)

### Why STEP is useful here

STEP directly exercises the **reference-agreement and retention** layer:

\[
e_{ijkt}=HR^{wearable}_{ijkt}-HR^{ECG}_{ijkt},
\]

with device \(j\), activity \(k\), participant \(i\), and synchronized observation \(t\).

For each device/activity stratum the adapter derives:

\[
\text{Bias},\quad MAE,\quad RMSE,\quad \rho_c,\quad LoA,
\]

plus the retained-measurement denominator. Fitzpatrick is retained as a **subjective phototype scale**, so gpbiometricspy does not silently treat it as a continuous optical pigmentation measure.

The associated 2020 publication reported no overall skin-tone association with HR measurement error in its marginal mixed model (`p = 0.634`), strong device and activity effects, and a significant skin-tone-by-device interaction. The purpose of the gpbiometricspy adapter is **not** to force reproduction of one p-value. It is to provide transparent device/activity/retention summaries using the package's current measurement-accountability contract.

### Run STEP locally

After obtaining the data legitimately from PhysioNet:

```bash
python scripts/run_step_ppg_equity_evidence.py \
  --csv /secure/path/to/step.csv \
  --output-dir external-evidence/step \
  --n-boot 1000 \
  --seed 20261003
```

The script validates the official column contract:

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

It reshapes the six wearable columns into an analysis-ready long table and calls `compare_ppg_reference_by_pigmentation()` with device and activity preserved as explicit strata.

Only **derived summaries** are written by the script. The source rows are never copied into the repository output path. Review the applicable DUA before sharing even derived results.

## ENCoDE

ENCoDE is designed around a substantially richer skin-tone measurement model. The official resource describes 128 acute-care patients, measurements at 16 anatomical locations, three administered visual scales, reflectance colorimetry, two reflectance spectrophotometry systems, mobile-phone imaging at permitted sites, and linked clinical data in an OMOP-style structure.

Official source: [PhysioNet ENCoDE v1.0.0](https://physionet.org/content/encode-skin-color/1.0.0/)

Public tutorial: [aiwonglab/ENCoDE_tutorial](https://github.com/aiwonglab/ENCoDE_tutorial)

### Why ENCoDE is useful here

ENCoDE is a stress test for the package's **pigmentation provenance model**, not a reason to add clinical SpO2 validation to the current tranche.

The adapter checks the official OMOP-like measurement structure and inventories skin-related measurement concepts. It is specifically looking for the coexistence of:

- objective/instrumental measurements;
- subjective scales;
- instrument identity;
- anatomical-site information;
- repeated participant-level measurements;
- missingness/availability patterns.

That mirrors the package's rule that

\[
\text{pigmentation value}
\neq
\text{measurement method}
\neq
\text{measurement site}
\neq
\text{instrument provenance}.
\]

The package therefore avoids a single ambiguous `skin_tone` field whenever richer provenance exists.

### Run ENCoDE locally

After obtaining an authorized copy containing the OMOP CSV tables:

```bash
python scripts/run_encode_pigmentation_schema_stress.py \
  --data-dir /secure/path/to/encode \
  --output-dir external-evidence/encode
```

The adapter requires at minimum:

```text
MEASUREMENT.csv
CONCEPT.csv
```

and records the presence of other expected tables such as `OBSERVATION.csv`, `DEVICE_EXPOSURE.csv`, `PROCEDURE_OCCURRENCE.csv`, `OBSERVATION_PERIOD.csv`, `PERSON.csv`, and `VISIT_OCCURRENCE.csv`.

The generated public-safe evidence is an inventory of skin-related concepts and availability; it is **not** a copy of the restricted patient table.

## Why the restricted-data result is not committed yet

Both external targets have formal access controls. STEP requires registered access and the project DUA. ENCoDE requires credentialing, required training, and its DUA. The public repository therefore contains:

1. the exact adapter code;
2. tests against contract-faithful synthetic fixtures;
3. documented expected schemas;
4. deterministic synthetic demonstration evidence;
5. no restricted source rows and no invented external result.

This is stronger than writing “validated on STEP/ENCoDE” without having legally executed those datasets.

## What will count as empirical external qualification

When the authorized datasets are available locally, the pre-release record should capture:

### STEP

- source version and DOI;
- row and participant counts observed locally;
- device/activity coverage;
- per-device/activity retention;
- bias, MAE, RMSE, CCC and Bland--Altman limits;
- Fitzpatrick-stratified descriptive summaries;
- warnings produced by the package;
- exact gpbiometricspy commit and Python environment.

### ENCoDE

- source version and DOI;
- available OMOP tables;
- number of skin-related measurement concepts detected;
- objective versus subjective concept counts;
- anatomical-site coverage;
- instrument/provenance coverage;
- missingness/availability by measurement family;
- exact gpbiometricspy commit and Python environment.

Only after those runs should the development documentation change from **adapter qualified / empirical execution pending** to **external empirical evidence executed**.

## Relationship to the synthetic example

The [synthetic worked example](examples/ppg-equity-synthetic.md) is fully reproducible inside the public repository and exists to demonstrate known mechanisms. It must never be presented as external validation.

Conversely, STEP and ENCoDE are valuable precisely because their observations are not generated by gpbiometricspy. The two evidence types answer different questions:

\[
\text{synthetic evidence} \Rightarrow \text{software behavior under known truth},
\]

\[
\text{external evidence} \Rightarrow \text{behavior on independently collected measurements}.
\]

Both are needed before the next release is frozen.
