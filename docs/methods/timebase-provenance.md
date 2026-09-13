# Timebase provenance and multimodal alignment certification

`gpbiometricspy.timebase_provenance` is a Python-native methodological extension for making timing evidence explicit before multimodal fusion. It sits **outside the frozen 406-function `gpbiometrics 2.0.0` parity contract**.

The module separates three questions that are often collapsed in analysis code:

1. **What timing information was actually recorded?**
2. **How were two clocks related and corrected?**
3. **Is the resulting alignment sufficiently supported for the downstream tolerance being claimed?**

It does not make a stream trustworthy merely because a nominal sampling rate was configured, and it does not treat successful affine clock correction as proof of sub-millisecond synchronization accuracy.

## 1. Audit the recorded timebase

```python
import pandas as pd

from gpbiometricspy.timebase_provenance import audit_gazepoint_timebase

eda = pd.DataFrame({
    "time_s": [0.000, 0.052, 0.104, 0.156, 0.208],
    "EDA": [2.01, 2.02, 2.03, 2.02, 2.04],
})

audit = audit_gazepoint_timebase(
    eda,
    time_col="time_s",
    time_unit="seconds",
    nominal_rate_hz=20,
    clock_id="eda_device_clock",
)

print(audit.status)
print(audit.observed_median_rate_hz)
print(audit.interval_jitter_sd_s)
print(audit.issues)
```

The audit keeps nominal and timestamp-derived quantities separate. Its principal fields include:

| Field | Meaning |
|---|---|
| `nominal_rate_hz` | Declared/configured rate supplied by the analyst. |
| `observed_median_rate_hz` | Reciprocal of the median positive recorded interval. |
| `observed_mean_rate_hz` | Reciprocal of the mean positive recorded interval. |
| `observed_span_rate_hz` | Finite sample intervals divided by the recorded start-to-end span. |
| `observed_rate_sd_hz` | SD of instantaneous rates `1 / Δt`. |
| `interval_jitter_sd_s` | SD of positive inter-sample intervals. |
| `interval_jitter_mad_s` | Median absolute deviation of positive inter-sample intervals around their median. |
| `interval_cv` | Inter-sample interval SD divided by the mean interval. |
| `n_duplicate_timestamps` | Number of repeated finite timestamp values beyond their first occurrence. |
| `n_backward_timestamps` | Number of negative timestamp steps. |
| `n_large_gaps` | Positive intervals exceeding `gap_factor × median_interval_s`. |
| `estimated_missing_samples` | Approximate missing samples implied by unusually long intervals. |
| `nominal_rate_error_fraction` | Relative difference between timestamp-derived median rate and the nominal rate. |
| `nominal_rate_deviation_ppm` | The same nominal-rate departure expressed in parts per million. This is **not** an inter-device clock-drift estimate. |
| `rate_evidence` | Whether rate evidence comes from recorded timestamps or from a counter scaled by a supplied nominal rate. |
| `time_sha256` | Deterministic SHA-256 over the normalized timestamp sequence. |

### Counters are not timestamps

A sample counter such as `CNT` can reveal missing or repeated counter steps, but it cannot independently establish elapsed physical time or device-clock stability. Therefore:

```python
audit = audit_gazepoint_timebase(
    frame,
    time_col="CNT",
    time_unit="samples",
    nominal_rate_hz=60,
    clock_id="gazepoint_counter",
)
```

is recorded as:

```text
rate_evidence = "counter_scaled_by_nominal_rate"
issue         = "counter_scaled_timebase"
status        = "warning"
```

The reported rate is then a counter-scaled quantity, not an empirical timestamp-derived sampling rate. A multimodal certificate will not silently promote this warning to clean timing evidence.

### Unit inference is provenance, too

Explicit units are preferred. `time_unit="auto"` can use recognized column names such as `time_s` or `TIME_MS`. If units must instead be inferred from interval scale, the audit records `unit_source="interval_heuristic"` and emits `heuristic_time_unit`.

That warning is deliberate: a numerical sequence such as `0, 10, 20` is not intrinsically seconds or milliseconds without metadata.

## 2. Create an immutable timebase certificate

```python
from gpbiometricspy.timebase_provenance import (
    create_gazepoint_timebase_certificate,
    validate_gazepoint_timebase_certificate,
)

certificate = create_gazepoint_timebase_certificate(audit)
assert validate_gazepoint_timebase_certificate(audit, certificate)
```

The certificate contains the complete audit payload plus a canonical SHA-256 digest. JSON key order does not affect validation. Any changed metric, clock identifier, warning state, timestamp hash, or threshold causes validation to fail.

The certificate is a **reproducibility binding**, not a digital signature or external trust assertion. It proves consistency between the supplied audit object and certificate payload; it does not prove that the original sensor, file, or study metadata were truthful.

## 3. Estimate the mapping between clocks

Clock alignment requires matched anchors: for example corresponding TTL transitions or event markers observed on both devices.

```python
from gpbiometricspy.timebase_provenance import fit_gazepoint_clock_alignment

alignment = fit_gazepoint_clock_alignment(
    reference=[0.0, 10.0, 20.0, 30.0],
    target=[0.250, 10.260, 20.270, 30.280],
    reference_time_unit="seconds",
    target_time_unit="seconds",
    reference_clock="master_clock",
    target_clock="ppg_clock",
    method="affine",
)
```

For the affine method, the fitted model is

```text
target_time = intercept + slope × reference_time
```

and target timestamps are transformed onto the reference clock as

```text
reference_time = (target_time - intercept) / slope
```

The alignment object records:

- intercept;
- slope;
- inter-device `drift_ppm = (slope - 1) × 10^6`;
- residual mean, SD and maximum absolute residual;
- R² when defined;
- matched-anchor count;
- deterministic hashes of both anchor sequences;
- input units and how those units were established;
- `anchor_match_method="row_order"`;
- estimator (`ordinary_least_squares` or `median_offset`).

### Anchor correspondence is a scientific assumption

Version 1 fits anchors in the order supplied. It does **not** infer whether two events truly correspond. The two supplied anchor sequences must have equal length and be strictly increasing in both clocks. Event-ID matching, protocol validation, or another justified matching procedure should therefore occur before `fit_gazepoint_clock_alignment()` is called.

The alignment residual describes agreement of the supplied matched anchors with the selected mapping. It is not, by itself, a hardware synchronization-accuracy specification.

## 4. Apply the clock correction

```python
from gpbiometricspy.timebase_provenance import apply_gazepoint_clock_alignment

ppg_time_on_master = apply_gazepoint_clock_alignment(
    target_times=ppg["time_s"],
    alignment=alignment,
    time_unit="seconds",
)
```

Clock correction and signal resampling are intentionally separate operations. This function changes the time coordinate only. It does not interpolate, decimate, upsample, filter, or otherwise alter physiological values.

## 5. Certify multimodal alignment

Audit both source streams using the same clock identities supplied to the alignment model:

```python
from gpbiometricspy.timebase_provenance import (
    audit_gazepoint_timebase,
    create_gazepoint_multimodal_alignment_certificate,
)

master_audit = audit_gazepoint_timebase(
    master,
    time_col="time_s",
    time_unit="seconds",
    clock_id="master_clock",
)

ppg_audit = audit_gazepoint_timebase(
    ppg,
    time_col="time_s",
    time_unit="seconds",
    clock_id="ppg_clock",
)

alignment_certificate = create_gazepoint_multimodal_alignment_certificate(
    master_audit,
    ppg_audit,
    alignment,
    tolerance_s=0.010,
    resampling_operation="none",
)
```

Certification is **fail-closed** when:

- either timebase audit has status `fail`;
- audit warnings exist but were not explicitly accepted;
- clock identities do not agree across the audits and alignment object;
- the maximum anchor residual exceeds `tolerance_s`; or
- the corrected streams have no positive temporal overlap.

If a warning is scientifically acceptable for a particular analysis, it must be made explicit:

```python
alignment_certificate = create_gazepoint_multimodal_alignment_certificate(
    master_audit,
    ppg_audit,
    alignment,
    tolerance_s=0.010,
    allow_timebase_warnings=True,
    resampling_operation="linear interpolation to 20 Hz after clock correction",
)
```

The resulting payload is marked `certified_with_warnings` and retains the warning names. Acceptance does not delete their provenance.

## 6. Require a valid certificate before fusion

```python
from gpbiometricspy.timebase_provenance import assert_gazepoint_multimodal_fusion_ready

assert_gazepoint_multimodal_fusion_ready(
    master_audit,
    ppg_audit,
    alignment,
    alignment_certificate,
    max_tolerance_s=0.010,
)
```

`max_tolerance_s` lets a downstream workflow impose a stricter tolerance than the certificate originally carried. A certificate generated at 20 ms cannot be reused to satisfy a downstream 10 ms requirement.

The alignment certificate binds:

```text
reference timebase certificate SHA-256
    + target timebase certificate SHA-256
    + clock mapping and anchor hashes
    + residual tolerance
    + corrected temporal overlap
    + explicit warning acceptance
    + recorded resampling operation
```

This makes timing lineage inspectable rather than implicit.

## Status semantics

### `pass`

No configured audit warning or failure condition was detected.

### `warning`

The stream remains characterizable, but one or more conditions require explicit interpretation, such as:

- non-finite timestamps;
- duplicate timestamps;
- large sampling gaps;
- high interval jitter;
- nominal-rate mismatch;
- heuristic time-unit inference; or
- a counter-derived rather than timestamp-observed timebase.

Counter-scaled anchor units used in the clock fit are also retained as alignment warnings and require explicit acceptance.

### `fail`

The timebase is not eligible for multimodal certification, including cases with insufficient finite timestamps, no positive time intervals, or backward timestamp steps.

## Relationship to the existing API

This module does not replace the established parity functions:

- `detect_gazepoint_biometric_timebase()` remains the lightweight schema/timebase detector;
- `assess_gazepoint_sampling_irregularity()` remains the parity-level irregularity summary;
- `diagnose_gazepoint_sync_drift()` remains the parity-level drift diagnostic;
- MNE/EEG/LSL bridges retain their specialized synchronization workflows.

The Python-native layer adds a stricter, cross-workflow **measurement-lineage contract** over those concepts: deterministic hashes, explicit clock identity, distinction between timestamp and counter evidence, explicit correction equations, residual-tolerance gates, overlap accounting, warning retention, and certificate validation.

## Scientific boundaries

A valid certificate supports a narrow claim: the supplied timebases and matched anchors satisfy the recorded audit and alignment conditions under the stated tolerance and transformation history.

It does **not** establish that:

- the device manufacturer's nominal sampling specification was achieved simply because it was configured;
- affine correction recovers unobserved within-anchor timing error;
- clock agreement proves sensor validity;
- a small anchor residual proves sub-millisecond hardware synchronization;
- interpolation reconstructs physiological information that was never sampled;
- two modalities measure the same biological process; or
- temporal alignment establishes causal ordering beyond the accuracy supported by the acquisition and synchronization design.

The intended reporting pattern is therefore two-part: report the **nominal acquisition specification** and the **timestamp-derived timing characteristics actually observed**.

## Methodological motivation

Recent multimodal data releases increasingly expose observed sampling characteristics, explicit master timelines, minimally transformed streams, and machine-readable quality metadata rather than relying only on nominal device rates. A useful contemporary example is Tomar et al. (2026), *Synchronized Multimodal Characterization of Physiological, Environmental, and Behavioral Responses During Controlled Indoor Thermal Exposure*, *Scientific Data*, DOI: [10.1038/s41597-026-08275-z](https://doi.org/10.1038/s41597-026-08275-z).

That literature motivates the provenance model here; it does not turn the cited dataset, or this software, into a universal timing ground truth.
