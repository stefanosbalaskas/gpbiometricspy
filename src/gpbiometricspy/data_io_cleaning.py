from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd


class GazepointSessionData(OrderedDict):
    """Named mapping of Gazepoint session exports with R-style metadata."""

    def __init__(self, *args, dir=None, session=None, file_index=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dir = dir
        self.session = session
        self.file_index = file_index
        self.attrs = {
            "dir": dir,
            "session": session,
            "file_index": file_index,
            "class": ["gazepoint_session_data", "list"],
        }


def _clean_path(value) -> str:
    return Path(value).resolve(strict=False).as_posix()


def _guess_delimiter(path: Path) -> str:
    try:
        first = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    except (IndexError, OSError):
        return ","
    counts = {",": first.count(","), ";": first.count(";"), "\t": first.count("\t")}
    # R which.max() selects the first maximum in comma, semicolon, tab order.
    return max(counts, key=counts.get) if any(counts.values()) else ","


def _detect_type(path: Path) -> str:
    name = path.name.lower()
    if re.search(r"all[_ -]?gaze|allgaze", name):
        return "all_gaze"
    if re.search(r"fixation|fixations", name):
        return "fixations"
    if "summary" in name:
        return "summary"
    if re.search(r"biometric|gsr|eda|ppg|bvp|heart|hr|ibi|rri", name):
        return "biometrics"
    if re.search(r"marker|trigger|ttl|event", name):
        return "markers"
    return "unknown"


def _safe_name(path: Path, session=None) -> str:
    name = path.stem
    sessions = [] if session is None else ([session] if isinstance(session, str) else list(session))
    for ss in sessions:
        name = re.sub(rf"^{re.escape(str(ss))}([_ -]+)?", "", name, flags=re.I)
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "gazepoint_file"


def _make_unique(names):
    used = set()
    out = []
    for raw in names:
        candidate = raw
        if candidate in used:
            i = 1
            while f"{raw}_{i}" in used:
                i += 1
            candidate = f"{raw}_{i}"
        used.add(candidate)
        out.append(candidate)
    return out


def _session_keep(files, session=None, session_match="prefix"):
    if session_match not in {"prefix", "contains", "regex"}:
        raise ValueError("`session_match` must be one of: prefix, contains, regex.")
    sessions = [] if session is None else ([session] if isinstance(session, str) else list(session))
    sessions = [str(x) for x in sessions if str(x)]
    if not sessions:
        return [True] * len(files)
    result = []
    for path in files:
        base = path.name
        keep = False
        for ss in sessions:
            if session_match == "regex":
                keep |= re.search(ss, base, flags=re.I) is not None
            elif session_match == "prefix":
                keep |= re.search(rf"^{re.escape(ss)}", base, flags=re.I) is not None
            else:
                keep |= re.search(re.escape(ss), base, flags=re.I) is not None
        result.append(keep)
    return result


def _read_csv(path: Path, file_encoding="UTF-8-BOM"):
    sep = _guess_delimiter(path)
    encoding = "utf-8-sig" if str(file_encoding).upper() == "UTF-8-BOM" else file_encoding
    return pd.read_csv(
        path,
        sep=sep,
        encoding=encoding,
        na_values=["", "NA", "NaN", "N/A", "NULL", "null"],
        keep_default_na=True,
    )


def import_gazepoint_data(
    dir,
    session=None,
    pattern=r"\.csv$",
    recursive=False,
    session_match="prefix",
    file_encoding="UTF-8-BOM",
    add_file_info=True,
):
    """Import Gazepoint-style exports from a session directory.

    This is a direct Python counterpart of the R 2.0.0 session-folder importer.
    The returned ordered mapping exposes ``file_index`` and related metadata as
    attributes, analogous to the R ``gazepoint_session_data`` list attributes.
    """
    if dir is None or not str(dir):
        raise ValueError("Supply `dir`, the folder containing Gazepoint export files.")
    root = Path(dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Folder does not exist: {dir}")
    try:
        regex = re.compile(pattern, flags=re.I)
    except re.error as exc:
        raise ValueError(f"Invalid `pattern`: {exc}") from exc
    iterator = root.rglob("*") if recursive else root.glob("*")
    files = sorted(p for p in iterator if p.is_file() and regex.search(p.name))
    if not files:
        raise ValueError(f"No files matching `pattern` were found in: {dir}")
    keep = _session_keep(files, session=session, session_match=session_match)
    files = [p for p, flag in zip(files, keep) if flag]
    if not files:
        raise ValueError(f"No files matched `session` in: {dir}")

    names = _make_unique([_safe_name(p, session=session) for p in files])
    rows = []
    result = GazepointSessionData(dir=_clean_path(root), session=session)
    for i, (name, path) in enumerate(zip(names, files), start=1):
        dat = _read_csv(path, file_encoding=file_encoding)
        if add_file_info:
            dat["gp_source_file"] = _clean_path(path)
            dat["gp_source_basename"] = path.name
            dat["gp_source_index"] = i
        result[name] = dat
        rows.append(
            {
                "element": name,
                "file": _clean_path(path),
                "basename": path.name,
                "detected_type": _detect_type(path),
                "rows": int(len(dat)),
                "columns": int(dat.shape[1]),
            }
        )
    index = pd.DataFrame(rows)
    result.file_index = index
    result.attrs["file_index"] = index
    return result


def _allowed_missing(missing: np.ndarray, max_gap):
    missing = np.asarray(missing, dtype=bool)
    if not missing.any():
        return np.zeros(len(missing), dtype=bool)
    if np.isinf(max_gap):
        return missing.copy()
    allowed = np.zeros(len(missing), dtype=bool)
    start = None
    for i, flag in enumerate(np.r_[missing, False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start <= int(max_gap):
                allowed[start:i] = True
            start = None
    return allowed


def _locf(values):
    out = np.asarray(values, dtype=float).copy()
    last = np.nan
    for i in range(len(out)):
        if np.isnan(out[i]):
            out[i] = last
        else:
            last = out[i]
    return out


def _nocb(values):
    return _locf(np.asarray(values, dtype=float)[::-1])[::-1]


def _impute_vector(
    values,
    time=None,
    method="linear",
    max_gap=np.inf,
    fill_edges=True,
    constant_value=0,
    treat_infinite_as_missing=True,
):
    original = np.asarray(values)
    try:
        x = original.astype(float, copy=True)
    except (TypeError, ValueError):
        x = pd.to_numeric(pd.Series(original), errors="coerce").to_numpy(float)
    if time is None:
        tt = np.arange(1, len(x) + 1, dtype=float)
    else:
        tt = pd.to_numeric(pd.Series(time), errors="coerce").to_numpy(float)
        if len(tt) != len(x) or not np.isfinite(tt).all():
            tt = np.arange(1, len(x) + 1, dtype=float)
    missing = np.isnan(x)
    if treat_infinite_as_missing:
        missing |= ~np.isfinite(x)
    x[missing] = np.nan
    allowed = _allowed_missing(missing, max_gap)
    disallowed = missing & ~allowed
    if not allowed.any():
        return x, np.zeros(len(x), dtype=bool)
    observed = ~np.isnan(x)
    if not observed.any():
        if method == "constant":
            out = x.copy()
            out[allowed] = constant_value
            return out, allowed
        warnings.warn("Cannot impute a signal with no observed values.", RuntimeWarning, stacklevel=2)
        return x, np.zeros(len(x), dtype=bool)

    if method == "constant":
        out = x.copy()
        out[allowed] = constant_value
    elif method == "linear":
        out = x.copy()
        if observed.sum() == 1:
            fitted = np.full(len(x), x[observed][0], dtype=float)
        else:
            fitted = np.interp(tt, tt[observed], x[observed])
            if not fill_edges:
                fitted[tt < np.min(tt[observed])] = np.nan
                fitted[tt > np.max(tt[observed])] = np.nan
        out[allowed] = fitted[allowed]
    elif method == "locf":
        fitted = _locf(x)
        if fill_edges:
            fitted = _nocb(fitted)
        out = x.copy()
        out[allowed] = fitted[allowed]
    elif method == "nocb":
        fitted = _nocb(x)
        if fill_edges:
            fitted = _locf(fitted)
        out = x.copy()
        out[allowed] = fitted[allowed]
    elif method == "nearest":
        out = x.copy()
        observed_idx = np.flatnonzero(observed)
        for i in np.flatnonzero(allowed):
            lefts = observed_idx[observed_idx < i]
            rights = observed_idx[observed_idx > i]
            left = lefts[-1] if len(lefts) else None
            right = rights[0] if len(rights) else None
            if left is None and right is None:
                out[i] = np.nan
            elif left is None:
                out[i] = x[right]
            elif right is None:
                out[i] = x[left]
            else:
                out[i] = x[left] if abs(tt[i] - tt[left]) <= abs(tt[right] - tt[i]) else x[right]
    else:
        raise ValueError("`method` must be one of: linear, locf, nocb, nearest, constant.")
    out[disallowed] = np.nan
    # R flags only originally-NA values; Inf may be replaced but is not counted
    # by `is.na(original)`. Preserve that subtle behavior.
    original_na = pd.isna(pd.Series(original)).to_numpy(bool)
    return out, allowed & original_na


def impute_gazepoint_missing(
    data,
    method="linear",
    cols=None,
    time_col=None,
    group_cols=None,
    max_gap=np.inf,
    fill_edges=True,
    constant_value=0,
    add_flags=True,
    treat_infinite_as_missing=True,
):
    """Impute missing Gazepoint signal values with R 2.0.0 semantics."""
    methods = {"linear", "locf", "nocb", "nearest", "constant"}
    if method not in methods:
        raise ValueError("`method` must be one of: linear, locf, nocb, nearest, constant.")
    try:
        gap = float(max_gap)
    except (TypeError, ValueError) as exc:
        raise ValueError("`max_gap` must be a non-negative number or Inf.") from exc
    if np.isnan(gap) or gap < 0:
        raise ValueError("`max_gap` must be a non-negative number or Inf.")
    max_gap = np.inf if np.isinf(gap) else int(gap)

    if isinstance(data, pd.Series) and pd.api.types.is_numeric_dtype(data):
        values, _ = _impute_vector(data.to_numpy(), method=method, max_gap=max_gap,
                                   fill_edges=fill_edges, constant_value=constant_value,
                                   treat_infinite_as_missing=treat_infinite_as_missing)
        return pd.Series(values, index=data.index, name=data.name)
    if isinstance(data, (list, tuple, np.ndarray)):
        arr = np.asarray(data)
        if arr.ndim != 1:
            raise TypeError("`data` must be a numeric vector or data frame.")
        values, _ = _impute_vector(arr, method=method, max_gap=max_gap,
                                   fill_edges=fill_edges, constant_value=constant_value,
                                   treat_infinite_as_missing=treat_infinite_as_missing)
        return values
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a numeric vector or data frame.")

    out = data.copy()
    groups = [] if group_cols is None else ([group_cols] if isinstance(group_cols, str) else list(group_cols))
    if groups:
        missing = [c for c in groups if c not in out.columns]
        if missing:
            raise ValueError("Missing grouping columns: " + ", ".join(missing))
    if time_col is not None and time_col not in out.columns:
        raise ValueError("`time_col` not found in `data`.")
    if cols is None:
        cols = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c]) and c not in set(groups + ([time_col] if time_col else []))]
    elif isinstance(cols, str):
        cols = [cols]
    else:
        cols = list(cols)
    if not cols:
        raise ValueError("No columns selected for imputation.")
    missing = [c for c in cols if c not in out.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    non_numeric = [c for c in cols if not pd.api.types.is_numeric_dtype(out[c])]
    if non_numeric:
        raise ValueError("Selected columns must be numeric: " + ", ".join(non_numeric))

    if groups:
        group_indices = [np.asarray(idx, dtype=int) for idx in out.groupby(groups, sort=True, dropna=True).indices.values()]
    else:
        group_indices = [np.arange(len(out), dtype=int)]
    summaries = []
    for col in cols:
        flag = np.zeros(len(out), dtype=bool)
        numeric = pd.to_numeric(out[col], errors="coerce").to_numpy(float)
        before_mask = np.isnan(numeric) | ((~np.isfinite(numeric)) if treat_infinite_as_missing else False)
        before = int(np.sum(before_mask))
        for idx in group_indices:
            tt = out.iloc[idx][time_col].to_numpy() if time_col is not None else None
            values, imputed = _impute_vector(
                out.iloc[idx][col].to_numpy(), time=tt, method=method, max_gap=max_gap,
                fill_edges=fill_edges, constant_value=constant_value,
                treat_infinite_as_missing=treat_infinite_as_missing,
            )
            col_loc = out.columns.get_loc(col)
            out.iloc[idx, col_loc] = values
            flag[idx] = imputed
        numeric_after = pd.to_numeric(out[col], errors="coerce").to_numpy(float)
        after_mask = np.isnan(numeric_after) | ((~np.isfinite(numeric_after)) if treat_infinite_as_missing else False)
        if add_flags:
            out[f"{col}_was_imputed"] = flag
        summaries.append({
            "column": col,
            "n_missing_before": before,
            "n_imputed": int(flag.sum()),
            "n_missing_after": int(after_mask.sum()),
            "method": method,
            "max_gap": np.inf if np.isinf(max_gap) else max_gap,
        })
    out.attrs.update(data.attrs)
    out.attrs["imputation_summary"] = pd.DataFrame(summaries)
    return out
