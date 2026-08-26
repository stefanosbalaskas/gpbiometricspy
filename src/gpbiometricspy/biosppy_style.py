from __future__ import annotations

from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, find_peaks, hilbert
from scipy.stats import spearmanr, kendalltau


def _interp(x):
    a=pd.to_numeric(pd.Series(x),errors='coerce').to_numpy(float); ok=np.isfinite(a)
    if not len(a) or not ok.any(): return np.full(len(a),np.nan)
    if not ok.all(): a[~ok]=np.interp(np.flatnonzero(~ok),np.flatnonzero(ok),a[ok])
    return a


def _running_mean(x,k):
    a=_interp(x); k=max(1,int(k))
    if k<=1:return a
    y=pd.Series(a).rolling(k,center=True,min_periods=k).mean().to_numpy(float); bad=~np.isfinite(y); y[bad]=a[bad]; return y


def _running_median(x,k):
    a=_interp(x); k=max(3,int(k)); h=k//2
    return np.array([np.median(a[max(0,i-h):min(len(a),i+h+1)]) for i in range(len(a))],float)


def _prepare_signal(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,candidates=()):
    if isinstance(data,(list,tuple,np.ndarray,pd.Series)) and not isinstance(data,pd.DataFrame):
        a=np.asarray(data,dtype=float)
        if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0: raise ValueError('`sampling_rate_hz` is required for numeric input.')
        d=pd.DataFrame({'time_s':np.arange(len(a))/float(sampling_rate_hz),'signal':a,'group':'all'})
        return d,'signal','time_s',['group'],float(sampling_rate_hz)
    if not isinstance(data,pd.DataFrame): raise TypeError('`data` must be a data frame or numeric vector.')
    d=data.copy()
    if signal_col is None:
        signal_col=next((c for c in candidates if c in d.columns),None)
        if signal_col is None: raise ValueError('Could not infer signal column. Please supply it explicitly.')
    if signal_col not in d: raise ValueError('`signal_col` not found.')
    if time_col is None:
        if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0: raise ValueError('Supply `time_col` or `sampling_rate_hz`.')
        time_col='time_s'; d[time_col]=np.arange(len(d))/float(sampling_rate_hz)
    elif time_col not in d: raise ValueError('`time_col` not found.')
    if group_cols is None or (not isinstance(group_cols,str) and len(group_cols)==0): group_cols=['group']; d['group']='all'
    elif isinstance(group_cols,str): group_cols=[group_cols]
    else: group_cols=list(group_cols)
    miss=[c for c in group_cols if c not in d]
    if miss: raise ValueError('Missing group columns: '+', '.join(miss))
    d[signal_col]=pd.to_numeric(d[signal_col],errors='coerce'); d[time_col]=pd.to_numeric(d[time_col],errors='coerce')
    if sampling_rate_hz is None:
        t=np.sort(pd.unique(d[time_col].dropna())); dt=np.diff(t); dt=dt[np.isfinite(dt)&(dt>0)]; sampling_rate_hz=1/np.median(dt) if len(dt) else np.nan
    return d,signal_col,time_col,group_cols,float(sampling_rate_hz)


def _groups(d,cols):
    if not cols:return [('all',np.arange(len(d)))]
    grouper=cols[0] if len(cols)==1 else cols; out=[]
    for k,b in d.reset_index(drop=True).groupby(grouper,sort=False,dropna=False):
        if not isinstance(k,tuple): k=(k,)
        out.append((' | '.join(map(str,k)),b.index.to_numpy(int)))
    return out


def _bandpass(x,fs,low=.5,high=8):
    a=_interp(x)
    if len(a)<10:return a
    hi=min(high,fs*.49); lo=max(low,1e-6)
    if lo>=hi:return a
    sos=butter(3,[lo,hi],btype='bandpass',fs=fs,output='sos')
    try:return sosfiltfilt(sos,a)
    except ValueError:return a


def _detect_ppg(d,sc,tc,gc,fs):
    rows=[]
    for g,idx in _groups(d,gc):
        sig=_interp(d.iloc[idx][sc]); dist=max(1,int(round(.3*fs)))
        prom=max(np.std(sig)*.15,1e-9); pk,_=find_peaks(sig,distance=dist,prominence=prom)
        for j,p in enumerate(pk,1): rows.append({'group':g,'peak_id':j,'peak_index':int(idx[p])+1,'peak_time_s':float(d.iloc[idx[p]][tc]),'peak_value':float(sig[p]),'accepted':True})
    return pd.DataFrame(rows)


def _peak_indices(peaks,time,n):
    if peaks is None:return pd.DataFrame(columns=['index','group'])
    if isinstance(peaks,pd.DataFrame):
        if 'peak_index' in peaks: idx=pd.to_numeric(peaks.peak_index,errors='coerce').dropna().astype(int).to_numpy()
        elif 'peak_time_s' in peaks:
            tt=np.asarray(time,float); idx=np.array([int(np.argmin(np.abs(tt-v)))+1 for v in pd.to_numeric(peaks.peak_time_s,errors='coerce').dropna()])
        else:return pd.DataFrame(columns=['index','group'])
        groups=peaks.get('group',pd.Series(['all']*len(peaks))).astype(str).to_numpy()[:len(idx)]
    else:
        idx=np.asarray(peaks,int); groups=np.array(['all']*len(idx))
    ok=(idx>=1)&(idx<=n); return pd.DataFrame({'index':idx[ok],'group':groups[ok]})


def prepare_gazepoint_biosppy_input(data,signal_type='auto',signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,missing='error',irregular='error',sampling_tolerance=.05,min_segment_samples=3,signal_units=None,output_dir=None,prefix='gazepoint_biosppy',write_manifest=True,overwrite=False):
    if signal_type not in {'auto','eda','ppg'}: raise ValueError('Invalid `signal_type`.')
    if missing not in {'error','interpolate','segments'}: raise ValueError('Invalid `missing`.')
    if irregular not in {'error','allow'}: raise ValueError('Invalid `irregular`.')
    if sampling_tolerance<0 or min_segment_samples<1: raise ValueError('Invalid preparation settings.')
    numeric=not isinstance(data,pd.DataFrame)
    if numeric:
        a=np.asarray(data,dtype=float)
        if len(a)==0: raise ValueError('`data` must contain at least one signal sample.')
        if signal_type=='auto': raise ValueError('Numeric-vector input requires explicit `signal_type`.')
        if sampling_rate_hz is None or sampling_rate_hz<=0: raise ValueError('`sampling_rate_hz` is required for numeric input.')
        d=pd.DataFrame({'time_s':np.arange(len(a))/sampling_rate_hz,'signal_raw':a}); signal_col='signal'; time_col='time_s'; group_cols=[]
    else:
        d=data.copy()
        if signal_type=='auto':
            eda=[c for c in ['EDA','GSR','eda','gsr','SCR'] if c in d]; ppg=[c for c in ['PPG','BVP','HRP','PULSE','ppg','pulse'] if c in d]
            if eda and ppg: raise ValueError('Both EDA and PPG candidate columns were found; specify `signal_type`.')
            if eda: signal_type='eda'; signal_col=signal_col or eda[0]
            elif ppg: signal_type='ppg'; signal_col=signal_col or ppg[0]
            else: raise ValueError('Could not infer EDA or PPG signal column.')
        candidates=['EDA','GSR','eda','gsr','SCR'] if signal_type=='eda' else ['PPG','BVP','HRP','PULSE','ppg','pulse']
        signal_col=signal_col or next((c for c in candidates if c in d),None)
        if signal_col is None or signal_col not in d: raise ValueError('Could not identify `signal_col`.')
        if not pd.api.types.is_numeric_dtype(d[signal_col]): raise TypeError('Signal column must be numeric.')
        if time_col is None:
            time_col=next((c for c in ['time_s','Time','TIME','timestamp','Timestamp'] if c in d),None)
            if time_col is None:
                if sampling_rate_hz is None: raise ValueError('`time_col` or `sampling_rate_hz` is required.')
                time_col='time_s'; d[time_col]=np.arange(len(d))/sampling_rate_hz
        d['signal_raw']=pd.to_numeric(d[signal_col],errors='coerce')
        group_cols=[] if group_cols is None else ([group_cols] if isinstance(group_cols,str) else list(group_cols))
    d['time_s']=pd.to_numeric(d[time_col],errors='coerce')
    d=d.reset_index(drop=True); d['signal_prepared']=np.nan; d['finite_raw']=np.isfinite(d.signal_raw); d['interpolated']=False; d['included']=False; d['segment_id']=pd.Series([pd.NA]*len(d),dtype='Int64'); d['vector_id']=None; d['exclusion_reason']=None
    vectors={}; rates={}; manifest=[]
    for gid,idx in _groups(d,group_cols):
        tt=d.loc[idx,'time_s'].to_numpy(float); sig=d.loc[idx,'signal_raw'].to_numpy(float)
        if not np.isfinite(tt).all(): raise ValueError(f'Non-finite time values were found in group `{gid}`.')
        if len(tt)>1 and (np.diff(tt)<=0).any(): raise ValueError(f'Time values must be strictly increasing within group `{gid}`.')
        dt=np.diff(tt); rate=float(sampling_rate_hz) if sampling_rate_hz else (1/np.median(dt) if len(dt) else np.nan)
        if not np.isfinite(rate) or rate<=0: raise ValueError('Could not infer a valid sampling rate.')
        expected=1/rate; rel=np.abs(dt-expected)/expected if len(dt) else np.array([]); irr=rel>sampling_tolerance
        if irr.any() and irregular=='error': raise ValueError(f'Irregular sampling intervals were found in group `{gid}`.')
        finite=np.isfinite(sig)
        def add(local,vals,seg=None):
            vid=gid if seg is None else f'{gid}__segment_{seg:03d}'; gix=idx[local]; vectors[vid]=np.asarray(vals,float); rates[vid]=rate
            d.loc[gix,'signal_prepared']=vals; d.loc[gix,'included']=True; d.loc[gix,'vector_id']=vid
            if seg is not None:d.loc[gix,'segment_id']=seg
            row={'vector_id':vid,'sample_count':len(local),'sampling_rate_hz':rate,'missing_samples_in_group':int((~finite).sum()),'interpolated_samples':int(d.loc[gix,'interpolated'].sum()),'irregular_intervals_in_group':int(irr.sum()),'maximum_relative_interval_error':float(rel.max()) if len(rel) else 0.0}
            for c in group_cols:row[c]=d.loc[gix[0],c]
            manifest.append(row)
        if missing=='error':
            if not finite.all(): raise ValueError(f'Non-finite signal values were found in group `{gid}`.')
            add(np.arange(len(idx)),sig)
        elif missing=='interpolate':
            if finite.sum()<2: raise ValueError('At least two finite signal samples are required for interpolation.')
            vals=sig.copy(); vals[~finite]=np.interp(np.flatnonzero(~finite),np.flatnonzero(finite),sig[finite]); d.loc[idx[~finite],'interpolated']=True; add(np.arange(len(idx)),vals)
        else:
            d.loc[idx[~finite],'exclusion_reason']='missing_or_nonfinite'; seg=0; i=0
            while i<len(sig):
                if not finite[i]:i+=1;continue
                j=i+1
                while j<len(sig) and finite[j]:j+=1
                seg+=1; local=np.arange(i,j)
                if len(local)>=min_segment_samples:add(local,sig[local],seg)
                else:d.loc[idx[local],'exclusion_reason']='short_segment'
                i=j
    mf=pd.DataFrame(manifest); files=[]
    if output_dir is not None:
        od=Path(output_dir); od.mkdir(parents=True,exist_ok=True); planned=[]
        for vid in vectors: planned.append((vid,od/f'{prefix}_{signal_type}_{re.sub(r"[^A-Za-z0-9_.-]+","_",vid)}.csv'))
        mp=od/f'{prefix}_{signal_type}_manifest.csv'
        for _,q in planned:
            if q.exists() and not overwrite: raise FileExistsError(f'Output file already exists: {q}')
        if write_manifest and mp.exists() and not overwrite: raise FileExistsError(f'Output file already exists: {mp}')
        for vid,q in planned:
            q.write_text('\n'.join(f'{v:g}' for v in vectors[vid])+'\n'); files.append({'file_type':'signal','vector_id':vid,'path':str(q)})
        if write_manifest: mf.to_csv(mp,index=False); files.append({'file_type':'manifest','vector_id':None,'path':str(mp)})
    return {'samples':d,'vectors':vectors,'sampling_rates_hz':pd.Series(rates,dtype=float),'manifest':mf,'files':pd.DataFrame(files),'settings':{'signal_type':signal_type,'signal_col':signal_col,'time_col':time_col,'group_cols':group_cols,'signal_units':signal_units,'missing':missing,'irregular':irregular,'python_call_templates':{'eda':'biosppy.signals.eda.eda(signal=signal, sampling_rate=fs)','ppg':'biosppy.signals.ppg.ppg(signal=signal, sampling_rate=fs)'}},'class':'gazepoint_biosppy_input'}


def extract_gazepoint_eda_events_biosppy_style(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,smoothing_seconds=1,min_amplitude=None,min_distance_seconds=1,onset_window_seconds=4):
    d,sc,tc,gc,fs=_prepare_signal(data,signal_col,time_col,group_cols,sampling_rate_hz,['EDA','GSR','eda','gsr','SCR','signal'])
    if not np.isfinite(fs) or fs<=0: raise ValueError('Could not infer a valid sampling rate.')
    rows=[]
    for g,idx in _groups(d,gc):
        sig=_interp(d.iloc[idx][sc]); tt=d.iloc[idx][tc].to_numpy(float); tonic=_running_median(sig,max(3,round(smoothing_seconds*fs))); ph=sig-tonic; ps=_running_mean(ph,max(3,round(.25*fs)))
        thr=min_amplitude if min_amplitude is not None else max(.01,float(np.median(np.abs(ps))+np.median(np.abs(ps-np.median(ps)))))
        cand,_=find_peaks(ps,height=thr,distance=max(1,round(min_distance_seconds*fs)))
        for j,p in enumerate(cand,1):
            lo=max(0,p-round(onset_window_seconds*fs)); oi=lo+int(np.argmin(ps[lo:p+1])); rows.append({'group':g,'event_id':j,'onset_index':int(idx[oi])+1,'peak_index':int(idx[p])+1,'onset_time_s':tt[oi],'peak_time_s':tt[p],'rise_time_s':tt[p]-tt[oi],'amplitude':ps[p]-ps[oi],'tonic_at_peak':tonic[p],'phasic_peak':ps[p]})
    return pd.DataFrame(rows)


def estimate_gazepoint_eda_recovery_times(data,events=None,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,recovery_prop=.5,max_recovery_seconds=10):
    d,sc,tc,gc,fs=_prepare_signal(data,signal_col,time_col,group_cols,sampling_rate_hz,['EDA','GSR','eda','gsr','SCR','signal'])
    if events is None: events=extract_gazepoint_eda_events_biosppy_style(d,sc,tc,gc,fs)
    out=events.copy()
    for c in ['recovery_index','recovery_timepoint_s','recovery_time_s']:out[c]=np.nan
    sig=_interp(d[sc]); tt=d[tc].to_numpy(float)
    for i,row in out.iterrows():
        pi=int(row.peak_index)-1; oi=int(row.onset_index)-1; target=sig[oi]+(sig[pi]-sig[oi])*(1-recovery_prop); hi=min(len(sig),pi+max(1,round(max_recovery_seconds*fs))+1); rel=np.flatnonzero(sig[pi:hi]<=target)
        if len(rel):r=pi+int(rel[0]); out.at[i,'recovery_index']=r+1; out.at[i,'recovery_timepoint_s']=tt[r]; out.at[i,'recovery_time_s']=tt[r]-row.peak_time_s
    return out


def run_gazepoint_biosppy_eda(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,smoothing_seconds=4):
    d,sc,tc,gc,fs=_prepare_signal(data,signal_col,time_col,group_cols,sampling_rate_hz,['EDA','GSR','eda','gsr','SCR','signal']); tonic=np.full(len(d),np.nan); ph=np.full(len(d),np.nan)
    for _,idx in _groups(d,gc):
        sig=_interp(d.iloc[idx][sc]); to=_running_median(sig,max(3,round(smoothing_seconds*fs))); tonic[idx]=to; ph[idx]=sig-to
    sigtab=d.copy(); sigtab['eda_raw']=d[sc]; sigtab['eda_tonic']=tonic; sigtab['eda_phasic']=ph
    events=extract_gazepoint_eda_events_biosppy_style(d,sc,tc,gc,fs); recovery=estimate_gazepoint_eda_recovery_times(d,events,sc,tc,gc,fs)
    summary=pd.DataFrame([{'n_samples':len(d),'sampling_rate_hz':fs,'n_events':len(events),'mean_phasic':np.nanmean(ph),'sd_phasic':np.nanstd(ph,ddof=1),'mean_tonic':np.nanmean(tonic)}])
    return {'signal':sigtab,'events':events,'recovery':recovery,'summary':summary,'settings':{'sampling_rate_hz':fs,'smoothing_seconds':smoothing_seconds}}


def detect_gazepoint_ppg_onsets(data,signal_col=None,time_col=None,peaks=None,group_cols=None,sampling_rate_hz=None,search_seconds=.6):
    d,sc,tc,gc,fs=_prepare_signal(data,signal_col,time_col,group_cols,sampling_rate_hz,['PPG','BVP','PULSE','HRP','pulse','signal']); sig=_interp(d[sc]); peaks=_detect_ppg(d,sc,tc,gc,fs) if peaks is None else peaks; pk=_peak_indices(peaks,d[tc],len(sig)); rows=[]
    for i,r in pk.reset_index(drop=True).iterrows():
        p=int(r['index'])-1; lo=max(0,p-round(search_seconds*fs)); oi=lo+int(np.argmin(sig[lo:p+1])); rows.append({'group':r['group'],'beat_id':i+1,'onset_index':oi+1,'onset_time_s':d.iloc[oi][tc],'peak_index':p+1,'peak_time_s':d.iloc[p][tc],'rise_time_s':d.iloc[p][tc]-d.iloc[oi][tc],'amplitude':sig[p]-sig[oi]})
    return pd.DataFrame(rows)


def extract_gazepoint_ppg_templates(data,signal_col=None,time_col=None,peaks=None,group_cols=None,sampling_rate_hz=None,before_seconds=.30,after_seconds=.60):
    d,sc,tc,gc,fs=_prepare_signal(data,signal_col,time_col,group_cols,sampling_rate_hz,['PPG','BVP','PULSE','HRP','pulse','signal']); sig=_interp(d[sc]); peaks=_detect_ppg(d,sc,tc,gc,fs) if peaks is None else peaks; pk=_peak_indices(peaks,d[tc],len(sig)); pre=max(1,round(before_seconds*fs)); post=max(1,round(after_seconds*fs)); mats=[]; used=[]
    for p in pk['index'].astype(int):
        z=p-1
        if z-pre>=0 and z+post<len(sig):mats.append(sig[z-pre:z+post+1]);used.append(p)
    mat=np.vstack(mats) if mats else np.empty((0,pre+post+1)); tr=np.arange(-pre,post+1)/fs; avg=np.nanmean(mat,axis=0) if len(mat) else np.full(len(tr),np.nan); quality=np.nan
    if len(mat)>=2:
        cc=np.corrcoef(mat); quality=float(np.nanmean(cc[np.triu_indices_from(cc,1)]))
    return {'templates':mat,'average_template':pd.DataFrame({'time_s':tr,'amplitude':avg}),'template_time_s':tr,'peak_indices_used':np.array(used,int),'template_quality_correlation':quality,'settings':{'before_seconds':before_seconds,'after_seconds':after_seconds,'sampling_rate_hz':fs}}


def run_gazepoint_biosppy_ppg(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None):
    d,sc,tc,gc,fs=_prepare_signal(data,signal_col,time_col,group_cols,sampling_rate_hz,['PPG','BVP','PULSE','HRP','pulse','signal']); d=d.copy(); d['ppg_filtered']=_bandpass(d[sc],fs); peaks=_detect_ppg(d,'ppg_filtered',tc,gc,fs); onsets=detect_gazepoint_ppg_onsets(d,'ppg_filtered',tc,peaks,gc,fs); templates=extract_gazepoint_ppg_templates(d,'ppg_filtered',tc,peaks,gc,fs)
    hr=pd.DataFrame();
    if len(peaks)>=2:
        pt=peaks.peak_time_s.to_numpy(float); hr=pd.DataFrame({'time_s':pt[1:],'heart_rate_bpm':60/np.diff(pt)})
    return {'signal':d,'peaks':peaks,'onsets':onsets,'templates':templates,'heart_rate':hr,'settings':{'sampling_rate_hz':fs}}


def detrend_gazepoint_rri_window(rri_ms,time_s=None,window_seconds=60,method='median'):
    if method not in {'median','mean','linear'}: raise ValueError('Invalid `method`.')
    r0=np.asarray(rri_ms,float); ok=np.isfinite(r0)&(r0>0); r=r0[ok]; tt=np.cumsum(r)/1000 if time_s is None else np.asarray(time_s,float)[ok]
    if len(r)<3:return pd.DataFrame({'time_s':tt,'rri_ms':r,'trend_ms':np.nan,'rri_detrended_ms':np.nan})
    trend=np.empty(len(r))
    for i in range(len(r)):
        ix=np.flatnonzero(np.abs(tt-tt[i])<=window_seconds/2)
        if method=='median':trend[i]=np.median(r[ix])
        elif method=='mean':trend[i]=np.mean(r[ix])
        elif len(ix)>=3:trend[i]=np.polyval(np.polyfit(tt[ix],r[ix],1),tt[i])
        else:trend[i]=np.mean(r[ix])
    return pd.DataFrame({'time_s':tt,'rri_ms':r,'trend_ms':trend,'rri_detrended_ms':r-trend+np.mean(trend)})


def correct_gazepoint_rri_artifacts_local(rri_ms,method='local_median',window_intervals=5,threshold=.20,replacement='local_median'):
    if method not in {'local_median','quotient','zscore'} or replacement not in {'local_median','interpolate'}: raise ValueError('Invalid method.')
    r=np.asarray(rri_ms,float); n=len(r); art=(~np.isfinite(r))|(r<=0); reason=np.where(art,'nonfinite_or_nonpositive','accepted').astype(object)
    if n>=3 and method=='local_median':
        for i in range(n):
            lo=max(0,i-window_intervals); hi=min(n,i+window_intervals+1); med=np.nanmedian(r[lo:hi])
            if np.isfinite(med) and med>0 and np.isfinite(r[i]) and abs(r[i]-med)/med>threshold:art[i]=True;reason[i]='local_median_threshold'
    elif n>=3 and method=='quotient':
        rat=np.ones(n); rat[1:]=np.minimum(r[1:]/r[:-1],r[:-1]/r[1:]); bad=np.isfinite(rat)&(rat<(1-threshold)); art[bad]=True;reason[bad]='quotient_threshold'
    elif n>=3 and method=='zscore':
        sd=np.nanstd(r,ddof=1)
        if sd>0:
            bad=np.abs((r-np.nanmean(r))/sd)>3.5; art[bad]=True;reason[bad]='zscore_threshold'
    corr=r.copy()
    if art.any() and replacement=='local_median':
        for i in np.flatnonzero(art):
            lo=max(0,i-window_intervals);hi=min(n,i+window_intervals+1); vals=r[lo:hi][~art[lo:hi]]; corr[i]=np.nanmedian(vals) if len(vals) else np.nan
    elif art.any():
        good=(~art)&np.isfinite(r)
        if good.sum()>=2:corr[art]=np.interp(np.flatnonzero(art),np.flatnonzero(good),r[good])
    return pd.DataFrame({'index':np.arange(1,n+1),'rri_ms':r,'rri_corrected_ms':corr,'artifact':art,'reason':reason})


def compute_gazepoint_signal_power_spectrum(x,sampling_rate_hz,detrend=True):
    a=_interp(x); fs=float(sampling_rate_hz)
    if not np.isfinite(fs) or fs<=0: raise ValueError('Invalid sampling rate.')
    n=len(a)
    if n<4:return pd.DataFrame({'frequency_hz':[],'power':[]})
    if detrend:a=a-np.mean(a)
    fy=np.fft.fft(a); p=np.abs(fy)**2/(n*fs); f=np.arange(n)*fs/n; keep=np.arange(n//2)
    return pd.DataFrame({'frequency_hz':f[keep],'power':p[keep]})


def compute_gazepoint_signal_band_power(x,sampling_rate_hz=None,bands=None,relative=True):
    if bands is None:bands={'very_low':(.003,.04),'low':(.04,.15),'high':(.15,.40)}
    psd=x if isinstance(x,pd.DataFrame) and {'frequency_hz','power'}<=set(x) else compute_gazepoint_signal_power_spectrum(x,sampling_rate_hz)
    total=float(pd.to_numeric(psd.power,errors='coerce').sum()); rows=[]
    for nm,b in bands.items():
        keep=(psd.frequency_hz>=b[0])&(psd.frequency_hz<b[1]); p=float(psd.loc[keep,'power'].sum()); rows.append({'band':nm,'low_hz':b[0],'high_hz':b[1],'power':p,'relative_power':p/total if relative and total>0 else np.nan})
    return pd.DataFrame(rows)


def compute_gazepoint_signal_phase_locking(x,y,sampling_rate_hz,band=None):
    a=_interp(x);b=_interp(y);n=min(len(a),len(b));a=a[:n];b=b[:n]
    if band is not None:a=_bandpass(a,sampling_rate_hz,band[0],band[1]);b=_bandpass(b,sampling_rate_hz,band[0],band[1])
    diff=np.angle(hilbert(a-np.mean(a)))-np.angle(hilbert(b-np.mean(b))); return pd.DataFrame([{'n':n,'phase_locking_value':abs(np.mean(np.exp(1j*diff))),'mean_phase_difference_rad':np.angle(np.mean(np.exp(1j*diff)))}])


def compute_gazepoint_signal_correlation(x,y,method='pearson',lag_max=None):
    if method not in {'pearson','spearman','kendall'}: raise ValueError('Invalid `method`.')
    a=np.asarray(x,float);b=np.asarray(y,float);n=min(len(a),len(b));a=a[:n];b=b[:n];ok=np.isfinite(a)&np.isfinite(b)
    def cor(u,v):
        good=np.isfinite(u)&np.isfinite(v)
        if good.sum()<3:return np.nan
        if method=='pearson':return float(np.corrcoef(u[good],v[good])[0,1])
        if method=='spearman':return float(spearmanr(u[good],v[good]).statistic)
        return float(kendalltau(u[good],v[good]).statistic)
    c0=cor(a,b); bestlag=np.nan; bestc=np.nan
    if lag_max is not None:
        vals=[]
        for lg in range(-abs(int(lag_max)),abs(int(lag_max))+1):
            if lg<0:c=cor(a[:n+lg],b[-lg:])
            elif lg>0:c=cor(a[lg:],b[:n-lg])
            else:c=c0
            vals.append((lg,c))
        good=[z for z in vals if np.isfinite(z[1])]
        if good:bestlag,bestc=max(good,key=lambda z:abs(z[1]))
    return pd.DataFrame([{'n':int(ok.sum()),'correlation':c0,'method':method,'best_lag':bestlag,'best_lag_correlation':bestc}])
