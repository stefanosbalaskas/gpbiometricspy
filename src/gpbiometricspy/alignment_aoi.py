from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ._helpers import as_list, guess_col, time_seconds, trapz


def _check_df(data, arg="data"):
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"`{arg}` must be a data frame.")
    if data.empty:
        raise ValueError(f"`{arg}` has no rows.")
    return data


def _event_table(events, event_time_col=None, event_id_col=None):
    if isinstance(events, (list, tuple, np.ndarray, pd.Series)) and not isinstance(events, pd.DataFrame):
        arr = np.asarray(events)
        if np.issubdtype(arr.dtype, np.number):
            return pd.DataFrame({"event_id": [f"E{i+1}" for i in range(len(arr))], "event_time_s": time_seconds(arr)})
    ev = _check_df(events, "events").copy()
    etc = event_time_col or guess_col(ev, ["event_time_s","event_time","onset","onset_s","time_s","time","timestamp","MSTIMER"], "event time", True)
    eid = event_id_col or guess_col(ev, ["event_id","event","marker","trial","trial_id","condition"], "event id", False)
    ev["event_time_s"] = time_seconds(ev[etc])
    ev["event_id"] = ev[eid].astype(str) if eid and eid in ev.columns else [f"E{i+1}" for i in range(len(ev))]
    return ev


def align_gazepoint_streams_by_events(reference, target, reference_events, target_events,
                                      reference_time_col=None, target_time_col=None,
                                      reference_event_time_col=None, target_event_time_col=None,
                                      event_id_col=None, method="linear", include_streams=True):
    ref = _check_df(reference, "reference").copy(); tar = _check_df(target, "target").copy()
    if method not in {"linear", "offset"}: raise ValueError("`method` must be 'linear' or 'offset'.")
    rtc = reference_time_col or guess_col(ref,["time_s","time","timestamp","event_time","TIME","MSTIMER","CNT"],"time",True)
    ttc = target_time_col or guess_col(tar,["time_s","time","timestamp","event_time","TIME","MSTIMER","CNT"],"time",True)
    re = _event_table(reference_events, reference_event_time_col, event_id_col)
    te = _event_table(target_events, target_event_time_col, event_id_col)
    if event_id_col and event_id_col in re.columns and event_id_col in te.columns:
        matched = re.merge(te, on=event_id_col, suffixes=("_reference","_target"))
        rt = pd.to_numeric(matched["event_time_s_reference"],errors="coerce").to_numpy(float)
        tt = pd.to_numeric(matched["event_time_s_target"],errors="coerce").to_numpy(float)
    else:
        n=min(len(re),len(te))
        if n<1: raise ValueError("No event pairs are available for alignment.")
        rt=re.event_time_s.iloc[:n].to_numpy(float); tt=te.event_time_s.iloc[:n].to_numpy(float)
        matched=pd.DataFrame({"event_id":np.arange(1,n+1),"reference_event_time_s":rt,"target_event_time_s":tt})
    ok=np.isfinite(rt)&np.isfinite(tt); rt=rt[ok]; tt=tt[ok]; matched=matched.loc[ok].reset_index(drop=True)
    if not len(rt): raise ValueError("No finite event pairs are available for alignment.")
    actual_method=method
    if method=="linear" and len(rt)>=2 and len(np.unique(rt))>=2:
        slope, intercept = np.polyfit(rt,tt,1); fitted=intercept+slope*rt
    else:
        intercept=float(np.median(tt-rt)); slope=1.0; fitted=rt+intercept; actual_method="offset"
    clock=time_seconds(tar[ttc]); aligned=(clock-intercept)/slope
    ta=tar.copy(); ta["target_time_original_s"]=clock; ta["target_time_aligned_s"]=aligned
    table=pd.DataFrame({"event_pair":np.arange(1,len(rt)+1),"reference_event_time_s":rt,"target_event_time_s":tt,
                        "fitted_target_event_time_s":fitted,"residual_s":tt-fitted,"aligned_target_event_time_s":(tt-intercept)/slope})
    resid=table.residual_s.to_numpy(float)
    diag=pd.DataFrame([{"n_event_pairs":len(rt),"method":actual_method,"intercept_s":float(intercept),"slope_target_per_reference":float(slope),
                        "median_raw_lag_s":float(np.median(tt-rt)),"residual_sd_s":float(np.std(resid,ddof=1)) if len(resid)>1 else np.nan,
                        "max_abs_residual_s":float(np.max(np.abs(resid)))}])
    out={"diagnostics":diag,"alignment_table":table,"class":["gazepoint_stream_alignment","list"]}
    if include_streams: out.update({"reference":ref,"target_aligned":ta})
    return out


def _aoi_from_rectangles(df,x_col,y_col,defs):
    required=["AOI","xmin","xmax","ymin","ymax"]
    missing=[c for c in required if c not in defs.columns]
    if missing: raise ValueError("`aoi_definitions` must contain columns: " + ", ".join(required))
    x=pd.to_numeric(df[x_col],errors="coerce").to_numpy(float); y=pd.to_numeric(df[y_col],errors="coerce").to_numpy(float)
    out=np.full(len(df),None,dtype=object)
    for _,r in defs.iterrows():
        hit=pd.isna(out)&np.isfinite(x)&np.isfinite(y)&(x>=r.xmin)&(x<=r.xmax)&(y>=r.ymin)&(y<=r.ymax)
        out[hit]=str(r.AOI)
    return out


def build_gazepoint_aoi_timecourse(data,time_col=None,aoi_col=None,x_col=None,y_col=None,aoi_definitions=None,group_cols=None,bin_width_s=.10,valid_col=None,include_empty=True):
    df=_check_df(data).copy(); tc=time_col or guess_col(df,["time_s","time","timestamp","event_time","TIME","MSTIMER","CNT"],"time",True)
    groups=as_list(group_cols); missing=[c for c in groups if c not in df.columns]
    if missing: raise ValueError("Missing grouping columns: "+", ".join(missing))
    if not isinstance(bin_width_s,(int,float,np.number)) or not np.isfinite(bin_width_s) or bin_width_s<=0: raise ValueError("`bin_width_s` must be positive.")
    if aoi_col is None and aoi_definitions is None: aoi_col=guess_col(df,["AOI","aoi","AOI_NAME","aoi_name","area_of_interest"],"AOI",True)
    if aoi_definitions is not None:
        xc=x_col or guess_col(df,["gaze_x","x","BPOGX","FPOGX","GPOGX"],"x",True); yc=y_col or guess_col(df,["gaze_y","y","BPOGY","FPOGY","GPOGY"],"y",True)
        df[".gp_aoi_label"]=_aoi_from_rectangles(df,xc,yc,aoi_definitions); aoi_col=".gp_aoi_label"
    if aoi_col not in df.columns: raise ValueError("`aoi_col` was not found in `data`.")
    if groups: grouped=list(df.groupby(groups,sort=False,dropna=False))
    else: grouped=[("all",df)]
    rows=[]
    for key,z in grouped:
        t=time_seconds(z[tc]); finite=np.isfinite(t)
        if not finite.any(): continue
        rel=t-np.nanmin(t[finite]); bins=np.floor(rel/bin_width_s)*bin_width_s
        valid=np.ones(len(z),bool)
        if valid_col and valid_col in z.columns:
            if pd.api.types.is_bool_dtype(z[valid_col]): valid=z[valid_col].fillna(False).to_numpy(bool)
            else:
                v=pd.to_numeric(z[valid_col],errors="coerce").to_numpy(float); valid=np.isfinite(v)&(v>0)
        aoi=z[aoi_col].astype("string"); aoi=aoi.where(aoi.notna()&(aoi.str.len()>0),pd.NA)
        aois=sorted(aoi.dropna().unique().tolist()); ubins=sorted(np.unique(bins[np.isfinite(bins)]).tolist())
        for bb in ubins:
            inbin=np.isfinite(bins)&(bins==bb); binvalid=inbin&valid; denom=int(binvalid.sum())
            for aa in aois:
                aoi_cmp=aoi.fillna("<NA>").astype(str).to_numpy()
                hit=binvalid&(aoi_cmp==aa)
                if not include_empty and not hit.any(): continue
                row={"group":str(key),"bin_start_s":bb,"bin_end_s":bb+bin_width_s,"bin_center_s":bb+bin_width_s/2,"AOI":aa,
                     "n_bin_samples":int(inbin.sum()),"valid_bin_samples":denom,"aoi_samples":int(hit.sum()),"aoi_prop":int(hit.sum())/denom if denom else np.nan}
                if groups:
                    row.pop("group",None)
                    first=z.iloc[0]
                    row={**{c:first[c] for c in groups},**row}
                rows.append(row)
    return pd.DataFrame(rows)


def _signal_summary(rel,value,baseline_window_s,summary_window_s):
    rel=np.asarray(rel,float); value=np.asarray(value,float); full=np.isfinite(rel)
    b=full&(rel>=baseline_window_s[0])&(rel<baseline_window_s[1]); s=full&(rel>=summary_window_s[0])&(rel<=summary_window_s[1]); bv=value[b]; sv=value[s]; st=rel[s]; fs=np.isfinite(sv)
    peak=float(np.nanmax(sv)) if fs.any() else np.nan; mn=float(np.nanmin(sv)) if fs.any() else np.nan
    if fs.any():
        # R which.max on vector with possible NA is effectively first finite maximum after coercion pattern.
        valid_idx=np.flatnonzero(fs); loc=valid_idx[int(np.argmax(sv[fs]))]; plat=float(st[loc])
    else: plat=np.nan
    return {"n_samples":len(value),"n_summary_samples":len(sv),"baseline_mean":float(np.nanmean(bv)) if np.isfinite(bv).any() else np.nan,
            "summary_mean":float(np.nanmean(sv)) if fs.any() else np.nan,"peak_value":peak,"min_value":mn,"peak_latency_s":plat,
            "auc":trapz(st,sv),"missing_prop":float(np.mean(~np.isfinite(value))) if len(value) else np.nan}


def summarize_gazepoint_eventlocked_multimodal(data,events,time_col=None,event_time_col=None,event_id_col=None,group_cols=None,signal_cols=None,pre_s=1,post_s=3,baseline_window_s=(-1,0),summary_window_s=(0,3)):
    ev=_event_table(events,event_time_col,event_id_col)
    streams=data if isinstance(data,dict) and all(isinstance(v,pd.DataFrame) for v in data.values()) else {"data":data}
    samples=[]; summaries=[]
    groups=as_list(group_cols)
    for name,stream in streams.items():
        z=_check_df(stream,f"data${name}").copy(); tc = time_col if (time_col is not None and time_col in z.columns) else None
        if tc is None: tc=guess_col(z,["time_s","time","timestamp","event_time","TIME","MSTIMER","CNT"],"time",True)
        t=time_seconds(z[tc])
        sc=signal_cols.get(name) if isinstance(signal_cols,dict) else signal_cols
        if sc is None: sc=[c for c in z.columns if pd.api.types.is_numeric_dtype(z[c]) and c not in [tc,*groups]]
        sc=[c for c in as_list(sc) if c in z.columns]
        for _,e in ev.iterrows():
            idx=np.arange(len(z))
            for c in groups:
                if c in z.columns and c in ev.columns: idx=idx[z.loc[idx,c].astype(str).to_numpy()==str(e[c])]
            if not len(idx): continue
            relall=t[idx]-float(e.event_time_s); win=np.isfinite(relall)&(relall>=-pre_s)&(relall<=post_s)
            if not win.any(): continue
            pos=idx[win]; rel=relall[win]
            extras={c:e[c] for c in ev.columns if c not in {"event_id","event_time_s"}}
            for sig in sc:
                val=pd.to_numeric(z.iloc[pos][sig],errors="coerce").to_numpy(float)
                sr=pd.DataFrame({"event_id":str(e.event_id),"modality":name,"signal":sig,"sample_index":pos+1,"time_s":t[pos],"relative_time_s":rel,"value":val})
                for c,v in extras.items(): sr[c]=v
                samples.append(sr)
                row={"event_id":str(e.event_id),"event_time_s":float(e.event_time_s),"modality":name,"signal":sig,**_signal_summary(rel,val,baseline_window_s,summary_window_s),**extras}
                summaries.append(row)
    return {"samples":pd.concat(samples,ignore_index=True) if samples else pd.DataFrame(),"summary":pd.DataFrame(summaries),"events":ev,
            "settings":{"pre_s":pre_s,"post_s":post_s,"baseline_window_s":baseline_window_s,"summary_window_s":summary_window_s},"class":["gazepoint_eventlocked_multimodal","list"]}


def create_gazepoint_quality_dashboard(data=None,audit=None,missingness=None,alignment=None,eventlocked=None,title="Gazepoint quality dashboard",output_dir=None):
    # In the full port, data-only mode will delegate to the corresponding audit/missingness functions.
    # This reconstructed family accepts already-computed objects exactly as the R contract does.
    if not isinstance(title,str) or not title: raise ValueError("`title` must be a non-empty string.")
    ov={"title":title,"created":str(datetime.now()),"has_audit":audit is not None,"has_missingness":missingness is not None,"has_alignment":alignment is not None,"has_eventlocked":eventlocked is not None}
    if isinstance(audit,dict) and audit.get("dimensions") is not None:
        dims=audit["dimensions"]
        if isinstance(dims,pd.DataFrame): dims=dims.iloc[0].to_dict()
        ov.update({"n_rows":dims.get("n_rows",np.nan),"n_cols":dims.get("n_cols",np.nan),"n_warnings":len(audit.get("warnings",[])),
                   "n_duplicate_rows":(audit.get("duplicate_rows",{}).get("n_duplicate_rows",np.nan) if isinstance(audit.get("duplicate_rows"),dict) else np.nan)})
    else: ov.update({"n_rows":np.nan,"n_cols":np.nan,"n_warnings":np.nan,"n_duplicate_rows":np.nan})
    if isinstance(missingness,pd.DataFrame) and "missing_prop" in missingness.columns and len(missingness):
        ov["max_missing_prop"]=float(np.nanmax(missingness.missing_prop)); ov["mean_missing_prop"]=float(np.nanmean(missingness.missing_prop))
    else: ov.update({"max_missing_prop":np.nan,"mean_missing_prop":np.nan})
    if isinstance(alignment,dict) and isinstance(alignment.get("diagnostics"),pd.DataFrame) and len(alignment["diagnostics"]):
        d=alignment["diagnostics"].iloc[0]; ov["n_alignment_pairs"]=d.n_event_pairs; ov["alignment_residual_sd_s"]=d.residual_sd_s
    else: ov.update({"n_alignment_pairs":np.nan,"alignment_residual_sd_s":np.nan})
    ov["n_eventlocked_rows"]=len(eventlocked["summary"]) if isinstance(eventlocked,dict) and isinstance(eventlocked.get("summary"),pd.DataFrame) else np.nan
    overview=pd.DataFrame([ov]); out={"overview":overview,"audit":audit,"missingness":missingness,"alignment":alignment,"eventlocked":eventlocked,"class":["gazepoint_quality_dashboard","list"]}
    if output_dir is not None:
        p=Path(output_dir); p.mkdir(parents=True,exist_ok=True); overview.to_csv(p/"quality_dashboard_overview.csv",index=False)
        if isinstance(missingness,pd.DataFrame): missingness.to_csv(p/"quality_dashboard_missingness.csv",index=False)
        if isinstance(audit,dict):
            if isinstance(audit.get("modalities"),pd.DataFrame): audit["modalities"].to_csv(p/"quality_dashboard_modalities.csv",index=False)
            (p/"quality_dashboard_warnings.txt").write_text("\n".join(audit.get("warnings",[])) if audit.get("warnings") else "No audit warnings.",encoding="utf-8")
        if isinstance(alignment,dict) and isinstance(alignment.get("diagnostics"),pd.DataFrame): alignment["diagnostics"].to_csv(p/"quality_dashboard_alignment.csv",index=False)
        if isinstance(eventlocked,dict) and isinstance(eventlocked.get("summary"),pd.DataFrame): eventlocked["summary"].to_csv(p/"quality_dashboard_eventlocked_summary.csv",index=False)
        out["output_dir"]=p.resolve().as_posix()
    return out
