from __future__ import annotations

from pathlib import Path
import re
import numpy as np
import pandas as pd

from ._helpers import as_list, ensure_df, require_cols, r_sd


def _groups(df, cols=None):
    cols=as_list(cols); require_cols(df,cols,"group_cols")
    if not cols: return [("all_rows",np.arange(len(df),dtype=int))]
    work=df.reset_index(drop=True); grouper=cols[0] if len(cols)==1 else cols
    return [(" | ".join(map(str,key if isinstance(key,tuple) else (key,))), b.index.to_numpy(int)) for key,b in work.groupby(grouper,sort=False,dropna=False)]


def _regress_adjust(df,y_col,x_cols,group_cols=None,output_col="adjusted",fitted_col="fitted",quadratic=False,model_by_group=True,add_mean=True,status_col="status"):
    out=df.reset_index(drop=True).copy(); out[output_col]=np.nan; out[fitted_col]=np.nan; out[status_col]="not_processed"
    groups=_groups(out,group_cols) if model_by_group else [("all_rows",np.arange(len(out)))]
    rows=[]
    for gid,idx in groups:
        y=pd.to_numeric(out.loc[idx,y_col],errors="coerce").to_numpy(float)
        X=np.column_stack([pd.to_numeric(out.loc[idx,c],errors="coerce").to_numpy(float) for c in x_cols])
        if quadratic: X=np.column_stack([X,X[:,0]**2])
        complete=np.isfinite(y)&np.all(np.isfinite(X),axis=1); minimum=max(5,X.shape[1]+2)
        if complete.sum()<minimum:
            out.loc[idx,status_col]="insufficient_complete_cases"; rows.append({"group_id":gid,"n_rows":len(idx),"n_complete":int(complete.sum()),"r_squared":np.nan,"status":"insufficient_complete_cases"}); continue
        A=np.column_stack([np.ones(complete.sum()),X[complete]])
        beta=np.linalg.lstsq(A,y[complete],rcond=None)[0]; pred=A@beta; resid=y[complete]-pred
        fitted=np.full(len(idx),np.nan); fitted[complete]=pred
        adj=np.full(len(idx),np.nan); adj[complete]=resid+(float(np.mean(y[complete])) if add_mean else 0)
        out.loc[idx,output_col]=adj; out.loc[idx,fitted_col]=fitted; out.loc[idx,status_col]=np.where(complete,"adjusted","incomplete")
        ssr=float(np.sum(resid**2)); sst=float(np.sum((y[complete]-np.mean(y[complete]))**2)); r2=1-ssr/sst if sst>0 else np.nan
        n=complete.sum(); p=A.shape[1]-1; ar2=1-(1-r2)*(n-1)/(n-p-1) if np.isfinite(r2) and n>p+1 else np.nan
        rows.append({"group_id":gid,"n_rows":len(idx),"n_complete":int(n),"r_squared":r2,"adjusted_r_squared":ar2,"residual_sd":r_sd(resid),"status":"model_fitted"})
    return out,pd.DataFrame(rows),groups


def correct_gazepoint_eda_temperature(dat,eda_col="GSR_US",temperature_cols=None,group_cols=None,time_col=None,output_col="eda_temperature_adjusted",fitted_col="eda_temperature_fitted",model_by_group=True,add_intercept_mean=True):
    df=ensure_df(dat,"dat"); temps=as_list(temperature_cols)
    if not temps: raise ValueError("`temperature_cols` must identify one or more columns.")
    require_cols(df,[eda_col,*temps,*as_list(group_cols),*([time_col] if time_col else [])],"required columns")
    out,summary,groups=_regress_adjust(df,eda_col,temps,group_cols,output_col,fitted_col,False,model_by_group,add_intercept_mean,"eda_temperature_correction_status")
    summary["status"]=summary["status"].replace("model_fitted","temperature_model_fitted")
    ok=summary.status.eq("temperature_model_fitted"); status="eda_temperature_correction_complete" if ok.all() else ("eda_temperature_correction_partial" if ok.any() else "eda_temperature_correction_failed")
    overview=pd.DataFrame([{"input_rows":len(df),"output_rows":len(out),"group_count":len(groups),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":status,"interpretation":"The output is temperature-adjusted EDA. Residualisation does not make the signal purely cognitive, emotional, or sympathetic."}])
    out.attrs.update(eda_temperature_overview=overview.iloc[0].to_dict(),eda_temperature_model_summary=summary,eda_temperature_settings={"eda_col":eda_col,"temperature_cols":temps,"group_cols":as_list(group_cols),"time_col":time_col,"output_col":output_col,"fitted_col":fitted_col,"model_by_group":model_by_group,"add_intercept_mean":add_intercept_mean},class_=["gazepoint_eda_temperature_corrected","data.frame"])
    return out


def _time_seconds(x):
    a=np.asarray(x,float); d=np.diff(a[np.isfinite(a)]); d=d[d>0]; return a/1000 if d.size and np.median(d)>10 else a


def _simple_kmeans_1d(x,k,seed=None,iters=50):
    rng=np.random.default_rng(seed); vals=np.asarray(x,float); q=np.linspace(0,1,k+2)[1:-1]; centers=np.quantile(vals,q) if k>1 else np.array([np.mean(vals)])
    if np.unique(centers).size<k: centers=rng.choice(vals,k,replace=False)
    lab=np.zeros(len(vals),int)
    for _ in range(iters):
        new=np.argmin(np.abs(vals[:,None]-centers[None,:]),axis=1)
        nc=np.array([vals[new==j].mean() if np.any(new==j) else centers[j] for j in range(k)])
        if np.array_equal(new,lab) and np.allclose(nc,centers): break
        lab,centers=new,nc
    return lab,centers


def extract_gazepoint_beats_kmeans(dat,pulse_col="HRP",time_col="CNT",group_cols=None,k=2,peak_polarity="positive",min_distance_s=.30,sampling_rate=None,seed=None):
    df=ensure_df(dat,"dat").reset_index(drop=True); require_cols(df,[pulse_col,time_col,*as_list(group_cols)])
    beats=[]; intervals=[]; ts=[]; summaries=[]
    for gid,idx in _groups(df,group_cols):
        idx=idx[np.argsort(pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float))]; tr=pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float); t=_time_seconds(tr); p=pd.to_numeric(df.loc[idx,pulse_col],errors="coerce").to_numpy(float); finite=np.isfinite(t)&np.isfinite(p)
        if finite.sum()<max(10,k*3) or np.unique(p[finite]).size<k:
            summaries.append({"group_id":gid,"n_rows":len(idx),"beat_count":0,"mean_ibi_s":np.nan,"mean_hr_bpm":np.nan,"status":"insufficient_pulse_variability"}); continue
        labels,centers=_simple_kmeans_1d(p[finite],k,seed); full=np.full(len(p),-1); full[np.flatnonzero(finite)]=labels; target=int(np.argmax(centers) if peak_polarity=="positive" else np.argmin(centers)); cand=np.flatnonzero(full==target)
        # local extrema among candidate-region points, followed by refractory selection
        local=[]
        for j in cand:
            left=p[j-1] if j>0 else p[j]; right=p[j+1] if j+1<len(p) else p[j]
            if (peak_polarity=="positive" and p[j]>=left and p[j]>=right) or (peak_polarity=="negative" and p[j]<=left and p[j]<=right): local.append(j)
        chosen=[]
        for j in sorted(local,key=lambda z:t[z]):
            if not chosen or t[j]-t[chosen[-1]]>=min_distance_s: chosen.append(j)
            elif (p[j]>p[chosen[-1]] if peak_polarity=="positive" else p[j]<p[chosen[-1]]): chosen[-1]=j
        bt=t[chosen]
        for n,j in enumerate(chosen,1): beats.append({"group_id":gid,"beat_index":n,"row_index":int(idx[j])+1,"beat_time":float(t[j]),"pulse":float(p[j])})
        ibis=np.diff(bt)
        for n,v in enumerate(ibis,1): intervals.append({"group_id":gid,"interval_index":n,"ibi_s":float(v),"hr_bpm":60/float(v) if v>0 else np.nan})
        summaries.append({"group_id":gid,"n_rows":len(idx),"beat_count":len(chosen),"mean_ibi_s":float(np.mean(ibis)) if len(ibis) else np.nan,"mean_hr_bpm":float(np.mean(60/ibis)) if len(ibis) else np.nan,"status":"beats_extracted" if chosen else "no_beats_extracted"})
    b=pd.DataFrame(beats); i=pd.DataFrame(intervals); s=pd.DataFrame(summaries)
    return {"overview":pd.DataFrame([{"group_count":len(s),"beat_rows":len(b),"interval_rows":len(i),"status":"kmeans_beats_extracted" if len(b) else "kmeans_beats_failed"}]),"beat_table":b,"interval_table":i,"timeseries":pd.DataFrame(ts),"summary":s,"settings":{"pulse_col":pulse_col,"time_col":time_col,"group_cols":as_list(group_cols),"k":k,"peak_polarity":peak_polarity,"min_distance_s":min_distance_s,"sampling_rate":sampling_rate,"seed":seed},"class":["gazepoint_kmeans_beats","list"]}


def audit_gazepoint_stabilization_period(dat,time_col="CNT",group_cols=None,stabilization_minutes=10,action="flag",output_col="in_stabilization_period",time_units="auto"):
    df=ensure_df(dat,"dat").reset_index(drop=True).copy(); require_cols(df,[time_col,*as_list(group_cols)]); out=df.copy(); out[output_col]=False; out["stabilization_elapsed_s"]=np.nan; out["stabilization_audit_status"]="not_processed"; rows=[]; cutoff=stabilization_minutes*60
    for gid,idx in _groups(df,group_cols):
        raw=pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float); t=raw/1000 if time_units=="milliseconds" else (raw if time_units=="seconds" else _time_seconds(raw)); finite=t[np.isfinite(t)]; start=float(np.min(finite)); elapsed=t-start; flag=np.isfinite(elapsed)&(elapsed<cutoff); out.loc[idx,output_col]=flag; out.loc[idx,"stabilization_elapsed_s"]=elapsed; out.loc[idx,"stabilization_audit_status"]=np.where(flag,"within_stabilization_period","after_stabilization_period"); rows.append({"group_id":gid,"n_rows":len(idx),"stabilization_rows":int(flag.sum()),"retained_rows_after_stabilization":int((~flag).sum()),"stabilization_minutes":stabilization_minutes,"start_time_s":start,"cutoff_time_s":start+cutoff,"status":"stabilization_period_audited"})
    if action=="trim": out=out.loc[~out[output_col]].reset_index(drop=True)
    out.attrs.update(stabilization_overview={"input_rows":len(df),"output_rows":len(out),"group_count":len(rows),"stabilization_minutes":stabilization_minutes,"action":action,"status":"stabilization_period_audited"},stabilization_summary=pd.DataFrame(rows),class_=["gazepoint_stabilization_audit","data.frame"]); return out


def regress_gazepoint_pupil_luminance(dat,pupil_col,luminance_col,group_cols=None,time_col=None,output_col="pupil_luminance_adjusted",fitted_col="pupil_luminance_fitted",include_quadratic=True,model_by_group=True,add_intercept_mean=True):
    df=ensure_df(dat,"dat"); require_cols(df,[pupil_col,luminance_col,*as_list(group_cols),*([time_col] if time_col else [])]); out,summary,groups=_regress_adjust(df,pupil_col,[luminance_col],group_cols,output_col,fitted_col,include_quadratic,model_by_group,add_intercept_mean,"pupil_luminance_regression_status"); summary["status"]=summary["status"].replace("model_fitted","luminance_model_fitted"); ok=summary.status.eq("luminance_model_fitted"); status="pupil_luminance_regression_complete" if ok.all() else ("pupil_luminance_regression_partial" if ok.any() else "pupil_luminance_regression_failed"); out.attrs.update(pupil_luminance_overview={"input_rows":len(df),"output_rows":len(out),"group_count":len(groups),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":status},pupil_luminance_model_summary=summary,class_=["gazepoint_pupil_luminance_adjusted","data.frame"]); return out


def model_gazepoint_hrv_ipfm(dat,ibi_col="IBI",beat_time_col=None,group_cols=None,ibi_units="auto",output_sampling_rate=4,max_frequency=.5):
    df=ensure_df(dat,"dat").reset_index(drop=True); require_cols(df,[*([ibi_col] if ibi_col else []),*([beat_time_col] if beat_time_col else []),*as_list(group_cols)]); br=[]; ir=[]; sr=[]; sums=[]
    for gid,idx in _groups(df,group_cols):
        if beat_time_col:
            bt=np.unique(pd.to_numeric(df.loc[idx,beat_time_col],errors="coerce").to_numpy(float)); bt=np.sort(bt[np.isfinite(bt)])
        else:
            ibi=pd.to_numeric(df.loc[idx,ibi_col],errors="coerce").to_numpy(float); ibi=ibi[np.isfinite(ibi)&(ibi>0)]; sec=ibi/1000 if ibi_units=="milliseconds" or (ibi_units=="auto" and ibi.size and np.median(ibi)>10) else ibi; bt=np.cumsum(sec)
        if len(bt)<3: sums.append({"group_id":gid,"beat_count":len(bt),"impulse_rows":0,"dominant_frequency_hz":np.nan,"status":"insufficient_beats"}); continue
        bt=bt-np.min(bt); grid=np.arange(0,np.max(bt)+1/output_sampling_rate/2,1/output_sampling_rate); impulse=np.zeros(len(grid)); nearest=[int(np.argmin(np.abs(grid-b))) for b in bt]; impulse[nearest]=1
        for n,b in enumerate(bt,1): br.append({"group_id":gid,"beat_index":n,"beat_time":float(b)})
        for t,v in zip(grid,impulse): ir.append({"group_id":gid,"time":float(t),"impulse":float(v)})
        z=impulse-np.mean(impulse); spec=np.abs(np.fft.rfft(z))**2/len(z); freq=np.fft.rfftfreq(len(z),d=1/output_sampling_rate); keep=(freq>0)&(freq<=max_frequency)
        for f,p in zip(freq[keep],spec[keep]): sr.append({"group_id":gid,"frequency_hz":float(f),"power":float(p)})
        dom=float(freq[keep][np.argmax(spec[keep])]) if keep.any() else np.nan; sums.append({"group_id":gid,"beat_count":len(bt),"impulse_rows":len(grid),"dominant_frequency_hz":dom,"status":"ipfm_impulse_train_created"})
    b,i,s,sm=pd.DataFrame(br),pd.DataFrame(ir),pd.DataFrame(sr),pd.DataFrame(sums); ok=sm.status.eq("ipfm_impulse_train_created") if len(sm) else pd.Series([],dtype=bool); status="ipfm_model_created" if len(ok) and ok.all() else ("ipfm_model_partial" if ok.any() else "ipfm_model_failed")
    return {"overview":pd.DataFrame([{"group_count":len(sm),"beat_rows":len(b),"impulse_rows":len(i),"spectrum_rows":len(s),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()) if len(ok) else 0,"status":status}]),"beat_table":b,"impulse_table":i,"spectrum_table":s,"summary":sm,"settings":{"ibi_col":ibi_col,"beat_time_col":beat_time_col,"group_cols":as_list(group_cols),"ibi_units":ibi_units,"output_sampling_rate":output_sampling_rate,"max_frequency":max_frequency},"class":["gazepoint_hrv_ipfm","list"]}


def _extract_df(data):
    if isinstance(data,pd.DataFrame): return data
    if isinstance(data,dict):
        for k in ["data","biometrics","signal_table"]:
            if isinstance(data.get(k),pd.DataFrame): return data[k]
    raise TypeError("`data` must be a data frame or contain one.")


def _external_eda(data,method,eda_col=None,time_col=None,group_cols=None,sampling_rate=None,time_unit="auto",convert_resistance_to_us=False,min_finite_prop=.5,output_dir=None,prefix="gazepoint"):
    df=_extract_df(data).reset_index(drop=True); groups=as_list(group_cols); require_cols(df,groups,"group_cols")
    if eda_col is None:
        for c in ["GSR_US","EDA","EDA_US","SCR","SCL","GSR"]:
            if c in df.columns: eda_col=c; break
    if eda_col is None or eda_col not in df.columns: raise ValueError("No EDA/conductance column was found.")
    rows=[]; sums=[]
    for gid,idx in _groups(df,groups):
        sig=pd.to_numeric(df.loc[idx,eda_col],errors="coerce").to_numpy(float); converted=bool(convert_resistance_to_us and str(eda_col).upper()=="GSR"); cond=np.where(np.isfinite(sig)&(sig!=0),1_000_000/sig,np.nan) if converted else sig.copy()
        if time_col is not None:
            require_cols(df,[time_col]); raw=pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float)
            if time_unit=="ms": t=raw/1000; detected="milliseconds"
            elif time_unit=="seconds": t=raw; detected="seconds"
            elif time_unit=="samples":
                if sampling_rate is None: raise ValueError("`sampling_rate` is required for sample time.")
                t=(raw-raw[0])/sampling_rate; detected="samples"
            else:
                # CNT and integer counters use supplied sampling rate as sample indices.
                if str(time_col).upper()=="CNT" and sampling_rate is not None: t=(raw-raw[0])/sampling_rate; detected="samples"
                else: t=_time_seconds(raw); detected="milliseconds" if np.nanmedian(np.diff(raw))>10 else "seconds"
        else:
            if sampling_rate is None: raise ValueError("`sampling_rate` is required when no time column is available.")
            t=np.arange(len(idx))/sampling_rate; detected="sample_index"
        finite=np.isfinite(cond)&np.isfinite(t); ready=float(finite.mean())>=min_finite_prop
        group_values={c:df.loc[idx[0],c] for c in groups}
        for j,pos in enumerate(idx): rows.append({**group_values,"group_id":gid,"row_index":int(pos)+1,"time_s":float(t[j]),"conductance_us":float(cond[j]) if np.isfinite(cond[j]) else np.nan,"conductance_unit":"microsiemens_converted_from_resistance" if converted else "microsiemens","used_resistance_conversion":converted,"detected_time_unit":detected,"sampling_rate_hz":sampling_rate})
        sums.append({**group_values,"group_id":gid,"n_rows":len(idx),"n_finite":int(finite.sum()),"finite_prop":float(finite.mean()),"status":"ready" if ready else "insufficient_finite_data"})
    signal=pd.DataFrame(rows); summary=pd.DataFrame(sums)
    if method=="cvxeda": signal["y"]=signal["conductance_us"]
    manifest=pd.DataFrame(columns=["file_role","path"])
    if output_dir is not None:
        p=Path(output_dir); p.mkdir(parents=True,exist_ok=True); sf=p/f"{prefix}_signal.csv"; gf=p/f"{prefix}_groups.csv"; signal.to_csv(sf,index=False); summary.to_csv(gf,index=False); manifest=pd.DataFrame([{"file_role":"signal_table","path":str(sf)},{"file_role":"group_summary","path":str(gf)}])
    ready=int(summary.status.eq("ready").sum()); status=f"{method}_input_prepared" if ready==len(summary) else (f"{method}_input_partial" if ready else f"{method}_input_failed")
    return {"overview":pd.DataFrame([{"input_rows":len(df),"group_count":len(summary),"ready_group_count":ready,"status":status}]),"signal_table":signal,"group_summary":summary,"manifest":manifest,"settings":{"method":method,"eda_col":eda_col,"time_col":time_col,"group_cols":groups,"sampling_rate":sampling_rate,"time_unit":time_unit,"convert_resistance_to_us":convert_resistance_to_us,"min_finite_prop":min_finite_prop},"class":[f"gazepoint_{method}_input","gazepoint_external_eda_input","list"]}


def prepare_gazepoint_ledalab_input(data,**kwargs): return _external_eda(data,"ledalab",**kwargs)
def prepare_gazepoint_pspm_input(data,**kwargs): return _external_eda(data,"pspm",**kwargs)
def prepare_gazepoint_cvxeda_input(data,**kwargs): return _external_eda(data,"cvxeda",**kwargs)


def classify_gazepoint_eda_response_pattern(data,response_col=None,group_cols=None,summary_function="max_abs",no_response_threshold=.01,low_response_threshold=.05,moderate_response_threshold=.20):
    df=_extract_df(data).reset_index(drop=True); groups=as_list(group_cols); require_cols(df,groups,"group_cols")
    if response_col is None:
        for c in ["scr_amplitude_us","scr_amplitude","SCR_Amplitude","GSR_US_PHASIC","GSR_US"]:
            if c in df.columns: response_col=c; break
    if response_col is None: raise ValueError("No EDA response column was found.")
    if not (0<=no_response_threshold<=low_response_threshold<=moderate_response_threshold): raise ValueError("Thresholds must satisfy: no_response_threshold <= low_response_threshold <= moderate_response_threshold.")
    rows=[]
    for gid,idx in _groups(df,groups):
        vals=pd.to_numeric(df.loc[idx,response_col],errors="coerce").to_numpy(float); finite=vals[np.isfinite(vals)]; ab=np.abs(finite); val=np.nan if not len(ab) else (float(np.max(ab)) if summary_function=="max_abs" else (float(np.mean(ab)) if summary_function=="mean_abs" else float(np.median(ab))))
        if not np.isfinite(val): label="unclassified_no_finite_response"
        elif val<=no_response_threshold: label="no_detectable_response"
        elif val<=low_response_threshold: label="low_response"
        elif val<=moderate_response_threshold: label="moderate_response"
        else: label="high_response"
        row={c:df.loc[idx[0],c] for c in groups}; row.update(group_id=gid,response_col=response_col,n_rows=len(idx),n_finite=len(finite),finite_prop=len(finite)/len(idx),summary_function=summary_function,response_value=val,response_pattern=label,status="response_pattern_classified" if len(finite) else "fail_no_finite_response_values",interpretation="This is a descriptive EDA response-pattern label only. It does not infer emotion, valence, stress, trust, preference, cognition, or diagnosis."); rows.append(row)
    cl=pd.DataFrame(rows); ok=cl.status.eq("response_pattern_classified"); status="eda_response_patterns_classified" if ok.all() else ("partial_eda_response_patterns_classified" if ok.any() else "eda_response_patterns_not_classified")
    return {"overview":pd.DataFrame([{"input_rows":len(df),"group_count":len(cl),"classified_group_count":int(ok.sum()),"response_col":response_col,"summary_function":summary_function,"status":status}]),"classifications":cl,"settings":{"response_col":response_col,"group_cols":groups,"summary_function":summary_function,"no_response_threshold":no_response_threshold,"low_response_threshold":low_response_threshold,"moderate_response_threshold":moderate_response_threshold},"class":["gazepoint_eda_response_pattern","list"]}


def extract_gazepoint_bilateral_eda_asymmetry(dat,left_col,right_col,time_col=None,group_cols=None,output_prefix="beda"):
    df=ensure_df(dat,"dat").reset_index(drop=True); require_cols(df,[left_col,right_col,*([time_col] if time_col else []),*as_list(group_cols)]); rows=[]; sums=[]
    for gid,idx in _groups(df,group_cols):
        if time_col: idx=idx[np.argsort(pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float))]
        l=pd.to_numeric(df.loc[idx,left_col],errors="coerce").to_numpy(float); r=pd.to_numeric(df.loc[idx,right_col],errors="coerce").to_numpy(float); diff=l-r; mean_pair=np.nanmean(np.column_stack([l,r]),axis=1); norm=np.where(np.isfinite(mean_pair)&(mean_pair!=0),diff/mean_pair,np.nan); logr=np.where(np.isfinite(l)&np.isfinite(r)&(l>0)&(r>0),np.log(l/r),np.nan); grad=np.full(len(idx),np.nan)
        if time_col and len(idx)>1:
            t=pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float); dt=np.diff(t); grad[1:]=np.where(np.isfinite(dt)&(dt!=0),np.diff(diff)/dt,np.nan)
        block=pd.DataFrame({"row_index":idx+1,"group_id":gid,left_col:l,right_col:r,f"{output_prefix}_left_minus_right":diff,f"{output_prefix}_absolute_difference":np.abs(diff),f"{output_prefix}_normalised_difference":norm,f"{output_prefix}_log_left_right_ratio":logr,f"{output_prefix}_difference_gradient":grad});
        if time_col: block.insert(2,time_col,df.loc[idx,time_col].to_numpy())
        rows.append(block); valid=np.isfinite(l)&np.isfinite(r); sums.append({"group_id":gid,"n_rows":len(idx),"n_valid_pairs":int(valid.sum()),"mean_left":float(np.mean(l[valid])) if valid.any() else np.nan,"mean_right":float(np.mean(r[valid])) if valid.any() else np.nan,"mean_left_minus_right":float(np.mean(diff[valid])) if valid.any() else np.nan,"median_left_minus_right":float(np.median(diff[valid])) if valid.any() else np.nan,"mean_absolute_difference":float(np.mean(np.abs(diff[valid]))) if valid.any() else np.nan,"mean_normalised_difference":float(np.nanmean(norm[valid])) if valid.any() else np.nan,"mean_log_left_right_ratio":float(np.nanmean(logr[valid])) if valid.any() else np.nan,"sd_left_minus_right":r_sd(diff[valid]),"status":"bilateral_eda_asymmetry_extracted" if valid.any() else "no_valid_bilateral_pairs"})
    ts=pd.concat(rows,ignore_index=True); sm=pd.DataFrame(sums); ok=sm.status.eq("bilateral_eda_asymmetry_extracted"); status="bilateral_eda_asymmetry_complete" if ok.all() else ("bilateral_eda_asymmetry_partial" if ok.any() else "bilateral_eda_asymmetry_failed"); return {"overview":pd.DataFrame([{"group_count":len(sm),"timeseries_rows":len(ts),"summary_rows":len(sm),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":status}]),"asymmetry_timeseries":ts,"summary":sm,"settings":{"left_col":left_col,"right_col":right_col,"time_col":time_col,"group_cols":as_list(group_cols),"output_prefix":output_prefix},"class":["gazepoint_bilateral_eda_asymmetry","list"]}


def denoise_gazepoint_quantization_noise(dat,signal_cols,resolution,group_cols=None,output_suffix="_quantization_jittered",seed=None,overwrite=False):
    df=ensure_df(dat,"dat").copy(); sigs=as_list(signal_cols); require_cols(df,[*sigs,*as_list(group_cols)]); rng=np.random.default_rng(seed); summary=[]
    if isinstance(resolution,dict): resmap=resolution
    elif np.isscalar(resolution): resmap={c:float(resolution) for c in sigs}
    else: raise ValueError("When `resolution` has multiple values, it must be named.")
    for c in sigs:
        outc=c+output_suffix
        if outc in df.columns and not overwrite: raise ValueError(f"Output column `{outc}` already exists. Use `overwrite = TRUE`.")
        res=float(resmap[c]); x=pd.to_numeric(df[c],errors="coerce").to_numpy(float); noise=rng.uniform(-res/2,res/2,len(df)); y=x.copy(); y[np.isfinite(x)]+=noise[np.isfinite(x)]; df[outc]=y; summary.append({"signal_col":c,"output_col":outc,"resolution":res,"noise_min":-res/2,"noise_max":res/2,"finite_rows":int(np.isfinite(x).sum()),"changed_rows":int(np.isfinite(x).sum()),"status":"quantization_jitter_added"})
    df.attrs.update(quantization_noise_overview={"input_rows":len(df),"output_rows":len(df),"signal_count":len(sigs),"status":"quantization_noise_reduction_complete"},quantization_noise_summary=pd.DataFrame(summary),class_=["gazepoint_quantization_noise_adjusted","data.frame"]); return df


def extract_gazepoint_edr_pca(dat,ecg_cols,time_col=None,group_cols=None,n_components=1,scale=True,output_prefix="edr_pca"):
    df=ensure_df(dat,"dat").reset_index(drop=True); cols=as_list(ecg_cols)
    if len(cols)<2: raise ValueError("`ecg_cols` must contain at least two ECG morphology columns.")
    require_cols(df,[*cols,*([time_col] if time_col else []),*as_list(group_cols)]); rows=[]; comps=[]
    for gid,idx in _groups(df,group_cols):
        if time_col: idx=idx[np.argsort(pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float))]
        X=df.loc[idx,cols].apply(pd.to_numeric,errors="coerce").to_numpy(float); complete=np.all(np.isfinite(X),axis=1); block=pd.DataFrame({"row_index":idx+1,"group_id":gid});
        if time_col: block[time_col]=df.loc[idx,time_col].to_numpy()
        for k in range(1,n_components+1): block[f"{output_prefix}_pc{k}"]=np.nan
        if complete.sum()<max(3,n_components+1): block[f"{output_prefix}_status"]="insufficient_complete_ecg_morphology"; comps.append(pd.DataFrame({"group_id":gid,"component":range(1,n_components+1),"variance_explained":np.nan,"cumulative_variance_explained":np.nan,"status":"insufficient_complete_ecg_morphology"})); rows.append(block); continue
        Z=X[complete].copy(); Z-=Z.mean(axis=0)
        if scale:
            sd=Z.std(axis=0,ddof=1); sd[sd==0]=1; Z/=sd
        U,S,Vt=np.linalg.svd(Z,full_matrices=False); scores=U*S; avail=min(n_components,scores.shape[1]);
        for k in range(avail): block.loc[complete,f"{output_prefix}_pc{k+1}"]=scores[:,k]
        block[f"{output_prefix}_status"]=np.where(complete,"edr_pca_extracted","incomplete_ecg_morphology"); var=S**2; ve=var/var.sum(); comps.append(pd.DataFrame({"group_id":gid,"component":np.arange(1,avail+1),"variance_explained":ve[:avail],"cumulative_variance_explained":np.cumsum(ve)[:avail],"status":"edr_pca_extracted"})); rows.append(block)
    ts=pd.concat(rows,ignore_index=True); cs=pd.concat(comps,ignore_index=True); status_col=f"{output_prefix}_status"; ok=ts[status_col].eq("edr_pca_extracted"); return {"overview":pd.DataFrame([{"group_count":len(_groups(df,group_cols)),"timeseries_rows":len(ts),"component_rows":len(cs),"successful_rows":int(ok.sum()),"problem_rows":int((~ok).sum()),"status":"edr_pca_extracted" if ok.any() else "edr_pca_failed"}]),"edr_timeseries":ts,"component_summary":cs,"settings":{"ecg_cols":cols,"time_col":time_col,"group_cols":as_list(group_cols),"n_components":n_components,"scale":scale,"output_prefix":output_prefix},"class":["gazepoint_edr_pca","list"]}


def analyze_gazepoint_skin_potential(dat,sp_col,time_col,group_cols=None,response_direction="both",response_threshold=None,min_response_distance_s=1):
    df=ensure_df(dat,"dat").reset_index(drop=True); require_cols(df,[sp_col,time_col,*as_list(group_cols)]); levels=[]; responses=[]; times=[]
    for gid,idx in _groups(df,group_cols):
        idx=idx[np.argsort(pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float))]; t=pd.to_numeric(df.loc[idx,time_col],errors="coerce").to_numpy(float); sp=pd.to_numeric(df.loc[idx,sp_col],errors="coerce").to_numpy(float); finite=np.isfinite(t)&np.isfinite(sp); center=float(np.median(sp[finite])) if finite.any() else np.nan; centered=sp-center; deriv=np.full(len(sp),np.nan); dt=np.diff(t); deriv[1:]=np.where(np.isfinite(dt)&(dt!=0),np.diff(sp)/dt,np.nan)
        thr=response_threshold
        if thr is None:
            vals=deriv[np.isfinite(deriv)]; mad=np.median(np.abs(vals-np.median(vals))) if len(vals) else np.nan
            if not np.isfinite(mad) or mad==0: mad=np.std(vals,ddof=1) if len(vals)>1 else np.nan
            thr=6*mad if np.isfinite(mad) and mad>0 else np.nan
        if not np.isfinite(thr) or thr<=0: cand=np.array([],int)
        elif response_direction=="positive": cand=np.flatnonzero(np.isfinite(deriv)&(deriv>=thr))
        elif response_direction=="negative": cand=np.flatnonzero(np.isfinite(deriv)&(deriv<=-thr))
        else: cand=np.flatnonzero(np.isfinite(deriv)&(np.abs(deriv)>=thr))
        selected=[]
        for j in cand:
            if not selected or t[j]-t[selected[-1]]>=min_response_distance_s: selected.append(j)
            elif abs(deriv[j])>abs(deriv[selected[-1]]): selected[-1]=j
        flag=np.zeros(len(idx),bool); flag[selected]=True
        for n,j in enumerate(selected,1): responses.append({"group_id":gid,"response_index":n,"row_index":int(idx[j])+1,"response_time":float(t[j]),"skin_potential":float(sp[j]),"centered_skin_potential":float(centered[j]),"derivative":float(deriv[j]),"response_polarity":"positive" if deriv[j]>0 else ("negative" if deriv[j]<0 else "zero")})
        times.append(pd.DataFrame({"row_index":idx+1,"group_id":gid,"time":t,"skin_potential":sp,"centered_skin_potential":centered,"skin_potential_derivative":deriv,"skin_potential_response":flag})); duration=(np.nanmax(t)-np.nanmin(t)) if finite.any() else np.nan; rate=len(selected)/(duration/60) if np.isfinite(duration) and duration>0 else np.nan; levels.append({"group_id":gid,"n_rows":len(idx),"n_finite":int(finite.sum()),"mean_spl":float(np.mean(sp[finite])) if finite.any() else np.nan,"median_spl":float(np.median(sp[finite])) if finite.any() else np.nan,"sd_spl":r_sd(sp[finite]),"min_spl":float(np.min(sp[finite])) if finite.any() else np.nan,"max_spl":float(np.max(sp[finite])) if finite.any() else np.nan,"response_count":len(selected),"response_rate_per_min":rate,"threshold_used":thr,"status":"skin_potential_analysed" if finite.any() else "no_valid_skin_potential"})
    lv=pd.DataFrame(levels); rt=pd.DataFrame(responses); ts=pd.concat(times,ignore_index=True); ok=lv.status.eq("skin_potential_analysed"); status="skin_potential_analysis_complete" if ok.all() else ("skin_potential_analysis_partial" if ok.any() else "skin_potential_analysis_failed"); return {"overview":pd.DataFrame([{"group_count":len(lv),"timeseries_rows":len(ts),"response_rows":len(rt),"successful_groups":int(ok.sum()),"problem_groups":int((~ok).sum()),"status":status}]),"level_summary":lv,"response_table":rt,"timeseries":ts,"settings":{"sp_col":sp_col,"time_col":time_col,"group_cols":as_list(group_cols),"response_direction":response_direction,"response_threshold":response_threshold,"min_response_distance_s":min_response_distance_s},"class":["gazepoint_skin_potential_analysis","list"]}
