"""Matched-anchor clock alignment and event reconstruction diagnostics.

Clock correction is not physiological event reconstruction. No hardware
synchronization guarantee is inferred from fitted timestamps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def audit_clock_and_event_alignment(
    anchors: pd.DataFrame,
    events: pd.DataFrame,
    *,
    anchor_reference_col="reference_time_s",
    anchor_device_col="device_time_s",
    event_reference_col="reference_event_time_s",
    event_device_col="device_event_time_s",
    participant_col="participant_id",
    session_col="session_id",
    fit="affine",
) -> dict:
    """Estimate clock mapping from anchors and score independent event timings.

    Requires 3 anchors and 1 independent matched event per participant-session.
    Events MUST NOT have been used as anchors. Rows are ordered matched pairs.
    Offset uses reference=device+offset; affine uses reference=a+b*device.
    """
    if fit not in {"offset", "affine"}:
        raise ValueError("fit must be offset or affine")
    group_cols = [participant_col, session_col]
    if not set(group_cols + [anchor_reference_col, anchor_device_col]).issubset(anchors):
        raise ValueError("matched clock anchors required")
    if not set(group_cols + [event_reference_col, event_device_col]).issubset(events):
        raise ValueError("independent matched event timestamps required")
    if anchors[group_cols].isna().any().any() or events[group_cols].isna().any().any():
        raise ValueError("participant/session identities must be complete")
    fit_rows, event_rows = [], []
    for key, group in anchors.groupby(group_cols, sort=False):
        relevant = events[(events[participant_col] == key[0])
                          & (events[session_col] == key[1])]
        if len(group) < 3 or len(relevant) < 1:
            raise ValueError("every session requires >=3 anchors and >=1 independent event")
        a = group[anchor_device_col].to_numpy(dtype=float)
        b = group[anchor_reference_col].to_numpy(dtype=float)
        ed = relevant[event_device_col].to_numpy(dtype=float)
        er = relevant[event_reference_col].to_numpy(dtype=float)
        if not all(np.isfinite(x).all() for x in (a, b, ed, er)):
            raise ValueError("all anchor and event timestamps must be finite")
        if np.any(np.diff(a) <= 0) or np.any(np.diff(b) <= 0):
            raise ValueError("anchor timestamps must be strictly increasing in matched order")
        if fit == "affine":
            matrix = np.column_stack((np.ones(len(a)), a))
            if np.linalg.matrix_rank(matrix) != 2:
                raise ValueError("clock anchors are degenerate")
            intercept, slope = np.linalg.lstsq(matrix, b, rcond=None)[0]
        else:
            slope = 1.0
            intercept = float(np.mean(b-a))
        residual = b - (intercept + slope*a)
        event_residual = er - (intercept + slope*ed)
        fit_rows.append({
            "participant_id": key[0], "session_id": key[1], "fit": fit,
            "clock_offset_s": float(intercept),
            "clock_slope": float(slope),
            "anchor_rms_residual_ms": float(np.sqrt(np.mean(residual**2))*1000),
            "max_abs_anchor_residual_ms": float(np.max(np.abs(residual))*1000),
            "n_anchors": len(a), "n_independent_events": len(ed),
        })
        for i, residual_value in enumerate(event_residual):
            event_rows.append({
                "participant_id": key[0], "session_id": key[1],
                "matched_event_index": i,
                "event_alignment_error_ms": float(residual_value*1000),
                "absolute_event_alignment_error_ms": float(abs(residual_value)*1000),
            })
    if set(map(tuple, events[group_cols].drop_duplicates().to_numpy())) != set(
        map(tuple, anchors[group_cols].drop_duplicates().to_numpy())
    ):
        raise ValueError("events and anchors must contain identical session identities")
    return {
        "clock_fits": pd.DataFrame(fit_rows),
        "independent_event_errors": pd.DataFrame(event_rows),
        "claim_boundary": (
            "Anchor-fitted clock coordinates and paired-event timing only; "
            "independence of event annotations and hardware synchronization "
            "require external verification."
        ),
    }
