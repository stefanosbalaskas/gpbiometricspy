"""Experimental paired measurement validation and acquisition-rate provenance.

Agreement, perturbation responsiveness, and recovery are distinct questions.
No stress diagnosis or reference-device equivalence is inferred automatically.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_acquisition_rate_lineage(
    timestamps_s,
    *,
    device_native_rate_hz: float | None = None,
    sdk_declared_rate_hz: float | None = None,
    analysis_stream_rate_hz: float | None = None,
) -> dict:
    """Separate device capability, SDK declaration, timestamp evidence, analysis rate."""
    t = np.asarray(timestamps_s, dtype=float)
    if t.ndim != 1 or t.size < 3 or not np.isfinite(t).all():
        raise ValueError("timestamps_s must contain at least three finite timestamps")
    d = np.diff(t)
    if np.any(d <= 0):
        raise ValueError("timestamps_s must be strictly increasing")
    rates = {}
    for name, value in [
        ("device_native_rate_hz", device_native_rate_hz),
        ("sdk_declared_rate_hz", sdk_declared_rate_hz),
        ("analysis_stream_rate_hz", analysis_stream_rate_hz),
    ]:
        if value is not None and (not np.isfinite(value) or value <= 0):
            raise ValueError(f"{name} must be positive and finite when declared")
        rates[name] = None if value is None else float(value)
    rates.update({
        "observed_median_rate_hz": float(1 / np.median(d)),
        "observed_span_rate_hz": float((len(t) - 1) / (t[-1] - t[0])),
        "interval_jitter_sd_s": float(np.std(d, ddof=1)),
        "n_intervals": int(d.size),
        "interpretation": "Observed rates describe the supplied timestamps, not device hardware capability.",
    })
    return rates


def validate_biosignal_measurement(
    data: pd.DataFrame,
    *,
    reference_col: str,
    candidate_col: str,
    participant_col: str = "participant_id",
    phase_col: str = "phase",
    baseline: str = "baseline",
    perturbation: str = "perturbation",
    recovery: str = "recovery",
) -> dict:
    """Provide separate descriptive paired agreement, responsiveness, and recovery.

    Comparisons aggregate matched repeated observations at participant/phase
    level. Limits of agreement are descriptive, not confidence limits or proof
    of interchangeable instruments. Missing pairs remain counted in provenance.
    """
    required = (reference_col, candidate_col, participant_col, phase_col)
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("data must be a nonempty DataFrame")
    if len(set(required)) != len(required) or not set(required).issubset(data.columns):
        raise ValueError("measurement and grouping columns must exist and be distinct")
    if data[[participant_col, phase_col]].isna().any().any():
        raise ValueError("participant and phase identities cannot be missing")
    if len({baseline, perturbation, recovery}) != 3:
        raise ValueError("phase labels must be distinct")
    copy = data.loc[:, list(required)].copy()
    a = pd.to_numeric(copy[reference_col], errors="coerce")
    b = pd.to_numeric(copy[candidate_col], errors="coerce")
    paired = np.isfinite(a.to_numpy(dtype=float)) & np.isfinite(b.to_numpy(dtype=float))
    n_unpaired = int((~paired).sum())
    if paired.sum() < 2:
        raise ValueError("at least two finite paired observations are required")
    copy = copy.loc[paired].copy()
    copy[reference_col] = a.loc[paired].to_numpy(dtype=float)
    copy[candidate_col] = b.loc[paired].to_numpy(dtype=float)
    per = copy.groupby([participant_col, phase_col], sort=False, as_index=False)[
        [reference_col, candidate_col]
    ].mean()
    differences = (per[candidate_col] - per[reference_col]).to_numpy(dtype=float)
    bias = float(differences.mean())
    sd = float(differences.std(ddof=1)) if len(differences) > 1 else float("nan")
    agreement = {
        "n_participant_phase_pairs": len(per),
        "n_independent_participants": int(per[participant_col].nunique()),
        "paired_observations": int(paired.sum()),
        "unpaired_or_nonfinite_rows": n_unpaired,
        "mean_bias_candidate_minus_reference": bias,
        "descriptive_loa_lower": bias - 1.96 * sd,
        "descriptive_loa_upper": bias + 1.96 * sd,
        "agreement_interpretation": (
            "Participant-phase descriptive Bland-Altman limits; repeated phases "
            "are dependent and these are not inferential coverage intervals."
        ),
    }
    wide_ref = per.pivot(index=participant_col, columns=phase_col, values=reference_col)
    wide_can = per.pivot(index=participant_col, columns=phase_col, values=candidate_col)
    response_rows = []
    recovery_rows = []
    for pid in wide_ref.index:
        r, c = wide_ref.loc[pid], wide_can.loc[pid]
        if all(phase in r.index and pd.notna(r[phase]) and pd.notna(c[phase])
               for phase in (baseline, perturbation)):
            response_rows.append({
                participant_col: pid,
                "reference_change": float(r[perturbation] - r[baseline]),
                "candidate_change": float(c[perturbation] - c[baseline]),
            })
        if all(phase in r.index and pd.notna(r[phase]) and pd.notna(c[phase])
               for phase in (perturbation, recovery)):
            recovery_rows.append({
                participant_col: pid,
                "reference_recovery_change": float(r[recovery] - r[perturbation]),
                "candidate_recovery_change": float(c[recovery] - c[perturbation]),
            })
    return {
        "agreement": agreement,
        "participant_phase_means": per,
        "construct_responsiveness": pd.DataFrame(
            response_rows, columns=[participant_col, "reference_change", "candidate_change"]
        ),
        "recovery": pd.DataFrame(
            recovery_rows,
            columns=[participant_col, "reference_recovery_change", "candidate_recovery_change"],
        ),
        "claim_boundary": (
            "Descriptive agreement, construct responsiveness, and recovery only. "
            "No equivalence, device validity, or physiological-state inference."
        ),
    }
