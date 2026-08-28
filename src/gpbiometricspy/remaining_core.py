from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import math
import pickle
import platform
import sys
from typing import Any

import numpy as np
import pandas as pd

from ._helpers import as_list, r_sd

_GROUP_CANDIDATES = [
    "source_file", "source_participant", "USER", "USER_FILE", "participant",
    "subject", "subject_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name",
    "trial", "trial_id", "trial_global",
]


def _coerce_df(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, (str, Path)):
        return pd.read_csv(data)
    if isinstance(data, dict) and isinstance(data.get("data"), pd.DataFrame):
        return data["data"].copy()
    raise TypeError("`data` must be a data frame or a supported result object.")


def _numeric(s) -> np.ndarray:
    return pd.to_numeric(pd.Series(s), errors="coerce").to_numpy(float)


def _resolve_groups(df: pd.DataFrame, group_cols=None) -> list[str]:
    cols = as_list(group_cols) if group_cols is not None else [c for c in _GROUP_CANDIDATES if c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError("`group_cols` were not found in `data`: " + ", ".join(missing))
    return cols


def _group_ids(df: pd.DataFrame, group_cols: list[str]) -> pd.Series:
    if not group_cols:
        return pd.Series(["all"] * len(df), index=df.index, dtype=object)
    vals = df[group_cols].astype(object).where(pd.notna(df[group_cols]), "<NA>").astype(str)
    return vals.agg("||".join, axis=1)


def simulate_gazepoint_artifact(
    data,
    signal_cols,
    artifact=("missing_run", "flatline", "spike"),
    n_artifacts=1,
    artifact_length=5,
    magnitude=None,
    seed=None,
    suffix="_artifact",
    overwrite=False,
):
    df = _coerce_df(data)
    if df.empty:
        raise ValueError("`data` must contain at least one row.")
    cols = as_list(signal_cols)
    if not cols:
        raise ValueError("`signal_cols` must contain at least one column name.")
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError("`signal_cols` contains columns not found in `data`: " + ", ".join(missing))
    nonnum = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
    if nonnum:
        raise TypeError("All `signal_cols` must be numeric. Non-numeric columns: " + ", ".join(nonnum))
    arts = as_list(artifact)
    choices = {"missing_run", "flatline", "spike", "noise", "drift"}
    if not arts or any(a not in choices for a in arts):
        raise ValueError("Unsupported artifact type.")
    if not isinstance(n_artifacts, (int, float, np.number)) or not np.isfinite(n_artifacts) or n_artifacts < 0:
        raise ValueError("`n_artifacts` must be a single non-negative number.")
    if not isinstance(artifact_length, (int, float, np.number)) or not np.isfinite(artifact_length) or artifact_length < 1:
        raise ValueError("`artifact_length` must be a single positive number.")
    n_artifacts = int(n_artifacts)
    artifact_length = int(artifact_length)
    if magnitude is not None and (not isinstance(magnitude, (int, float, np.number)) or not np.isfinite(magnitude)):
        raise ValueError("`magnitude` must be `None` or a single finite number.")
    if not isinstance(suffix, str):
        raise TypeError("`suffix` must be a single character string.")
    if not isinstance(overwrite, (bool, np.bool_)):
        raise TypeError("`overwrite` must be True or False.")

    # Exact R RNG streams are not portable; preserve the documented deterministic contract.
    rng = np.random.default_rng(seed)
    out = df.copy()
    log = []
    for signal in cols:
        output_col = signal if overwrite else f"{signal}{suffix}"
        if not overwrite and output_col in out.columns:
            raise ValueError(f"Output column already exists: {output_col}. Choose another `suffix` or set `overwrite = True`.")
        out[output_col] = pd.to_numeric(out[signal], errors="coerce")
        for artifact_type in arts:
            for j in range(1, n_artifacts + 1):
                max_start = max(1, len(out) - artifact_length + 1)
                start_row = int(rng.integers(1, max_start + 1))
                end_row = min(len(out), start_row + artifact_length - 1)
                pos = np.arange(start_row - 1, end_row)
                vals = pd.to_numeric(out.iloc[pos][output_col], errors="coerce").to_numpy(float)
                full = pd.to_numeric(out[output_col], errors="coerce").to_numpy(float)
                finite = full[np.isfinite(full)]
                scale = r_sd(finite)
                if not np.isfinite(scale) or scale == 0:
                    scale = 1.0
                mag = 5 * scale if magnitude is None else float(magnitude)
                if artifact_type == "missing_run":
                    out.iloc[pos, out.columns.get_loc(output_col)] = np.nan
                elif artifact_type == "flatline":
                    good = vals[np.isfinite(vals)]
                    flat = float(good[0]) if good.size else (float(np.median(finite)) if finite.size else 0.0)
                    out.iloc[pos, out.columns.get_loc(output_col)] = flat
                elif artifact_type == "spike":
                    signs = rng.choice([-1.0, 1.0], size=len(pos))
                    out.iloc[pos, out.columns.get_loc(output_col)] = vals + signs * mag
                elif artifact_type == "noise":
                    out.iloc[pos, out.columns.get_loc(output_col)] = vals + rng.normal(0.0, abs(mag), size=len(pos))
                elif artifact_type == "drift":
                    out.iloc[pos, out.columns.get_loc(output_col)] = vals + np.linspace(0.0, mag, len(pos))
                log.append({
                    "signal": signal, "output_col": output_col, "artifact": artifact_type,
                    "artifact_index": j, "start_row": start_row, "end_row": end_row,
                    "n_samples_modified": len(pos), "magnitude": mag,
                })
    artifact_log = pd.DataFrame(log, columns=[
        "signal", "output_col", "artifact", "artifact_index", "start_row", "end_row",
        "n_samples_modified", "magnitude",
    ])
    return {
        "data": out,
        "artifact_log": artifact_log,
        "parameters": {
            "signal_cols": cols, "artifact": arts, "n_artifacts": n_artifacts,
            "artifact_length": artifact_length, "magnitude": magnitude, "seed": seed,
            "suffix": suffix, "overwrite": bool(overwrite),
        },
        "class": ["gazepoint_artifact_simulation", "list"],
    }


def _manifest_file_table(input_paths) -> pd.DataFrame:
    cols = ["path", "exists", "is_directory", "size_bytes", "modified_time"]
    paths = [input_paths] if isinstance(input_paths, (str, Path)) else as_list(input_paths)
    if input_paths is None or len(paths) == 0:
        return pd.DataFrame(columns=cols)
    rows = []
    for raw in paths:
        p = Path(raw).expanduser().resolve(strict=False)
        exists = p.exists()
        stat = p.stat() if exists else None
        rows.append({
            "path": p.as_posix(), "exists": exists,
            "is_directory": p.is_dir() if exists else np.nan,
            "size_bytes": float(stat.st_size) if stat else np.nan,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(sep=" ") if stat else np.nan,
        })
    return pd.DataFrame(rows, columns=cols)


def _manifest_text(m: dict) -> str:
    lines = [
        "Gazepoint analysis manifest",
        f"created_at: {m['created_at']}",
        f"package: {m['package']}",
        f"package_version: {m['package_version']}",
        f"python_version: {m['python_version']}",
        f"platform: {m['platform']}",
    ]
    if m["input_files"].empty:
        lines.append("input: none supplied")
    else:
        for _, r in m["input_files"].iterrows():
            lines.append(f"input: {r.path} | exists={r.exists} | directory={r.is_directory} | size_bytes={r.size_bytes}")
    if m["parameters"]:
        lines += [f"parameter: {k} = {repr(v)}" for k, v in m["parameters"].items()]
    else:
        lines.append("parameters: none supplied")
    lines += [f"output: {x}" for x in as_list(m["outputs"])] if m["outputs"] is not None else ["output: none supplied"]
    lines += [f"note: {x}" for x in as_list(m["notes"])] if m["notes"] is not None else ["note: none supplied"]
    return "\n".join(lines) + "\n"


def generate_gazepoint_manifest(input_paths=None, parameters=None, outputs=None, notes=None, write_path=None, include_session_info=True):
    if input_paths is not None and not isinstance(input_paths, (str, Path, list, tuple, np.ndarray, pd.Series)):
        raise TypeError("`input_paths` must be `None` or a character vector.")
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise TypeError("`parameters` must be a list/dict.")
    if outputs is not None and not isinstance(outputs, (str, list, tuple, np.ndarray, pd.Series)):
        raise TypeError("`outputs` must be `None` or a character vector.")
    if notes is not None and not isinstance(notes, (str, list, tuple, np.ndarray, pd.Series)):
        raise TypeError("`notes` must be `None` or a character vector.")
    if write_path is not None and not isinstance(write_path, (str, Path)):
        raise TypeError("`write_path` must be `None` or a single file path.")
    if not isinstance(include_session_info, (bool, np.bool_)):
        raise TypeError("`include_session_info` must be True or False.")
    try:
        from . import __version__ as version
    except Exception:
        version = "0.1.1"
    manifest = {
        "created_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "package": "gpbiometricspy",
        "package_version": version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "input_files": _manifest_file_table(input_paths),
        "outputs": outputs,
        "parameters": dict(parameters),
        "notes": notes,
        "session_info": {"python": sys.version, "platform": platform.platform()} if include_session_info else None,
        "class": ["gazepoint_manifest", "list"],
    }
    if write_path is not None:
        p = Path(write_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".rds":
            # Python round-trip analogue; not claimed as an R-compatible RDS serializer.
            with p.open("wb") as f:
                pickle.dump(manifest, f)
        elif p.suffix.lower() == ".json":
            serial = {**manifest, "input_files": manifest["input_files"].to_dict(orient="records")}
            p.write_text(json.dumps(serial, indent=2, default=str), encoding="utf-8")
        else:
            p.write_text(_manifest_text(manifest), encoding="utf-8")
    return manifest


def _named_lookup(cols, values):
    if values is None:
        return [np.nan] * len(cols)
    if isinstance(values, pd.Series):
        values = values.to_dict()
    if not isinstance(values, dict):
        raise ValueError("Named lookup values must have names.")
    return [str(values[c]) if c in values else np.nan for c in cols]


def _append_missing_required(dictionary, required_cols, units, descriptions):
    req = as_list(required_cols)
    if not req:
        return dictionary
    present_cols = set(dictionary["column"].dropna().astype(str))
    missing = [c for c in req if c not in present_cols]
    if not missing:
        return dictionary
    rows = pd.DataFrame({
        "source": ["required_cols"] * len(missing), "column": missing, "present": False,
        "required": True, "type": np.nan, "n_rows": np.nan, "n_missing": np.nan,
        "prop_missing": np.nan, "n_unique": np.nan,
        "unit": _named_lookup(missing, units), "description": _named_lookup(missing, descriptions),
    })
    return pd.concat([dictionary, rows], ignore_index=True)


def create_gazepoint_dictionary(data=None, file_paths=None, units=None, descriptions=None, required_cols=None, write_path=None):
    if data is not None and not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be `None` or a data frame.")
    if file_paths is not None and not isinstance(file_paths, (str, Path, list, tuple, np.ndarray, pd.Series)):
        raise TypeError("`file_paths` must be `None` or a character vector.")
    if data is None and file_paths is None:
        raise ValueError("Supply either `data` or `file_paths`.")
    req = as_list(required_cols)
    if data is not None:
        cols = list(data.columns)
        rows = []
        for c in cols:
            s = data[c]
            rows.append({
                "source": "data", "column": c, "present": True, "required": c in req,
                "type": str(s.dtype), "n_rows": len(data), "n_missing": int(s.isna().sum()),
                "prop_missing": float(s.isna().mean()) if len(s) else np.nan,
                "n_unique": int(s.nunique(dropna=False)),
                "unit": _named_lookup([c], units)[0], "description": _named_lookup([c], descriptions)[0],
            })
        dictionary = pd.DataFrame(rows)
    else:
        rows = []
        for raw in ([file_paths] if isinstance(file_paths, (str, Path)) else as_list(file_paths)):
            p = Path(raw).expanduser().resolve(strict=False)
            if not p.exists():
                rows.append({"source": p.as_posix(), "column": np.nan, "present": False, "required": np.nan,
                             "type": np.nan, "n_rows": np.nan, "n_missing": np.nan, "prop_missing": np.nan,
                             "n_unique": np.nan, "unit": np.nan, "description": "File not found"})
                continue
            cols = list(pd.read_csv(p, nrows=0).columns)
            for c in cols:
                rows.append({"source": p.as_posix(), "column": c, "present": True, "required": c in req,
                             "type": np.nan, "n_rows": np.nan, "n_missing": np.nan, "prop_missing": np.nan,
                             "n_unique": np.nan, "unit": _named_lookup([c], units)[0],
                             "description": _named_lookup([c], descriptions)[0]})
        dictionary = pd.DataFrame(rows)
    dictionary = _append_missing_required(dictionary, req, units, descriptions)
    dictionary.attrs["class"] = ["gazepoint_dictionary", "data.frame"]
    if write_path is not None:
        p = Path(write_path); p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".csv":
            dictionary.to_csv(p, index=False)
        else:
            cols = [c for c in ["column", "present", "required", "type", "unit", "description"] if c in dictionary.columns]
            d = dictionary[cols].copy().fillna("")
            lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
            lines += ["| " + " | ".join(map(str, row)) + " |" for row in d.to_numpy()]
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dictionary


def anonymize_gazepoint_data(data, id_cols, prefix="P", width=3, keep_mapping=True):
    df = _coerce_df(data)
    cols = as_list(id_cols)
    if not cols:
        raise ValueError("`id_cols` must contain at least one column name.")
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError("`id_cols` contains columns not found in `data`: " + ", ".join(missing))
    if not isinstance(prefix, str):
        raise TypeError("`prefix` must be a single character string.")
    if not isinstance(width, (int, float, np.number)) or not np.isfinite(width) or width < 1:
        raise ValueError("`width` must be a single positive number.")
    if not isinstance(keep_mapping, (bool, np.bool_)):
        raise TypeError("`keep_mapping` must be True or False.")
    width = int(width); out = df.copy(); maps = []
    for c in cols:
        original = out[c].astype("string")
        uniq = sorted(original.dropna().unique().tolist())
        mapping = {u: f"{prefix}{i:0{width}d}" for i, u in enumerate(uniq, 1)}
        replaced = original.map(mapping).astype(object)
        replaced[pd.isna(original)] = np.nan
        out[c] = replaced
        maps += [{"column": c, "original_value": u, "anonymized_value": mapping[u]} for u in uniq]
    if keep_mapping:
        out.attrs["id_mapping"] = pd.DataFrame(maps, columns=["column", "original_value", "anonymized_value"])
    out.attrs["class"] = ["gazepoint_anonymized_data", "data.frame"]
    return out


def _baseline_correct(data, baseline_rows, value_column, validity_column, group_columns, output_column, summary, exclude_zero):
    df = _coerce_df(data)
    if value_column is None or value_column not in df.columns:
        raise ValueError(f"`value_column` was not found in `data`: {value_column}")
    br = np.asarray(baseline_rows)
    if br.dtype != bool or len(br) != len(df):
        raise ValueError("`baseline_rows` must be a logical vector with length equal to nrow(data).")
    if summary not in {"mean", "median"}:
        raise ValueError("`summary` must be 'mean' or 'median'.")
    groups = as_list(group_columns)
    missing = [c for c in groups if c not in df.columns]
    if missing:
        raise ValueError("`group_columns` were not found in `data`: " + ", ".join(missing))
    x = _numeric(df[value_column])
    valid = np.isfinite(x)
    if exclude_zero:
        valid &= x != 0
    validity_used = validity_column if validity_column is not None and validity_column in df.columns else None
    if validity_used:
        v = _numeric(df[validity_used]); valid &= np.isfinite(v) & (v > 0)
    eligible = br & valid
    corrected = np.full(len(df), np.nan)
    rows = []
    if not groups:
        keys = [("all", np.arange(len(df)))]
    else:
        gids = _group_ids(df, groups)
        keys = [(g, np.flatnonzero((gids == g).to_numpy())) for g in pd.unique(gids)]
    for g, idx in keys:
        e = eligible[idx]
        vals = x[idx][e]
        baseline = np.nan if vals.size == 0 else float(np.median(vals) if summary == "median" else np.mean(vals))
        corrected[idx] = x[idx] - baseline
        rows.append({"group": g, "value_column": value_column, "validity_column": validity_used if validity_used else np.nan,
                     "baseline_rows": int(br[idx].sum()), "baseline_usable_rows": int(e.sum()),
                     "baseline_value": baseline, "summary": summary})
    df[output_column] = corrected
    df.attrs["baseline_summary"] = pd.DataFrame(rows)
    return df


def baseline_correct_gazepoint_gsr(data, baseline_rows, value_column=None, validity_column="GSRV", group_columns=None, output_column=None, summary="mean", exclude_zero=True):
    df = _coerce_df(data)
    if value_column is None:
        value_column = next((c for c in ("GSR_US", "GSR") if c in df.columns), None)
    if value_column is None:
        raise ValueError("`value_column` could not be determined.")
    output_column = output_column or f"{value_column}_baseline_corrected"
    return _baseline_correct(df, baseline_rows, value_column, validity_column, group_columns, output_column, summary, exclude_zero)


def baseline_correct_gazepoint_hr(data, baseline_rows, value_column="HR", validity_column="HRV", group_columns=None, output_column=None, summary="mean", exclude_zero=True):
    output_column = output_column or f"{value_column}_baseline_corrected"
    return _baseline_correct(data, baseline_rows, value_column, validity_column, group_columns, output_column, summary, exclude_zero)


def smooth_gazepoint_biometrics(data, value_column, window=5, output_column=None, na_rm=True):
    df = _coerce_df(data)
    if not isinstance(value_column, str) or not value_column:
        raise ValueError("`value_column` must be a single non-empty column name.")
    if value_column not in df.columns:
        raise ValueError(f"`value_column` was not found in `data`: {value_column}")
    if not isinstance(window, (int, np.integer)) or window < 1 or window % 2 == 0:
        raise ValueError("`window` must be a positive odd integer.")
    output_column = output_column or f"{value_column}_smoothed"
    x = _numeric(df[value_column]); half = window // 2; out = np.full(len(x), np.nan)
    for i in range(len(x)):
        vals = x[max(0, i-half): min(len(x), i+half+1)]
        if na_rm:
            vals = vals[np.isfinite(vals)]
        if vals.size and np.isfinite(vals).all():
            out[i] = float(np.mean(vals))
    df[output_column] = out
    return df


def _detect_unit(x, unit):
    if unit not in {"auto", "ms", "seconds"}:
        raise ValueError("`unit` must be 'auto', 'ms', or 'seconds'.")
    if unit != "auto":
        return unit
    a = np.asarray(x, float); a = a[np.isfinite(a) & (a > 0)]
    if not a.size:
        return "ms"
    med = np.median(a)
    return "seconds" if 0.2 < med < 5 else "ms"


def _positive_scalar(x, name):
    if not isinstance(x, (int, float, np.number)) or not np.isfinite(x) or x <= 0:
        raise ValueError(f"`{name}` must be a single positive finite number.")


def filter_gazepoint_ibi_implausible(data, ibi_col="IBI", time_col=None, group_cols=None, validity_col=None, unit="auto", min_ibi_ms=300, max_ibi_ms=2000, max_change_ms=400, max_change_prop=0.30, output_col="IBI_clean_ms"):
    df = _coerce_df(data)
    if ibi_col not in df.columns: raise ValueError("`ibi_col` was not found in `data`.")
    if time_col is not None and time_col not in df.columns: raise ValueError("`time_col` was not found in `data`.")
    if validity_col is not None and validity_col not in df.columns: raise ValueError("`validity_col` was not found in `data`.")
    groups = _resolve_groups(df, group_cols)
    for x, n in [(min_ibi_ms,"min_ibi_ms"),(max_ibi_ms,"max_ibi_ms"),(max_change_ms,"max_change_ms"),(max_change_prop,"max_change_prop")]: _positive_scalar(x,n)
    if max_ibi_ms <= min_ibi_ms: raise ValueError("`max_ibi_ms` must be greater than `min_ibi_ms`.")
    raw = _numeric(df[ibi_col]); detected = _detect_unit(raw, unit); ibi = raw*1000 if detected=="seconds" else raw.copy()
    gids = _group_ids(df, groups)
    nonfinite = ~np.isfinite(ibi); nonpositive=np.isfinite(ibi)&(ibi<=0); low=np.isfinite(ibi)&(ibi<min_ibi_ms); high=np.isfinite(ibi)&(ibi>max_ibi_ms)
    invalidv=np.zeros(len(df),bool)
    if validity_col:
        v=_numeric(df[validity_col]); invalidv=(~np.isfinite(v))|(v==0)
    flag_abs=np.zeros(len(df),bool); flag_rel=np.zeros(len(df),bool)
    for g in pd.unique(gids):
        idx=np.flatnonzero((gids==g).to_numpy()); x=ibi[idx]
        if len(idx)<2: continue
        prev=np.r_[np.nan,x[:-1]]; da=np.abs(x-prev); dr=da/prev
        flag_abs[idx]=np.isfinite(da)&(da>max_change_ms); flag_rel[idx]=np.isfinite(dr)&(dr>max_change_prop)
    impl=nonfinite|nonpositive|low|high|invalidv|flag_abs|flag_rel
    clean=ibi.copy(); clean[impl]=np.nan
    outdf=df.copy(); outdf[output_col]=clean
    rf=pd.DataFrame({"row_id":np.arange(1,len(df)+1),"group_id":gids.to_numpy(),"ibi_raw":raw,"ibi_ms":ibi,"ibi_clean_ms":clean,
                     "flag_nonfinite":nonfinite,"flag_nonpositive":nonpositive,"flag_too_low":low,"flag_too_high":high,
                     "flag_invalid_validity":invalidv,"flag_large_absolute_change":flag_abs,"flag_large_relative_change":flag_rel,"flag_implausible":impl})
    if groups: rf=pd.concat([df[groups].reset_index(drop=True),rf.reset_index(drop=True)],axis=1)
    summaries=[]
    for g in pd.unique(gids):
        d=rf[rf.group_id==g]; cl=d.ibi_clean_ms[np.isfinite(d.ibi_clean_ms)]
        row={"group_id":g,"rows":len(d),"implausible_rows":int(d.flag_implausible.sum()),"implausible_prop":float(d.flag_implausible.mean()),"clean_rows":len(cl),
             "mean_clean_ibi_ms":float(cl.mean()) if len(cl) else np.nan,"median_clean_ibi_ms":float(cl.median()) if len(cl) else np.nan}
        if groups:
            for c in groups: row[c]=d.iloc[0][c]
        summaries.append(row)
    gs=pd.DataFrame(summaries)
    status="fail_no_clean_ibi_values" if not np.isfinite(clean).any() else ("warn_implausible_ibi_detected" if impl.any() else "ibi_values_pass")
    ov=pd.DataFrame([{"input_rows":len(df),"ibi_col":ibi_col,"output_col":output_col,"detected_unit":detected,"implausible_rows":int(impl.sum()),"implausible_prop":float(impl.mean()),"clean_rows":int(np.isfinite(clean).sum()),"group_count":int(gids.nunique()),"status":status}])
    return {"overview":ov,"data":outdf,"row_flags":rf,"group_summary":gs,"settings":{"ibi_col":ibi_col,"time_col":time_col,"group_cols":groups,"validity_col":validity_col,"unit":unit,"detected_unit":detected,"min_ibi_ms":min_ibi_ms,"max_ibi_ms":max_ibi_ms,"max_change_ms":max_change_ms,"max_change_prop":max_change_prop,"output_col":output_col},"class":["gazepoint_ibi_filter","list"]}


def compare_gazepoint_hr_ibi_consistency(data, hr_col="HR", ibi_col="IBI", time_col=None, group_cols=None, unit="auto", max_abs_diff_bpm=10, max_rel_diff_prop=0.15):
    df=_coerce_df(data)
    if hr_col not in df.columns: raise ValueError("`hr_col` was not found in `data`.")
    if ibi_col not in df.columns: raise ValueError("`ibi_col` was not found in `data`.")
    if time_col is not None and time_col not in df.columns: raise ValueError("`time_col` was not found in `data`.")
    groups=_resolve_groups(df,group_cols); _positive_scalar(max_abs_diff_bpm,"max_abs_diff_bpm"); _positive_scalar(max_rel_diff_prop,"max_rel_diff_prop")
    hr=_numeric(df[hr_col]); raw=_numeric(df[ibi_col]); detected=_detect_unit(raw,unit); ibi=raw*1000 if detected=="seconds" else raw.copy()
    hribi=np.where(np.isfinite(ibi)&(ibi>0),60000/ibi,np.nan); ad=np.abs(hr-hribi); rd=ad/hribi; missing=(~np.isfinite(hr))|(~np.isfinite(hribi)); inconsistent=(~missing)&((ad>max_abs_diff_bpm)|(rd>max_rel_diff_prop)); gids=_group_ids(df,groups)
    rows=pd.DataFrame({"row_id":np.arange(1,len(df)+1),"group_id":gids.to_numpy(),"hr_observed_bpm":hr,"ibi_ms":ibi,"hr_from_ibi_bpm":hribi,"abs_diff_bpm":ad,"rel_diff_prop":rd,"flag_missing_pair":missing,"flag_inconsistent":inconsistent})
    if groups: rows=pd.concat([df[groups].reset_index(drop=True),rows],axis=1)
    sums=[]
    for g in pd.unique(gids):
        d=rows[rows.group_id==g]; comp=~d.flag_missing_pair; n=int(comp.sum()); inc=int(d.flag_inconsistent.sum())
        row={"group_id":g,"rows":len(d),"comparable_rows":n,"inconsistent_rows":inc,"inconsistent_prop":inc/n if n else np.nan,
             "median_abs_diff_bpm":float(np.nanmedian(d.abs_diff_bpm)) if np.isfinite(d.abs_diff_bpm).any() else np.nan,"mean_abs_diff_bpm":float(np.nanmean(d.abs_diff_bpm)) if np.isfinite(d.abs_diff_bpm).any() else np.nan}
        if groups:
            for c in groups: row[c]=d.iloc[0][c]
        sums.append(row)
    comp=int((~missing).sum()); inc=int(inconsistent.sum()); status="fail_no_comparable_hr_ibi_rows" if comp==0 else ("warn_hr_ibi_inconsistency_detected" if inc>0 else "hr_ibi_consistency_pass")
    ov=pd.DataFrame([{"input_rows":len(df),"comparable_rows":comp,"inconsistent_rows":inc,"inconsistent_prop":inc/comp if comp else np.nan,"detected_ibi_unit":detected,"mean_abs_diff_bpm":float(np.nanmean(ad)) if np.isfinite(ad).any() else np.nan,"median_abs_diff_bpm":float(np.nanmedian(ad)) if np.isfinite(ad).any() else np.nan,"group_count":int(gids.nunique()),"status":status}])
    return {"overview":ov,"row_diagnostics":rows,"group_summary":pd.DataFrame(sums),"settings":{"hr_col":hr_col,"ibi_col":ibi_col,"time_col":time_col,"group_cols":groups,"unit":unit,"detected_ibi_unit":detected,"max_abs_diff_bpm":max_abs_diff_bpm,"max_rel_diff_prop":max_rel_diff_prop},"class":["gazepoint_hr_ibi_consistency","list"]}


def _collapse_repeated(x,tol):
    if len(x)<=1: return x
    return x[np.r_[True,np.abs(np.diff(x))>tol]]


def _hrv_features(x,min_intervals,min_duration_s,diff_threshold_ms):
    n=len(x); duration=float(np.sum(x)/1000) if n else np.nan
    if n<min_intervals:
        return {"n_intervals":n,"duration_s":duration,"min_duration_s":min_duration_s,"mean_ibi_ms":np.nan,"median_ibi_ms":np.nan,"mean_hr_bpm":np.nan,"sdnn_ms":np.nan,"rmssd_ms":np.nan,"sdsd_ms":np.nan,"nn50":np.nan,"pnn50":np.nan,"cvnn":np.nan,"min_ibi_ms":float(np.min(x)) if n else np.nan,"max_ibi_ms":float(np.max(x)) if n else np.nan,"feature_status":"insufficient_intervals"}
    d=np.diff(x); sd=r_sd(x); sdsd=r_sd(d) if len(d)>1 else np.nan; nn50=int(np.sum(np.abs(d)>diff_threshold_ms));
    return {"n_intervals":n,"duration_s":duration,"min_duration_s":min_duration_s,"mean_ibi_ms":float(np.mean(x)),"median_ibi_ms":float(np.median(x)),"mean_hr_bpm":float(np.mean(60000/x)),"sdnn_ms":sd,"rmssd_ms":float(np.sqrt(np.mean(d*d))) if len(d) else np.nan,"sdsd_ms":sdsd,"nn50":nn50,"pnn50":nn50/len(d) if len(d) else np.nan,"cvnn":sd/float(np.mean(x)),"min_ibi_ms":float(np.min(x)),"max_ibi_ms":float(np.max(x)),"feature_status":"warn_short_hrv_duration" if np.isfinite(duration) and duration<min_duration_s else "features_computed"}


def extract_gazepoint_hrv_features(data, ibi_col="IBI_clean_ms", group_cols=None, unit="auto", min_intervals=3, min_duration_s=30, diff_threshold_ms=50, collapse_repeated_intervals=True, repeated_tolerance_ms=1e-8):
    df=_coerce_df(data)
    if ibi_col not in df.columns: raise ValueError("`ibi_col` was not found in `data`.")
    groups=_resolve_groups(df,group_cols); _positive_scalar(min_intervals,"min_intervals"); _positive_scalar(diff_threshold_ms,"diff_threshold_ms")
    if not isinstance(min_duration_s,(int,float,np.number)) or not np.isfinite(min_duration_s) or min_duration_s<0: raise ValueError("`min_duration_s` must be a single non-negative finite number.")
    if not isinstance(collapse_repeated_intervals,(bool,np.bool_)): raise ValueError("`collapse_repeated_intervals` must be TRUE or FALSE.")
    if not isinstance(repeated_tolerance_ms,(int,float,np.number)) or not np.isfinite(repeated_tolerance_ms) or repeated_tolerance_ms<0: raise ValueError("`repeated_tolerance_ms` must be a single non-negative finite number.")
    raw=_numeric(df[ibi_col]); detected=_detect_unit(raw,unit); ibi=raw*1000 if detected=="seconds" else raw.copy(); gids=_group_ids(df,groups); rows=[]
    for g in pd.unique(gids):
        idx=np.flatnonzero((gids==g).to_numpy()); xraw=ibi[idx]; xraw=xraw[np.isfinite(xraw)&(xraw>0)]; x=_collapse_repeated(xraw,repeated_tolerance_ms) if collapse_repeated_intervals else xraw
        row=_hrv_features(x,int(min_intervals),float(min_duration_s),float(diff_threshold_ms)); row.update({"input_interval_rows":len(xraw),"used_intervals_after_collapse":len(x),"collapsed_repeated_intervals":bool(collapse_repeated_intervals),"group_id":g})
        if groups:
            for c in groups: row[c]=df.iloc[idx[0]][c]
        rows.append(row)
    features=pd.DataFrame(rows); valid=features.feature_status.isin(["features_computed","warn_short_hrv_duration"]) if len(features) else pd.Series([],dtype=bool); short=int((features.feature_status=="warn_short_hrv_duration").sum()) if len(features) else 0
    nv=int(valid.sum()) if len(features) else 0; n=len(features); status="fail_no_hrv_features_computed" if nv==0 else ("warn_some_groups_insufficient_intervals" if nv<n else ("warn_short_hrv_duration" if short>0 else "hrv_features_computed"))
    ov=pd.DataFrame([{"group_count":n,"valid_feature_groups":nv,"insufficient_interval_groups":int((features.feature_status=="insufficient_intervals").sum()) if n else 0,"short_duration_groups":short,"detected_ibi_unit":detected,"min_intervals":min_intervals,"min_duration_s":min_duration_s,"diff_threshold_ms":diff_threshold_ms,"status":status}])
    return {"overview":ov,"features":features,"settings":{"ibi_col":ibi_col,"group_cols":groups,"unit":unit,"detected_ibi_unit":detected,"min_intervals":min_intervals,"min_duration_s":min_duration_s,"diff_threshold_ms":diff_threshold_ms,"collapse_repeated_intervals":bool(collapse_repeated_intervals),"repeated_tolerance_ms":repeated_tolerance_ms},"class":["gazepoint_hrv_feature_extraction","list"]}
