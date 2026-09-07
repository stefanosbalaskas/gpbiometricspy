# Measurement accountability for multimodal physiology

The `gpbiometricspy.measurement_accountability` module adds four conservative diagnostics motivated by the September 2026 methods-surveillance tranche.

## Metric-level HRV/PRV agreement

`compare_hrv_prv_devices()` computes ICC(A,1), Lin's CCC, Bland–Altman bias and 95% limits for **one derived metric at a time** while carrying source/site provenance. It deliberately does not produce a global “PPG agrees with ECG” flag.

```python
from gpbiometricspy.measurement_accountability import compare_hrv_prv_devices

agreement = compare_hrv_prv_devices(
    ecg_rmssd,
    ppg_rmssd,
    metric="RMSSD",
    reference_source="ECG-HRV",
    candidate_source="PPG-PRV",
    reference_site="chest",
    candidate_site="finger",
)
```

## Retention-first SCR responsivity

`scr_responsivity_sensitivity()` preserves the conventional response threshold and non-responder flag, but estimates a Beta-Binomial posterior response probability and sets `retain_for_modeling=True`. This supports exclusion-vs-retention sensitivity analyses rather than irreversible preprocessing deletion.

## Validation ladder

`validation_ladder()` records acquisition QC, analytical QC, construct checks, within-person evidence, and held-out-person generalization separately. A population/generalization claim cannot pass without held-out-participant evidence.

## Experimental PPG topology

`ppg_topology_features()` constructs a delay embedding and summarizes H0 persistence lifetimes through the equivalent Euclidean minimum-spanning-tree edge lengths. The output is explicitly labelled `experimental_structural_descriptor`; it is **not** a direct physiological surrogate. Any out-of-person ML use should employ participant-grouped validation.

## Methodological provenance

The implementation is independent and auditable rather than a verbatim port of publication code. The motivating primary literature includes DOI `10.1186/s12872-026-06556-4` (metric-dependent ECG/PPG agreement), DOI `10.1016/j.biopsycho.2026.109336` (SCR responsivity heterogeneity), DOI `10.3389/fnrgo.2026.1911259` (validation ladder/grouped generalization), and DOI `10.1016/j.measurement.2026.122168` (topology-aware PPG morphology).
