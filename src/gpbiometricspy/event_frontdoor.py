from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .compatibility import standardize_gazepoint_column_names


def _time_seconds(x):
    arr=pd.to_numeric(pd.Series(x),errors='coerce').to_numpy(float)
    finite=arr[np.isfinite(arr)]
    if len(finite)<2:return arr
    d=np.diff(finite); d=d[np.isfinite(d)&(d>0)]
    return arr/1000 if len(d) and np.median(d)>5 else arr


def _guess(df,cands,label,required=True):
    low={str(c).lower():c for c in df.columns}
    for c in cands:
        if c.lower() in low:return low[c.lower()]
    if required: raise ValueError(f"Could not identify {label} column. Supply it explicitly.")
    return None


def _groups(df,cols=None):
    cols=[] if cols is None else ([cols] if isinstance(cols,str) else list(cols))
    miss=[c for c in cols if c not in df.columns]
    if miss:raise ValueError(f"Missing grouping columns: {', '.join(miss)}")
    if not cols:return [('all',np.arange(len(df),dtype=int))]
    keys=df[cols].astype(str).agg(' | '.join,axis=1).to_numpy()
    return [(k,np.flatnonzero(keys==k)) for k in dict.fromkeys(keys.tolist())]


def _standard_events(events,event_time_col=None,event_id_col=None,event_group_cols=None):
    if isinstance(events,(list,tuple,np.ndarray,pd.Series)) and not isinstance(events,pd.DataFrame):
        arr=pd.to_numeric(pd.Series(events),errors='coerce').to_numpy(float)
        return pd.DataFrame({'event_id':np.arange(1,len(arr)+1),'event_time':arr})
    if not isinstance(events,pd.DataFrame) or len(events)==0:raise TypeError('`events` must be a numeric vector of timestamps or a data frame.')
    if event_time_col is None:event_time_col=_guess(events,['event_time','time_s','time','timestamp','onset','onset_time','trial_onset','stimulus_onset'],'event time')
    out=events.copy(); out['event_time']=pd.to_numeric(out[event_time_col],errors='coerce')
    if event_id_col is None:event_id_col=_guess(events,['event_id','trial','trial_id','stimulus','condition'],'event id',False)
    if event_id_col is not None and event_id_col in out.columns: out['event_id']=out[event_id_col]
    else: out['event_id']=np.arange(1,len(out)+1)
    keep=['event_id','event_time']; egs=[] if event_group_cols is None else ([event_group_cols] if isinstance(event_group_cols,str) else list(event_group_cols))
    miss=[c for c in egs if c not in out.columns]
    if miss:raise ValueError(f"Missing event grouping columns: {', '.join(miss)}")
    return out[list(dict.fromkeys(keep+egs))]


def _scr_peaks(time,signal,min_amplitude=.01,min_distance_s=1,latency_min_s=0,latency_max_s=np.inf):
    t=np.asarray(time,float); y=np.asarray(signal,float); ok=np.isfinite(t)&np.isfinite(y)
    if ok.sum()<3:return pd.DataFrame(columns=['scr_peak_time','scr_trough_time','scr_amplitude','scr_peak_value','scr_trough_value'])
    t=t[ok]; y=y[ok]; o=np.argsort(t); t=t[o]; y=y[o]
    local=np.flatnonzero((y[1:-1]>y[:-2])&(y[2:]<=y[1:-1]))+1
    local=local[(t[local]>=latency_min_s)&(t[local]<=latency_max_s)]
    rows=[]; last=-np.inf
    for ii in local:
        if t[ii]-last<min_distance_s:continue
        before=np.arange(ii)
        if len(before)==0:continue
        tr=before[np.argmin(y[before])]; amp=y[ii]-y[tr]
        if not np.isfinite(amp) or amp<min_amplitude:continue
        rows.append({'scr_peak_time':t[ii],'scr_trough_time':t[tr],'scr_amplitude':amp,'scr_peak_value':y[ii],'scr_trough_value':y[tr]}); last=t[ii]
    return pd.DataFrame(rows)


def epoch_gazepoint_scr(data,events,pre,post,time_col=None,signal_col=None,event_time_col=None,event_id_col=None,event_group_cols=None,baseline_window=None,response_window=None,min_amplitude=.01,min_distance_s=1):
    if not isinstance(data,pd.DataFrame) or len(data)==0:raise TypeError('`data` must be a data frame.')
    if pre<0 or post<=0:raise ValueError('`pre` must be non-negative and `post` must be positive.')
    time_col=time_col or _guess(data,['time_s','time','TIME','timestamp','MSTIMER'],'time')
    signal_col=signal_col or _guess(data,['GSR','EDA','SCR','eda','gsr','skin_conductance','conductance'],'EDA/GSR signal')
    ev=_standard_events(events,event_time_col,event_id_col,event_group_cols)
    t=_time_seconds(data[time_col]); sig=pd.to_numeric(data[signal_col],errors='coerce').to_numpy(float)
    baseline_window=[-pre,0] if baseline_window is None else baseline_window; response_window=[0,post] if response_window is None else response_window
    rows=[]; egs=[] if event_group_cols is None else ([event_group_cols] if isinstance(event_group_cols,str) else list(event_group_cols))
    for _,e in ev.iterrows():
        et=float(e['event_time']); rel=t-et; idx=np.flatnonzero((rel>=-pre)&(rel<=post))
        base={c:e[c] for c in egs}
        if len(idx)==0:
            base.update({'event_id':e['event_id'],'event_time':et,'n_samples':0,'baseline_mean':np.nan,'epoch_mean':np.nan,'response_mean':np.nan,'response_auc':np.nan,'scr_count':0,'scr_max_amplitude':np.nan,'scr_mean_amplitude':np.nan,'scr_total_amplitude':0.0,'first_scr_latency_s':np.nan}); rows.append(base); continue
        re=rel[idx]; se=sig[idx]; bi=(re>=baseline_window[0])&(re<=baseline_window[1]); ri=(re>=response_window[0])&(re<=response_window[1])
        bm=np.nanmean(se[bi]) if bi.any() else np.nan; sbc=se-bm; peaks=_scr_peaks(re[ri],sbc[ri],min_amplitude,min_distance_s,response_window[0],response_window[1])
        auc=np.nan
        if ri.sum()>=2:
            tr=re[ri]; yr=sbc[ri]; o=np.argsort(tr); auc=float(np.nansum(np.diff(tr[o])*(yr[o][:-1]+yr[o][1:])/2))
        base.update({'event_id':e['event_id'],'event_time':et,'n_samples':len(idx),'baseline_mean':bm,'epoch_mean':float(np.nanmean(sbc)),'response_mean':float(np.nanmean(sbc[ri])) if ri.any() else np.nan,'response_auc':auc,'scr_count':len(peaks),'scr_max_amplitude':peaks['scr_amplitude'].max() if len(peaks) else np.nan,'scr_mean_amplitude':peaks['scr_amplitude'].mean() if len(peaks) else np.nan,'scr_total_amplitude':peaks['scr_amplitude'].sum() if len(peaks) else 0.0,'first_scr_latency_s':peaks['scr_peak_time'].min() if len(peaks) else np.nan}); rows.append(base)
    out=pd.DataFrame(rows); out.attrs.update({'time_col':time_col,'signal_col':signal_col,'pre':pre,'post':post,'baseline_window':baseline_window,'response_window':response_window}); return out


def _normalize(x,method,na_rm=True):
    a=pd.to_numeric(pd.Series(x),errors='coerce').to_numpy(float)
    if method=='none':return a
    z=np.log1p(np.maximum(a,0)) if method=='log_z' else a
    if method in {'z','log_z'}:
        mu=np.nanmean(z); sd=np.nanstd(z,ddof=1); return np.zeros(len(a)) if not np.isfinite(sd) or sd==0 else (z-mu)/sd
    if method=='center':return a-np.nanmean(a)
    if method=='percent_max':
        mx=np.nanmax(a); return np.zeros(len(a)) if not np.isfinite(mx) or mx==0 else 100*a/mx
    mn,mx=np.nanmin(a),np.nanmax(a); return np.zeros(len(a)) if not np.isfinite(mx-mn) or mx==mn else (a-mn)/(mx-mn)


def normalize_gazepoint_scr(amplitudes,method='z',amplitude_col=None,group_cols=None,output_col='scr_amplitude_normalized',na_rm=True):
    if method not in {'z','percent_max','range','center','log_z','none'}:raise ValueError('Invalid normalization method.')
    if not isinstance(amplitudes,pd.DataFrame):return _normalize(amplitudes,method,na_rm)
    out=amplitudes.copy(); amplitude_col=amplitude_col or _guess(out,['scr_amplitude','amplitude','SCR','SCR_Amplitude','response_amplitude'],'SCR amplitude')
    out[output_col]=np.nan
    for _,idx in _groups(out,group_cols):out.loc[idx,output_col]=_normalize(out.loc[idx,amplitude_col],method,na_rm)
    out.attrs['normalization_method']=method; out.attrs['amplitude_col']=amplitude_col; return out


def flag_gazepoint_rr_outliers(rr_intervals,method='mad',z_threshold=5,mad_threshold=5,min_rr=300,max_rr=2000,return_='flags',**kwargs):
    if 'return' in kwargs:return_=kwargs['return']
    rr=pd.to_numeric(pd.Series(rr_intervals),errors='coerce').to_numpy(float); missing=~np.isfinite(rr); range_bad=np.isfinite(rr)&((rr<min_rr)|(rr>max_rr)); flags=missing|range_bad
    ok=np.isfinite(rr)&~range_bad
    if method!='range' and ok.sum()>=3:
        if method=='z':
            sd=np.std(rr[ok],ddof=1); stat=np.zeros(len(rr),bool) if not np.isfinite(sd) or sd==0 else np.abs((rr-np.mean(rr[ok]))/sd)>z_threshold
        else:
            med=np.median(rr[ok]); mad=np.median(np.abs(rr[ok]-med))*1.4826
            if not np.isfinite(mad) or mad==0: mad=(np.percentile(rr[ok],75)-np.percentile(rr[ok],25))/1.349
            stat=np.zeros(len(rr),bool) if not np.isfinite(mad) or mad==0 else np.abs(rr-med)>mad_threshold*mad
        stat[~np.isfinite(rr)]=False; flags|=stat
    filtered=rr.copy(); filtered[flags]=np.nan
    if return_=='flags':return flags
    if return_=='filtered':return filtered
    return pd.DataFrame({'index':np.arange(1,len(rr)+1),'rr_interval':rr,'rr_filtered':filtered,'is_missing':missing,'is_range_outlier':range_bad,'is_outlier':flags,'method':method})


def compute_gazepoint_engagement_index(dial,time=None,threshold=50,group=None,return_='data',**kwargs):
    if 'return' in kwargs:return_=kwargs['return']
    x=pd.to_numeric(pd.Series(dial),errors='coerce').to_numpy(float); tt=np.arange(1,len(x)+1,dtype=float) if time is None else _time_seconds(time)
    if len(tt)!=len(x):raise ValueError('`time` must have the same length as `dial`.')
    gr=np.array(['all']*len(x),object) if group is None else np.asarray(group)
    if len(gr)!=len(x):raise ValueError('`group` must have the same length as `dial`.')
    rows=[]
    for g in dict.fromkeys(gr.tolist()):
        idx=np.flatnonzero(gr==g); xx=x[idx]; t=tt[idx]; ok=np.isfinite(xx)&np.isfinite(t)
        if not ok.any():rows.append({'group':str(g),'n_samples':len(idx),'n_valid':0,'duration_s':np.nan,'mean_engagement':np.nan,'median_engagement':np.nan,'sd_engagement':np.nan,'min_engagement':np.nan,'max_engagement':np.nan,'percent_time_above_threshold':np.nan,'volatility':np.nan,'auc_engagement':np.nan});continue
        xx=xx[ok];t=t[ok];o=np.argsort(t);xx=xx[o];t=t[o]; duration=float(t.max()-t.min()) if len(t)>=2 else 0.0
        if len(t)>=2:
            dt=np.diff(t); valid=np.isfinite(dt)&(dt>=0); total=dt[valid].sum()
            if total>0: pct=100*dt[valid&(xx[:-1]>threshold)].sum()/total; auc=np.sum(dt[valid]*(xx[:-1][valid]+xx[1:][valid])/2); vol=np.mean(np.abs(np.diff(xx))[valid])
            else:pct=100*np.mean(xx>threshold);auc=np.nan;vol=np.std(xx,ddof=1)
        else:pct=100*np.mean(xx>threshold);auc=0.;vol=0.
        rows.append({'group':str(g),'n_samples':len(idx),'n_valid':len(xx),'duration_s':duration,'mean_engagement':np.mean(xx),'median_engagement':np.median(xx),'sd_engagement':np.std(xx,ddof=1) if len(xx)>1 else np.nan,'min_engagement':np.min(xx),'max_engagement':np.max(xx),'percent_time_above_threshold':pct,'volatility':vol,'auc_engagement':auc})
    out=pd.DataFrame(rows);out.attrs['threshold']=threshold
    if return_=='scalar':
        if len(out)!=1:raise ValueError("`return = 'scalar'` is only available when a single group is used.")
        return float(out.loc[0,'percent_time_above_threshold'])
    return out


def summarize_gazepoint_missingness(data,signal_cols=None,time_col=None,group_cols=None,long_gap_s=None,count_nonfinite=True):
    if not isinstance(data,pd.DataFrame) or len(data)==0:raise TypeError('`data` must be a data frame.')
    if time_col is None:time_col=_guess(data,['time_s','time','timestamp','TIME','TIME_TICK','MSTIMER','CNT'],'time',False)
    groups=[] if group_cols is None else ([group_cols] if isinstance(group_cols,str) else list(group_cols)); signals=([signal_cols] if isinstance(signal_cols,str) else list(signal_cols)) if signal_cols is not None else [c for c in data.columns if c not in [time_col,*groups]]
    rows=[]
    for g,idx in _groups(data,groups):
        z=data.iloc[idx]; ts=_time_seconds(z[time_col]) if time_col else None
        for sig in signals:
            vals=z[sig]; miss=vals.isna().to_numpy();
            if count_nonfinite and pd.api.types.is_numeric_dtype(vals):miss|=~np.isfinite(vals.to_numpy(float))
            runs=[];start=None
            med=np.median(np.diff(ts[np.isfinite(ts)])) if ts is not None and np.isfinite(ts).sum()>1 else np.nan
            for i,v in enumerate(np.r_[miss,False]):
                if v and start is None:start=i
                elif not v and start is not None:
                    dur=(max(0,ts[i-1]-ts[start])+med) if ts is not None and np.isfinite(ts[start]) and np.isfinite(ts[i-1]) and np.isfinite(med) else np.nan
                    runs.append((start,i-1,i-start,dur));start=None
            n=int(miss.sum()); longest=max([r[2] for r in runs],default=0); durations=[r[3] for r in runs if np.isfinite(r[3])]
            row={} if not groups else z.iloc[0][groups].to_dict();row.update({'signal':sig,'n_samples':len(vals),'n_missing':n,'missing_prop':n/len(vals),'n_missing_runs':len(runs),'longest_missing_run_samples':longest,'longest_missing_gap_s':max(durations) if durations else np.nan,'n_long_gaps':sum(d>=long_gap_s for d in durations) if long_gap_s is not None else np.nan,'first_missing_index':int(np.flatnonzero(miss)[0]+1) if n else np.nan,'last_missing_index':int(np.flatnonzero(miss)[-1]+1) if n else np.nan,'missing_burst_prop':longest/n if n else 0});rows.append(row)
    return pd.DataFrame(rows)


def detrend_gazepoint_signal(data,signal_col=None,time_col=None,group_cols=None,method='linear',span=.30,preserve_mean=False,suffix='_detrended'):
    vector=not isinstance(data,pd.DataFrame); df=pd.DataFrame({'sample_index':np.arange(1,len(data)+1),'signal':data}) if vector else data.copy(); signal_col='signal' if vector else signal_col; time_col='sample_index' if vector else time_col
    if signal_col is None:
        cand=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in [time_col,*([] if group_cols is None else ([group_cols] if isinstance(group_cols,str) else group_cols))]]; signal_col=cand[0] if cand else None
    if signal_col is None or signal_col not in df:raise ValueError('`signal_col` was not found in `data`.')
    if time_col is None:time_col=_guess(df,['time_s','time','timestamp','TIME','TIME_TICK','MSTIMER','CNT'],'time',False)
    y=pd.to_numeric(df[signal_col],errors='coerce').to_numpy(float);tt=_time_seconds(df[time_col]) if time_col else np.arange(1,len(y)+1,dtype=float);trend=np.full(len(y),np.nan);detr=np.full(len(y),np.nan)
    for _,idx in _groups(df,group_cols):
        yy=y[idx];t=tt[idx];ok=np.isfinite(yy)&np.isfinite(t); gt=np.full(len(idx),np.nan)
        if ok.any():
            if method=='none':gt[ok]=0
            elif method=='mean':gt[ok]=np.mean(yy[ok])
            elif method=='median':gt[ok]=np.median(yy[ok])
            elif method=='linear' and ok.sum()>=2 and len(np.unique(t[ok]))>=2:gt[ok]=np.polyval(np.polyfit(t[ok],yy[ok],1),t[ok])
            else:gt[ok]=np.mean(yy[ok])
            center=np.mean(gt[ok]) if preserve_mean else 0; gd=yy-gt+center;trend[idx]=gt;detr[idx]=gd
    df[f'{signal_col}_trend']=trend;df[f'{signal_col}{suffix}']=detr;df.attrs['gazepoint_detrend']={'signal_col':signal_col,'time_col':time_col,'group_cols':group_cols,'method':method,'span':span,'preserve_mean':preserve_mean,'trend_col':f'{signal_col}_trend','detrended_col':f'{signal_col}{suffix}'};return df

_MODALITIES={'time':['time_s','time','timestamp','MSTIMER','TIME','CNT'],'eda':['GSR','EDA','skin_conductance','conductance','GSR_US'],'ppg':['PPG','BVP','HRP','pulse','bvp','ppg'],'hr':['HR','heart_rate','heartrate','bpm'],'ibi':['IBI','RRI','RR','NN','ibi_ms','rr_ms'],'pupil':['pupil_left','pupil_right','LPD','RPD','LPMM','RPMM'],'gaze':['gaze_x','gaze_y','BPOGX','BPOGY','FPOGX','FPOGY','GPOGX','GPOGY'],'events':['TTL','TTL0','TTL1','marker','event_marker','event_id','event_time','USER','USER_DATA']}

def audit_gazepoint_biometrics_file(path=None,data=None,expected_modalities=('time','eda','ppg','hr','ibi','pupil','gaze','events'),time_col=None,standardize=True,include_data=False,long_gap_s=None):
    if data is None:
        if path is None:raise ValueError('Supply either `path` or `data`.')
        p=Path(path);sep={',':0,';':0,'\t':0};first=p.read_text(errors='replace').splitlines()[0]
        for k in sep:sep[k]=first.count(k)
        data=pd.read_csv(p,sep=max(sep,key=sep.get))
    if not isinstance(data,pd.DataFrame) or len(data)==0:raise TypeError('`data` must be a data frame.')
    original=list(data.columns); df=standardize_gazepoint_column_names(data) if standardize else data.copy(); auditmap=df.attrs.get('gazepoint_column_standardization',pd.DataFrame())
    time_col=time_col or _guess(df,['time_s','time','timestamp','TIME','TIME_TICK','MSTIMER','CNT'],'time',False)
    rows=[];low={c.lower():c for c in df.columns}
    for mod,aliases in _MODALITIES.items():
        hits=[low[a.lower()] for a in aliases if a.lower() in low];rows.append({'modality':mod,'present':bool(hits),'n_columns':len(hits),'columns':', '.join(dict.fromkeys(hits))})
    modalities=pd.DataFrame(rows);missingness=summarize_gazepoint_missingness(df,time_col=time_col,long_gap_s=long_gap_s)
    dup=df.duplicated();duplicate_rows=pd.DataFrame([{'n_rows':len(df),'n_duplicate_rows':int(dup.sum()),'duplicate_prop':float(dup.mean()),'first_duplicate_index':int(np.flatnonzero(dup)[0]+1) if dup.any() else np.nan}])
    missing=[m for m in expected_modalities if m not in modalities.loc[modalities.present,'modality'].tolist()];warnings=[]
    if missing:warnings.append(f"Missing expected modalities: {', '.join(missing)}.")
    if dup.any():warnings.append(f"Detected {int(dup.sum())} duplicated rows.")
    if (missingness['missing_prop']>.2).any():warnings.append('At least one column has more than 20% missing values.')
    out={'input':{'path':path,'source':'data' if path is None else 'path','standardized':bool(standardize),'time_col':time_col},'dimensions':pd.DataFrame([{'n_rows':len(df),'n_cols':df.shape[1]}]),'original_columns':original,'current_columns':list(df.columns),'modalities':modalities,'schema':modalities.copy(),'missingness':missingness,'timestamp_diagnostics':pd.DataFrame([{'available':bool(time_col),'reason':'' if time_col else 'No time column detected.'}]),'duplicate_rows':duplicate_rows,'column_standardization':auditmap,'warnings':warnings}
    if include_data:out['data']=df
    return out
