from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd
from scipy import signal


def _require_df(dat: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(dat, pd.DataFrame):
        raise TypeError("`dat` must be a data frame.")
    return dat


def _numeric_col(dat: pd.DataFrame, col: str) -> np.ndarray:
    if col not in dat.columns:
        raise ValueError(f"Column `{col}` was not found in `dat`.")
    if not pd.api.types.is_numeric_dtype(dat[col]):
        raise TypeError(f"`{col}` must identify a numeric column.")
    return pd.to_numeric(dat[col], errors="coerce").to_numpy(dtype=float)


def _groups(dat: pd.DataFrame, group_cols: Iterable[str] | None):
    cols = [] if group_cols is None else list(group_cols)
    missing = [c for c in cols if c not in dat.columns]
    if missing:
        raise ValueError("Missing `group_cols`: " + ", ".join(missing))
    if not cols:
        return cols, [("all_rows", np.arange(len(dat), dtype=int), {"unit_label": "all_rows"})]
    work = dat[cols].astype(object).where(dat[cols].notna(), "<NA>").astype(str)
    keys = work.agg(" | ".join, axis=1)
    out = []
    for key in sorted(keys.unique()):
        idx = np.flatnonzero(keys.to_numpy() == key)
        base = {c: str(dat.iloc[idx[0]][c]) for c in cols}
        out.append((str(key), idx, base))
    return cols, out


def _sample_entropy(x: np.ndarray, m: int = 2, r: float = np.nan) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) <= m + 2 or not np.isfinite(r) or r <= 0:
        return np.nan

    def matches(mm: int) -> float:
        n = len(x) - mm + 1
        emb = np.lib.stride_tricks.sliding_window_view(x, mm)
        count = 0
        total = 0
        for i in range(n - 1):
            d = np.max(np.abs(emb[i + 1 :] - emb[i]), axis=1)
            count += int(np.sum(d <= r))
            total += len(d)
        return count / total if total else np.nan

    a, b = matches(m + 1), matches(m)
    if not np.isfinite(a) or not np.isfinite(b) or a <= 0 or b <= 0:
        return np.nan
    return float(-np.log(a / b))


def _approx_entropy(x: np.ndarray, m: int = 2, r: float = np.nan) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) <= m + 2 or not np.isfinite(r) or r <= 0:
        return np.nan

    def phi(mm: int) -> float:
        emb = np.lib.stride_tricks.sliding_window_view(x, mm)
        ci = []
        for row in emb:
            d = np.max(np.abs(emb - row), axis=1)
            ci.append(np.mean(d <= r))
        return float(np.mean(np.log(np.maximum(ci, np.finfo(float).eps))))

    p0, p1 = phi(m), phi(m + 1)
    return float(p0 - p1) if np.isfinite(p0) and np.isfinite(p1) else np.nan


def _dfa_alpha(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 32:
        return np.nan
    y = np.cumsum(x - np.mean(x))
    upper = max(8, math.floor(n / 4))
    raw = np.floor(np.exp(np.linspace(np.log(4), np.log(upper), 8))).astype(int)
    scales = np.unique(raw)
    scales = scales[(scales >= 4) & (scales < n / 2)]
    fluct = []
    used = []
    for s in scales:
        rms = []
        for st in range(0, n - s + 1, s):
            seg = y[st : st + s]
            coef = np.polyfit(np.arange(1, s + 1, dtype=float), seg, 1)
            resid = seg - np.polyval(coef, np.arange(1, s + 1, dtype=float))
            rms.append(np.sqrt(np.mean(resid**2)))
        f = np.mean(rms) if rms else np.nan
        if np.isfinite(f) and f > 0:
            used.append(s)
            fluct.append(f)
    if len(fluct) < 3:
        return np.nan
    return float(np.polyfit(np.log(used), np.log(fluct), 1)[0])


def _coarse(x: np.ndarray, scale: int) -> np.ndarray:
    if scale <= 1:
        return x.copy()
    n = len(x) // scale
    if n < 1:
        return np.array([], dtype=float)
    return np.mean(x[: n * scale].reshape(n, scale), axis=1)


def extract_gazepoint_hrv_nonlinear(
    dat: pd.DataFrame,
    ibi_col: str = "IBI",
    group_cols: Iterable[str] | None = None,
    min_intervals: int = 10,
    sampen_m: int = 2,
    sampen_r_multiplier: float = 0.2,
    mse_scales: Iterable[int] = range(1, 6),
):
    dat = _require_df(dat)
    _numeric_col(dat, ibi_col)
    scales_arr = np.asarray(list(mse_scales), dtype=float)
    if len(scales_arr) < 1 or not np.all(np.isfinite(scales_arr)) or np.any(scales_arr < 1):
        raise ValueError("`mse_scales` must be positive integer-like values.")
    scales = sorted(set(scales_arr.astype(int).tolist()))
    cols, groups = _groups(dat, group_cols)
    rows = []
    for unit_id, idx, base in groups:
        x = pd.to_numeric(dat.iloc[idx][ibi_col], errors="coerce").to_numpy(float)
        x = x[np.isfinite(x) & (x > 0)]
        row = dict(base)
        if cols:
            row.pop("unit_label", None)
        row.update(unit_id=unit_id, n_intervals=len(x))
        if len(x) < min_intervals:
            row.update(mean_ibi=np.nan, sdnn=np.nan, rmssd=np.nan, sd1=np.nan, sd2=np.nan,
                       sd1_sd2_ratio=np.nan, sample_entropy=np.nan, approximate_entropy=np.nan,
                       dfa_alpha=np.nan, mse_mean=np.nan, status="insufficient_intervals")
            row.update({f"mse_scale_{s}": np.nan for s in scales})
            rows.append(row)
            continue
        dx = np.diff(x)
        sdnn = float(np.std(x, ddof=1))
        diff_var = float(np.var(dx, ddof=1)) if len(dx) > 1 else np.nan
        rmssd = float(np.sqrt(np.mean(dx**2)))
        sd1 = float(np.sqrt(diff_var / 2)) if np.isfinite(diff_var) else np.nan
        sd2 = float(np.sqrt(max(2 * sdnn**2 - 0.5 * diff_var, 0))) if np.isfinite(diff_var) else np.nan
        tol = sampen_r_multiplier * sdnn
        mse = []
        for s in scales:
            cx = _coarse(x, s)
            csd = float(np.std(cx, ddof=1)) if len(cx) > 1 else np.nan
            mse.append(_sample_entropy(cx, sampen_m, sampen_r_multiplier * csd) if len(cx) > sampen_m + 2 and csd > 0 else np.nan)
        row.update(
            mean_ibi=float(np.mean(x)), sdnn=sdnn, rmssd=rmssd, sd1=sd1, sd2=sd2,
            sd1_sd2_ratio=sd1 / sd2 if np.isfinite(sd2) and sd2 > 0 else np.nan,
            sample_entropy=_sample_entropy(x, sampen_m, tol),
            approximate_entropy=_approx_entropy(x, sampen_m, tol),
            dfa_alpha=_dfa_alpha(x),
            mse_mean=float(np.nanmean(mse)) if np.any(np.isfinite(mse)) else np.nan,
            status="nonlinear_hrv_extracted",
        )
        row.update({f"mse_scale_{s}": v for s, v in zip(scales, mse)})
        rows.append(row)
    features = pd.DataFrame(rows)
    ok = features["status"].eq("nonlinear_hrv_extracted")
    status = "nonlinear_hrv_extracted" if ok.all() else ("nonlinear_hrv_partial" if ok.any() else "nonlinear_hrv_failed")
    overview = pd.DataFrame([{"group_count": len(groups), "feature_rows": len(features), "successful_groups": int(ok.sum()),
                              "problem_groups": int((~ok).sum()), "ibi_col": ibi_col, "status": status,
                              "interpretation": "Nonlinear HRV features describe interval variability, irregularity, and scale-dependent structure. They do not infer emotion, cognitive load, psychiatric status, health status, or diagnosis by themselves."}])
    return {"overview": overview, "features": features, "settings": {"ibi_col": ibi_col, "group_cols": cols, "min_intervals": min_intervals, "sampen_m": sampen_m, "sampen_r_multiplier": sampen_r_multiplier, "mse_scales": scales}}


def extract_gazepoint_eda_complexity(dat: pd.DataFrame, eda_col: str = "GSR_US", group_cols: Iterable[str] | None = None,
                                      min_samples: int = 32, sampen_m: int = 2, sampen_r_multiplier: float = 0.2):
    dat = _require_df(dat); _numeric_col(dat, eda_col)
    cols, groups = _groups(dat, group_cols); rows = []
    for unit_id, idx, base in groups:
        x = pd.to_numeric(dat.iloc[idx][eda_col], errors="coerce").to_numpy(float); x = x[np.isfinite(x)]
        sd = float(np.std(x, ddof=1)) if len(x) > 1 else np.nan
        row = dict(base); row.update(unit_id=unit_id, n_samples=len(x), signal_sd=sd)
        if len(x) < min_samples or (np.isfinite(sd) and sd == 0):
            row.update(sample_entropy=np.nan, dfa_alpha=np.nan, status="insufficient_or_constant_signal")
        else:
            row.update(sample_entropy=_sample_entropy(x, sampen_m, sampen_r_multiplier * sd), dfa_alpha=_dfa_alpha(x), status="eda_complexity_extracted")
        rows.append(row)
    features = pd.DataFrame(rows); ok = features.status.eq("eda_complexity_extracted")
    status = "eda_complexity_extracted" if ok.all() else ("eda_complexity_partial" if ok.any() else "eda_complexity_failed")
    overview = pd.DataFrame([{"group_count": len(groups), "feature_rows": len(features), "successful_groups": int(ok.sum()), "problem_groups": int((~ok).sum()), "eda_col": eda_col, "status": status,
                              "interpretation": "EDA complexity features describe nonlinear or scale-dependent signal structure. They are not direct emotion, stress, cognition, trust, preference, or diagnosis labels."}])
    return {"overview": overview, "features": features, "settings": {"eda_col": eda_col, "group_cols": cols, "min_samples": min_samples, "sampen_m": sampen_m, "sampen_r_multiplier": sampen_r_multiplier}}


def _runs(values: np.ndarray):
    if len(values) == 0:
        return [], []
    vals = [values[0]]; lens = [1]
    for v in values[1:]:
        if v == vals[-1]: lens[-1] += 1
        else: vals.append(v); lens.append(1)
    return vals, lens


def extract_gazepoint_hrv_fragmentation(dat: pd.DataFrame, ibi_col: str = "IBI", group_cols: Iterable[str] | None = None,
                                          zero_tolerance: float = 0, short_segment_length: int = 3):
    dat = _require_df(dat); _numeric_col(dat, ibi_col); cols, groups = _groups(dat, group_cols); rows=[]
    for gid, idx, base in groups:
        x = pd.to_numeric(dat.iloc[idx][ibi_col], errors="coerce").to_numpy(float); x=x[np.isfinite(x)&(x>0)]
        row=dict(base); row.update(group_id=gid,n_intervals=len(x),n_differences=max(len(x)-1,0))
        fields=["percentage_inflection_points","pip","inverse_average_segment_length","ials","percentage_short_segments","pss","percentage_alternation_segments","pas","mean_segment_length","median_segment_length","longest_segment"]
        if len(x)<5:
            row.update({k:np.nan for k in fields}); row["status"]="insufficient_intervals"; rows.append(row); continue
        dx=np.diff(x); sx=np.sign(dx); sx[np.abs(dx)<=zero_tolerance]=0; sx=sx[sx!=0]
        if len(sx)<2:
            row.update({k:np.nan for k in fields}); row["status"]="insufficient_nonzero_differences"; rows.append(row); continue
        inf=int(np.sum(sx[1:]*sx[:-1]<0)); pip=100*inf/(len(sx)-1); _, lens=_runs(sx); lens=np.asarray(lens,float)
        mean=float(np.mean(lens)); med=float(np.median(lens)); longest=float(np.max(lens)); ials=1/mean if mean>0 else np.nan
        pss=100*float(np.sum(lens<=short_segment_length))/float(np.sum(lens)); pas=100*float(np.sum(lens==1))/float(np.sum(lens))
        row.update(percentage_inflection_points=pip,pip=pip,inverse_average_segment_length=ials,ials=ials,percentage_short_segments=pss,pss=pss,percentage_alternation_segments=pas,pas=pas,mean_segment_length=mean,median_segment_length=med,longest_segment=longest,status="hrv_fragmentation_extracted"); rows.append(row)
    f=pd.DataFrame(rows); ok=f.status.eq("hrv_fragmentation_extracted"); st="hrv_fragmentation_extracted" if ok.all() else ("hrv_fragmentation_partial" if ok.any() else "hrv_fragmentation_failed")
    return {"overview":pd.DataFrame([{"group_count":len(groups),"feature_rows":len(f),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":st,"interpretation":"Heart-rate fragmentation features describe rapid sign changes and segment structure in IBI/RR dynamics. They are not diagnostic labels and do not directly infer vagal tone, cardiovascular disease, emotion, or cognition."}]),"features":f,"settings":{"ibi_col":ibi_col,"group_cols":cols,"zero_tolerance":zero_tolerance,"short_segment_length":short_segment_length}}


def extract_gazepoint_hrv_asymmetry(dat: pd.DataFrame, ibi_col: str="IBI", group_cols: Iterable[str]|None=None, zero_tolerance: float=0):
    dat=_require_df(dat); _numeric_col(dat,ibi_col); cols,groups=_groups(dat,group_cols); feats=[]; runrows=[]
    for gid,idx,base in groups:
        x=pd.to_numeric(dat.iloc[idx][ibi_col],errors="coerce").to_numpy(float); x=x[np.isfinite(x)&(x>0)]; row=dict(base); row.update(group_id=gid,n_intervals=len(x),n_differences=max(len(x)-1,0))
        blank=["acceleration_count","deceleration_count","acceleration_proportion","deceleration_proportion","acceleration_run_count","deceleration_run_count","mean_acceleration_run_length","mean_deceleration_run_length","longest_acceleration_run","longest_deceleration_run","guzik_index","porta_index","asymmetry_balance"]
        if len(x)<5: row.update({k:np.nan for k in blank}); row["status"]="insufficient_intervals"; feats.append(row); continue
        dx=np.diff(x); dx[np.abs(dx)<=zero_tolerance]=0; direction=np.where(dx>0,"deceleration",np.where(dx<0,"acceleration","no_change")); mask=direction!="no_change"
        if np.sum(mask)<2:
            row.update({k:np.nan for k in blank}); row.update(acceleration_count=int(np.sum(direction=="acceleration")),deceleration_count=int(np.sum(direction=="deceleration")),status="insufficient_nonzero_differences"); feats.append(row); continue
        dn=direction[mask]; dxn=dx[mask]; rv,rl=_runs(dn); acc=[l for v,l in zip(rv,rl) if v=="acceleration"]; dec=[l for v,l in zip(rv,rl) if v=="deceleration"]
        for j,(v,l) in enumerate(zip(rv,rl),1): runrows.append({"group_id":gid,"run_index":j,"run_type":v,"run_length":l})
        ac=int(np.sum(dn=="acceleration")); dc=int(np.sum(dn=="deceleration")); total=len(dn); pe=float(np.sum(dxn[dxn>0]**2)); ne=float(np.sum(dxn[dxn<0]**2)); energy=pe+ne
        row.update(acceleration_count=ac,deceleration_count=dc,acceleration_proportion=ac/total,deceleration_proportion=dc/total,acceleration_run_count=len(acc),deceleration_run_count=len(dec),mean_acceleration_run_length=float(np.mean(acc)) if acc else np.nan,mean_deceleration_run_length=float(np.mean(dec)) if dec else np.nan,longest_acceleration_run=max(acc) if acc else np.nan,longest_deceleration_run=max(dec) if dec else np.nan,guzik_index=100*pe/energy if energy>0 else np.nan,porta_index=100*dc/total,asymmetry_balance=(dc-ac)/total,status="hrv_asymmetry_extracted"); feats.append(row)
    f=pd.DataFrame(feats); rt=pd.DataFrame(runrows); ok=f.status.eq("hrv_asymmetry_extracted"); st="hrv_asymmetry_extracted" if ok.all() else ("hrv_asymmetry_partial" if ok.any() else "hrv_asymmetry_failed")
    return {"overview":pd.DataFrame([{"group_count":len(groups),"feature_rows":len(f),"run_rows":len(rt),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":st,"interpretation":"Heart-rate asymmetry features summarise unequal acceleration and deceleration dynamics. They do not directly infer health status, emotion, cognition, or diagnosis."}]),"features":f,"run_table":rt,"settings":{"ibi_col":ibi_col,"group_cols":cols,"zero_tolerance":zero_tolerance}}


def _line_lengths(a: np.ndarray) -> list[int]:
    vals=[]; n=0
    for v in a.astype(bool):
        if v: n+=1
        elif n: vals.append(n); n=0
    if n: vals.append(n)
    return vals


def extract_gazepoint_hrv_rqa(dat: pd.DataFrame, ibi_col: str="IBI", group_cols: Iterable[str]|None=None,
                               embedding_dimension: int=2, delay: int=1, radius: float|None=None, radius_multiplier: float=0.2, min_line_length: int=2):
    dat=_require_df(dat); _numeric_col(dat,ibi_col); cols,groups=_groups(dat,group_cols); rows=[]
    for gid,idx,base in groups:
        x=pd.to_numeric(dat.iloc[idx][ibi_col],errors="coerce").to_numpy(float); x=x[np.isfinite(x)&(x>0)]; row=dict(base); row.update(group_id=gid,n_intervals=len(x))
        names=["recurrence_rate","determinism","laminarity","trapping_time","diagonal_entropy","mean_diagonal_length","longest_diagonal"]
        if len(x)<(embedding_dimension+2)*delay+5:
            row.update({k:np.nan for k in names}); row["status"]="insufficient_intervals"; rows.append(row); continue
        n=len(x)-(embedding_dimension-1)*delay; emb=np.column_stack([x[j*delay:j*delay+n] for j in range(embedding_dimension)]); rad=radius if radius is not None else radius_multiplier*float(np.std(emb.ravel(),ddof=1)); rad=np.finfo(float).eps if not np.isfinite(rad) or rad<=0 else float(rad)
        d=np.linalg.norm(emb[:,None,:]-emb[None,:,:],axis=2); rec=d<=rad; diag=[]
        for off in range(-(n-1),n): diag.extend(_line_lengths(np.diag(rec,k=off)))
        vert=[]
        for j in range(n): vert.extend(_line_lengths(rec[:,j]))
        rp=int(np.sum(rec)); total=rec.size; de=sum(l for l in diag if l>=min_line_length); ve=sum(l for l in vert if l>=min_line_length); ed=[l for l in diag if l>=min_line_length]; ev=[l for l in vert if l>=min_line_length]
        if ed:
            _,counts=np.unique(ed,return_counts=True); p=counts/counts.sum(); ent=float(-np.sum(p*np.log(p)))
        else: ent=np.nan
        row.update(recurrence_rate=rp/total,determinism=de/rp if rp else np.nan,laminarity=ve/rp if rp else np.nan,trapping_time=float(np.mean(ev)) if ev else np.nan,diagonal_entropy=ent,mean_diagonal_length=float(np.mean(ed)) if ed else np.nan,longest_diagonal=max(diag) if diag else np.nan,status="hrv_rqa_extracted"); rows.append(row)
    f=pd.DataFrame(rows); ok=f.status.eq("hrv_rqa_extracted"); st="hrv_rqa_extracted" if ok.all() else ("hrv_rqa_partial" if ok.any() else "hrv_rqa_failed")
    return {"overview":pd.DataFrame([{"group_count":len(groups),"feature_rows":len(f),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":st,"interpretation":"RQA features describe recurrence structure in IBI/RR dynamics. They are nonlinear descriptors and do not infer health status or diagnosis by themselves."}]),"features":f,"settings":{"ibi_col":ibi_col,"group_cols":cols,"embedding_dimension":embedding_dimension,"delay":delay,"radius":radius,"radius_multiplier":radius_multiplier,"min_line_length":min_line_length}}


def extract_gazepoint_hrv_geometric(dat: pd.DataFrame, ibi_col: str="IBI", group_cols: Iterable[str]|None=None, bin_width: float|None=None):
    dat=_require_df(dat); _numeric_col(dat,ibi_col); cols,groups=_groups(dat,group_cols); rows=[]
    for gid,idx,base in groups:
        x=pd.to_numeric(dat.iloc[idx][ibi_col],errors="coerce").to_numpy(float); x=x[np.isfinite(x)&(x>0)]; row=dict(base); row.update(group_id=gid,n_intervals=len(x))
        if len(x)<5: row.update(bin_width=np.nan,hrv_triangular_index=np.nan,tinn=np.nan,histogram_peak_count=np.nan,status="insufficient_intervals"); rows.append(row); continue
        bw=float(bin_width) if bin_width is not None else (7.8125 if np.median(x)>10 else 0.0078125)
        lo=math.floor(np.min(x)/bw)*bw; hi=math.ceil(np.max(x)/bw)*bw+bw; edges=np.arange(lo,hi+bw*0.5,bw); counts,_=np.histogram(x,bins=edges); mx=int(counts.max()); hti=len(x)/mx if mx>0 else np.nan; nz=np.flatnonzero(counts>0); tinn=edges[nz.max()+1]-edges[nz.min()] if len(nz)>=2 else np.nan
        row.update(bin_width=bw,hrv_triangular_index=hti,tinn=float(tinn),histogram_peak_count=mx,status="hrv_geometric_extracted"); rows.append(row)
    f=pd.DataFrame(rows); ok=f.status.eq("hrv_geometric_extracted"); st="hrv_geometric_extracted" if ok.all() else ("hrv_geometric_partial" if ok.any() else "hrv_geometric_failed")
    return {"overview":pd.DataFrame([{"group_count":len(groups),"feature_rows":len(f),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":st,"interpretation":"Geometric HRV features summarise the distributional shape of IBI/RR intervals. They are not diagnostic labels by themselves."}]),"features":f,"settings":{"ibi_col":ibi_col,"group_cols":cols,"bin_width":bin_width}}


def _sampling_rate(time: np.ndarray, given: float|None):
    if given is not None: return float(given)
    t=time[np.isfinite(time)]
    if len(t)<3: return np.nan
    dt=np.diff(t); dt=dt[np.isfinite(dt)&(dt>0)]
    if not len(dt): return np.nan
    md=float(np.median(dt)); return 1000/md if md>10 else 1/md


def _smooth(x: np.ndarray, window: int):
    x=np.asarray(x,float)
    if not isinstance(window,(int,np.integer,float)) or window<=1 or len(x)<int(window): return x.copy()
    w=int(window); y=np.convolve(np.nan_to_num(x,nan=0.0),np.ones(w)/w,mode="same"); edge=w//2; y[:edge]=x[:edge]; y[len(x)-edge:]=x[len(x)-edge:]; y[~np.isfinite(x)]=x[~np.isfinite(x)]; return y


def _find_peaks(x: np.ndarray,time: np.ndarray,min_dist: float):
    x=np.asarray(x,float); time=np.asarray(time,float); cand=[]
    for i in range(1,len(x)-1):
        if np.isfinite(x[i]) and np.isfinite(time[i]) and x[i]>x[i-1] and x[i]>=x[i+1]: cand.append(i)
    if not cand:return []
    sel=[cand[0]]
    for i in cand[1:]:
        if time[i]-time[sel[-1]]>=min_dist: sel.append(i)
        elif x[i]>x[sel[-1]]: sel[-1]=i
    return sel


def _feature_rate(time: np.ndarray,feature: np.ndarray,band,resample_rate: float):
    keep=np.isfinite(time)&np.isfinite(feature); t=time[keep]; y=feature[keep]
    if len(t)<8 or len(np.unique(t))<8 or np.std(y,ddof=1)==0:return np.nan
    order=np.argsort(t); t=t[order]; y=y[order]; grid=np.arange(t.min(),t.max()+1e-12,1/resample_rate)
    if len(grid)<16:return np.nan
    yi=np.interp(grid,t,y); yi-=np.mean(yi)
    if np.std(yi,ddof=1)==0:return np.nan
    freq,p=signal.periodogram(yi,fs=resample_rate,detrend="linear"); mask=(freq>=band[0])&(freq<=band[1])&np.isfinite(p)
    return float(freq[mask][np.argmax(p[mask])]) if np.any(mask) else np.nan


def extract_gazepoint_pdr_signals(dat: pd.DataFrame, ppg_col: str="HRP", time_col: str="CNT", group_cols: Iterable[str]|None=None,
                                   sampling_rate: float|None=None, min_peak_distance_s: float=0.30, smooth_window: int=5,
                                   respiration_band=(0.10,0.60), pdr_resample_rate: float=4):
    dat=_require_df(dat); _numeric_col(dat,ppg_col); _numeric_col(dat,time_col); band=np.asarray(respiration_band,float)
    if band.shape!=(2,) or not np.all(np.isfinite(band)) or band[0]<=0 or band[0]>=band[1]: raise ValueError("`respiration_band` must be a positive numeric vector of length two.")
    cols,groups=_groups(dat,group_cols); pulse=[]; summaries=[]; positions=np.arange(len(dat))+1
    for gid,idx,base in groups:
        order=np.argsort(pd.to_numeric(dat.iloc[idx][time_col],errors="coerce").to_numpy(float)); idx=idx[order]; t=pd.to_numeric(dat.iloc[idx][time_col],errors="coerce").to_numpy(float); ppg=pd.to_numeric(dat.iloc[idx][ppg_col],errors="coerce").to_numpy(float); fs=_sampling_rate(t,sampling_rate); sm=_smooth(ppg,smooth_window); peaks=_find_peaks(sm,t,min_peak_distance_s)
        if len(peaks)<3:
            summaries.append({"group_id":gid,"n_samples":len(idx),"n_pulses":len(peaks),"sampling_rate_hz":fs,"riiv_resp_rate_hz":np.nan,"pav_resp_rate_hz":np.nan,"pwv_resp_rate_hz":np.nan,"prv_resp_rate_hz":np.nan,"proxy_resp_rate_hz":np.nan,"proxy_resp_rate_bpm":np.nan,"status":"insufficient_pulse_peaks"}); continue
        grp=[]
        for j in range(1,len(peaks)):
            prev,cur=peaks[j-1],peaks[j]; seg=np.arange(prev,cur+1); trough=int(seg[np.nanargmin(sm[seg])]); interval=t[cur]-t[prev]; rate=60/interval if np.isfinite(interval) and interval>0 else np.nan; width=interval if j>=2 else np.nan; amp=sm[cur]-sm[trough]
            r={"group_id":gid,"pulse_index":j,"peak_row":int(positions[idx[cur]]),"trough_row":int(positions[idx[trough]]),"peak_time":t[cur],"trough_time":t[trough],"peak_value":sm[cur],"trough_value":sm[trough],"riiv":sm[trough],"pav":amp,"pwv":width,"prv":rate,"pulse_interval_s":interval,"pulse_rate_bpm":rate}; pulse.append(r); grp.append(r)
        g=pd.DataFrame(grp); rates=[_feature_rate(g.peak_time.to_numpy(float),g[c].to_numpy(float),band,pdr_resample_rate) for c in ["riiv","pav","pwv","prv"]]; vr=[r for r in rates if np.isfinite(r)]; proxy=float(np.median(vr)) if vr else np.nan
        summaries.append({"group_id":gid,"n_samples":len(idx),"n_pulses":len(peaks),"sampling_rate_hz":fs,"riiv_resp_rate_hz":rates[0],"pav_resp_rate_hz":rates[1],"pwv_resp_rate_hz":rates[2],"prv_resp_rate_hz":rates[3],"proxy_resp_rate_hz":proxy,"proxy_resp_rate_bpm":proxy*60,"status":"pdr_extracted" if np.isfinite(proxy) else "pdr_rate_not_estimated"})
    pf=pd.DataFrame(pulse); ps=pd.DataFrame(summaries)
    if len(pf):
        arr=[]
        for c in ["riiv","pav","pwv","prv"]:
            x=pf[c].to_numpy(float); good=np.isfinite(x); z=np.full(len(x),np.nan); sd=np.std(x[good],ddof=1) if good.sum()>1 else np.nan
            if good.sum()>=2 and sd>0: z[good]=(x[good]-np.mean(x[good]))/sd
            arr.append(z)
        z=np.column_stack(arr); proxy=np.array([np.nan if np.all(~np.isfinite(r)) else np.nanmean(r) for r in z]); pf["resp_proxy"]=proxy; pts=pf[["group_id","pulse_index","peak_time","riiv","pav","pwv","prv","resp_proxy"]].copy()
    else: pts=pd.DataFrame()
    ok=ps.status.eq("pdr_extracted") if len(ps) else pd.Series([],dtype=bool); st="pdr_extraction_complete" if len(ok) and ok.all() else ("pdr_extraction_partial" if len(ok) and ok.any() else "pdr_extraction_failed")
    ov=pd.DataFrame([{"group_count":len(groups),"pulse_feature_rows":len(pf),"pdr_summary_rows":len(ps),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()) if len(ok) else len(groups),"ppg_col":ppg_col,"time_col":time_col,"status":st,"interpretation":"PPG-derived respiration features are proxy estimates from pulse morphology and timing. They are not a substitute for direct respiratory-belt measurement."}])
    out={"overview":ov,"pulse_features":pf,"pdr_timeseries":pts,"pdr_summary":ps,"settings":{"ppg_col":ppg_col,"time_col":time_col,"group_cols":cols,"sampling_rate":sampling_rate,"min_peak_distance_s":min_peak_distance_s,"smooth_window":smooth_window,"respiration_band":list(band),"pdr_resample_rate":pdr_resample_rate}}
    out["_class"]="gazepoint_pdr_signals"; return out


def _rsa_pb(time,ibi,resp_rate,band,resample):
    keep=np.isfinite(time)&np.isfinite(ibi)&(ibi>0); t=time[keep]; x=ibi[keep]
    if len(t)<8 or len(np.unique(t))<8 or np.std(x,ddof=1)==0:return np.nan
    o=np.argsort(t);t=t[o];x=x[o];grid=np.arange(t.min(),t.max()+1e-12,1/resample)
    if len(grid)<16:return np.nan
    y=np.interp(grid,t,x);y-=np.mean(y); use=list(band)
    if np.isfinite(resp_rate) and resp_rate>0: use=[max(.05,resp_rate-.05),min(resample/2-.01,resp_rate+.05)]
    f,p=signal.periodogram(y,fs=resample,detrend="linear"); m=(f>=use[0])&(f<=use[1])&np.isfinite(p)
    power=float(np.sum(p[m])) if np.any(m) else np.nan
    return float(np.log(power)) if np.isfinite(power) and power>0 else np.nan


def calculate_gazepoint_rsa(dat: pd.DataFrame, ibi_col: str="IBI", time_col: str="CNT", group_cols: Iterable[str]|None=None,
                            pdr=None, resp_rate_hz: float|None=None, respiration_band=(0.12,0.40), resample_rate: float=4):
    dat=_require_df(dat); _numeric_col(dat,ibi_col); _numeric_col(dat,time_col); cols,groups=_groups(dat,group_cols)
    ps=pts=None
    if pdr is not None:
        if not isinstance(pdr,dict) or pdr.get("_class")!="gazepoint_pdr_signals": raise ValueError("`pdr` must be output from `extract_gazepoint_pdr_signals()`.")
        ps=pdr["pdr_summary"];pts=pdr["pdr_timeseries"]
    rows=[]
    for gid,idx,base in groups:
        o=np.argsort(pd.to_numeric(dat.iloc[idx][time_col],errors="coerce").to_numpy(float)); idx=idx[o]; t=pd.to_numeric(dat.iloc[idx][time_col],errors="coerce").to_numpy(float); x=pd.to_numeric(dat.iloc[idx][ibi_col],errors="coerce").to_numpy(float); keep=np.isfinite(t)&np.isfinite(x)&(x>0);t=t[keep];x=x[keep]
        rr=float(resp_rate_hz) if resp_rate_hz is not None and np.isfinite(resp_rate_hz) else np.nan
        if not np.isfinite(rr) and ps is not None and len(ps):
            q=ps[ps.group_id.astype(str)==str(gid)]; rr=float(q.proxy_resp_rate_hz.iloc[0]) if len(q) and np.isfinite(q.proxy_resp_rate_hz.iloc[0]) else np.nan
        p2t=np.nan
        if pts is not None and len(pts):
            q=pts[pts.group_id.astype(str)==str(gid)].sort_values("peak_time")
            if len(q)>=4 and "resp_proxy" in q:
                peaks=_find_peaks(q.resp_proxy.to_numpy(float),q.peak_time.to_numpy(float),1.0); vals=[]
                for a,b in zip(peaks[:-1],peaks[1:]):
                    m=(t>=q.peak_time.iloc[a])&(t<=q.peak_time.iloc[b])
                    if m.sum()>=2: vals.append(float(np.max(x[m])-np.min(x[m])))
                if vals:p2t=float(np.mean(vals))
        pb=_rsa_pb(t,x,rr,respiration_band,resample_rate); rows.append({"group_id":gid,"n_intervals":len(x),"resp_rate_hz":rr,"resp_rate_bpm":rr*60,"rsa_p2t_proxy":p2t,"rsa_pb_log_power_proxy":pb,"status":"rsa_proxy_calculated" if len(x)>=5 and (np.isfinite(p2t) or np.isfinite(pb)) else "rsa_proxy_insufficient_information"})
    rs=pd.DataFrame(rows);ok=rs.status.eq("rsa_proxy_calculated");st="rsa_proxy_complete" if ok.all() else ("rsa_proxy_partial" if ok.any() else "rsa_proxy_failed")
    return {"overview":pd.DataFrame([{"group_count":len(groups),"rsa_rows":len(rs),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":st,"interpretation":"RSA outputs are respiration-informed HRV proxy summaries. Without direct respiration measurement they should not be interpreted as definitive vagal-tone estimates."}]),"rsa_summary":rs,"settings":{"ibi_col":ibi_col,"time_col":time_col,"group_cols":cols,"pdr_supplied":pdr is not None,"resp_rate_hz":resp_rate_hz,"respiration_band":list(respiration_band),"resample_rate":resample_rate}}
