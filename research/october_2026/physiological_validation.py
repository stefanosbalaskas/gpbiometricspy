"""Research-only paired preprocessing and physiological baseline audits.

No claim of physiological equivalence or validated stabilization threshold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def baseline_stability_audit(
    frame: pd.DataFrame,
    *,
    participant_col: str = "participant_id",
    time_col: str = "time_s",
    value_col: str = "value",
    minimum_valid: int = 4,
) -> pd.DataFrame:
    """Describe temporal stability; no universally valid pass/fail threshold.

    Uses centered OLS time slope, early-minus-late mean and coefficient of
    variation of valid values within each participant. Missingness is counted
    before dropping invalid values. Each group must have strictly increasing
    timestamps in original recording order.
    """
    required = {participant_col, time_col, value_col}
    if not required.issubset(frame.columns):
        raise ValueError("required participant, time, or value columns missing")
    if minimum_valid < 4:
        raise ValueError("minimum_valid must be at least four")
    rows = []
    for participant, group in frame.groupby(participant_col, sort=False, dropna=False):
        if pd.isna(participant):
            raise ValueError("participant identity cannot be missing")
        t = pd.to_numeric(group[time_col], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(group[value_col], errors="coerce").to_numpy(dtype=float)
        if not np.all(np.isfinite(t)) or np.any(np.diff(t) <= 0):
            raise ValueError("timestamps must be finite and strictly increasing")
        valid = np.isfinite(y)
        n = int(valid.sum())
        if n < minimum_valid:
            raise ValueError("insufficient valid baseline observations")
        v = y[valid]
        tv = t[valid]
        centered = tv - tv.mean()
        slope = float(np.dot(centered, v - v.mean()) / np.dot(centered, centered))
        split = n // 2
        early_late = float(v[:split].mean() - v[split:].mean())
        half_sd = float(np.std(v, ddof=1))
        rows.append({
            "participant_id": participant,
            "usable_n": n,
            "missing_fraction": float(1 - n / len(y)),
            "duration_s": float(t[-1] - t[0]),
            "baseline_mean": float(v.mean()),
            "slope_per_s": slope,
            "early_minus_late": early_late,
            "baseline_sd": half_sd,
            "stability_decision": "not_inferred",
        })
    if not rows:
        raise ValueError("empty baseline data")
    return pd.DataFrame(rows)


def preprocessing_to_inference_audit(
    frame: pd.DataFrame,
    *,
    participant_col: str = "participant_id",
    reference_col: str = "reference",
    raw_col: str = "raw",
    processed_col: str = "processed",
    raw_event_col: str = "raw_event",
    processed_event_col: str = "processed_event",
    reference_event_col: str = "reference_event",
    raw_effect_col: str = "raw_effect",
    processed_effect_col: str = "processed_effect",
    bootstrap_replicates: int = 499,
    seed: int = 1,
) -> dict:
    """Compare matched waveform, event and participant-level inferential effects.

    Event columns are binary reference labels on a COMMON sample grid. This
    is sample/event-label agreement, not onset-latency or SCR morphology
    validation. Effect columns must contain separately estimated participant-
    level quantities and cannot be fabricated from waveform error.
    """
    required = {participant_col, reference_col, raw_col, processed_col,
                raw_event_col, processed_event_col, reference_event_col,
                raw_effect_col, processed_effect_col}
    if not required.issubset(frame.columns):
        raise ValueError("all three validation-layer columns are required")
    if bootstrap_replicates < 99:
        raise ValueError("at least 99 participant bootstrap replicates required")
    if frame[participant_col].isna().any():
        raise ValueError("participant identities cannot be missing")
    nums = frame[list(required - {participant_col})].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(nums.to_numpy(dtype=float)).all():
        raise ValueError("matched inputs must be completely finite")
    for col in [raw_event_col, processed_event_col, reference_event_col]:
        if not nums[col].isin([0, 1]).all():
            raise ValueError("event indicators must be zero or one")
    grouped = []
    for ident, idx in frame.groupby(participant_col, sort=False).indices.items():
        d = nums.iloc[idx]
        grouped.append({
            "participant_id": ident,
            "waveform_raw_mae": float(np.abs(d[raw_col] - d[reference_col]).mean()),
            "waveform_processed_mae": float(np.abs(d[processed_col] - d[reference_col]).mean()),
            "event_raw_error": float((d[raw_event_col] != d[reference_event_col]).mean()),
            "event_processed_error": float((d[processed_event_col] != d[reference_event_col]).mean()),
            "effect_raw": float(d[raw_effect_col].mean()),
            "effect_processed": float(d[processed_effect_col].mean()),
        })
    units = pd.DataFrame(grouped)
    if len(units) < 2:
        raise ValueError("at least two independent participants required")
    units["waveform_delta_mae"] = units.waveform_processed_mae - units.waveform_raw_mae
    units["event_delta_error"] = units.event_processed_error - units.event_raw_error
    units["effect_delta"] = units.effect_processed - units.effect_raw
    rng = np.random.default_rng(seed)
    metrics = ("waveform_delta_mae", "event_delta_error", "effect_delta")
    summary = []
    for metric in metrics:
        values = units[metric].to_numpy(dtype=float)
        draws = values[rng.integers(0, len(values), size=(bootstrap_replicates, len(values)))].mean(axis=1)
        lo, hi = np.quantile(draws, [0.025, 0.975])
        summary.append({"metric": metric, "mean_delta": float(values.mean()),
                        "bootstrap_lower": float(lo), "bootstrap_upper": float(hi)})
    return {
        "participant_results": units,
        "summary": pd.DataFrame(summary),
        "bootstrap_unit": "participant",
        "claim_boundary": "Descriptive matched comparisons; no superiority, equivalence or causal claim.",
    }


def baseline_window_sensitivity(
    frame: pd.DataFrame,
    windows,
    *,
    participant_col: str = "participant_id",
    time_col: str = "time_s",
    value_col: str = "value",
    minimum_valid: int = 4,
) -> pd.DataFrame:
    """Retain *all* prespecified baseline windows, including failures.

    Absolute time windows are closed [start,end]. This function deliberately
    does not select the best-looking baseline. Failed windows are recorded,
    not removed from the analysis plan; no cardiovascular/EDA universal
    stabilization time is implied.
    """
    if not windows:
        raise ValueError("at least one prespecified window is required")
    required = [participant_col, time_col, value_col]
    if not set(required).issubset(frame):
        raise ValueError("baseline observation columns missing")
    if frame.empty or frame[participant_col].isna().any():
        raise ValueError("nonempty identified participant observations required")
    result = []
    for index, candidate in enumerate(windows):
        if len(candidate) != 2:
            raise ValueError("window requires a start and end")
        start, end = map(float, candidate)
        if not np.isfinite([start, end]).all() or start >= end:
            raise ValueError("baseline window start must precede end")
        for person, samples in frame.groupby(participant_col, sort=False):
            times = pd.to_numeric(samples[time_col], errors="coerce").to_numpy(dtype=float)
            values = pd.to_numeric(samples[value_col], errors="coerce").to_numpy(dtype=float)
            if not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
                raise ValueError("timestamps must be finite and strictly increasing")
            selected = (times >= start) & (times <= end)
            sub = samples.loc[selected, required]
            n_valid = int(np.isfinite(values[selected]).sum())
            entry = {
                "participant_id": person, "window_index": index,
                "window_start_s": start, "window_end_s": end,
                "selected_n": int(selected.sum()), "valid_n": n_valid,
                "status": "evaluable" if n_valid >= minimum_valid else "insufficient_valid",
                "mean_value": np.nan, "slope_per_s": np.nan,
                "early_minus_late": np.nan,
            }
            if n_valid >= minimum_valid:
                estimate = baseline_stability_audit(
                    sub, participant_col=participant_col,
                    time_col=time_col, value_col=value_col,
                    minimum_valid=minimum_valid,
                ).iloc[0]
                entry["mean_value"] = float(estimate.baseline_mean)
                entry["slope_per_s"] = float(estimate.slope_per_s)
                entry["early_minus_late"] = float(estimate.early_minus_late)
            result.append(entry)
    return pd.DataFrame(result)
