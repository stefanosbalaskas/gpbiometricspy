from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _coerce_data(data: Any, arg: str = "data") -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, (str, Path)):
        return pd.read_csv(data)
    raise TypeError(f"`{arg}` must be a data frame or CSV path.")


def _as_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def _numeric(x):
    return pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(float)


def _first_existing(names, candidates):
    names = list(names)
    for candidate in candidates:
        if candidate in names:
            return candidate
    lower = {str(name).lower(): name for name in names}
    for candidate in candidates:
        found = lower.get(str(candidate).lower())
        if found is not None:
            return found
    return None


def _group_key(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    if not cols:
        return np.repeat("all", len(df)).astype(object)
    z = df[cols].copy()
    for col in cols:
        z[col] = z[col].astype(object).where(z[col].notna(), "<NA>").astype(str)
    return z.astype(str).agg("||".join, axis=1).to_numpy(object)


def _empty_ttl_events(group_columns, time_columns):
    out = pd.DataFrame(
        {
            "row_index": pd.Series(dtype="int64"),
            "event_order": pd.Series(dtype="int64"),
            "ttl_channel": pd.Series(dtype="object"),
            "ttl_value": pd.Series(dtype="float64"),
            "previous_ttl_value": pd.Series(dtype="float64"),
        }
    )
    for col in reversed(_as_list(group_columns)):
        out.insert(0, col, pd.Series(dtype="object"))
    for col in time_columns:
        out[col] = pd.Series(dtype="float64")
    out["ttl_validity"] = pd.Series(dtype="float64")
    return out


def extract_gazepoint_ttl_events(
    data,
    ttl_columns=None,
    group_columns=None,
    validity_column="TTLV",
    require_validity=True,
    mode="changes",
    include_initial=True,
):
    """Extract TTL changes or non-zero TTL rows using the frozen R 2.0.0 rules."""
    dat = _coerce_data(data)
    if mode not in {"changes", "nonzero"}:
        raise ValueError("`mode` must be 'changes' or 'nonzero'.")

    if ttl_columns is None:
        ttl_columns = [f"TTL{i}" for i in range(7) if f"TTL{i}" in dat.columns]
    ttl_columns = _as_list(ttl_columns)
    if not ttl_columns:
        raise ValueError("No TTL columns were found in `data`.")
    missing = [c for c in ttl_columns if c not in dat.columns]
    if missing:
        raise ValueError("`ttl_columns` were not found in `data`: " + ", ".join(missing))

    groups = _as_list(group_columns)
    missing_groups = [c for c in groups if c not in dat.columns]
    if missing_groups:
        raise ValueError("`group_columns` were not found in `data`: " + ", ".join(missing_groups))
    keys = _group_key(dat, groups)
    time_columns = [c for c in ("CNT", "TIME", "TIME_TICK") if c in dat.columns]
    validity_present = validity_column is not None and validity_column in dat.columns

    rows = []
    event_order = 0
    # R unique() preserves first appearance.
    for key in pd.unique(keys):
        group_rows = np.flatnonzero(keys == key)
        if validity_present:
            validity = _numeric(dat.iloc[group_rows][validity_column])
        else:
            validity = np.full(len(group_rows), np.nan)
        if require_validity:
            valid_mask = np.full(len(group_rows), bool(validity_present), dtype=bool)
            valid_mask &= np.isfinite(validity) & (validity > 0)
        else:
            valid_mask = np.ones(len(group_rows), dtype=bool)

        for ttl_column in ttl_columns:
            ttl = _numeric(dat.iloc[group_rows][ttl_column])
            present = np.isfinite(ttl) & valid_mask
            if mode == "nonzero":
                positions = np.flatnonzero(present & (ttl != 0))
            else:
                flags = np.zeros(len(ttl), dtype=bool)
                previous = np.nan
                for i in range(len(ttl)):
                    if not present[i]:
                        continue
                    if not np.isfinite(previous):
                        flags[i] = bool(include_initial)
                    else:
                        flags[i] = ttl[i] != previous
                    previous = ttl[i]
                positions = np.flatnonzero(flags)

            for pos in positions:
                source_pos = int(group_rows[pos])
                prev_candidates = np.arange(pos, dtype=int)
                prev_candidates = prev_candidates[valid_mask[:pos] & np.isfinite(ttl[:pos])]
                previous_value = ttl[prev_candidates[-1]] if len(prev_candidates) else np.nan
                event_order += 1
                row = {}
                for col in groups:
                    row[col] = dat.iloc[source_pos][col]
                row.update(
                    {
                        "row_index": source_pos + 1,
                        "event_order": event_order,
                        "ttl_channel": ttl_column,
                        "ttl_value": ttl[pos],
                        "previous_ttl_value": previous_value,
                    }
                )
                for col in time_columns:
                    row[col] = dat.iloc[source_pos][col]
                row["ttl_validity"] = (
                    float(_numeric([dat.iloc[source_pos][validity_column]])[0])
                    if validity_present
                    else np.nan
                )
                rows.append(row)

    return pd.DataFrame(rows) if rows else _empty_ttl_events(groups, time_columns)


def _ttl_time_ms(dat: pd.DataFrame, time_col):
    if time_col is None:
        return np.full(len(dat), np.nan)
    x = _numeric(dat[time_col])
    if np.isnan(x).all():
        return np.full(len(dat), np.nan)
    diffs = np.diff(x)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if not len(diffs):
        return x
    return x * 1000.0 if np.median(diffs) <= 0.25 else x


def _ttl_active(series, event_value=None):
    s = pd.Series(series)
    if event_value is not None:
        allowed = {str(v) for v in _as_list(event_value)}
        return s.notna().to_numpy() & s.astype(str).isin(allowed).to_numpy()
    if pd.api.types.is_bool_dtype(s.dtype):
        return s.fillna(False).to_numpy(bool)
    if pd.api.types.is_numeric_dtype(s.dtype):
        x = pd.to_numeric(s, errors="coerce").to_numpy(float)
        return np.isfinite(x) & (x != 0)
    chars = s.astype("string").fillna("").str.strip()
    nums = pd.to_numeric(chars, errors="coerce")
    non_empty = chars.ne("")
    if int((nums.notna() & non_empty).sum()) >= max(1, int(non_empty.sum()) / 2):
        x = nums.to_numpy(float)
        return np.isfinite(x) & (x != 0)
    return (non_empty & ~chars.str.upper().isin(["0", "FALSE", "F", "NA", "NAN", "NULL"])).to_numpy(bool)


def _ttl_active_info(dat, ttl_cols, event_value=None):
    mats = np.column_stack([_ttl_active(dat[c], event_value) for c in ttl_cols])
    active = mats.sum(axis=1) > 0
    columns = np.full(len(dat), None, dtype=object)
    values = np.full(len(dat), None, dtype=object)
    for i in np.flatnonzero(active):
        active_cols = [ttl_cols[j] for j in range(len(ttl_cols)) if mats[i, j]]
        columns[i] = ";".join(active_cols)
        values[i] = ";".join(f"{c}={dat.iloc[i][c]}" for c in active_cols)
    return active, columns, values


def _empty_alignment_events(group_cols):
    columns = {c: pd.Series(dtype="object") for c in group_cols}
    columns.update(
        {
            "ttl_event_id": pd.Series(dtype="object"),
            "ttl_event_sequence": pd.Series(dtype="int64"),
            "event_row_id": pd.Series(dtype="int64"),
            "event_group_sample_index": pd.Series(dtype="int64"),
            "event_time_ms": pd.Series(dtype="float64"),
            "event_ttl_column": pd.Series(dtype="object"),
            "event_ttl_value": pd.Series(dtype="object"),
        }
    )
    return pd.DataFrame(columns)


def _empty_aligned(dat):
    out = dat.iloc[0:0].copy()
    additions = {
        "ttl_event_id": "object",
        "ttl_event_sequence": "int64",
        "event_row_id": "int64",
        "event_group_sample_index": "int64",
        "event_time_ms": "float64",
        "event_ttl_column": "object",
        "event_ttl_value": "object",
        "event_relative_sample_index": "int64",
        "event_relative_time_ms": "float64",
        "event_window_position": "object",
        "within_pre_event_window": "bool",
        "within_post_event_window": "bool",
        "ttl_alignment_status": "object",
    }
    for c, dtype in additions.items():
        out[c] = pd.Series(dtype=dtype)
    return out.drop(columns=[c for c in (".gpbiometrics_group_id", ".gpbiometrics_order_value") if c in out], errors="ignore")


def align_gazepoint_biometrics_to_ttl(
    data,
    ttl_cols=None,
    event_col=None,
    ttl_valid_col=None,
    time_col=None,
    sample_col=None,
    group_cols=None,
    participant_col=None,
    stimulus_col=None,
    trial_col=None,
    event_value=None,
    valid_values=(True, 1, "1"),
    event_edge="rising",
    pre_window_ms=1000,
    post_window_ms=5000,
    pre_window_samples=None,
    post_window_samples=None,
    collapse_nearby_ms=0,
    require_valid_ttl=True,
):
    """Align samples to TTL/event markers using the frozen R 2.0.0 contract."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    if event_edge not in {"rising", "change", "active"}:
        raise ValueError("`event_edge` must be 'rising', 'change', or 'active'.")
    for name, value in (("pre_window_ms", pre_window_ms), ("post_window_ms", post_window_ms), ("collapse_nearby_ms", collapse_nearby_ms)):
        if not isinstance(value, (int, float, np.number)) or not np.isfinite(value) or value < 0:
            raise ValueError(f"`{name}` must be a single non-negative number.")

    dat = data.copy()
    dat[".gpbiometrics_row_id"] = np.arange(1, len(dat) + 1)
    if dat.empty:
        return {
            "overview": pd.DataFrame([{"input_rows": 0, "ttl_event_rows": 0, "aligned_rows": 0, "group_count": 0, "status": "empty_input"}]),
            "events": _empty_alignment_events([]),
            "aligned_data": _empty_aligned(dat),
            "settings": {"ttl_cols": ttl_cols, "event_col": event_col, "ttl_valid_col": ttl_valid_col, "time_col": time_col, "sample_col": sample_col, "group_cols": group_cols, "event_edge": event_edge, "pre_window_ms": pre_window_ms, "post_window_ms": post_window_ms, "pre_window_samples": pre_window_samples, "post_window_samples": post_window_samples, "collapse_nearby_ms": collapse_nearby_ms, "require_valid_ttl": require_valid_ttl},
            "class": ["gazepoint_biometrics_ttl_alignment", "list"],
        }

    names = list(dat.columns)
    if event_col is not None:
        if event_col not in dat.columns:
            raise ValueError("`event_col` was not found in `data`.")
        ttl_cols = [event_col]
        event_source = "user_event_col"
    else:
        if ttl_cols is None:
            marker = _first_existing(names, ["ttl_marker"])
            ttl_cols = [marker] if marker is not None else sorted([c for c in names if str(c).lower() in {f"ttl{i}" for i in range(7)}], key=lambda x: str(x).lower())
        ttl_cols = _as_list(ttl_cols)
        if not ttl_cols:
            raise ValueError("No TTL/event columns were found. Supply `ttl_cols` or `event_col`.")
        missing = [c for c in ttl_cols if c not in dat.columns]
        if missing:
            raise ValueError("`ttl_cols` not found in `data`: " + ", ".join(missing))
        event_source = "ttl_cols"

    if ttl_valid_col is None:
        ttl_valid_col = _first_existing(names, ["ttl_validity_flag", "TTLV", "ttlv"])
    if ttl_valid_col is not None and ttl_valid_col not in dat.columns:
        raise ValueError("`ttl_valid_col` was not found in `data`.")
    if time_col is None:
        time_col = _first_existing(names, ["time_ms", "timestamp_ms", "timestamp", "TIME", "Time", "time", "recording_time", "sample_time"])
    if time_col is not None and time_col not in dat.columns:
        raise ValueError("`time_col` was not found in `data`.")
    if sample_col is None:
        sample_col = _first_existing(names, ["CNT", "cnt", "sample", "sample_index"])
    if sample_col is not None and sample_col not in dat.columns:
        raise ValueError("`sample_col` was not found in `data`.")

    explicit = [c for c in (participant_col, stimulus_col, trial_col) if c is not None]
    if group_cols is not None:
        groups = list(dict.fromkeys(_as_list(group_cols) + explicit))
    else:
        participant = _first_existing(names, ["participant", "subject", "subject_id", "USER", "USER_FILE", "user_file"])
        stimulus = _first_existing(names, ["stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name"])
        trial = _first_existing(names, ["trial", "trial_id", "TRIAL", "trial_global"])
        groups = list(dict.fromkeys([*explicit, *[x for x in (participant, stimulus, trial) if x is not None]]))
    missing = [c for c in groups if c not in dat.columns]
    if missing:
        raise ValueError("`group_cols` not found in `data`: " + ", ".join(missing))

    dat[".gpbiometrics_time_ms"] = _ttl_time_ms(dat, time_col)
    dat[".gpbiometrics_group_id"] = _group_key(dat, groups)
    order_value = dat[".gpbiometrics_row_id"].to_numpy(float)
    if not np.isnan(dat[".gpbiometrics_time_ms"].to_numpy(float)).all():
        order_value = dat[".gpbiometrics_time_ms"].to_numpy(float)
    elif sample_col is not None:
        sample_numeric = _numeric(dat[sample_col])
        if not np.isnan(sample_numeric).all():
            order_value = sample_numeric
    dat[".gpbiometrics_order_value"] = order_value
    dat[".gpbiometrics_group_sample_index"] = np.nan

    group_indices = {}
    for group_name in pd.unique(dat[".gpbiometrics_group_id"]):
        idx = np.flatnonzero(dat[".gpbiometrics_group_id"].to_numpy(object) == group_name)
        idx = idx[np.lexsort((dat.iloc[idx][".gpbiometrics_row_id"].to_numpy(), dat.iloc[idx][".gpbiometrics_order_value"].to_numpy()))]
        group_indices[str(group_name)] = idx
        dat.loc[dat.index[idx], ".gpbiometrics_group_sample_index"] = np.arange(1, len(idx) + 1)
    dat[".gpbiometrics_group_sample_index"] = dat[".gpbiometrics_group_sample_index"].astype(int)

    ttl_active, event_ttl_column, event_ttl_value = _ttl_active_info(dat, ttl_cols, event_value)
    ttl_valid = np.ones(len(dat), dtype=bool)
    if ttl_valid_col is not None and require_valid_ttl:
        allowed = {str(x) for x in _as_list(valid_values)}
        s = dat[ttl_valid_col]
        ttl_valid = s.notna().to_numpy() & s.astype(str).isin(allowed).to_numpy()
    event_active = ttl_active & ttl_valid

    event_rows = []
    for group_name, idx in group_indices.items():
        active = event_active[idx]
        vals = event_ttl_value[idx]
        lag_active = np.concatenate(([False], active[:-1]))
        lag_vals = np.concatenate(([None], vals[:-1]))
        if event_edge == "rising":
            flags = active & ~lag_active
        elif event_edge == "change":
            flags = active & (~lag_active | (vals != lag_vals))
        else:
            flags = active
        candidates = idx[flags]
        if len(candidates) > 1 and collapse_nearby_ms > 0:
            times = dat.iloc[candidates][".gpbiometrics_time_ms"].to_numpy(float)
            if not np.isnan(times).all():
                keep = np.ones(len(candidates), dtype=bool)
                last = times[0]
                for i in range(1, len(candidates)):
                    current = times[i]
                    if np.isfinite(current) and np.isfinite(last) and current - last < collapse_nearby_ms:
                        keep[i] = False
                    else:
                        last = current
                candidates = candidates[keep]
        event_rows.extend(candidates.tolist())

    settings = {"ttl_cols": ttl_cols, "event_col": event_col, "ttl_valid_col": ttl_valid_col, "time_col": time_col, "sample_col": sample_col, "group_cols": groups, "event_source": event_source, "event_edge": event_edge, "pre_window_ms": pre_window_ms, "post_window_ms": post_window_ms, "pre_window_samples": pre_window_samples, "post_window_samples": post_window_samples, "collapse_nearby_ms": collapse_nearby_ms, "require_valid_ttl": require_valid_ttl}
    if not event_rows:
        return {"overview": pd.DataFrame([{"input_rows": len(dat), "ttl_event_rows": 0, "aligned_rows": 0, "group_count": len(group_indices), "status": "no_ttl_events_detected"}]), "events": _empty_alignment_events(groups), "aligned_data": _empty_aligned(dat), "settings": settings, "class": ["gazepoint_biometrics_ttl_alignment", "list"]}

    event_rows = sorted(event_rows, key=lambda i: (str(dat.iloc[i][".gpbiometrics_group_id"]), float(dat.iloc[i][".gpbiometrics_order_value"]), int(dat.iloc[i][".gpbiometrics_row_id"])))
    sequence_by_group = {}
    event_records = []
    for n, row_pos in enumerate(event_rows, start=1):
        gid = str(dat.iloc[row_pos][".gpbiometrics_group_id"])
        sequence_by_group[gid] = sequence_by_group.get(gid, 0) + 1
        rec = {c: dat.iloc[row_pos][c] for c in groups}
        rec.update({"ttl_event_id": f"ttl_event_{n}", "ttl_event_sequence": sequence_by_group[gid], "event_row_id": int(dat.iloc[row_pos][".gpbiometrics_row_id"]), "event_group_id": gid, "event_group_sample_index": int(dat.iloc[row_pos][".gpbiometrics_group_sample_index"]), "event_time_ms": float(dat.iloc[row_pos][".gpbiometrics_time_ms"]), "event_ttl_column": event_ttl_column[row_pos], "event_ttl_value": event_ttl_value[row_pos]})
        event_records.append(rec)
    events_internal = pd.DataFrame(event_records)

    aligned_parts = []
    for i, event in events_internal.iterrows():
        group_rows = group_indices[str(event.event_group_id)]
        rel_sample = dat.iloc[group_rows][".gpbiometrics_group_sample_index"].to_numpy(int) - int(event.event_group_sample_index)
        rel_time = dat.iloc[group_rows][".gpbiometrics_time_ms"].to_numpy(float) - float(event.event_time_ms)
        if np.isfinite(rel_time).any() and np.isfinite(float(event.event_time_ms)):
            keep = np.isfinite(rel_time) & (rel_time >= -pre_window_ms) & (rel_time <= post_window_ms)
        else:
            pre_s = 0 if pre_window_samples is None else pre_window_samples
            post_s = 0 if post_window_samples is None else post_window_samples
            for name, value in (("pre_window_samples", pre_s), ("post_window_samples", post_s)):
                if not isinstance(value, (int, float, np.number)) or not np.isfinite(value) or value < 0:
                    raise ValueError(f"`{name}` must be `NULL` or a single non-negative number.")
            keep = (rel_sample >= -pre_s) & (rel_sample <= post_s)
        kept = group_rows[keep]
        if not len(kept):
            continue
        block = dat.iloc[kept].copy()
        block["ttl_event_id"] = event.ttl_event_id
        block["ttl_event_sequence"] = int(event.ttl_event_sequence)
        block["event_row_id"] = int(event.event_row_id)
        block["event_group_sample_index"] = int(event.event_group_sample_index)
        block["event_time_ms"] = float(event.event_time_ms)
        block["event_ttl_column"] = event.event_ttl_column
        block["event_ttl_value"] = event.event_ttl_value
        block["event_relative_sample_index"] = rel_sample[keep]
        block["event_relative_time_ms"] = rel_time[keep]
        block["event_window_position"] = np.where(block["event_relative_sample_index"] < 0, "pre_event", np.where(block["event_relative_sample_index"] == 0, "event", "post_event"))
        block["within_pre_event_window"] = block["event_relative_sample_index"] < 0
        block["within_post_event_window"] = block["event_relative_sample_index"] > 0
        block["ttl_alignment_status"] = "aligned"
        aligned_parts.append(block)
    if aligned_parts:
        aligned = pd.concat(aligned_parts, ignore_index=True)
        status = "ttl_events_aligned"
    else:
        aligned = _empty_aligned(dat)
        status = "ttl_events_detected_no_rows_aligned"
    aligned = aligned.drop(columns=[c for c in (".gpbiometrics_group_id", ".gpbiometrics_order_value") if c in aligned], errors="ignore")
    events = events_internal.drop(columns=["event_group_id"])
    overview = pd.DataFrame([{"input_rows": len(dat), "ttl_event_rows": len(events), "aligned_rows": len(aligned), "group_count": len(group_indices), "status": status}])
    return {"overview": overview, "events": events, "aligned_data": aligned, "settings": settings, "class": ["gazepoint_biometrics_ttl_alignment", "list"]}


_BIOMETRIC_JOIN_COLUMNS = [
    "DIAL", "DIALV", "GSR", "GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSRV",
    "HR", "HRV", "HRP", "IBI", *[f"TTL{i}" for i in range(7)], "TTLV",
]


def sync_gazepoint_biometrics_with_gaze(biometrics, gaze, by, all_x=True, suffixes=(".gaze", ".bio")):
    """Exact-key synchronization; intentionally no interpolation or nearest matching."""
    bio = _coerce_data(biometrics, "biometrics")
    if not isinstance(gaze, pd.DataFrame):
        raise TypeError("`gaze` must be a data frame.")
    keys = _as_list(by)
    if not keys or not all(isinstance(c, str) for c in keys):
        raise ValueError("`by` must be a non-empty character vector of join columns.")
    missing_bio = [c for c in keys if c not in bio.columns]
    missing_gaze = [c for c in keys if c not in gaze.columns]
    if missing_bio:
        raise ValueError("`by` columns were not found in `biometrics`: " + ", ".join(missing_bio))
    if missing_gaze:
        raise ValueError("`by` columns were not found in `gaze`: " + ", ".join(missing_gaze))
    present = [c for c in _BIOMETRIC_JOIN_COLUMNS if c in bio.columns]
    keep_bio = list(dict.fromkeys(keys + present))
    out = gaze.merge(bio[keep_bio], how="left" if all_x else "inner", on=keys, sort=False, suffixes=tuple(suffixes))
    out.attrs["sync_summary"] = pd.DataFrame([{"n_gaze_rows": len(gaze), "n_biometric_rows": len(bio), "n_output_rows": len(out), "join_keys": ",".join(keys), "all_x": bool(all_x), "biometric_columns_joined": ",".join([c for c in keep_bio if c not in keys])}])
    out.attrs["class"] = ["gazepoint_biometrics_sync", "data.frame"]
    return out


def join_gazepoint_biometrics_to_master(master, biometrics, by, all_x=True):
    return sync_gazepoint_biometrics_with_gaze(biometrics=biometrics, gaze=master, by=by, all_x=all_x)


def chunk_gazepoint_biometrics(
    dat,
    time_col="CNT",
    group_cols=None,
    chunk_seconds=60,
    start_time=None,
    chunk_col="chunk_id",
    episode_col="episode_id",
    include_partial=False,
):
    if not isinstance(dat, pd.DataFrame):
        raise TypeError("`dat` must be a data frame.")
    if time_col not in dat.columns:
        raise ValueError(f"Column `{time_col}` was not found in `dat`.")
    if not pd.api.types.is_numeric_dtype(dat[time_col]):
        raise TypeError("`time_col` must identify a numeric column.")
    if not isinstance(chunk_seconds, (int, float, np.number)) or not np.isfinite(chunk_seconds) or chunk_seconds <= 0:
        raise ValueError("`chunk_seconds` must be a positive number.")
    groups = _as_list(group_cols)
    missing = [c for c in groups if c not in dat.columns]
    if missing:
        raise ValueError("Missing `group_cols`: " + ", ".join(missing))

    out = dat.copy()
    out[chunk_col] = pd.Series([pd.NA] * len(out), dtype="Int64")
    out[episode_col] = pd.Series([pd.NA] * len(out), dtype="string")
    out["chunk_start"] = np.nan
    out["chunk_end"] = np.nan
    out["chunk_midpoint"] = np.nan
    out["chunk_complete"] = False
    if groups:
        z = out[groups].copy()
        for c in groups:
            z[c] = z[c].astype(object).where(z[c].notna(), "<NA>").astype(str)
        labels = z.astype(str).agg(" | ".join, axis=1)
        ordered_labels = pd.unique(labels)
        split = [(str(label), np.flatnonzero(labels.to_numpy(object) == label)) for label in ordered_labels]
    else:
        split = [("all_rows", np.arange(len(out), dtype=int))]

    summaries = []
    for group_id, idx in split:
        time = _numeric(out.iloc[idx][time_col])
        finite = np.isfinite(time)
        if not finite.any():
            continue
        gstart = float(start_time) if start_time is not None else float(np.min(time[finite]))
        raw_chunk = np.floor((time - gstart) / float(chunk_seconds)) + 1
        raw_chunk[~np.isfinite(raw_chunk) | (raw_chunk < 1)] = np.nan
        for cid_float in sorted(pd.unique(raw_chunk[np.isfinite(raw_chunk)])):
            cid = int(cid_float)
            local_mask = raw_chunk == cid_float
            chunk_idx = idx[local_mask]
            cstart = gstart + (cid - 1) * float(chunk_seconds)
            cend = cstart + float(chunk_seconds)
            ctime = _numeric(out.iloc[chunk_idx][time_col])
            complete = bool(np.nanmax(ctime) >= cend or include_partial)
            if complete or include_partial:
                out.loc[out.index[chunk_idx], chunk_col] = cid
                out.loc[out.index[chunk_idx], episode_col] = f"{group_id}_chunk_{cid}"
            else:
                out.loc[out.index[chunk_idx], chunk_col] = pd.NA
                out.loc[out.index[chunk_idx], episode_col] = pd.NA
            out.loc[out.index[chunk_idx], "chunk_start"] = cstart
            out.loc[out.index[chunk_idx], "chunk_end"] = cend
            out.loc[out.index[chunk_idx], "chunk_midpoint"] = (cstart + cend) / 2
            out.loc[out.index[chunk_idx], "chunk_complete"] = complete
            summaries.append({"group_id": group_id, "chunk_id": cid, "episode_id": f"{group_id}_chunk_{cid}", "chunk_start": cstart, "chunk_end": cend, "chunk_midpoint": (cstart + cend) / 2, "row_count": len(chunk_idx), "observed_start": float(np.nanmin(ctime)), "observed_end": float(np.nanmax(ctime)), "complete": complete, "assigned": bool(complete or include_partial)})

    summary = pd.DataFrame(summaries)
    assigned_chunks = int(summary["assigned"].sum()) if len(summary) else 0
    out.attrs["chunk_overview"] = pd.DataFrame([{"input_rows": len(dat), "output_rows": len(out), "group_count": len(split), "chunk_rows": len(summary), "assigned_chunks": assigned_chunks, "chunk_seconds": chunk_seconds, "include_partial": bool(include_partial), "status": "biometric_chunks_created"}])
    out.attrs["chunk_summary"] = summary
    out.attrs["chunk_settings"] = {"time_col": time_col, "group_cols": groups, "chunk_seconds": chunk_seconds, "start_time": start_time, "chunk_col": chunk_col, "episode_col": episode_col, "include_partial": bool(include_partial)}
    out.attrs["class"] = ["gazepoint_biometric_chunks", "data.frame"]
    return out
