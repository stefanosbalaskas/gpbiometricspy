# Cardiac variability source provenance

`gpbiometricspy.cardiac_provenance` is a Python-native measurement-accountability layer for distinguishing **what a cardiac variability input actually represents** before HRV/PRV feature extraction, device comparison, export, or modelling.

The method is deliberately declarative. It does not infer ECG versus PPG from column names, does not promote a vendor field to HRV because it is named `HRV`, and does not reconstruct beat-to-beat intervals from sampled heart-rate values.

## Why this layer exists

Cardiac variability workflows often collapse scientifically different objects into a single “HRV” label:

- normal-to-normal ECG intervals;
- uncleaned ECG R–R intervals;
- PPG pulse-to-pulse intervals;
- vendor-exported interval streams with unclear origin;
- precomputed device “HRV” metrics whose algorithms may be undisclosed; and
- periodic heart-rate samples from wearables or platform APIs.

Those inputs are not interchangeable. The provenance layer gives each source an explicit identity, allowed operation set, warning set, prohibited-claim set, and deterministic certificate.

## Source ontology

| `source_type` | Canonical interpretation | Variability term | Beat-level? | Main boundary |
|---|---|---:|---:|---|
| `ecg_nn_intervals` | ECG normal-to-normal intervals | HRV | yes | Beat detection and normal-beat/artifact handling should be documented. |
| `ecg_rr_intervals` | ECG R–R intervals | RR variability | yes | Raw/uncleaned RR must not be silently labelled NN-HRV. |
| `ppg_pulse_intervals` | PPG pulse-to-pulse intervals | PRV | yes | PRV is not globally interchangeable with ECG-HRV without metric-specific validation. |
| `device_intervals_unspecified` | Device-reported beat intervals of incompletely established origin | interval variability | yes | Modality/algorithm/interval semantics remain provenance limitations. |
| `device_variability_metric` | Precomputed device/vendor variability metric | vendor metric | no | A single metric cannot be reverse-engineered into beat intervals or a hidden algorithm. |
| `heart_rate_series` | Periodically sampled heart-rate series | HR-series variability | no | Resampling HR values cannot recover RR/NN/PPI beat-to-beat variability. |

## Declare provenance explicitly

```python
from gpbiometricspy.cardiac_provenance import declare_cardiac_variability_source

ECG = declare_cardiac_variability_source(
    "ecg_nn_intervals",
    source_id="chest_ecg",
    site="chest",
    interval_unit="ms",
    sampling_rate_hz=1000,
    beat_detection_disclosed=True,
    artifact_handling_disclosed=True,
)

PPG = declare_cardiac_variability_source(
    "ppg_pulse_intervals",
    source_id="finger_ppg",
    site="finger",
    interval_unit="ms",
    sampling_rate_hz=100,
    beat_detection_disclosed=True,
    artifact_handling_disclosed=True,
)
```

Beat-interval units must be supplied explicitly. The provenance layer intentionally does not assume milliseconds from typical practice.

The returned object is immutable and records:

- source identity and source type;
- modality and anatomical/site metadata;
- measurement level (`beat_interval`, `precomputed_metric`, or `sampled_heart_rate`);
- scientifically appropriate terminology;
- whether beat-level analysis is supported;
- interval units and optional source sampling rate;
- disclosure status for algorithms, beat detection, and artifact handling;
- allowed operations;
- warning-grade provenance limitations;
- prohibited scientific claims; and
- an overall `supported`, `supported_with_warnings`, or `restricted` state.

## ECG RR is not automatically NN-HRV

```python
RR = declare_cardiac_variability_source(
    "ecg_rr_intervals",
    interval_unit="ms",
    beat_detection_disclosed=True,
    artifact_handling_disclosed=False,
)
```

This source remains beat-level data, but its terminology is `RR variability`, not `HRV`, and it carries the warning:

```text
rr_not_nn_without_normal_beat_processing
```

The corresponding operation contract permits `rr_variability_features` but rejects `hrv_features`. This prevents an unprocessed RR sequence from being relabelled as a normal-to-normal series merely because an HRV function is available.

## PPG pulse intervals are PRV

PPG pulse-to-pulse intervals support PRV analysis:

```python
from gpbiometricspy.cardiac_provenance import assert_cardiac_operation_supported

assert_cardiac_operation_supported(PPG, "prv_features")
```

The same provenance object rejects `hrv_features` and carries the warning:

```text
prv_not_interchangeable_with_ecg_hrv_without_metric_validation
```

This is compatible with the existing `compare_hrv_prv_devices()` design: agreement should be demonstrated for a named derived metric and acquisition configuration rather than converted into a global “PPG equals ECG” assertion.

## Vendor/device intervals remain generic until their semantics are established

```python
DEVICE_IBI = declare_cardiac_variability_source(
    "device_intervals_unspecified",
    source_id="wearable_intervals",
    interval_unit="ms",
    modality="unknown",
    vendor="ExampleVendor",
    algorithm_disclosed=False,
)
```

This source can undergo interval QC, generic interval-variability analysis, metric-specific agreement analysis, and beat-level export. It cannot be promoted to ECG-HRV or PPG-PRV solely from a column name or vendor label.

If documentation later establishes modality and interval-generation semantics, declare a new provenance object rather than mutating the original record.

## A vendor metric is not an interval stream

```python
WATCH_RMSSD = declare_cardiac_variability_source(
    "device_variability_metric",
    source_id="watch_rmssd",
    modality="ppg",
    metric_name="RMSSD",
    vendor="ExampleVendor",
    algorithm_disclosed=False,
)
```

The object is marked `restricted` and permits only:

```text
metric_specific_agreement
report_vendor_metric
```

It explicitly prohibits:

```text
recompute_beat_level_hrv_from_metric
infer_hidden_vendor_algorithm
treat_precomputed_metric_as_intervals
```

A device metric can therefore be reported or compared with the same named metric, but it is not evidence that the analyst possesses the underlying NN/RR/PPI series.

## Sampled HR cannot be upsampled into HRV

```python
HR = declare_cardiac_variability_source(
    "heart_rate_series",
    source_id="wearable_hr_1min",
    modality="ppg",
    sampling_rate_hz=1 / 60,
)
```

This source is `restricted` to `heart_rate_summary`. It records two key warnings:

```text
sampled_hr_not_beat_intervals
resampling_cannot_recover_beat_to_beat_variability
```

Interpolating a one-minute, five-second, or one-second heart-rate stream onto a denser grid changes the numerical grid; it does not recreate the unobserved sequence of beat intervals. The provenance contract therefore blocks RR/NN/PPI reconstruction and HRV/PRV labelling from sampled HR alone.

## Deterministic provenance certificates

```python
from gpbiometricspy.cardiac_provenance import (
    create_cardiac_provenance_certificate,
    validate_cardiac_provenance_certificate,
)

certificate = create_cardiac_provenance_certificate(PPG)
assert validate_cardiac_provenance_certificate(PPG, certificate)
```

The certificate binds the complete provenance payload to a canonical SHA-256 digest. JSON key order is irrelevant; changed source identity, terminology, warnings, disclosure state, units, or allowed operations invalidate the certificate.

The certificate is a reproducibility binding, not an external digital signature. It records what the analysis declared; it does not independently verify manufacturer documentation or acquisition truth.

## Bind metric-specific agreement to provenance

Before computing agreement statistics, the two source declarations can be bound to the named metric:

```python
from gpbiometricspy.cardiac_provenance import audit_cardiac_metric_comparison
from gpbiometricspy.measurement_accountability import compare_hrv_prv_devices

comparison_contract = audit_cardiac_metric_comparison(
    ECG,
    PPG,
    metric="RMSSD",
)

agreement = compare_hrv_prv_devices(
    ecg_rmssd,
    ppg_rmssd,
    metric="RMSSD",
    reference_source=ECG.canonical_label,
    candidate_source=PPG.canonical_label,
    reference_site=ECG.site,
    candidate_site=PPG.site,
)
```

`audit_cardiac_metric_comparison()` records both provenance-certificate hashes and always returns:

```text
comparison_scope = "metric_specific_only"
global_interchangeability_supported = False
```

If a source is a device-reported metric, its declared `metric_name` must match the requested comparison metric case-insensitively.

## Relationship to existing cardiac tooling

This module does not replace:

- `audit_gazepoint_ibi_quality()` or interval-cleaning functions;
- time-, frequency-, nonlinear-, entropy-, or RQA-based HRV/PRV feature extractors;
- HeartPy, pyHRV, BioSPPy, RHRV, NeuroKit, or other interoperability bridges; or
- `compare_hrv_prv_devices()`.

Instead, it sits **before** those operations and answers a different question: whether the scientific identity of the source supports the requested analysis and terminology.

## Scientific claim boundaries

The provenance layer does not establish sensor validity, clinical equivalence, causal effects, construct validity, or physiological meaning from a variability number alone. In particular:

- `ECG-NN` supports HRV terminology only to the extent that normal-beat and artifact-processing provenance is defensible;
- `ECG-RR` remains RR variability until normal-beat processing is justified;
- `PPG` beat intervals support PRV terminology and require metric-specific evidence for ECG-HRV agreement claims;
- vendor intervals with unclear semantics remain generic intervals;
- vendor metrics remain metric-only observations; and
- sampled HR remains a sampled HR series even after interpolation, smoothing, or upsampling.

These boundaries are intentionally conservative because provenance errors cannot be repaired downstream by more sophisticated statistics.
