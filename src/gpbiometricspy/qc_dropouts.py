from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd


_TIME_GROUP_CANDIDATES = [
    "source_file", "source_participant", "USER", "USER_FILE", "participant",
    "subject", "subject_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name",
    "trial", "trial_id", "trial_global",
]
_ACTIVITY_SIGNAL_CANDIDATES = [
    "DIAL", "DIALV", "GSR", "GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSRV",
    "HR", "HRV", "HRP", "IBI", "dial", "dialv", "gsr", "gsr_us",
    "gsr_us_tonic", "gsr_us_phasic", "gsrv", "hr", "hrv", "hrp", "ibi",
]
_DROPOUT_SIGNAL_CANDIDATES = ["GSR", "GSR_US", "GSR_OHMS", "HR", "IBI", "ENGAGEMENT"]


def _as_cols(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _check_df(data) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    return data.copy()


def _resolve_groups(columns: Iterable[str], group_cols=None) -> list[str]:
    cols = list(columns)
    groups = _as_cols(group_cols) if group_cols is not None else [x for x in _TIME_GROUP_CANDIDATES if x in cols]
    missing = [x for x in groups if x not in cols]
    if missing:
        raise ValueError(f"`group_cols` not found in `data`: {', '.join(missing)}")
    return list(dict.fromkeys(groups))


def _group_id(dat: pd.DataFrame, groups: list[str]) -> pd.Series:
    if not groups:
        return pd.Series(["all"] * len(dat), index=dat.index, dtype=object)
    work = dat[groups].copy().astype(object)
    work = work.where(~work.isna(), "<NA>")
    return work.astype(str).agg("||".join, axis=1)


def _group_positions(dat: pd.DataFrame, groups: list[str]):
    if not groups:
        return [("all", np.arange(len(dat), dtype=int))]
    ids = _group_id(dat, groups).to_numpy()
    # preserve first-observed group order, like split(factor(...)) sufficiently for package fixtures
    names = list(dict.fromkeys(ids.tolist()))
    return [(name, np.flatnonzero(ids == name)) for name in names]


def audit_gazepoint_time_resets(
    data,
    time_col=None,
    group_cols=None,
    allow_ties=True,
    split_on_negative_step=True,
    return_reindexed_time=False,
    min_segment_rows=1,
):
    dat = _check_df(data).reset_index(drop=True)
    if not isinstance(allow_ties, (bool, np.bool_)):
        raise TypeError("`allow_ties` must be TRUE or FALSE.")
    if not isinstance(split_on_negative_step, (bool, np.bool_)):
        raise TypeError("`split_on_negative_step` must be TRUE or FALSE.")
    if not isinstance(return_reindexed_time, (bool, np.bool_)):
        raise TypeError("`return_reindexed_time` must be TRUE or FALSE.")
    if not isinstance(min_segment_rows, (int, float, np.integer, np.floating)) or min_segment_rows < 1:
        raise ValueError("`min_segment_rows` must be a positive number.")

    if time_col is None:
        candidates = ["time_ms", "timestamp_ms", "timestamp", "TIME", "Time", "time", "CNT", "cnt"]
        exact = next((x for x in candidates if x in dat.columns), None)
        if exact is None:
            lower = {str(c).lower(): c for c in dat.columns}
            exact = next((lower[x.lower()] for x in candidates if x.lower() in lower), None)
        time_col = exact
    if time_col is None or time_col not in dat.columns:
        raise ValueError("No usable time column was found. Supply `time_col`.")

    groups = _resolve_groups(dat.columns, group_cols)
    t = pd.to_numeric(dat[time_col], errors="coerce").to_numpy(float)
    row_id = np.arange(1, len(dat) + 1, dtype=int)
    gid = _group_id(dat, groups).to_numpy()
    group_row = np.full(len(dat), np.nan)
    delta = np.full(len(dat), np.nan)
    neg = np.zeros(len(dat), dtype=bool)
    dup = np.zeros(len(dat), dtype=bool)
    nonmono = np.zeros(len(dat), dtype=bool)
    seg = np.full(len(dat), np.nan)

    for _, idx in _group_positions(dat, groups):
        group_row[idx] = np.arange(1, len(idx) + 1)
        x = t[idx]
        d = np.r_[np.nan, np.diff(x)]
        finite = np.isfinite(d)
        n = finite & (d < 0)
        z = finite & (d == 0)
        m = n.copy() if allow_ties else finite & (d <= 0)
        delta[idx], neg[idx], dup[idx], nonmono[idx] = d, n, z, m
        seg[idx] = np.cumsum(n).astype(int) + 1 if split_on_negative_step else 1

    row_flags = pd.DataFrame({
        ".gpbiometrics_row_id": row_id,
        "time_col": [time_col] * len(dat),
        "time_value": t,
        "group_id": gid,
        "group_row_index": group_row.astype(int, copy=False) if len(dat) else group_row,
        "time_delta": delta,
        "flag_nonfinite_time": ~np.isfinite(t),
        "flag_negative_step": neg,
        "flag_duplicate_time": dup,
        "flag_nonmonotonic": nonmono,
        "reset_segment_index": seg.astype(int, copy=False) if len(dat) else seg,
        "flag_short_segment": False,
    })
    if groups:
        row_flags = pd.concat([dat[groups].reset_index(drop=True), row_flags], axis=1)

    keys = np.array([f"{g}||segment_{int(s)}" for g, s in zip(gid, seg)], dtype=object)
    segment_rows = []
    for key in dict.fromkeys(keys.tolist()):
        idx = np.flatnonzero(keys == key)
        finite_t = t[idx][np.isfinite(t[idx])]
        row = {}
        if groups:
            row.update(dat.iloc[idx[0]][groups].to_dict())
        row.update({
            "segment_key": key,
            "group_id": gid[idx[0]],
            "segment_index": int(seg[idx[0]]),
            "start_row_id": int(row_id[idx[0]]),
            "end_row_id": int(row_id[idx[-1]]),
            "rows": int(len(idx)),
            "start_time": finite_t[0] if len(finite_t) else np.nan,
            "end_time": finite_t[-1] if len(finite_t) else np.nan,
            "duration": finite_t[-1] - finite_t[0] if len(finite_t) > 1 else np.nan,
            "nonfinite_time_rows": int((~np.isfinite(t[idx])).sum()),
            "negative_steps": int(neg[idx].sum()),
            "duplicate_steps": int(dup[idx].sum()),
            "nonmonotonic_steps": int(nonmono[idx].sum()),
            "short_segment": bool(len(idx) < min_segment_rows),
        })
        segment_rows.append(row)
    segment_summary = pd.DataFrame(segment_rows)
    short_keys = set(segment_summary.loc[segment_summary["rows"] < min_segment_rows, "segment_key"]) if len(segment_summary) else set()
    row_flags["flag_short_segment"] = [k in short_keys for k in keys]

    enriched = dat.copy()
    enriched["time_qc_group_id"] = gid
    enriched["time_qc_group_row_index"] = group_row.astype(int)
    enriched["time_qc_delta"] = delta
    enriched["time_qc_negative_step"] = neg
    enriched["time_qc_duplicate_step"] = dup
    enriched["time_qc_nonmonotonic"] = nonmono
    enriched["time_qc_segment_index"] = seg.astype(int)
    if return_reindexed_time:
        reindexed = np.full(len(dat), np.nan)
        for key in dict.fromkeys(keys.tolist()):
            idx = np.flatnonzero(keys == key)
            finite_idx = idx[np.isfinite(t[idx])]
            if len(finite_idx):
                reindexed[idx] = t[idx] - t[finite_idx[0]]
        enriched["time_reindexed_within_segment"] = reindexed

    nneg, ndup, nmono, nfinite = int(neg.sum()), int(dup.sum()), int(nonmono.sum()), int((~np.isfinite(t)).sum())
    affected = len(set(gid[neg]))
    status = "fail_no_numeric_time" if np.isnan(t).all() else (
        "warn_time_irregularities_detected" if nneg or nmono or nfinite else "pass"
    )
    overview = pd.DataFrame([{
        "input_rows": len(dat), "time_col": time_col, "group_count": len(_group_positions(dat, groups)),
        "segment_count": len(segment_summary), "negative_steps": nneg, "duplicate_steps": ndup,
        "nonmonotonic_steps": nmono, "nonfinite_time_rows": nfinite,
        "affected_groups": affected, "status": status,
    }])
    return {
        "overview": overview, "segment_summary": segment_summary, "row_flags": row_flags,
        "data_with_segments": enriched,
        "settings": {"time_col": time_col, "group_cols": groups, "allow_ties": bool(allow_ties),
                     "split_on_negative_step": bool(split_on_negative_step),
                     "return_reindexed_time": bool(return_reindexed_time), "min_segment_rows": min_segment_rows},
    }


def audit_gazepoint_signal_activity(
    data,
    signal_cols=None,
    group_cols=None,
    zero_is_inactive=True,
    min_unique_nonzero=2,
    missing_as_inactive=True,
):
    dat = _check_df(data).reset_index(drop=True)
    if not isinstance(zero_is_inactive, (bool, np.bool_)):
        raise TypeError("`zero_is_inactive` must be TRUE or FALSE.")
    if not isinstance(min_unique_nonzero, (int, float, np.integer, np.floating)) or min_unique_nonzero < 1:
        raise ValueError("`min_unique_nonzero` must be a positive number.")
    if not isinstance(missing_as_inactive, (bool, np.bool_)):
        raise TypeError("`missing_as_inactive` must be TRUE or FALSE.")
    signals = _as_cols(signal_cols) if signal_cols is not None else [x for x in _ACTIVITY_SIGNAL_CANDIDATES if x in dat.columns]
    signals = list(dict.fromkeys(signals))
    if not signals:
        raise ValueError("No biometric signal columns were found. Supply `signal_cols`.")
    missing = [x for x in signals if x not in dat.columns]
    if missing:
        raise ValueError(f"`signal_cols` not found in `data`: {', '.join(missing)}")
    groups = _resolve_groups(dat.columns, group_cols)

    rows = []
    for gname, idx in _group_positions(dat, groups):
        base = dat.iloc[idx[0]][groups].to_dict() if groups else {}
        for signal in signals:
            source = dat.iloc[idx][signal]
            x = pd.to_numeric(source, errors="coerce").to_numpy(float)
            numeric_or_coercible = not np.isnan(x).all()
            source_all_missing = bool(source.isna().all())
            finite = x[np.isfinite(x)]
            nonzero = finite[finite != 0]
            n = len(x); nmiss = int(np.isnan(x).sum()); nzero = int((np.isfinite(x) & (x == 0)).sum())
            nnonzero = int((np.isfinite(x) & (x != 0)).sum())
            nuf, nunz = len(np.unique(finite)), len(np.unique(nonzero))
            if n == 0 or (missing_as_inactive and nmiss == n and source_all_missing):
                status = "insufficient_data"
            elif not numeric_or_coercible:
                status = "nonnumeric"
            elif zero_is_inactive and nnonzero == 0 and nzero > 0:
                status = "inactive_all_zero"
            elif nuf <= 1:
                status = "inactive_constant"
            elif nunz < min_unique_nonzero:
                status = "low_variation"
            else:
                status = "active"
            row = dict(base)
            row.update({
                "group_id": gname, "signal": signal, "n": n, "missing_count": nmiss,
                "missing_prop": nmiss / n if n else np.nan, "zero_count": nzero,
                "zero_prop": nzero / n if n else np.nan, "nonzero_count": nnonzero,
                "nonzero_prop": nnonzero / n if n else np.nan, "unique_finite": nuf,
                "unique_nonzero": nunz, "mean": np.mean(finite) if len(finite) else np.nan,
                "sd": np.std(finite, ddof=1) if len(finite) > 1 else np.nan,
                "min": np.min(finite) if len(finite) else np.nan,
                "max": np.max(finite) if len(finite) else np.nan,
                "numeric_or_coercible": numeric_or_coercible, "status": status,
            })
            rows.append(row)
    sbg = pd.DataFrame(rows)
    inactive_statuses = {"inactive_all_zero", "inactive_constant", "low_variation", "insufficient_data", "nonnumeric"}
    group_rows = []
    for gid in sbg["group_id"].drop_duplicates():
        d = sbg[sbg["group_id"] == gid]
        row = d.iloc[0][groups].to_dict() if groups else {}
        active = int((d["status"] == "active").sum())
        row.update({
            "group_id": gid, "signal_count": len(d), "active_signal_count": active,
            "inactive_signal_count": int(d["status"].isin(inactive_statuses).sum()),
            "low_variation_signal_count": int((d["status"] == "low_variation").sum()),
            "all_zero_signal_count": int((d["status"] == "inactive_all_zero").sum()),
            "constant_signal_count": int((d["status"] == "inactive_constant").sum()),
            "group_status": "no_active_signals" if active == 0 else ("partial_active_signals" if active < len(d) else "all_signals_active"),
        })
        group_rows.append(row)
    gs = pd.DataFrame(group_rows)
    inactive_groups = gs[gs["active_signal_count"] == 0].reset_index(drop=True)
    signal_rows = []
    for signal in sbg["signal"].drop_duplicates():
        d = sbg[sbg["signal"] == signal]
        active = int((d["status"] == "active").sum())
        signal_rows.append({
            "signal": signal, "group_count": len(d), "active_group_count": active,
            "inactive_group_count": int(d["status"].isin(inactive_statuses).sum()),
            "all_zero_group_count": int((d["status"] == "inactive_all_zero").sum()),
            "constant_group_count": int((d["status"] == "inactive_constant").sum()),
            "low_variation_group_count": int((d["status"] == "low_variation").sum()),
            "median_nonzero_prop": float(d["nonzero_prop"].median()),
            "median_missing_prop": float(d["missing_prop"].median()),
            "signal_status": "inactive_in_all_groups" if active == 0 else ("active_in_some_groups" if active < len(d) else "active_in_all_groups"),
        })
    inactive_signals = pd.DataFrame(signal_rows)
    active_groups = int((gs["active_signal_count"] > 0).sum())
    no_active = int((gs["active_signal_count"] == 0).sum())
    status = "fail_no_active_signals" if active_groups == 0 else (
        "warn_inactive_groups_detected" if no_active else ("warn_inactive_or_low_variation_signals_detected" if (sbg["status"] != "active").any() else "pass")
    )
    overview = pd.DataFrame([{
        "input_rows": len(dat), "signal_count": len(signals), "group_count": len(gs),
        "active_group_count": active_groups, "no_active_group_count": no_active,
        "inactive_signal_rows": int(sbg["status"].isin(inactive_statuses).sum()), "status": status,
    }])
    return {"overview": overview, "signal_by_group": sbg, "inactive_groups": inactive_groups,
            "inactive_signals": inactive_signals,
            "settings": {"signal_cols": signals, "group_cols": groups, "zero_is_inactive": bool(zero_is_inactive),
                         "min_unique_nonzero": min_unique_nonzero, "missing_as_inactive": bool(missing_as_inactive)}}


def _run_flags(condition, min_run: int) -> np.ndarray:
    cond = np.asarray(condition, dtype=bool)
    flags = np.zeros(len(cond), dtype=bool)
    start = None
    for i, value in enumerate(np.r_[cond, False]):
        if value and start is None:
            start = i
        elif not value and start is not None:
            if i - start >= min_run:
                flags[start:i] = True
            start = None
    return flags


def _flatline_flags(values, min_run, tolerance):
    x = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    valid = np.isfinite(x)
    flags = np.zeros(len(x), dtype=bool)
    start = None; length = 0
    for i in range(len(x)):
        if not valid[i]:
            if start is not None and length >= min_run:
                flags[start:i] = True
            start = None; length = 0
            continue
        if start is None:
            start = i; length = 1; continue
        if valid[i - 1] and abs(x[i] - x[i - 1]) <= tolerance:
            length += 1
        else:
            if length >= min_run:
                flags[start:i] = True
            start = i; length = 1
    if start is not None and length >= min_run:
        flags[start:] = True
    return flags


def _safe_col(x):
    s = re.sub(r"[^A-Za-z0-9]+", "_", str(x))
    s = re.sub(r"_+", "_", s).strip("_") or "signal"
    # make.names equivalent needed for common signal names only; prefix X for digit-leading
    if s[0].isdigit():
        s = "X" + s
    return s


def _infer_dropout_signals(dat):
    return [c for c in _DROPOUT_SIGNAL_CANDIDATES if c in dat.columns]


def flag_gazepoint_biometric_dropouts(
    data, signal_cols=None, group_cols=None, time_col=None,
    min_missing_run=5, min_flatline_run=10, constant_tolerance=0,
    prefix="biometric_dropout",
):
    dat = _check_df(data).reset_index(drop=True)
    signals = _as_cols(signal_cols) if signal_cols is not None else _infer_dropout_signals(dat)
    groups = _as_cols(group_cols)
    for arg, cols in [("signal_cols", signals), ("group_cols", groups), ("time_col", [] if time_col is None else [time_col])]:
        missing = [x for x in cols if x not in dat.columns]
        if missing:
            raise ValueError(f"`{arg}` contains columns not found in `data`: {', '.join(missing)}")
    for name, value in [("min_missing_run", min_missing_run), ("min_flatline_run", min_flatline_run)]:
        if not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"`{name}` must be a positive integer.")
    if not isinstance(constant_tolerance, (int, float, np.integer, np.floating)) or not np.isfinite(constant_tolerance) or constant_tolerance < 0:
        raise ValueError("`constant_tolerance` must be a non-negative number.")
    if not isinstance(prefix, str) or not prefix:
        raise ValueError("`prefix` must be a non-empty character string.")
    out = dat.copy()
    if not signals:
        out[f"{prefix}_any"] = False
        out.attrs["dropout_summary"] = pd.DataFrame(columns=["column", "signal_type", "n", "n_missing_dropout", "missing_dropout_rate", "n_flatline_dropout", "flatline_dropout_rate", "n_any_dropout", "any_dropout_rate"])
        out.attrs["dropout_settings"] = {"signal_cols": signals, "group_cols": groups or None, "time_col": time_col,
                                          "min_missing_run": min_missing_run, "min_flatline_run": min_flatline_run,
                                          "constant_tolerance": constant_tolerance, "prefix": prefix}
        return out
    all_any_cols = []
    for signal in signals:
        safe = _safe_col(signal)
        missing_col, flat_col, any_col = f"{prefix}_{safe}_missing", f"{prefix}_{safe}_flatline", f"{prefix}_{safe}_any"
        out[missing_col] = False; out[flat_col] = False
        for _, idx in _group_positions(out, groups):
            ordered = idx
            if time_col is not None:
                tv = pd.to_numeric(out.iloc[idx][time_col], errors="coerce").to_numpy(float)
                # finite values first ordered ascending; nonfinite last stably
                ordered = idx[np.argsort(np.where(np.isfinite(tv), tv, np.inf), kind="stable")]
            vals = out.iloc[ordered][signal]
            x = pd.to_numeric(vals, errors="coerce").to_numpy(float)
            miss_flags = _run_flags(~np.isfinite(x), min_missing_run)
            flat_flags = _flatline_flags(vals.to_numpy(), min_flatline_run, constant_tolerance)
            out.loc[ordered, missing_col] = miss_flags
            out.loc[ordered, flat_col] = flat_flags
        out[any_col] = out[missing_col] | out[flat_col]
        all_any_cols.append(any_col)
    out[f"{prefix}_any"] = out[all_any_cols].any(axis=1)
    summary_rows = []
    for signal in signals:
        safe = _safe_col(signal); mc=f"{prefix}_{safe}_missing"; fc=f"{prefix}_{safe}_flatline"; ac=f"{prefix}_{safe}_any"
        standard = signal.upper()
        stype = "gsr_eda" if standard in {"GSR", "GSR_US", "GSR_OHMS"} else ("heart_rate" if standard == "HR" else ("ibi" if standard == "IBI" else ("engagement_dial" if standard == "ENGAGEMENT" else "other")))
        n = len(out)
        summary_rows.append({"column": signal, "signal_type": stype, "n": n,
                             "n_missing_dropout": int(out[mc].sum()), "missing_dropout_rate": float(out[mc].mean()) if n else np.nan,
                             "n_flatline_dropout": int(out[fc].sum()), "flatline_dropout_rate": float(out[fc].mean()) if n else np.nan,
                             "n_any_dropout": int(out[ac].sum()), "any_dropout_rate": float(out[ac].mean()) if n else np.nan})
    out.attrs["dropout_summary"] = pd.DataFrame(summary_rows)
    out.attrs["dropout_settings"] = {"signal_cols": signals, "group_cols": groups or None, "time_col": time_col,
                                      "min_missing_run": int(min_missing_run), "min_flatline_run": int(min_flatline_run),
                                      "constant_tolerance": constant_tolerance, "prefix": prefix}
    return out


def _flag_run_intervals(flag, min_run):
    flags = np.asarray(flag, dtype=bool)
    rows = []
    start = None
    for i, v in enumerate(np.r_[flags, False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_run:
                rows.append((start, i - 1, i - start))
            start = None
    return rows


def _constant_intervals(x, min_run, tolerance):
    x = np.asarray(x, dtype=float); n = len(x)
    if n <= 1:
        return []
    finite = np.isfinite(x)
    new = np.ones(n, dtype=bool)
    for i in range(1, n):
        new[i] = not (finite[i] and finite[i-1] and abs(x[i]-x[i-1]) <= tolerance)
    run_id = np.cumsum(new)
    counts = pd.Series(run_id).value_counts().to_dict()
    constant = finite & np.array([counts[r] >= min_run for r in run_id])
    return _flag_run_intervals(constant, min_run)


def _lowvar_intervals(x, min_run, threshold):
    x = np.asarray(x, dtype=float); flag = np.zeros(len(x), dtype=bool)
    if len(x) >= min_run:
        for i in range(len(x) - min_run + 1):
            vals = x[i:i+min_run]
            if np.isfinite(vals).all() and np.std(vals, ddof=1) <= threshold:
                flag[i:i+min_run] = True
    return _flag_run_intervals(flag, min_run)


def detect_gazepoint_nonwear(
    data, signal_cols, group_cols=None, time_col=None, min_run_length=10,
    zero_tolerance=0, constant_tolerance=0, low_variance_threshold=None,
    detect_missing=True, detect_zero=True, detect_constant=True, detect_low_variance=True,
):
    dat = _check_df(data).reset_index(drop=True)
    if len(dat) == 0:
        raise ValueError("`data` must contain at least one row.")
    signals = _as_cols(signal_cols)
    if not signals:
        raise ValueError("`signal_cols` must contain at least one column name.")
    missing = [c for c in signals if c not in dat.columns]
    if missing:
        raise ValueError(f"`signal_cols` contains columns not found in `data`: {', '.join(missing)}")
    nonnumeric = [c for c in signals if not pd.api.types.is_numeric_dtype(dat[c])]
    if nonnumeric:
        raise TypeError(f"All `signal_cols` must be numeric. Non-numeric columns: {', '.join(nonnumeric)}")
    groups = _as_cols(group_cols)
    missing_groups = [c for c in groups if c not in dat.columns]
    if missing_groups:
        raise ValueError(f"`group_cols` contains columns not found in `data`: {', '.join(missing_groups)}")
    if time_col is not None:
        if time_col not in dat.columns:
            raise ValueError("`time_col` was not found in `data`.")
        if not pd.api.types.is_numeric_dtype(dat[time_col]):
            raise TypeError("`time_col` must be numeric.")
    if not isinstance(min_run_length, (int, np.integer, float, np.floating)) or min_run_length < 1:
        raise ValueError("`min_run_length` must be a single positive number.")
    min_run_length = int(min_run_length)
    for name, val in [("zero_tolerance", zero_tolerance), ("constant_tolerance", constant_tolerance)]:
        if not isinstance(val, (int, float, np.integer, np.floating)) or not np.isfinite(val) or val < 0:
            raise ValueError(f"`{name}` must be a single non-negative number.")
    if low_variance_threshold is not None and (not isinstance(low_variance_threshold, (int,float,np.integer,np.floating)) or not np.isfinite(low_variance_threshold) or low_variance_threshold < 0):
        raise ValueError("`low_variance_threshold` must be a single non-negative number.")

    working = dat.copy(); working[".gp_row_index"] = np.arange(1, len(working)+1)
    interval_rows=[]; summary_rows=[]
    for piece_name, idx in _group_positions(working, groups):
        piece = working.iloc[idx].copy()
        if time_col is not None:
            piece = piece.sort_values(time_col, na_position="last", kind="stable")
        base = piece.iloc[0][groups].to_dict() if groups else {"segment_id": piece_name}
        for signal in signals:
            x = piece[signal].to_numpy(float); any_flag=np.zeros(len(x), bool)
            specs = {}
            if detect_missing: specs["missing_run"] = _flag_run_intervals(~np.isfinite(x), min_run_length)
            if detect_zero: specs["zero_run"] = _flag_run_intervals(np.isfinite(x) & (np.abs(x) <= zero_tolerance), min_run_length)
            if detect_constant: specs["constant_run"] = _constant_intervals(x, min_run_length, constant_tolerance)
            if detect_low_variance and low_variance_threshold is not None: specs["low_variance_run"] = _lowvar_intervals(x, min_run_length, low_variance_threshold)
            counts = {k: len(specs.get(k, [])) for k in ["missing_run","zero_run","constant_run","low_variance_run"]}
            for run_type, intervals in specs.items():
                for start, end, ns in intervals:
                    any_flag[start:end+1] = True
                    row = dict(base)
                    row.update({"signal":signal,"run_type":run_type,"start_row":int(piece.iloc[start][".gp_row_index"]),
                                "end_row":int(piece.iloc[end][".gp_row_index"]),"start_position":start+1,"end_position":end+1,
                                "n_samples":ns,"start_time":piece.iloc[start][time_col] if time_col else np.nan,
                                "end_time":piece.iloc[end][time_col] if time_col else np.nan})
                    interval_rows.append(row)
            row=dict(base); row.update({"signal":signal,"n_samples":len(x),"n_intervals":sum(counts.values()),
                                        "n_flagged_samples":int(any_flag.sum()),"prop_flagged_samples":float(any_flag.mean()) if len(x) else np.nan,
                                        **{f"n_{k}":v for k,v in counts.items()}})
            summary_rows.append(row)
    base_interval_cols = (groups if groups else ["segment_id"]) + ["signal","run_type","start_row","end_row","start_position","end_position","n_samples","start_time","end_time"]
    intervals=pd.DataFrame(interval_rows, columns=base_interval_cols)
    summary=pd.DataFrame(summary_rows)
    return {"intervals":intervals,"summary":summary,"parameters":{"signal_cols":signals,"group_cols":groups or None,"time_col":time_col,
            "min_run_length":min_run_length,"zero_tolerance":zero_tolerance,"constant_tolerance":constant_tolerance,
            "low_variance_threshold":low_variance_threshold,"detect_missing":detect_missing,"detect_zero":detect_zero,
            "detect_constant":detect_constant,"detect_low_variance":detect_low_variance}}


def summarize_gazepoint_nonwear(nonwear, by="signal"):
    summary = nonwear.get("summary") if isinstance(nonwear, dict) and "summary" in nonwear else nonwear
    if not isinstance(summary, pd.DataFrame):
        raise TypeError("`nonwear` must be a gazepoint_nonwear_detection object or data frame.")
    required=["n_samples","n_intervals","n_flagged_samples","n_missing_run","n_zero_run","n_constant_run","n_low_variance_run"]
    missing=[c for c in required if c not in summary.columns]
    if missing: raise ValueError(f"`nonwear` is missing required columns: {', '.join(missing)}")
    groups=_as_cols(by); missing=[c for c in groups if c not in summary.columns]
    if missing: raise ValueError(f"`by` contains columns not found in `nonwear`: {', '.join(missing)}")
    rows=[]
    for key,piece in summary.groupby(groups, sort=False, dropna=False):
        if len(groups) == 1:
            key = key if isinstance(key, tuple) else (key,)
        row=dict(zip(groups,key)); ns=float(piece["n_samples"].sum()); nf=float(piece["n_flagged_samples"].sum())
        row.update({"n_signal_segments":len(piece),"n_samples_total":int(ns),"n_intervals_total":int(piece["n_intervals"].sum()),
                    "n_flagged_samples_total":int(nf),"prop_flagged_samples":nf/ns if ns>0 else np.nan,
                    "n_missing_run":int(piece["n_missing_run"].sum()),"n_zero_run":int(piece["n_zero_run"].sum()),
                    "n_constant_run":int(piece["n_constant_run"].sum()),"n_low_variance_run":int(piece["n_low_variance_run"].sum())})
        rows.append(row)
    return pd.DataFrame(rows)


def _roll(x, window, fun, na_rm):
    x=np.asarray(x,dtype=float); n=len(x); y=np.full(n,np.nan)
    left=(window-1)//2; right=int(np.ceil((window-1)/2))
    for i in range(n):
        vals=x[max(0,i-left):min(n,i+right+1)].copy(); vals[~np.isfinite(vals)]=np.nan
        if (not na_rm and np.isnan(vals).any()) or (na_rm and np.isnan(vals).all()): continue
        y[i]=fun(vals[~np.isnan(vals)] if na_rm else vals)
    return y


def filter_gazepoint_signal(data, signal_cols, method="moving_average", group_cols=None, time_col=None, window=5, suffix=None, overwrite=False, na_rm=False):
    dat=_check_df(data).reset_index(drop=True); signals=_as_cols(signal_cols)
    if not signals: raise ValueError("`signal_cols` must contain at least one column name.")
    if method not in {"moving_average","rolling_median","detrend"}: raise ValueError("`method` must be one of moving_average, rolling_median, detrend.")
    missing=[c for c in signals if c not in dat.columns]
    if missing: raise ValueError(f"`signal_cols` contains columns not found in `data`: {', '.join(missing)}")
    nonnum=[c for c in signals if not pd.api.types.is_numeric_dtype(dat[c])]
    if nonnum: raise TypeError(f"All `signal_cols` must be numeric. Non-numeric columns: {', '.join(nonnum)}")
    groups=_as_cols(group_cols); mg=[c for c in groups if c not in dat.columns]
    if mg: raise ValueError(f"`group_cols` contains columns not found in `data`: {', '.join(mg)}")
    if time_col is not None:
        if time_col not in dat.columns: raise ValueError("`time_col` was not found in `data`.")
        if not pd.api.types.is_numeric_dtype(dat[time_col]): raise TypeError("`time_col` must be numeric.")
    if method in {"moving_average","rolling_median"} and (not isinstance(window,(int,float,np.integer,np.floating)) or window<1): raise ValueError("`window` must be a single positive number.")
    window=int(window); suffix=f"_{method}" if suffix is None else suffix
    if not isinstance(suffix,str): raise TypeError("`suffix` must be `NULL` or a single character string.")
    out=dat.copy(); logs=[]
    for signal in signals:
        output=signal if overwrite else signal+suffix
        if not overwrite and output in out.columns: raise ValueError(f"Output column already exists: {output}. Choose another `suffix` or set `overwrite = TRUE`.")
        out[output]=np.nan
        for gname,idx in _group_positions(dat,groups):
            ordered=idx
            if time_col is not None:
                t=dat.iloc[idx][time_col].to_numpy(float); ordered=idx[np.argsort(np.where(np.isfinite(t),t,np.inf),kind="stable")]
            x=dat.iloc[ordered][signal].to_numpy(float)
            if method=="moving_average": filt=_roll(x,window,np.mean,na_rm)
            elif method=="rolling_median": filt=_roll(x,window,np.median,na_rm)
            else:
                tt=dat.iloc[ordered][time_col].to_numpy(float) if time_col else np.arange(1,len(x)+1,dtype=float)
                finite=np.isfinite(x)&np.isfinite(tt); filt=np.full(len(x),np.nan)
                if finite.sum()>=2:
                    coef=np.polyfit(tt[finite],x[finite],1); trend=np.polyval(coef,tt[finite]); filt[finite]=x[finite]-(trend-np.mean(trend))
            out.loc[ordered,output]=filt
            logs.append({"signal":signal,"output_col":output,"group":gname,"method":method,"window":np.nan if method=="detrend" else window,
                         "n_samples":len(x),"n_nonmissing_input":int(np.isfinite(x).sum()),"n_nonmissing_output":int(np.isfinite(filt).sum())})
    out.attrs["filter_log"]=pd.DataFrame(logs)
    return out


def _approx_signal(time,value,xout,method):
    t=np.asarray(time,float); v=np.asarray(value,float); valid=np.isfinite(t)&np.isfinite(v)
    if valid.sum()<2: return np.full(len(xout),np.nan)
    d=pd.DataFrame({"time":t[valid],"value":v[valid]}).groupby("time",as_index=False)["value"].mean().sort_values("time")
    tx=d["time"].to_numpy(); vy=d["value"].to_numpy(); xo=np.asarray(xout,float)
    if method=="linear":
        y=np.interp(xo,tx,vy); y[(xo<tx.min())|(xo>tx.max())]=np.nan; return y
    pos=np.searchsorted(tx,xo,side="right")-1; y=np.full(len(xo),np.nan); ok=(pos>=0)&(xo<=tx.max()); y[ok]=vy[pos[ok]]; return y


def upsample_gazepoint_data(data,time_col,signal_cols=None,group_cols=None,interval=None,method="linear"):
    dat=_check_df(data).reset_index(drop=True)
    if len(dat)==0: raise ValueError("`data` must contain at least one row.")
    if time_col not in dat.columns: raise ValueError("`time_col` was not found in `data`.")
    if not pd.api.types.is_numeric_dtype(dat[time_col]): raise TypeError("`time_col` must be numeric.")
    groups=_as_cols(group_cols); mg=[c for c in groups if c not in dat.columns]
    if mg: raise ValueError(f"`group_cols` contains columns not found in `data`: {', '.join(mg)}")
    signals=_as_cols(signal_cols) if signal_cols is not None else [c for c in dat.columns if pd.api.types.is_numeric_dtype(dat[c]) and c not in [time_col,*groups]]
    if not signals: raise ValueError("No numeric signal columns were selected.")
    missing=[c for c in signals if c not in dat.columns]
    if missing: raise ValueError(f"`signal_cols` contains columns not found in `data`: {', '.join(missing)}")
    nonnum=[c for c in signals if not pd.api.types.is_numeric_dtype(dat[c])]
    if nonnum: raise TypeError(f"All `signal_cols` must be numeric. Non-numeric columns: {', '.join(nonnum)}")
    if interval is not None and (not isinstance(interval,(int,float,np.integer,np.floating)) or not np.isfinite(interval) or interval<=0): raise ValueError("`interval` must be a single positive number.")
    if method not in {"linear","constant"}: raise ValueError("`method` must be one of: linear, constant.")
    rows=[]; logs=[]
    for piece_name,idx in _group_positions(dat,groups):
        piece=dat.iloc[idx].copy().sort_values(time_col,na_position="last",kind="stable"); piece=piece[np.isfinite(piece[time_col])]
        if len(piece)<2: continue
        times=piece[time_col].to_numpy(float); unique=np.unique(times); diffs=np.diff(unique); positive=diffs[np.isfinite(diffs)&(diffs>0)]
        if not len(positive): continue
        step=float(np.median(positive) if interval is None else interval)
        start,end=float(unique.min()),float(unique.max()); count=int(np.floor((end-start)/step+1e-12)); grid=start+step*np.arange(count+1)
        base=piece.iloc[0][groups].to_dict() if groups else {"segment_id":piece_name}
        op=pd.DataFrame([base]*len(grid)); op[time_col]=grid
        for signal in signals: op[signal]=_approx_signal(times,piece[signal].to_numpy(float),grid,method)
        rows.append(op); log=dict(base); log.update({"n_input_rows":len(piece),"n_output_rows":len(grid),"time_min":start,"time_max":end,"interval":step,"method":method,"signals":",".join(signals)}); logs.append(log)
    if not rows: raise ValueError("No groups contained at least two finite time points.")
    out=pd.concat(rows,ignore_index=True); out.attrs["upsample_log"]=pd.DataFrame(logs); return out
