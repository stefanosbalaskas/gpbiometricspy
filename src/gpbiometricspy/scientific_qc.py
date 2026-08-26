from __future__ import annotations
import numpy as np
import pandas as pd


def _groups(df, cols):
    if cols is None or cols == []: return {"all": np.arange(len(df))}
    if isinstance(cols,str): cols=[cols]
    miss=[c for c in cols if c not in df]
    if miss: raise ValueError("not found: "+", ".join(miss))
    out={};grouper=cols[0] if len(cols)==1 else cols
    for key,z in df.groupby(grouper,sort=True,dropna=False):
        label=" | ".join(map(str,key)) if isinstance(key,tuple) else str(key);out[label]=z.index.to_numpy()
    return out


def _ibi_col(df, col):
    if col is not None:
        if col not in df: raise ValueError("ibi_col not found")
        return col
    for c in df.columns:
        s=str(c).upper()
        if s in {"IBI","RR","RRI","RR_INTERVAL","IBI_MS","RR_MS","IBI_CLEAN_MS"}: return c
    raise ValueError("No IBI/RR interval column was detected. Provide `ibi_col` explicitly.")


def _ibi_metrics(v):
    v=np.asarray(v,float);v=v[np.isfinite(v)&(v>0)];hr=60000/v if len(v) else np.array([]);d=np.diff(v)
    return dict(mean_ibi_ms=np.mean(v) if len(v) else np.nan,median_ibi_ms=np.median(v) if len(v) else np.nan,min_ibi_ms=np.min(v) if len(v) else np.nan,max_ibi_ms=np.max(v) if len(v) else np.nan,mean_hr_bpm=np.mean(hr) if len(hr) else np.nan,median_hr_bpm=np.median(hr) if len(hr) else np.nan,min_hr_bpm=np.min(hr) if len(hr) else np.nan,max_hr_bpm=np.max(hr) if len(hr) else np.nan,sdnn_ms=np.std(v,ddof=1) if len(v)>1 else np.nan,rmssd_ms=np.sqrt(np.mean(d*d)) if len(d) else np.nan,pnn20=np.mean(np.abs(d)>20) if len(d) else np.nan,pnn50=np.mean(np.abs(d)>50) if len(d) else np.nan)


def audit_gazepoint_ibi_quality(data, ibi_col=None, group_cols=None, time_col=None, unit="auto", min_ibi_ms=300, max_ibi_ms=2000, max_jump_ms=500):
    if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame.")
    if min_ibi_ms<=0: raise ValueError("`min_ibi_ms` must be a positive number.")
    if max_ibi_ms<=0 or max_jump_ms<=0: raise ValueError("thresholds must be positive")
    if min_ibi_ms>=max_ibi_ms: raise ValueError("`min_ibi_ms` must be smaller than `max_ibi_ms`.")
    if time_col is not None and time_col not in data: raise ValueError("time_col not found")
    c=_ibi_col(data,ibi_col)
    if not pd.api.types.is_numeric_dtype(data[c]): raise TypeError("The selected IBI/RR interval column must be numeric.")
    raw=data[c].to_numpy(float);finite=raw[np.isfinite(raw)&(raw>0)]
    resolved="seconds" if unit=="auto" and len(finite) and np.median(finite)<10 else ("milliseconds" if unit=="auto" else unit)
    ms=raw*1000 if resolved=="seconds" else raw.copy();n=len(data)
    s=pd.DataFrame({'row_id':np.arange(1,n+1),'group':'all','ibi_raw':raw,'ibi_ms':ms})
    s['missing_ibi']=np.isnan(raw);s['nonfinite_ibi']=(~np.isnan(raw))&(~np.isfinite(raw));s['nonpositive_ibi']=np.isfinite(ms)&(ms<=0);s['below_min_ibi']=np.isfinite(ms)&(ms>0)&(ms<min_ibi_ms);s['above_max_ibi']=np.isfinite(ms)&(ms>max_ibi_ms);s['large_jump_ibi']=False
    for g,idx in _groups(data,group_cols).items():
        s.loc[idx,'group']=g;ordidx=np.asarray(idx)
        if time_col is not None: ordidx=ordidx[np.argsort(pd.to_numeric(data.loc[ordidx,time_col],errors='coerce').to_numpy(),kind='stable')]
        vals=ms[ordidx]
        for j in range(1,len(ordidx)):
            if np.isfinite(vals[j]) and vals[j]>0 and np.isfinite(vals[j-1]) and vals[j-1]>0 and abs(vals[j]-vals[j-1])>max_jump_ms:s.loc[ordidx[j],'large_jump_ibi']=True
    s['valid_ibi']=~(s.missing_ibi|s.nonfinite_ibi|s.nonpositive_ibi|s.below_min_ibi|s.above_max_ibi);s['any_quality_flag']=~s.valid_ibi|s.large_jump_ibi
    def status(r):
        for col,name in [('missing_ibi','missing_ibi'),('nonfinite_ibi','nonfinite_ibi'),('nonpositive_ibi','nonpositive_ibi'),('below_min_ibi','below_min_ibi'),('above_max_ibi','above_max_ibi'),('large_jump_ibi','large_jump_ibi')]:
            if r[col]: return name
        return 'valid_ibi'
    s['status']=s.apply(status,axis=1)
    gr=[]
    for g,z in s.groupby('group',sort=True):
        v=z.loc[z.valid_ibi,'ibi_ms'].to_numpy();m=_ibi_metrics(v);gr.append({'group':g,'n_rows':len(z),'n_valid_ibi':len(v),'valid_ibi_rate':len(v)/len(z) if len(z) else np.nan,'n_quality_flagged':int(z.any_quality_flag.sum()),'quality_flag_rate':float(z.any_quality_flag.mean()) if len(z) else np.nan,'mean_ibi_ms':m['mean_ibi_ms'],'median_ibi_ms':m['median_ibi_ms'],'mean_hr_bpm':m['mean_hr_bpm'],'sdnn_ms':m['sdnn_ms'],'rmssd_ms':m['rmssd_ms'],'pnn50':m['pnn50'],'status':'sufficient_ibi' if len(v)>=2 else 'insufficient_ibi'})
    nvalid=int(s.valid_ibi.sum());nflag=int(s.any_quality_flag.sum())
    ov=pd.DataFrame([{'n_rows':n,'ibi_column':c,'unit':resolved,'group_column_count':0 if group_cols is None else (1 if isinstance(group_cols,str) else len(group_cols)),'n_missing_ibi':int(s.missing_ibi.sum()),'n_nonfinite_ibi':int(s.nonfinite_ibi.sum()),'n_nonpositive_ibi':int(s.nonpositive_ibi.sum()),'n_below_min_ibi':int(s.below_min_ibi.sum()),'n_above_max_ibi':int(s.above_max_ibi.sum()),'n_large_jump_ibi':int(s.large_jump_ibi.sum()),'n_valid_ibi':nvalid,'valid_ibi_rate':nvalid/n if n else np.nan,'n_quality_flagged':nflag,'quality_flag_rate':nflag/n if n else np.nan,'status':'no_valid_ibi_intervals' if nvalid==0 else ('ibi_quality_issues_detected' if nflag else 'ibi_quality_ok')}])
    return {'overview':ov,'samples':s,'group_summary':pd.DataFrame(gr),'settings':{'ibi_col':c,'group_cols':group_cols,'time_col':time_col,'unit':unit,'resolved_unit':resolved,'min_ibi_ms':min_ibi_ms,'max_ibi_ms':max_ibi_ms,'max_jump_ms':max_jump_ms,'note':'IBI quality and HRV-style summaries are based only on the selected IBI/RR interval column, not on raw HRV validity/vendor columns.'}}


def summarise_gazepoint_ibi_windows(data, ibi_col=None, group_cols=None, time_col=None, unit="auto", min_ibi_ms=300, max_ibi_ms=2000, max_jump_ms=500, exclude_large_jumps=True, min_valid_ibi=2):
    if not isinstance(exclude_large_jumps,(bool,np.bool_)): raise ValueError("`exclude_large_jumps` must be TRUE or FALSE.")
    if int(min_valid_ibi)<1: raise ValueError("`min_valid_ibi` must be a positive integer.")
    a=audit_gazepoint_ibi_quality(data,ibi_col,group_cols,time_col,unit,min_ibi_ms,max_ibi_ms,max_jump_ms);s=a['samples'].copy();s['analysis_valid_ibi']=s.valid_ibi & (~s.large_jump_ibi if exclude_large_jumps else True);rows=[]
    for g,z in s.groupby('group',sort=True):
        v=z.loc[z.analysis_valid_ibi,'ibi_ms'].to_numpy();m=_ibi_metrics(v);rows.append({'group':g,'n_rows':len(z),'n_ibi':int((~z.missing_ibi).sum()),'n_valid_ibi':len(v),'valid_ibi_rate':len(v)/len(z) if len(z) else np.nan,'n_excluded_for_quality':int((~z.analysis_valid_ibi).sum()),'duration_s':np.sum(v)/1000 if len(v) else np.nan,**m,'status':'sufficient_ibi_window' if len(v)>=min_valid_ibi else 'insufficient_ibi_window'})
    w=pd.DataFrame(rows);ns=int((w.status=='sufficient_ibi_window').sum()) if len(w) else 0;ov=pd.DataFrame([{'n_rows':len(data),'ibi_column':a['overview'].loc[0,'ibi_column'],'unit':a['overview'].loc[0,'unit'],'window_count':len(w),'sufficient_window_count':ns,'insufficient_window_count':len(w)-ns,'exclude_large_jumps':exclude_large_jumps,'min_valid_ibi':int(min_valid_ibi),'status':'no_ibi_windows' if len(w)==0 else ('no_sufficient_ibi_windows' if ns==0 else ('some_ibi_windows_insufficient' if ns<len(w) else 'ibi_windows_summarised'))}]);return {'overview':ov,'windows':w,'samples':s,'settings':{'ibi_col':a['overview'].loc[0,'ibi_column'],'group_cols':group_cols,'time_col':time_col,'unit':unit,'resolved_unit':a['overview'].loc[0,'unit'],'min_ibi_ms':min_ibi_ms,'max_ibi_ms':max_ibi_ms,'max_jump_ms':max_jump_ms,'exclude_large_jumps':exclude_large_jumps,'min_valid_ibi':int(min_valid_ibi),'note':'Window summaries are derived from genuine IBI/RR intervals only. They are not calculated from raw HRV validity/vendor columns.'}}


def classify_gazepoint_scr_intervals(dat,response_time_col=None,stimulus_onset_col=None,latency_col=None,output_col='scr_interval',latency_output_col='scr_latency_s',fir=(1,4),sir=(4,7),tir=(7,10)):
    if not isinstance(dat,pd.DataFrame): raise TypeError("`dat` must be a data frame.")
    for name,w in [('fir',fir),('sir',sir),('tir',tir)]:
        if len(w)!=2 or not np.all(np.isfinite(w)) or w[0]>=w[1]:raise ValueError(f"`{name}` must be a numeric vector of length two with start < end.")
    if latency_col is not None:
        if latency_col not in dat:raise ValueError(f"Column `{latency_col}` was not found in `dat`.")
        lat=pd.to_numeric(dat[latency_col],errors='coerce').to_numpy()
    else:
        if response_time_col is None or stimulus_onset_col is None:raise ValueError("Supply either `latency_col` or both `response_time_col` and `stimulus_onset_col`.")
        if response_time_col not in dat or stimulus_onset_col not in dat:raise ValueError("Column was not found in `dat`.")
        lat=(pd.to_numeric(dat[response_time_col],errors='coerce')-pd.to_numeric(dat[stimulus_onset_col],errors='coerce')).to_numpy()
    out=dat.copy();lab=np.full(len(out),'outside_defined_intervals',dtype=object);lab[~np.isfinite(lat)]='missing_latency';lab[np.isfinite(lat)&(lat>=fir[0])&(lat<fir[1])]='FIR';lab[np.isfinite(lat)&(lat>=sir[0])&(lat<sir[1])]='SIR';lab[np.isfinite(lat)&(lat>=tir[0])&(lat<=tir[1])]='TIR';out[latency_output_col]=lat;out[output_col]=lab
    out.attrs['scr_interval_summary']=pd.DataFrame([{'input_rows':len(out),'fir_rows':int((lab=='FIR').sum()),'sir_rows':int((lab=='SIR').sum()),'tir_rows':int((lab=='TIR').sum()),'outside_rows':int((lab=='outside_defined_intervals').sum()),'missing_latency_rows':int((lab=='missing_latency').sum()),'fir_window':f'{fir[0]}-{fir[1]}','sir_window':f'{sir[0]}-{sir[1]}','tir_window':f'{tir[0]}-{tir[1]}','status':'scr_intervals_classified'}]);return out


def flag_kleckner_eda_artifacts(dat,eda_col='GSR_US',time_col=None,group_cols=None,min_us=.01,max_us=100,max_abs_percent_change_per_second=20,transition_padding=1,output_prefix='kleckner'):
    if not isinstance(dat,pd.DataFrame):raise TypeError("`dat` must be a data frame.")
    if eda_col not in dat:raise ValueError(f"Column `{eda_col}` was not found in `dat`.")
    if not pd.api.types.is_numeric_dtype(dat[eda_col]):raise TypeError("`eda_col` must identify a numeric conductance column.")
    if transition_padding<0:raise ValueError("`transition_padding` must be a non-negative number.")
    out=dat.copy();cols={k:f'{output_prefix}_{v}' for k,v in [('nonfinite','nonfinite'),('range','range_artifact'),('rapid','rapid_change_artifact'),('transition','transition_artifact'),('final','artifact'),('status','artifact_status')]}
    for k in ['nonfinite','range','rapid','transition','final']:out[cols[k]]=False
    out[cols['status']]='usable'
    for _,idx in _groups(out,group_cols).items():
        x=out.loc[idx,eda_col].to_numpy(float);non=~np.isfinite(x);rang=np.isfinite(x)&((x<min_us)|(x>max_us));rapid=np.zeros(len(idx),bool)
        if len(idx)>=2:
            dx=np.diff(x);dt=np.ones(len(dx)) if time_col is None else np.diff(pd.to_numeric(out.loc[idx,time_col],errors='coerce').to_numpy(float));dt[(~np.isfinite(dt))|(dt<=0)]=np.nan;prev=x[:-1];pct=np.abs((dx/prev)*100)/dt;rapid[1:]=np.isfinite(pct)&(pct>max_abs_percent_change_per_second)
        primary=non|rang|rapid;trans=primary.copy()
        if transition_padding>0 and primary.any():
            for i in np.where(primary)[0]:trans[max(0,i-transition_padding):min(len(trans),i+transition_padding+1)]=True
        trans=trans&~primary;final=primary|trans
        for arr,k in [(non,'nonfinite'),(rang,'range'),(rapid,'rapid'),(trans,'transition'),(final,'final')]:out.loc[idx,cols[k]]=arr
    out.loc[out[cols['transition']],cols['status']]='transition_artifact';out.loc[out[cols['rapid']],cols['status']]='rapid_change_artifact';out.loc[out[cols['range']],cols['status']]='range_artifact';out.loc[out[cols['nonfinite']],cols['status']]='nonfinite_artifact'
    out.attrs['kleckner_artifact_summary']=pd.DataFrame([{'input_rows':len(out),'artifact_rows':int(out[cols['final']].sum()),'artifact_rate':float(out[cols['final']].mean()),'nonfinite_rows':int(out[cols['nonfinite']].sum()),'range_artifact_rows':int(out[cols['range']].sum()),'rapid_change_artifact_rows':int(out[cols['rapid']].sum()),'transition_artifact_rows':int(out[cols['transition']].sum()),'min_us':min_us,'max_us':max_us,'max_abs_percent_change_per_second':max_abs_percent_change_per_second,'transition_padding':int(transition_padding),'status':'kleckner_style_artifacts_flagged'}]);return out


def convert_gazepoint_gsr_to_conductance(data,gsr_col=None,output_col='GSR_US',input_unit='auto',overwrite=False):
    if not isinstance(data,pd.DataFrame):raise TypeError("`data` must be a data frame.")
    if not output_col:raise ValueError("`output_col` must be a non-empty character string.")
    out=data.copy()
    if output_col in out and not overwrite:
        out.attrs['gsr_conversion_summary']=pd.DataFrame([{'status':'conductance_column_already_present','source_column':np.nan,'output_column':output_col,'input_unit':input_unit,'n':len(out),'n_converted':int(out[output_col].notna().sum()),'n_invalid':0}]);return out
    source=gsr_col
    if source is None:
        source=next((c for c in out.columns if 'ohm' in str(c).lower() or 'resistance' in str(c).lower()),None)
    if source is None:
        out.attrs['gsr_conversion_summary']=pd.DataFrame([{'status':'no_resistance_source_detected','source_column':np.nan,'output_column':output_col,'input_unit':input_unit,'n':len(out),'n_converted':0,'n_invalid':0}]);return out
    if source not in out:raise ValueError("gsr_col not found")
    if not pd.api.types.is_numeric_dtype(out[source]):raise TypeError("The selected GSR source column must be numeric.")
    resolved=input_unit
    if input_unit=='auto':
        sl=str(source).lower();resolved='ohms' if ('ohm' in sl or 'resistance' in sl) else ('microsiemens' if 'us' in sl or 'microsiemens' in sl else 'unknown')
    if resolved=='unknown':out.attrs['gsr_conversion_summary']=pd.DataFrame([{'status':'unit_not_confirmed','source_column':source,'output_column':output_col,'input_unit':input_unit,'n':len(out),'n_converted':0,'n_invalid':0}]);return out
    v=out[source].to_numpy(float);conv=np.full(len(v),np.nan);invalid=np.zeros(len(v),bool)
    if resolved in {'ohms','kohms'}:
        valid=np.isfinite(v)&(v>0);invalid=(~np.isnan(v))&((~np.isfinite(v))|(v<=0));conv[valid]=(1_000_000 if resolved=='ohms' else 1000)/v[valid]
    else:
        valid=np.isfinite(v);invalid=(~np.isnan(v))&(~np.isfinite(v));conv[valid]=v[valid]
    out[output_col]=conv;out.attrs['gsr_conversion_summary']=pd.DataFrame([{'status':'conductance_created','source_column':source,'output_column':output_col,'input_unit':resolved,'n':len(out),'n_converted':int(np.isfinite(conv).sum()),'n_invalid':int(invalid.sum())}]);return out


def summarise_gazepoint_gsr_tonic_phasic(data,gsr_col=None,group_cols=None,time_col=None,window_n=15,peak_threshold=None,output_prefix='gsr'):
    if not isinstance(data,pd.DataFrame):raise TypeError("`data` must be a data frame.")
    if int(window_n)<1:raise ValueError("`window_n` must be positive")
    if peak_threshold is not None and not isinstance(peak_threshold,(int,float,np.number)):raise ValueError("`peak_threshold` must be NULL or a single numeric value.")
    if not output_prefix:raise ValueError("`output_prefix` must be a non-empty character string.")
    if gsr_col is None:gsr_col=next((c for c in ['GSR_US','GSR','EDA'] if c in data),None)
    if gsr_col is None:raise ValueError("No GSR/EDA column was detected. Provide `gsr_col` explicitly.")
    if gsr_col not in data:raise ValueError("gsr_col not found")
    if not pd.api.types.is_numeric_dtype(data[gsr_col]):raise TypeError("The selected GSR/EDA column must be numeric.")
    out=data.copy();tc=f'{output_prefix}_tonic';pc=f'{output_prefix}_phasic';pkc=f'{output_prefix}_phasic_peak';thc=f'{output_prefix}_phasic_peak_threshold';out[tc]=np.nan;out[pc]=np.nan;out[pkc]=False;out[thc]=np.nan;summary=[]
    for g,idx in _groups(out,group_cols).items():
        ordidx=np.asarray(idx)
        if time_col is not None:ordidx=ordidx[np.argsort(pd.to_numeric(out.loc[ordidx,time_col],errors='coerce').to_numpy(),kind='stable')]
        x=out.loc[ordidx,gsr_col].to_numpy(float);h=int(window_n)//2;ton=np.array([np.nanmedian(x[max(0,i-h):min(len(x),i+h+1)][np.isfinite(x[max(0,i-h):min(len(x),i+h+1)])]) if np.isfinite(x[max(0,i-h):min(len(x),i+h+1)]).any() else np.nan for i in range(len(x))]);ph=x-ton
        th=peak_threshold
        if th is None:
            f=ph[np.isfinite(ph)]
            if len(f)==0:th=np.nan
            else:
                med=np.median(f);mad=1.4826*np.median(np.abs(f-med));sc=mad if np.isfinite(mad) and mad>0 else np.std(f,ddof=1)
                th=med+2*sc if np.isfinite(sc) and sc>0 else np.inf
        peaks=np.zeros(len(x),bool)
        if np.isfinite(th):
            for i,v in enumerate(ph):
                if not np.isfinite(v) or v<=th:continue
                l=(i==0 or not np.isfinite(ph[i-1]) or v>=ph[i-1]);r=(i==len(ph)-1 or not np.isfinite(ph[i+1]) or v>=ph[i+1]);peaks[i]=l and r
        out.loc[ordidx,tc]=ton;out.loc[ordidx,pc]=ph;out.loc[ordidx,pkc]=peaks;out.loc[ordidx,thc]=th
        fs=x[np.isfinite(x)];ft=ton[np.isfinite(ton)];fp=ph[np.isfinite(ph)];pos=fp[fp>0];summary.append({'group':g,'n_rows':len(x),'source_column':gsr_col,'n_signal_finite':len(fs),'mean_signal':np.mean(fs) if len(fs) else np.nan,'median_signal':np.median(fs) if len(fs) else np.nan,'mean_tonic':np.mean(ft) if len(ft) else np.nan,'median_tonic':np.median(ft) if len(ft) else np.nan,'mean_phasic':np.mean(fp) if len(fp) else np.nan,'median_phasic':np.median(fp) if len(fp) else np.nan,'max_phasic':np.max(fp) if len(fp) else np.nan,'min_phasic':np.min(fp) if len(fp) else np.nan,'positive_phasic_sum':np.sum(pos) if len(pos) else 0,'n_phasic_peaks':int(peaks.sum()),'peak_threshold':th})
    return {'data':out,'summary':pd.DataFrame(summary),'settings':{'gsr_col':gsr_col,'group_cols':group_cols,'time_col':time_col,'window_n':int(window_n),'peak_threshold':peak_threshold,'output_prefix':output_prefix,'tonic_col':tc,'phasic_col':pc,'peak_col':pkc,'threshold_col':thc,'note':'This is a descriptive rolling-median tonic/phasic decomposition, not a full EDA deconvolution model.'}}
