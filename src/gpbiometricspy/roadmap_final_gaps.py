from __future__ import annotations

from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd

from ._helpers import as_list, ensure_df, require_cols, r_sd
from ._types import ParityNotImplementedError


def _resolve_col(data: pd.DataFrame, supplied, candidates, description: str, required: bool = True):
    if supplied is not None:
        if not isinstance(supplied, str) or not supplied.strip():
            raise ValueError(f"`{description}_col` must be one non-empty character value.")
        if supplied not in data.columns:
            raise ValueError(f"Selected {description} column was not found: {supplied}.")
        return supplied
    lower = {str(c).lower(): c for c in data.columns}
    for candidate in candidates:
        hit = lower.get(str(candidate).lower())
        if hit is not None:
            return hit
    if required:
        raise ValueError(f"Could not identify a {description} column. Supply it explicitly.")
    return None


def _resolve_time_unit(values, column: str, requested: str = "auto") -> str:
    allowed = {"auto", "seconds", "milliseconds", "samples"}
    if requested not in allowed:
        raise ValueError(f"`time_unit` must be one of {sorted(allowed)}.")
    if requested != "auto":
        return requested
    lower = str(column).lower()
    if any(s in lower for s in ("cnt", "sample", "index")):
        return "samples"
    if any(s in lower for s in ("mstimer", "millisecond", "msec")) or lower.endswith("_ms") or lower.startswith("ms_"):
        return "milliseconds"
    if any(s in lower for s in ("time_s", "timestamp_s", "onset_s", "start_s", "end_s", "second")):
        return "seconds"
    x = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    finite = np.sort(np.unique(x[np.isfinite(x)]))
    delta = np.diff(finite)
    delta = delta[np.isfinite(delta) & (delta > 0)]
    if not delta.size:
        raise ValueError("Could not infer the time unit; supply it explicitly.")
    med = float(np.median(delta))
    if med < 1:
        return "seconds"
    if med >= 5:
        return "milliseconds"
    raise ValueError("The time unit is ambiguous; supply it explicitly.")


def _resolve_duration_unit(values, column: str, requested: str = "auto") -> str:
    allowed = {"auto", "seconds", "milliseconds", "samples"}
    if requested not in allowed:
        raise ValueError(f"`duration_unit` must be one of {sorted(allowed)}.")
    if requested != "auto":
        return requested
    lower = str(column).lower()
    if "sample" in lower or "count" in lower:
        return "samples"
    if any(s in lower for s in ("millisecond", "msec", "fpogd")) or lower.endswith("_ms") or lower.startswith("ms_"):
        return "milliseconds"
    if "duration_s" in lower or "second" in lower or lower.endswith("_sec") or lower.startswith("sec_"):
        return "seconds"
    x = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    finite = x[np.isfinite(x) & (x >= 0)]
    if not finite.size:
        raise ValueError("Could not infer the duration unit; supply it explicitly.")
    return "milliseconds" if float(np.median(finite)) > 10 else "seconds"


def _to_seconds(values, unit: str, sampling_rate_hz=None):
    x = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    if unit == "seconds":
        return x
    if unit == "milliseconds":
        return x / 1000.0
    if unit == "samples":
        if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or float(sampling_rate_hz) <= 0:
            raise ValueError("`sampling_rate_hz` must be one positive finite number.")
        return x / float(sampling_rate_hz)
    raise ValueError(f"Unsupported unit: {unit}")


def _valid_values(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.fillna(False).to_numpy(bool)
    if pd.api.types.is_numeric_dtype(series.dtype):
        x = pd.to_numeric(series, errors="coerce").to_numpy(float)
        return np.isfinite(x) & (x > 0)
    text = series.astype("string").str.strip().str.lower()
    return text.isin(["1", "true", "valid", "yes", "y", "on"]).fillna(False).to_numpy(bool)


def _coordinate_system(x, y, requested, width=None, height=None):
    if requested not in {"auto", "normalized", "pixels", "degrees"}:
        raise ValueError("`coordinate_system` must be auto, normalized, pixels, or degrees.")
    if requested != "auto":
        return requested
    finite = np.isfinite(x) & np.isfinite(y)
    if not finite.any():
        return "normalized"
    xx, yy = x[finite], y[finite]
    plausible = np.all((xx >= -0.5) & (xx <= 1.5) & (yy >= -0.5) & (yy <= 1.5))
    within = np.mean((xx >= 0) & (xx <= 1) & (yy >= 0) & (yy <= 1))
    if plausible or within >= 0.90:
        return "normalized"
    if width is not None or height is not None or np.max(np.abs(np.r_[xx, yy])) > 2:
        return "pixels"
    return "degrees"


def _position_groups(df: pd.DataFrame, group_cols):
    cols = as_list(group_cols)
    if not cols:
        return [("all", np.arange(len(df), dtype=int))]
    require_cols(df, cols, "group_cols")
    work = df.reset_index(drop=True)
    groups = []
    grouper = cols[0] if len(cols) == 1 else cols
    for key, block in work.groupby(grouper, sort=False, dropna=False):
        groups.append((key, block.index.to_numpy(int)))
    return groups


def validate_gazepoint_gaze(
    data,
    time_col=None,
    x_col=None,
    y_col=None,
    validity_cols=None,
    group_cols=None,
    coordinate_system="auto",
    screen_width_px=None,
    screen_height_px=None,
    time_unit="auto",
    sampling_rate_hz=None,
    expected_sampling_rate_hz=None,
    sampling_tolerance=0.20,
    missing_threshold=0.20,
    gap_multiplier=3,
):
    df = ensure_df(data).reset_index(drop=True).copy()
    if not np.isfinite(sampling_tolerance) or sampling_tolerance < 0:
        raise ValueError("`sampling_tolerance` must be one non-negative finite number.")
    if not np.isfinite(missing_threshold) or not 0 <= missing_threshold <= 1:
        raise ValueError("`missing_threshold` must be between 0 and 1.")
    if not np.isfinite(gap_multiplier) or gap_multiplier <= 0:
        raise ValueError("`gap_multiplier` must be one positive finite number.")

    time_col = _resolve_col(df, time_col, ["time_s", "time_ms", "time", "timestamp", "MSTIMER", "TIME", "CNT"], "time", True)
    x_col = _resolve_col(df, x_col, ["gaze_x", "x", "FPOGX", "BPOGX", "LPOGX", "RPOGX", "POGX"], "horizontal gaze coordinate", True)
    y_col = _resolve_col(df, y_col, ["gaze_y", "y", "FPOGY", "BPOGY", "LPOGY", "RPOGY", "POGY"], "vertical gaze coordinate", True)
    groups = as_list(group_cols)
    require_cols(df, groups, "group_cols")

    if validity_cols is None:
        candidates = {x.lower() for x in ["valid", "validity", "gaze_valid", "FPOGV", "BPOGV", "LPOGV", "RPOGV"]}
        validity_cols = [c for c in df.columns if str(c).lower() in candidates]
    else:
        validity_cols = as_list(validity_cols)
        require_cols(df, validity_cols, "validity_cols")

    raw_time = pd.to_numeric(df[time_col], errors="coerce").to_numpy(float)
    gaze_x = pd.to_numeric(df[x_col], errors="coerce").to_numpy(float)
    gaze_y = pd.to_numeric(df[y_col], errors="coerce").to_numpy(float)
    if not np.isfinite(raw_time).any():
        raise ValueError("The selected time column contains no finite numeric values.")
    resolved_time_unit = _resolve_time_unit(raw_time, time_col, time_unit)
    time_s = _to_seconds(raw_time, resolved_time_unit, sampling_rate_hz)
    if expected_sampling_rate_hz is not None and (not np.isfinite(expected_sampling_rate_hz) or expected_sampling_rate_hz <= 0):
        raise ValueError("`expected_sampling_rate_hz` must be one positive finite number.")
    for val, name in [(screen_width_px, "screen_width_px"), (screen_height_px, "screen_height_px")]:
        if val is not None and (not np.isfinite(val) or val <= 0):
            raise ValueError(f"`{name}` must be one positive finite number.")

    finite_xy = np.isfinite(gaze_x) & np.isfinite(gaze_y)
    resolved_coordinate = _coordinate_system(gaze_x, gaze_y, coordinate_system, screen_width_px, screen_height_px)
    invalid_by_validity = np.zeros(len(df), dtype=bool)
    if validity_cols:
        vals = np.column_stack([_valid_values(df[c]) for c in validity_cols])
        invalid_by_validity = vals.sum(axis=1) < vals.shape[1]
    missing_xy = ~finite_xy
    gaze_invalid = missing_xy | invalid_by_validity

    out_of_range = np.zeros(len(df), dtype=bool)
    range_assessed = True
    if resolved_coordinate == "normalized":
        out_of_range = finite_xy & ((gaze_x < 0) | (gaze_x > 1) | (gaze_y < 0) | (gaze_y > 1))
    elif resolved_coordinate == "pixels":
        if screen_width_px is None or screen_height_px is None:
            range_assessed = False
        else:
            out_of_range = finite_xy & ((gaze_x < 0) | (gaze_x > screen_width_px) | (gaze_y < 0) | (gaze_y > screen_height_px))
    else:
        range_assessed = False

    flags = df.copy()
    flags[".gaze_time_s"] = time_s
    flags[".gaze_missing_xy"] = missing_xy
    flags[".gaze_invalid_validity"] = invalid_by_validity
    flags[".gaze_invalid"] = gaze_invalid
    flags[".gaze_out_of_range"] = out_of_range
    flags[".gaze_duplicate_time"] = False
    flags[".gaze_nonmonotonic_time"] = False
    flags[".gaze_large_gap_after"] = False

    group_rows = []
    for _, idx in _position_groups(df, groups):
        local_t = time_s[idx]
        dt = np.diff(local_t)
        duplicate = np.r_[False, np.isfinite(dt) & (dt == 0)]
        nonmono = np.r_[False, np.isfinite(dt) & (dt < 0)]
        positive = dt[np.isfinite(dt) & (dt > 0)]
        med_interval = float(np.median(positive)) if positive.size else np.nan
        inferred_rate = 1.0 / med_interval if np.isfinite(med_interval) and med_interval > 0 else np.nan
        ref_interval = 1.0 / expected_sampling_rate_hz if expected_sampling_rate_hz is not None else med_interval
        large = np.zeros(len(idx), dtype=bool)
        if dt.size and np.isfinite(ref_interval) and ref_interval > 0:
            large[: len(dt)] = np.isfinite(dt) & (dt > gap_multiplier * ref_interval)
        flags.loc[idx, ".gaze_duplicate_time"] = duplicate
        flags.loc[idx, ".gaze_nonmonotonic_time"] = nonmono
        flags.loc[idx, ".gaze_large_gap_after"] = large
        dev = abs(inferred_rate - expected_sampling_rate_hz) / expected_sampling_rate_hz if expected_sampling_rate_hz is not None and np.isfinite(inferred_rate) else np.nan
        row = {c: df.loc[idx[0], c] for c in groups}
        if not groups:
            row[".group"] = "all"
        local_invalid = gaze_invalid[idx]
        local_out = out_of_range[idx]
        row.update(
            n_samples=len(idx),
            finite_time_count=int(np.isfinite(local_t).sum()),
            missing_gaze_count=int(local_invalid.sum()),
            missing_gaze_rate=float(local_invalid.mean()),
            out_of_range_count=int(local_out.sum()),
            out_of_range_rate=float(local_out.mean()),
            duplicate_time_count=int(duplicate.sum()),
            nonmonotonic_time_count=int(nonmono.sum()),
            large_gap_count=int(large.sum()),
            median_interval_s=med_interval,
            inferred_sampling_rate_hz=inferred_rate,
            relative_sampling_rate_deviation=dev,
        )
        group_rows.append(row)
    group_table = pd.DataFrame(group_rows)

    missing_rate = float(gaze_invalid.mean())
    out_rate = float(out_of_range.mean())
    dup = int(flags[".gaze_duplicate_time"].sum())
    nonmono = int(flags[".gaze_nonmonotonic_time"].sum())
    gaps = int(flags[".gaze_large_gap_after"].sum())
    rates = pd.to_numeric(group_table.get("inferred_sampling_rate_hz"), errors="coerce").to_numpy(float)
    rates = rates[np.isfinite(rates)]
    median_rate = float(np.median(rates)) if rates.size else np.nan
    overall_dev = abs(median_rate - expected_sampling_rate_hz) / expected_sampling_rate_hz if expected_sampling_rate_hz is not None and np.isfinite(median_rate) else np.nan

    checks = pd.DataFrame([
        {"check": "finite_time", "status": "pass" if np.isfinite(time_s).all() else "fail", "value": int(np.isfinite(time_s).sum()), "threshold": len(df), "detail": "Finite timestamp count versus total rows."},
        {"check": "monotonic_time", "status": "pass" if nonmono == 0 else "fail", "value": nonmono, "threshold": 0, "detail": "Negative within-group time differences."},
        {"check": "duplicate_time", "status": "pass" if dup == 0 else "warn", "value": dup, "threshold": 0, "detail": "Repeated within-group timestamps."},
        {"check": "missing_gaze", "status": "pass" if missing_rate <= missing_threshold else "warn", "value": missing_rate, "threshold": missing_threshold, "detail": "Rows with missing coordinates or invalid validity flags."},
        {"check": "coordinate_range", "status": "not_assessed" if not range_assessed else ("pass" if out_rate == 0 else "warn"), "value": out_rate if range_assessed else np.nan, "threshold": 0, "detail": f"Resolved coordinate system: {resolved_coordinate}."},
        {"check": "sampling_rate", "status": "not_assessed" if expected_sampling_rate_hz is None else ("pass" if np.isfinite(overall_dev) and overall_dev <= sampling_tolerance else "warn"), "value": overall_dev, "threshold": sampling_tolerance, "detail": "Relative deviation from the expected sampling rate."},
        {"check": "large_time_gaps", "status": "pass" if gaps == 0 else "warn", "value": gaps, "threshold": 0, "detail": f"Gap threshold multiplier: {gap_multiplier}."},
    ])
    rank = {"not_assessed": 0, "pass": 1, "warn": 2, "fail": 3}
    overall = max(checks["status"], key=lambda x: rank[x])
    summary = pd.DataFrame([{
        "status": overall,
        "n_samples": len(df),
        "n_groups": len(group_rows),
        "missing_gaze_rate": missing_rate,
        "out_of_range_rate": out_rate if range_assessed else np.nan,
        "duplicate_time_count": dup,
        "nonmonotonic_time_count": nonmono,
        "large_gap_count": gaps,
        "median_inferred_sampling_rate_hz": median_rate,
        "coordinate_system": resolved_coordinate,
    }])
    return {
        "summary": summary,
        "checks": checks,
        "groups": group_table,
        "data": flags,
        "columns": {"time": time_col, "x": x_col, "y": y_col, "validity": validity_cols, "groups": groups},
        "settings": {
            "coordinate_system": resolved_coordinate,
            "range_assessed": range_assessed,
            "screen_width_px": screen_width_px,
            "screen_height_px": screen_height_px,
            "time_unit": resolved_time_unit,
            "sampling_rate_hz": sampling_rate_hz,
            "expected_sampling_rate_hz": expected_sampling_rate_hz,
            "sampling_tolerance": sampling_tolerance,
            "missing_threshold": missing_threshold,
            "gap_multiplier": gap_multiplier,
        },
        "class": ["gazepoint_gaze_validation", "list"],
    }


def summarise_gazepoint_fixations_by_aoi(
    fixations,
    aoi_col=None,
    participant_col=None,
    trial_col=None,
    group_cols=None,
    start_col=None,
    end_col=None,
    duration_col=None,
    event_onset_col=None,
    time_unit="auto",
    duration_unit="auto",
    sampling_rate_hz=None,
    include_unassigned=False,
    unassigned_label="UNASSIGNED",
):
    df = ensure_df(fixations, "fixations").reset_index(drop=True).copy()
    if not isinstance(include_unassigned, (bool, np.bool_)):
        raise TypeError("`include_unassigned` must be TRUE or FALSE.")
    if not isinstance(unassigned_label, str) or not unassigned_label.strip():
        raise ValueError("`unassigned_label` must be one non-empty character value.")
    aoi_col = _resolve_col(df, aoi_col, ["aoi", "AOI", "aoi_label", "roi", "region", "area_of_interest"], "AOI", True)
    participant_col = _resolve_col(df, participant_col, ["participant", "participant_id", "subject", "subject_id", "ParticipantName"], "participant", False)
    trial_col = _resolve_col(df, trial_col, ["trial", "trial_id", "stimulus", "stimulus_id", "Trial"], "trial", False)
    start_col = _resolve_col(df, start_col, ["fixation_start_ms", "fixation_start_s", "start_time_ms", "start_time_s", "start_time", "start", "FPOGS", "onset"], "fixation start", True)
    end_col = _resolve_col(df, end_col, ["fixation_end_ms", "fixation_end_s", "end_time_ms", "end_time_s", "end_time", "end", "offset"], "fixation end", False)
    duration_col = _resolve_col(df, duration_col, ["fixation_duration_ms", "fixation_duration_s", "duration_ms", "duration_s", "duration", "FPOGD"], "fixation duration", False)
    event_onset_col = _resolve_col(df, event_onset_col, ["event_onset_ms", "event_onset_s", "event_time_ms", "event_time_s", "stimulus_onset", "trial_onset"], "event onset", False)
    if end_col is None and duration_col is None:
        raise ValueError("Supply or provide an inferable `end_col` or `duration_col`.")
    groups = []
    for c in [participant_col, trial_col, *as_list(group_cols)]:
        if c and c not in groups:
            groups.append(c)
    require_cols(df, groups, "group_cols")

    start_raw = pd.to_numeric(df[start_col], errors="coerce").to_numpy(float)
    resolved_time = _resolve_time_unit(start_raw, start_col, time_unit)
    start_ms = 1000 * _to_seconds(start_raw, resolved_time, sampling_rate_hz)
    end_ms = np.full(len(df), np.nan)
    if end_col is not None:
        raw = pd.to_numeric(df[end_col], errors="coerce").to_numpy(float)
        unit = _resolve_time_unit(raw, end_col, time_unit)
        end_ms = 1000 * _to_seconds(raw, unit, sampling_rate_hz)
    duration_ms = np.full(len(df), np.nan)
    resolved_duration = None
    if duration_col is not None:
        raw = pd.to_numeric(df[duration_col], errors="coerce").to_numpy(float)
        resolved_duration = _resolve_duration_unit(raw, duration_col, duration_unit)
        duration_ms = 1000 * _to_seconds(raw, resolved_duration, sampling_rate_hz)
    else:
        duration_ms = end_ms - start_ms
        resolved_duration = "derived"
    if not np.isfinite(end_ms).any():
        end_ms = start_ms + duration_ms
    else:
        missing_end = ~np.isfinite(end_ms) & np.isfinite(start_ms) & np.isfinite(duration_ms)
        end_ms[missing_end] = start_ms[missing_end] + duration_ms[missing_end]
    onset_ms = np.full(len(df), np.nan)
    if event_onset_col is not None:
        raw = pd.to_numeric(df[event_onset_col], errors="coerce").to_numpy(float)
        unit = _resolve_time_unit(raw, event_onset_col, time_unit)
        onset_ms = 1000 * _to_seconds(raw, unit, sampling_rate_hz)

    aoi = df[aoi_col].astype("string").str.strip()
    unassigned = aoi.isna() | (aoi == "")
    if include_unassigned:
        aoi = aoi.mask(unassigned, unassigned_label)
    valid = np.isfinite(start_ms) & np.isfinite(end_ms) & np.isfinite(duration_ms) & (duration_ms > 0) & (end_ms >= start_ms)
    if not include_unassigned:
        valid &= ~unassigned.to_numpy(bool)
    if not valid.any():
        raise ValueError("No valid assigned fixation rows remain.")
    work = df.loc[valid, groups].reset_index(drop=True) if groups else pd.DataFrame(index=np.arange(valid.sum()))
    work[".aoi"] = aoi[valid].astype(str).to_numpy()
    work[".start_ms"] = start_ms[valid]
    work[".end_ms"] = end_ms[valid]
    work[".duration_ms"] = duration_ms[valid]
    work[".event_onset_ms"] = onset_ms[valid]
    split_cols = [*groups, ".aoi"]
    grouper = split_cols[0] if len(split_cols) == 1 else split_cols
    rows = []
    for key, block in work.groupby(grouper, sort=False, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(split_cols, key))
        durations = block[".duration_ms"].to_numpy(float)
        starts = block[".start_ms"].to_numpy(float)
        ends = block[".end_ms"].to_numpy(float)
        onset = block[".event_onset_ms"].to_numpy(float)
        finite_onset = np.isfinite(onset)
        latency = float(np.nanmin(starts - onset)) if finite_onset.any() else np.nan
        row.update(
            fixation_count=len(block),
            total_fixation_duration_ms=float(np.sum(durations)),
            mean_fixation_duration_ms=float(np.mean(durations)),
            median_fixation_duration_ms=float(np.median(durations)),
            sd_fixation_duration_ms=r_sd(durations),
            minimum_fixation_duration_ms=float(np.min(durations)),
            maximum_fixation_duration_ms=float(np.max(durations)),
            first_fixation_start_ms=float(np.min(starts)),
            last_fixation_end_ms=float(np.max(ends)),
            first_fixation_latency_ms=latency,
        )
        rows.append(row)
    out = pd.DataFrame(rows).rename(columns={".aoi": aoi_col})
    if groups:
        denom = out.groupby(groups, dropna=False)["total_fixation_duration_ms"].transform("sum")
    else:
        denom = pd.Series(float(out["total_fixation_duration_ms"].sum()), index=out.index)
    out["dwell_proportion"] = out["total_fixation_duration_ms"] / denom
    out = out.sort_values([*groups, aoi_col], na_position="last", kind="mergesort").reset_index(drop=True)
    out.attrs["class"] = ["gazepoint_fixation_aoi_summary", "data.frame"]
    out.attrs["audit"] = {
        "source_rows": len(df), "retained_rows": int(valid.sum()), "excluded_rows": int((~valid).sum()),
        "include_unassigned": bool(include_unassigned), "time_unit": resolved_time, "duration_unit": resolved_duration,
        "columns": {"aoi": aoi_col, "participant": participant_col, "trial": trial_col, "groups": groups, "start": start_col, "end": end_col, "duration": duration_col, "event_onset": event_onset_col},
    }
    return out


def summarize_gazepoint_fixations_by_aoi(*args, **kwargs):
    return summarise_gazepoint_fixations_by_aoi(*args, **kwargs)


def _bids_wrapper(modality: str, data, execute=True, **kwargs):
    if not isinstance(execute, (bool, np.bool_)):
        raise TypeError("`execute` must be TRUE or FALSE.")
    spec = {"modality": modality, "function_name": "export_gazepoint_to_bids", "arguments": {"data": data, **kwargs}, "executed": False, "class": ["gazepoint_bids_wrapper_spec", "list"]}
    if not execute:
        return spec
    # Deliberately call through the public registry. Until the unified exporter is
    # ported, this raises ParityNotImplementedError instead of silently writing a
    # non-parity BIDS layout.
    import gpbiometricspy as gp
    exporter = getattr(gp, "export_gazepoint_to_bids")
    result = exporter(data, **kwargs)
    if isinstance(result, dict):
        result.setdefault("gpbiometrics_bids_modality", modality)
    return result


def prepare_gazepoint_bids_eye(data, execute=True, **kwargs):
    return _bids_wrapper("eye", data, execute=execute, **kwargs)


def prepare_gazepoint_bids_physio(data, execute=True, **kwargs):
    return _bids_wrapper("physio", data, execute=execute, **kwargs)


def _mne_script_text():
    return "\n".join([
        "import mne", "import numpy as np", "info = mne.create_info(...)" ,
        "raw = mne.io.RawArray(data, info, first_samp=first_samp)", "raw.save(output, overwrite=overwrite)",
    ])


def _coerce_prepared_mne(x):
    if isinstance(x, dict) and "data" in x:
        return x
    if isinstance(x, pd.DataFrame):
        import gpbiometricspy as gp
        prep = getattr(gp, "prepare_gazepoint_mne_input")
        return prep(x)
    raise TypeError("`x` must be a `gazepoint_mne_input` object or data frame.")


def write_gazepoint_mne_fif(x, fname, events=None, overwrite=False, fmt="single", python=None, execute=True, keep_intermediate=False, verbose=False, **kwargs):
    if fmt not in {"single", "double"}:
        raise ValueError("`fmt` must be 'single' or 'double'.")
    for v, name in [(overwrite, "overwrite"), (execute, "execute"), (keep_intermediate, "keep_intermediate"), (verbose, "verbose")]:
        if not isinstance(v, (bool, np.bool_)):
            raise TypeError(f"`{name}` must be TRUE or FALSE.")
    if not isinstance(fname, (str, Path)) or not str(fname).strip():
        raise ValueError("`fname` must be one non-empty character value.")
    fname = str(fname)
    base = Path(fname).name.lower()
    if not (base.endswith("_raw.fif") or base.endswith("_raw.fif.gz") or base.endswith("_eeg.fif") or base.endswith("_eeg.fif.gz") or base.endswith("_ieeg.fif") or base.endswith("_ieeg.fif.gz") or base.endswith("_meg.fif") or base.endswith("_meg.fif.gz")):
        raise ValueError("`fname` must use an MNE-compatible suffix such as `_raw.fif`.")
    prepared = _coerce_prepared_mne(x)
    matrix = np.asarray(prepared["data"], dtype=float)
    if matrix.ndim != 2 or matrix.size == 0:
        raise ValueError("The prepared MNE data matrix is empty.")
    if not np.isfinite(matrix).all():
        raise ValueError("FIF writing requires finite channel values. Clean or interpolate non-finite values explicitly before export.")
    channel_info = prepared.get("channel_info")
    if not isinstance(channel_info, pd.DataFrame):
        channel_info = pd.DataFrame(channel_info)
    sfreq = float(prepared.get("info_spec", {}).get("sfreq", prepared.get("sampling_rate_hz", np.nan)))
    first_samp = int(prepared.get("rawarray_spec", {}).get("first_samp", prepared.get("first_samp", 0)))
    event_matrix = None
    event_dictionary = None
    if events is not None:
        if isinstance(events, dict) and "events" in events:
            event_matrix = np.asarray(events["events"], dtype=int)
            event_dictionary = events.get("event_dictionary")
        else:
            event_matrix = np.asarray(events, dtype=int)
        if event_matrix.ndim != 2 or event_matrix.shape[1] != 3:
            raise ValueError("MNE events must contain exactly three columns.")
    out_path = str(Path(fname).expanduser().resolve())
    dry = {
        "output": out_path, "n_channels": matrix.shape[0], "n_samples": matrix.shape[1], "sampling_rate_hz": sfreq,
        "first_samp": first_samp, "channel_info": channel_info, "event_count": 0 if event_matrix is None else len(event_matrix),
        "fmt": fmt, "overwrite": bool(overwrite), "python": python, "python_script": _mne_script_text(), "executed": False,
        "class": ["gazepoint_mne_fif_export", "list"],
    }
    if not execute:
        return dry
    try:
        import mne
    except ImportError as exc:
        raise ImportError("MNE is required for `execute=True`; install gpbiometricspy[mne].") from exc
    if not np.isfinite(sfreq) or sfreq <= 0:
        raise ValueError("Prepared MNE input must contain a positive sampling frequency.")
    names = channel_info["channel_name"].astype(str).tolist()
    types = channel_info["channel_type"].astype(str).tolist()
    info = mne.create_info(ch_names=names, sfreq=sfreq, ch_types=types)
    raw = mne.io.RawArray(matrix, info, first_samp=first_samp, verbose=None if verbose else "ERROR")
    if event_matrix is not None:
        if event_dictionary is not None:
            ed = pd.DataFrame(event_dictionary)
            event_desc = dict(zip(ed["event_code"].astype(int), ed["event_label"].astype(str)))
        else:
            event_desc = {int(code): f"event_{int(code)}" for code in np.unique(event_matrix[:, 2])}
        ann = mne.annotations_from_events(event_matrix, sfreq=sfreq, event_desc=event_desc, first_samp=first_samp)
        raw.set_annotations(ann)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    raw.save(out_path, overwrite=overwrite, fmt=fmt, verbose=None if verbose else "ERROR")
    dry.update(executed=True, mne_version=getattr(mne, "__version__", None), python_output=None, intermediate_directory=None)
    return dry


def estimate_gazepoint_lsl_clock_offsets(stream_name=None, stream_type=None, source_id=None, timeout_s=5, n_estimates=5, pause_s=0.05, python=None, execute=True):
    for value, name in [(timeout_s, "timeout_s"), (pause_s, "pause_s")]:
        if not isinstance(value, (int, float, np.number)) or not np.isfinite(value) or value < (0 if name == "pause_s" else np.finfo(float).eps):
            adjective = "non-negative" if name == "pause_s" else "positive"
            raise ValueError(f"`{name}` must be one {adjective} finite number.")
    if not isinstance(n_estimates, (int, np.integer)) or n_estimates < 1:
        raise ValueError("`n_estimates` must be one positive integer.")
    for value, name in [(stream_name, "stream_name"), (stream_type, "stream_type"), (source_id, "source_id")]:
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"`{name}` must be one non-empty character value.")
    if not isinstance(execute, (bool, np.bool_)):
        raise TypeError("`execute` must be TRUE or FALSE.")
    script = "import pylsl\n# StreamInlet(info).time_correction(timeout=...)"
    dry = {
        "filters": {"stream_name": stream_name, "stream_type": stream_type, "source_id": source_id},
        "timeout_s": float(timeout_s), "n_estimates": int(n_estimates), "pause_s": float(pause_s), "python": python,
        "python_script": script, "executed": False, "class": ["gazepoint_lsl_clock_offsets", "list"],
    }
    if not execute:
        return dry
    try:
        import pylsl
    except ImportError as exc:
        raise ImportError("pylsl is required for live LSL clock-offset estimation.") from exc
    streams = pylsl.resolve_streams(wait_time=float(timeout_s))
    selected = []
    for info in streams:
        if stream_name is not None and info.name() != stream_name:
            continue
        if stream_type is not None and info.type() != stream_type:
            continue
        if source_id is not None and info.source_id() != source_id:
            continue
        selected.append(info)
    if not selected:
        raise RuntimeError("No active LSL streams matched the requested filters.")
    rows = []
    for info in selected:
        inlet = pylsl.StreamInlet(info, max_buflen=1, recover=True)
        try:
            for i in range(int(n_estimates)):
                offset = float(inlet.time_correction(timeout=float(timeout_s)))
                rows.append({
                    "stream_name": info.name(), "stream_type": info.type(), "source_id": info.source_id(), "uid": info.uid(),
                    "hostname": info.hostname(), "estimate_index": i + 1, "offset_s": offset, "local_clock_s": float(pylsl.local_clock()),
                })
                if pause_s > 0 and i + 1 < int(n_estimates):
                    time.sleep(float(pause_s))
        finally:
            close = getattr(inlet, "close_stream", None)
            if callable(close):
                close()
    estimates = pd.DataFrame(rows)
    if estimates.empty:
        raise RuntimeError("No LSL clock-offset estimates were returned.")
    summary_rows = []
    for _, block in estimates.groupby(["stream_name", "stream_type", "source_id"], sort=False, dropna=False):
        vals = block["offset_s"].to_numpy(float)
        summary_rows.append({
            "stream_name": block.iloc[0]["stream_name"], "stream_type": block.iloc[0]["stream_type"], "source_id": block.iloc[0]["source_id"],
            "uid": block.iloc[0]["uid"], "hostname": block.iloc[0]["hostname"], "n_estimates": len(vals), "median_offset_s": float(np.median(vals)),
            "mean_offset_s": float(np.mean(vals)), "sd_offset_s": r_sd(vals), "mad_offset_s": float(np.median(np.abs(vals - np.median(vals))) * 1.4826),
            "minimum_offset_s": float(np.min(vals)), "maximum_offset_s": float(np.max(vals)), "offset_range_s": float(np.ptp(vals)),
        })
    summary = pd.DataFrame(summary_rows)
    # R make.unique(stream_name): emulate with suffixes only when duplicated.
    seen = {}
    offsets = {}
    for _, row in summary.iterrows():
        name = str(row["stream_name"])
        n = seen.get(name, 0)
        key = name if n == 0 else f"{name}.{n}"
        seen[name] = n + 1
        offsets[key] = float(row["median_offset_s"])
    dry.update(executed=True, estimates=estimates, summary=summary, clock_offsets_s=offsets, pylsl_version=getattr(pylsl, "__version__", None), python_output=None)
    return dry
