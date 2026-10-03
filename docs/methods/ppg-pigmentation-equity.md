# PPG pigmentation & measurement-equity audit

`gpbiometricspy.ppg_equity` is an additive Python-native measurement-accountability layer for optical PPG workflows. It asks whether pigmentation was actually measured, how it was measured, whether acquisition quality or data retention varies across the observed pigmentation range, and whether reference agreement varies after keeping retention separate from accuracy.

The module does **not** treat race or ethnicity as a skin-pigmentation measurement, does not label a device "fair" or "unfair", does not automatically exclude observations because of pigmentation, and does not apply a pigmentation-based correction to a signal.

## Why the audit separates three outcomes

Optical-device performance can differ at more than one stage. A final heart-rate error metric can appear stable even when one part of the sample has more missing, rejected, or low-quality observations. The audit therefore keeps these outcomes distinct:

1. **Acquisition quality** — finite waveform proportion, missingness, flatness, robust AC amplitude, DC level, AC/DC ratio, spectral SNR, and beat-template correlation.
2. **Retention** — whether a participant/window survives the package's existing waveform-quality rules, and whether a reference-available measurement remains available in the candidate signal.
3. **Reference agreement** — bias, MAE, RMSE, Lin's concordance correlation coefficient, and Bland–Altman limits for paired measurements.

The three layers should not be collapsed into a single verdict.

## Pigmentation metadata comes first

The preferred optical representation is an objective measurement when available. `compute_skin_ita()` derives continuous Individual Typology Angle (ITA) from CIELAB `L*` and `b*` values:

\[
ITA^\circ = \arctan\left(\frac{L^* - 50}{b^*}\right)\frac{180}{\pi}.
\]

Conventional ITA categories can be added for presentation, but the continuous value remains primary for analysis.

```python
from gpbiometricspy.ppg_equity import compute_skin_ita

ita = compute_skin_ita(
    l_star=[68.4, 55.1, 39.8],
    b_star=[18.7, 20.2, 16.4],
    classify=True,
)
```

`validate_skin_pigmentation_metadata()` preserves the measurement method, site, instrument, assessor, missingness reason, raw CIELAB values when present, and whether the pigmentation-measurement site matches the PPG sensor site.

```python
from gpbiometricspy.ppg_equity import validate_skin_pigmentation_metadata

meta = validate_skin_pigmentation_metadata(
    data,
    metric="cielab",
    l_star_col="skin_L_star",
    a_star_col="skin_a_star",
    b_star_col="skin_b_star",
    method="colorimetry",
    measurement_site="pigmentation_site",
    sensor_site="sensor_site",
    instrument_manufacturer="instrument_vendor",
    instrument_model="instrument_model",
    assessor="assessor_id",
    missing_reason_col="pigmentation_missing_reason",
)
```

Supported measurement families are deliberately distinguished:

| Evidence class | Examples | Default analytical use |
| --- | --- | --- |
| Objective | ITA, CIELAB-derived ITA, melanin index | Continuous association + descriptive strata |
| Subjective | Monk, Fitzpatrick, Pantone, von Luschan | Descriptive strata; no automatic continuous model |
| Demographic proxy | race, ethnicity | **Not treated as pigmentation**; pigmentation-stratified audit is not run |

No crosswalk is performed between ITA, Monk, Fitzpatrick, race, ethnicity, or other scales.

## PPG quality and retention

`summarize_ppg_quality_by_pigmentation()` reuses the existing `assess_gazepoint_hrp_waveform_quality()` decision path for the QC status and adds PPG-specific signal-quality indicators.

```python
from gpbiometricspy.ppg_equity import summarize_ppg_quality_by_pigmentation

quality = summarize_ppg_quality_by_pigmentation(
    data,
    participant_col="participant",
    ppg_col="HRP",
    pigmentation_col="ita_degrees",
    pigmentation_metric="ita",
    time_col="time_s",
    group_cols=["condition"],
    sampling_rate_hz=60,
    n_boot=1000,
    random_state=2026,
)
```

The group-level table includes:

- finite and missing waveform proportions;
- the existing waveform-quality status and a retained/not-retained indicator based on that existing status;
- robust AC amplitude and DC level;
- AC/DC ratio;
- spectral PPG SNR using the dominant pulse-band component against remaining 0.5–5 Hz power;
- mean beat-template correlation where the waveform supports beat extraction;
- sampling-rate provenance;
- pigmentation consistency within the analysis group.

For objective pigmentation measurements, continuous slopes are accompanied by **participant-cluster bootstrap** confidence intervals. The participant, not the sample row, is the resampling unit.

For subjective scales, the module reports descriptive strata but does not silently treat the scale as an interval-valued optical measurement.

## Reference agreement and missing candidate measurements

`compare_ppg_reference_by_pigmentation()` separates the paired-error denominator from the acquisition denominator.

```python
from gpbiometricspy.ppg_equity import compare_ppg_reference_by_pigmentation

agreement = compare_ppg_reference_by_pigmentation(
    data,
    participant_col="participant",
    reference_col="ecg_hr",
    candidate_col="ppg_hr",
    pigmentation_col="ita_degrees",
    pigmentation_metric="ita",
    metric_name="heart_rate",
    device_col="device",
    condition_col="activity",
    n_boot=1000,
    random_state=2026,
)
```

The output contains:

- `agreement`: bias, MAE, RMSE, Bland–Altman limits, Lin's CCC, and retention;
- `agreement_ci`: participant-cluster bootstrap intervals for the principal metrics;
- `category_summary`: descriptive pigmentation strata, optionally within device/condition strata;
- `associations`: participant-clustered continuous slopes for signed and absolute error when the pigmentation variable is objective;
- `retention_association`: a participant-cluster bootstrap logistic association for measurement retention, reported as an odds ratio per 10 pigmentation units;
- `row_level`: analysis-ready reference availability, retention, signed error, and absolute error fields.

The retention denominator is all rows with an available reference. Missing candidate measurements are therefore not allowed to disappear from the analysis simply because an error cannot be computed for them.

## Integrated audit

`ppg_pigmentation_audit()` combines metadata validation, quality/retention analysis, optional reference agreement, provenance, warnings, and conservative reporting text.

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
    pigmentation_method="colorimetry",
    pigmentation_site="finger",
    sensor_site="finger",
    instrument_manufacturer="Vendor",
    instrument_model="Model",
    time_col="time_s",
    group_cols=["activity"],
    sampling_rate_hz=60,
    reference_col="ecg_hr",
    candidate_col="ppg_hr",
    metric_name="heart_rate",
    device_col="device",
    condition_col="activity",
    n_boot=1000,
    random_state=2026,
)
```

Main result objects are:

```text
metadata
acquisition_quality
reference_agreement
warnings
reporting_text
provenance
settings
```

If no reference/candidate pair is supplied, reference agreement is returned as `not_assessed` rather than inferred. If only race or ethnicity is supplied, the audit records that pigmentation was not measured and does not run pigmentation-stratified PPG analyses.

## Interpretation boundary

A safe interpretation is:

> PPG waveform retention decreased across the observed objective pigmentation range in this sample. Because pigmentation was observational and acquisition conditions may differ across participants, the association does not establish pigmentation or melanin as the causal source of the difference.

A second valid pattern is:

> Reference heart-rate error showed little evidence of association with the objective pigmentation measure, while usable-data retention differed across the observed range.

Avoid statements such as:

- "the device is unbiased across skin tones" based only on paired error;
- "dark skin caused poorer PPG performance" from an observational association;
- "race was used as skin tone";
- "the software corrected skin-tone bias".

The module intentionally does not generate these claims.

## Anatomical site and acquisition configuration

Pigmentation measurement and sensor placement are stored separately because skin optical properties vary by anatomical site. Where available, retain:

- pigmentation measurement site;
- PPG sensor site;
- measurement method and instrument;
- device manufacturer/model and firmware;
- wavelength or wavelength set;
- source–detector geometry;
- sampling rate;
- contact pressure or fit information;
- posture/activity;
- ambient and skin temperature;
- tattoo/hair/site context.

Unknown acquisition parameters should remain unknown rather than being inferred from device category.

## Scope boundary: PPG/HR/PRV, not clinical SpO2 validation

This tranche is designed for optical PPG waveform quality, pulse/heart-rate measurements, beat/IBI retention, and metric-specific PRV/HRV comparison. It is **not** a clinical pulse-oximeter validation module.

A future SpO2/SaO2 extension would require a dedicated clinical design with paired arterial reference measurements, desaturation-range coverage, ARMS and threshold-detection analyses, and pulse-oximeter-specific standards. Those claims are deliberately outside this module.

## External validation targets

The code is designed so external validation can be performed without redistributing restricted source data:

- **BigIdeasLab STEP** — synchronized reference ECG and wearable HR across deliberately varied Fitzpatrick types and activities; useful for reference-error × retention × device/activity checks.
- **ENCoDE** — prospective skin-tone data using multiple sites and multiple objective/subjective measurement systems; useful for stress-testing the pigmentation metadata model.
- **OpenOximetry** — relevant to a future dedicated SpO2/SaO2 extension, not used to imply clinical validation of the current PPG audit.

External datasets should remain external. Only reproducible analysis code and legally redistributable derived summaries should enter the repository.

## Methodological anchors

The tranche was motivated by the recent literature showing that optical measurement performance must be separated into signal quality, availability/retention, and final reference error; that objective pigmentation measurement is preferable to demographic proxies; and that wavelength, geometry, site, perfusion, motion, and contact conditions can interact with pigmentation.

Key anchors include:

- Singh et al. (2024), systematic review/meta-analysis of skin tone and pulse oximetry/wearable pulse-rate accuracy.
- FDA (2025), draft guidance on pulse oximeters and skin pigmentation measurement.
- ISO 80601-2-61:2026, pulse oximeter equipment standard.
- Hu et al. (2025), multi-wavelength PPG signal quality across objectively characterized skin pigmentation.
- Mulholland et al. (2025), wearable HR accuracy and data availability across objective pigmentation during exercise.
- ENCoDE (2026), multi-method and multi-site skin-tone dataset.

These sources motivate measurement accountability; they do not justify a universal claim that pigmentation causes error in every PPG device or metric.
