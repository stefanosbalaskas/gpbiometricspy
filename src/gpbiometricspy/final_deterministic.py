from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .qc_windows_standardization import summarise_gazepoint_multimodal_windows


def _df(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, (str, Path)):
        return pd.read_csv(data)
    raise TypeError("`data` must be a data frame or CSV path.")


def _cols(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def _group_indices(df: pd.DataFrame, cols: list[str]):
    if not cols:
        return [("all_rows", df.index.to_numpy())]
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise ValueError("Missing grouping columns: " + ", ".join(miss))
    key = df[cols].astype(object).where(pd.notna(df[cols]), "<NA>").astype(str).agg(" | ".join, axis=1)
    return [(str(k), df.index[key == k].to_numpy()) for k in pd.unique(key)]


def _ema(x: np.ndarray, alpha: float) -> np.ndarray:
    out = np.empty(len(x), dtype=float)
    if not len(x):
        return out
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
    return out


def _fill_linear_edge(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    finite = np.isfinite(x)
    if finite.all():
        return x.copy()
    if not finite.any():
        return np.zeros(len(x), dtype=float)
    if finite.sum() == 1:
        return np.full(len(x), x[finite][0], dtype=float)
    idx = np.arange(len(x), dtype=float)
    return np.interp(idx, idx[finite], x[finite])


def standardise_gazepoint_adaptive_ema(
    dat,
    signal_col="GSR_US",
    group_cols=None,
    time_col=None,
    alpha=0.05,
    iqr_multiplier=1.5,
    suffix="_adaptive_ema",
    center_suffix="_ema_center",
    scale_suffix="_ema_scale",
    min_scale=1e-8,
    overwrite=False,
):
    if not isinstance(dat, pd.DataFrame):
        raise TypeError("`dat` must be a data frame.")
    if signal_col not in dat.columns:
        raise ValueError(f"Column `{signal_col}` was not found in `dat`.")
    if not pd.api.types.is_numeric_dtype(dat[signal_col]):
        raise TypeError("`signal_col` must identify a numeric column.")
    groups = _cols(group_cols)
    missing = [c for c in groups if c not in dat.columns]
    if missing:
        raise ValueError("Missing `group_cols`: " + ", ".join(missing))
    if time_col is not None and time_col not in dat.columns:
        raise ValueError(f"Column `{time_col}` was not found in `dat`.")
    if not np.isfinite(alpha) or alpha <= 0 or alpha > 1:
        raise ValueError("`alpha` must be a finite number in `(0, 1]`.")
    if not np.isfinite(iqr_multiplier) or iqr_multiplier < 0:
        raise ValueError("`iqr_multiplier` must be a finite non-negative number.")
    if not np.isfinite(min_scale) or min_scale <= 0:
        raise ValueError("`min_scale` must be positive.")

    out_col = signal_col + suffix
    center_col = signal_col + center_suffix
    scale_col = signal_col + scale_suffix
    status_col = signal_col + "_adaptive_ema_status"
    new_cols = [out_col, center_col, scale_col, status_col]
    existing = [c for c in new_cols if c in dat.columns]
    if existing and not overwrite:
        raise ValueError("One or more output columns already exist: " + ", ".join(existing) + ". Use `overwrite = True`.")

    out = dat.copy()
    out[out_col] = np.nan
    out[center_col] = np.nan
    out[scale_col] = np.nan
    out[status_col] = "not_processed"
    rows = []
    for unit_id, idx in _group_indices(out, groups):
        idx = np.asarray(idx)
        if time_col is not None:
            t = pd.to_numeric(out.loc[idx, time_col], errors="coerce").to_numpy(float)
            idx = idx[np.argsort(np.where(np.isfinite(t), t, np.inf), kind="stable")]
        x = pd.to_numeric(out.loc[idx, signal_col], errors="coerce").to_numpy(float)
        finite = np.isfinite(x)
        if finite.sum() < 5:
            out.loc[idx, status_col] = "insufficient_finite_samples"
            rows.append({"unit_id": unit_id, "n_rows": len(idx), "n_finite": int(finite.sum()), "n_outliers": np.nan, "status": "insufficient_finite_samples"})
            continue
        q25, q75 = np.quantile(x[finite], [0.25, 0.75])
        iqr = q75 - q25
        lower, upper = q25 - iqr_multiplier * iqr, q75 + iqr_multiplier * iqr
        outlier = finite & ((x < lower) | (x > upper))
        clean = x.copy(); clean[outlier] = np.nan
        filled = _fill_linear_edge(clean)
        center = _ema(filled, float(alpha))
        scale = _ema(np.abs(filled - center), float(alpha)) * 1.4826
        scale[~np.isfinite(scale) | (scale < min_scale)] = min_scale
        normalized = (x - center) / scale
        out.loc[idx, out_col] = normalized
        out.loc[idx, center_col] = center
        out.loc[idx, scale_col] = scale
        out.loc[idx, status_col] = np.where(outlier, "iqr_outlier_used_for_output_not_center", "adaptive_ema_normalized")
        rows.append({"unit_id": unit_id, "n_rows": len(idx), "n_finite": int(finite.sum()), "n_outliers": int(outlier.sum()), "status": "adaptive_ema_normalized"})
    summary = pd.DataFrame(rows)
    good = int((summary["status"] == "adaptive_ema_normalized").sum()) if len(summary) else 0
    status = "adaptive_ema_normalization_complete" if good == len(summary) else ("adaptive_ema_normalization_partial" if good else "adaptive_ema_normalization_failed")
    out.attrs["adaptive_ema_overview"] = {"input_rows": len(dat), "group_count": len(summary), "successful_groups": good, "problem_groups": len(summary)-good, "signal_col": signal_col, "output_col": out_col, "status": status, "interpretation": "Adaptive EMA normalization estimates local signal center and scale after IQR-based outlier screening; it does not infer psychological or clinical states."}
    out.attrs["adaptive_ema_summary"] = summary.to_dict("records")
    out.attrs["adaptive_ema_settings"] = {"signal_col": signal_col, "group_cols": groups, "time_col": time_col, "alpha": alpha, "iqr_multiplier": iqr_multiplier, "suffix": suffix, "center_suffix": center_suffix, "scale_suffix": scale_suffix, "min_scale": min_scale, "overwrite": overwrite}
    return out


def standardize_gazepoint_adaptive_ema(*args, **kwargs):
    return standardise_gazepoint_adaptive_ema(*args, **kwargs)


def audit_gazepoint_gsr_units(dat, gsr_col="GSR", convert=False, output_col=None, resistance_to_us_factor=1_000_000):
    if not isinstance(dat, pd.DataFrame):
        raise TypeError("`dat` must be a data frame.")
    if gsr_col not in dat.columns:
        raise ValueError(f"Column `{gsr_col}` was not found in `dat`.")
    if not pd.api.types.is_numeric_dtype(dat[gsr_col]):
        raise TypeError("`gsr_col` must identify a numeric column.")
    x = pd.to_numeric(dat[gsr_col], errors="coerce").to_numpy(float)
    finite = x[np.isfinite(x)]
    if not len(finite):
        raise ValueError("`gsr_col` contains no finite numeric values.")
    q = np.quantile(finite, [0, .01, .25, .5, .75, .99, 1])
    lower = gsr_col.lower()
    if lower.endswith("_us") or lower.endswith("us") or any(s in lower for s in ["microsiemens", "micro_siemens", "conductance"]):
        likely, confidence = "conductance_microSiemens", "high_column_name"
    elif q[3] > 1000 or q[4] > 1000:
        likely, confidence = "resistance_or_impedance_ohms", "high_numeric_range"
    elif q[3] > 0 and q[3] <= 100 and q[5] <= 500:
        likely, confidence = "conductance_microSiemens", "moderate_numeric_range"
    elif q[3] > 100 and q[3] <= 1000:
        likely, confidence = "ambiguous_large_conductance_or_scaled_signal", "low_numeric_range"
    else:
        likely, confidence = "ambiguous", "low"
    status = {"resistance_or_impedance_ohms":"unit_warning_resistance_like", "conductance_microSiemens":"unit_audit_conductance_like"}.get(likely, "unit_audit_ambiguous")
    rec = "Do not apply SCR thresholds expressed in microSiemens directly to this column. Convert resistance-like values to conductance first or use a verified conductance column such as GSR_US." if likely == "resistance_or_impedance_ohms" else ("SCR thresholds expressed in microSiemens may be appropriate if the column is verified as conductance." if likely == "conductance_microSiemens" else "Verify device/export documentation before applying SCR thresholds.")
    names = ["min","q01","q25","median","q75","q99","max"]
    diag = {"gsr_col":gsr_col,"n_rows":len(x),"n_finite":len(finite),"missing_rate":float(np.mean(~np.isfinite(x))), **dict(zip(names,q)), "likely_unit":likely,"confidence":confidence}
    result = {"overview":pd.DataFrame([{"gsr_col":gsr_col,"likely_unit":likely,"confidence":confidence,"convert_requested":bool(convert),"status":status,"interpretation":"This audit uses column names and numerical ranges to flag likely GSR/EDA units; verify device documentation."}]), "diagnostics":pd.DataFrame([diag]), "recommendation":pd.DataFrame([{"gsr_col":gsr_col,"likely_unit":likely,"recommendation":rec}]), "settings":{"gsr_col":gsr_col,"convert":bool(convert),"output_col":output_col,"resistance_to_us_factor":resistance_to_us_factor}, "class":["gazepoint_gsr_unit_audit","list"]}
    if convert:
        col = output_col or f"{gsr_col}_converted_us"
        out = dat.copy()
        if likely == "resistance_or_impedance_ohms":
            vals = pd.to_numeric(out[gsr_col], errors="coerce").to_numpy(float)
            out[col] = np.where(np.isfinite(vals) & (vals > 0), resistance_to_us_factor / vals, np.nan)
            out.attrs["gsr_unit_conversion"] = "resistance_or_impedance_to_microSiemens"
        else:
            out[col] = out[gsr_col]
            out.attrs["gsr_unit_conversion"] = "copied_without_conversion_unit_not_resistance_like"
        result["data"] = out
    return result


def downsample_gazepoint_data(data, time_col, signal_cols=None, group_cols=None, interval=None, method="mean", na_rm=True, time_value="start", origin=None):
    df = _df(data)
    if df.empty:
        raise ValueError("`data` must contain at least one row.")
    if time_col not in df.columns:
        raise ValueError("`time_col` was not found in `data`.")
    if not pd.api.types.is_numeric_dtype(df[time_col]):
        raise TypeError("`time_col` must be numeric.")
    groups = _cols(group_cols)
    miss = [c for c in groups if c not in df.columns]
    if miss: raise ValueError("`group_cols` contains columns not found in `data`: " + ", ".join(miss))
    if time_col in groups: raise ValueError("`group_cols` must not include `time_col`.")
    if signal_cols is None:
        signals = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in [time_col,*groups]]
    else: signals = _cols(signal_cols)
    if not signals: raise ValueError("No numeric signal columns were selected.")
    miss = [c for c in signals if c not in df.columns]
    if miss: raise ValueError("`signal_cols` contains columns not found in `data`: " + ", ".join(miss))
    if any(c in [time_col,*groups] for c in signals): raise ValueError("`signal_cols` must not include time or grouping columns.")
    if any(not pd.api.types.is_numeric_dtype(df[c]) for c in signals): raise TypeError("All `signal_cols` must be numeric.")
    if interval is None or not np.isfinite(interval) or interval <= 0: raise ValueError("`interval` must be a positive finite number.")
    if method not in {"mean","median","first","last"}: raise ValueError("Unsupported `method`.")
    if time_value not in {"start","center","mean"}: raise ValueError("Unsupported `time_value`.")
    finite_t = pd.to_numeric(df[time_col], errors="coerce").to_numpy(float)
    finite_vals = finite_t[np.isfinite(finite_t)]
    if not len(finite_vals): raise ValueError("`time_col` contains no finite values.")
    origin_val = float(np.min(finite_vals) if origin is None else origin)
    if not np.isfinite(origin_val): raise ValueError("`origin` must be finite.")
    work = df.copy()
    work["__bin"] = np.floor((pd.to_numeric(work[time_col], errors="coerce") - origin_val) / interval)
    work = work[np.isfinite(work["__bin"])].copy(); work["__bin"] = work["__bin"].astype(int)
    by = [*groups,"__bin"]
    rows=[]
    grouped = work.groupby(by, sort=True, dropna=False) if by else [((),work)]
    for key, g in grouped:
        if not isinstance(key, tuple): key=(key,)
        row={}
        for c,val in zip(groups,key[:len(groups)]): row[c]=val
        b=int(key[-1])
        if time_value=="start": tv=origin_val+b*interval
        elif time_value=="center": tv=origin_val+b*interval+interval/2
        else: tv=float(pd.to_numeric(g[time_col],errors="coerce").mean())
        row[time_col]=tv
        for c in signals:
            vals=pd.to_numeric(g[c],errors="coerce").to_numpy(float)
            if method in {"mean","median"} and not na_rm and np.isnan(vals).any(): val=np.nan
            else:
                use=vals[np.isfinite(vals)] if na_rm else vals
                if not len(use): val=np.nan
                elif method=="mean": val=float(np.mean(use))
                elif method=="median": val=float(np.median(use))
                elif method=="first": val=float(use[0]) if np.isfinite(use[0]) else np.nan
                else: val=float(use[-1]) if np.isfinite(use[-1]) else np.nan
            row[c]=val
        row["n_source_rows"]=len(g); rows.append(row)
    out=pd.DataFrame(rows)
    out.attrs["downsample_log"]={"input_rows":len(df),"output_rows":len(out),"compression_ratio":len(out)/len(df),"origin":origin_val}
    out.attrs["downsample_settings"]={"time_col":time_col,"signal_cols":signals,"group_cols":groups,"interval":interval,"method":method,"na_rm":bool(na_rm),"time_value":time_value,"origin":origin_val}
    return out


def audit_gazepoint_biometric_sampling(data, group_columns=None, time_column=None, time_unit="seconds", expected_rate_hz=60, tolerance_hz=5):
    df=_df(data); groups=_cols(group_columns)
    if time_unit not in {"seconds","milliseconds","microseconds","samples"}: raise ValueError("Unsupported `time_unit`.")
    if time_column is None:
        time_column=next((c for c in ["TIME","TIME_TICK","CNT"] if c in df.columns),None)
    if time_column is None: raise ValueError("No timing/order column was found in `data`.")
    if time_column not in df: raise ValueError(f"`time_column` was not found in `data`: {time_column}")
    miss=[c for c in groups if c not in df]
    if miss: raise ValueError("`group_columns` were not found in `data`: "+", ".join(miss))
    parts=_group_indices(df,groups);rows=[]
    scale={"seconds":1,"milliseconds":1000,"microseconds":1_000_000}.get(time_unit)
    for _,idx in parts:
        row=df.loc[idx,groups].iloc[0].to_dict() if groups else {"group":"all"}
        tv=pd.to_numeric(df.loc[idx,time_column],errors="coerce").to_numpy(float); usable=tv[np.isfinite(tv)]; intervals=np.diff(usable); pos=intervals[intervals>0]
        estimated=median_sec=np.nan
        if len(pos) and time_unit!="samples": median_sec=float(np.median(pos/scale)); estimated=1/median_sec if median_sec>0 else np.nan
        if not np.isfinite(estimated): rate="not_estimated"
        elif expected_rate_hz is None or not np.isfinite(expected_rate_hz): rate="estimated"
        else: rate="within_tolerance" if abs(estimated-expected_rate_hz)<=tolerance_hz else "outside_tolerance"
        row.update({"time_column":time_column,"time_unit":time_unit,"n_rows":len(tv),"non_missing_time_rows":len(usable),"missing_time_rows":int((~np.isfinite(tv)).sum()),"missing_time_pct":100*(~np.isfinite(tv)).mean() if len(tv) else np.nan,"duplicate_time_rows":int(pd.Series(usable).duplicated().sum()),"interval_rows":len(intervals),"positive_interval_rows":len(pos),"zero_interval_rows":int((intervals==0).sum()),"negative_interval_rows":int((intervals<0).sum()),"monotonic_non_decreasing":bool(np.all(intervals>=0)),"strictly_increasing":bool(np.all(intervals>0)),"median_interval_seconds":median_sec,"estimated_rate_hz":estimated,"expected_rate_hz":expected_rate_hz,"rate_deviation_hz":estimated-expected_rate_hz if np.isfinite(estimated) and expected_rate_hz is not None else np.nan,"rate_status":rate}); rows.append(row)
    return pd.DataFrame(rows)


def summarise_gazepoint_hrv_features(data, ibi_col=None, group_cols=None, time_col=None, ibi_unit="auto", min_ibi_ms=300, max_ibi_ms=2000, min_valid_ibi=3):
    if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame.")
    groups=_cols(group_cols)
    miss=[c for c in groups if c not in data]
    if miss: raise ValueError("`group_cols` contains columns not found in `data`: "+", ".join(miss))
    if time_col is not None and time_col not in data: raise ValueError("`time_col` contains columns not found in `data`.")
    if min_ibi_ms<=0 or max_ibi_ms<=0 or min_ibi_ms>=max_ibi_ms: raise ValueError("IBI bounds must be positive with min < max.")
    if int(min_valid_ibi)<1: raise ValueError("`min_valid_ibi` must be positive.")
    if ibi_col is None:
        candidates=[c for c in data.columns if c.upper()!="HRV" and (c.upper()=="IBI" or c.upper().startswith(("RR","IBI","INTERBEAT","INTER_BEAT"))) and pd.api.types.is_numeric_dtype(data[c])]
        ibi_col=candidates[0] if candidates else None
    if ibi_col is None or ibi_col not in data: raise ValueError("No IBI/RR interval column was detected. Provide `ibi_col` explicitly. The raw `HRV` column is not treated as an HRV metric.")
    if ibi_col=="HRV": raise ValueError("`HRV` is treated as a validity/vendor flag, not as an HRV metric.")
    if not pd.api.types.is_numeric_dtype(data[ibi_col]): raise TypeError("`ibi_col` must be numeric.")
    rows=[]
    for name,idx in _group_indices(data,groups):
        idx=np.asarray(idx)
        if time_col is not None:
            t=pd.to_numeric(data.loc[idx,time_col],errors="coerce").to_numpy(float);idx=idx[np.argsort(np.where(np.isfinite(t),t,np.inf),kind="stable")]
        x=pd.to_numeric(data.loc[idx,ibi_col],errors="coerce").to_numpy(float);finite=x[np.isfinite(x)]
        unit=ibi_unit if ibi_unit!="auto" else ("unknown" if not len(finite) else ("milliseconds" if np.median(finite)>10 else "seconds"))
        ms=x if unit=="milliseconds" else x*1000 if unit=="seconds" else x
        missing=~np.isfinite(ms);oor=np.isfinite(ms)&((ms<min_ibi_ms)|(ms>max_ibi_ms));valid=np.isfinite(ms)&~oor;v=ms[valid];d=np.diff(v)
        rows.append({"group":name,"n_total_ibi":len(ms),"n_missing_ibi":int(missing.sum()),"n_out_of_range_ibi":int(oor.sum()),"n_valid_ibi":len(v),"valid_ibi_rate":len(v)/len(ms) if len(ms) else np.nan,"unit_detected":unit,"mean_ibi_ms":np.mean(v) if len(v) else np.nan,"median_ibi_ms":np.median(v) if len(v) else np.nan,"sdnn_ms":np.std(v,ddof=1) if len(v)>1 else np.nan,"rmssd_ms":np.sqrt(np.mean(d*d)) if len(d) else np.nan,"pnn50_percent":100*np.mean(np.abs(d)>50) if len(d) else np.nan,"mean_hr_bpm_from_ibi":60000/np.mean(v) if len(v) else np.nan,"min_ibi_ms":np.min(v) if len(v) else np.nan,"max_ibi_ms":np.max(v) if len(v) else np.nan,"status":"hrv_features_computed" if len(v)>=min_valid_ibi else "insufficient_valid_ibi"})
    features=pd.DataFrame(rows); computed=int((features.status=="hrv_features_computed").sum()) if len(features) else 0
    overview=pd.DataFrame([{"n_rows":len(data),"ibi_col":ibi_col,"group_count":len(features),"feature_rows":len(features),"groups_with_computed_features":computed,"groups_with_insufficient_ibi":len(features)-computed,"total_valid_ibi":int(features.n_valid_ibi.sum()) if len(features) else 0,"status":"hrv_features_available" if computed else "insufficient_valid_ibi"}])
    return {"overview":overview,"features":features,"settings":{"ibi_col":ibi_col,"group_cols":groups,"time_col":time_col,"ibi_unit":ibi_unit,"min_ibi_ms":min_ibi_ms,"max_ibi_ms":max_ibi_ms,"min_valid_ibi":int(min_valid_ibi),"note":"Time-domain HRV features are derived from IBI/RR intervals only; the raw Gazepoint HRV column is treated as a validity/vendor flag."},"class":["gazepoint_hrv_features","list"]}


def summarise_gazepoint_ibi_hrv_windows(data, group_columns, ibi_column="IBI", validity_column="HRV", min_ibi=0.3, max_ibi=2.0):
    df=_df(data);groups=_cols(group_columns)
    if not groups: raise ValueError("`group_columns` must define the analysis windows.")
    miss=[c for c in groups if c not in df]
    if miss: raise ValueError("`group_columns` were not found in `data`: "+", ".join(miss))
    if ibi_column not in df: raise ValueError(f"`ibi_column` was not found in `data`: {ibi_column}")
    rows=[]
    for _,idx in _group_indices(df,groups):
        row=df.loc[idx,groups].iloc[0].to_dict();ibi=pd.to_numeric(df.loc[idx,ibi_column],errors="coerce").to_numpy(float);valid=np.isfinite(ibi)&(ibi>=min_ibi)&(ibi<=max_ibi); vp=validity_column is not None and validity_column in df
        if vp:
            v=pd.to_numeric(df.loc[idx,validity_column],errors="coerce").to_numpy(float);valid &= np.isfinite(v)&(v>0)
        u=ibi[valid];d=np.diff(u)
        row.update({"ibi_column":ibi_column,"validity_column":validity_column if vp else np.nan,"n_rows":len(ibi),"ibi_usable_rows":len(u),"ibi_usable_pct":100*len(u)/len(ibi) if len(ibi) else np.nan,"mean_ibi_sec":np.mean(u) if len(u) else np.nan,"median_ibi_sec":np.median(u) if len(u) else np.nan,"sd_ibi_sec":np.std(u,ddof=1) if len(u)>1 else np.nan,"mean_hr_from_ibi_bpm":np.mean(60/u) if len(u) else np.nan,"sdnn_ms":np.std(u,ddof=1)*1000 if len(u)>1 else np.nan,"rmssd_ms":np.sqrt(np.mean(d*d))*1000 if len(d) else np.nan,"pnn50":np.mean(np.abs(d)>0.05) if len(d) else np.nan,"min_ibi_sec":np.min(u) if len(u) else np.nan,"max_ibi_sec":np.max(u) if len(u) else np.nan});rows.append(row)
    return pd.DataFrame(rows)


def recommend_gazepoint_biometric_exclusions(data, group_columns=None, data_is_window_summary=False, participant_column=None, gsr_min_usable_pct=50, hr_min_usable_pct=50, dial_min_usable_pct=50, require_gsr=True, require_hr=True, require_dial=False):
    if data_is_window_summary:
        if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame when `data_is_window_summary = True`.")
        windows=data.copy()
    else:
        if not _cols(group_columns): raise ValueError("`group_columns` must be supplied when `data` is row-level.")
        windows=summarise_gazepoint_multimodal_windows(_df(data), group_columns=_cols(group_columns))
    needed=["gsr_usable_pct","hr_usable_pct","dial_usable_pct"];miss=[c for c in needed if c not in windows]
    if miss: raise ValueError("`data` does not look like a multimodal biometric window summary. Missing columns: "+", ".join(miss))
    if participant_column is None: participant_column=next((c for c in ["source_participant","USER","USERID","participant","subject"] if c in windows),None)
    out=windows.copy()
    out["low_gsr_usable"]=out.gsr_usable_pct.isna()|(out.gsr_usable_pct<gsr_min_usable_pct);out["low_hr_usable"]=out.hr_usable_pct.isna()|(out.hr_usable_pct<hr_min_usable_pct);out["low_dial_usable"]=out.dial_usable_pct.isna()|(out.dial_usable_pct<dial_min_usable_pct)
    req=(out.low_gsr_usable if require_gsr else False)|(out.low_hr_usable if require_hr else False)|(out.low_dial_usable if require_dial else False)
    opt=(out.low_gsr_usable if not require_gsr else False)|(out.low_hr_usable if not require_hr else False)|(out.low_dial_usable if not require_dial else False)
    out["recommendation"]=np.where(req,"exclude",np.where(opt,"review","keep"))
    def reason(r):
        a=[]
        if r.low_gsr_usable:a.append(f"GSR/EDA usable coverage below {gsr_min_usable_pct}%")
        if r.low_hr_usable:a.append(f"Heart-rate usable coverage below {hr_min_usable_pct}%")
        if r.low_dial_usable:a.append(f"Engagement-dial usable coverage below {dial_min_usable_pct}%")
        return "; ".join(a) if a else "usable biometric coverage acceptable"
    out["recommendation_reason"]=out.apply(reason,axis=1)
    prows=[]
    if participant_column and participant_column in out:
        for p,g in out.groupby(participant_column,sort=False,dropna=False):
            n=len(g);e=int((g.recommendation=="exclude").sum());r=int((g.recommendation=="review").sum());k=int((g.recommendation=="keep").sum());pr="exclude" if e==n else ("review" if e or r else "keep")
            prows.append({"participant":str(p),"n_windows":n,"keep_windows":k,"review_windows":r,"exclude_windows":e,"exclude_pct":100*e/n if n else np.nan,"participant_recommendation":pr})
    participants=pd.DataFrame(prows,columns=["participant","n_windows","keep_windows","review_windows","exclude_windows","exclude_pct","participant_recommendation"])
    overview=pd.DataFrame([{"n_windows":len(out),"keep_windows":int((out.recommendation=="keep").sum()),"review_windows":int((out.recommendation=="review").sum()),"exclude_windows":int((out.recommendation=="exclude").sum()),"participant_column":participant_column,"n_participants":len(participants) if len(participants) else np.nan}])
    settings=pd.DataFrame([{"gsr_min_usable_pct":gsr_min_usable_pct,"hr_min_usable_pct":hr_min_usable_pct,"dial_min_usable_pct":dial_min_usable_pct,"require_gsr":require_gsr,"require_hr":require_hr,"require_dial":require_dial}])
    return {"overview":overview,"window_recommendations":out,"participant_recommendations":participants,"settings":settings,"class":["gazepoint_biometric_exclusion_recommendations","list"]}


def baseline_correct_gazepoint_pupil(dat, pupil_col=None, time_col="time", stimulus_onset_col=None, trial_cols=None, baseline_window=(-250,-50), baseline_function="median", correction="subtract", suffix="_baseline_corrected", min_baseline_rows=2, overwrite=False):
    if not isinstance(dat,pd.DataFrame): raise TypeError("`dat` must be a data frame.")
    candidates=["Pupil","pupil","pupil_size","PUPIL","LPMM","RPMM","LPD","RPD"]
    if pupil_col is None: pupil_col=next((c for c in candidates if c in dat and pd.api.types.is_numeric_dtype(dat[c])),None)
    if pupil_col is None or pupil_col not in dat: raise ValueError("No common numeric Gazepoint pupil column was detected. Supply `pupil_col`.")
    if time_col not in dat: raise ValueError(f"Column `{time_col}` was not found in `dat`.")
    if baseline_function not in {"median","mean"} or correction not in {"subtract","divide"}: raise ValueError("Unsupported baseline setting.")
    if len(baseline_window)!=2 or baseline_window[0]>=baseline_window[1]: raise ValueError("`baseline_window` must have start < end.")
    groups=_cols(trial_cols) if trial_cols is not None else [c for c in ["source_participant","participant","USER_FILE","source_file","MEDIA_ID","trial","trial_id"] if c in dat]
    miss=[c for c in groups if c not in dat]
    if miss: raise ValueError("The following `trial_cols` were not found in `dat`: "+", ".join(miss))
    col=pupil_col+suffix
    if col in dat and not overwrite: raise ValueError(f"Output column `{col}` already exists. Use `overwrite = True` to replace it.")
    out=dat.copy();out[col]=np.nan;rows=[]
    for unit,idx in _group_indices(out,groups):
        rel=pd.to_numeric(out.loc[idx,time_col],errors="coerce").to_numpy(float)
        if stimulus_onset_col is not None:
            if stimulus_onset_col not in out: raise ValueError(f"Column `{stimulus_onset_col}` was not found in `dat`.")
            rel=rel-pd.to_numeric(out.loc[idx,stimulus_onset_col],errors="coerce").to_numpy(float)
        mask=np.isfinite(rel)&(rel>=baseline_window[0])&(rel<=baseline_window[1]); base=pd.to_numeric(out.loc[idx,pupil_col],errors="coerce").to_numpy(float)[mask];base=base[np.isfinite(base)];status="baseline_corrected";value=np.nan
        if len(base)<min_baseline_rows: status="insufficient_baseline_rows"
        else:
            value=float(np.median(base) if baseline_function=="median" else np.mean(base));x=pd.to_numeric(out.loc[idx,pupil_col],errors="coerce").to_numpy(float);corr=x-value if correction=="subtract" else x/value;corr[~np.isfinite(corr)]=np.nan;out.loc[idx,col]=corr
        rows.append({"unit_id":unit,"pupil_col":pupil_col,"output_col":col,"n_rows":len(idx),"n_baseline_rows":int(mask.sum()),"n_finite_baseline_rows":len(base),"baseline_value":value,"status":status})
    tab=pd.DataFrame(rows);good=int((tab.status=="baseline_corrected").sum());status="pupil_baseline_correction_complete" if good==len(tab) else ("pupil_baseline_correction_partial" if good else "pupil_baseline_correction_failed")
    out.attrs["pupil_baseline_summary"]={"input_rows":len(out),"trial_count":len(tab),"corrected_trials":good,"problem_trials":len(tab)-good,"pupil_col":pupil_col,"output_col":col,"correction":correction,"baseline_function":baseline_function,"baseline_window":f"{baseline_window[0]} to {baseline_window[1]}","status":status,"interpretation":"Pupil baseline correction expresses pupil size relative to a trial-level reference period; it does not infer cognition or diagnosis."}
    out.attrs["pupil_baseline_table"]=tab.to_dict("records");out.attrs["pupil_baseline_settings"]={"pupil_col":pupil_col,"time_col":time_col,"stimulus_onset_col":stimulus_onset_col,"trial_cols":groups,"baseline_window":list(baseline_window),"baseline_function":baseline_function,"correction":correction,"suffix":suffix,"min_baseline_rows":min_baseline_rows,"overwrite":overwrite};return out


def plot_gazepoint_saccade_main_sequence(dat, amplitude_col=None, peak_velocity_col=None, group_col=None, log_axes=True, add_smoother=True, main="Gazepoint saccade main-sequence diagnostic"):
    if not isinstance(dat,pd.DataFrame): raise TypeError("`dat` must be a data frame.")
    if amplitude_col is None: amplitude_col=next((c for c in ["saccade_amplitude","amplitude","amplitude_deg","SACC_AMPLITUDE"] if c in dat and pd.api.types.is_numeric_dtype(dat[c])),None)
    if peak_velocity_col is None: peak_velocity_col=next((c for c in ["peak_velocity","peak_velocity_deg_s","saccade_peak_velocity","SACC_PEAK_VELOCITY"] if c in dat and pd.api.types.is_numeric_dtype(dat[c])),None)
    if amplitude_col is None or peak_velocity_col is None: raise ValueError("Could not detect required saccade kinematic columns.")
    if group_col is not None and group_col not in dat: raise ValueError(f"Column `{group_col}` was not found in `dat`.")
    x=pd.to_numeric(dat[amplitude_col],errors="coerce");y=pd.to_numeric(dat[peak_velocity_col],errors="coerce");plot_dat=dat[np.isfinite(x)&np.isfinite(y)&(x>0)&(y>0)].copy()
    if plot_dat.empty: raise ValueError("No finite positive amplitude/peak-velocity rows are available.")
    xp=np.log10(plot_dat[amplitude_col].to_numpy(float)) if log_axes else plot_dat[amplitude_col].to_numpy(float);yp=np.log10(plot_dat[peak_velocity_col].to_numpy(float)) if log_axes else plot_dat[peak_velocity_col].to_numpy(float)
    fig,ax=plt.subplots();ax.scatter(xp,yp,s=20);ax.set_title(main);ax.set_xlabel(f"log10({amplitude_col})" if log_axes else amplitude_col);ax.set_ylabel(f"log10({peak_velocity_col})" if log_axes else peak_velocity_col)
    if add_smoother and len(plot_dat)>=5:
        try:
            from statsmodels.nonparametric.smoothers_lowess import lowess
            sm=lowess(yp,xp,return_sorted=True);ax.plot(sm[:,0],sm[:,1])
        except Exception: pass
    return {"figure":fig,"data":plot_dat,"settings":{"amplitude_col":amplitude_col,"peak_velocity_col":peak_velocity_col,"group_col":group_col,"log_axes":bool(log_axes),"add_smoother":bool(add_smoother)},"interpretation":"This is a saccade-kinematic quality diagnostic and requires valid saccade-level data."}


def simulate_gazepoint_eye_data(params=None):
    if params is None: params={}
    if not isinstance(params,dict): raise TypeError("`params` must be a named list/dict.")
    def scalar(name,default,lo=None,hi=None):
        v=params.get(name,default)
        if not isinstance(v,(int,float,np.number)) or not np.isfinite(v): raise ValueError(f"`params${name}` must be a single finite numeric value.")
        if lo is not None and v<lo: raise ValueError(f"`params${name}` must be >= {lo}.")
        if hi is not None and v>hi: raise ValueError(f"`params${name}` must be <= {hi}.")
        return float(v)
    rng=np.random.default_rng(params.get("seed"));sr=scalar("sampling_rate_hz",60,1);duration=params.get("duration_s")
    n=params.get("n")
    if n is None: n=600 if duration is None else max(1,int(round(scalar("duration_s",duration,.001)*sr)))
    n=int(scalar("n",n,1));bounds=np.asarray(params.get("screen_bounds",[0,1,0,1]),float)
    if bounds.size!=4 or not np.isfinite(bounds).all(): raise ValueError("`params$screen_bounds` must be c(x_min, x_max, y_min, y_max).")
    t=np.arange(n)/sr; fix_mean=scalar("fixation_mean_s",.35,.01);fix_sd=scalar("fixation_sd_s",.10,0);noise=scalar("gaze_noise_sd",.015,0);sacc=max(1,int(scalar("saccade_samples",3,1)))
    nf=params.get("n_fixations");nf=max(1,int(round((t[-1]-t[0])/fix_mean))) if nf is None else max(1,int(nf))
    lens=np.maximum(sacc+2,np.rint(rng.normal(fix_mean*sr,fix_sd*sr,nf)).astype(int)).tolist()
    while sum(lens)<n:lens.append(int(rng.choice(lens)))
    over=sum(lens)-n;lens[-1]-=over;lens=[v for v in lens if v>0];nf=len(lens)
    cx=rng.uniform(bounds[0]+.08,bounds[1]-.08,nf);cy=rng.uniform(bounds[2]+.08,bounds[3]-.08,nf);gx=np.empty(n);gy=np.empty(n);fid=np.empty(n,int);start=0
    for i,L in enumerate(lens):
        end=min(n,start+L);idx=np.arange(start,end);gx[idx]=cx[i]+rng.normal(0,noise,len(idx));gy[idx]=cy[i]+rng.normal(0,noise,len(idx));fid[idx]=i+1
        if i>0 and len(idx)>sacc:
            tr=idx[:min(sacc,len(idx))];a=np.linspace(0,1,len(tr));gx[tr]=(1-a)*cx[i-1]+a*cx[i]+rng.normal(0,noise*2,len(tr));gy[tr]=(1-a)*cy[i-1]+a*cy[i]+rng.normal(0,noise*2,len(tr))
        start=end
    gx=np.clip(gx,bounds[0],bounds[1]);gy=np.clip(gy,bounds[2],bounds[3])
    rate=scalar("blink_rate_per_min",15,0);bdm=scalar("blink_duration_mean_s",.15,.001);bds=scalar("blink_duration_sd_s",.04,0);nb=int(rng.poisson(rate*n/sr/60));blink=np.zeros(n,bool);bid=np.full(n,np.nan)
    for j in range(nb):
        L=max(1,int(round(rng.normal(bdm*sr,bds*sr))));st=int(rng.integers(0,max(1,n-L)));ix=np.arange(st,min(n,st+L));blink[ix]=True;bid[ix]=j+1
    pupil_mean=scalar("pupil_mean",3.2,0);pupil_sd=scalar("pupil_sd",.08,0);drift_sd=scalar("pupil_drift_sd",.003,0);base=pupil_mean+np.cumsum(rng.normal(0,drift_sd,n))+rng.normal(0,pupil_sd,n);lpd=base+rng.normal(0,pupil_sd/3,n);rpd=base+rng.normal(0,pupil_sd/3,n);lpv=np.ones(n,int);rpv=np.ones(n,int);lpd[blink]=np.nan;rpd[blink]=np.nan;lpv[blink]=0;rpv[blink]=0
    valid=np.ones(n,bool)
    if bool(params.get("include_invalid_gaze",False)):
        prop=scalar("invalid_gaze_prop",.02,0,1);nbad=max(1,int(round(n*prop))) if prop>0 else 0
        if nbad:
            bad=rng.choice(n,min(nbad,n),replace=False);gx[bad]=rng.uniform(bounds[1]+.05,bounds[1]+.5,len(bad));gy[bad]=rng.uniform(bounds[2],bounds[3],len(bad));valid[bad]=False
    out=pd.DataFrame({"participant":str(params.get("participant_id","P01")),"trial":str(params.get("trial_id","T01")),"sample_id":np.arange(1,n+1),"time_s":t,"MSTIMER":np.rint(t*1000).astype(int),"BPOGX":gx,"BPOGY":gy,"FPOGX":gx,"FPOGY":gy,"LPD":lpd,"RPD":rpd,"LPV":lpv,"RPV":rpv,"fixation_id":fid,"in_blink":blink,"blink_id":bid,"gaze_valid_simulated":valid})
    out.attrs["simulation_params"]=dict(params);out.attrs["sampling_rate_hz"]=sr;out.attrs["screen_bounds"]=bounds.tolist();return out


def simulate_gazepoint_biometrics(n_seconds=120,sampling_rate=60,participant_id="sim_p1",scr_onsets=None,scr_rate_per_min=4,pulse_rate_bpm=72,respiration_rate_bpm=15,eda_noise_sd=.01,ppg_noise_sd=.02,include_ttl=True,seed=None):
    if not np.isfinite(n_seconds) or n_seconds<=0: raise ValueError("`n_seconds` must be a positive number.")
    if not np.isfinite(sampling_rate) or sampling_rate<=0: raise ValueError("`sampling_rate` must be a positive number.")
    rng=np.random.default_rng(seed);time=np.arange(0,n_seconds+1/sampling_rate/2,1/sampling_rate);n=len(time)
    if scr_onsets is None:
        ne=max(1,round(n_seconds/60*scr_rate_per_min));scr=np.sort(rng.uniform(5,max(6,n_seconds-5),ne))
    else:scr=np.asarray(scr_onsets,float)
    scr=scr[np.isfinite(scr)&(scr>=0)&(scr<=n_seconds)];amps=rng.uniform(.03,.20,len(scr));eda=1+.001*time
    for onset,amp in zip(scr,amps):
        rt=np.maximum(0,time-onset);resp=np.exp(-rt/3)-np.exp(-rt/.7);resp[resp<0]=0
        if resp.max()>0:resp/=resp.max()
        eda+=amp*resp
    eda+=rng.normal(0,eda_noise_sd,n);pi=60/pulse_rate_bpm;pulse=np.arange(.5,n_seconds+1e-12,pi)+rng.normal(0,pi*.03,len(np.arange(.5,n_seconds+1e-12,pi)));pulse=pulse[(pulse>=0)&(pulse<=n_seconds)];respiration=1+.15*np.sin(2*np.pi*(respiration_rate_bpm/60)*time);ppg=np.zeros(n)
    for pt in pulse:ppg+=np.exp(-.5*((time-pt)/.06)**2)
    ppg*=respiration
    if ppg.max()>0:ppg/=ppg.max()
    ppg+=rng.normal(0,ppg_noise_sd,n);ibi=np.full(n,pi)
    if len(pulse)>=2:ibi=np.interp(time,pulse[1:],np.diff(pulse),left=np.diff(pulse)[0],right=np.diff(pulse)[-1])
    hr=60/ibi;ttl=np.zeros(n,int)
    if include_ttl:
        for onset in scr:ttl[np.argmin(np.abs(time-onset))]=1
    dat=pd.DataFrame({"participant_id":participant_id,"CNT":time,"GSR_US":eda,"HRP":ppg,"HR":hr,"IBI":ibi,"TTL0":ttl});truth=pd.DataFrame({"event_id":np.arange(1,len(scr)+1),"onset":scr,"amplitude":amps,"tau0":3.,"tau1":.7});ptruth=pd.DataFrame({"pulse_id":np.arange(1,len(pulse)+1),"peak_time":pulse,"expected_ibi":pi})
    return {"overview":pd.DataFrame([{"rows":len(dat),"n_seconds":n_seconds,"sampling_rate_hz":sampling_rate,"scr_events":len(truth),"pulse_peaks":len(ptruth),"status":"synthetic_gazepoint_biometrics_created","interpretation":"Synthetic signals are for teaching, examples, tests, and model validation; they are not real participant physiology."}]),"data":dat,"ground_truth":{"scr_events":truth,"pulse_peaks":ptruth,"respiration_rate_bpm":respiration_rate_bpm,"pulse_rate_bpm":pulse_rate_bpm},"settings":{"n_seconds":n_seconds,"sampling_rate":sampling_rate,"participant_id":participant_id,"scr_onsets":scr.tolist(),"scr_rate_per_min":scr_rate_per_min,"pulse_rate_bpm":pulse_rate_bpm,"respiration_rate_bpm":respiration_rate_bpm,"eda_noise_sd":eda_noise_sd,"ppg_noise_sd":ppg_noise_sd,"include_ttl":include_ttl,"seed":seed},"class":["gazepoint_biometrics_simulation","list"]}
