from __future__ import annotations

from datetime import datetime
from pathlib import Path
import importlib.util
import math
import numpy as np
import pandas as pd
from scipy import interpolate, signal as sp_signal
import matplotlib.pyplot as plt


def _as_num(x):
    return pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype=float)


def _interp_na(x):
    y = _as_num(x)
    ok = np.isfinite(y)
    if ok.sum() < 2:
        return y
    idx = np.arange(len(y), dtype=float)
    return np.interp(idx, idx[ok], y[ok])


def _pick_col(df, candidates, label):
    low = {str(c).lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    pats = [c.lower() for c in candidates]
    for c in df.columns:
        s = str(c).lower()
        if any(p in s for p in pats):
            return c
    raise ValueError(f"Could not infer {label} column. Please supply it explicitly.")


def _running_mean(x, k):
    x = np.asarray(x, dtype=float)
    k = max(1, int(round(k)))
    if k % 2 == 0:
        k += 1
    if len(x) < k:
        return np.full(len(x), np.nanmean(x))
    # R stats::filter sides=2 gives NA at edges; caller fills those with overall mean.
    out = np.convolve(x, np.ones(k) / k, mode="same")
    half = k // 2
    out[:half] = np.nan
    out[-half:] = np.nan
    return out


def _running_median(x, k):
    x = np.asarray(x, dtype=float)
    k = max(3, int(round(k)))
    if k % 2 == 0:
        k += 1
    h = k // 2
    return np.array([np.nanmedian(x[max(0, i-h):min(len(x), i+h+1)]) for i in range(len(x))], dtype=float)


def _group_indices(df, group_cols=None):
    if group_cols is None or group_cols == []:
        return {"__all__": np.arange(len(df))}
    if isinstance(group_cols, str):
        group_cols = [group_cols]
    missing = [c for c in group_cols if c not in df.columns]
    if missing:
        raise ValueError("Missing group columns: " + ", ".join(missing))
    out = {}
    grouper = group_cols[0] if len(group_cols) == 1 else group_cols
    for key, sub in df.groupby(grouper, sort=True, dropna=False):
        if isinstance(key, tuple):
            label = " | ".join(map(str, key))
        else:
            label = str(key)
        out[label] = sub.index.to_numpy()
    return out


def _mad(x, constant=1.4826):
    x = np.asarray(x, dtype=float)
    med = np.nanmedian(x)
    return float(constant * np.nanmedian(np.abs(x-med)))


def _iqr(x):
    q = np.nanquantile(np.asarray(x, dtype=float), [.25,.75])
    return float(q[1]-q[0])


def prepare_gazepoint_heartpy_input(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, output_dir=None, prefix="gazepoint_heartpy"):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a data frame.")
    if data.empty:
        raise ValueError("`data` must contain at least one row.")
    if signal_col is None:
        signal_col = _pick_col(data, ["PULSE","PPG","HRP","PULSE_SIGNAL","heart_signal","biometric_pulse"], "pulse/PPG signal")
    if signal_col not in data.columns:
        raise ValueError("`signal_col` not found in data.")
    if time_col is None:
        candidates=["TIME","TIME_SECONDS","TIMESTAMP","FPOGX","time_s","timestamp_s"]
        low={str(c).lower():c for c in data.columns}
        time_col=next((low[c.lower()] for c in candidates if c.lower() in low), None)
        if time_col is None:
            time_col=next((c for c in data.columns if "time" in str(c).lower() or "timestamp" in str(c).lower()), None)
    sig=_interp_na(data[signal_col])
    if time_col is not None:
        if time_col not in data.columns: raise ValueError("`time_col` not found in data.")
        t=_as_num(data[time_col])
        if not np.isfinite(t).any(): raise ValueError("`time_col` could not be converted to numeric time.")
        t=t-np.nanmin(t)
        if sampling_rate_hz is None:
            u=np.unique(t[np.isfinite(t)]); dt=np.diff(np.sort(u)); dt=dt[np.isfinite(dt)&(dt>0)]
            sampling_rate_hz=float(1/np.median(dt)) if len(dt) else np.nan
    else:
        if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0:
            raise ValueError("Supply `sampling_rate_hz` when no time column can be inferred.")
        t=np.arange(len(sig))/float(sampling_rate_hz)
    out=pd.DataFrame({"time_s":t,"signal":sig})
    if group_cols is not None:
        if isinstance(group_cols,str): group_cols=[group_cols]
        missing=[c for c in group_cols if c not in data.columns]
        if missing: raise ValueError("Missing group columns: "+", ".join(missing))
        out=pd.concat([data[group_cols].reset_index(drop=True),out],axis=1)
    if group_cols:
        gs=out.groupby(group_cols,dropna=False,sort=True)["signal"].apply(lambda z:int(np.isfinite(z).sum())).reset_index(name="finite_samples")
    else:
        gs=pd.DataFrame({"group":["all"],"finite_samples":[int(np.isfinite(out.signal).sum())]})
    paths=[]
    if output_dir is not None:
        p=Path(output_dir)
        if str(p)=="": raise ValueError("`output_dir` must be NULL or a single non-empty character value.")
        p.mkdir(parents=True,exist_ok=True)
        f1=p/f"{prefix}_signal.csv"; f2=p/f"{prefix}_group_summary.csv"
        out.to_csv(f1,index=False);gs.to_csv(f2,index=False);paths=[str(f1.resolve()),str(f2.resolve())]
    return {"signal_table":out,"sampling_rate_hz":sampling_rate_hz,"group_summary":gs,"path":paths}


def export_gazepoint_heartpy_input(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, output_dir=None, prefix="gazepoint_heartpy"):
    if output_dir is None: raise ValueError("`output_dir` must be supplied. Use a temporary directory for temporary outputs.")
    return prepare_gazepoint_heartpy_input(data,signal_col,time_col,group_cols,sampling_rate_hz,output_dir,prefix)


def reconstruct_gazepoint_ppg_clipping(x, near_max_prop=.02, flat_diff_prop=.001, min_run=2):
    x=_interp_na(x); n=len(x)
    empty=pd.DataFrame(columns=["start","end","length"])
    if n<4 or not np.isfinite(x).any(): return {"signal":x,"clipped":np.zeros(n,bool),"runs":empty}
    lo,hi=np.nanmin(x),np.nanmax(x); amp=hi-lo
    if not np.isfinite(amp) or amp<=0:return {"signal":x,"clipped":np.zeros(n,bool),"runs":empty}
    near=x>=hi-near_max_prop*amp
    d=np.abs(np.diff(x)); flat=np.zeros(n,bool)
    if n>1:
        flat[1:] |= d<=flat_diff_prop*amp; flat[:-1] |= d<=flat_diff_prop*amp
    cand=near&flat
    runs=[]; i=0
    while i<n:
        if not cand[i]: i+=1; continue
        j=i
        while j+1<n and cand[j+1]: j+=1
        if j-i+1>=int(min_run): runs.append((i,j,j-i+1))
        i=j+1
    clipped=np.zeros(n,bool)
    for a,b,_ in runs:clipped[a:b+1]=True
    y=x.copy()
    good=(~clipped)&np.isfinite(x)
    if clipped.any() and good.sum()>=4:
        f=interpolate.CubicSpline(np.where(good)[0],x[good],bc_type="natural",extrapolate=True)
        y[clipped]=f(np.where(clipped)[0])
    rdf=pd.DataFrame([{"start":a+1,"end":b+1,"length":ln} for a,b,ln in runs]) if runs else empty
    return {"signal":y,"clipped":clipped,"runs":rdf}


def enhance_gazepoint_ppg_peaks(x,sampling_rate_hz,iterations=2):
    y=_interp_na(x)
    if not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0: raise ValueError("Invalid sampling rate.")
    for _ in range(max(0,int(iterations))):
        k=max(3,round(.75*sampling_rate_hz)); base=_running_mean(y,k);base=np.where(np.isfinite(base),base,np.nanmean(y));y=y-base
        s=_mad(y,1.0)
        if not np.isfinite(s) or s<=0:s=np.nanstd(y,ddof=1)
        if np.isfinite(s) and s>0:y=y/s
    return y


def filter_gazepoint_ppg_butterworth(x,cutoff_hz=5,sampling_rate_hz=None,passes=1):
    x=_interp_na(x)
    if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0: raise ValueError("Invalid sampling rate.")
    if not np.isfinite(cutoff_hz) or cutoff_hz<=0 or cutoff_hz>=sampling_rate_hz/2:raise ValueError("`cutoff_hz` must be between 0 and Nyquist frequency.")
    k=math.tan(math.pi*cutoff_hz/sampling_rate_hz); norm=1/(1+math.sqrt(2)*k+k*k)
    b0=k*k*norm;b1=2*b0;b2=b0;a1=2*(k*k-1)*norm;a2=(1-math.sqrt(2)*k+k*k)*norm
    def one(sig):
        y=np.zeros(len(sig),float)
        for i in range(len(sig)):
            x0=sig[i];x1=sig[i-1] if i>0 else sig[i];x2=sig[i-2] if i>1 else x1
            y1=y[i-1] if i>0 else sig[i];y2=y[i-2] if i>1 else y1
            y[i]=b0*x0+b1*x1+b2*x2-a1*y1-a2*y2
        return y
    y=x
    for _ in range(max(1,int(passes))):y=one(y)
    return y


def correct_gazepoint_ppg_hampel(x,sampling_rate_hz,window_seconds=1,n_sigmas=3):
    x=_interp_na(x)
    if not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0:raise ValueError("Invalid sampling rate.")
    med=_running_median(x,max(3,round(window_seconds*sampling_rate_hz)));res=x-med;s=_mad(res,1.4826)
    if not np.isfinite(s) or s<=0:return x
    y=x.copy();bad=np.abs(res)>n_sigmas*s;y[bad]=med[bad];return y


def _peak_rois(x,threshold,min_distance):
    above=(x>threshold)&np.isfinite(x)&np.isfinite(threshold)
    peaks=[];i=0;n=len(x)
    while i<n:
        if not above[i]:i+=1;continue
        j=i
        while j+1<n and above[j+1]:j+=1
        idx=np.arange(i,j+1);peaks.append(int(idx[np.argmax(x[idx])]))
        i=j+1
    kept=[]
    for p in sorted(set(peaks)):
        if not kept or p-kept[-1]>=min_distance:kept.append(p)
        elif x[p]>x[kept[-1]]:kept[-1]=p
    return np.asarray(kept,dtype=int)


def _high_precision(x,t,p,window_s=.1,target_hz=1000):
    pt=t[p];idx=np.where((t>=pt-window_s)&(t<=pt+window_s)&np.isfinite(x)&np.isfinite(t))[0]
    if len(idx)<4:return pt,x[p]
    nt=np.arange(t[idx].min(),t[idx].max()+.5/target_hz,1/target_hz)
    if len(nt)<3:return pt,x[p]
    try:y=interpolate.CubicSpline(t[idx],x[idx])(nt);j=int(np.nanargmax(y));return float(nt[j]),float(y[j])
    except Exception:return pt,x[p]


def detect_gazepoint_ppg_peaks(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,bpm_min=40,bpm_max=180,moving_average_seconds=.75,threshold_offsets=None,reconstruct_clipping=True,enhance_peaks=False,lowpass_hz=None,hampel=False,high_precision=True):
    if threshold_offsets is None:threshold_offsets=np.arange(-.25,1.2501,.05)
    if not isinstance(data,pd.DataFrame):
        arr=np.asarray(data)
        if arr.ndim!=1:raise TypeError("`data` must be a data frame or numeric vector.")
        if sampling_rate_hz is None:raise ValueError("`sampling_rate_hz` is required for numeric signal input.")
        data=pd.DataFrame({"signal":arr,"time_s":np.arange(len(arr))/sampling_rate_hz});signal_col="signal";time_col="time_s"
    prep=prepare_gazepoint_heartpy_input(data,signal_col,time_col,group_cols,sampling_rate_hz)
    tbl=prep["signal_table"].reset_index(drop=True);fs=float(prep["sampling_rate_hz"])
    if not np.isfinite(fs) or fs<=0:raise ValueError("Could not infer a valid sampling rate.")
    groups=_group_indices(tbl,group_cols);peak_rows=[];sig_rows=[];diag=[]
    for g,idx in groups.items():
        d=tbl.iloc[idx].reset_index(drop=True);x0=_interp_na(d.signal);t=_as_num(d.time_s)
        if (~np.isfinite(t)).any():t=np.arange(len(x0))/fs
        clip={"signal":x0,"clipped":np.zeros(len(x0),bool),"runs":pd.DataFrame()};x=x0.copy()
        if reconstruct_clipping:clip=reconstruct_gazepoint_ppg_clipping(x);x=clip["signal"]
        if hampel:x=correct_gazepoint_ppg_hampel(x,fs)
        if lowpass_hz is not None:x=filter_gazepoint_ppg_butterworth(x,lowpass_hz,fs)
        if enhance_peaks:x=enhance_gazepoint_ppg_peaks(x,fs)
        k=max(3,round((moving_average_seconds*2)*fs));ma=_running_mean(x,k);ma=np.where(np.isfinite(ma),ma,np.nanmean(x));sx=np.nanstd(x,ddof=1);sx=sx if np.isfinite(sx) and sx>0 else 1
        md=max(1,math.floor(fs*60/bpm_max*.8));fits=[]
        for off in threshold_offsets:
            pk=_peak_rois(x,ma+off*sx,md);dur=(np.nanmax(t)-np.nanmin(t))/60;bpm=len(pk)/dur if len(pk)>=2 and dur>0 else np.nan
            rr=np.diff(t[pk])*1000 if len(pk)>1 else np.array([]);sdsd=np.nanstd(np.diff(rr),ddof=1) if len(rr)>=3 else np.inf
            fits.append((off,len(pk),bpm,sdsd))
        cand=[z for z in fits if np.isfinite(z[2]) and bpm_min<=z[2]<=bpm_max and z[1]>=3]
        best=min(cand,key=lambda z:z[3] if z[3]>0 else np.inf)[0] if cand else 0
        thr=ma+best*sx;pk=_peak_rois(x,thr,md)
        for p in pk:
            pt,pv=_high_precision(x,t,p) if high_precision else (float(t[p]),float(x[p]))
            row={"group":g,"peak_index":int(p+1),"peak_time_s":pt,"peak_value":pv,"accepted":True}
            if group_cols:
                cols=[group_cols] if isinstance(group_cols,str) else list(group_cols)
                for c in cols:row[c]=d.iloc[0][c]
            peak_rows.append(row)
        for i in range(len(x)):
            row={"group":g,"sample_index":i+1,"time_s":t[i],"signal_raw":x0[i],"signal_processed":x[i],"moving_average":ma[i],"threshold":thr[i],"clipped":bool(clip["clipped"][i])}
            if group_cols:
                cols=[group_cols] if isinstance(group_cols,str) else list(group_cols)
                for c in cols:row[c]=d.iloc[i][c]
            sig_rows.append(row)
        diag.append({"group":g,"sampling_rate_hz":fs,"best_offset":best,"n_peaks":len(pk),"clipped_samples":int(np.sum(clip["clipped"]))})
    peaks=pd.DataFrame(peak_rows,columns=(([group_cols] if isinstance(group_cols,str) else list(group_cols or []))+["group","peak_index","peak_time_s","peak_value","accepted"]))
    return {"peaks":peaks,"processed_signal":pd.DataFrame(sig_rows),"diagnostics":pd.DataFrame(diag),"settings":{"sampling_rate_hz":fs,"bpm_min":bpm_min,"bpm_max":bpm_max,"moving_average_seconds":moving_average_seconds,"reconstruct_clipping":reconstruct_clipping,"enhance_peaks":enhance_peaks,"lowpass_hz":lowpass_hz,"hampel":hampel,"high_precision":high_precision}}


def reject_gazepoint_ppg_peaks(peaks,group_col="group",rr_tolerance=.30,min_rr_ms=300):
    if not isinstance(peaks,pd.DataFrame) or peaks.empty:return peaks.copy() if isinstance(peaks,pd.DataFrame) else peaks
    if "peak_time_s" not in peaks:raise ValueError("`peaks` must contain `peak_time_s`.")
    out=peaks.copy();
    if group_col not in out:out[group_col]="all"
    out=out.sort_values([group_col,"peak_time_s"],kind="stable").reset_index(drop=True);out["rr_ms"]=np.nan;out["accepted"]=True
    for _,idx in out.groupby(group_col,sort=False).groups.items():
        idx=np.asarray(list(idx));
        if len(idx)<3:continue
        rr=np.r_[np.nan,np.diff(out.loc[idx,"peak_time_s"].to_numpy(float))*1000];m=np.nanmean(rr);tol=max(rr_tolerance*m,min_rr_ms);bad=np.isfinite(rr)&((rr<m-tol)|(rr>m+tol));out.loc[idx,"rr_ms"]=rr;out.loc[idx[bad],"accepted"]=False
    return out


def _rr_from_peaks(peaks,group_col="group"):
    if not isinstance(peaks,pd.DataFrame) or peaks.empty:return pd.DataFrame(columns=["group","interval_index","peak_time_s","rr_ms"])
    if "peak_time_s" not in peaks:raise ValueError("`peaks` must contain `peak_time_s`.")
    d=peaks.copy();
    if "accepted" not in d:d["accepted"]=True
    if group_col not in d:d[group_col]="all"
    d=d[(d.accepted==True)&np.isfinite(pd.to_numeric(d.peak_time_s,errors="coerce"))]
    rows=[]
    for g,z in d.groupby(group_col,sort=True):
        z=z.sort_values("peak_time_s");t=z.peak_time_s.to_numpy(float)
        for i,r in enumerate(np.diff(t),1):rows.append({"group":str(g),"interval_index":i,"peak_time_s":t[i],"rr_ms":r*1000})
    return pd.DataFrame(rows)


def _resample_rr(rr_ms,rr_time_s=None,resample_hz=4):
    rr=_as_num(rr_ms);ok=np.isfinite(rr)&(rr>0);rr=rr[ok]
    if len(rr)==0:return np.array([]),np.array([])
    t=np.cumsum(rr)/1000 if rr_time_s is None else _as_num(rr_time_s)[ok]
    ok=np.isfinite(t);t=t[ok];rr=rr[ok]
    if len(rr)<4 or np.ptp(t)<=0:return np.array([]),np.array([])
    grid=np.arange(t.min(),t.max()+1e-12,1/resample_hz)
    if len(grid)<4:return np.array([]),np.array([])
    y=np.interp(grid,t,rr);return grid,y-np.mean(y)


def _fft_psd(y,fs):
    y=np.asarray(y,float);y=y[np.isfinite(y)];n=len(y)
    if n<4:return pd.DataFrame(columns=["frequency_hz","psd"])
    y=y-y.mean();fy=np.fft.fft(y);psd=np.abs(fy)**2/(n*fs);freq=np.arange(n)*fs/n;keep=np.arange(max(1,n//2))
    return pd.DataFrame({"frequency_hz":freq[keep],"psd":psd[keep]})


def estimate_gazepoint_breathing_rate_from_ibi(rr_ms,rr_time_s=None,resample_hz=4,breathing_band=(.10,.50)):
    t,y=_resample_rr(rr_ms,rr_time_s,resample_hz)
    ps=_fft_psd(y,resample_hz)
    if ps.empty:return {"breathing_rate_hz":np.nan,"frequency":np.array([]),"psd":np.array([]),"band":breathing_band}
    keep=(ps.frequency_hz>=breathing_band[0])&(ps.frequency_hz<=breathing_band[1])&np.isfinite(ps.psd)
    br=float(ps.loc[keep].sort_values("psd",ascending=False).iloc[0].frequency_hz) if keep.any() else np.nan
    return {"breathing_rate_hz":br,"frequency":ps.frequency_hz.to_numpy(),"psd":ps.psd.to_numpy(),"band":breathing_band}


def compute_gazepoint_ppg_measures(peaks,group_col="group"):
    if not isinstance(peaks,pd.DataFrame) or peaks.empty:return pd.DataFrame()
    if "peak_time_s" not in peaks:raise ValueError("`peaks` must contain `peak_time_s`.")
    d=peaks.copy();
    if "accepted" not in d:d["accepted"]=True
    if group_col not in d:d[group_col]="all"
    rows=[]
    for g,z in d.groupby(group_col,sort=True):
        z=z[(z.accepted==True)&np.isfinite(pd.to_numeric(z.peak_time_s,errors="coerce"))].sort_values("peak_time_s");t=z.peak_time_s.to_numpy(float)
        base={"group":str(g),"n_peaks":len(t)}
        if len(t)<3:
            rows.append(base|{k:np.nan for k in ["bpm","ibi_ms","sdnn_ms","sdsd_ms","rmssd_ms","pnn20","pnn50","mad_rr_ms","lf","hf","hf_lf","breathing_rate_hz"]});continue
        rr=np.diff(t)*1000;dr=np.diff(rr);dur=np.ptp(t)/60;_,y=_resample_rr(rr,None,4);ps=_fft_psd(y,4)
        def bp(lo,hi):
            q=ps[(ps.frequency_hz>=lo)&(ps.frequency_hz<hi)];return float(q.psd.sum()) if len(q) else np.nan
        lf,hf=bp(.05,.15),bp(.15,.50);br=estimate_gazepoint_breathing_rate_from_ibi(rr)["breathing_rate_hz"]
        rows.append(base|{"bpm":len(t)/dur if dur>0 else np.nan,"ibi_ms":float(np.mean(rr)),"sdnn_ms":float(np.std(rr,ddof=1)) if len(rr)>1 else np.nan,"sdsd_ms":float(np.std(dr,ddof=1)) if len(dr)>1 else np.nan,"rmssd_ms":float(np.sqrt(np.mean(dr**2))) if len(dr) else np.nan,"pnn20":float(np.mean(np.abs(dr)>20)) if len(dr) else np.nan,"pnn50":float(np.mean(np.abs(dr)>50)) if len(dr) else np.nan,"mad_rr_ms":_mad(rr),"lf":lf,"hf":hf,"hf_lf":hf/lf if np.isfinite(lf) and lf>0 else np.nan,"breathing_rate_hz":br})
    return pd.DataFrame(rows)


def plot_gazepoint_ppg_peak_detection(detection,group=None,accepted_only=False):
    if not isinstance(detection,dict) or "processed_signal" not in detection:raise ValueError("Invalid detection object.")
    s=detection["processed_signal"];p=detection["peaks"]
    if group is not None:s=s[s.group==group];p=p[p.group==group]
    if accepted_only and "accepted" in p:p=p[p.accepted==True]
    fig,ax=plt.subplots();ax.plot(s.time_s,s.signal_processed);ax.plot(s.time_s,s.moving_average,ls="--");ax.plot(s.time_s,s.threshold,ls=":")
    if len(p):ax.scatter(p.peak_time_s,p.peak_value);ax.set_xlabel("Time (s)");return fig


def create_gazepoint_heartpy_report(detection,output_dir=None,prefix="gazepoint_heartpy"):
    if not isinstance(detection,dict) or "peaks" not in detection:raise ValueError("Invalid detection object.")
    peaks=reject_gazepoint_ppg_peaks(detection["peaks"]);measures=compute_gazepoint_ppg_measures(peaks);diag=detection.get("diagnostics",pd.DataFrame());paths=[]
    if output_dir is not None:
        p=Path(output_dir);p.mkdir(parents=True,exist_ok=True)
        files=[p/f"{prefix}_peaks.csv",p/f"{prefix}_measures.csv",p/f"{prefix}_diagnostics.csv",p/f"{prefix}_report.txt"]
        peaks.to_csv(files[0],index=False);measures.to_csv(files[1],index=False);diag.to_csv(files[2],index=False);files[3].write_text(f"Gazepoint HeartPy-style pulse/PPG report\nGenerated: {datetime.now()}\nGroups: {peaks.group.nunique() if 'group' in peaks else 0}\nPeaks: {len(peaks)}\n")
        paths=[str(f.resolve()) for f in files]
    return {"peaks":peaks,"measures":measures,"diagnostics":diag,"path":paths}


def run_gazepoint_heartpy_crosscheck(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,**kwargs):
    native=detect_gazepoint_ppg_peaks(data,signal_col,time_col,group_cols,sampling_rate_hz,**kwargs);report=create_gazepoint_heartpy_report(native);avail=importlib.util.find_spec("heartpy") is not None;hp=None
    if avail:
        try:
            import heartpy as h
            sig=native["processed_signal"]["signal_raw"].to_numpy(float);wd,m=h.process(sig,float(native["settings"]["sampling_rate_hz"]),report_time=False);hp={"working_data":wd,"measures":m}
        except Exception as e:hp={"error":str(e)}
    return {"native":report,"heartpy":hp,"heartpy_available":avail}


def estimate_gazepoint_samplerate_mstimer(mstimer,robust=True):
    x=_as_num(mstimer);x=x[np.isfinite(x)]
    if len(x)<2:return {"sampling_rate_hz":np.nan,"interval_ms":np.nan,"n_intervals":0}
    d=np.diff(np.unique(np.sort(x)));d=d[(d>0)&np.isfinite(d)]
    if len(d)==0:return {"sampling_rate_hz":np.nan,"interval_ms":np.nan,"n_intervals":0}
    v=float(np.median(d) if robust else np.mean(d));return {"sampling_rate_hz":1000/v,"interval_ms":v,"n_intervals":len(d),"interval_iqr_ms":_iqr(d)}


def estimate_gazepoint_samplerate_datetime(datetime,format=None,tz="UTC",robust=True):
    t=pd.to_datetime(pd.Series(datetime),format=format,utc=True,errors="coerce").dropna().drop_duplicates().sort_values()
    if len(t)<2:return {"sampling_rate_hz":np.nan,"interval_seconds":np.nan,"n_intervals":0}
    d=t.diff().dt.total_seconds().dropna().to_numpy(dtype=float,copy=True);d=d[(d>0)&np.isfinite(d)]
    if len(d)==0:return {"sampling_rate_hz":np.nan,"interval_seconds":np.nan,"n_intervals":0}
    v=float(np.median(d) if robust else np.mean(d));return {"sampling_rate_hz":1/v,"interval_seconds":v,"n_intervals":len(d),"interval_iqr_seconds":_iqr(d)}


def scale_gazepoint_ppg_signal(x,method="zscore",range=(0,1)):
    x=_as_num(x)
    if method=="none":return x
    if method=="center":return x-np.nanmean(x)
    if method=="zscore":
        s=np.nanstd(x,ddof=1);return (x-np.nanmean(x))/s if np.isfinite(s) and s>0 else np.full(len(x),np.nan)
    if method=="robust":
        med=np.nanmedian(x);s=_mad(x);return (x-med)/s if np.isfinite(s) and s>0 else np.full(len(x),np.nan)
    if method=="minmax":
        lo,hi=np.nanmin(x),np.nanmax(x);return range[0]+((x-lo)/(hi-lo))*(range[1]-range[0]) if hi>lo else np.full(len(x),np.nan)
    raise ValueError("Invalid scaling method.")


def scale_gazepoint_ppg_sections(data,signal_col=None,section_cols=None,method="zscore",output_col="ppg_scaled",range=(0,1)):
    if not isinstance(data,pd.DataFrame):return scale_gazepoint_ppg_signal(data,method,range)
    if signal_col is None:signal_col=_pick_col(data,["PULSE","PPG","HRP","PULSE_SIGNAL","heart_signal","biometric_pulse"],"pulse/PPG signal")
    if signal_col not in data:raise ValueError("`signal_col` not found.")
    out=data.copy();out[output_col]=np.nan
    if not section_cols:out[output_col]=scale_gazepoint_ppg_signal(out[signal_col],method,range);return out
    if isinstance(section_cols,str):section_cols=[section_cols]
    if any(c not in out for c in section_cols):raise ValueError("Missing section columns.")
    for _,idx in out.groupby(section_cols[0] if len(section_cols)==1 else section_cols,dropna=False).groups.items():out.loc[idx,output_col]=scale_gazepoint_ppg_signal(out.loc[idx,signal_col],method,range)
    return out


def flip_gazepoint_ppg_signal(x,method="negative"):
    x=_as_num(x)
    if method=="negative":return -x
    if method=="max_minus":return np.nanmax(x)-x
    raise ValueError("Invalid flip method.")


def remove_gazepoint_ppg_baseline_wander(x,sampling_rate_hz,method="median",window_seconds=2):
    x=_interp_na(x)
    if sampling_rate_hz<=0:raise ValueError("Invalid sampling rate.")
    k=max(3,round(window_seconds*sampling_rate_hz));base=_running_median(x,k) if method=="median" else _running_mean(x,k);base=np.where(np.isfinite(base),base,np.nanmean(x));return x-base


def smooth_gazepoint_ppg_signal(x,sampling_rate_hz,method="mean",window_seconds=.10):
    x=_interp_na(x)
    if sampling_rate_hz<=0:raise ValueError("Invalid sampling rate.")
    k=max(3,round(window_seconds*sampling_rate_hz));y=_running_median(x,k) if method=="median" else _running_mean(x,k);return np.where(np.isfinite(y),y,np.nanmean(x))


def filter_gazepoint_ppg_signal(x,sampling_rate_hz,type="lowpass",low_hz=None,high_hz=None,passes=1):
    x=_interp_na(x)
    if sampling_rate_hz<=0:raise ValueError("Invalid sampling rate.")
    if type=="lowpass":return filter_gazepoint_ppg_butterworth(x,5 if high_hz is None else high_hz,sampling_rate_hz,passes)
    if type=="highpass":
        lo=filter_gazepoint_ppg_butterworth(x,.5 if low_hz is None else low_hz,sampling_rate_hz,passes);return x-lo
    if type=="bandpass":
        if low_hz is None or high_hz is None:raise ValueError("Supply both `low_hz` and `high_hz` for bandpass filtering.")
        return filter_gazepoint_ppg_signal(filter_gazepoint_ppg_signal(x,sampling_rate_hz,"highpass",low_hz=low_hz,passes=passes),sampling_rate_hz,"lowpass",high_hz=high_hz,passes=passes)
    if type=="notch":
        if low_hz is None or high_hz is None:raise ValueError("Supply both `low_hz` and `high_hz` for notch filtering.")
        fy=np.fft.fft(x);n=len(x);f=np.arange(n)*sampling_rate_hz/n;fa=np.where(f>sampling_rate_hz/2,sampling_rate_hz-f,f);fy[(fa>=low_hz)&(fa<=high_hz)]=0;return np.fft.ifft(fy).real
    raise ValueError("Invalid filter type.")


def clean_gazepoint_rr_intervals(rr_ms,method="quotient",group_col="group",quotient_threshold=.20,iqr_multiplier=1.5,z_threshold=3.5):
    if method not in {"quotient","iqr","modified_z","zscore","none"}:raise ValueError("Invalid cleaning method.")
    if isinstance(rr_ms,pd.DataFrame) and "peak_time_s" in rr_ms:
        p=rr_ms.copy();
        if "accepted" not in p:p["accepted"]=True
        if group_col not in p:p[group_col]="all"
        p=p.sort_values([group_col,"peak_time_s"],kind="stable").reset_index(drop=True);p["rr_ms"]=np.nan;p["rr_clean"]=True;p["rr_clean_reason"]="accepted"
        for _,idx in p.groupby(group_col,sort=False).groups.items():
            idx=np.asarray(list(idx));
            if len(idx)<3:continue
            rr=np.r_[np.nan,np.diff(p.loc[idx,"peak_time_s"].to_numpy(float))*1000];c=clean_gazepoint_rr_intervals(rr[1:],method,quotient_threshold=quotient_threshold,iqr_multiplier=iqr_multiplier,z_threshold=z_threshold);p.loc[idx,"rr_ms"]=rr;p.loc[idx[1:],"rr_clean"]=c.accepted.to_numpy();p.loc[idx[1:],"rr_clean_reason"]=c.reason.to_numpy();p.loc[idx[1:],"accepted"]=p.loc[idx[1:],"accepted"].to_numpy(bool)&c.accepted.to_numpy(bool)
        return p
    rr=_as_num(rr_ms);acc=np.isfinite(rr)&(rr>0);reason=np.where(acc,"accepted","non_finite_or_non_positive").astype(object);out=pd.DataFrame({"interval_index":np.arange(1,len(rr)+1),"rr_ms":rr,"accepted":acc,"reason":reason})
    if method=="none" or not acc.any():return out
    v=rr[acc];a=np.ones(len(v),bool);r=np.array(["accepted"]*len(v),object)
    if method=="quotient" and len(v)>=2:
        ratio=np.r_[1,np.minimum(v[1:]/v[:-1],v[:-1]/v[1:])];bad=ratio<(1-quotient_threshold);a[bad]=False;r[bad]="quotient_threshold"
    elif method=="iqr":
        q=np.quantile(v,[.25,.75]);iq=q[1]-q[0];bad=(v<q[0]-iqr_multiplier*iq)|(v>q[1]+iqr_multiplier*iq);a[bad]=False;r[bad]="iqr_threshold"
    elif method=="modified_z":
        med=np.median(v);madv=np.median(np.abs(v-med));
        if madv>0:
            bad=np.abs(.6745*(v-med)/madv)>z_threshold;a[bad]=False;r[bad]="modified_z_threshold"
    elif method=="zscore":
        s=np.std(v,ddof=1)
        if np.isfinite(s) and s>0:
            bad=np.abs((v-np.mean(v))/s)>z_threshold;a[bad]=False;r[bad]="zscore_threshold"
    out.loc[acc,"accepted"]=a;out.loc[acc,"reason"]=r;return out


def compute_gazepoint_ppg_frequency_measures(peaks=None,rr_ms=None,rr_time_s=None,group_col="group",method="welch",resample_hz=4,bands=None,welch_window_seconds=64,welch_overlap=.5):
    if bands is None:bands={"lf":(.05,.15),"hf":(.15,.50)}
    def one(rr,t=None,g="all"):
        grid,y=_resample_rr(rr,t,resample_hz)
        if len(y)==0:return pd.DataFrame([{"group":g,"method":method,"lf":np.nan,"hf":np.nan,"hf_lf":np.nan,"total_power":np.nan,"peak_frequency_hz":np.nan,"breathing_rate_hz":np.nan}])
        if method=="welch":
            nper=min(len(y),max(8,round(welch_window_seconds*resample_hz)));f,p=sp_signal.welch(y,fs=resample_hz,nperseg=nper,noverlap=min(nper-1,round(nper*welch_overlap)),window="hann",detrend=False,scaling="density")
        else:
            ps=_fft_psd(y,resample_hz);f=ps.frequency_hz.to_numpy();p=ps.psd.to_numpy()
        vals={k:float(np.sum(p[(f>=b[0])&(f<b[1])])) if np.any((f>=b[0])&(f<b[1])) else np.nan for k,b in bands.items()};lf=vals.get("lf",np.nan);hf=vals.get("hf",np.nan);br=estimate_gazepoint_breathing_rate_from_ibi(rr,t,resample_hz)["breathing_rate_hz"]
        return pd.DataFrame([{"group":g,"method":method,"lf":lf,"hf":hf,"hf_lf":hf/lf if np.isfinite(lf) and lf>0 else np.nan,"total_power":float(np.nansum(p)),"peak_frequency_hz":float(f[np.nanargmax(p)]) if len(p) else np.nan,"breathing_rate_hz":br}])
    if peaks is not None:
        r=_rr_from_peaks(peaks,group_col);return pd.concat([one(z.rr_ms,z.peak_time_s,g) for g,z in r.groupby("group",sort=True)],ignore_index=True) if len(r) else pd.DataFrame()
    if rr_ms is None:raise ValueError("Supply either `peaks` or `rr_ms`.")
    return one(rr_ms,rr_time_s)


def check_gazepoint_ppg_binary_quality(measures=None,peaks=None,min_peaks=5,bpm_range=(40,180),max_missing_prop=.25):
    if measures is None:
        if peaks is None:raise ValueError("Supply `measures` or `peaks`.")
        measures=compute_gazepoint_ppg_measures(peaks)
    if not isinstance(measures,pd.DataFrame) or measures.empty:return pd.DataFrame()
    out=measures.copy()
    if "n_peaks" not in out:out["n_peaks"]=np.nan
    if "bpm" not in out:out["bpm"]=np.nan
    if "missing_prop" not in out:out["missing_prop"]=np.nan
    enough=pd.to_numeric(out.n_peaks,errors="coerce")>=min_peaks;bpm=pd.to_numeric(out.bpm,errors="coerce").between(*bpm_range);miss=out.missing_prop.isna()|(pd.to_numeric(out.missing_prop,errors="coerce")<=max_missing_prop);out["quality_pass"]=enough&bpm&miss
    out["quality_reason"]=["pass" if ok else ";".join(r for r,b in [("too_few_peaks",e),("implausible_bpm",bp),("high_missingness",m)] if not b) or "fail" for ok,e,bp,m in zip(out.quality_pass,enough,bpm,miss)]
    return out


def process_gazepoint_ppg_heartpy_style(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,clean_rr=True,clean_rr_method="quotient",frequency_method="welch",output_dir=None,**kwargs):
    det=detect_gazepoint_ppg_peaks(data,signal_col,time_col,group_cols,sampling_rate_hz,**kwargs);peaks=reject_gazepoint_ppg_peaks(det["peaks"]);peaks=clean_gazepoint_rr_intervals(peaks,clean_rr_method) if clean_rr else peaks;meas=compute_gazepoint_ppg_measures(peaks);freq=compute_gazepoint_ppg_frequency_measures(peaks=peaks,method=frequency_method);q=check_gazepoint_ppg_binary_quality(measures=meas);rep=create_gazepoint_heartpy_report(det,output_dir)
    return {"detection":det,"peaks":peaks,"measures":meas,"frequency":freq,"quality":q,"report":rep,"settings":{"clean_rr":clean_rr,"clean_rr_method":clean_rr_method,"frequency_method":frequency_method,"output_dir":output_dir}}


def process_gazepoint_ppg_segmentwise(data,signal_col=None,time_col=None,group_cols=None,sampling_rate_hz=None,window_seconds=60,overlap=.5,min_segment_seconds=10,clean_rr=True,clean_rr_method="quotient",frequency_method="welch",**kwargs):
    if overlap>=1:raise ValueError("`overlap` must be smaller than 1.")
    if not isinstance(data,pd.DataFrame):
        if sampling_rate_hz is None:raise ValueError("`sampling_rate_hz` is required for numeric input.")
        arr=np.asarray(data);data=pd.DataFrame({"time_s":np.arange(len(arr))/sampling_rate_hz,"signal":arr});signal_col="signal";time_col="time_s"
    prep=prepare_gazepoint_heartpy_input(data,signal_col,time_col,group_cols,sampling_rate_hz);tbl=prep["signal_table"].reset_index(drop=True);fs=prep["sampling_rate_hz"];groups=_group_indices(tbl,group_cols);segs=[];pl=[];ml=[];fl=[];sid=0
    for g,idx in groups.items():
        d=tbl.iloc[idx].reset_index(drop=True);t=d.time_s.to_numpy(float);start=t.min();maxstart=t.max()-window_seconds;starts=[start] if maxstart<start else np.arange(start,maxstart+1e-12,window_seconds*(1-overlap))
        for s in starts:
            e=s+window_seconds;mask=(t>=s)&(t<e);z=d.loc[mask].copy();dur=np.ptp(z.time_s) if len(z) else 0
            if len(z)==0 or dur<min_segment_seconds:continue
            sid+=1
            try:
                det=detect_gazepoint_ppg_peaks(z,"signal","time_s",sampling_rate_hz=fs,**kwargs);pk=reject_gazepoint_ppg_peaks(det["peaks"]);pk=clean_gazepoint_rr_intervals(pk,clean_rr_method) if clean_rr else pk;me=compute_gazepoint_ppg_measures(pk);fr=compute_gazepoint_ppg_frequency_measures(peaks=pk,method=frequency_method);segs.append({"segment_id":sid,"group":g,"start_s":s,"end_s":e,"n_samples":len(z),"n_peaks":len(pk),"status":"ok","message":""})
                if len(pk):pk=pk.copy();pk["segment_id"]=sid;pk["segment_group"]=g;pl.append(pk)
                if len(me):me=me.copy();me["segment_id"]=sid;me["segment_group"]=g;me["start_s"]=s;me["end_s"]=e;ml.append(me)
                if len(fr):fr=fr.copy();fr["segment_id"]=sid;fr["segment_group"]=g;fr["start_s"]=s;fr["end_s"]=e;fl.append(fr)
            except Exception as ex:segs.append({"segment_id":sid,"group":g,"start_s":s,"end_s":e,"n_samples":len(z),"status":"error","message":str(ex)})
    return {"segments":pd.DataFrame(segs),"peaks":pd.concat(pl,ignore_index=True) if pl else pd.DataFrame(),"measures":pd.concat(ml,ignore_index=True) if ml else pd.DataFrame(),"frequency":pd.concat(fl,ignore_index=True) if fl else pd.DataFrame(),"settings":{"sampling_rate_hz":fs,"window_seconds":window_seconds,"overlap":overlap,"min_segment_seconds":min_segment_seconds,"clean_rr":clean_rr,"clean_rr_method":clean_rr_method,"frequency_method":frequency_method}}


def plot_gazepoint_ppg_segmentwise(segmentwise,measure="bpm"):
    if not isinstance(segmentwise,dict) or "measures" not in segmentwise:raise ValueError("`segmentwise` must be returned by process_gazepoint_ppg_segmentwise().")
    d=segmentwise["measures"]
    if d.empty:raise ValueError("No segmentwise measures available.")
    if measure not in d:raise ValueError("Measure column not found: "+measure)
    fig,ax=plt.subplots();ax.plot(d.start_s if "start_s" in d else np.arange(1,len(d)+1),d[measure],marker="o");return fig


def plot_gazepoint_ppg_poincare(peaks=None,rr_ms=None,group_col="group"):
    rr=_rr_from_peaks(peaks,group_col).rr_ms.to_numpy() if peaks is not None else _as_num(rr_ms);rr=rr[np.isfinite(rr)&(rr>0)]
    if len(rr)<3:raise ValueError("At least three valid RR intervals are required.")
    x,y=rr[:-1],rr[1:];dr=y-x;sd1=np.sqrt(np.var(dr,ddof=1)/2);sd2=np.sqrt(2*np.var(rr,ddof=1)-.5*np.var(dr,ddof=1));fig,ax=plt.subplots();ax.scatter(x,y);lo=min(x.min(),y.min());hi=max(x.max(),y.max());ax.plot([lo,hi],[lo,hi],ls="--");fig.gazepoint_result={"data":pd.DataFrame({"rr_n_ms":x,"rr_next_ms":y}),"sd1_ms":sd1,"sd2_ms":sd2,"sd1_sd2":sd1/sd2 if sd2>0 else np.nan};return fig


def plot_gazepoint_ppg_breathing(rr_ms,rr_time_s=None,resample_hz=4,breathing_band=(.10,.50)):
    br=estimate_gazepoint_breathing_rate_from_ibi(rr_ms,rr_time_s,resample_hz,breathing_band)
    if len(br["frequency"])==0:raise ValueError("No frequency spectrum available.")
    fig,ax=plt.subplots();ax.plot(br["frequency"],br["psd"]);return fig
