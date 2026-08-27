from __future__ import annotations

from pathlib import Path
import json
import pickle
import re

import numpy as np
import pandas as pd
from scipy.stats import gamma as gamma_dist, t as t_dist


def _num(x):
    return pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(float)


def _pick_col(data: pd.DataFrame, candidates, label: str) -> str:
    for c in candidates:
        if c in data.columns:
            return c
    raise ValueError(f"Could not infer {label} column. Please supply it explicitly.")


def _prepare_time_data(data, time_col=None, sampling_rate_hz=None):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    out = data.copy()
    if time_col is None:
        if sampling_rate_hz is not None and np.isfinite(sampling_rate_hz) and sampling_rate_hz > 0:
            time_col = "time_s"
            out[time_col] = np.arange(len(out), dtype=float) / float(sampling_rate_hz)
        else:
            time_col = _pick_col(out, ["time_s", "Time", "TIME", "RecordingTime", "MSTIMER", "timestamp", "Timestamp"], "time")
    if time_col not in out.columns:
        raise ValueError("`time_col` not found.")
    out[time_col] = pd.to_numeric(out[time_col], errors="coerce")
    return out, time_col


def _group_positions(data: pd.DataFrame, group_cols=None):
    if group_cols is None or (hasattr(group_cols, "__len__") and not isinstance(group_cols, str) and len(group_cols) == 0):
        return [("all", np.arange(len(data), dtype=int))]
    cols = [group_cols] if isinstance(group_cols, str) else list(group_cols)
    missing = [c for c in cols if c not in data.columns]
    if missing:
        raise ValueError("Missing group columns: " + ", ".join(missing))
    work = data.reset_index(drop=True)
    groups=[]
    grouper = cols[0] if len(cols) == 1 else cols
    for key, block in work.groupby(grouper, sort=False, dropna=False):
        if not isinstance(key, tuple): key=(key,)
        groups.append((" | ".join(map(str,key)), block.index.to_numpy(dtype=int)))
    return groups


def _interp_na(x):
    a=np.asarray(x,dtype=float).copy()
    ok=np.isfinite(a)
    if not len(a) or not ok.any(): return a
    idx=np.arange(len(a))
    a[~ok]=np.interp(idx[~ok], idx[ok], a[ok])
    return a


def _running_mean(x, n):
    a=np.asarray(x,dtype=float)
    n=max(1,int(n))
    if n <= 1 or len(a) == 0: return a.copy()
    # R stats::filter sides=2 gives NAs at incomplete edges; helper restores original clean signal there.
    s=pd.Series(a).rolling(n, center=True, min_periods=n).mean().to_numpy(dtype=float,copy=True)
    bad=~np.isfinite(s)
    s[bad]=a[bad]
    return s


def _expand_flags(flag, n):
    f=np.asarray(flag,dtype=bool)
    n=max(0,int(n))
    if n == 0 or not f.any(): return f.copy()
    out=f.copy(); where=np.flatnonzero(f)
    for i in where:
        out[max(0,i-n):min(len(f),i+n+1)] = True
    return out


def _short_islands(valid, min_samples):
    valid=np.asarray(valid,dtype=bool)
    out=np.zeros(len(valid),dtype=bool)
    if min_samples <= 1: return out
    start=0
    while start < len(valid):
        v=valid[start]; end=start+1
        while end < len(valid) and valid[end] == v: end += 1
        if v and end-start < min_samples: out[start:end]=True
        start=end
    return out


def _artifact_table(time, artifact, reason):
    t=np.asarray(time,dtype=float); f=np.asarray(artifact,dtype=bool); reason=np.asarray(reason,object)
    rows=[]; i=0; aid=1
    while i < len(f):
        if not f[i]: i+=1; continue
        j=i+1
        while j < len(f) and f[j]: j+=1
        rs=[]
        for r in reason[i:j]:
            if r != "accepted" and r not in rs: rs.append(str(r))
        rows.append({"artifact_id":aid,"start_index":i+1,"end_index":j,"start_time_s":t[i],"end_time_s":t[j-1],"duration_s":t[j-1]-t[i],"reason":";".join(rs)})
        aid+=1; i=j
    return pd.DataFrame(rows)


def _kernel(dt, response="scr", response_length_s=20):
    if response not in {"scr","canonical","boxcar"}: raise ValueError("Invalid `response`.")
    if not np.isfinite(dt) or dt <= 0: raise ValueError("Invalid sampling interval.")
    t=np.arange(0,float(response_length_s)+dt*0.5,dt)
    if response == "boxcar": k=np.ones_like(t)
    elif response == "scr": k=gamma_dist.pdf(t,a=3,scale=1.5)
    else: k=gamma_dist.pdf(t,a=6,scale=1)-0.35*gamma_dist.pdf(t,a=16,scale=1)
    m=np.nanmax(np.abs(k)) if len(k) else 0
    return k/m if m>0 else k


def _safe_name(x):
    s=str(x)
    s=re.sub(r"[^0-9A-Za-z_.]", ".", s)
    if not s or not re.match(r"[A-Za-z.]",s[0]): s="X"+s
    return s


def extract_gazepoint_markerinfo_pspm_style(data, marker_cols=None, time_col=None, sampling_rate_hz=None, group_cols=None, edge="rising", nonzero_only=True):
    if edge not in {"rising","change","nonzero"}: raise ValueError("Invalid `edge`.")
    d,time_col=_prepare_time_data(data,time_col,sampling_rate_hz)
    if marker_cols is None:
        marker_cols=[c for c in d.columns if re.search(r"marker|ttl|trigger|event|stim|condition",str(c),re.I) and c != time_col]
    marker_cols=[marker_cols] if isinstance(marker_cols,str) else list(marker_cols)
    if not marker_cols: raise ValueError("No marker columns found. Supply `marker_cols`.")
    missing=[c for c in marker_cols if c not in d.columns]
    if missing: raise ValueError("Missing marker columns: "+", ".join(missing))
    rows=[]
    for label,pos in _group_positions(d,group_cols):
        dd=d.iloc[pos]; time=_num(dd[time_col])
        for mc in marker_cols:
            raw=dd[mc]
            val=raw.astype(object).where(~raw.isna(),"0").astype(str).to_numpy()
            numeric=pd.to_numeric(pd.Series(val),errors="coerce").to_numpy(float)
            is_zero=np.where(np.isfinite(numeric), numeric==0, np.isin(val,["","0","FALSE","false","NA","NaN"]))
            previous=np.r_[True,is_zero[:-1]]
            if edge == "rising": ev=np.flatnonzero((~is_zero)&previous)
            elif edge == "change":
                changed=np.r_[True,val[1:] != val[:-1]]; ev=np.flatnonzero(changed)
                if nonzero_only: ev=ev[~is_zero[ev]]
            else: ev=np.flatnonzero(~is_zero)
            for i in ev:
                after=np.flatnonzero(is_zero[i:])
                end_i = i + int(after[0]) if len(after) else i
                rows.append({"group":label,"marker_id":len(rows)+1,"marker_channel":mc,"marker_code":val[i],"marker_label":f"{mc}_{val[i]}","sample_index":int(pos[i])+1,"time_s":time[i],"duration_s": float(time[end_i]-time[i]) if end_i>i else 0.0})
    return pd.DataFrame(rows)


def combine_gazepoint_marker_channels_pspm_style(data, marker_cols=None, time_col=None, sampling_rate_hz=None, group_cols=None, combined_col="pspm_marker"):
    d,tc=_prepare_time_data(data,time_col,sampling_rate_hz)
    markers=extract_gazepoint_markerinfo_pspm_style(d,marker_cols,tc,None,group_cols,"rising",True)
    d[combined_col]=pd.Series([None]*len(d),dtype=object); d[f"{combined_col}_code"]=pd.Series([pd.NA]*len(d),dtype="Int64")
    if not markers.empty:
        for sample,block in markers.groupby("sample_index",sort=False):
            ix=int(sample)-1
            d.at[d.index[ix],combined_col]="+".join(block["marker_label"].astype(str))
            d.at[d.index[ix],f"{combined_col}_code"]=int(block["marker_id"].min())
    return {"data":d,"markers":markers,"marker_cols":marker_cols,"combined_col":combined_col}


def trim_gazepoint_biometrics_pspm_style(data,start_s=None,end_s=None,time_col=None,reset_time=False):
    d,tc=_prepare_time_data(data,time_col,None)
    keep=np.ones(len(d),bool)
    if start_s is not None: keep &= d[tc].to_numpy(float)>=start_s
    if end_s is not None: keep &= d[tc].to_numpy(float)<=end_s
    out=d.loc[keep].copy().reset_index(drop=True)
    if reset_time and len(out): out[tc]=out[tc]-out[tc].min(skipna=True)
    return out


def split_gazepoint_sessions_pspm_style(data,time_col=None,gap_seconds=None,session_col="pspm_session",reset_time=True):
    d,tc=_prepare_time_data(data,time_col,None); t=_num(d[tc])
    if len(d)==0: return {"data":d,"sessions":pd.DataFrame(),"split":[]}
    dt=np.r_[np.nan,np.diff(t)]
    pos=dt[np.isfinite(dt)&(dt>0)]
    if gap_seconds is None: gap_seconds=float(5*np.median(pos)) if len(pos) else np.inf
    new=np.isnan(dt)|(~np.isfinite(dt))|(dt<0)|(dt>gap_seconds); new[0]=True
    sid=np.cumsum(new).astype(int); d[session_col]=sid
    rel=[]; sessions=[]; split=[]
    for s in np.unique(sid):
        ix=np.flatnonzero(sid==s); block=d.iloc[ix].copy()
        if reset_time:
            block["pspm_session_time_s"]=_num(block[tc])-np.nanmin(_num(block[tc])); rel.extend(block["pspm_session_time_s"].tolist())
        sessions.append({"session":int(s),"start_index":int(ix[0])+1,"end_index":int(ix[-1])+1,"start_time_s":t[ix[0]],"end_time_s":t[ix[-1]],"n_samples":len(ix)})
        split.append(block.reset_index(drop=True))
    if reset_time:
        # assign by session order robustly
        d["pspm_session_time_s"]=np.nan
        for s in np.unique(sid):
            ix=np.flatnonzero(sid==s); d.loc[d.index[ix],"pspm_session_time_s"]=t[ix]-np.nanmin(t[ix])
    return {"data":d,"sessions":pd.DataFrame(sessions),"split_data":split}


def merge_gazepoint_recordings_pspm_style(recordings,time_col=None,gap_seconds=1,recording_col="pspm_recording",reset_first_time=True):
    if not isinstance(recordings,(list,tuple)) or not recordings: raise ValueError("`recordings` must be a non-empty list of data frames.")
    out=[]; offset=0.0
    for i,rec in enumerate(recordings,1):
        d,tc=_prepare_time_data(rec,time_col,None); d["pspm_original_time_s"]=d[tc]
        if reset_first_time and len(d): d[tc]=d[tc]-d[tc].min(skipna=True)
        d[tc]=d[tc]+offset; d[recording_col]=i
        if len(d): offset=float(d[tc].max(skipna=True))+float(gap_seconds)
        out.append(d)
    return pd.concat(out,ignore_index=True,sort=False)


def preprocess_gazepoint_scr_pspm_style(data,signal_col=None,time_col=None,sampling_rate_hz=None,range=(0,50),slope_limit_per_s=10,clipping_tolerance=1e-5,clipping_seconds=0.5,min_valid_island_seconds=1,artifact_epoch_seconds=0.25,smoothing_seconds=0.25):
    if isinstance(data,(list,tuple,np.ndarray,pd.Series)) and not isinstance(data,pd.DataFrame):
        a=np.asarray(data,dtype=float)
        if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0: raise ValueError("`sampling_rate_hz` is required for numeric input.")
        d=pd.DataFrame({"time_s":np.arange(len(a))/float(sampling_rate_hz),"scr":a}); signal_col="scr"; time_col="time_s"
    else:
        d,time_col=_prepare_time_data(data,time_col,sampling_rate_hz)
        if signal_col is None: signal_col=_pick_col(d,["SCR","GSR","EDA","scr","gsr","eda","signal"],"SCR/GSR")
    if signal_col not in d.columns: raise ValueError("`signal_col` not found.")
    sig=_num(d[signal_col]); time=_num(d[time_col])
    if sampling_rate_hz is None:
        dt0=np.diff(time); dt0=dt0[np.isfinite(dt0)&(dt0>0)]; sampling_rate_hz=1/np.median(dt0) if len(dt0) else np.nan
    if not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0: raise ValueError("Could not infer a valid sampling rate.")
    reason=np.array(["accepted"]*len(sig),dtype=object)
    lo,hi=float(range[0]),float(range[1]); range_flag=(~np.isfinite(sig))|(sig<lo)|(sig>hi); reason[range_flag]="range_or_nonfinite"
    dt=np.r_[np.nan,np.diff(time)]; slope=np.r_[np.nan,np.abs(np.diff(sig))/dt[1:]]; slope_flag=np.isfinite(slope)&(slope>slope_limit_per_s)
    for i in np.flatnonzero(slope_flag): reason[i]="slope" if reason[i]=="accepted" else reason[i]+";slope"
    flat=np.r_[False,np.abs(np.diff(sig))<=clipping_tolerance]; min_flat=max(2,int(round(clipping_seconds*sampling_rate_hz))); clip=np.zeros(len(sig),bool)
    i=0
    while i<len(flat):
        v=flat[i]; j=i+1
        while j<len(flat) and flat[j]==v:j+=1
        if v and j-i>=min_flat: clip[i:j]=True
        i=j
    for i in np.flatnonzero(clip): reason[i]="clipping" if reason[i]=="accepted" else reason[i]+";clipping"
    initial=range_flag|slope_flag|clip; island=_short_islands(~initial,max(1,int(round(min_valid_island_seconds*sampling_rate_hz))))
    for i in np.flatnonzero(island): reason[i]="short_valid_island" if reason[i]=="accepted" else reason[i]+";short_valid_island"
    artifact=_expand_flags(initial|island,max(0,int(round(artifact_epoch_seconds*sampling_rate_hz)))); reason[artifact&(reason=="accepted")]="artifact_epoch"
    clean=sig.copy(); clean[artifact]=np.nan; clean=_interp_na(clean); processed=_running_mean(clean,max(1,int(round(smoothing_seconds*sampling_rate_hz))))
    out=d.copy(); out["scr_raw"]=sig; out["scr_clean"]=clean; out["scr_processed"]=processed; out["pspm_artifact"]=artifact; out["pspm_artifact_reason"]=reason
    artifacts=_artifact_table(time,artifact,reason)
    summary=pd.DataFrame([{"n_samples":len(sig),"sampling_rate_hz":sampling_rate_hz,"n_artifact_samples":int(artifact.sum()),"artifact_fraction":float(artifact.mean()) if len(artifact) else np.nan,"n_artifact_epochs":len(artifacts),"mean_scr_processed":float(np.nanmean(processed)),"sd_scr_processed":float(np.nanstd(processed,ddof=1)) if np.isfinite(processed).sum()>1 else np.nan}])
    settings={"range":tuple(range),"slope_limit_per_s":slope_limit_per_s,"clipping_tolerance":clipping_tolerance,"clipping_seconds":clipping_seconds,"min_valid_island_seconds":min_valid_island_seconds,"artifact_epoch_seconds":artifact_epoch_seconds,"smoothing_seconds":smoothing_seconds,"sampling_rate_hz":sampling_rate_hz}
    return {"signal":out,"artifacts":artifacts,"summary":summary,"settings":settings}


def extract_gazepoint_segments_pspm_style(data,events,signal_col,time_col=None,event_time_col="onset_time_s",event_id_col=None,condition_col=None,pre_s=1,post_s=5,baseline_window=(-1,0),baseline_correct=True):
    d,tc=_prepare_time_data(data,time_col,None)
    if signal_col not in d.columns: raise ValueError("`signal_col` not found.")
    if not isinstance(events,pd.DataFrame) or event_time_col not in events.columns: raise ValueError("`events` must contain `event_time_col`.")
    time=_num(d[tc]); signal=_num(d[signal_col]); rows=[]
    for i,ev in events.reset_index(drop=True).iterrows():
        onset=float(pd.to_numeric(pd.Series([ev[event_time_col]]),errors="coerce").iloc[0]); idx=np.flatnonzero((time>=onset-pre_s)&(time<=onset+post_s))
        if not len(idx): continue
        rel=time[idx]-onset; b_local=(rel>=baseline_window[0])&(rel<=baseline_window[1]); bidx=idx[b_local]
        baseline=float(np.nanmean(signal[bidx])) if len(bidx) and np.isfinite(signal[bidx]).any() else np.nan
        ev_id=ev[event_id_col] if event_id_col and event_id_col in events.columns else i+1
        cond=str(ev[condition_col]) if condition_col and condition_col in events.columns else "event"
        for pos,r in zip(idx,rel):
            rows.append({"event_id":ev_id,"condition":cond,"onset_time_s":onset,"sample_index":int(pos)+1,"time_s":time[pos],"relative_time_s":r,"value":signal[pos],"baseline":baseline,"value_baseline_corrected":signal[pos]-baseline if baseline_correct else signal[pos]})
    return pd.DataFrame(rows)


def create_gazepoint_pspm_glm_design(events, time, time_col=None, onset_col="onset_time_s", condition_col="condition", duration_col=None, response="scr", response_length_s=20, include_derivative=False, add_intercept=True):
    if isinstance(time, pd.DataFrame):
        td,tc=_prepare_time_data(time,time_col,None); tt=_num(td[tc])
    else:
        tt=np.asarray(time,dtype=float)
    tt=tt[np.isfinite(tt)]
    if len(tt)<3: raise ValueError("At least three time points are required.")
    if not isinstance(events,pd.DataFrame) or onset_col not in events.columns: raise ValueError("`events` must contain `onset_col`.")
    evs=events.copy()
    if condition_col not in evs.columns: evs[condition_col]="event"
    dtvals=np.diff(np.unique(np.sort(tt))); dtvals=dtvals[np.isfinite(dtvals)&(dtvals>0)]
    if not len(dtvals): raise ValueError("Could not infer sampling interval from `time`.")
    dt=float(np.median(dtvals)); k=_kernel(dt,response,response_length_s)
    design=pd.DataFrame({"time_s":tt})
    if add_intercept: design["intercept"]=1.0
    used=set()
    for cond in pd.unique(evs[condition_col].astype(str)):
        subset=evs.loc[evs[condition_col].astype(str)==cond]
        impulse=np.zeros(len(tt),float)
        for _,ev in subset.iterrows():
            onset=float(pd.to_numeric(pd.Series([ev[onset_col]]),errors="coerce").iloc[0])
            if not np.isfinite(onset): continue
            dur=float(pd.to_numeric(pd.Series([ev[duration_col]]),errors="coerce").iloc[0]) if duration_col and duration_col in subset.columns else 0.0
            if np.isfinite(dur) and dur>dt: idx=np.flatnonzero((tt>=onset)&(tt<=onset+dur))
            else: idx=np.array([int(np.argmin(np.abs(tt-onset)))])
            impulse[idx]+=1.0
        reg=np.convolve(impulse,k,mode="full")[:len(impulse)]
        nm=_safe_name(cond); base=nm; n=1
        while nm in used: n+=1; nm=f"{base}.{n}"
        used.add(nm); col=f"pspm_{nm}"; design[col]=reg
        if include_derivative: design[f"{col}_derivative"]=np.r_[0.0,np.diff(reg)]/dt
    design.attrs.update({"kernel":k,"response":response,"response_length_s":response_length_s})
    return design


def fit_gazepoint_convolution_glm(data, design, signal_col, time_col=None, design_time_col="time_s", regressor_cols=None):
    d,tc=_prepare_time_data(data,time_col,None)
    if signal_col not in d.columns: raise ValueError("`signal_col` not found.")
    if not isinstance(design,pd.DataFrame) or design_time_col not in design.columns: raise ValueError("`design` must be a data frame containing `design_time_col`.")
    y0=_num(d[signal_col]); t0=_num(d[tc]); td=_num(design[design_time_col])
    same=len(y0)==len(td) and len(y0)>0 and np.nanmax(np.abs(t0-td))<=1e-8
    if not same:
        ok=np.isfinite(t0)&np.isfinite(y0)
        if ok.sum()<2: raise ValueError("Insufficient finite signal samples for interpolation.")
        order=np.argsort(t0[ok]); y=np.interp(td,t0[ok][order],y0[ok][order])
    else: y=y0
    if regressor_cols is None: regressor_cols=[c for c in design.columns if c!=design_time_col]
    regressor_cols=[regressor_cols] if isinstance(regressor_cols,str) else list(regressor_cols)
    if not regressor_cols: raise ValueError("No regressors found in `design`.")
    missing=[c for c in regressor_cols if c not in design.columns]
    if missing: raise ValueError("Regressors not found: "+", ".join(missing))
    X=design[regressor_cols].apply(pd.to_numeric,errors="coerce").to_numpy(float); good=np.isfinite(y)&np.isfinite(X).all(axis=1)
    Xg=X[good]; yg=y[good]
    if len(yg)==0: raise ValueError("No complete rows available for GLM fitting.")
    beta,_,rank,_=np.linalg.lstsq(Xg,yg,rcond=None); fitted=X@beta; residual=y-fitted
    rss=float(np.sum((yg-Xg@beta)**2)); n=len(yg); p=Xg.shape[1]; df=max(0,n-int(rank)); tss=float(np.sum((yg-np.mean(yg))**2)); sigma2=rss/df if df>0 else np.nan
    se=np.full(len(beta),np.nan)
    if np.isfinite(sigma2) and int(rank)==p: se=np.sqrt(np.diag(np.linalg.inv(Xg.T@Xg))*sigma2)
    stat=beta/se; pval=2*t_dist.sf(np.abs(stat),df) if df>0 else np.full(len(beta),np.nan)
    coefs=pd.DataFrame({"term":regressor_cols,"estimate":beta,"std_error":se,"statistic":stat,"p_value":pval})
    predictions=pd.DataFrame({"time_s":td,"observed":y,"fitted":fitted,"residual":residual})
    summary=pd.DataFrame([{"n":n,"n_regressors":p,"rank":int(rank),"df_residual":df,"rss":rss,"r_squared":1-rss/tss if tss>0 else np.nan,"aic":n*np.log(rss/n)+2*p if n>0 and rss>0 else np.nan}])
    return {"coefficients":coefs,"predictions":predictions,"summary":summary,"design":design.copy(),"signal_col":signal_col,"regressor_cols":regressor_cols,"response":design.attrs.get("response"),"class":"gazepoint_pspm_glm"}


def export_gazepoint_pspm_model_estimates(model, path, format=None, include_predictions=True):
    if not isinstance(model,dict) or "coefficients" not in model: raise TypeError("`model` must be a PsPM-style GLM result.")
    p=Path(path)
    if format is None:
        ext=p.suffix.lower().lstrip("."); format=ext if ext in {"csv","rds","json"} else "csv"
    format=str(format).lower()
    if format not in {"csv","rds","json"}: raise ValueError("Invalid `format`.")
    if not p.suffix: p=p.with_suffix("."+format)
    p.parent.mkdir(parents=True,exist_ok=True)
    manifest=[]
    def guard(q):
        return None
    if format == "csv":
        guard(p); model["coefficients"].to_csv(p,index=False); manifest.append({"file":str(p),"role":"coefficients"})
        sp=p.with_name(p.stem+"_summary.csv"); guard(sp); model.get("summary",pd.DataFrame()).to_csv(sp,index=False); manifest.append({"file":str(sp),"role":"summary"})
        if include_predictions and isinstance(model.get("predictions"),pd.DataFrame):
            pp=p.with_name(p.stem+"_predictions.csv"); guard(pp); model["predictions"].to_csv(pp,index=False); manifest.append({"file":str(pp),"role":"predictions"})
    elif format == "rds":
        guard(p)
        with p.open("wb") as f: pickle.dump(model,f)
        manifest.append({"file":str(p),"role":"model_rds"})
    else:
        guard(p)
        payload={}
        for k,v in model.items():
            if isinstance(v,pd.DataFrame): payload[k]=v.replace({np.nan:None}).to_dict(orient="records")
            elif isinstance(v,np.ndarray): payload[k]=v.tolist()
            elif isinstance(v,(str,int,float,bool,list,dict,type(None))): payload[k]=v
        p.write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8"); manifest.append({"file":str(p),"role":"model_json"})
    return pd.DataFrame(manifest)
