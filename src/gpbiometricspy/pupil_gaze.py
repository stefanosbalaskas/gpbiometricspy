from __future__ import annotations

import numpy as np
import pandas as pd

from ._helpers import as_list, ensure_df, group_indices, guess_col, mad, require_cols, time_seconds, r_sd


def _guess_pupil_cols(df, pupil_cols=None):
    if pupil_cols is not None:
        cols=as_list(pupil_cols); require_cols(df,cols,"pupil columns"); return cols
    exact=["pupil","pupil_size","pupil_diameter","pupil_left","pupil_right","left_pupil","right_pupil","left_pupil_diameter","right_pupil_diameter","LPD","RPD"]
    lower={str(c).lower():c for c in df.columns}; cols=[]
    for e in exact:
        if e.lower() in lower and lower[e.lower()] not in cols: cols.append(lower[e.lower()])
    for c in df.columns:
        s=str(c)
        if any(k in s.lower() for k in ["pupil","diameter"]) or s.upper() in {"LPD","RPD"}:
            if not any(k in s.lower() for k in ["valid","flag","blink","clean","imputed","outlier","spike","was_"]) and pd.api.types.is_numeric_dtype(df[c]) and c not in cols:
                cols.append(c)
    if not cols: raise ValueError("Could not identify pupil columns. Supply `pupil_cols` explicitly.")
    return cols


def _time_col(df,time_col=None,required=False):
    if time_col is not None:
        if time_col not in df.columns: raise ValueError("`time_col` not found in `data`.")
        return time_col
    return guess_col(df,["time_s","TIME","time","Time","timestamp","Timestamp","MSTIMER","TIME_TICK","FPOGS","BKPMIN"],"time",required)


def _validity_col(df,pupil):
    p=str(pupil)
    candidates=(['LPV','left_pupil_valid','pupil_left_valid'] if p.upper()=='LPD' else ['RPV','right_pupil_valid','pupil_right_valid'] if p.upper()=='RPD' else [p+'_valid',p+'_validity',p.replace('diameter','valid')])
    return guess_col(df,candidates,'validity',False)


def _invalid_matrix(df,cols,validity_cols=None,invalid_values=(0,),nonpositive_is_missing=True):
    out=np.zeros((len(df),len(cols)),dtype=bool)
    vc=as_list(validity_cols)
    if len(vc)==1 and len(cols)>1: vc=vc*len(cols)
    for i,c in enumerate(cols):
        x=pd.to_numeric(df[c],errors='coerce').to_numpy(float)
        bad=~np.isfinite(x)
        if invalid_values: bad |= np.isin(x,list(invalid_values))
        if nonpositive_is_missing: bad |= x<=0
        vcol=vc[i] if vc else _validity_col(df,c)
        if vcol is not None:
            if vcol not in df.columns: raise ValueError(f"Validity column not found: {vcol}")
            s=df[vcol]
            if pd.api.types.is_bool_dtype(s): bad |= ~s.fillna(False).to_numpy(bool)
            else:
                vv=pd.to_numeric(s,errors='coerce').to_numpy(float); bad |= ~np.isfinite(vv)|(vv<=0)
        out[:,i]=bad
    return out


def _runs(flag, idx, raw, sec, min_samples):
    rows=[]; start=None
    for j,v in enumerate(np.r_[flag,False]):
        if v and start is None: start=j
        if not v and start is not None:
            end=j-1
            if end-start+1>=min_samples:
                gs=int(idx[start]); ge=int(idx[end])
                rows.append({"start_index":gs+1,"end_index":ge+1,"onset_time":raw[gs],"offset_time":raw[ge],"duration_s":sec[ge]-sec[gs],"n_samples":end-start+1})
            start=None
    return pd.DataFrame(rows)


def detect_gazepoint_pupil_blinks(data,pupil_cols=None,time_col=None,group_cols=None,validity_cols=None,invalid_values=(0,),nonpositive_is_missing=True,combine="all",min_blink_samples=1,return_="intervals",**kwargs):
    if "return" in kwargs:
        if return_!="intervals": raise TypeError("Specify only one of return_ or return")
        return_=kwargs.pop("return")
    if kwargs: raise TypeError(f"Unexpected keyword(s): {', '.join(kwargs)}")
    df=ensure_df(data); combine=str(combine); return_=str(return_)
    if combine not in {'all','any'}: raise ValueError("combine must be 'all' or 'any'")
    if return_ not in {'intervals','onsets','flags'}: raise ValueError("return must be intervals, onsets, or flags")
    cols=_guess_pupil_cols(df,pupil_cols); tc=_time_col(df,time_col,False)
    raw=pd.to_numeric(df[tc],errors='coerce').to_numpy(float) if tc else np.arange(1,len(df)+1,dtype=float)
    sec=time_seconds(raw); inv=_invalid_matrix(df,cols,validity_cols,invalid_values,nonpositive_is_missing)
    flag=inv.all(1) if combine=='all' else inv.any(1); flag=np.nan_to_num(flag).astype(bool)
    if return_=='flags': return flag
    intervals=[]
    for _,idx in group_indices(df,group_cols):
        z=_runs(flag[idx],idx,raw,sec,int(min_blink_samples))
        if not z.empty:
            if group_cols:
                for c in as_list(group_cols): z.insert(len(z.columns)*0,c,df.loc[idx[0],c])
            intervals.append(z)
    if intervals:
        out=pd.concat(intervals,ignore_index=True); out.insert(0,'blink_id',np.arange(1,len(out)+1))
    else:
        out=pd.DataFrame(columns=['blink_id','start_index','end_index','onset_time','offset_time','duration_s','n_samples'])
    out.attrs['pupil_cols']=cols; out.attrs['blink_flags']=flag
    return out['onset_time'].to_numpy() if return_=='onsets' else out


def _impute(x,method='linear',max_gap=np.inf):
    s=pd.Series(np.asarray(x,float))
    if method=='linear': out=s.interpolate('linear',limit_area=None).ffill().bfill()
    elif method=='locf': out=s.ffill().bfill()
    elif method=='nocb': out=s.bfill().ffill()
    elif method=='nearest': out=s.interpolate('nearest',limit_direction='both').ffill().bfill()
    elif method=='constant':
        val=float(np.nanmedian(s.to_numpy())) if s.notna().any() else np.nan; out=s.fillna(val)
    else: raise ValueError("Unsupported imputation method")
    if np.isfinite(max_gap):
        na=s.isna().to_numpy(); start=None
        for i,v in enumerate(np.r_[na,False]):
            if v and start is None: start=i
            if not v and start is not None:
                if i-start>max_gap: out.iloc[start:i]=np.nan
                start=None
    return out.to_numpy(float)


def clean_gazepoint_pupil_signal(data,pupil_cols=None,time_col=None,group_cols=None,validity_cols=None,method='linear',max_gap=np.inf,spike_mad=6,combine='all',min_blink_samples=1,suffix='_clean',keep_flags=True):
    df=ensure_df(data).copy(); cols=_guess_pupil_cols(df,pupil_cols)
    if time_col is not None and time_col not in df.columns: raise ValueError("`time_col` not found in `data`.")
    blink=detect_gazepoint_pupil_blinks(df,cols,time_col,None,validity_cols,combine=combine,min_blink_samples=min_blink_samples,return_='flags')
    inv=_invalid_matrix(df,cols,validity_cols); groups=group_indices(df,group_cols); summaries=[]
    for j,c in enumerate(cols):
        x=pd.to_numeric(df[c],errors='coerce').to_numpy(float); invalid=inv[:,j]|blink
        good=x[~invalid]; med=np.nanmedian(good) if good.size else np.nan; sc=mad(good,1.4826)
        if not np.isfinite(sc) or sc==0:
            q=np.nanpercentile(good,[25,75]) if good.size else [np.nan,np.nan]; sc=(q[1]-q[0])/1.349
        spike=np.zeros(len(x),bool) if not np.isfinite(sc) or sc==0 else np.nan_to_num(np.abs(x-med)>spike_mad*sc).astype(bool)
        dirty=invalid|spike; work=x.copy(); work[dirty]=np.nan; cleaned=work.copy()
        for _,idx in groups: cleaned[idx]=_impute(work[idx],method,max_gap)
        imp=np.isnan(work)&np.isfinite(cleaned); outcol=c+suffix; df[outcol]=cleaned
        if keep_flags:
            df[c+'_was_blink']=blink; df[c+'_was_spike']=spike; df[c+'_was_pupil_imputed']=imp
        summaries.append({"column":c,"clean_column":outcol,"n_blink_samples":int(blink.sum()),"n_invalid_samples":int(invalid.sum()),"n_spike_samples":int(spike.sum()),"n_imputed_samples":int(imp.sum()),"n_missing_after":int(np.isnan(cleaned).sum()),"method":method,"max_gap":max_gap})
    df.attrs['pupil_cols']=cols; df.attrs['pupil_cleaning_summary']=pd.DataFrame(summaries)
    return df


def summarize_gazepoint_fixations(fixDF,duration_col=None,x_col=None,y_col=None,participant_col=None,trial_col=None,aoi_col=None,group_cols=None,duration_unit='auto'):
    df=ensure_df(fixDF,'fixDF')
    duration_col=duration_col or guess_col(df,['duration_s','duration','fixation_duration','fix_duration','FPOGD'],'fixation duration',True)
    require_cols(df,[duration_col],"duration_col")
    x_col=x_col or guess_col(df,['x','X','fix_x','fixation_x','FPOGX','BPOGX'],'fixation x',False)
    y_col=y_col or guess_col(df,['y','Y','fix_y','fixation_y','FPOGY','BPOGY'],'fixation y',False)
    participant_col=participant_col or guess_col(df,['participant','participant_id','subject','id','USER'],'participant',False)
    trial_col=trial_col or guess_col(df,['trial','trial_id','TRIAL','stimulus','screen'],'trial',False)
    aoi_col=aoi_col or guess_col(df,['AOI','aoi','aoi_name','area','region','interest_area'],'AOI',False)
    groups=as_list(group_cols) if group_cols is not None else [c for c in [participant_col,trial_col,aoi_col] if c is not None]
    require_cols(df,groups,"grouping columns")
    dur=pd.to_numeric(df[duration_col],errors='coerce').to_numpy(float)
    if duration_unit=='milliseconds' or (duration_unit=='auto' and np.nanmedian(np.abs(dur))>10): dur=dur/1000
    work=df.copy(); work['_dur']=dur
    rows=[]
    iterator=work.groupby(groups,dropna=False,sort=False) if groups else [('all',work)]
    for key,b in iterator:
        d=b['_dur'].to_numpy(float); x=pd.to_numeric(b[x_col],errors='coerce').to_numpy(float) if x_col else np.full(len(b),np.nan); y=pd.to_numeric(b[y_col],errors='coerce').to_numpy(float) if y_col else np.full(len(b),np.nan)
        xd=np.nan if np.all(np.isnan(x)) else float(np.nanmax(x)-np.nanmin(x)); yd=np.nan if np.all(np.isnan(y)) else float(np.nanmax(y)-np.nanmin(y))
        row={"n_fixations":int(np.isfinite(d).sum()),"total_duration_s":float(np.nansum(d)),"mean_duration_s":float(np.nanmean(d)),"median_duration_s":float(np.nanmedian(d)),"sd_duration_s":r_sd(d),"min_duration_s":float(np.nanmin(d)),"max_duration_s":float(np.nanmax(d)),"x_dispersion":xd,"y_dispersion":yd,"spatial_dispersion":xd+yd if np.isfinite(xd) and np.isfinite(yd) else np.nan,"bbox_area":xd*yd if np.isfinite(xd) and np.isfinite(yd) else np.nan}
        if groups:
            key=key if isinstance(key,tuple) else (key,); row={**dict(zip(groups,key,strict=True)),**row}
        else: row={'group':'all',**row}
        rows.append(row)
    out=pd.DataFrame(rows); out.attrs.update(duration_col=duration_col,x_col=x_col,y_col=y_col); return out


def filter_gazepoint_gaze(data,x_col=None,y_col=None,time_col=None,group_cols=None,screen_bounds=(0,1,0,1),max_velocity=np.inf,drop_invalid=False,suffix='_filtered'):
    df=ensure_df(data).copy()
    if len(screen_bounds)!=4 or not np.all(np.isfinite(screen_bounds)): raise ValueError("`screen_bounds` must be c(x_min, x_max, y_min, y_max).")
    x_col=x_col or guess_col(df,['BPOGX','FPOGX','GPOGX','LPOGX','RPOGX','x','gaze_x','X'],'gaze x',True); y_col=y_col or guess_col(df,['BPOGY','FPOGY','GPOGY','LPOGY','RPOGY','y','gaze_y','Y'],'gaze y',True)
    require_cols(df,[x_col,y_col],"gaze columns"); tc=_time_col(df,time_col,False)
    x=pd.to_numeric(df[x_col],errors='coerce').to_numpy(float); y=pd.to_numeric(df[y_col],errors='coerce').to_numpy(float); raw=pd.to_numeric(df[tc],errors='coerce').to_numpy(float) if tc else np.arange(1,len(df)+1,dtype=float); sec=time_seconds(raw)
    xmin,xmax,ymin,ymax=screen_bounds; inb=np.isfinite(x)&np.isfinite(y)&(x>=xmin)&(x<=xmax)&(y>=ymin)&(y<=ymax); vel=np.full(len(df),np.nan); vok=np.ones(len(df),bool)
    for _,idx in group_indices(df,group_cols):
        if len(idx)>1:
            dt=np.diff(sec[idx]); v=np.sqrt(np.diff(x[idx])**2+np.diff(y[idx])**2)/dt; v[~np.isfinite(v)]=np.nan; vel[idx[1:]]=v
            if np.isfinite(max_velocity): vok[idx[1:]]=np.isnan(v)|(v<=max_velocity)
    valid=inb&vok; reason=np.full(len(df),'valid',object); reason[~inb]='outside_screen'; reason[~vok]='high_velocity'; reason[(~inb)&(~vok)]='outside_screen;high_velocity'
    df['gaze_in_bounds']=inb; df['gaze_velocity']=vel; df['gaze_velocity_ok']=vok; df['gaze_valid']=valid; df['gaze_filter_reason']=reason; df[x_col+suffix]=x; df[y_col+suffix]=y; df.loc[~valid,[x_col+suffix,y_col+suffix]]=np.nan
    df.attrs.update(x_col=x_col,y_col=y_col,time_col=tc,screen_bounds=tuple(screen_bounds),max_velocity=max_velocity)
    return df.loc[valid].reset_index(drop=True) if drop_invalid else df
