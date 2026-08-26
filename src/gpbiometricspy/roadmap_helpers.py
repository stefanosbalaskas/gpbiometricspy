from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import platform
import warnings
import builtins

import numpy as np
import pandas as pd
from scipy import stats

from ._helpers import ensure_df, guess_col, time_seconds, trapz


_EXACT_DICTIONARY = {
    "time_s": ["time_s", "time", "timestamp", "TIME", "TIME_TICK", "MSTIMER", "CNT"],
    "participant": ["participant", "participant_id", "subject", "subject_id", "SUBJECT", "P"],
    "trial": ["trial", "trial_id", "TRIAL", "stimulus", "stimulus_id", "screen"],
    "pupil_left": ["pupil_left", "left_pupil", "LPD", "LPMM", "left_pupil_diameter"],
    "pupil_right": ["pupil_right", "right_pupil", "RPD", "RPMM", "right_pupil_diameter"],
    "gaze_x": ["gaze_x", "x", "BPOGX", "FPOGX", "GPOGX", "CX"],
    "gaze_y": ["gaze_y", "y", "BPOGY", "FPOGY", "GPOGY", "CY"],
    "validity_left": ["validity_left", "left_validity", "LPV", "LVALID", "left_valid"],
    "validity_right": ["validity_right", "right_validity", "RPV", "RVALID", "right_valid"],
    "fixation_id": ["fixation_id", "fix_id", "FPOGID", "fixation"],
    "AOI": ["AOI", "aoi", "aoi_name", "AOI_NAME", "area_of_interest"],
    "GSR": ["GSR", "GSR_US", "EDA", "eda", "skin_conductance", "conductance"],
    "PPG": ["PPG", "BVP", "HRP", "ppg", "bvp", "pulse"],
    "HR": ["HR", "heart_rate", "heartrate", "bpm"],
    "IBI": ["IBI", "RRI", "RR", "NN", "ibi_ms", "rr_ms"],
    "DIAL": ["DIAL", "dial", "engagement", "engagement_dial"],
    "TTL": ["TTL", "TTL0", "TTL1", "marker", "event_marker", "USER", "USER_DATA"],
}


def _df(data, name="data") -> pd.DataFrame:
    return ensure_df(data, name).copy()


def _list_cols(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def _groups(df: pd.DataFrame, cols=None):
    cols = _list_cols(cols)
    if not cols:
        return [("all", np.arange(len(df), dtype=int), {})]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError("Missing grouping columns: " + ", ".join(missing))
    work = df.reset_index(drop=True)
    by = cols[0] if len(cols) == 1 else cols
    out = []
    for key, block in work.groupby(by, sort=True, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        label = " | ".join(map(str, key))
        vals = dict(zip(cols, key))
        out.append((label, block.index.to_numpy(dtype=int), vals))
    return out


def _numeric(values):
    return pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)


def _guess(df, candidates, label, required=True):
    return guess_col(df, candidates, label, required)


def _pupil_cols(df: pd.DataFrame, pupil_cols=None):
    if pupil_cols is not None:
        cols = _list_cols(pupil_cols)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError("Missing pupil columns: " + ", ".join(missing))
        return cols
    cols = []
    for c in df.columns:
        s = str(c)
        low = s.lower()
        hit = ("pupil" in low or s.upper() in {"LPD", "RPD"} or "diameter" in low)
        reject = any(t in low for t in ["valid", "flag", "blink", "clean", "imputed", "outlier", "spike", "was_"])
        if hit and not reject and pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    if not cols:
        raise ValueError("Could not identify pupil columns. Supply `pupil_cols` explicitly.")
    return cols


def _validity_for_pupil(df: pd.DataFrame, pupil_col: str):
    up = str(pupil_col).upper()
    if up == "LPD":
        candidates = ["LPV", "left_pupil_valid", "pupil_left_valid"]
    elif up == "RPD":
        candidates = ["RPV", "right_pupil_valid", "pupil_right_valid"]
    else:
        candidates = [f"{pupil_col}_valid", f"{pupil_col}_validity"]
    return _guess(df, candidates, "pupil validity", False)


def _standardize_events(events, event_time_col=None, event_id_col=None, event_label_col=None):
    if isinstance(events, (list, tuple, np.ndarray, pd.Series)) and not isinstance(events, pd.DataFrame):
        arr = _numeric(events)
        return pd.DataFrame({
            "event_id": np.arange(1, len(arr) + 1),
            "event_time": arr,
            "event_label": [f"event_{i}" for i in range(1, len(arr) + 1)],
        })
    if isinstance(events, (str, Path)):
        return import_gazepoint_event_log(events, time_col=event_time_col, id_col=event_id_col, event_col=event_label_col)
    ev = _df(events, "events")
    if event_time_col is None:
        event_time_col = _guess(ev, ["event_time", "time_s", "time", "timestamp", "onset", "onset_time", "trial_onset", "stimulus_onset"], "event time", True)
    if event_time_col not in ev.columns:
        raise ValueError("`event_time_col` not found in `events`.")
    if event_id_col is None:
        event_id_col = _guess(ev, ["event_id", "trial_id", "trial", "stimulus", "screen"], "event id", False)
    if event_label_col is None:
        event_label_col = _guess(ev, ["event_label", "label", "event", "condition", "type", "stimulus"], "event label", False)
    out = ev.copy()
    out["event_time"] = time_seconds(out[event_time_col])
    out["event_id"] = out[event_id_col].to_numpy() if event_id_col in out.columns else np.arange(1, len(out) + 1)
    out["event_label"] = out[event_label_col].astype(str).to_numpy() if event_label_col in out.columns else [f"event_{i}" for i in range(1, len(out) + 1)]
    first = ["event_id", "event_time", "event_label"]
    return out[first + [c for c in out.columns if c not in first]].reset_index(drop=True)


def _local_peaks(x, min_distance=1):
    x = np.asarray(x, dtype=float)
    if len(x) < 3:
        return np.array([], dtype=int)
    peaks = np.flatnonzero((x[1:-1] > x[:-2]) & (x[1:-1] >= x[2:])) + 1
    peaks = peaks[np.isfinite(x[peaks])]
    if len(peaks) == 0 or min_distance <= 1:
        return peaks
    kept = []
    for p in peaks:
        if not kept or p - kept[-1] >= min_distance:
            kept.append(int(p))
        elif x[p] > x[kept[-1]]:
            kept[-1] = int(p)
    return np.asarray(kept, dtype=int)


def _r_mean(x):
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.mean(a)) if len(a) else np.nan


def _r_sd(x):
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.std(a, ddof=1)) if len(a) > 1 else np.nan


def compute_gazepoint_scr_habituation(data, amplitude_col=None, trial_col=None, subject_col=None, method="linear", min_trials=3):
    if method not in {"linear", "log_linear", "ratio"}:
        raise ValueError("`method` must be 'linear', 'log_linear', or 'ratio'.")
    if isinstance(data, (list, tuple, np.ndarray, pd.Series)) and not isinstance(data, pd.DataFrame):
        amp = _numeric(data)
        dat = pd.DataFrame({".subject": "all", ".trial": np.arange(1, len(amp) + 1), ".amplitude": amp})
        subject_col, trial_col, amplitude_col = ".subject", ".trial", ".amplitude"
    else:
        dat = _df(data)
        if amplitude_col is None:
            amplitude_col = _guess(dat, ["scr_amplitude", "amplitude", "SCR", "response_amplitude"], "SCR amplitude", True)
        if trial_col is None:
            trial_col = _guess(dat, ["trial", "trial_id", "event_id", "order", "trial_order"], "trial/order", False)
        if trial_col is None:
            dat[".trial"] = np.arange(1, len(dat) + 1)
            trial_col = ".trial"
        if subject_col is None:
            dat[".subject"] = "all"
            subject_col = ".subject"
    rows = []
    for _, idx, vals in _groups(dat, subject_col):
        amp = _numeric(dat.iloc[idx][amplitude_col])
        trial = _numeric(dat.iloc[idx][trial_col])
        if np.all(~np.isfinite(trial)):
            trial = np.arange(1, len(amp) + 1, dtype=float)
        ok = np.isfinite(amp) & np.isfinite(trial)
        amp, trial = amp[ok], trial[ok]
        order = np.argsort(trial, kind="stable")
        amp, trial = amp[order], trial[order]
        n = len(amp)
        split_n = max(1, n // 3)
        first_mean = _r_mean(amp[:split_n]) if n else np.nan
        last_mean = _r_mean(amp[-split_n:]) if n else np.nan
        ratio = last_mean / first_mean if np.isfinite(first_mean) and first_mean != 0 else np.nan
        intercept = slope = p_value = r_value = np.nan
        if n >= int(min_trials) and method != "ratio":
            y = np.log1p(np.maximum(amp, 0)) if method == "log_linear" else amp
            lr = stats.linregress(trial, y)
            intercept, slope, p_value, r_value = float(lr.intercept), float(lr.slope), float(lr.pvalue), float(lr.rvalue)
        subject = dat.iloc[idx[0]][subject_col]
        direction = "decreasing" if np.isfinite(slope) and slope < 0 else ("increasing" if np.isfinite(slope) and slope > 0 else "undetermined")
        rows.append({"subject": str(subject), "n_trials": n, "method": method, "intercept": intercept, "habituation_slope": slope, "p_value": p_value, "r_value": r_value, "first_mean": first_mean, "last_mean": last_mean, "last_first_ratio": ratio, "habituation_direction": direction})
    return pd.DataFrame(rows)


def summarize_gazepoint_scr_recovery(data, events, pre=1, post=6, time_col=None, signal_col=None, event_time_col=None, event_id_col=None, baseline_window=None, peak_window=(0.5, 4), recovery_fraction=0.5):
    df = _df(data)
    if pre < 0 or post <= 0:
        raise ValueError("`pre` must be non-negative and `post` must be positive.")
    baseline_window = (-pre, 0) if baseline_window is None else baseline_window
    time_col = time_col or _guess(df, ["time_s", "time", "TIME", "timestamp", "MSTIMER"], "time", True)
    signal_col = signal_col or _guess(df, ["GSR", "EDA", "SCR", "eda", "gsr", "skin_conductance"], "EDA/GSR signal", True)
    ev = _standardize_events(events, event_time_col, event_id_col)
    t, sig = time_seconds(df[time_col]), _numeric(df[signal_col])
    rows = []
    for _, e in ev.iterrows():
        et = float(e.event_time); rel = t - et; idx = np.flatnonzero((rel >= -pre) & (rel <= post))
        base = peak_amp = peak_latency = target = recovery_latency = recovery_slope = np.nan; recovered = False
        if len(idx):
            rr, yy = rel[idx], sig[idx]
            bm = (rr >= baseline_window[0]) & (rr <= baseline_window[1])
            base = _r_mean(yy[bm]) if bm.any() else np.nan
            bc = yy - base
            pm = (rr >= peak_window[0]) & (rr <= peak_window[1]) & np.isfinite(bc)
            if pm.any():
                p_candidates = np.flatnonzero(pm); p = p_candidates[np.argmax(bc[p_candidates])]
                peak_amp, peak_latency = float(bc[p]), float(rr[p]); target = peak_amp * recovery_fraction
                after = np.flatnonzero((rr > peak_latency) & (rr <= post) & np.isfinite(bc))
                rec = after[bc[after] <= target]
                if len(rec): recovery_latency, recovered = float(rr[rec[0]]), True
                if len(after) >= 3:
                    recovery_slope = float(stats.linregress(rr[after], bc[after]).slope)
        rows.append({"event_id": e.event_id, "event_time": et, "event_label": e.event_label, "n_samples": len(idx), "baseline_mean": base, "peak_amplitude": peak_amp, "peak_latency_s": peak_latency, "recovery_target": target, "recovery_latency_s": recovery_latency, "recovery_slope": recovery_slope, "recovered": bool(recovered)})
    return pd.DataFrame(rows)


def summarize_gazepoint_pupil_events(data, events, pre=1, post=3, time_col=None, pupil_col=None, event_time_col=None, event_id_col=None, baseline_window=None, response_window=(0, 3)):
    df = _df(data)
    baseline_window = (-pre, 0) if baseline_window is None else baseline_window
    time_col = time_col or _guess(df, ["time_s", "time", "TIME", "timestamp", "MSTIMER"], "time", True)
    pupil_col = pupil_col or _pupil_cols(df)[0]
    ev = _standardize_events(events, event_time_col, event_id_col)
    t, pupil = time_seconds(df[time_col]), _numeric(df[pupil_col])
    rows = []
    for _, e in ev.iterrows():
        et = float(e.event_time); rel = t - et; idx = np.flatnonzero((rel >= -pre) & (rel <= post)); rr, pp = rel[idx], pupil[idx]
        bm = (rr >= baseline_window[0]) & (rr <= baseline_window[1]); base = _r_mean(pp[bm]) if bm.any() else np.nan; bc = pp - base
        rm = (rr >= response_window[0]) & (rr <= response_window[1]) & np.isfinite(bc)
        peak = latency = mean = auc = np.nan
        if rm.any():
            cand = np.flatnonzero(rm); p = cand[np.argmax(bc[cand])]
            peak, latency, mean, auc = float(bc[p]), float(rr[p]), _r_mean(bc[rm]), trapz(rr[rm], bc[rm])
        rows.append({"event_id": e.event_id, "event_time": et, "event_label": e.event_label, "n_samples": len(idx), "baseline_mean": base, "pupil_peak_dilation": peak, "pupil_peak_latency_s": latency, "pupil_mean_dilation": mean, "pupil_auc": auc})
    return pd.DataFrame(rows)


def summarize_gazepoint_tracking(data, pupil_cols=None, x_col=None, y_col=None, group_cols=None, screen_bounds=(0, 1, 0, 1), nonpositive_is_invalid=True):
    df = _df(data)
    try: pupils = _pupil_cols(df, pupil_cols)
    except ValueError: pupils = []
    x_col = x_col or _guess(df, ["BPOGX", "FPOGX", "GPOGX", "x", "gaze_x"], "gaze x", False)
    y_col = y_col or _guess(df, ["BPOGY", "FPOGY", "GPOGY", "y", "gaze_y"], "gaze y", False)
    rows = []
    for label, idx, vals in _groups(df, group_cols):
        z = df.iloc[idx]
        pupil_valid = np.full(len(z), np.nan)
        if pupils:
            mat = np.ones((len(z), len(pupils)), bool)
            for j, c in enumerate(pupils):
                x = _numeric(z[c]); valid = np.isfinite(x)
                if nonpositive_is_invalid: valid &= x > 0
                vc = _validity_for_pupil(df, c)
                if vc is not None:
                    vv = _numeric(z[vc]); valid &= np.isfinite(vv) & (vv > 0)
                mat[:, j] = valid
            pupil_valid = np.all(mat, axis=1)
        gaze_valid = np.full(len(z), np.nan)
        if x_col is not None and y_col is not None:
            gx, gy = _numeric(z[x_col]), _numeric(z[y_col])
            gaze_valid = np.isfinite(gx) & np.isfinite(gy) & (gx >= screen_bounds[0]) & (gx <= screen_bounds[1]) & (gy >= screen_bounds[2]) & (gy <= screen_bounds[3])
        if np.all(pd.isna(pupil_valid)): combined = gaze_valid
        elif np.all(pd.isna(gaze_valid)): combined = pupil_valid
        else: combined = pupil_valid.astype(bool) & gaze_valid.astype(bool)
        def nanmean_bool(v):
            a = np.asarray(v, dtype=float); return float(np.nanmean(a)) if np.isfinite(a).any() else np.nan
        row = dict(vals) if vals else {"group": label}
        row.update({"n_samples": len(z), "pupil_valid_ratio": nanmean_bool(pupil_valid), "gaze_valid_ratio": nanmean_bool(gaze_valid), "tracking_ratio": nanmean_bool(combined), "n_invalid_tracking": int(np.nansum(~np.asarray(combined, dtype=bool))) if not np.all(pd.isna(combined)) else 0})
        rows.append(row)
    return pd.DataFrame(rows)


def audit_gazepoint_pupil_luminance(data, pupil_col=None, luminance_col=None, group_cols=None, threshold=0.30, method="pearson"):
    df = _df(data)
    if method not in {"pearson", "spearman"}: raise ValueError("`method` must be 'pearson' or 'spearman'.")
    pupil_col = pupil_col or _pupil_cols(df)[0]
    luminance_col = luminance_col or _guess(df, ["luminance", "brightness", "lum", "screen_luminance", "stimulus_luminance"], "luminance", True)
    rows=[]
    for label, idx, vals in _groups(df, group_cols):
        z=df.iloc[idx]; x,y=_numeric(z[pupil_col]),_numeric(z[luminance_col]); ok=np.isfinite(x)&np.isfinite(y)
        r=np.nan
        if ok.sum()>=3:
            r=float(stats.pearsonr(x[ok],y[ok]).statistic if method=="pearson" else stats.spearmanr(x[ok],y[ok]).statistic)
        row=dict(vals) if vals else {"group":label}; row.update({"n_complete":int(ok.sum()),"pupil_col":pupil_col,"luminance_col":luminance_col,"correlation":r,"abs_correlation":abs(r) if np.isfinite(r) else np.nan,"threshold":threshold,"flag_luminance_confound":bool(np.isfinite(r) and abs(r)>=threshold),"method":method}); rows.append(row)
    return pd.DataFrame(rows)


def extract_gazepoint_ppg_morphology(data, time_col=None, ppg_col=None, peaks=None, min_peak_distance_s=0.30):
    df=_df(data); time_col=time_col or _guess(df,["time_s","time","TIME","timestamp","MSTIMER"],"time",True); ppg_col=ppg_col or _guess(df,["PPG","BVP","HRP","ppg","bvp","pulse"],"PPG/BVP signal",True)
    t=time_seconds(df[time_col]); sig=_numeric(df[ppg_col]); d=np.diff(t); dt=float(np.nanmedian(d)) if len(d) else np.nan; min_distance=max(1,int(round(min_peak_distance_s/dt))) if np.isfinite(dt) and dt>0 else 1
    if peaks is None: pidx=_local_peaks(sig,min_distance)
    else:
        p=np.asarray(peaks,dtype=float)
        if np.all(np.isfinite(p)&(p>=1)&(p<=len(sig))&(np.abs(p-np.round(p))<1e-8)): pidx=np.round(p).astype(int)-1
        else: pidx=np.array([int(np.argmin(np.abs(t-z))) for z in p],dtype=int)
    pidx=np.unique(np.sort(pidx)); pidx=pidx[(pidx>=2)&(pidx<len(sig)-1)]
    rows=[]
    for i,p in enumerate(pidx):
        lb=0 if i==0 else pidx[i-1]; rb=len(sig)-1 if i==len(pidx)-1 else pidx[i+1]
        left=np.arange(lb,p+1); right=np.arange(p,rb+1); lt=int(left[np.nanargmin(sig[left])]); rt=int(right[np.nanargmin(sig[right])]); amp=float(sig[p]-sig[lt]); half=sig[lt]+amp/2
        lc=left[sig[left]<=half]; rc=right[sig[right]<=half]; lcross=int(np.max(lc)) if len(lc) else lt; rcross=int(np.min(rc)) if len(rc) else rt
        notch_end=min(len(sig)-1,p+max(3,int(round(.35/dt)))) if np.isfinite(dt) and dt>0 else min(len(sig)-1,p+3); nr=np.arange(p,notch_end+1); notch=int(nr[np.nanargmin(sig[nr])]) if len(nr)>=3 else None
        rows.append({"pulse_id":len(rows)+1,"peak_index":p+1,"peak_time":t[p],"peak_value":sig[p],"left_trough_index":lt+1,"right_trough_index":rt+1,"pulse_amplitude":amp,"rise_time_s":t[p]-t[lt],"decay_time_s":t[rt]-t[p],"half_width_s":t[rcross]-t[lcross],"notch_proxy_index":notch+1 if notch is not None else np.nan,"notch_proxy_latency_s":t[notch]-t[p] if notch is not None else np.nan,"notch_proxy_value":sig[notch] if notch is not None else np.nan})
    return pd.DataFrame(rows)


def flag_gazepoint_ppg_quality(data, time_col=None, ppg_col=None, window_s=10, step_s=None, missing_prop_threshold=0.20, flat_sd_threshold=1e-6, outlier_prop_threshold=0.10):
    df=_df(data); step_s=window_s if step_s is None else step_s; time_col=time_col or _guess(df,["time_s","time","TIME","timestamp","MSTIMER"],"time",True); ppg_col=ppg_col or _guess(df,["PPG","BVP","HRP","ppg","bvp","pulse"],"PPG/BVP signal",True)
    t=time_seconds(df[time_col]); sig=_numeric(df[ppg_col]); starts=np.arange(np.nanmin(t),np.nanmax(t)+step_s*0.5,step_s); rows=[]
    for s in starts:
        e=s+window_s; idx=np.flatnonzero((t>=s)&(t<e))
        if not len(idx): continue
        x=sig[idx]; finite=x[np.isfinite(x)]; miss=float(np.mean(~np.isfinite(x))); sd=_r_sd(finite)
        if len(finite): med=float(np.median(finite)); sc=float(np.median(np.abs(finite-med))*1.4826)
        else: med=sc=np.nan
        outlier=0.0 if not len(finite) or not np.isfinite(sc) or sc==0 else float(np.mean(np.abs(finite-med)>5*sc))
        flat=float(np.mean(np.abs(np.diff(finite))<=flat_sd_threshold)) if len(finite)>=2 else np.nan
        ok=bool(miss<=missing_prop_threshold and np.isfinite(sd) and sd>=flat_sd_threshold and outlier<=outlier_prop_threshold)
        rows.append({"segment_id":len(rows)+1,"start_time":s,"end_time":e,"n_samples":len(idx),"missing_prop":miss,"sd_signal":sd,"range_signal":float(np.ptp(finite)) if len(finite) else np.nan,"flatline_prop":flat,"outlier_prop":outlier,"quality_ok":ok,"quality_flag":"ok" if ok else "review"})
    return pd.DataFrame(rows)


def import_gazepoint_event_log(path, time_col=None, event_col=None, id_col=None, sep=None, **kwargs):
    if isinstance(path,pd.DataFrame): dat=_df(path,"event log")
    else:
        p=Path(path)
        if not p.is_file(): raise ValueError("`path` must be an existing event-log path or a data frame.")
        if sep is None:
            first=p.open("r",encoding=kwargs.pop("encoding","utf-8")).readline(); counts={",":first.count(","),";":first.count(";"),"\t":first.count("\t")}; sep=max(counts,key=counts.get)
        dat=pd.read_csv(p,sep=sep,**kwargs); _df(dat,"event log")
    time_col=time_col or _guess(dat,["event_time","time_s","time","timestamp","onset","onset_time","trial_onset","stimulus_onset"],"event time",True); event_col=event_col or _guess(dat,["event_label","label","event","condition","type","stimulus"],"event label",False); id_col=id_col or _guess(dat,["event_id","trial_id","trial","id"],"event id",False)
    out=dat.copy(); out["event_time"]=time_seconds(out[time_col]); out["event_id"]=out[id_col].to_numpy() if id_col in out.columns else np.arange(1,len(out)+1); out["event_label"]=out[event_col].astype(str).to_numpy() if event_col in out.columns else [f"event_{i}" for i in range(1,len(out)+1)]; first=["event_id","event_time","event_label"]; return out[first+[c for c in out.columns if c not in first]].reset_index(drop=True)


def match_gazepoint_events_to_biometrics(data, events, pre=0, post=5, time_col=None, event_time_col=None, event_id_col=None, summary_cols=None, return_="windows", **kwargs):
    if "return" in kwargs: return_=kwargs.pop("return")
    if return_ not in {"windows","summary"}: raise ValueError("`return` must be 'windows' or 'summary'.")
    df=_df(data); time_col=time_col or _guess(df,["time_s","time","TIME","timestamp","MSTIMER"],"time",True); ev=_standardize_events(events,event_time_col,event_id_col); t=time_seconds(df[time_col])
    if summary_cols is None: summary_cols=[c for c in df.columns if c!=time_col and pd.api.types.is_numeric_dtype(df[c])]
    if return_=="windows":
        blocks=[]
        for _,e in ev.iterrows():
            et=float(e.event_time); idx=np.flatnonzero((t>=et-pre)&(t<=et+post))
            if not len(idx): continue
            z=df.iloc[idx].copy(); z["event_id"]=e.event_id; z["event_time"]=et; z["event_label"]=e.event_label; z["relative_time_s"]=t[idx]-et; blocks.append(z)
        return pd.concat(blocks,ignore_index=True) if blocks else pd.DataFrame()
    rows=[]
    for _,e in ev.iterrows():
        et=float(e.event_time); idx=np.flatnonzero((t>=et-pre)&(t<=et+post)); row={"event_id":e.event_id,"event_time":et,"event_label":e.event_label,"n_samples":len(idx)}
        for c in summary_cols:
            x=_numeric(df.iloc[idx][c]); finite=x[np.isfinite(x)]; row[f"{c}_mean"]=_r_mean(x); row[f"{c}_sd"]=_r_sd(x); row[f"{c}_min"]=float(np.min(finite)) if len(finite) else np.nan; row[f"{c}_max"]=float(np.max(finite)) if len(finite) else np.nan; row[f"{c}_missing_prop"]=float(np.mean(~np.isfinite(x))) if len(x) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def assert_gazepoint_columns(data, required, optional=(), mode="error", ignore_case=True):
    df=_df(data); required=_list_cols(required); optional=_list_cols(optional)
    if mode not in {"error","warning","summary"}: raise ValueError("Invalid `mode`.")
    nms=list(df.columns)
    def match_one(c):
        for n in nms:
            if (str(n).lower()==str(c).lower()) if ignore_case else (n==c): return n
        return None
    rows=[]
    for role,cols in [("required",required),("optional",optional)]:
        for c in cols:
            m=match_one(c); rows.append({"column":c,"role":role,"present":m is not None,"matched_name":m})
    summary=pd.DataFrame(rows); missing=[r["column"] for r in rows if r["role"]=="required" and not r["present"]]
    if missing and mode=="error": raise ValueError("Missing required Gazepoint columns: "+", ".join(missing))
    if missing and mode=="warning": warnings.warn("Missing required Gazepoint columns: "+", ".join(missing),RuntimeWarning,stacklevel=2)
    return summary if mode=="summary" else True


def gpbiometrics_info(print=True, include_session=False):
    out={"package":"gpbiometrics","version":"2.0.0","title":"R tools for importing, validating, preprocessing, analysing, plotting, and reporting Gazepoint Biometrics exports.","url":"https://stefanosbalaskas.github.io/gpbiometrics/","bug_reports":"https://github.com/stefanosbalaskas/gpbiometrics/issues","r_version":None,"platform":platform.platform(),"os":platform.system(),"date":datetime.now().date().isoformat(),"python_port":"gpbiometricspy"}
    if include_session: out["session_info"]={"python":platform.python_version(),"platform":platform.platform()}
    if print:
        builtins.print(f"gpbiometrics {out['version']}")
        builtins.print(f"Python port on {out['platform']}")
        builtins.print("URL:", out["url"])
        builtins.print("Bug reports:", out["bug_reports"])
    return out


def audit_gazepoint_export_schema(data, expected_roles=None, dictionary=None, strict=False):
    if isinstance(data,(str,Path)):
        p=Path(data)
        if not p.is_file(): raise ValueError("`path` must be an existing file path.")
        first=p.open("r",encoding="utf-8").readline(); counts={",":first.count(","),";":first.count(";"),"\t":first.count("\t")}; df=pd.read_csv(p,sep=max(counts,key=counts.get))
    else: df=_df(data)
    dictionary=_EXACT_DICTIONARY if dictionary is None else dictionary; expected_roles=list(dictionary) if expected_roles is None else list(expected_roles); low=[str(c).lower() for c in df.columns]; rows=[]
    for role in expected_roles:
        aliases=list(dict.fromkeys([role]+list(dictionary.get(role,[])))); hits=[df.columns[i] for i,n in enumerate(low) if n in {str(a).lower() for a in aliases}]; status="missing" if not hits else ("present" if len(hits)==1 else "ambiguous")
        rec={"missing":f"Add or map a column for role `{role}`.","ambiguous":f"Multiple columns match role `{role}`; standardize explicitly.","present":"OK"}[status]
        rows.append({"role":role,"present":bool(hits),"n_matches":len(hits),"matched_columns":", ".join(map(str,hits)),"status":status,"recommendation":rec})
    out=pd.DataFrame(rows); out.attrs["duplicate_columns"]=[c for i,c in enumerate(df.columns) if c in list(df.columns)[:i]]
    if strict and (out.status=="missing").any(): raise ValueError("Missing required Gazepoint roles: "+", ".join(out.loc[out.status=="missing","role"]))
    return out


def simulate_gazepoint_multimodal_data(n=None, duration_s=20, sampling_rate_hz=50, seed=1, participant="P01", n_trials=4):
    rng=np.random.default_rng(seed); n=max(2,int(duration_s*sampling_rate_hz)+1) if n is None else int(n); t=np.linspace(0,duration_s,n); mst=np.round(t*1000).astype(int)
    trial_num=np.minimum(n_trials,np.floor(t/(duration_s/n_trials if duration_s else 1)).astype(int)+1); trial=np.array([f"T{i}" for i in trial_num]); event_time=np.linspace(2,max(2,duration_s-2),n_trials)
    events=pd.DataFrame({"event_id":[f"E{i}" for i in range(1,n_trials+1)],"event_time":event_time,"event_label":np.resize(["baseline","stimulus"],n_trials),"trial":[f"T{i}" for i in range(1,n_trials+1)],"participant":participant})
    pulse=np.zeros(n)
    for et in event_time: pulse+=np.exp(-((t-(et+1.2))**2)/.20)
    gsr=2+.03*t+.20*pulse+rng.normal(0,.01,n); ppg=np.sin(2*np.pi*1.2*t)+.15*np.sin(2*np.pi*2.4*t); hr=72+4*np.sin(2*np.pi*.08*t)+rng.normal(0,.3,n); ibi=60000/np.maximum(hr,1); dial=50+10*np.sin(2*np.pi*.03*t); ttl=np.zeros(n,dtype=int)
    for et in event_time: ttl[int(np.argmin(np.abs(t-et)))]=1
    biometrics=pd.DataFrame({"time_s":t,"MSTIMER":mst,"participant":participant,"trial":trial,"GSR":gsr,"PPG":ppg,"HR":hr,"IBI":ibi,"DIAL":dial,"TTL":ttl})
    gx=np.clip(.5+.25*np.sin(2*np.pi*.15*t)+rng.normal(0,.02,n),0,1); gy=np.clip(.5+.20*np.cos(2*np.pi*.11*t)+rng.normal(0,.02,n),0,1); pl=3+.15*pulse+rng.normal(0,.02,n); pr=pl+rng.normal(0,.015,n)
    for b in np.linspace(round(n*.20),round(n*.80),2).astype(int):
        span=np.arange(max(0,b-3),min(n,b+2)); pl[span]=np.nan; pr[span]=np.nan
    aoi=np.where(gx<.33,"left",np.where(gx>.67,"right","center")); eye=pd.DataFrame({"time_s":t,"participant":participant,"trial":trial,"pupil_left":pl,"pupil_right":pr,"gaze_x":gx,"gaze_y":gy,"validity_left":np.isfinite(pl).astype(int),"validity_right":np.isfinite(pr).astype(int),"AOI":aoi})
    step=max(1,duration_s/10); fs=np.arange(0,max(0,duration_s-1)+1e-12,step); m=len(fs); tr=np.clip(np.ceil(np.arange(1,m+1)/max(1,m/n_trials)).astype(int),1,n_trials)
    fix=pd.DataFrame({"participant":participant,"trial":[f"T{i}" for i in tr],"fixation_id":np.arange(1,m+1),"start_time":fs,"end_time":np.minimum(fs+.6,duration_s),"duration_s":np.minimum(fs+.6,duration_s)-fs,"AOI":np.resize(["left","center","right"],m),"x":np.resize([.25,.5,.75],m),"y":np.resize([.45,.5,.55],m)})
    return {"biometrics":biometrics,"eye":eye,"events":events,"fixations":fix,"metadata":{"participant":participant,"duration_s":duration_s,"sampling_rate_hz":sampling_rate_hz,"n_samples":n,"synthetic":True}}


def assess_gazepoint_sampling_irregularity(data, time_col=None, group_cols=None, nominal_rate_hz=None, large_gap_factor=3):
    if not isinstance(data,pd.DataFrame): data=pd.DataFrame({"time_s":_numeric(data)}); time_col="time_s"
    df=_df(data); time_col=time_col or _guess(df,_EXACT_DICTIONARY["time_s"],"time",True); rows=[]
    for label,idx,vals in _groups(df,group_cols):
        tt=time_seconds(df.iloc[idx][time_col]); tt=tt[np.isfinite(tt)]; d=np.diff(tt); pos=d[np.isfinite(d)&(d>0)]; med=float(np.median(pos)) if len(pos) else np.nan; rate=1/med if np.isfinite(med) and med>0 else np.nan; jitter=_r_sd(pos); threshold=med*large_gap_factor if np.isfinite(med) else np.nan; dropped=float(np.sum(np.maximum(0,np.round(pos/med)-1))) if np.isfinite(med) and med>0 and len(pos) else np.nan
        row=dict(vals) if vals else {"group":label}; row.update({"n_samples":len(tt),"median_interval_s":med,"effective_rate_hz":rate,"nominal_rate_hz":np.nan if nominal_rate_hz is None else nominal_rate_hz,"jitter_sd_s":jitter,"min_interval_s":float(np.min(pos)) if len(pos) else np.nan,"max_interval_s":float(np.max(pos)) if len(pos) else np.nan,"n_negative_steps":int(np.sum(d<0)),"n_zero_steps":int(np.sum(d==0)),"n_large_gaps":int(np.sum(pos>threshold)) if np.isfinite(threshold) else np.nan,"estimated_dropped_samples":dropped}); rows.append(row)
    return pd.DataFrame(rows)


def diagnose_gazepoint_sync_drift(reference, target=None, reference_time_col=None, target_time_col=None, max_pairs=None):
    if isinstance(reference,pd.DataFrame): reference_time_col=reference_time_col or _guess(reference,_EXACT_DICTIONARY["time_s"],"reference time",True); ref=time_seconds(reference[reference_time_col])
    else: ref=time_seconds(reference)
    if target is None: raise ValueError("Supply `target` timestamps or a target data frame.")
    if isinstance(target,pd.DataFrame): target_time_col=target_time_col or _guess(target,_EXACT_DICTIONARY["time_s"],"target time",True); tar=time_seconds(target[target_time_col])
    else: tar=time_seconds(target)
    n=min(len(ref),len(tar)); n=min(n,int(max_pairs)) if max_pairs is not None else n
    if n<2: raise ValueError("At least two matched timestamp pairs are required.")
    ref,tar=np.asarray(ref[:n]),np.asarray(tar[:n]); ok=np.isfinite(ref)&np.isfinite(tar); ref,tar=ref[ok],tar[ok]
    if len(ref)<2: raise ValueError("At least two finite matched timestamp pairs are required.")
    lag=tar-ref; lr=stats.linregress(ref,lag); fitted=lr.intercept+lr.slope*ref; resid=lag-fitted
    lag_table=pd.DataFrame({"pair_id":np.arange(1,len(ref)+1),"reference_time":ref,"target_time":tar,"lag_s":lag,"fitted_lag_s":fitted,"residual_lag_s":resid}); summary=pd.DataFrame([{"n_pairs":len(ref),"median_lag_s":float(np.median(lag)),"mean_lag_s":float(np.mean(lag)),"min_lag_s":float(np.min(lag)),"max_lag_s":float(np.max(lag)),"lag_range_s":float(np.ptp(lag)),"drift_slope_s_per_s":float(lr.slope),"drift_intercept_s":float(lr.intercept),"residual_sd_s":_r_sd(resid)}]); return {"summary":summary,"lag_table":lag_table}


def summarize_gazepoint_aoi_dwell(data, time_col=None, aoi_col=None, duration_col=None, group_cols=None, valid_col=None):
    df=_df(data); aoi_col=aoi_col or _guess(df,_EXACT_DICTIONARY["AOI"],"AOI",True); duration_col=duration_col or _guess(df,["duration_s","duration","fixation_duration","FPOGD"],"duration",False)
    if time_col is None and duration_col is None: time_col=_guess(df,_EXACT_DICTIONARY["time_s"],"time",True)
    elif time_col is None: time_col=_guess(df,_EXACT_DICTIONARY["time_s"],"time",False)
    rows=[]
    for label,idx,vals in _groups(df,group_cols):
        z=df.iloc[idx].copy().reset_index(drop=True); aoi=z[aoi_col].astype(object).to_numpy(); valid=np.ones(len(z),bool)
        if valid_col is not None and valid_col in z.columns: vv=_numeric(z[valid_col]); valid=np.isfinite(vv)&(vv>0)
        if duration_col is not None and duration_col in z.columns:
            duration=_numeric(z[duration_col]); tm=time_seconds(z[time_col]) if time_col is not None and time_col in z.columns else np.arange(1,len(z)+1,dtype=float)
        else:
            tm=time_seconds(z[time_col]); order=np.argsort(tm,kind="stable"); z=z.iloc[order].reset_index(drop=True); aoi=aoi[order]; valid=valid[order]; tm=tm[order]; d=np.diff(tm); pos=d[np.isfinite(d)&(d>0)]; med=float(np.median(pos)) if len(pos) else 0.; duration=np.r_[d,med]; duration[(~np.isfinite(duration))|(duration<0)]=0
        unique=[]
        for a in aoi:
            if pd.notna(a) and str(a)!="" and a not in unique: unique.append(a)
        start=float(np.nanmin(tm)) if np.isfinite(tm).any() else np.nan
        for aa in unique:
            same=np.array([pd.notna(x) and x==aa for x in aoi]); ina=same&valid; prev=np.r_[False,ina[:-1]]; first=np.flatnonzero(ina); row=dict(vals) if vals else {"group":label}; row.update({"AOI":aa,"n_samples":int(same.sum()),"valid_samples":int(ina.sum()),"dwell_time_s":float(np.nansum(duration[ina])),"entry_count":int(np.sum(ina&~prev)),"latency_to_first_entry_s":float(tm[first[0]]-start) if len(first) and np.isfinite(start) else np.nan,"valid_ratio":float(np.mean(valid[same])) if same.any() else np.nan}); rows.append(row)
    return pd.DataFrame(rows)


def summarize_gazepoint_scanpath_metrics(data, x_col=None, y_col=None, time_col=None, aoi_col=None, fixation_id_col=None, group_cols=None, min_saccade_distance=0.02):
    df=_df(data); x_col=x_col or _guess(df,["gaze_x","x","BPOGX","FPOGX","GPOGX"],"x",True); y_col=y_col or _guess(df,["gaze_y","y","BPOGY","FPOGY","GPOGY"],"y",True); time_col=time_col or _guess(df,_EXACT_DICTIONARY["time_s"],"time",False); aoi_col=aoi_col or _guess(df,_EXACT_DICTIONARY["AOI"],"AOI",False); fixation_id_col=fixation_id_col or _guess(df,_EXACT_DICTIONARY["fixation_id"],"fixation id",False); rows=[]
    for label,idx,vals in _groups(df,group_cols):
        z=df.iloc[idx].copy()
        if time_col is not None and time_col in z.columns: z=z.iloc[np.argsort(time_seconds(z[time_col]),kind="stable")]
        x,y=_numeric(z[x_col]),_numeric(z[y_col]); ok=np.isfinite(x)&np.isfinite(y); x,y=x[ok],y[ok]; dist=np.sqrt(np.diff(x)**2+np.diff(y)**2) if len(x)>=2 else np.array([])
        fix_count=len(pd.unique(z[fixation_id_col].dropna())) if fixation_id_col is not None and fixation_id_col in z.columns else len(x); trans_count=np.nan; entropy=np.nan
        if aoi_col is not None and aoi_col in z.columns:
            a=[str(v) for v in z[aoi_col] if pd.notna(v) and str(v)!=""]
            if a:
                collapsed=[a[0]]+[a[i] for i in range(1,len(a)) if a[i]!=a[i-1]]; trans_count=max(0,len(collapsed)-1); trans=[f"{collapsed[i]}->{collapsed[i+1]}" for i in range(len(collapsed)-1)]
                if trans:
                    counts=pd.Series(trans).value_counts().to_numpy(float); p=counts/counts.sum(); entropy=float(-np.sum(p*np.log2(p)))
        row=dict(vals) if vals else {"group":label}; row.update({"n_points":len(x),"fixation_count":fix_count,"path_length":float(np.sum(dist)),"mean_step_length":float(np.mean(dist)) if len(dist) else np.nan,"saccade_count":int(np.sum(dist>min_saccade_distance)),"regression_like_count":int(np.sum(np.diff(x)<-min_saccade_distance)) if len(x)>=2 else 0,"aoi_transition_count":trans_count,"transition_entropy":entropy}); rows.append(row)
    return pd.DataFrame(rows)


def create_gazepoint_analysis_manifest(files=None, settings=None, outputs=None, exclusions=None, path=None, include_session=True):
    settings={} if settings is None else settings
    if not isinstance(settings,dict): raise TypeError("`settings` must be a named list.")
    paths=[] if files is None else ([files] if isinstance(files,(str,Path)) else list(files)); frows=[]
    for f in paths:
        p=Path(f); st=p.stat() if p.exists() else None; frows.append({"path":str(f),"exists":p.exists(),"size_bytes":st.st_size if st else np.nan,"modified_time":datetime.fromtimestamp(st.st_mtime).isoformat() if st else None})
    manifest={"package":"gpbiometrics","package_version":"2.0.0","created":datetime.now(timezone.utc).isoformat(),"files":pd.DataFrame(frows),"settings":settings,"outputs":outputs,"exclusions":exclusions}
    if include_session: manifest["session_info"]={"python":platform.python_version(),"platform":platform.platform()}
    if path is not None:
        p=Path(path); lines=["gpbiometrics analysis manifest",f"created: {manifest['created']}",f"package_version: {manifest['package_version']}","","[files]"]
        if frows:
            for r in frows: lines.append("; ".join(f"{k}={v}" for k,v in r.items()))
        else: lines.append("none")
        lines += ["","[settings]"] + ([f"{k}: {v}" for k,v in settings.items()] if settings else ["none"]); lines += ["","[outputs]"]
        if outputs is None: lines.append("none")
        elif isinstance(outputs,dict): lines.extend(f"{k}: {v}" for k,v in outputs.items())
        else: lines.extend(map(str,outputs if isinstance(outputs,(list,tuple)) else [outputs]))
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text("\n".join(lines)+"\n",encoding="utf-8"); manifest["manifest_path"]=str(p.resolve())
    return manifest


def compute_gazepoint_ppg_template_similarity(data, time_col=None, ppg_col=None, peaks=None, window_s=(-0.25,0.45), sampling_rate_hz=None, n_grid=101, similarity_threshold=0.80):
    if isinstance(data,pd.DataFrame):
        df=_df(data); time_col=time_col or _guess(df,_EXACT_DICTIONARY["time_s"],"time",False); ppg_col=ppg_col or _guess(df,_EXACT_DICTIONARY["PPG"],"PPG",True); ppg=_numeric(df[ppg_col]);
        if time_col is not None and time_col in df.columns: t=time_seconds(df[time_col])
        else: sampling_rate_hz=50 if sampling_rate_hz is None else sampling_rate_hz; t=np.arange(1,len(ppg)+1)/sampling_rate_hz
    else:
        ppg=_numeric(data); sampling_rate_hz=50 if sampling_rate_hz is None else sampling_rate_hz; t=np.arange(1,len(ppg)+1)/sampling_rate_hz
    d=np.diff(t); dt=float(np.nanmedian(d)) if len(d) else np.nan; dt=(1/(sampling_rate_hz or 50)) if not np.isfinite(dt) or dt<=0 else dt
    if peaks is None: pidx=_local_peaks(ppg,max(1,int(round(.30/dt))))
    else:
        p=np.asarray(peaks,dtype=float)
        if np.all(np.isfinite(p)&(p>=1)&(p<=len(ppg))&(np.abs(p-np.round(p))<1e-8)): pidx=np.round(p).astype(int)-1
        else: pidx=np.array([int(np.argmin(np.abs(t-z))) for z in p],dtype=int)
    grid=np.linspace(window_s[0],window_s[1],int(n_grid)); wins=[]; kept=[]
    for p in pidx:
        rel=t-t[p]; idx=np.flatnonzero((rel>=window_s[0])&(rel<=window_s[1])&np.isfinite(ppg))
        if len(idx)<5: continue
        order=np.argsort(rel[idx]); xx,yy=rel[idx][order],ppg[idx][order]; yy=yy-np.mean(yy); sd=_r_sd(yy); yy=yy/sd if np.isfinite(sd) and sd>0 else yy; win=np.interp(grid,xx,yy,left=yy[0],right=yy[-1])
        if np.all(np.isfinite(win)): wins.append(win); kept.append(p)
    if not wins:
        return {"beats":pd.DataFrame(),"template":pd.DataFrame({"relative_time_s":grid,"template":np.nan}),"summary":pd.DataFrame([{"n_beats":0,"mean_similarity":np.nan,"quality_ok_ratio":np.nan}]),"settings":{"window_s":tuple(window_s),"n_grid":n_grid,"similarity_threshold":similarity_threshold}}
    W=np.vstack(wins); template=np.median(W,axis=0); sim=np.array([np.corrcoef(w,template)[0,1] for w in W]); kept=np.asarray(kept,dtype=int); beats=pd.DataFrame({"beat_id":np.arange(1,len(kept)+1),"peak_index":kept+1,"peak_time":t[kept],"template_similarity":sim,"quality_ok":np.isfinite(sim)&(sim>=similarity_threshold)}); summary=pd.DataFrame([{"n_beats":len(beats),"mean_similarity":float(np.nanmean(sim)),"median_similarity":float(np.nanmedian(sim)),"min_similarity":float(np.nanmin(sim)),"quality_ok_ratio":float(np.mean(beats.quality_ok))}]); return {"beats":beats,"template":pd.DataFrame({"relative_time_s":grid,"template":template}),"summary":summary,"settings":{"window_s":tuple(window_s),"n_grid":n_grid,"similarity_threshold":similarity_threshold}}


def compute_gazepoint_hrv_wavelet_psd(rr_intervals, time=None, bands=None, max_scale=None):
    orig=np.asarray(rr_intervals,dtype=float); rr=orig[np.isfinite(orig)]
    if len(rr)<8: raise ValueError("At least 8 finite RR/NN intervals are required.")
    unit="ms" if np.nanmedian(rr)>10 else "s"; rrs=rr/1000 if unit=="ms" else rr; x=rrs-np.mean(rrs); n=len(x); max_scale=2**int(np.floor(np.log2(max(2,n//4)))) if max_scale is None else max_scale; scales=2**np.arange(0,int(np.floor(np.log2(max_scale)))+1); scales=scales[(scales>=1)&(scales*2<=n)]; med=float(np.median(rrs)); rows=[]
    for s in scales.astype(int):
        coeff=np.array([np.mean(x[k:k+s])-np.mean(x[k+s:k+2*s]) for k in range(n-2*s+1)]); freq=1/(2*s*med) if np.isfinite(med) and med>0 else np.nan; rows.append({"scale_beats":s,"pseudo_frequency_hz":freq,"period_beats":2*s,"n_coefficients":len(coeff),"wavelet_power":float(np.mean(coeff**2)/2)})
    psd=pd.DataFrame(rows); bands={"vlf":(.0033,.04),"lf":(.04,.15),"hf":(.15,.40)} if bands is None else bands; brows=[]
    for name,band in bands.items():
        mask=(psd.pseudo_frequency_hz>=band[0])&(psd.pseudo_frequency_hz<band[1]); brows.append({"band":name,"low_hz":band[0],"high_hz":band[1],"n_scales":int(mask.sum()),"band_power":float(psd.loc[mask,"wavelet_power"].sum())})
    return {"psd":psd,"band_power":pd.DataFrame(brows),"settings":{"interval_unit":unit,"method":"haar_style_multiscale_power","max_scale":int(np.max(scales))}}


__all__ = [
    "compute_gazepoint_scr_habituation", "summarize_gazepoint_scr_recovery",
    "summarize_gazepoint_pupil_events", "summarize_gazepoint_tracking",
    "audit_gazepoint_pupil_luminance", "extract_gazepoint_ppg_morphology",
    "flag_gazepoint_ppg_quality", "import_gazepoint_event_log",
    "match_gazepoint_events_to_biometrics", "assert_gazepoint_columns",
    "gpbiometrics_info", "audit_gazepoint_export_schema",
    "simulate_gazepoint_multimodal_data", "assess_gazepoint_sampling_irregularity",
    "diagnose_gazepoint_sync_drift", "summarize_gazepoint_aoi_dwell",
    "summarize_gazepoint_scanpath_metrics", "create_gazepoint_analysis_manifest",
    "compute_gazepoint_ppg_template_similarity", "compute_gazepoint_hrv_wavelet_psd",
]
