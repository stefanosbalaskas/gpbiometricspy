from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal, stats

from .advanced_nonlinear import _sample_entropy, _approx_entropy


def _df(x):
    if not isinstance(x,pd.DataFrame): raise TypeError("input must be a data frame.")
    return x.copy()

def _cols(x): return [] if x is None else ([x] if isinstance(x,str) else list(x))

def _groups(df, cols=None):
    cols=_cols(cols); miss=[c for c in cols if c not in df]
    if miss: raise ValueError("Missing `group_cols`: "+", ".join(miss))
    if not cols:return [("all_rows",np.arange(len(df)),{})]
    key=df[cols].astype(object).where(df[cols].notna(),"<NA>").astype(str).agg(" | ".join,axis=1)
    return [(str(k),np.flatnonzero(key.to_numpy()==k),df.iloc[np.flatnonzero(key.to_numpy()==k)[0]][cols].to_dict()) for k in pd.unique(key)]

def _sampling(time, sampling_rate=None):
    if sampling_rate is not None:
        if not np.isfinite(sampling_rate) or sampling_rate<=0:return np.nan
        return float(sampling_rate)
    if time is None:return np.nan
    t=np.asarray(time,float);d=np.diff(t[np.isfinite(t)]);d=d[d>0]
    if not len(d):return np.nan
    med=float(np.median(d)); return 1/med if med>0 else np.nan

def _fill(x):
    x=np.asarray(x,float);ok=np.isfinite(x);idx=np.arange(len(x))
    if ok.all():return x.copy()
    if not ok.any():return np.zeros(len(x))
    if ok.sum()==1:return np.full(len(x),x[ok][0])
    return np.interp(idx,idx[ok],x[ok])

def _moving(x,w):
    return pd.Series(x).rolling(max(1,int(w)),center=True,min_periods=1).mean().to_numpy(float)

def _run_flags(mask,min_run):
    mask=np.asarray(mask,bool);out=np.zeros(len(mask),bool);runs=[];i=0
    while i<len(mask):
        if not mask[i]:i+=1;continue
        j=i
        while j+1<len(mask) and mask[j+1]:j+=1
        if j-i+1>=min_run:out[i:j+1]=True;runs.append((i,j))
        i=j+1
    return out,runs

def _constant_run_flags(values, min_run, zero_only=False):
    x=np.asarray(values,float);out=np.zeros(len(x),bool);runs=[];i=0
    while i<len(x):
        if not np.isfinite(x[i]): i+=1; continue
        j=i
        while j+1<len(x) and np.isfinite(x[j+1]) and x[j+1] == x[i]: j+=1
        if j-i+1>=int(min_run) and (not zero_only or x[i] == 0):
            out[i:j+1]=True;runs.append((i,j))
        i=j+1
    return out,runs

# ---- EDA artifact and peak/event workflow ----------------------------------

def audit_gazepoint_eda_artifacts(data, signal_col=None, time_col=None, group_cols=None, prefer_gsr_us=True, jump_threshold_sd=6, slope_threshold_sd=6, flat_run_length=20, zero_run_length=20, saturation_min=None, saturation_max=None, negative_allowed=None):
    df=_df(data)
    if signal_col is None:
        prefs=["GSR_US","GSR_US_PHASIC","EDA","GSR"] if prefer_gsr_us else ["GSR","GSR_US","GSR_US_PHASIC","EDA"]
        signal_col=next((c for c in prefs if c in df),None)
    if signal_col is None or signal_col not in df:raise ValueError("No usable EDA signal column was found.")
    if not pd.api.types.is_numeric_dtype(df[signal_col]):raise TypeError("`signal_col` must contain numeric values.")
    if time_col is not None and time_col not in df:raise ValueError("`time_col` was not found in `data`.")
    if negative_allowed is None:negative_allowed="phasic" in signal_col.lower()
    flags=pd.DataFrame(index=df.index)
    for c in ["flag_missing","flag_nonfinite","flag_jump","flag_slope","flag_flatline_run","flag_zero_run","flag_negative_conductance","flag_out_of_bounds"]:flags[c]=False
    runs=[]
    for gid,idx,_ in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][signal_col],errors="coerce").to_numpy(float);t=np.arange(len(x),dtype=float) if time_col is None else pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float)
        missing=np.isnan(x);nonfinite=~np.isfinite(x)&~missing;diff=np.r_[np.nan,np.diff(x)];dt=np.r_[np.nan,np.diff(t)];slope=diff/dt
        def rz(v):
            f=v[np.isfinite(v)]
            if len(f)<3:return np.zeros(len(v),bool)
            med=np.median(f);mad=1.4826*np.median(np.abs(f-med));sd=mad if np.isfinite(mad) and mad>0 else np.std(f,ddof=1)
            return np.isfinite(v)&(np.abs(v-med)> (jump_threshold_sd if v is diff else slope_threshold_sd)*sd) if np.isfinite(sd) and sd>0 else np.zeros(len(v),bool)
        fj=rz(diff); fs=rz(slope)
        flat,flat_runs=_constant_run_flags(x,int(flat_run_length),False)
        zero,zero_runs=_constant_run_flags(x,int(zero_run_length),True)
        neg=np.isfinite(x)&(x<0)&(not negative_allowed);bounds=np.zeros(len(x),bool)
        if saturation_min is not None:bounds|=np.isfinite(x)&(x<saturation_min)
        if saturation_max is not None:bounds|=np.isfinite(x)&(x>saturation_max)
        vals=[missing,nonfinite,fj,fs,flat,zero,neg,bounds]
        for c,v in zip(flags.columns,vals):flags.loc[df.index[idx],c]=v
        for c,v in zip(flags.columns,vals):
            rr,_=_run_flags(v,1)
            starts=np.flatnonzero(v & ~np.r_[False,v[:-1]])
            for st in starts:
                en=st
                while en+1<len(v) and v[en+1]:en+=1
                runs.append({"group_id":gid,"artifact_type":c,"start_index":int(st+1),"end_index":int(en+1),"n_rows":int(en-st+1)})
    flags["artifact_flag"]=flags.any(axis=1); row_flags=pd.concat([df.reset_index(drop=True),flags.reset_index(drop=True)],axis=1)
    counts={c:int(flags[c].sum()) for c in flags.columns if c.startswith("flag_")}
    overview=pd.DataFrame([{ "signal_col":signal_col,"input_rows":len(df),"artifact_rows":int(flags.artifact_flag.sum()),"artifact_rate":float(flags.artifact_flag.mean()) if len(df) else np.nan,"jump_rows":counts['flag_jump'],"slope_rows":counts['flag_slope'],"flatline_run_rows":counts['flag_flatline_run'],"zero_run_rows":counts['flag_zero_run'],"negative_conductance_rows":counts['flag_negative_conductance'],"out_of_bounds_rows":counts['flag_out_of_bounds'],"status":"pass" if not flags.artifact_flag.any() else ("fail_high_artifact_rate" if float(flags.artifact_flag.mean()) >= .5 else "warn_artifacts_detected")}])
    return {"overview":overview,"row_flags":row_flags,"group_summary":pd.DataFrame(),"artifact_runs":pd.DataFrame(runs),"settings":{"signal_col":signal_col,"time_col":time_col,"group_cols":_cols(group_cols),"negative_allowed":bool(negative_allowed)},"class":["gazepoint_eda_artifact_audit","list"]}


def _smooth_center(x,w):
    w=max(1,int(round(w)));w=w+1 if w%2==0 else w
    if w<=1:return np.asarray(x,float)
    sm=pd.Series(x).rolling(w,center=True,min_periods=w).mean().to_numpy(float);out=np.asarray(x,float).copy();ok=np.isfinite(sm);out[ok]=sm[ok];return out

def _candidate_peaks(x):
    return np.array([i for i in range(1,len(x)-1) if np.isfinite(x[i-1:i+2]).all() and x[i]>x[i-1] and x[i]>=x[i+1]],int)

def _filter_peaks(x,candidates,distance):
    if distance<=1 or len(candidates)<=1:return candidates
    selected=[]
    for i in candidates[np.argsort(x[candidates])[::-1]]:
        if not selected or all(abs(i-j)>=distance for j in selected):selected.append(int(i))
    return np.array(sorted(selected),int)

def detect_gazepoint_scr_peaks(data, signal_col=None, phasic_col=None, time_col=None, group_cols=None, prefer_vendor_phasic=True, amplitude_min=.01, recovery_fraction=.5, smooth_width=1, min_peak_distance=1):
    df=_df(data)
    if amplitude_min<0:raise ValueError("`amplitude_min` must be non-negative.")
    if not 0<recovery_fraction<1:raise ValueError("`recovery_fraction` must be between 0 and 1.")
    if min_peak_distance<1:raise ValueError("`min_peak_distance` must be positive.")
    if phasic_col and phasic_col in df:src=phasic_col
    elif prefer_vendor_phasic and "GSR_US_PHASIC" in df:src="GSR_US_PHASIC"
    elif signal_col and signal_col in df:src=signal_col
    else:src=next((c for c in ["GSR_US_PHASIC","GSR_US","EDA","GSR"] if c in df),None)
    if src is None:raise ValueError("No usable SCR signal column was found.")
    xall=pd.to_numeric(df[src],errors="coerce").to_numpy(float)
    if np.isnan(xall).all():raise TypeError("selected SCR signal column must be numeric")
    if time_col is None:time_col=next((c for c in ["time_ms","timestamp_ms","timestamp","TIME","Time","time","CNT","cnt"] if c in df),None)
    peaks=[];grows=[]; candidates_total=0; below=0; incomplete=0
    for gid,idx,base in _groups(df,group_cols):
        x=_smooth_center(xall[idx],smooth_width);t=np.arange(1,len(idx)+1,dtype=float) if time_col is None else pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float)
        cand=_filter_peaks(x,_candidate_peaks(x),int(round(min_peak_distance)));candidates_total+=len(cand);det=[];b=inc=0
        for p in cand:
            onset=p
            while onset>0 and np.isfinite(x[onset-1]) and np.isfinite(x[onset]) and x[onset-1]<=x[onset]:onset-=1
            amp=x[p]-x[onset]
            if not np.isfinite(amp) or amp<amplitude_min:b+=1;below+=1;continue
            target=x[p]-recovery_fraction*amp; rec=np.nan
            for j in range(p+1,len(x)):
                if np.isfinite(x[j]) and x[j]<=target:rec=j;break
            st="detected_incomplete_recovery" if not np.isfinite(rec) else "detected";inc+=int(st!="detected");incomplete+=int(st!="detected")
            row={**base,"group_id":gid,"peak_id":len(det)+1,"source_signal":src,"onset_row_id":int(idx[onset]+1),"peak_row_id":int(idx[p]+1),"recovery_row_id":int(idx[int(rec)]+1) if np.isfinite(rec) else np.nan,"onset_index":onset+1,"peak_index":p+1,"recovery_index":int(rec)+1 if np.isfinite(rec) else np.nan,"onset_time":t[onset],"peak_time":t[p],"recovery_time":t[int(rec)] if np.isfinite(rec) else np.nan,"onset_value":x[onset],"peak_value":x[p],"recovery_value":x[int(rec)] if np.isfinite(rec) else np.nan,"amplitude":amp,"rise_time":t[p]-t[onset] if np.isfinite(t[p]) and np.isfinite(t[onset]) else np.nan,"recovery_time_after_peak":t[int(rec)]-t[p] if np.isfinite(rec) else np.nan,"status":st};det.append(row);peaks.append(row)
        finite=x[np.isfinite(x)];gs="insufficient_signal" if len(finite)<3 else ("no_candidate_peaks" if not len(cand) else ("no_peaks_above_threshold" if not len(det) else ("peaks_detected_with_incomplete_recovery" if inc else "peaks_detected")))
        grows.append({**base,"group_id":gid,"rows":len(idx),"finite_signal_rows":len(finite),"candidate_peaks":len(cand),"detected_peaks":len(det),"below_threshold_peaks":b,"incomplete_recovery_peaks":inc,"status":gs})
    peakdf=pd.DataFrame(peaks); groupdf=pd.DataFrame(grows); detected=len(peakdf)
    status="peaks_detected" if detected else ("candidate_peaks_below_threshold" if candidates_total else "no_candidate_peaks")
    overview=pd.DataFrame([{"source_signal":src,"input_rows":len(df),"group_count":len(groupdf),"candidate_peaks":candidates_total,"detected_peaks":detected,"below_threshold_peaks":below,"incomplete_recovery_peaks":incomplete,"status":status}])
    return {"overview":overview,"peaks":peakdf,"group_summary":groupdf,"signal_summary":pd.DataFrame([{"source_signal":src,"input_rows":len(df),"finite_signal_rows":int(np.isfinite(xall).sum())}]),"settings":{"source_signal":src,"signal_col":signal_col,"phasic_col":phasic_col,"time_col":time_col,"group_cols":_cols(group_cols),"amplitude_min":amplitude_min,"recovery_fraction":recovery_fraction,"smooth_width":smooth_width,"min_peak_distance":min_peak_distance},"class":["gazepoint_scr_peak_detection","list"]}


def _events_from_ttl(data,time_col,ttl_cols,valid_col,event_detection="rising"):
    rows=[];t=pd.to_numeric(data[time_col],errors="coerce").to_numpy(float)
    for col in _cols(ttl_cols):
        x=pd.to_numeric(data[col],errors="coerce").fillna(0).to_numpy(float);active=x>0
        hit=active if event_detection=="active" else active & ~np.r_[False,active[:-1]]
        if valid_col and valid_col in data: hit &= pd.to_numeric(data[valid_col],errors="coerce").fillna(0).to_numpy(float)>0
        for i in np.flatnonzero(hit):rows.append({"event_id":f"{col}_{i+1}","event_label":col,"event_time":t[i],"source_row_id":i+1})
    return pd.DataFrame(rows)

def summarise_gazepoint_scr_event_windows(data=None, scr_peaks=None, events=None, time_col=None, event_time_col=None, event_id_col=None, event_label_col=None, group_cols=None, ttl_cols=None, ttl_valid_col=None, event_detection="rising", analysis_window=(0,6), response_window=(1,4), amplitude_col="amplitude", peak_time_col="peak_time", onset_time_col="onset_time", rise_time_col="rise_time", recovery_time_col="recovery_time_after_peak", peak_status_col="status", peak_selection="largest_amplitude", collapse_simultaneous_events=False):
    peaks=scr_peaks.get("peaks",pd.DataFrame()) if isinstance(scr_peaks,dict) else _df(scr_peaks)
    groups=_cols(group_cols)
    if len(analysis_window)!=2 or len(response_window)!=2 or response_window[0] < analysis_window[0] or response_window[1] > analysis_window[1]:
        raise ValueError("`response_window` must fall inside `analysis_window`.")
    if not isinstance(collapse_simultaneous_events,(bool,np.bool_)):
        raise ValueError("`collapse_simultaneous_events` must be TRUE or FALSE.")
    if peak_selection not in {"largest_amplitude","first_peak"}: raise ValueError("Invalid `peak_selection`.")
    if event_detection not in {"rising","active"}: raise ValueError("Invalid `event_detection`.")
    if events is None:
        if data is None or not ttl_cols: ev=pd.DataFrame()
        else:
            d=_df(data); tc=time_col or next((c for c in ["time","CNT","TIME"] if c in d),None)
            if tc is None:raise ValueError("No event time column could be determined.")
            ev=_events_from_ttl(d,tc,ttl_cols,ttl_valid_col,event_detection)
            for c in groups:
                if c in d and len(ev): ev[c]=[d.iloc[int(str(e).split('_')[-1])-1][c] for e in ev.event_id]
    else:
        ev=_df(events); etc=event_time_col or next((c for c in ["event_time","onset","time","CNT"] if c in ev),None)
        if etc is None:raise ValueError("`event_time_col` could not be determined.")
        ev=ev.copy();ev["event_time"]=pd.to_numeric(ev[etc],errors="coerce");ev["event_id"]=ev[event_id_col].astype(str) if event_id_col and event_id_col in ev else pd.Series([f"event_{i}" for i in range(1,len(ev)+1)],index=ev.index);ev["event_label"]=ev[event_label_col].astype(str) if event_label_col and event_label_col in ev else (ev["condition"].astype(str) if "condition" in ev else "event");ev["source_row_id"]=np.arange(1,len(ev)+1)
    if len(ev):
        if groups:
            missing=[c for c in groups if c not in ev]
            if missing: raise ValueError("`events` is missing grouping columns: "+", ".join(missing))
            ev["event_group_id"]=ev[groups].astype(object).where(ev[groups].notna(),"<NA>").astype(str).agg("||".join,axis=1)
        else:
            ev["event_group_id"]="all"
        if collapse_simultaneous_events:
            out=[]
            for _,d in ev.groupby(["event_group_id","event_time"],sort=False,dropna=False):
                row=d.iloc[0].copy(); ids=[str(v) for v in pd.unique(d.event_id.dropna())]; labs=[str(v) for v in pd.unique(d.event_label.dropna())]
                row["event_id"]="+".join(ids) if ids else "event";row["event_label"]="+".join(labs) if labs else "event";row["collapsed_event_count"]=len(d);row["collapsed_event_ids"]="+".join(ids);row["collapsed_event_labels"]="+".join(labs);out.append(row)
            ev=pd.DataFrame(out).reset_index(drop=True)
    if ev.empty:
        return {"overview":pd.DataFrame([{"event_count":0,"response_events":0,"response_rate":np.nan,"status":"fail_no_events"}]),"events":ev,"event_table":pd.DataFrame(),"window_qc":pd.DataFrame(),"qc":pd.DataFrame(),"settings":{},"class":["gazepoint_scr_event_window_summary","list"]}
    rows=[]
    for _,e in ev.iterrows():
        p=peaks.copy()
        for c in groups:
            if c in e and c in p:p=p[p[c].astype(str)==str(e[c])]
        pt=pd.to_numeric(p[peak_time_col],errors="coerce") if peak_time_col in p else pd.Series(dtype=float); et=float(e.event_time); ina=(pt>=et+analysis_window[0])&(pt<=et+analysis_window[1]);inr=(pt>=et+response_window[0])&(pt<=et+response_window[1]);ap=p[ina];rp=p[inr];sel=None
        if len(rp):sel=rp.loc[pd.to_numeric(rp[amplitude_col],errors="coerce").idxmax()] if peak_selection=="largest_amplitude" else rp.loc[pd.to_numeric(rp[peak_time_col],errors="coerce").idxmin()]
        row={c:e.get(c,np.nan) for c in groups};row.update({"event_id":str(e.event_id),"event_label":str(e.event_label),"event_time":et,"event_group_id":str(e.get("event_group_id","all")),"source_row_id":e.get("source_row_id",np.nan),"window_start":et+analysis_window[0],"window_end":et+analysis_window[1],"response_start":et+response_window[0],"response_end":et+response_window[1],"response_flag":int(sel is not None),"n_candidate_peaks":len(ap),"n_response_window_peaks":len(rp),"selected_peak_id":str(sel.get("peak_id")) if sel is not None and "peak_id" in sel else np.nan,"selected_peak_time":float(sel.get(peak_time_col)) if sel is not None else np.nan,"selected_onset_time":float(sel.get(onset_time_col)) if sel is not None and onset_time_col in sel else np.nan,"scr_latency":float(sel.get(peak_time_col))-et if sel is not None else np.nan,"scr_amplitude":float(sel.get(amplitude_col)) if sel is not None else np.nan,"scr_rise_time":float(sel.get(rise_time_col)) if sel is not None and rise_time_col in sel else np.nan,"scr_recovery_time":float(sel.get(recovery_time_col)) if sel is not None and recovery_time_col in sel else np.nan,"selected_peak_status":sel.get(peak_status_col) if sel is not None and peak_status_col in sel else np.nan,"event_status":"response_detected" if sel is not None else ("no_peaks_in_analysis_window" if not len(ap) else "no_peaks_in_response_window")});rows.append(row)
    tab=pd.DataFrame(rows);responses=int(tab.response_flag.sum());status="scr_event_windows_summarised" if responses else "warn_no_scr_responses"
    qrows=[]
    for gid,d in tab.groupby("event_group_id",sort=False,dropna=False):
        qr={"event_group_id":gid,"event_count":len(d),"response_events":int(d.response_flag.sum()),"response_rate":float(d.response_flag.mean()),"no_response_events":int((d.response_flag==0).sum()),"events_with_candidate_peaks":int((d.n_candidate_peaks>0).sum()),"events_with_response_window_peaks":int((d.n_response_window_peaks>0).sum()),"median_scr_amplitude":float(pd.to_numeric(d.scr_amplitude,errors="coerce").median()),"median_scr_latency":float(pd.to_numeric(d.scr_latency,errors="coerce").median())}
        for c in groups: qr[c]=d.iloc[0].get(c,np.nan)
        qrows.append(qr)
    qc=pd.DataFrame(qrows)
    return {"overview":pd.DataFrame([{"event_count":len(tab),"response_events":responses,"response_rate":responses/len(tab) if len(tab) else np.nan,"nonresponse_events":len(tab)-responses,"status":status}]),"events":ev,"event_table":tab,"window_qc":qc,"qc":qc,"settings":{"analysis_window":list(analysis_window),"response_window":list(response_window),"peak_selection":peak_selection,"collapse_simultaneous_events":collapse_simultaneous_events},"class":["gazepoint_scr_event_window_summary","list"]}


def screen_gazepoint_eda_nonresponders(x, group_cols=None, response_col="response_flag", amplitude_col="scr_amplitude", min_events=1, min_response_events=1, min_response_rate=.05, min_detected_peaks=1):
    if min_events<0:raise ValueError("`min_events` must be non-negative.")
    if not 0<=min_response_rate<=1:raise ValueError("`min_response_rate` must be between 0 and 1.")
    tab=x.get("event_table") if isinstance(x,dict) and "event_table" in x else (x.get("peaks") if isinstance(x,dict) and "peaks" in x else _df(x))
    groups=_cols(group_cols); rows=[]
    event_mode=response_col in tab
    for gid,idx,base in _groups(tab,groups):
        g=tab.iloc[idx]
        if event_mode:
            n=len(g);resp=int(pd.to_numeric(g[response_col],errors="coerce").fillna(0).gt(0).sum());rate=resp/n if n else np.nan;candidate=(n>=min_events and (resp<min_response_events or rate<min_response_rate));status="candidate_nonresponder" if candidate else ("insufficient_events" if n<min_events else "responder")
            rows.append({**base,"group_id":gid,"n_events":n,"response_events":resp,"response_rate":rate,"detected_peaks":np.nan,"candidate_nonresponder":candidate,"status":status})
        else:
            n=len(g);candidate=n<min_detected_peaks;rows.append({**base,"group_id":gid,"n_events":np.nan,"response_events":np.nan,"response_rate":np.nan,"detected_peaks":n,"candidate_nonresponder":candidate,"status":"candidate_nonresponder" if candidate else "responder"})
    summ=pd.DataFrame(rows);cand=summ[summ.candidate_nonresponder].copy();return {"overview":pd.DataFrame([{"group_count":len(summ),"candidate_nonresponder_count":len(cand),"status":"eda_nonresponder_screen_complete"}]),"group_summary":summ,"candidate_nonresponders":cand,"settings":{},"class":["gazepoint_eda_nonresponder_screen","list"]}


def prepare_gazepoint_scr_hurdle_model_data(scr_event_windows, response_col="response_flag", amplitude_col="scr_amplitude", latency_col="scr_latency", rise_time_col="scr_rise_time", recovery_time_col="scr_recovery_time", predictor_cols=None, factor_cols=None, numeric_cols=None, group_cols=None, event_id_col="event_id", amplitude_transform="none", amplitude_offset=1e-6, drop_missing_predictors=True):
    tab=scr_event_windows.get("event_table") if isinstance(scr_event_windows,dict) else _df(scr_event_windows)
    if response_col not in tab: raise ValueError("`response_col` was not found in `scr_event_windows`.")
    if amplitude_col not in tab: raise ValueError("`amplitude_col` was not found in `scr_event_windows`.")
    preds=_cols(predictor_cols);miss=[c for c in preds if c not in tab]
    if miss:raise ValueError("Requested columns were not found: "+", ".join(miss))
    out=tab.copy();out["scr_response_binary"]=(pd.to_numeric(out[response_col],errors="coerce").fillna(0)>0).astype(int);amp=pd.to_numeric(out[amplitude_col],errors="coerce");out["scr_amplitude_raw"]=amp
    if amplitude_transform=="log":out["scr_amplitude_model"]=np.log(amp+amplitude_offset)
    elif amplitude_transform=="log1p":out["scr_amplitude_model"]=np.log1p(amp)
    else:out["scr_amplitude_model"]=amp
    for c in _cols(factor_cols):
        if c in out:out[c]=out[c].astype("category")
    response=out.copy()
    if drop_missing_predictors and preds:response=response.dropna(subset=preds)
    amplitude=response[(response.scr_response_binary==1)&np.isfinite(response.scr_amplitude_model)].copy()
    rhs=" + ".join(preds) if preds else "1";groups=_cols(group_cols);rand=" + ".join(f"(1 | {g})" for g in groups);rhs2=rhs+(" + "+rand if rand else "")
    formulas=pd.DataFrame([{"model":"response","formula":f"scr_response_binary ~ {rhs2}"},{"model":"amplitude","formula":f"scr_amplitude_model ~ {rhs2}"}])
    st="scr_hurdle_model_data_prepared" if len(amplitude) else "warn_no_positive_amplitude_rows"
    return {"overview":pd.DataFrame([{"input_events":len(tab),"response_events":int(out.scr_response_binary.sum()),"response_model_rows":len(response),"amplitude_model_rows":len(amplitude),"status":st}]),"response_model_data":response,"amplitude_model_data":amplitude,"variable_summary":pd.DataFrame(),"model_formulas":formulas,"settings":{},"class":["gazepoint_scr_hurdle_model_data","list"]}


def run_gazepoint_scr_threshold_sensitivity(data, phasic_col=None, signal_col=None, time_col=None, group_cols=None, amplitude_min_values=(.005,.01,.02,.03), min_peak_distance_values=(1,5,10,20,30), recovery_fraction=.5, smooth_width=1, events=None, event_time_col=None, event_id_col=None, event_label_col=None, ttl_cols=None, ttl_valid_col=None, event_detection="rising", analysis_window=(0,6), response_window=(1,4), peak_selection="largest_amplitude", collapse_simultaneous_events=False, include_event_windows=True, keep_objects=False):
    if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame.")
    amps=np.asarray(amplitude_min_values,float).reshape(-1);dists=np.asarray(min_peak_distance_values,float).reshape(-1)
    if not len(amps) or np.any(~np.isfinite(amps)) or np.any(amps<0): raise ValueError("`amplitude_min_values` must be a non-empty non-negative numeric vector.")
    if not len(dists) or np.any(~np.isfinite(dists)) or np.any(dists<1): raise ValueError("`min_peak_distance_values` must contain values >= 1.")
    amps=np.unique(np.sort(amps));dists=np.unique(np.round(dists).astype(int))
    rows=[];objs=[];ew=[]
    for a in amps:
        for d in dists:
            p=detect_gazepoint_scr_peaks(data,signal_col,phasic_col,time_col,group_cols,True,float(a),recovery_fraction,smooth_width,int(d));row={"amplitude_min":a,"min_peak_distance":d,"detected_peaks":int(p['overview'].loc[0,'detected_peaks']),"status":"sensitivity_completed"}
            w=None
            if include_event_windows and (events is not None or ttl_cols):
                w=summarise_gazepoint_scr_event_windows(data,p,events,time_col,event_time_col,event_id_col,event_label_col,group_cols,ttl_cols,ttl_valid_col,event_detection,analysis_window,response_window,peak_selection=peak_selection,collapse_simultaneous_events=collapse_simultaneous_events);row["event_count"]=int(w['overview'].loc[0,'event_count']);row["response_events"]=int(w['overview'].loc[0,'response_events']); tmp=w.get('window_qc',w['event_table']).copy();tmp['amplitude_min']=a;tmp['min_peak_distance']=d;ew.append(tmp)
            rows.append(row)
            if keep_objects:objs.append({"peaks":p,"event_windows":w})
    grid=pd.DataFrame(rows);return {"overview":pd.DataFrame([{"grid_rows":len(grid),"status":"scr_threshold_sensitivity_completed"}]),"sensitivity_grid":grid,"event_window_summary":pd.concat(ew,ignore_index=True) if ew else pd.DataFrame(),"objects":objs if keep_objects else None,"settings":{},"class":["gazepoint_scr_threshold_sensitivity","list"]}

# ---- spectral / denoising ---------------------------------------------------
def extract_gazepoint_eda_spectral_power(dat, eda_col="GSR_US", time_col=None, group_cols=None, sampling_rate=None, band=(.045,.25), min_samples=32, detrend=True):
    df=_df(dat)
    if eda_col not in df or not pd.api.types.is_numeric_dtype(df[eda_col]):raise ValueError("`eda_col` must identify a numeric column.")
    rows=[]
    for gid,idx,base in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][eda_col],errors="coerce").to_numpy(float);ok=np.isfinite(x);fs=_sampling(pd.to_numeric(df.iloc[idx][time_col],errors="coerce") if time_col else None,sampling_rate);row={**base,"unit_id":gid,"n_rows":len(idx),"n_finite":int(ok.sum()),"sampling_rate_hz":fs,"band_lower_hz":band[0],"band_upper_hz":band[1]}
        if ok.sum()<min_samples or not np.isfinite(fs):row.update(total_power=np.nan,band_power=np.nan,relative_band_power=np.nan,peak_frequency_hz=np.nan,spectral_centroid_hz=np.nan,status="insufficient_data")
        else:
            y=x[ok];y=signal.detrend(y) if detrend else y-y.mean();f,p=signal.periodogram(y,fs=fs);m=f>0;f=f[m];p=p[m];ib=(f>=band[0])&(f<=band[1]);tot=float(p.sum());bp=float(p[ib].sum());row.update(total_power=tot,band_power=bp,relative_band_power=bp/tot if tot>0 else np.nan,peak_frequency_hz=float(f[np.argmax(p)]) if len(p) else np.nan,spectral_centroid_hz=float(np.sum(f*p)/tot) if tot>0 else np.nan,status="spectral_power_extracted")
        rows.append(row)
    s=pd.DataFrame(rows);ok=s.status.eq("spectral_power_extracted");st="eda_spectral_power_extracted" if ok.all() else ("eda_spectral_power_partial" if ok.any() else "eda_spectral_power_failed")
    return {"overview":pd.DataFrame([{"group_count":len(s),"spectral_rows":len(s),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"eda_col":eda_col,"band_lower_hz":band[0],"band_upper_hz":band[1],"status":st}]),"spectral_summary":s,"settings":{"eda_col":eda_col,"band":list(band)},"class":["gazepoint_eda_spectral_power","list"]}

def denoise_gazepoint_eda_wavelet(dat, eda_col="GSR_US", group_cols=None, output_col=None, levels=3, threshold_multiplier=1, overwrite=False):
    df=_df(dat);output_col=output_col or eda_col+"_wavelet_denoised"
    if eda_col not in df:raise ValueError(f"Column `{eda_col}` was not found in `dat`.")
    if output_col in df and not overwrite:raise ValueError("Output column already exists.")
    out=df.copy();out[output_col]=np.nan;rows=[]
    for gid,idx,_ in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][eda_col],errors="coerce").to_numpy(float);ok=np.isfinite(x)
        if ok.sum()<8:rows.append({"unit_id":gid,"n_rows":len(idx),"n_finite":int(ok.sum()),"threshold":np.nan,"levels_used":np.nan,"status":"insufficient_finite_samples"});continue
        z=_fill(x);detail=np.diff(z);sigma=np.median(np.abs(detail-np.median(detail)))/.6745 if len(detail) else 0;thr=threshold_multiplier*sigma*np.sqrt(2*np.log(len(z))) if sigma>0 else 0
        # dependency-light Haar-like smoothing: repeated pair averaging + residual soft threshold
        smooth=z.copy()
        for _ in range(min(int(levels),int(np.floor(np.log2(max(2,len(z))))))):smooth=_moving(smooth,2)
        residual=z-smooth;den=smooth+np.sign(residual)*np.maximum(np.abs(residual)-thr,0);den[~ok]=np.nan;out.loc[out.index[idx],output_col]=den;rows.append({"unit_id":gid,"n_rows":len(idx),"n_finite":int(ok.sum()),"threshold":thr,"levels_used":int(levels),"status":"wavelet_denoised"})
    tab=pd.DataFrame(rows);good=int(tab.status.eq("wavelet_denoised").sum());st="eda_wavelet_denoising_complete" if good==len(tab) else ("eda_wavelet_denoising_partial" if good else "eda_wavelet_denoising_failed");out.attrs["wavelet_denoising_overview"]={"status":st,"input_rows":len(df),"successful_groups":good};out.attrs["wavelet_denoising_summary"]=tab.to_dict("records");out.attrs["class"]=["gazepoint_eda_wavelet_denoised","data.frame"];return out

def extract_gazepoint_eda_tvsymp(dat, eda_col="GSR_US", time_col="CNT", group_cols=None, sampling_rate=None, band=(.08,.24), window_seconds=60, step_seconds=5, min_valid_fraction=.70, normalise=True):
    df=_df(dat);rows=[]
    for gid,idx,base in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][eda_col],errors="coerce").to_numpy(float);t=pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float) if time_col in df else np.arange(len(idx));fs=_sampling(t,sampling_rate)
        if not np.isfinite(fs):continue
        wn=max(4,int(round(window_seconds*fs)));step=max(1,int(round(step_seconds*fs)))
        vals=[]
        for st in range(0,max(1,len(x)-wn+1),step):
            seg=x[st:min(len(x),st+wn)];valid=np.isfinite(seg)
            if valid.mean()<min_valid_fraction or valid.sum()<4:continue
            y=_fill(seg);f,p=signal.periodogram(signal.detrend(y),fs=fs);ib=(f>=band[0])&(f<=band[1]);power=float(p[ib].sum());vals.append((st,power,float(t[min(len(t)-1,st+len(seg)//2)])))
        denom=np.mean([v[1] for v in vals]) if vals and normalise else 1
        for st,pw,tm in vals:rows.append({**base,"group_id":gid,"window_start_index":st+1,"time":tm,"tvsymp_power":pw,"edasympn":pw/denom if denom and np.isfinite(denom) else np.nan,"status":"tvsymp_extracted"})
    ts=pd.DataFrame(rows);return {"overview":pd.DataFrame([{"window_rows":len(ts),"status":"eda_tvsymp_extracted" if len(ts) else "eda_tvsymp_failed"}]),"tvsymp_timeseries":ts,"settings":{"band":list(band),"window_seconds":window_seconds,"step_seconds":step_seconds},"class":["gazepoint_eda_tvsymp","list"]}

def plot_gazepoint_eda_gram(dat, eda_col="GSR_US", time_col="CNT", group_cols=None, group_id_to_plot=None, sampling_rate=None, window_seconds=30, step_seconds=5, frequency_range=(.01,.50), frequency_bins=64, log_power=True, plot=True, main="EDA-gram"):
    df=_df(dat);groups=_groups(df,group_cols);gid,idx,base=next((g for g in groups if group_id_to_plot is None or g[0]==str(group_id_to_plot)),groups[0]);x=pd.to_numeric(df.iloc[idx][eda_col],errors="coerce").to_numpy(float);t=pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float);fs=_sampling(t,sampling_rate);wn=max(8,int(round(window_seconds*fs)));step=max(1,int(round(step_seconds*fs)));freqs=np.linspace(frequency_range[0],frequency_range[1],frequency_bins);rows=[]
    for st in range(0,max(1,len(x)-wn+1),step):
        y=_fill(x[st:min(len(x),st+wn)]);f,p=signal.periodogram(signal.detrend(y),fs=fs);interp=np.interp(freqs,f,p,left=np.nan,right=np.nan);tm=t[min(len(t)-1,st+len(y)//2)]
        for fr,pw in zip(freqs,interp):rows.append({"group_id":gid,"time":tm,"frequency_hz":fr,"power":np.log10(max(pw,np.finfo(float).tiny)) if log_power and np.isfinite(pw) else pw})
    tab=pd.DataFrame(rows);fig=None
    if plot and len(tab):fig,ax=plt.subplots();im=ax.tricontourf(tab.time,tab.frequency_hz,tab.power,levels=20);ax.set_title(main);ax.set_xlabel("time");ax.set_ylabel("frequency (Hz)")
    return {"gram_table":tab,"figure":fig,"settings":{"group_id":gid,"sampling_rate":fs},"class":["gazepoint_eda_gram","list"]}

# ---- nonlinear HRV ----------------------------------------------------------
def _fuzzy_phi(x,m,r,power):
    emb=np.lib.stride_tricks.sliding_window_view(x,m);count=[]
    for i,row in enumerate(emb):
        others=np.delete(emb,i,axis=0)
        if not len(others):continue
        d=np.max(np.abs((others-others.mean(axis=1,keepdims=True))-(row-row.mean())),axis=1);count.extend(np.exp(-((d/r)**power)))
    return np.mean(count) if count else np.nan

def extract_gazepoint_hrv_fuzzy_csi(dat, ibi_col="IBI", group_cols=None, m=2, r_multiplier=.2, fuzzy_power=2, min_intervals=10):
    df=_df(dat);rows=[]
    for gid,idx,base in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][ibi_col],errors="coerce").to_numpy(float);x=x[np.isfinite(x)&(x>0)];row={**base,"group_id":gid,"n_intervals":len(x)}
        if len(x)<min_intervals or np.std(x,ddof=1)==0:row.update(fuzzy_entropy=np.nan,sd1=np.nan,sd2=np.nan,csi=np.nan,cvi=np.nan,modified_csi=np.nan,status="insufficient_intervals")
        else:
            r=r_multiplier*np.std(x,ddof=1);a=_fuzzy_phi(x,m+1,r,fuzzy_power);b=_fuzzy_phi(x,m,r,fuzzy_power);fe=-np.log(a/b) if np.isfinite(a) and np.isfinite(b) and a>0 and b>0 else np.nan;dx=np.diff(x);sdnn=np.std(x,ddof=1);dv=np.var(dx,ddof=1);sd1=np.sqrt(dv/2);sd2=np.sqrt(max(2*sdnn**2-.5*dv,0));row.update(fuzzy_entropy=fe,sd1=sd1,sd2=sd2,csi=sd2/sd1 if sd1>0 else np.nan,cvi=np.log10(sd1*sd2) if sd1>0 and sd2>0 else np.nan,modified_csi=sd2**2/sd1 if sd1>0 else np.nan,status="fuzzy_csi_extracted")
        rows.append(row)
    f=pd.DataFrame(rows);ok=f.status.eq("fuzzy_csi_extracted");return {"overview":pd.DataFrame([{"group_count":len(f),"status":"fuzzy_csi_extracted" if ok.all() else ("fuzzy_csi_partial" if ok.any() else "fuzzy_csi_failed")}]),"features":f,"settings":{},"class":["gazepoint_hrv_fuzzy_csi","list"]}

def _match_count(x,m,r):
    if len(x)<m+1:return 0
    emb=np.lib.stride_tricks.sliding_window_view(x,m);c=0
    for i in range(len(emb)-1):c+=int(np.sum(np.max(np.abs(emb[i+1:]-emb[i]),axis=1)<=r))
    return c

def extract_gazepoint_hrv_rcmse(dat, ibi_col="IBI", group_cols=None, scales=range(1,11), m=2, r_multiplier=.2, min_intervals=20):
    df=_df(dat);sc=sorted(set(int(s) for s in scales));sr=[];summ=[]
    if not sc or min(sc)<1:raise ValueError("`scales` must contain positive integer-like values.")
    for gid,idx,_ in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][ibi_col],errors="coerce").to_numpy(float);x=x[np.isfinite(x)&(x>0)];vals=[]
        if len(x)<min_intervals or (len(x)>1 and np.std(x,ddof=1)==0):
            for s in sc:sr.append({"group_id":gid,"scale":s,"rcmse":np.nan,"match_count_m":np.nan,"match_count_m1":np.nan,"status":"insufficient_intervals"})
            summ.append({"group_id":gid,"n_intervals":len(x),"mean_rcmse":np.nan,"finite_scales":0,"status":"insufficient_intervals"});continue
        r=r_multiplier*np.std(x,ddof=1)
        for s in sc:
            cm=cm1=0
            for off in range(s):
                y=x[off:];n=len(y)//s
                if n< m+2:continue
                cg=y[:n*s].reshape(n,s).mean(axis=1);cm+=_match_count(cg,m,r);cm1+=_match_count(cg,m+1,r)
            val=-np.log(cm1/cm) if cm>0 and cm1>0 else np.nan;vals.append(val);sr.append({"group_id":gid,"scale":s,"rcmse":val,"match_count_m":cm,"match_count_m1":cm1,"status":"rcmse_extracted" if np.isfinite(val) else "rcmse_not_estimated"})
        finite=np.asarray(vals)[np.isfinite(vals)];summ.append({"group_id":gid,"n_intervals":len(x),"mean_rcmse":float(np.mean(finite)) if len(finite) else np.nan,"finite_scales":len(finite),"status":"rcmse_extracted" if len(finite) else "rcmse_not_estimated"})
    sdf=pd.DataFrame(sr);summary=pd.DataFrame(summ);ok=summary.status.eq("rcmse_extracted");return {"overview":pd.DataFrame([{"group_count":len(summary),"scale_rows":len(sdf),"status":"rcmse_extraction_complete" if ok.all() else ("rcmse_extraction_partial" if ok.any() else "rcmse_extraction_failed")}]),"rcmse_by_scale":sdf,"summary":summary,"settings":{},"class":["gazepoint_hrv_rcmse","list"]}

def test_gazepoint_hrv_nonlinearity(dat, ibi_col="IBI", group_cols=None, metric="sample_entropy", n_surrogates=99, surrogate_method="phase_randomized", m=2, r_multiplier=.2, statistic_fun=None, seed=None):
    df=_df(dat);rng=np.random.default_rng(seed);res=[];sur=[]
    def statistic(x):
        if statistic_fun is not None:return float(statistic_fun(x))
        sd=np.std(x,ddof=1);r=r_multiplier*sd
        if metric=="sample_entropy":return _sample_entropy(x,m,r)
        if metric=="approximate_entropy":return _approx_entropy(x,m,r)
        dx=np.diff(x);sd1=np.sqrt(np.var(dx,ddof=1)/2);sd2=np.sqrt(max(2*sd**2-.5*np.var(dx,ddof=1),0));return sd1/sd2 if sd2>0 else np.nan
    for gid,idx,base in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][ibi_col],errors="coerce").to_numpy(float);x=x[np.isfinite(x)&(x>0)];obs=statistic(x);sv=[]
        for j in range(int(n_surrogates)):
            if surrogate_method=="shuffle":y=rng.permutation(x)
            else:
                ft=np.fft.rfft(x-x.mean());phase=rng.uniform(0,2*np.pi,len(ft));phase[0]=0
                if len(x)%2==0:phase[-1]=0
                y=np.fft.irfft(np.abs(ft)*np.exp(1j*phase),n=len(x))+x.mean()
            v=statistic(y);sv.append(v);sur.append({**base,"group_id":gid,"surrogate_id":j+1,"statistic":v})
        finite=np.asarray(sv)[np.isfinite(sv)];p=(1+np.sum(np.abs(finite-np.mean(finite))>=abs(obs-np.mean(finite))))/(1+len(finite)) if len(finite) and np.isfinite(obs) else np.nan;res.append({**base,"group_id":gid,"observed_statistic":obs,"surrogate_mean":np.mean(finite) if len(finite) else np.nan,"p_two_sided":p,"status":"surrogate_test_complete" if len(finite) else "surrogate_test_failed"})
    return {"overview":pd.DataFrame([{"group_count":len(res),"status":"hrv_nonlinearity_test_complete"}]),"results":pd.DataFrame(res),"surrogate_statistics":pd.DataFrame(sur),"settings":{},"class":["gazepoint_hrv_nonlinearity_test","list"]}

# ---- respiration / artifact / drift ----------------------------------------
def extract_gazepoint_respiration_ceemdan(dat, signal_col, time_col="CNT", group_cols=None, sampling_rate=None, respiration_band=(.10,.60), scales=(5,15,30,60,120), external_fun=None):
    df=_df(dat);ts=[];summ=[];comps=[]
    for gid,idx,base in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][signal_col],errors="coerce").to_numpy(float);t=pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float) if time_col in df else np.arange(len(idx));fs=_sampling(t,sampling_rate)
        if np.isfinite(fs) and np.isfinite(x).sum()>=8:
            y=_fill(x);lo,hi=respiration_band;nyq=fs/2
            if hi<nyq:
                b,a=signal.butter(2,[lo/nyq,hi/nyq],btype='band');proxy=signal.filtfilt(b,a,y) if len(y)>12 else y-y.mean()
            else:proxy=y-y.mean()
            f,p=signal.periodogram(proxy,fs=fs);mask=(f>=lo)&(f<=hi);rate=float(f[mask][np.argmax(p[mask])]) if mask.any() else np.nan;st="respiration_proxy_extracted";ts.extend([{**base,"row_index":int(idx[j]+1),"group_id":gid,"time":t[j],"respiration_proxy":proxy[j],"status":st} for j in range(len(idx))]);summ.append({**base,"group_id":gid,"n_rows":len(idx),"sampling_rate_hz":fs,"selected_component_count":1,"proxy_respiration_rate_hz":rate,"proxy_respiration_rate_bpm":rate*60,"status":st});comps.append({"group_id":gid,"component":"bandpass_proxy","dominant_frequency_hz":rate,"selected_for_respiration":True,"variance":np.var(proxy,ddof=1),"method":"dependency_light_multiscale_fallback"})
        else:summ.append({**base,"group_id":gid,"n_rows":len(idx),"sampling_rate_hz":fs,"selected_component_count":0,"proxy_respiration_rate_hz":np.nan,"proxy_respiration_rate_bpm":np.nan,"status":"insufficient_signal_or_sampling_rate"})
    sd=pd.DataFrame(summ);ok=sd.status.eq("respiration_proxy_extracted");return {"overview":pd.DataFrame([{"group_count":len(sd),"component_rows":len(comps),"timeseries_rows":len(ts),"status":"ceemdan_respiration_proxy_complete" if ok.all() else ("ceemdan_respiration_proxy_partial" if ok.any() else "ceemdan_respiration_proxy_failed")}]),"component_table":pd.DataFrame(comps),"respiration_timeseries":pd.DataFrame(ts),"summary":sd,"settings":{},"class":["gazepoint_respiration_ceemdan","list"]}

def fuse_gazepoint_respiration_kalman(dat, primary_col, secondary_col, time_col=None, group_cols=None, process_var=.01, primary_var=.05, secondary_var=.05, output_col="respiration_kalman_fused"):
    df=_df(dat);out=df.copy();out[output_col]=np.nan;out[output_col+"_variance"]=np.nan;out[output_col+"_status"]="not_processed";summ=[]
    for gid,idx,base in _groups(df,group_cols):
        idx=np.asarray(idx)
        if time_col: idx=idx[np.argsort(pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float),kind="stable")]
        p=pd.to_numeric(df.iloc[idx][primary_col],errors="coerce").to_numpy(float);s=pd.to_numeric(df.iloc[idx][secondary_col],errors="coerce").to_numpy(float);state=np.nan;var=1.;states=[];vars=[];sts=[]
        for a,b in zip(p,s):
            var+=process_var;meas=[]
            if np.isfinite(a):meas.append((a,primary_var,"primary"))
            if np.isfinite(b):meas.append((b,secondary_var,"secondary"))
            if not meas:states.append(state);vars.append(var);sts.append("missing");continue
            if not np.isfinite(state):state=meas[0][0]
            for z,r,_ in meas:k=var/(var+r);state=state+k*(z-state);var=(1-k)*var
            states.append(state);vars.append(var);sts.append("fused" if len(meas)==2 else meas[0][2]+"_only")
        out.loc[out.index[idx],output_col]=states;out.loc[out.index[idx],output_col+"_variance"]=vars;out.loc[out.index[idx],output_col+"_status"]=sts;summ.append({**base,"group_id":gid,"n_rows":len(idx),"finite_primary":int(np.isfinite(p).sum()),"finite_secondary":int(np.isfinite(s).sum()),"fused_rows":sts.count("fused"),"primary_only_rows":sts.count("primary_only"),"secondary_only_rows":sts.count("secondary_only"),"missing_rows":sts.count("missing"),"status":"kalman_respiration_fusion_complete" if any(v!="missing" for v in sts) else "kalman_respiration_fusion_failed"})
    sd=pd.DataFrame(summ);good=sd.status.eq("kalman_respiration_fusion_complete");st="kalman_respiration_fusion_complete" if good.all() else ("kalman_respiration_fusion_partial" if good.any() else "kalman_respiration_fusion_failed");out.attrs["kalman_respiration_overview"]={"status":st,"input_rows":len(df),"group_count":len(sd)};out.attrs["kalman_respiration_summary"]=sd.to_dict("records");out.attrs["class"]=["gazepoint_respiration_kalman_fused","data.frame"];return out

def flag_gazepoint_mad_artifacts(dat, eda_col="GSR_US", time_col=None, group_cols=None, mad_multiplier=8, flatline_tolerance=1e-6, flatline_min_run=5, wall_abs_change=None, output_prefix="mad"):
    df=_df(dat);out=df.copy();art=np.zeros(len(df),bool);typ=np.array(["none"]*len(df),object)
    for gid,idx,_ in _groups(df,group_cols):
        x=pd.to_numeric(df.iloc[idx][eda_col],errors="coerce").to_numpy(float);d=np.r_[np.nan,np.diff(x)];f=d[np.isfinite(d)];med=np.median(f) if len(f) else 0;mad=1.4826*np.median(np.abs(f-med)) if len(f) else 0;needle=np.isfinite(d)&(np.abs(d-med)>mad_multiplier*mad) if mad>0 else np.zeros(len(x),bool);flat,_=_run_flags(np.r_[False,np.abs(np.diff(x))<=flatline_tolerance],flatline_min_run);wall=np.isfinite(d)&(np.abs(d)>wall_abs_change) if wall_abs_change is not None else np.zeros(len(x),bool);step=needle.copy(); local=needle|flat|wall|step
        for j,pos in enumerate(idx):
            if not local[j]:continue
            kinds=[]
            if flat[j]:kinds.append("flatline")
            if needle[j]:kinds.append("needle")
            if step[j]:kinds.append("step")
            if wall[j]:kinds.append("wall")
            art[pos]=True;typ[pos]=kinds[0] if len(kinds)==1 else "multiple"
    out[output_prefix+"_artifact"]=art;out[output_prefix+"_artifact_type"]=typ;out.attrs["mad_artifact_overview"]={"artifact_rows":int(art.sum()),"status":"mad_artifacts_flagged"};out.attrs["class"]=["gazepoint_mad_artifact_flags","data.frame"];return out

def _psi(ref,cur,bins=10,eps=1e-6):
    ref=np.asarray(ref,float);cur=np.asarray(cur,float);ref=ref[np.isfinite(ref)];cur=cur[np.isfinite(cur)]
    if len(ref)<2 or len(cur)<2:return np.nan
    edges=np.unique(np.quantile(ref,np.linspace(0,1,bins+1)));edges[0]=-np.inf;edges[-1]=np.inf
    if len(edges)<3:return 0.
    a=np.histogram(ref,bins=edges)[0]/len(ref);b=np.histogram(cur,bins=edges)[0]/len(cur);a=np.maximum(a,eps);b=np.maximum(b,eps);return float(np.sum((b-a)*np.log(b/a)))
def audit_gazepoint_distributional_drift(dat, signal_cols, session_col="session", participant_col=None, reference_session=None, bins=10, psi_warn=.10, psi_fail=.25):
    df=_df(dat);signals=_cols(signal_cols);rows=[];sessions=list(pd.unique(df[session_col]));ref=reference_session if reference_session is not None else sessions[0]
    parts=[(None,df)] if participant_col is None else list(df.groupby(participant_col,sort=False,dropna=False))
    for pid,pdta in parts:
        for c in signals:
            rv=pd.to_numeric(pdta.loc[pdta[session_col]==ref,c],errors="coerce").to_numpy(float)
            for ses in sessions:
                if str(ses)==str(ref):continue
                cv=pd.to_numeric(pdta.loc[pdta[session_col]==ses,c],errors="coerce").to_numpy(float);psi=_psi(rv,cv,bins);ks=stats.ks_2samp(rv[np.isfinite(rv)],cv[np.isfinite(cv)]) if np.isfinite(rv).any() and np.isfinite(cv).any() else None;status="fail" if np.isfinite(psi) and psi>=psi_fail else ("warn" if np.isfinite(psi) and psi>=psi_warn else "pass");rows.append({"participant":pid,"signal":c,"reference_session":str(ref),"comparison_session":str(ses),"psi":psi,"ks_statistic":ks.statistic if ks else np.nan,"ks_p_value":ks.pvalue if ks else np.nan,"status":status})
    return {"overview":pd.DataFrame([{"comparison_rows":len(rows),"status":"distributional_drift_audited"}]),"drift_summary":pd.DataFrame(rows),"settings":{},"class":["gazepoint_distributional_drift","list"]}

# ---- change/recovery --------------------------------------------------------
def detect_gazepoint_doubly_stochastic_changepoints(dat, signal_col, time_col="CNT", group_cols=None, window_seconds=10, step_seconds=2, threshold_mad_multiplier=6, min_distance_s=5):
    df=_df(dat);rows=[];changes=[]
    for gid,idx,base in _groups(df,group_cols):
        t=pd.to_numeric(df.iloc[idx][time_col],errors="coerce").to_numpy(float);x=pd.to_numeric(df.iloc[idx][signal_col],errors="coerce").to_numpy(float);fs=_sampling(t);wn=max(2,int(round(window_seconds*fs))) if np.isfinite(fs) else int(window_seconds);step=max(1,int(round(step_seconds*fs))) if np.isfinite(fs) else int(step_seconds);scores=[]
        for center in range(wn,len(x)-wn+1,step):
            left=x[center-wn:center];right=x[center:center+wn];sc=abs(np.nanmean(right)-np.nanmean(left));tm=t[center];scores.append((center,tm,sc));rows.append({**base,"group_id":gid,"center_index":center+1,"time":tm,"change_score":sc})
        vals=np.array([s[2] for s in scores]);med=np.nanmedian(vals) if len(vals) else np.nan;mad=1.4826*np.nanmedian(np.abs(vals-med)) if len(vals) else np.nan;thr=med+threshold_mad_multiplier*mad if np.isfinite(mad) else np.inf;last=-np.inf
        for center,tm,sc in sorted(scores,key=lambda z:z[2],reverse=True):
            if sc>thr and all(abs(tm-c['time'])>=min_distance_s for c in changes if c.get('group_id')==gid):changes.append({**base,"group_id":gid,"time":tm,"change_score":sc,"threshold":thr})
    return {"overview":pd.DataFrame([{"score_rows":len(rows),"changepoints":len(changes),"status":"changepoint_scoring_complete"}]),"score_table":pd.DataFrame(rows),"changepoints":pd.DataFrame(changes),"settings":{},"class":["gazepoint_doubly_stochastic_changepoints","list"]}

def extract_gazepoint_scr_recovery_times(dat, eda_col="GSR_US", time_col="CNT", event_onset_col=None, group_cols=None, pre_onset_baseline_s=2, peak_window_s=5, recovery_window_s=20):
    df=_df(dat);rows=[]
    for gid,idx,base in _groups(df,group_cols):
        g=df.iloc[idx];t=pd.to_numeric(g[time_col],errors="coerce").to_numpy(float);x=pd.to_numeric(g[eda_col],errors="coerce").to_numpy(float);onsets=[]
        if event_onset_col and event_onset_col in g:onsets=pd.to_numeric(g[event_onset_col],errors="coerce").dropna().unique().tolist()
        for onset in onsets:
            bm=(t>=onset-pre_onset_baseline_s)&(t<onset);pm=(t>=onset)&(t<=onset+peak_window_s);baseline=np.nanmedian(x[bm]) if bm.any() else np.nan
            if not pm.any():continue
            loc=np.flatnonzero(pm)[np.nanargmax(x[pm])];pv=x[loc];amp=pv-baseline;target2=baseline+.5*amp;after=np.flatnonzero((t>t[loc])&(t<=onset+recovery_window_s));rec2=next((t[j]-t[loc] for j in after if np.isfinite(x[j]) and x[j]<=target2),np.nan)
            # exponential time constant from positive residual after peak
            yy=x[after]-baseline if len(after) else np.array([]);tt=t[after]-t[loc] if len(after) else np.array([]);ok=(yy>0)&np.isfinite(yy)&np.isfinite(tt);tc=np.nan
            if ok.sum()>=2:
                slope=np.polyfit(tt[ok],np.log(yy[ok]),1)[0];tc=-1/slope if slope<0 else np.nan
            rows.append({**base,"group_id":gid,"event_onset":onset,"peak_time":t[loc],"peak_amplitude":amp,"rec_t2":rec2,"rec_tc":tc,"status":"recovery_estimated"})
    return {"overview":pd.DataFrame([{"event_rows":len(rows),"status":"scr_recovery_times_extracted" if rows else "no_events"}]),"recovery_table":pd.DataFrame(rows),"settings":{},"class":["gazepoint_scr_recovery_times","list"]}
