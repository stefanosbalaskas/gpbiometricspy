from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


_EXPECTED_ROWS = [
    ("DIAL", "engagement_dial", "dial_value"),
    ("DIALV", "engagement_dial", "dial_validity"),
    ("GSR", "gsr_eda", "gsr_raw_or_resistance"),
    ("GSR_US", "gsr_eda", "gsr_conductance_microsiemens"),
    ("GSR_US_TONIC", "gsr_eda", "gsr_tonic_component"),
    ("GSR_US_PHASIC", "gsr_eda", "gsr_phasic_component"),
    ("GSRV", "gsr_eda", "gsr_validity"),
    ("HR", "heart_rate", "heart_rate_bpm"),
    ("HRV", "heart_rate", "heart_rate_validity_not_hrv_metric"),
    ("HRP", "heart_rate", "pulse_signal"),
    ("IBI", "heart_rate", "interbeat_interval_seconds"),
    *[(f"TTL{i}", "ttl_marker", "ttl_channel") for i in range(7)],
    ("TTLV", "ttl_marker", "ttl_validity"),
    ("CNT", "time_identity_sync", "sample_counter"),
    ("TIME", "time_identity_sync", "recording_time"),
    ("TIME_TICK", "time_identity_sync", "recording_tick"),
    ("USER", "time_identity_sync", "user_label"),
    ("USERID", "time_identity_sync", "user_identifier"),
    ("MEDIA_ID", "time_identity_sync", "media_identifier"),
    ("MEDIA_NAME", "time_identity_sync", "media_name"),
    ("FPOGX", "fixation_gaze", "fixation_x"),
    ("FPOGY", "fixation_gaze", "fixation_y"),
    ("FPOGS", "fixation_gaze", "fixation_start_time"),
    ("FPOGD", "fixation_gaze", "fixation_duration"),
    ("FPOGID", "fixation_gaze", "fixation_identifier"),
]


def check_gazepoint_biometric_columns(data):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    out = pd.DataFrame(_EXPECTED_ROWS, columns=["column", "signal", "role"])
    out["present"] = out["column"].isin(data.columns)
    return out


def _num(series):
    return pd.to_numeric(series, errors="coerce").to_numpy(float)


def _detect_one(data, signal, values, validity):
    present_values = [c for c in values if c in data.columns]
    present_validity = [c for c in validity if c in data.columns]
    present = bool(present_values or present_validity)
    if not present:
        return {"signal": signal, "present": False, "active": False, "value_columns": np.nan,
                "summary_column": np.nan, "validity_columns": np.nan, "valid_rows": 0,
                "nonzero_rows": 0, "min_value": np.nan, "max_value": np.nan}
    priority = {
        "gsr_eda": ["GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "GSR"],
        "heart_rate": ["HR", "IBI", "HRP"],
        "engagement_dial": ["DIAL"],
        "ttl_marker": [f"TTL{i}" for i in range(7)],
    }.get(signal, present_values)
    summary = next((c for c in priority if c in present_values), present_values[0] if present_values else None)
    x = _num(data[summary]) if summary is not None else np.full(len(data), np.nan)
    valid = np.isfinite(x)
    if present_validity:
        matrix = np.column_stack([_num(data[c]) for c in present_validity])
        valid &= np.any(np.isfinite(matrix) & (matrix > 0), axis=1)
    nonzero = np.isfinite(x) & (x != 0)
    usable = x[valid & np.isfinite(x)]
    return {
        "signal": signal,
        "present": True,
        "active": bool(np.any(nonzero & valid)),
        "value_columns": ",".join(present_values),
        "summary_column": summary if summary is not None else np.nan,
        "validity_columns": ",".join(present_validity) if present_validity else np.nan,
        "valid_rows": int(valid.sum()),
        "nonzero_rows": int(nonzero.sum()),
        "min_value": float(np.min(usable)) if len(usable) else np.nan,
        "max_value": float(np.max(usable)) if len(usable) else np.nan,
    }


def detect_active_biometric_channels(data):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    return pd.DataFrame([
        _detect_one(data, "gsr_eda", ["GSR_US", "GSR", "GSR_US_TONIC", "GSR_US_PHASIC"], ["GSRV"]),
        _detect_one(data, "heart_rate", ["HR", "IBI", "HRP"], ["HRV"]),
        _detect_one(data, "engagement_dial", ["DIAL"], ["DIALV"]),
        _detect_one(data, "ttl_marker", [f"TTL{i}" for i in range(7)], ["TTLV"]),
    ])


def _drop_empty_trailing_columns(data):
    drops = []
    for c in data.columns:
        empty_name = c is None or str(c) == "" or str(c).lower().startswith("unnamed:")
        if not empty_name:
            continue
        s = data[c]
        empty_values = (s.isna() | s.astype("string").fillna("").str.strip().eq("")).all()
        if empty_values:
            drops.append(c)
    return data.drop(columns=drops) if drops else data


def import_gazepoint_biometrics(file, na=("", "NA", "NaN")):
    if not isinstance(file, (str, Path)) or not str(file):
        raise ValueError("`file` must be a single non-empty file path.")
    path = Path(file)
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    dat = pd.read_csv(path, na_values=list(na), keep_default_na=True)
    dat = _drop_empty_trailing_columns(dat)
    dat.attrs["biometric_columns"] = check_gazepoint_biometric_columns(dat)
    dat.attrs["class"] = ["gazepoint_biometrics", "data.frame"]
    return dat


def _candidate_files(files, include_fixations=True, include_all_gaze=True, include_other_csv=False):
    kept = []
    for file in files:
        name = file.name.lower()
        if "data_summary" in name:
            continue
        is_fix = "fixation" in name
        is_gaze = "all_gaze" in name
        if (include_fixations and is_fix) or (include_all_gaze and is_gaze) or include_other_csv:
            kept.append(file)
    return kept


def _source_type(name):
    x = name.lower()
    if "all_gaze" in x:
        return "all_gaze"
    if "fixation" in x:
        return "fixations"
    if "data_summary" in x:
        return "data_summary"
    return "other"


def _source_participant(name):
    x = Path(name).name
    x = re.sub(r"\.csv$", "", x, flags=re.I)
    x = re.sub(r"_all_gaze$", "", x, flags=re.I)
    x = re.sub(r"_fixations?$", "", x, flags=re.I)
    return x.strip()


def import_gazepoint_biometric_folder(path, pattern=r"\.csv$", recursive=False,
                                      include_fixations=True, include_all_gaze=True,
                                      include_other_csv=False, na=("", "NA", "NaN")):
    if not isinstance(path, (str, Path)) or not str(path):
        raise ValueError("`path` must be a single non-empty folder path.")
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(f"Folder does not exist: {root}")
    iterator = root.rglob("*") if recursive else root.glob("*")
    regex = re.compile(pattern, flags=re.I)
    files = sorted([p for p in iterator if p.is_file() and regex.search(p.name)])
    if not files:
        raise ValueError(f"No CSV files were found in: {root}")
    candidates = _candidate_files(files, include_fixations, include_all_gaze, include_other_csv)
    if not candidates:
        raise ValueError("No candidate Gazepoint biometric CSV files were found.")
    imported = []
    for file in candidates:
        dat = import_gazepoint_biometrics(file, na=na)
        cols = check_gazepoint_biometric_columns(dat)
        if not cols.loc[cols.signal.isin(["gsr_eda", "heart_rate", "engagement_dial", "ttl_marker"]), "present"].any():
            continue
        # Avoid pandas comparing DataFrame-valued attrs during concat.
        dat = dat.copy()
        dat.attrs = {}
        dat["source_file"] = file.name
        dat["source_type"] = _source_type(file.name)
        dat["source_participant"] = _source_participant(file.name)
        imported.append(dat)
    if not imported:
        raise ValueError("CSV files were found, but none contained known Gazepoint Biometrics columns.")
    all_names = list(dict.fromkeys(c for frame in imported for c in frame.columns))
    aligned = [frame.reindex(columns=all_names) for frame in imported]
    out = pd.concat(aligned, ignore_index=True)
    out.attrs["source_files"] = [p.name for p in candidates]
    out.attrs["biometric_columns"] = check_gazepoint_biometric_columns(out)
    out.attrs["active_channels"] = detect_active_biometric_channels(out)
    out.attrs["class"] = ["gazepoint_biometrics_folder", "gazepoint_biometrics", "data.frame"]
    return out


def _coerce(data):
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, (str, Path)) and str(data):
        return import_gazepoint_biometrics(data)
    raise TypeError("`data` must be a data frame or a single path to a Gazepoint CSV export.")


def validate_gazepoint_biometrics(data, require_active_signal=False):
    dat = _coerce(data)
    cols = check_gazepoint_biometric_columns(dat)
    active = detect_active_biometric_channels(dat)
    bio_signals = ["gsr_eda", "heart_rate", "engagement_dial"]
    marker_signals = bio_signals + ["ttl_marker"]
    has_known = bool(cols.loc[cols.signal.isin(marker_signals), "present"].any())
    active_count = int(active.loc[active.signal.isin(bio_signals), "active"].sum())
    present_time = [c for c in ("CNT", "TIME", "TIME_TICK") if c in dat.columns]
    issues = []
    if len(dat) == 0:
        issues.append({"issue": "empty_data", "severity": "error", "details": "The data contain zero rows."})
    empty_names = [c for c in dat.columns if c is None or str(c) == ""]
    if empty_names:
        issues.append({"issue": "empty_column_names", "severity": "warning", "details": f"{len(empty_names)} column name(s) are empty or missing."})
    if not has_known:
        issues.append({"issue": "no_known_biometric_columns", "severity": "error", "details": "No known Gazepoint Biometrics columns were detected."})
    if not present_time:
        issues.append({"issue": "no_time_columns", "severity": "warning", "details": "No common Gazepoint time columns were detected: CNT, TIME, or TIME_TICK."})
    if require_active_signal and active_count == 0:
        issues.append({"issue": "no_active_biometric_signal", "severity": "warning", "details": "Biometric columns are present, but no active GSR/EDA, heart-rate, or engagement-dial signal was detected."})
    issue_df = pd.DataFrame(issues, columns=["issue", "severity", "details"])
    overview = pd.DataFrame([{"n_rows": len(dat), "n_columns": len(dat.columns),
                              "known_biometric_columns": int(cols.loc[cols.signal.isin(marker_signals), "present"].sum()),
                              "active_signal_count": active_count, "present_time_columns": ",".join(present_time),
                              "issue_count": len(issue_df)}])
    return {"overview": overview, "columns": cols, "active_channels": active, "issues": issue_df,
            "class": ["gazepoint_biometrics_validation", "list"]}


def audit_gazepoint_biometric_missingness(data, columns=None):
    dat = _coerce(data)
    cols = check_gazepoint_biometric_columns(dat)
    if columns is None:
        columns = cols.loc[cols.present & cols.signal.isin(["gsr_eda", "heart_rate", "engagement_dial", "ttl_marker"]), "column"].tolist()
    elif isinstance(columns, str):
        columns = [columns]
    elif not isinstance(columns, (list, tuple, pd.Index, np.ndarray)):
        raise TypeError("`columns` must be a character vector or NULL.")
    columns = [c for c in columns if c in dat.columns]
    fields = ["column", "signal", "role", "n_rows", "missing_rows", "missing_pct", "zero_rows", "zero_pct", "min_value", "max_value"]
    rows = []
    lookup = cols.set_index("column")
    for c in columns:
        s = dat[c]
        chars = s.astype("string").fillna("").str.strip()
        nums = pd.to_numeric(s, errors="coerce").to_numpy(float)
        missing = s.isna().to_numpy() | chars.eq("").to_numpy()
        zero = np.isfinite(nums) & (nums == 0)
        finite = nums[np.isfinite(nums)]
        meta = lookup.loc[c] if c in lookup.index else None
        rows.append({"column": c, "signal": meta.signal if meta is not None else "unknown",
                     "role": meta.role if meta is not None else "unknown", "n_rows": len(dat),
                     "missing_rows": int(missing.sum()), "missing_pct": 100*missing.sum()/len(dat) if len(dat) else np.nan,
                     "zero_rows": int(zero.sum()), "zero_pct": 100*zero.sum()/len(dat) if len(dat) else np.nan,
                     "min_value": float(np.min(finite)) if len(finite) else np.nan,
                     "max_value": float(np.max(finite)) if len(finite) else np.nan})
    return pd.DataFrame(rows, columns=fields)
