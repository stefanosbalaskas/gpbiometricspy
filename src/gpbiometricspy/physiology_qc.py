from __future__ import annotations

from itertools import combinations
import numpy as np
import pandas as pd
from scipy import signal

from ._helpers import as_list, ensure_df, group_indices, guess_col, r_sd, time_seconds, trapz


def _interval_to_ms(rr):
    arr=pd.to_numeric(pd.Series(rr),errors='coerce').to_numpy(float)
    finite=arr[np.isfinite(arr)]
    if finite.size and np.nanmedian(finite)<10: arr=arr*1000
    return arr


def flag_gazepoint_hrv_segments(data, rr_col=None, time_col=None, group_cols=None, window_s=60,
                                min_beats=20, min_duration_s=20, min_rr_ms=300, max_rr_ms=2000,
                                max_artifact_prop=0.20, max_successive_change_prop=0.20):
    if isinstance(data,(list,tuple,np.ndarray,pd.Series)) and not isinstance(data,pd.DataFrame):
        rr=_interval_to_ms(data); rr_s=rr/1000; t=np.cumsum(np.r_[0,rr_s[:-1]])
        df=pd.DataFrame({'segment_time_s':t,'rr':rr}); rr_col='rr'; time_col='segment_time_s'
    else:
        df=ensure_df(data).copy()
    rr_col=rr_col or guess_col(df,['rr','RR','RRI','NN','IBI','ibi','rr_ms','ibi_ms'],'RR/NN interval',True)
    if time_col is None: time_col=guess_col(df,['time_s','time','timestamp','segment_time_s','MSTIMER'],'time',False)
    rr_all=_interval_to_ms(df[rr_col])
    if time_col and time_col in df.columns: tt=time_seconds(df[time_col])
    else: tt=np.cumsum(np.r_[0,(rr_all/1000)[:-1]])
    df['_rr']=rr_all; df['_time']=tt; rows=[]
    for g,idx in group_indices(df,group_cols):
        z=df.loc[idx]; t=z['_time'].to_numpy(float); rr=z['_rr'].to_numpy(float); finite=t[np.isfinite(t)]
        if not finite.size: continue
        start=np.nanmin(finite); segid=np.ones(len(z),int) if window_s is None else np.floor((t-start)/window_s).astype(int)+1
        for seg in sorted(pd.unique(segid[np.isfinite(segid)])):
            loc=np.flatnonzero(segid==seg); r=rr[loc]; ts=t[loc]
            impl=(~np.isfinite(r))|(r<min_rr_ms)|(r>max_rr_ms); succ=np.zeros(len(r),bool)
            if len(r)>=2:
                ch=np.abs(r[1:]-r[:-1])/np.maximum(np.abs(r[:-1]),1); succ[1:]=np.isfinite(ch)&(ch>max_successive_change_prop)
            art=impl|succ; finite_r=r[np.isfinite(r)]; clean=r[(~art)&np.isfinite(r)]
            duration=float(np.nanmax(ts)-np.nanmin(ts)) if np.isfinite(ts).sum()>=2 else float(np.nansum(finite_r)/1000) if finite_r.size else np.nan
            ap=float(np.mean(art)) if len(r) else np.nan; reasons=[]
            if len(clean)<min_beats: reasons.append('too_few_clean_beats')
            if not np.isfinite(duration) or duration<min_duration_s: reasons.append('duration_too_short')
            if np.isfinite(ap) and ap>max_artifact_prop: reasons.append('high_artifact_prop')
            if impl.any(): reasons.append('implausible_rr')
            if succ.any(): reasons.append('large_successive_change')
            row={'segment_id':int(seg),'segment_start_s':float(np.nanmin(ts)),'segment_end_s':float(np.nanmax(ts)),'duration_s':duration,'n_beats':len(r),'n_clean_beats':len(clean),'artifact_prop':ap,'mean_rr_ms':float(np.mean(clean)) if len(clean) else np.nan,'median_rr_ms':float(np.median(clean)) if len(clean) else np.nan,'min_rr_ms':float(np.min(finite_r)) if len(finite_r) else np.nan,'max_rr_ms':float(np.max(finite_r)) if len(finite_r) else np.nan,'n_implausible_rr':int(impl.sum()),'n_large_successive_changes':int(succ.sum()),'quality_ok':not reasons,'reasons':';'.join(dict.fromkeys(reasons)) if reasons else 'ok'}
            if group_cols:
                row={**{c:z.iloc[0][c] for c in as_list(group_cols)},**row}
            else: row={'group':g,**row}
            rows.append(row)
    return pd.DataFrame(rows)


def _event_table(events,event_time_col=None,event_id_col=None):
    if isinstance(events,(list,tuple,np.ndarray,pd.Series)) and not isinstance(events,pd.DataFrame):
        vals=time_seconds(events); return pd.DataFrame({'event_id':[f'E{i+1}' for i in range(len(vals))],'event_time_s':vals})
    ev=ensure_df(events,'events').copy(); etc=event_time_col or guess_col(ev,['event_time_s','event_time','onset','onset_s','time_s','time','timestamp','MSTIMER'],'event time',True); eid=event_id_col or guess_col(ev,['event_id','event','marker','trial','trial_id','condition'],'event id',False)
    ev['event_time_s']=time_seconds(ev[etc]); ev['event_id']=ev[eid].astype(str) if eid else [f'E{i+1}' for i in range(len(ev))]; return ev


def compute_gazepoint_scr_latency(data,events,time_col=None,eda_col=None,event_time_col=None,event_id_col=None,group_cols=None,baseline_window_s=(-1,0),response_window_s=(0,5),onset_threshold=0.01,recovery_fraction=0.50):
    df=ensure_df(data); tc=time_col or guess_col(df,['time_s','time','timestamp','event_time','MSTIMER','TIME','CNT'],'time',True); ec=eda_col or guess_col(df,['GSR','EDA','skin_conductance','conductance','GSR_US','eda'],'EDA/GSR',True); ev=_event_table(events,event_time_col,event_id_col); t=time_seconds(df[tc]); eda=pd.to_numeric(df[ec],errors='coerce').to_numpy(float); rows=[]
    for _,e in ev.iterrows():
        idx=np.arange(len(df))
        for c in as_list(group_cols):
            if c in df.columns and c in ev.columns: idx=idx[df.loc[idx,c].astype(str).to_numpy()==str(e[c])]
        rel=t[idx]-float(e.event_time_s); val=eda[idx]
        b=(np.isfinite(rel)&(rel>=baseline_window_s[0])&(rel<baseline_window_s[1])&np.isfinite(val)); r=(np.isfinite(rel)&(rel>=response_window_s[0])&(rel<=response_window_s[1])&np.isfinite(val)); baseline=float(np.mean(val[b])) if b.any() else np.nan; rt=rel[r]; rv=val[r]; order=np.argsort(rt); rt=rt[order]; rv=rv[order]; cor=rv-baseline
        if not len(cor) or not np.isfinite(cor).any():
            row={'event_id':e.event_id,'event_time_s':e.event_time_s,'baseline_mean':baseline,'onset_latency_s':np.nan,'peak_latency_s':np.nan,'peak_amplitude':np.nan,'auc':np.nan,'recovery_latency_s':np.nan,'response_detected':False,'n_response_samples':len(cor)}
        else:
            p=int(np.nanargmax(cor)); amp=float(cor[p]); peak=float(rt[p]); hits=np.flatnonzero(cor>=onset_threshold); onset=float(rt[hits[0]]) if len(hits) else np.nan; rec=np.nan
            if np.isfinite(amp) and amp>onset_threshold:
                rh=np.flatnonzero(cor[p:]<=amp*recovery_fraction)
                if len(rh): rec=float(rt[p+rh[0]])
            row={'event_id':e.event_id,'event_time_s':e.event_time_s,'baseline_mean':baseline,'onset_latency_s':onset,'peak_latency_s':peak,'peak_amplitude':amp,'auc':trapz(rt,cor),'recovery_latency_s':rec,'response_detected':bool(np.isfinite(amp) and amp>=onset_threshold),'n_response_samples':len(cor)}
        for c in ev.columns:
            if c not in {'event_id','event_time_s'}: row[c]=e[c]
        rows.append(row)
    return pd.DataFrame(rows)


def compute_gazepoint_signal_lag_matrix(data,signal_cols=None,time_col=None,group_cols=None,max_lag_s=2,lag_step_s=None,min_overlap=10):
    df=ensure_df(data); tc=time_col or guess_col(df,['time_s','time','timestamp','event_time','MSTIMER','TIME','CNT'],'time',True)
    if signal_cols is None: signal_cols=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in [tc,*as_list(group_cols)]]
    signal_cols=[c for c in as_list(signal_cols) if c in df.columns]
    if len(signal_cols)<2: raise ValueError("At least two numeric `signal_cols` are required.")
    rows=[]
    for g,idx in group_indices(df,group_cols):
        z=df.loc[idx]; t=time_seconds(z[tc]); d=np.diff(np.sort(np.unique(t[np.isfinite(t)]))); d=d[np.isfinite(d)&(d>0)]; step=float(lag_step_s) if lag_step_s is not None else float(np.median(d)) if len(d) else np.nan
        if not np.isfinite(step) or step<=0: continue
        lags=np.arange(-max_lag_s,max_lag_s+step/2,step)
        for a,b in combinations(signal_cols,2):
            x=pd.to_numeric(z[a],errors='coerce').to_numpy(float); y=pd.to_numeric(z[b],errors='coerce').to_numpy(float); okx=np.isfinite(t)&np.isfinite(x); oky=np.isfinite(t)&np.isfinite(y)
            if okx.sum()<min_overlap or oky.sum()<min_overlap: continue
            xt=t[okx]; xv=x[okx]; yt=t[oky]; yv=y[oky]; corrs=[]; ns=[]
            for lag in lags:
                ys=np.interp(xt,yt-lag,yv,left=np.nan,right=np.nan); ok=np.isfinite(xv)&np.isfinite(ys); ns.append(int(ok.sum()))
                corrs.append(float(np.corrcoef(xv[ok],ys[ok])[0,1]) if ok.sum()>=min_overlap and np.std(xv[ok],ddof=1)>0 and np.std(ys[ok],ddof=1)>0 else np.nan)
            corrs=np.asarray(corrs); best=int(np.nanargmax(np.abs(corrs))) if np.isfinite(corrs).any() else None
            row={'signal_1':a,'signal_2':b,'best_lag_s':lags[best] if best is not None else np.nan,'best_correlation':corrs[best] if best is not None else np.nan,'abs_best_correlation':abs(corrs[best]) if best is not None else np.nan,'n_overlap_at_best':ns[best] if best is not None else np.nan,'max_lag_s':max_lag_s,'lag_step_s':step}
            if group_cols: row={**{c:z.iloc[0][c] for c in as_list(group_cols)},**row}
            else: row={'group':g,**row}
            rows.append(row)
    return pd.DataFrame(rows)


def estimate_gazepoint_respiration_from_ppg(data,ppg_col=None,time_col=None,sampling_rate_hz=None,respiratory_band_hz=(0.10,0.50),detrend=True):
    if isinstance(data,(list,tuple,np.ndarray,pd.Series)) and not isinstance(data,pd.DataFrame):
        ppg=np.asarray(data,float); fs=50.0 if sampling_rate_hz is None else float(sampling_rate_hz); t=np.arange(1,len(ppg)+1)/fs
    else:
        df=ensure_df(data); pc=ppg_col or guess_col(df,['PPG','BVP','HRP','pulse','ppg','bvp'],'PPG/BVP',True); tc=time_col or guess_col(df,['time_s','time','timestamp','event_time','MSTIMER','TIME','CNT'],'time',False); ppg=pd.to_numeric(df[pc],errors='coerce').to_numpy(float)
        if tc: t=time_seconds(df[tc]); fs=float(sampling_rate_hz) if sampling_rate_hz else 1/np.median(np.diff(np.sort(np.unique(t[np.isfinite(t)]))))
        else: fs=50.0 if sampling_rate_hz is None else float(sampling_rate_hz); t=np.arange(1,len(ppg)+1)/fs
    ok=np.isfinite(t)&np.isfinite(ppg)
    if ok.sum()<4 or not np.isfinite(fs) or fs<=0:
        spec=pd.DataFrame(columns=['frequency_hz','power']); summ=pd.DataFrame([{'respiration_rate_bpm':np.nan,'respiration_frequency_hz':np.nan,'peak_power':np.nan,'band_power':np.nan,'n_samples':0,'sampling_rate_hz':np.nan}]); return {'summary':summ,'spectrum':spec,'settings':{'respiratory_band_hz':respiratory_band_hz,'detrend':detrend}}
    tt=t[ok]; vv=ppg[ok]; order=np.argsort(tt); tt=tt[order]; vv=vv[order]; keep=np.r_[True,np.diff(tt)>0]; tt=tt[keep]; vv=vv[keep]; grid=np.arange(tt.min(),tt.max()+0.5/fs,1/fs); reg=np.interp(grid,tt,vv)
    if len(reg)<8:
        spec=pd.DataFrame(columns=['frequency_hz','power']); summ=pd.DataFrame([{'respiration_rate_bpm':np.nan,'respiration_frequency_hz':np.nan,'peak_power':np.nan,'band_power':np.nan,'n_samples':len(reg),'sampling_rate_hz':fs}]); return {'summary':summ,'spectrum':spec,'settings':{'respiratory_band_hz':respiratory_band_hz,'detrend':detrend}}
    if detrend: reg=signal.detrend(reg,type='linear')
    n=len(reg); taper=0.5-0.5*np.cos(2*np.pi*np.arange(n)/max(1,n-1)); z=np.fft.fft((reg-reg.mean())*taper); half=np.arange(n//2); freq=half*fs/n; power=np.abs(z[half])**2/n; spec=pd.DataFrame({'frequency_hz':freq,'power':power}); band=(freq>=respiratory_band_hz[0])&(freq<=respiratory_band_hz[1])
    if band.any(): bi=np.flatnonzero(band); best=bi[np.argmax(power[bi])]; rf=float(freq[best]); pp=float(power[best]); bp=float(np.nansum(power[bi]))
    else: rf=pp=bp=np.nan
    summ=pd.DataFrame([{'respiration_rate_bpm':rf*60,'respiration_frequency_hz':rf,'peak_power':pp,'band_power':bp,'n_samples':len(reg),'sampling_rate_hz':fs}]); return {'summary':summ,'spectrum':spec,'settings':{'respiratory_band_hz':respiratory_band_hz,'detrend':bool(detrend),'interpretation':'exploratory_ppg_derived_respiration_estimate'}}
