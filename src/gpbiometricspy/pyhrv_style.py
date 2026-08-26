from __future__ import annotations

from pathlib import Path
import json
import math
import pickle
import re
from typing import Any

import numpy as np
import pandas as pd
from scipy import signal


def _num(x):
    return pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(float)


def _clean_nni(nni_ms, min_ms=250, max_ms=2500):
    x = _num(nni_ms)
    return x[np.isfinite(x) & (x > 0) & (x >= min_ms) & (x <= max_ms)]


def _time_from_nni(nni_ms):
    return np.cumsum(_num(nni_ms)) / 1000.0


def _sd(x):
    x=np.asarray(x,float)
    return float(np.std(x,ddof=1)) if x.size>1 else np.nan


def _trapz(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    ok=np.isfinite(x)&np.isfinite(y); x=x[ok]; y=y[ok]
    if len(x)<2:return np.nan
    o=np.argsort(x); x=x[o]; y=y[o]
    return float(np.sum(np.diff(x)*(y[:-1]+y[1:])/2))


def _band_summaries(freq, psd):
    freq=np.asarray(freq,float); psd=np.asarray(psd,float)
    bands={"ulf":(0,.003),"vlf":(.003,.04),"lf":(.04,.15),"hf":(.15,.4)}
    powers={}; peaks={}
    for name,(lo,hi) in bands.items():
        k=np.isfinite(freq)&np.isfinite(psd)&(freq>=lo)&(freq<hi)
        powers[name]=_trapz(freq[k],psd[k])
        peaks[name]=float(freq[k][np.nanargmax(psd[k])]) if np.any(k) else np.nan
    vals=[v for v in powers.values() if np.isfinite(v)]
    total=float(np.sum(vals)) if vals else 0.0
    lf=powers['lf']; hf=powers['hf']; lh=lf+hf
    def rel(v): return 100*v/total if total>0 and np.isfinite(v) else np.nan
    return pd.DataFrame([{
        'total_power':total,'ulf_abs':powers['ulf'],'vlf_abs':powers['vlf'],'lf_abs':lf,'hf_abs':hf,
        'ulf_rel':rel(powers['ulf']),'vlf_rel':rel(powers['vlf']),'lf_rel':rel(lf),'hf_rel':rel(hf),
        'lf_norm':100*lf/lh if np.isfinite(lh) and lh>0 else np.nan,
        'hf_norm':100*hf/lh if np.isfinite(lh) and lh>0 else np.nan,
        'lf_hf':lf/hf if np.isfinite(hf) and hf>0 else np.nan,
        'ulf_peak':peaks['ulf'],'vlf_peak':peaks['vlf'],'lf_peak':peaks['lf'],'hf_peak':peaks['hf']
    }])


def _resample_nni(nni_ms,time_s=None,resample_hz=4):
    x=_clean_nni(nni_ms)
    if len(x)<4:return np.array([]),np.array([])
    t=_time_from_nni(x) if time_s is None else _num(time_s)[:len(x)]
    ok=np.isfinite(t)&np.isfinite(x); t=t[ok]; x=x[ok]
    if len(x)<4 or np.ptp(t)<=0:return np.array([]),np.array([])
    grid=np.arange(np.min(t),np.max(t)+1e-12,1/float(resample_hz))
    y=np.interp(grid,t,x); y=y-np.mean(y)
    return grid,y


def _fft_psd(y,fs):
    y=np.asarray(y,float); y=y[np.isfinite(y)]; n=len(y)
    if n<4:return pd.DataFrame({'frequency_hz':[],'psd':[]})
    y=y-np.mean(y); fy=np.fft.fft(y); p=(np.abs(fy)**2)/(n*fs); f=np.arange(n)*fs/n
    keep=np.arange(max(1,n//2))
    return pd.DataFrame({'frequency_hz':f[keep],'psd':p[keep]})


def _welch_psd(y,fs,window_seconds=256,overlap=.5):
    y=np.asarray(y,float); y=y[np.isfinite(y)]; n=len(y)
    if n<8:return pd.DataFrame({'frequency_hz':[],'psd':[]})
    wn=min(n,max(8,int(round(window_seconds*fs)))); step=max(1,int(round(wn*(1-overlap))))
    starts=list(range(0,n-wn+1,step)) or [0]; spectra=[]
    for s in starts:
        yy=y[s:s+wn]; taper=.5-.5*np.cos(2*np.pi*np.arange(len(yy))/(len(yy)-1)); spectra.append(_fft_psd(yy*taper,fs))
    freq=spectra[0]['frequency_hz'].to_numpy(); mat=[]
    for z in spectra: mat.append(np.interp(freq,z['frequency_hz'],z['psd']))
    return pd.DataFrame({'frequency_hz':freq,'psd':np.mean(np.vstack(mat),axis=0)})


def _lomb_psd(nni_ms,time_s=None,min_hz=.003,max_hz=.4,n_freq=512):
    x=_clean_nni(nni_ms)
    if len(x)<4:return pd.DataFrame({'frequency_hz':[],'psd':[]})
    t=_time_from_nni(x) if time_s is None else _num(time_s)[:len(x)]
    ok=np.isfinite(t)&np.isfinite(x); t=t[ok]; y=x[ok]-np.mean(x[ok]); f=np.linspace(min_hz,max_hz,int(n_freq)); p=[]
    for ff in f:
        w=2*np.pi*ff; cs=np.cos(w*t); sn=np.sin(w*t); cc=np.sum(cs**2); ss=np.sum(sn**2)
        p.append(((np.sum(y*cs)**2/cc)+(np.sum(y*sn)**2/ss))/len(y) if cc>0 and ss>0 else np.nan)
    return pd.DataFrame({'frequency_hz':f,'psd':p})


def _ar_psd(y,fs,order=None,n_freq=512):
    y=np.asarray(y,float); y=y[np.isfinite(y)]
    if len(y)<16:return pd.DataFrame({'frequency_hz':[],'psd':[]})
    max_order=min(20,len(y)//3)
    orders=[int(order)] if order is not None else range(1,max_order+1)
    best=None
    for p in orders:
        if p<1 or p>=len(y)-1:continue
        target=y[p:]; X=np.column_stack([y[p-k-1:len(y)-k-1] for k in range(p)])
        try: coef=np.linalg.lstsq(X,target,rcond=None)[0]
        except np.linalg.LinAlgError: continue
        res=target-X@coef; var=float(np.mean(res**2)); aic=len(target)*np.log(max(var,1e-30))+2*p
        if best is None or aic<best[0]:best=(aic,coef,var)
    if best is None:return pd.DataFrame({'frequency_hz':[],'psd':[]})
    _,ar,var=best; freq=np.linspace(0,fs/2,int(n_freq)); out=[]
    for f in freq:
        z=np.exp(-1j*2*np.pi*f/fs*np.arange(1,len(ar)+1)); den=abs(1-np.sum(ar*z))**2
        out.append(var/den/fs if np.isfinite(den) and den>0 else np.nan)
    return pd.DataFrame({'frequency_hz':freq,'psd':np.real(out)})


def extract_gazepoint_pyhrv_nn_intervals(peaks,peak_time_col='peak_time_s',time_unit='seconds'):
    if time_unit not in {'seconds','milliseconds'}:raise ValueError('`time_unit` must be seconds or milliseconds.')
    if isinstance(peaks,pd.DataFrame):
        if peak_time_col not in peaks:raise ValueError('`peak_time_col` not found.')
        t=_num(peaks[peak_time_col])
    else:t=_num(peaks)
    t=np.sort(t[np.isfinite(t)])
    if len(t)<2:return np.array([],float)
    d=np.diff(t); return d*1000 if time_unit=='seconds' else d


def compute_gazepoint_pyhrv_nn_diff(nni_ms,absolute=False):
    x=_clean_nni(nni_ms); d=np.diff(x) if len(x)>=2 else np.array([],float); return np.abs(d) if absolute else d


def compute_gazepoint_pyhrv_heart_rate(nni_ms):
    return 60000/_clean_nni(nni_ms)


def create_gazepoint_pyhrv_time_vector(nni_ms,start_s=0):
    return float(start_s)+_time_from_nni(_clean_nni(nni_ms))


def check_gazepoint_pyhrv_interval(nni_ms,min_ms=250,max_ms=2500):
    x=_num(nni_ms); valid=np.isfinite(x)&(x>=min_ms)&(x<=max_ms)
    return pd.DataFrame({'index':np.arange(1,len(x)+1),'nni_ms':x,'valid':valid,'reason':np.where(valid,'valid','outside_interval_or_nonfinite')})


def segment_gazepoint_pyhrv_nni(nni_ms,segment_seconds=300,overlap=0,min_intervals=3):
    x=_clean_nni(nni_ms)
    if not len(x):return pd.DataFrame()
    t=_time_from_nni(x); step=float(segment_seconds)*(1-float(overlap))
    if not np.isfinite(step) or step<=0:raise ValueError('`overlap` must be smaller than 1.')
    rows=[]; starts=np.arange(np.min(t),np.max(t)+1e-12,step)
    for i,s in enumerate(starts,1):
        e=s+segment_seconds; idx=np.flatnonzero((t>=s)&(t<e))
        if len(idx)>=int(min_intervals):
            rows.append(pd.DataFrame({'segment_id':i,'start_s':s,'end_s':e,'interval_index':idx+1,'nni_ms':x[idx]}))
    return pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()


def compute_gazepoint_pyhrv_nni_parameters(nni_ms):
    x=_clean_nni(nni_ms); return pd.DataFrame([{'nni_counter':len(x),'nni_mean':np.mean(x) if len(x) else np.nan,'nni_min':np.min(x) if len(x) else np.nan,'nni_max':np.max(x) if len(x) else np.nan}])


def compute_gazepoint_pyhrv_nni_differences_parameters(nni_ms):
    d=compute_gazepoint_pyhrv_nn_diff(nni_ms,True); return pd.DataFrame([{'nni_diff_counter':len(d),'nni_diff_mean':np.mean(d) if len(d) else np.nan,'nni_diff_min':np.min(d) if len(d) else np.nan,'nni_diff_max':np.max(d) if len(d) else np.nan}])


def compute_gazepoint_pyhrv_hr_parameters(nni_ms):
    h=compute_gazepoint_pyhrv_heart_rate(nni_ms); return pd.DataFrame([{'hr_mean':np.mean(h) if len(h) else np.nan,'hr_min':np.min(h) if len(h) else np.nan,'hr_max':np.max(h) if len(h) else np.nan,'hr_std':_sd(h)}])


def compute_gazepoint_pyhrv_sdnn(nni_ms):return _sd(_clean_nni(nni_ms))

def compute_gazepoint_pyhrv_sdnn_index(nni_ms,segment_seconds=300):
    s=segment_gazepoint_pyhrv_nni(nni_ms,segment_seconds)
    if s.empty:return np.nan
    vals=s.groupby('segment_id')['nni_ms'].apply(lambda z:_sd(z.to_numpy()))
    return float(np.nanmean(vals)) if np.isfinite(vals).any() else np.nan

def compute_gazepoint_pyhrv_sdann(nni_ms,segment_seconds=300):
    s=segment_gazepoint_pyhrv_nni(nni_ms,segment_seconds)
    if s.empty:return np.nan
    return _sd(s.groupby('segment_id')['nni_ms'].mean().to_numpy())
def compute_gazepoint_pyhrv_rmssd(nni_ms):
    d=compute_gazepoint_pyhrv_nn_diff(nni_ms); return float(np.sqrt(np.mean(d**2))) if len(d) else np.nan
def compute_gazepoint_pyhrv_sdsd(nni_ms):return _sd(compute_gazepoint_pyhrv_nn_diff(nni_ms))

def compute_gazepoint_pyhrv_nnxx(nni_ms,threshold_ms=50):
    d=compute_gazepoint_pyhrv_nn_diff(nni_ms,True); n=len(d); c=int(np.sum(d>threshold_ms)) if n else np.nan
    return pd.DataFrame([{'threshold_ms':threshold_ms,'nnxx':c,'pnnxx':100*c/n if n else np.nan}])
def compute_gazepoint_pyhrv_nn50(nni_ms):
    o=compute_gazepoint_pyhrv_nnxx(nni_ms,50).rename(columns={'nnxx':'nn50','pnnxx':'pnn50'}); return o
def compute_gazepoint_pyhrv_nn20(nni_ms):
    return compute_gazepoint_pyhrv_nnxx(nni_ms,20).rename(columns={'nnxx':'nn20','pnnxx':'pnn20'})

def compute_gazepoint_pyhrv_triangular_index(nni_ms,bin_width_ms=7.8125):
    x=_clean_nni(nni_ms)
    if len(x)<3:return np.nan
    lo=math.floor(np.min(x)/bin_width_ms)*bin_width_ms; hi=math.ceil(np.max(x)/bin_width_ms)*bin_width_ms+bin_width_ms
    counts,_=np.histogram(x,bins=np.arange(lo,hi+bin_width_ms*.1,bin_width_ms)); m=np.max(counts) if len(counts) else 0
    return len(x)/m if m>0 else np.nan

def compute_gazepoint_pyhrv_tinn(nni_ms,bin_width_ms=7.8125):
    x=_clean_nni(nni_ms)
    if len(x)<3:return np.nan
    lo=math.floor(np.min(x)/bin_width_ms)*bin_width_ms; hi=math.ceil(np.max(x)/bin_width_ms)*bin_width_ms+bin_width_ms
    edges=np.arange(lo,hi+bin_width_ms*.1,bin_width_ms); counts,edges=np.histogram(x,bins=edges); centers=(edges[:-1]+edges[1:])/2; pos=centers[counts>0]
    return float(np.ptp(pos)) if len(pos) else np.nan

def compute_gazepoint_pyhrv_time_domain(nni_ms,segment_seconds=300):
    parts=[compute_gazepoint_pyhrv_nni_parameters(nni_ms),compute_gazepoint_pyhrv_nni_differences_parameters(nni_ms),compute_gazepoint_pyhrv_hr_parameters(nni_ms)]
    o=pd.concat(parts,axis=1); n50=compute_gazepoint_pyhrv_nn50(nni_ms).iloc[0]; n20=compute_gazepoint_pyhrv_nn20(nni_ms).iloc[0]
    o=o.assign(sdnn=compute_gazepoint_pyhrv_sdnn(nni_ms),sdnn_index=compute_gazepoint_pyhrv_sdnn_index(nni_ms,segment_seconds),sdann=compute_gazepoint_pyhrv_sdann(nni_ms,segment_seconds),rmssd=compute_gazepoint_pyhrv_rmssd(nni_ms),sdsd=compute_gazepoint_pyhrv_sdsd(nni_ms),nn50=n50.nn50,pnn50=n50.pnn50,nn20=n20.nn20,pnn20=n20.pnn20,triangular_index=compute_gazepoint_pyhrv_triangular_index(nni_ms),tinn=compute_gazepoint_pyhrv_tinn(nni_ms)); return o


def compute_gazepoint_pyhrv_welch_psd(nni_ms,time_s=None,resample_hz=4,window_seconds=256,overlap=.5):
    _,y=_resample_nni(nni_ms,time_s,resample_hz); psd=_welch_psd(y,resample_hz,window_seconds,overlap); return {'psd':psd,'measures':_band_summaries(psd.frequency_hz,psd.psd),'method':'welch'}
def compute_gazepoint_pyhrv_lomb_psd(nni_ms,time_s=None,min_hz=.003,max_hz=.4,n_freq=512):
    psd=_lomb_psd(nni_ms,time_s,min_hz,max_hz,n_freq); return {'psd':psd,'measures':_band_summaries(psd.frequency_hz,psd.psd),'method':'lomb'}
def compute_gazepoint_pyhrv_ar_psd(nni_ms,time_s=None,resample_hz=4,order=None):
    _,y=_resample_nni(nni_ms,time_s,resample_hz); psd=_ar_psd(y,resample_hz,order); return {'psd':psd,'measures':_band_summaries(psd.frequency_hz,psd.psd),'method':'ar'}
def compute_gazepoint_pyhrv_frequency_domain(nni_ms,time_s=None,method='welch'):
    if method=='welch':return compute_gazepoint_pyhrv_welch_psd(nni_ms,time_s)
    if method=='lomb':return compute_gazepoint_pyhrv_lomb_psd(nni_ms,time_s)
    if method=='ar':return compute_gazepoint_pyhrv_ar_psd(nni_ms,time_s)
    raise ValueError('method must be welch, lomb, or ar')
def compare_gazepoint_pyhrv_psd_methods(nni_ms,time_s=None,methods=('welch','lomb','ar'),plot=False):
    import matplotlib.pyplot as plt
    if isinstance(methods,str):methods=[methods]
    outs={m:compute_gazepoint_pyhrv_frequency_domain(nni_ms,time_s,m) for m in methods}; rows=[]
    for m,o in outs.items(): z=o['measures'].copy(); z.insert(0,'method',m); rows.append(z)
    if plot:
        fig,ax=plt.subplots();
        for m,o in outs.items(): ax.plot(o['psd'].frequency_hz,o['psd'].psd,label=m)
        ax.legend(); ax.set(xlabel='Frequency (Hz)',ylabel='Power',title='pyHRV-style PSD comparison')
    return {'outputs':outs,'measures':pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()}
def compute_gazepoint_pyhrv_psd_waterfall(nni_ms,segment_seconds=300,method='welch',plot=False):
    import matplotlib.pyplot as plt
    seg=segment_gazepoint_pyhrv_nni(nni_ms,segment_seconds)
    if seg.empty:return {'psd':pd.DataFrame(),'measures':pd.DataFrame()}
    psds=[]; meas=[]
    for sid,z in seg.groupby('segment_id'):
        o=compute_gazepoint_pyhrv_frequency_domain(z.nni_ms.to_numpy(),method=method); p=o['psd'].copy(); p['segment_id']=sid; psds.append(p); m=o['measures'].copy(); m['segment_id']=sid; meas.append(m)
    p=pd.concat(psds,ignore_index=True); m=pd.concat(meas,ignore_index=True)
    if plot and not p.empty:
        piv=p.pivot_table(index='frequency_hz',columns='segment_id',values='psd'); fig,ax=plt.subplots(); ax.imshow(piv.to_numpy(),aspect='auto',origin='lower'); ax.set(title='pyHRV-style PSD waterfall',xlabel='Segment',ylabel='Frequency bin')
    return {'psd':p,'measures':m}


def compute_gazepoint_pyhrv_poincare(nni_ms,plot=False):
    import matplotlib.pyplot as plt
    x=_clean_nni(nni_ms)
    if len(x)<3:return pd.DataFrame([{'sd1':np.nan,'sd2':np.nan,'sd_ratio':np.nan,'ellipse_area':np.nan}])
    d=np.diff(x); sd1=math.sqrt(np.var(d,ddof=1)/2); term=2*np.var(x,ddof=1)-.5*np.var(d,ddof=1); sd2=math.sqrt(max(0,term))
    if plot:
        fig,ax=plt.subplots(); ax.scatter(x[:-1],x[1:]); lo=min(x);hi=max(x);ax.plot([lo,hi],[lo,hi],'--');ax.set(title='pyHRV-style Poincare plot',xlabel='NNI[n] (ms)',ylabel='NNI[n+1] (ms)')
    return pd.DataFrame([{'sd1':sd1,'sd2':sd2,'sd_ratio':sd1/sd2 if sd2>0 else np.nan,'ellipse_area':np.pi*sd1*sd2}])
def compute_gazepoint_pyhrv_sample_entropy(nni_ms,m=2,r=None):
    x=_clean_nni(nni_ms); n=len(x); m=int(m)
    if n<=m+2:return np.nan
    if r is None:r=.2*_sd(x)
    if not np.isfinite(r) or r<=0:return np.nan
    def count(mm):
        emb=np.array([x[i:i+mm] for i in range(n-mm+1)]); c=0
        for i in range(len(emb)-1):c+=int(np.sum(np.max(np.abs(emb[i+1:]-emb[i]),axis=1)<=r))
        return c
    b=count(m);a=count(m+1);return float(-np.log(a/b)) if b>0 and a>0 else np.nan
def compute_gazepoint_pyhrv_dfa(nni_ms,scales=None):
    x=_clean_nni(nni_ms)
    if len(x)<16:return pd.DataFrame([{'alpha':np.nan,'alpha1':np.nan,'alpha2':np.nan}])
    if scales is None:scales=np.unique(np.round(np.exp(np.linspace(np.log(4),np.log(64),12))).astype(int))
    y=np.cumsum(x-np.mean(x)); rows=[]
    for s in scales:
        s=int(s)
        if s<4 or s>=len(y)/2:continue
        rms=[]
        for st in range(0,len(y)-s+1,s):
            yy=y[st:st+s]; xx=np.arange(st+1,st+s+1); coef=np.polyfit(xx,yy,1); res=yy-np.polyval(coef,xx); rms.append(np.sqrt(np.mean(res**2)))
        f=np.sqrt(np.mean(np.asarray(rms)**2)) if rms else np.nan
        if np.isfinite(f) and f>0:rows.append((s,f))
    if len(rows)<2:return pd.DataFrame([{'alpha':np.nan,'alpha1':np.nan,'alpha2':np.nan}])
    df=pd.DataFrame(rows,columns=['scale','fluctuation'])
    def slope(z):return float(np.polyfit(np.log(z.scale),np.log(z.fluctuation),1)[0]) if len(z)>=2 else np.nan
    return pd.DataFrame([{'alpha':slope(df),'alpha1':slope(df[df.scale<=16]),'alpha2':slope(df[df.scale>16])}])
def compute_gazepoint_pyhrv_nonlinear(nni_ms):
    p=compute_gazepoint_pyhrv_poincare(nni_ms); d=compute_gazepoint_pyhrv_dfa(nni_ms); return pd.concat([p,pd.DataFrame([{'sample_entropy':compute_gazepoint_pyhrv_sample_entropy(nni_ms)}]),d],axis=1)


def plot_gazepoint_pyhrv_tachogram(nni_ms,time_s=None):
    import matplotlib.pyplot as plt
    x=_clean_nni(nni_ms)
    if not len(x):raise ValueError('No valid NN intervals.')
    t=_time_from_nni(x) if time_s is None else _num(time_s)[:len(x)]; fig,ax=plt.subplots();ax.plot(t,x);ax.set(title='pyHRV-style tachogram',xlabel='Time (s)',ylabel='NN interval (ms)'); return fig
def plot_gazepoint_pyhrv_hr_heatplot(nni_ms,time_bins=20,hr_bins=20):
    import matplotlib.pyplot as plt
    x=_clean_nni(nni_ms)
    if len(x)<3:raise ValueError('At least three valid NN intervals are required.')
    t=_time_from_nni(x); h=60000/x; tab,xe,ye=np.histogram2d(t,h,bins=[int(time_bins),int(hr_bins)]); fig,ax=plt.subplots();ax.imshow(tab.T,aspect='auto',origin='lower');ax.set(title='pyHRV-style heart-rate heatplot',xlabel='Time bin',ylabel='Heart-rate bin');return fig
def plot_gazepoint_pyhrv_radar_chart(measures,columns=('sdnn','rmssd','sdsd','pnn50','lf_norm','hf_norm','sd1','sd2')):
    import matplotlib.pyplot as plt
    if isinstance(measures,pd.DataFrame): s=measures.iloc[0]
    elif isinstance(measures,pd.Series):s=measures
    elif isinstance(measures,dict):s=pd.Series(measures)
    else:raise TypeError('`measures` must be named values or a one-row data frame.')
    names=[c for c in columns if c in s.index]; z=pd.to_numeric(s[names],errors='coerce').to_numpy(float)
    if not len(z) or not np.isfinite(z).any():raise ValueError('No finite radar values.')
    lo=np.nanmin(z);hi=np.nanmax(z); scaled=np.full(len(z),.5) if hi==lo else (z-lo)/(hi-lo); theta=np.linspace(0,2*np.pi,len(z)+1); rr=np.r_[scaled,scaled[0]]
    fig,ax=plt.subplots(subplot_kw={'projection':'polar'});ax.plot(theta,rr);ax.fill(theta,rr,alpha=.2);ax.set_xticks(theta[:-1],names);ax.set_title('pyHRV-style radar chart');return fig


def _jsonable(x):
    if isinstance(x,pd.DataFrame):return {'__dataframe__':True,'data':x.to_dict(orient='list')}
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,(np.floating,np.integer)):return x.item()
    if isinstance(x,dict):return {k:_jsonable(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [_jsonable(v) for v in x]
    return x

def _unjson(x):
    if isinstance(x,dict) and x.get('__dataframe__'):return pd.DataFrame(x['data'])
    if isinstance(x,dict):return {k:_unjson(v) for k,v in x.items()}
    if isinstance(x,list):return [_unjson(v) for v in x]
    return x

def export_gazepoint_pyhrv_results(results,path):
    if path is None or not str(path):raise ValueError('Supply `path`.')
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix.lower()=='.json':p.write_text(json.dumps(_jsonable(results),indent=2,allow_nan=True),encoding='utf-8')
    else:
        with p.open('wb') as f:pickle.dump(results,f)
    return p
def import_gazepoint_pyhrv_results(path):
    p=Path(path)
    if not p.exists():raise FileNotFoundError(f'File not found: {p}')
    if p.suffix.lower()=='.json':return _unjson(json.loads(p.read_text(encoding='utf-8')))
    with p.open('rb') as f:return pickle.load(f)
def run_gazepoint_pyhrv_style(nni_ms=None,peaks=None,peak_time_col='peak_time_s',time_unit='seconds',frequency_method='welch'):
    if nni_ms is None:
        if peaks is None:raise ValueError('Supply `nni_ms` or `peaks`.')
        nni_ms=extract_gazepoint_pyhrv_nn_intervals(peaks,peak_time_col,time_unit)
    x=_clean_nni(nni_ms);return {'nni_ms':x,'time_domain':compute_gazepoint_pyhrv_time_domain(x),'frequency_domain':compute_gazepoint_pyhrv_frequency_domain(x,method=frequency_method),'nonlinear':compute_gazepoint_pyhrv_nonlinear(x)}


def _safe_name(x):
    s=re.sub(r'[^A-Za-z0-9._-]+','_',str(x)).strip('_');return s or 'group'

def prepare_gazepoint_pyhrv_input(data,ibi_col=None,group_cols=None,unit='auto',filter='none',min_nni_ms=300,max_nni_ms=2000,collapse_repeated_intervals=False,repeated_tolerance_ms=1e-8,output_dir=None,prefix='gazepoint_pyhrv',write_manifest=True,overwrite=False):
    if unit not in {'auto','milliseconds','seconds'}:raise ValueError('invalid unit')
    if filter not in {'none','plausible'}:raise ValueError('invalid filter')
    if not np.isfinite(min_nni_ms) or min_nni_ms<=0 or not np.isfinite(max_nni_ms) or max_nni_ms<=0:raise ValueError('bounds must be positive')
    if max_nni_ms<=min_nni_ms:raise ValueError('`max_nni_ms` must be greater than `min_nni_ms`.')
    if repeated_tolerance_ms<0:raise ValueError('`repeated_tolerance_ms` must be non-negative.')
    if not isinstance(prefix,str) or not prefix:raise ValueError('`prefix` must be non-empty.')
    vector_input=not isinstance(data,pd.DataFrame)
    if vector_input:
        raw=_num(data)
        if len(raw)==0:raise ValueError('`data` must contain at least one interval.')
        if group_cols is not None and len([group_cols] if isinstance(group_cols,str) else group_cols)>0:raise ValueError('`group_cols` cannot be used with a numeric vector.')
        work=pd.DataFrame({'source_row':np.arange(1,len(raw)+1),'.interval_raw':raw}); ibi_name=None; groups=[]
    else:
        if data.empty:raise ValueError('`data` must contain at least one row.')
        d=data.copy()
        if ibi_col is None:
            candidates=['IBI_clean_ms','nni_ms','NNI_MS','NNI','RR_ms','RR_MS','RRI_ms','RRI_MS','IBI_MS','IBI','RR','RRI','ibi','rr','rri']
            found=[c for c in candidates if c in d and pd.api.types.is_numeric_dtype(d[c])]
            if not found:raise ValueError('Could not identify a numeric IBI, RR, or NNI column. Supply `ibi_col` explicitly.')
            ibi_col=found[0]
        if ibi_col not in d:raise ValueError('`ibi_col` was not found in `data`.')
        if not pd.api.types.is_numeric_dtype(d[ibi_col]):raise ValueError('`ibi_col` must identify a numeric column.')
        groups=[] if group_cols is None else ([group_cols] if isinstance(group_cols,str) else list(dict.fromkeys(map(str,group_cols))))
        missing=[c for c in groups if c not in d]
        if missing:raise ValueError('`group_cols` were not found in `data`: '+', '.join(missing))
        work=pd.DataFrame({'source_row':np.arange(1,len(d)+1)})
        for c in groups:work[c]=d[c].to_numpy()
        work['.interval_raw']=d[ibi_col].to_numpy(float); ibi_name=ibi_col
    raw=work['.interval_raw'].to_numpy(float)
    if unit!='auto':resolved=unit; method='explicit'
    else:
        lname=(ibi_name or '').lower()
        if re.search(r'(^|_)(ms|msec|millisecond|milliseconds)($|_)',lname):resolved='milliseconds';method='column_name'
        elif re.search(r'(^|_)(sec|secs|second|seconds|s)($|_)',lname):resolved='seconds';method='column_name'
        else:
            pos=raw[np.isfinite(raw)&(raw>0)]
            if not len(pos):raise ValueError('Automatic unit assessment requires at least one finite positive interval.')
            typical=np.median(pos)
            if typical<=10:resolved='seconds';method='median_heuristic'
            elif typical>=100:resolved='milliseconds';method='median_heuristic'
            else:raise ValueError('Automatic interval-unit assessment was ambiguous.')
    nni=raw*1000 if resolved=='seconds' else raw.copy()
    status=np.full(len(nni),'plausible',object);status[~np.isfinite(nni)]='missing_or_nonfinite';status[np.isfinite(nni)&(nni<=0)]='non_positive';status[np.isfinite(nni)&(nni>0)&(nni<min_nni_ms)]='below_minimum';status[np.isfinite(nni)&(nni>max_nni_ms)]='above_maximum'
    included=np.isfinite(nni)&(nni>0)
    if filter=='plausible':included &= (nni>=min_nni_ms)&(nni<=max_nni_ms)
    reason=np.full(len(nni),None,object);reason[~np.isfinite(nni)]='missing_or_nonfinite';reason[np.isfinite(nni)&(nni<=0)]='non_positive'
    if filter=='plausible':reason[np.isfinite(nni)&(nni>0)&(nni<min_nni_ms)]='below_minimum';reason[np.isfinite(nni)&(nni>max_nni_ms)]='above_maximum'
    if groups:
        grouper=groups[0] if len(groups)==1 else groups; split=[(k,np.asarray(v.index,int)) for k,v in work.groupby(grouper,sort=False,dropna=False)]
    else:split=[('all',np.arange(len(work)))]
    repeated=np.zeros(len(nni),bool)
    for _,idx in split:
        cur=nni[idx]
        if len(idx)>1:repeated[idx[1:]]=np.isfinite(cur[1:])&np.isfinite(cur[:-1])&(np.abs(cur[1:]-cur[:-1])<=repeated_tolerance_ms)
    if collapse_repeated_intervals:
        ri=repeated&included;included[ri]=False;reason[ri]='repeated_interval'
    intervals=work.drop(columns=['.interval_raw']).copy();intervals['nni_ms']=nni;intervals['interval_status']=status;intervals['repeated_interval']=repeated;intervals['included']=included;intervals['exclusion_reason']=reason;intervals['interval_index']=pd.array([pd.NA]*len(nni),dtype='Int64');intervals['interval_end_time_s']=np.nan
    vectors={}; manifest=[]
    for key,idx in split:
        if isinstance(key,tuple):gid='||'.join('<NA>' if pd.isna(v) else str(v) for v in key)
        else:gid='<NA>' if pd.isna(key) else str(key)
        ridx=idx[included[idx]]; vals=nni[ridx]; vectors[gid]=vals.copy()
        if len(ridx):intervals.loc[ridx,'interval_index']=np.arange(1,len(ridx)+1);intervals.loc[ridx,'interval_end_time_s']=np.cumsum(vals)/1000
        row={}
        if groups:
            for c in groups:row[c]=intervals.iloc[idx[0]][c]
        else:row['group']='all'
        row.update({'group_id':gid,'input_rows':len(idx),'finite_positive_rows':int(np.sum(np.isfinite(nni[idx])&(nni[idx]>0))),'plausible_rows':int(np.sum(status[idx]=='plausible')),'repeated_rows':int(np.sum(repeated[idx])),'included_intervals':int(np.sum(included[idx])),'excluded_intervals':int(np.sum(~included[idx]))})
        for lab in ['missing_or_nonfinite','non_positive','below_minimum','above_maximum','repeated_interval']:row['excluded_'+('repeated' if lab=='repeated_interval' else lab)]=int(np.sum(reason[idx]==lab))
        row['total_duration_s']=float(np.nansum(vals)/1000);row['mean_nni_ms']=float(np.mean(vals)) if len(vals) else np.nan;manifest.append(row)
    manifest=pd.DataFrame(manifest);files=[]
    if output_dir is not None:
        out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);safe=_safe_name(prefix);candidates=[]
        filenames=[]
        for i,(gid,vals) in enumerate(vectors.items(),1):
            suffix='' if len(vectors)==1 and gid=='all' else '_'+_safe_name(gid);fn=safe+suffix+'.csv'
            if fn in filenames:fn=Path(fn).stem+f'_{i}.csv'
            filenames.append(fn);candidates.append(("intervals",gid,out/fn,vals))
        mp=out/f'{safe}_manifest.csv' if write_manifest else None
        existing=[p for _,_,p,_ in candidates if p.exists()]+([mp] if mp is not None and mp.exists() else [])
        if existing and not overwrite:raise FileExistsError('Output file already exists: '+str(existing[0]))
        for typ,gid,p,vals in candidates:
            p.write_text('\n'.join(f'{v:g}' for v in vals)+('\n' if len(vals) else ''),encoding='utf-8');files.append({'file_type':typ,'group_id':gid,'path':str(p)})
        if mp is not None:manifest.to_csv(mp,index=False);files.append({'file_type':'manifest','group_id':None,'path':str(mp)})
    settings={'ibi_col':ibi_name,'group_cols':groups,'requested_unit':unit,'resolved_unit':resolved,'unit_resolution_method':method,'filter':filter,'min_nni_ms':min_nni_ms,'max_nni_ms':max_nni_ms,'collapse_repeated_intervals':collapse_repeated_intervals,'repeated_tolerance_ms':repeated_tolerance_ms,'output_dir':str(output_dir) if output_dir is not None else None,'prefix':prefix,'write_manifest':write_manifest,'interpretation_notes':['Prepared intervals are expressed in milliseconds.','The function prepares data but does not execute Python or pyHRV.','Intervals outside the plausibility range remain visible in the audit table.','Repeated-value collapsing should be enabled only when repeated sample-level interval values represent duplicated export rows.','HRV interpretation requires genuine NN or RR intervals and should not be derived from a vendor summary HRV field.']}
    return {'intervals':intervals,'vectors':vectors,'manifest':manifest,'files':pd.DataFrame(files,columns=['file_type','group_id','path']),'settings':settings}
