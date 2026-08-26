from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from matplotlib.figure import Figure


def _df(data):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    return data


def _cols(data, cols, label="columns"):
    vals=[] if cols is None else ([cols] if isinstance(cols,str) else list(cols))
    missing=[c for c in vals if c not in data.columns]
    if missing: raise ValueError(f"Missing `{label}`: " + ", ".join(missing))
    return vals


def _group_indices(data, cols):
    cols=_cols(data,cols,"group_cols")
    if not cols: return [("all_rows",np.arange(len(data),dtype=int),{})]
    keys=data[cols].astype(object).where(data[cols].notna(),"<NA>").astype(str).agg(" | ".join,axis=1)
    out=[]
    for key in pd.unique(keys):
        idx=np.flatnonzero(keys.to_numpy()==key); out.append((str(key),idx,{c:data.iloc[idx[0]][c] for c in cols}))
    return out

# Plot contracts ----------------------------------------------------------------
def standardise_gazepoint_plot_contract(plot, plot_data=None, settings=None, interpretation_notes=None, plot_type=None):
    if not isinstance(plot, Figure): raise TypeError("`plot` must be a matplotlib Figure object.")
    if plot_data is not None and not isinstance(plot_data,pd.DataFrame): raise TypeError("`plot_data` must be NULL or a data frame.")
    settings={} if settings is None else settings
    if not isinstance(settings,dict): raise TypeError("`settings` must be a dict/list-like settings object.")
    if interpretation_notes is not None and not isinstance(interpretation_notes,(str,list,tuple)): raise TypeError("`interpretation_notes` must be NULL or character text.")
    if plot_type is not None and not isinstance(plot_type,str): raise TypeError("`plot_type` must be NULL or a single character value.")
    if plot_data is None: plot_data=getattr(plot,"_gazepoint_plot_data",None)
    if not settings: settings=getattr(plot,"_gazepoint_settings",{})
    if interpretation_notes is None: interpretation_notes=getattr(plot,"_gazepoint_interpretation_notes",settings.get("interpretation_notes",[]))
    if plot_type is None: plot_type=settings.get("plot_type",getattr(plot,"_gazepoint_plot_type",None))
    plot._gazepoint_plot_data=plot_data
    plot._gazepoint_settings=settings
    plot._gazepoint_interpretation_notes=interpretation_notes if interpretation_notes is not None else []
    plot._gazepoint_plot_type=plot_type
    plot._gazepoint_plot_contract=True
    return plot


def check_gazepoint_plot_contract(plot, require_plot_data=True, require_settings=True):
    if not isinstance(require_plot_data,(bool,np.bool_)): raise TypeError("`require_plot_data` must be TRUE or FALSE.")
    if not isinstance(require_settings,(bool,np.bool_)): raise TypeError("`require_settings` must be TRUE or FALSE.")
    isplot=isinstance(plot,Figure); gp=bool(getattr(plot,"_gazepoint_plot_contract",False)) if isplot else False
    pdta=getattr(plot,"_gazepoint_plot_data",None); sett=getattr(plot,"_gazepoint_settings",None); notes=getattr(plot,"_gazepoint_interpretation_notes",None); ptype=getattr(plot,"_gazepoint_plot_type",None)
    hasd=isinstance(pdta,pd.DataFrame); hass=isinstance(sett,dict); hasn=isinstance(notes,(str,list,tuple)); hast=isinstance(ptype,str) and bool(ptype)
    checks=pd.DataFrame({"check":["is_ggplot","is_gazepoint_plot","has_plot_data","has_settings","has_interpretation_notes","has_plot_type"],"passed":[isplot,gp,hasd,hass,hasn,hast],"required":[True,False,require_plot_data,require_settings,False,False]})
    fail=bool((checks.required & ~checks.passed).any()); status="fail_plot_contract" if fail else ("warn_partial_plot_contract" if not gp or not hasn or not hast else "pass_plot_contract")
    ov=pd.DataFrame([{"is_ggplot":isplot,"is_gazepoint_plot":gp,"has_plot_data":hasd,"plot_data_rows":len(pdta) if hasd else np.nan,"has_settings":hass,"has_interpretation_notes":hasn,"has_plot_type":hast,"status":status}])
    return {"overview":ov,"checks":checks,"plot_data":pdta.copy() if hasd else pd.DataFrame(),"settings":dict(sett) if hass else {}}


def get_gazepoint_plot_data(plot):
    x=getattr(plot,"_gazepoint_plot_data",None)
    if not isinstance(x,pd.DataFrame): raise ValueError("No `plot_data` data frame is stored on this plot object.")
    return x


def get_gazepoint_plot_settings(plot):
    x=getattr(plot,"_gazepoint_settings",None)
    if not isinstance(x,dict): raise ValueError("No `settings` list is stored on this plot object.")
    return x


def standardize_gazepoint_plot_contracts(plot, plot_data=None, settings=None, interpretation_notes=None, plot_type=None):
    if isinstance(plot,Figure): return standardise_gazepoint_plot_contract(plot,plot_data,{} if settings is None else settings,interpretation_notes,plot_type)
    if not isinstance(plot,(list,tuple,dict)): raise TypeError("`plot` must be a matplotlib Figure object or a list of plot objects.")
    names=list(plot.keys()) if isinstance(plot,dict) else None; arr=list(plot.values()) if isinstance(plot,dict) else list(plot); n=len(arr)
    if not n:return {} if names is not None else []
    def pick(v,i,kind):
        if kind=="data" and isinstance(v,list): return v[i] if len(v)==n else v
        if kind=="settings" and isinstance(v,list) and len(v)==n and all(isinstance(z,dict) for z in v): return v[i]
        if kind in {"notes","type"} and isinstance(v,(list,tuple)) and len(v)==n:return v[i]
        return v
    out=[standardise_gazepoint_plot_contract(p,pick(plot_data,i,"data"),pick(settings,i,"settings") or {},pick(interpretation_notes,i,"notes"),pick(plot_type,i,"type")) for i,p in enumerate(arr)]
    return dict(zip(names,out)) if names is not None else out

# Within-unit standardisation ---------------------------------------------------
def standardize_gazepoint_biometrics_within_unit(data, signal_cols=None, unit_cols=None, reference_col=None, reference_value=True,
                                                   suffix="_z_within", center=True, scale=True, min_valid=2, zero_sd_action="NA", overwrite=False):
    data=_df(data); zero_sd_action=str(zero_sd_action)
    if zero_sd_action not in {"NA","zero"}: raise ValueError("`zero_sd_action` must be 'NA' or 'zero'.")
    if not suffix or not isinstance(suffix,str): raise ValueError("`suffix` must be a non-empty character string.")
    if min_valid<1: raise ValueError("`min_valid` must be a positive number.")
    if signal_cols is None:
        candidates=["GSR_US","GSR_US_PHASIC","GSR_US_TONIC","GSR","EDA","HR","HRP","IBI","DIAL"]
        signal_cols=[c for c in candidates if c in data and pd.api.types.is_numeric_dtype(data[c])]
        if not signal_cols: raise ValueError("No common numeric biometric signal columns were detected. Supply `signal_cols` explicitly.")
    signal_cols=_cols(data,signal_cols,"signal_cols")
    for c in signal_cols:
        if not pd.api.types.is_numeric_dtype(data[c]): raise TypeError(f"The following `signal_cols` are not numeric: {c}")
    if unit_cols is None:
        cand=["source_participant","participant","participant_id","subject","subject_id","USER_FILE","source_file","session","session_id"]
        unit_cols=[c for c in cand if c in data][:1]
    unit_cols=_cols(data,unit_cols,"unit_cols")
    if reference_col is not None and reference_col not in data: raise ValueError(f"Column `{reference_col}` was not found in `data`.")
    output=[c+suffix for c in signal_cols]
    if not overwrite and any(c in data for c in output): raise ValueError("The following output columns already exist. Use `overwrite = TRUE` to replace them.")
    out=data.copy(); [out.__setitem__(c,np.nan) for c in output]; params=[]; groups=_group_indices(data,unit_cols)
    for gid,idx,base in groups:
        refidx=idx
        if reference_col is not None:
            vals=data.iloc[idx][reference_col].to_numpy(); refidx=idx[pd.notna(vals)&(vals==reference_value)]
        for sig,oc in zip(signal_cols,output):
            ref=pd.to_numeric(data.iloc[refidx][sig],errors="coerce").to_numpy(float); good=ref[np.isfinite(ref)]; status="standardized"; mu=sd=np.nan
            if len(good)<int(min_valid): status="insufficient_reference_rows"; transformed=np.full(len(idx),np.nan)
            else:
                mu=float(np.mean(good)); sd=float(np.std(good,ddof=1)) if len(good)>1 else np.nan; transformed=pd.to_numeric(data.iloc[idx][sig],errors="coerce").to_numpy(float)
                if center: transformed=transformed-mu
                if scale:
                    if not np.isfinite(sd) or sd==0:
                        status="zero_or_missing_sd"; transformed=np.where(np.isfinite(transformed),0.0,np.nan) if zero_sd_action=="zero" else np.full(len(idx),np.nan)
                    else: transformed=transformed/sd
                transformed[~np.isfinite(transformed)]=np.nan
            out.iloc[idx,out.columns.get_loc(oc)]=transformed
            row=dict(base); row.update(unit_id=gid,signal_col=sig,output_col=oc,n_rows=len(idx),n_reference_rows=len(refidx),n_reference_finite=len(good),reference_mean=mu,reference_sd=sd,center=center,scale=scale,status=status); params.append(row)
    par=pd.DataFrame(params); ok=par.status.eq("standardized"); st="within_unit_standardization_complete" if ok.all() else ("within_unit_standardization_partial" if ok.any() else "within_unit_standardization_failed")
    summary=pd.DataFrame([{"input_rows":len(data),"signal_count":len(signal_cols),"output_count":len(output),"unit_count":len(groups),"parameter_rows":len(par),"standardized_rows":int(ok.sum()),"problem_rows":int((~ok).sum()),"center":center,"scale":scale,"reference_col":reference_col if reference_col is not None else np.nan,"suffix":suffix,"status":st,"interpretation":"Within-unit standardization rescales biometric signals relative to each unit's own reference distribution. It supports within-person comparison but removes between-unit level and scale differences. It does not infer emotion, valence, stress, trust, preference, cognition, or diagnosis."}])
    out.attrs["standardization_summary"]=summary; out.attrs["standardization_parameters"]=par; out.attrs["settings"]={"signal_cols":signal_cols,"unit_cols":unit_cols,"reference_col":reference_col,"reference_value":reference_value,"suffix":suffix,"center":center,"scale":scale,"min_valid":int(min_valid),"zero_sd_action":zero_sd_action,"overwrite":overwrite}; return out


def standardise_gazepoint_biometrics_within_unit(*args,**kwargs): return standardize_gazepoint_biometrics_within_unit(*args,**kwargs)

# External interoperability -----------------------------------------------------
def _detect_ibi_unit(x,unit):
    if unit not in {"auto","ms","seconds"}: raise ValueError("`unit` must be auto, ms, or seconds.")
    if unit!="auto":return unit
    good=np.asarray(x,float);good=good[np.isfinite(good)&(good>0)]
    return "seconds" if len(good) and np.median(good)<10 else "ms"


def _safe_name(s): return re.sub(r"[^A-Za-z0-9._-]+","_",str(s)).strip("_") or "group"


def export_gazepoint_rhrv_input(data, ibi_col="IBI_clean_ms", group_cols=None, unit="auto", collapse_repeated_intervals=True,
                                 repeated_tolerance_ms=1e-8, min_ibi_ms=300, max_ibi_ms=2000, output_dir=None, prefix="gazepoint_rhrv"):
    if isinstance(data,dict) and "data" in data: data=data["data"]
    data=_df(data)
    if ibi_col not in data: raise ValueError("`ibi_col` was not found in `data`.")
    if group_cols is None:
        group_cols=[c for c in ["participant","participant_id","subject","subject_id","source_participant","session","session_id"] if c in data][:1]
    groups=_group_indices(data,group_cols); raw=pd.to_numeric(data[ibi_col],errors="coerce").to_numpy(float); detected=_detect_ibi_unit(raw,unit); rows=[]; summaries=[]; manifests=[]
    for gid,idx,base in groups:
        x=raw[idx]*(1000 if detected=="seconds" else 1); x=x[np.isfinite(x)&(x>=min_ibi_ms)&(x<=max_ibi_ms)]; ninput=len(x)
        if collapse_repeated_intervals and len(x): x=np.asarray([v for i,v in enumerate(x) if i==0 or abs(v-x[i-1])>repeated_tolerance_ms])
        bt=pd.DataFrame({"group_id":gid,"beat_index":np.arange(1,len(x)+1),"time_s":np.cumsum(x)/1000,"ibi_ms":x,"ibi_s":x/1000,"input_interval_rows":ninput,"output_interval_rows":len(x),"used_intervals_after_collapse":len(x)})
        for c in reversed(list(base)): bt.insert(0,c,base[c])
        if len(bt): rows.append(bt)
        summaries.append({**base,"group_id":gid,"input_interval_rows":ninput,"output_interval_rows":len(x),"mean_ibi_ms":float(np.mean(x)) if len(x) else np.nan})
    beat=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(columns=[*group_cols,"group_id","beat_index","time_s","ibi_ms","ibi_s","input_interval_rows","output_interval_rows","used_intervals_after_collapse"])
    if output_dir is not None:
        od=Path(output_dir);od.mkdir(parents=True,exist_ok=True)
        for gid,g in beat.groupby("group_id",sort=False):
            path=od/f"{prefix}_{_safe_name(gid)}_rhrv_input.csv"; g.to_csv(path,index=False); manifests.append({"group_id":gid,"file_path":str(path)})
    manifest=pd.DataFrame(manifests,columns=["group_id","file_path"]) if manifests else pd.DataFrame({"group_id":[g[0] for g in groups],"file_path":[np.nan]*len(groups)})
    status="fail_no_ibi_rows_for_export" if len(beat)==0 else ("rhrv_input_exported" if output_dir is not None else "rhrv_input_prepared")
    overview=pd.DataFrame([{"input_rows":len(data),"beat_rows":len(beat),"group_count":len(groups),"detected_ibi_unit":detected,"collapse_repeated_intervals":collapse_repeated_intervals,"files_written":int(manifest.file_path.notna().sum()),"status":status}])
    return {"overview":overview,"beat_table":beat,"group_summary":pd.DataFrame(summaries),"manifest":manifest,"settings":{"ibi_col":ibi_col,"group_cols":list(group_cols),"unit":unit,"detected_ibi_unit":detected,"collapse_repeated_intervals":collapse_repeated_intervals,"repeated_tolerance_ms":repeated_tolerance_ms,"min_ibi_ms":min_ibi_ms,"max_ibi_ms":max_ibi_ms,"output_dir":output_dir,"prefix":prefix}}


def prepare_gazepoint_rhrv_input(*args,**kwargs): return export_gazepoint_rhrv_input(*args,**kwargs)


def prepare_gazepoint_neurokit_eda_input(data, eda_col="GSR_US", time_col=None, group_cols=None, sampling_rate=None, output_dir=None, prefix="gazepoint_neurokit_eda"):
    data=_df(data)
    if eda_col not in data:raise ValueError("`eda_col` was not found in `data`.")
    if time_col is not None and time_col not in data:raise ValueError("`time_col` was not found in `data`.")
    if group_cols is None:group_cols=[c for c in ["participant","participant_id","subject","subject_id"] if c in data][:1]
    groups=_group_indices(data,group_cols); tables=[]; summaries=[]; manifest=[]
    for gid,idx,base in groups:
        eda=pd.to_numeric(data.iloc[idx][eda_col],errors="coerce").to_numpy(float); si=np.arange(1,len(idx)+1)
        raw=pd.to_numeric(data.iloc[idx][time_col],errors="coerce").to_numpy(float) if time_col else si-1
        if sampling_rate is not None: ts=(si-1)/float(sampling_rate)
        elif time_col is not None:
            finite=raw[np.isfinite(raw)]; dt=np.diff(finite);dt=dt[dt>0]; factor=1000 if len(dt) and np.median(dt)>10 else 1; ts=(raw-raw[np.flatnonzero(np.isfinite(raw))[0]])/factor if np.any(np.isfinite(raw)) else np.full(len(raw),np.nan)
        else: ts=np.full(len(raw),np.nan)
        t=pd.DataFrame({"group_id":gid,"sample_index":si,"time_raw":raw,"time_s":ts,"eda":eda});
        for c in reversed(list(base)):t.insert(0,c,base[c])
        tables.append(t); summaries.append({**base,"group_id":gid,"n_rows":len(t),"finite_eda_rows":int(np.isfinite(eda).sum()),"status":"ready_for_neurokit_input" if np.isfinite(eda).any() else "no_finite_eda"})
    table=pd.concat(tables,ignore_index=True) if tables else pd.DataFrame()
    if output_dir is not None:
        od=Path(output_dir);od.mkdir(parents=True,exist_ok=True)
        for gid,g in table.groupby("group_id",sort=False):
            path=od/f"{prefix}_{_safe_name(gid)}_neurokit_eda_input.csv";g.to_csv(path,index=False);manifest.append({"group_id":gid,"file_path":str(path)})
    mf=pd.DataFrame(manifest,columns=["group_id","file_path"]) if manifest else pd.DataFrame({"group_id":[g[0] for g in groups],"file_path":[np.nan]*len(groups)})
    status="fail_no_eda_rows_for_export" if len(table)==0 else ("neurokit_eda_input_exported" if output_dir is not None else "neurokit_eda_input_prepared")
    return {"overview":pd.DataFrame([{"input_rows":len(data),"eda_rows":len(table),"group_count":len(groups),"eda_col":eda_col,"sampling_rate":sampling_rate if sampling_rate is not None else np.nan,"files_written":int(mf.file_path.notna().sum()),"status":status}]),"eda_table":table,"group_summary":pd.DataFrame(summaries),"manifest":mf,"settings":{"eda_col":eda_col,"time_col":time_col,"group_cols":list(group_cols),"sampling_rate":sampling_rate,"output_dir":output_dir,"prefix":prefix},"_class":"gazepoint_neurokit_eda_input"}


def run_gazepoint_neurokit_eda_crosscheck(data, eda_col="GSR_US", time_col=None, group_cols=None, sampling_rate=None, execute=False, python="python", output_dir=None, prefix="gazepoint_neurokit_crosscheck", keep_files=False):
    if not isinstance(execute,(bool,np.bool_)):raise TypeError("`execute` must be TRUE or FALSE.")
    prepared=data if isinstance(data,dict) and data.get("_class")=="gazepoint_neurokit_eda_input" else prepare_gazepoint_neurokit_eda_input(data,eda_col,time_col,group_cols,sampling_rate)
    if not execute:
        return {"overview":pd.DataFrame([{"status":"skipped_execute_false","executed":False,"input_rows":len(prepared["eda_table"])}]),"prepared_input":prepared,"results":pd.DataFrame(),"settings":{"execute":False,"sampling_rate":sampling_rate}}
    if importlib.util.find_spec("neurokit2") is None:
        return {"overview":pd.DataFrame([{"status":"neurokit2_not_available","executed":False,"input_rows":len(prepared["eda_table"])}]),"prepared_input":prepared,"results":pd.DataFrame(),"settings":{"execute":True,"sampling_rate":sampling_rate}}
    import neurokit2 as nk
    rows=[]
    for gid,g in prepared["eda_table"].groupby("group_id",sort=False):
        sr=float(sampling_rate or 1000/np.nanmedian(np.diff(g.time_s))*0.001 if len(g)>2 else 1000)
        try:
            sig,info=nk.eda_process(g.eda.to_numpy(float),sampling_rate=sr);rows.append({"group_id":gid,"n_scr_peaks":len(info.get("SCR_Peaks",[])),"status":"neurokit_crosscheck_complete"})
        except Exception as exc:rows.append({"group_id":gid,"n_scr_peaks":np.nan,"status":"neurokit_crosscheck_failed","error":str(exc)})
    return {"overview":pd.DataFrame([{"status":"neurokit_crosscheck_complete" if all(r["status"]=="neurokit_crosscheck_complete" for r in rows) else "neurokit_crosscheck_partial","executed":True,"input_rows":len(prepared["eda_table"])}]),"prepared_input":prepared,"results":pd.DataFrame(rows),"settings":{"execute":True,"sampling_rate":sampling_rate}}

# Lag/synchronisation -----------------------------------------------------------
def estimate_gazepoint_signal_lag(data, signal_x_col, signal_y_col, time_col=None, group_cols=None, max_lag=1000, lag_step=None, method="pearson", min_complete_pairs=20, use_first_difference=False):
    data=_df(data); _cols(data,[signal_x_col,signal_y_col]);
    if time_col is not None:_cols(data,[time_col])
    groups=_group_indices(data,group_cols); step=1 if lag_step is None else lag_step; lags=np.arange(-max_lag,max_lag+step/2,step); prof=[]; summ=[]
    for gid,idx,base in groups:
        x=pd.to_numeric(data.iloc[idx][signal_x_col],errors="coerce").to_numpy(float);y=pd.to_numeric(data.iloc[idx][signal_y_col],errors="coerce").to_numpy(float)
        if use_first_difference:x=np.diff(x);y=np.diff(y)
        vals=[]
        for lag in lags:
            k=int(round(lag/step)) if time_col is None else int(round(lag/step))
            if k>0:xx=x[:-k];yy=y[k:]
            elif k<0:xx=x[-k:];yy=y[:k]
            else:xx=x;yy=y
            good=np.isfinite(xx)&np.isfinite(yy);n=int(good.sum());corr=np.nan
            if n>=min_complete_pairs and np.std(xx[good])>0 and np.std(yy[good])>0:
                if method=="spearman":corr=float(pd.Series(xx[good]).corr(pd.Series(yy[good]),method="spearman"))
                else:corr=float(np.corrcoef(xx[good],yy[good])[0,1])
            prof.append({**base,"group_id":gid,"lag":float(lag),"correlation":corr,"complete_pairs":n});vals.append(corr)
        arr=np.asarray(vals,float)
        if np.any(np.isfinite(arr)):
            best=int(np.nanargmax(np.abs(arr)));summ.append({**base,"group_id":gid,"estimated_lag":float(lags[best]),"peak_correlation":float(arr[best]),"status":"estimated"})
        else:summ.append({**base,"group_id":gid,"estimated_lag":np.nan,"peak_correlation":np.nan,"status":"insufficient_data"})
    sb=pd.DataFrame(summ);ok=sb.status.eq("estimated");st="estimated" if ok.any() else "no_valid_estimates"
    return {"overview":pd.DataFrame([{"group_count":len(groups),"estimated_groups":int(ok.sum()),"status":st}]),"lag_by_group":sb,"lag_profile":pd.DataFrame(prof),"settings":{"signal_x_col":signal_x_col,"signal_y_col":signal_y_col,"time_col":time_col,"group_cols":[] if group_cols is None else list(group_cols) if not isinstance(group_cols,str) else [group_cols],"max_lag":max_lag,"lag_step":step,"method":method,"min_complete_pairs":min_complete_pairs,"use_first_difference":use_first_difference}}


def audit_gazepoint_biometric_sync_drift(data, time_col=None, group_cols=None, signal_pairs=None, signal_cols=None, reference_signal_col=None, max_lag=1000, lag_step=None, drift_tolerance=None, method="pearson", min_complete_pairs=20, use_first_difference=False, include_reset_segments=True):
    data=_df(data)
    if signal_pairs is None:
        sc=[] if signal_cols is None else ([signal_cols] if isinstance(signal_cols,str) else list(signal_cols))
        if reference_signal_col and reference_signal_col in sc: pairs=[(reference_signal_col,c) for c in sc if c!=reference_signal_col]
        elif len(sc)>=2:pairs=[(sc[0],c) for c in sc[1:]]
        else:pairs=[]
    elif isinstance(signal_pairs,pd.DataFrame):pairs=list(zip(signal_pairs.signal_x,signal_pairs.signal_y))
    else:pairs=[tuple(x) for x in signal_pairs]
    if not pairs:
        return {"overview":pd.DataFrame([{"status":"no_signal_pairs","signal_pair_count":0,"lag_estimate_rows":0}]),"checks":pd.DataFrame(),"time_reset_audit":pd.DataFrame(),"lag_by_group":pd.DataFrame(),"lag_profile":pd.DataFrame(),"drift_summary":pd.DataFrame(),"settings":{"signal_pairs":[]}}
    lags=[];profiles=[];drifts=[];tol=float(drift_tolerance if drift_tolerance is not None else max_lag*.25)
    for x,y in pairs:
        est=estimate_gazepoint_signal_lag(data,x,y,time_col,group_cols,max_lag,lag_step,method,min_complete_pairs,use_first_difference); a=est["lag_by_group"].copy();a["signal_x"]=x;a["signal_y"]=y;lags.append(a);p=est["lag_profile"].copy();p["signal_x"]=x;p["signal_y"]=y;profiles.append(p)
        good=a.estimated_lag.dropna();rng=float(good.max()-good.min()) if len(good)>=2 else 0.0 if len(good)==1 else np.nan;drifts.append({"signal_x":x,"signal_y":y,"lag_min":float(good.min()) if len(good) else np.nan,"lag_max":float(good.max()) if len(good) else np.nan,"lag_range":rng,"drift_tolerance":tol,"status":"drift_exceeds_tolerance" if np.isfinite(rng) and rng>tol else ("within_tolerance" if np.isfinite(rng) else "insufficient_estimates")})
    lb=pd.concat(lags,ignore_index=True);lp=pd.concat(profiles,ignore_index=True);ds=pd.DataFrame(drifts); st="review_sync_drift" if ds.status.eq("drift_exceeds_tolerance").any() else "sync_drift_within_tolerance"
    return {"overview":pd.DataFrame([{"status":st,"signal_pair_count":len(pairs),"lag_estimate_rows":len(lb)}]),"checks":pd.DataFrame([{"check":"signal_pairs_available","passed":True}]),"time_reset_audit":pd.DataFrame(),"lag_by_group":lb,"lag_profile":lp,"drift_summary":ds,"settings":{"signal_pairs":pairs,"drift_tolerance":tol,"include_reset_segments":include_reset_segments}}

# pyPPG ------------------------------------------------------------------------
def _resolve_ppg(data,col):
    if col is not None:
        if col not in data:raise ValueError("No usable HRP/PPG waveform column was found.")
        return col
    for c in ["HRP","PPG","PULSE","pulse"]:
        if c in data and pd.api.types.is_numeric_dtype(data[c]):return c
    raise ValueError("No usable HRP/PPG waveform column was found. Provide `ppg_col` explicitly.")


def prepare_gazepoint_pyppg_input(data, ppg_col=None, time_col=None, group_cols=None, sampling_rate=None, time_unit="auto", min_finite_prop=.50, output_dir=None, prefix="gazepoint_pyppg"):
    data=_df(data);ppg_col=_resolve_ppg(data,ppg_col);groups=_group_indices(data,group_cols);tables=[];summ=[]
    for gid,idx,base in groups:
        ppg=pd.to_numeric(data.iloc[idx][ppg_col],errors="coerce").to_numpy(float);si=np.arange(1,len(idx)+1);ts=np.full(len(idx),np.nan);status="prepared_with_sample_index_only"
        if time_col is not None:
            if time_col not in data:raise ValueError("`time_col` was not found in `data`.")
            raw=pd.to_numeric(data.iloc[idx][time_col],errors="coerce").to_numpy(float)
            if sampling_rate is not None:ts=(si-1)/sampling_rate
            else:
                good=raw[np.isfinite(raw)];dt=np.diff(good);dt=dt[dt>0];fac=1000 if time_unit=="ms" or (time_unit=="auto" and len(dt) and np.median(dt)>10) else 1;ts=(raw-raw[np.flatnonzero(np.isfinite(raw))[0]])/fac if np.any(np.isfinite(raw)) else ts
            status="ready_for_pyppg_input"
        elif sampling_rate is not None:ts=(si-1)/sampling_rate;status="ready_for_pyppg_input"
        t=pd.DataFrame({"group_id":gid,"sample_index":si,"time_s":ts,"ppg_signal":ppg});[t.insert(0,c,base[c]) for c in reversed(list(base))];tables.append(t);summ.append({**base,"group_id":gid,"n_rows":len(idx),"finite_prop":float(np.mean(np.isfinite(ppg))),"status":status if np.mean(np.isfinite(ppg))>=min_finite_prop else "insufficient_finite_ppg"})
    wt=pd.concat(tables,ignore_index=True);gs=pd.DataFrame(summ);manifest=[]
    if output_dir is not None:
        od=Path(output_dir);od.mkdir(parents=True,exist_ok=True)
        for item,obj in [("waveform_table",wt),("group_summary",gs)]:path=od/f"{prefix}_{item}.csv";obj.to_csv(path,index=False);manifest.append({"item":item,"path":str(path)})
    return {"overview":pd.DataFrame([{"input_rows":len(data),"waveform_rows":len(wt),"group_count":len(groups),"ppg_col":ppg_col,"status":"pyppg_input_prepared"}]),"waveform_table":wt,"group_summary":gs,"manifest":pd.DataFrame(manifest),"settings":{"ppg_col":ppg_col,"time_col":time_col,"group_cols":[] if group_cols is None else group_cols,"sampling_rate":sampling_rate,"time_unit":time_unit,"min_finite_prop":min_finite_prop},"_class":"gazepoint_pyppg_input"}


def assess_gazepoint_hrp_waveform_quality(data, hrp_col=None, time_col=None, group_cols=None, sampling_rate=None, time_unit="auto", min_rows=20, min_finite_prop=.80, max_flat_prop=.95, flat_tolerance=1e-8, max_gap_multiplier=3):
    data=_df(data);hrp_col=_resolve_ppg(data,hrp_col);groups=_group_indices(data,group_cols);flags=data.copy();flags["flag_missing_or_nonfinite_hrp"]=~np.isfinite(pd.to_numeric(data[hrp_col],errors="coerce"));flags["flag_large_time_gap"]=False;rows=[]
    for gid,idx,base in groups:
        x=pd.to_numeric(data.iloc[idx][hrp_col],errors="coerce").to_numpy(float);finite=np.isfinite(x);fp=float(finite.mean()) if len(x) else 0; flat=1.0
        if finite.sum()>1:flat=float(np.mean(np.abs(np.diff(x[finite]))<=flat_tolerance))
        gap=False
        if time_col is not None and time_col in data:
            t=pd.to_numeric(data.iloc[idx][time_col],errors="coerce").to_numpy(float);dt=np.diff(t);pos=dt[np.isfinite(dt)&(dt>0)];thr=np.median(pos)*max_gap_multiplier if len(pos) else np.inf;bad=np.flatnonzero(np.isfinite(dt)&(dt>thr))+1; flags.iloc[idx[bad],flags.columns.get_loc("flag_large_time_gap")]=True;gap=len(bad)>0
        if len(idx)<min_rows or fp<min_finite_prop:st="fail_low_finite_signal"
        elif flat>=max_flat_prop:st="review_flat_signal"
        elif gap:st="review_time_gaps"
        else:st="descriptive_quality_pass"
        rows.append({**base,"group_id":gid,"n_rows":len(idx),"finite_prop":fp,"flat_prop":flat,"status":st})
    gq=pd.DataFrame(rows); fail=gq.status.str.startswith("fail").any();review=(gq.status.str.startswith("review")).any();ost="fail_review_required" if fail else ("review_recommended" if review else "pass")
    return {"overview":pd.DataFrame([{"group_count":len(groups),"status":ost,"hrp_col":hrp_col}]),"group_quality":gq,"row_flags":flags,"settings":{"hrp_col":hrp_col,"time_col":time_col,"group_cols":group_cols,"min_rows":min_rows,"min_finite_prop":min_finite_prop,"max_flat_prop":max_flat_prop,"flat_tolerance":flat_tolerance,"max_gap_multiplier":max_gap_multiplier}}

# EDA descriptive ---------------------------------------------------------------
def _rolling_median(x,w):return pd.Series(x).rolling(int(w),center=True,min_periods=1).median().to_numpy(float)

def decompose_gazepoint_eda(data, signal_col=None, tonic_col=None, phasic_col=None, time_col=None, group_cols=None, window_size=31, output_prefix="eda", overwrite=False):
    data=_df(data)
    if signal_col is None:
        signal_col=next((c for c in ["GSR_US","EDA_US","GSR","EDA","GSR_OHMS","SKIN_CONDUCTANCE"] if c in data and pd.api.types.is_numeric_dtype(data[c])),None)
    if signal_col is None or signal_col not in data:raise ValueError("`signal_col` was not found in `data`.")
    if not pd.api.types.is_numeric_dtype(data[signal_col]):raise TypeError("`signal_col` must be numeric.")
    if int(window_size)<1:raise ValueError("`window_size` must be positive.")
    if not isinstance(output_prefix,str) or not output_prefix:raise ValueError("`output_prefix` must be non-empty.")
    existing_t = tonic_col if tonic_col is not None and tonic_col in data else next((c for c in ["GSR_US_TONIC","EDA_TONIC","eda_tonic"] if c in data), None)
    existing_p = phasic_col if phasic_col is not None and phasic_col in data else next((c for c in ["GSR_US_PHASIC","EDA_PHASIC","eda_phasic"] if c in data), None)
    to=f"{output_prefix}_tonic"; po=f"{output_prefix}_phasic"; mo=f"{output_prefix}_decomposition_method"
    if not overwrite and any(c in data for c in [to,po,mo]): raise ValueError("Output columns already exist. Use `overwrite = TRUE` to replace them.")
    out=data.copy(); out[to]=np.nan;out[po]=np.nan;out[mo]=None;groups=_group_indices(out,group_cols)
    if existing_t and existing_p:
        out[to]=pd.to_numeric(out[existing_t],errors="coerce");out[po]=pd.to_numeric(out[existing_p],errors="coerce");out[mo]="existing_tonic_phasic_columns";method="existing_tonic_phasic_columns"
    else:
        w=int(window_size);w=w+1 if w%2==0 else w
        for gid,idx,base in groups:
            if time_col is not None:
                if time_col not in out:raise ValueError("`time_col` was not found in `data`.")
                vals=pd.to_numeric(out.iloc[idx][time_col],errors="coerce").to_numpy(float);idx=idx[np.argsort(np.where(np.isfinite(vals),vals,np.inf))]
            x=pd.to_numeric(out.iloc[idx][signal_col],errors="coerce").to_numpy(float);ton=_rolling_median(x,w);out.iloc[idx,out.columns.get_loc(to)]=ton;out.iloc[idx,out.columns.get_loc(po)]=x-ton;out.iloc[idx,out.columns.get_loc(mo)]="rolling_median_residual"
        method="rolling_median_residual"
    ov=pd.DataFrame([{"n_rows":len(out),"signal_col":signal_col,"tonic_col":to,"phasic_col":po,"method":method,"used_existing_components":bool(existing_t and existing_p),"group_count":len(groups),"n_tonic_non_missing":int(out[to].notna().sum()),"n_phasic_non_missing":int(out[po].notna().sum()),"status":"eda_decomposition_created"}])
    out.attrs["overview"]=ov;out.attrs["settings"]={"signal_col":signal_col,"input_tonic_col":existing_t,"input_phasic_col":existing_p,"time_col":time_col,"group_cols":group_cols,"window_size":w if method=="rolling_median_residual" else int(window_size),"output_prefix":output_prefix,"note":"EDA decomposition is descriptive. Use specialised biosignal software for confirmatory SCR/EDA decomposition when required."};return out


def _mad(x):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if not len(x):return np.nan
    return float(np.median(np.abs(x-np.median(x))))


def detect_gazepoint_scr_events(data, phasic_col=None, signal_col=None, time_col=None, group_cols=None, threshold=None, min_peak_distance=10, window_size=31):
    data=_df(data)
    if phasic_col is not None and phasic_col not in data:raise ValueError("`phasic_col` was not found in `data`.")
    if signal_col is not None and signal_col not in data:raise ValueError("`signal_col` was not found in `data`.")
    if threshold is not None and (not np.isscalar(threshold) or not np.isfinite(threshold)):raise ValueError("`threshold` must be NULL or a single numeric value.")
    if int(min_peak_distance)<1:raise ValueError("`min_peak_distance` must be positive.")
    if int(window_size)<1:raise ValueError("`window_size` must be positive.")
    working=data;decomp=False
    if phasic_col is None:
        phasic_col=next((c for c in ["GSR_US_PHASIC","EDA_PHASIC","eda_phasic"] if c in working),None)
        if phasic_col is None:
            working=decompose_gazepoint_eda(working,signal_col=signal_col,time_col=time_col,group_cols=group_cols,window_size=window_size,output_prefix="scr_detection_eda",overwrite=True);phasic_col="scr_detection_eda_phasic";decomp=True
    if not pd.api.types.is_numeric_dtype(working[phasic_col]):raise TypeError("`phasic_col` must be numeric.")
    groups=_group_indices(working,group_cols);events=[];summ=[];eid=0
    for gid,idx,base in groups:
        if time_col is not None:
            vals_t=pd.to_numeric(working.iloc[idx][time_col],errors="coerce").to_numpy(float);idx=idx[np.argsort(np.where(np.isfinite(vals_t),vals_t,np.inf))]
        x=pd.to_numeric(working.iloc[idx][phasic_col],errors="coerce").to_numpy(float);finite=x[np.isfinite(x)]
        if threshold is None:
            med=float(np.median(finite)) if len(finite) else 0; mad=_mad(finite); local=max(0.0,med+3*(mad if np.isfinite(mad) else 0.0))
        else:local=float(threshold)
        cand=[i for i in range(1,len(x)-1) if np.isfinite(x[i]) and x[i]>=local and x[i]>x[i-1] and x[i]>=x[i+1]];sel=[]
        for i in cand:
            if not sel or i-sel[-1]>=int(min_peak_distance):sel.append(i)
            elif x[i]>x[sel[-1]]:sel[-1]=i
        for i in sel:
            eid+=1;pos=int(idx[i]);events.append({"event_id":eid,"group":gid,"row_index":pos+1,"time":np.nan if time_col is None else working.iloc[pos][time_col],"peak_value":x[i],"threshold":local,"phasic_col":phasic_col,"detection_method":"local_peak_above_threshold"})
        summ.append({"group":gid,"n_samples":len(x),"threshold":local,"n_events":len(sel),"event_rate_per_1000_samples":len(sel)/len(x)*1000 if len(x) else np.nan})
    ev=pd.DataFrame(events,columns=["event_id","group","row_index","time","peak_value","threshold","phasic_col","detection_method"]);gs=pd.DataFrame(summ);status="scr_events_detected" if len(ev) else "no_scr_events_detected"
    return {"overview":pd.DataFrame([{"n_rows":len(data),"group_count":len(groups),"phasic_col":phasic_col,"decomposition_used":decomp,"threshold":np.nan if threshold is None else threshold,"min_peak_distance":int(min_peak_distance),"n_events":len(ev),"status":status}]),"events":ev,"group_summary":gs,"settings":{"phasic_col":phasic_col,"signal_col":signal_col,"time_col":time_col,"group_cols":group_cols,"threshold":threshold,"min_peak_distance":int(min_peak_distance),"window_size":int(window_size),"note":"SCR events are simple SCR-like local peaks. Use specialised biosignal software for confirmatory SCR event detection."}}

# Reporting --------------------------------------------------------------------
def create_gazepoint_biometrics_checklist(data, require_active_signal=True):
    data=_df(data)
    def active(names):
        return any(c in data and pd.to_numeric(data[c],errors="coerce").notna().any() for c in names)
    gsr=active(["GSR_US","GSR","EDA"]);hr=active(["HR"]);dial=active(["DIAL"]);ppg=active(["HRP","PPG"]);ibi=active(["IBI","IBI_clean_ms"])
    overview=pd.DataFrame([{"n_rows":len(data),"n_columns":data.shape[1],"active_gsr_eda":gsr,"active_heart_rate":hr,"active_engagement_dial":dial,"active_ppg":ppg,"active_ibi":ibi,"status":"ready" if (gsr or hr or dial or ppg or ibi) else ("fail_no_active_signal" if require_active_signal else "review_no_active_signal")}])
    channels=pd.DataFrame([{"channel":"GSR/EDA","active":gsr},{"channel":"heart rate","active":hr},{"channel":"engagement dial","active":dial},{"channel":"PPG","active":ppg},{"channel":"IBI/RR","active":ibi}])
    miss=pd.DataFrame([{"column":c,"missing_n":int(data[c].isna().sum()),"missing_prop":float(data[c].isna().mean())} for c in data.columns])
    quality=pd.DataFrame([{"check":"active_signal_present","passed":bool(gsr or hr or dial or ppg or ibi)}]); issues=quality.loc[~quality.passed].copy(); caut=pd.DataFrame({"caution":["Biometric signals should be interpreted conservatively and do not directly identify emotion, stress, cognition, preference, health status, or diagnosis."]})
    return {"overview":overview,"channels":channels,"quality":quality,"missingness":miss,"validation_issues":issues,"interpretation_cautions":caut,"_class":"gazepoint_biometrics_checklist"}


def create_gazepoint_biometrics_methods_text(checklist=None, data=None, include_cautions=True):
    if checklist is None:
        if data is None:raise ValueError("Either `checklist` or `data` must be supplied.")
        checklist=create_gazepoint_biometrics_checklist(data)
    if not isinstance(checklist,dict) or checklist.get("_class")!="gazepoint_biometrics_checklist":raise ValueError("`checklist` must be produced by `create_gazepoint_biometrics_checklist()`.")
    ov=checklist["overview"].iloc[0];parts=[f"Gazepoint Biometrics data were processed in a table containing {int(ov.n_rows)} rows and {int(ov.n_columns)} columns."]
    if ov.active_gsr_eda:parts.append("GSR/EDA channels were retained for electrodermal analysis.")
    if ov.active_heart_rate:parts.append("The heart rate channel was retained for cardiovascular summaries.")
    if ov.active_engagement_dial:parts.append("The engagement dial channel was retained as a recorded response signal.")
    if include_cautions:parts.append("All biometric measures were interpreted conservatively; physiological signals were not treated as direct labels of emotion, stress, cognition, preference, health status, or diagnosis.")
    return " ".join(parts)
