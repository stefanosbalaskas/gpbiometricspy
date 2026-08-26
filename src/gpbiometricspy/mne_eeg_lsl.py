from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata as metadata
from pathlib import Path
import platform
import re
import sys

import numpy as np
import pandas as pd


def _time_unit(values, unit='auto', name=''):
    a=pd.to_numeric(pd.Series(values),errors='coerce').to_numpy(float)
    if unit=='samples': return a, 'samples'
    if unit=='milliseconds' or (unit=='auto' and re.search(r'ms|MSTIMER',str(name),re.I)): return a/1000.0,'milliseconds'
    if unit in {'seconds','auto'}: return a,'seconds'
    raise ValueError('Invalid time unit.')


def _event_id(labels,event_id=None):
    labs=list(dict.fromkeys(map(str,labels)))
    if event_id is None:return {lab:i+1 for i,lab in enumerate(labs)}
    if isinstance(event_id,dict): out={str(k):int(v) for k,v in event_id.items()}
    elif isinstance(event_id,pd.Series):out={str(k):int(v) for k,v in event_id.to_dict().items()}
    elif isinstance(event_id,pd.DataFrame) and {'event_label','event_code'}<=set(event_id):out=dict(zip(event_id.event_label.astype(str),event_id.event_code.astype(int)))
    else: raise TypeError('`event_id` must be a named mapping or event table.')
    missing=[x for x in labs if x not in out]
    if missing:raise ValueError('Missing event codes for: '+', '.join(missing))
    return out


def prepare_gazepoint_mne_events(events,event_time_col=None,event_label_col=None,event_code_col=None,marker_cols=None,participant_col=None,trial_col=None,time_unit='auto',sampling_rate_hz=None,recording_start_s=0,first_samp=0,event_id=None,previous_value=0,marker_onset='change',duplicate='error',export_csv=None):
    if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0:raise ValueError('`sampling_rate_hz` must be positive.')
    if marker_onset not in {'change','nonzero'} or duplicate not in {'error','allow'}:raise ValueError('Invalid option.')
    if isinstance(events,(list,tuple,np.ndarray,pd.Series)) and not isinstance(events,pd.DataFrame):
        src=pd.DataFrame({'source_row':np.arange(1,len(events)+1),'source_time':np.asarray(events,float),'event_label':'event'}); resolved='numeric_vector'
    elif isinstance(events,pd.DataFrame):
        if events.empty:raise ValueError('`events` must contain at least one row.')
        if marker_cols is not None:
            mc=[marker_cols] if isinstance(marker_cols,str) else list(marker_cols); tc=event_time_col or next((c for c in ['event_time_s','event_time','time_s','time_ms','time','timestamp','MSTIMER','CNT'] if c in events),None)
            if tc is None:raise ValueError('Could not identify event time column.')
            rows=[]
            for col in mc:
                if col not in events:raise ValueError(f'Marker column not found: {col}')
                text=events[col].astype(object).where(events[col].notna(),'').astype(str).str.strip(); active=~text.str.lower().isin(['','0','false','off','none','na','nan'])
                if marker_onset=='change': onset=active & (~active.shift(fill_value=False) | text.ne(text.shift()))
                else:onset=active
                for idx in np.flatnonzero(onset.to_numpy()):
                    val=text.iloc[idx]; label=col if val.lower() in {'1','true','on'} else f'{col}/{val}'; row={'source_row':idx+1,'source_time':events.iloc[idx][tc],'event_label':label}
                    if participant_col and participant_col in events:row['participant']=events.iloc[idx][participant_col]
                    if trial_col and trial_col in events:row['trial']=events.iloc[idx][trial_col]
                    rows.append(row)
            if not rows:raise ValueError('No active marker events were found.')
            src=pd.DataFrame(rows);resolved=tc
        else:
            tc=event_time_col or next((c for c in ['event_time_s','event_time','time_s','time_ms','time','timestamp','MSTIMER','CNT'] if c in events),None)
            if tc is None:raise ValueError('Could not identify event time column.')
            lc=event_label_col or next((c for c in ['event_label','event','label','condition','Event'] if c in events),None)
            labels=events[lc].astype(str) if lc else pd.Series(['event']*len(events))
            src=pd.DataFrame({'source_row':np.arange(1,len(events)+1),'source_time':events[tc],'event_label':labels})
            if event_code_col and event_code_col in events:src['event_code']=pd.to_numeric(events[event_code_col],errors='coerce')
            resolved=tc
    else:raise TypeError('`events` must be a numeric vector or data frame.')
    ts,unit=_time_unit(src.source_time,time_unit,resolved)
    if unit=='samples':samples=np.rint(ts).astype(int)+int(first_samp); time_s=ts/float(sampling_rate_hz)
    else: time_s=ts; samples=np.rint((time_s-float(recording_start_s))*float(sampling_rate_hz)).astype(int)+int(first_samp)
    if 'event_code' in src and src.event_code.notna().all(): codes=src.event_code.astype(int).to_numpy(); ids={lab:int(code) for lab,code in zip(src.event_label,codes)}
    else: ids=_event_id(src.event_label,event_id);codes=np.array([ids[str(l)] for l in src.event_label],int)
    if duplicate=='error' and pd.Series(samples).duplicated().any():raise ValueError('Repeated event sample numbers were found.')
    mat=np.c_[samples,np.full(len(samples),int(previous_value)),codes].astype(int); table=src.copy();table['event_time_s']=time_s;table['mne_sample']=samples;table['event_code']=codes
    exported=False
    if export_csv is not None:
        q=Path(export_csv);q.parent.mkdir(parents=True,exist_ok=True);np.savetxt(q,mat,fmt='%d');exported=True
    return {'events':mat,'table':table,'event_id':ids,'audit':{'n_events':len(mat),'duplicate_samples':int(pd.Series(samples).duplicated().sum()),'exported':exported},'settings':{'sampling_rate_hz':float(sampling_rate_hz),'recording_start_s':recording_start_s,'first_samp':int(first_samp),'time_unit':unit},'class':'gazepoint_mne_events'}


def _ch_type(name):
    n=name.lower()
    if 'ttl' in n or 'marker' in n or 'trigger' in n:return 'stim'
    if 'pupil' in n:return 'pupil'
    if 'gaze' in n or n in {'x','y'}:return 'eyegaze'
    if 'gsr' in n or 'eda' in n:return 'gsr'
    if 'eeg' in n:return 'eeg'
    if 'ecg' in n:return 'ecg'
    return 'misc'


def prepare_gazepoint_mne_input(data,channel_cols=None,channel_names=None,channel_types=None,time_col=None,time_unit='auto',sampling_rate_hz=None,first_samp=0,scale_factors=None,missing='error',irregular='error',sampling_tolerance=.05):
    if not isinstance(data,pd.DataFrame) or data.empty:raise TypeError('`data` must be a non-empty data frame.')
    if missing not in {'error','allow'} or irregular not in {'error','allow'}:raise ValueError('Invalid option.')
    tc=time_col or next((c for c in ['time_s','time_ms','Time','TIME','timestamp','MSTIMER'] if c in data),None)
    if tc is None:
        if sampling_rate_hz is None:raise ValueError('Could not identify time column or sampling rate.')
        tt=np.arange(len(data))/sampling_rate_hz;unit='seconds'
    else:tt,unit=_time_unit(data[tc],time_unit,tc)
    if len(tt)>1:
        dt=np.diff(tt); finite=dt[np.isfinite(dt)&(dt>0)]
        if sampling_rate_hz is None:sampling_rate_hz=1/np.median(finite) if len(finite) else np.nan
        expected=1/float(sampling_rate_hz); rel=np.abs(dt-expected)/expected; irr=np.isfinite(rel)&(rel>sampling_tolerance); irregular_count=int(irr.sum())
        if irregular_count and irregular=='error':raise ValueError('Irregular sampling intervals were found.')
    else:irregular_count=0
    if sampling_rate_hz is None or not np.isfinite(sampling_rate_hz) or sampling_rate_hz<=0:raise ValueError('Could not infer a valid sampling rate.')
    if channel_cols is None:
        channel_cols=[c for c in data.columns if c!=tc and pd.api.types.is_numeric_dtype(data[c])]
    channel_cols=[channel_cols] if isinstance(channel_cols,str) else list(channel_cols)
    if not channel_cols:raise ValueError('No channel columns found.')
    for c in channel_cols:
        if c not in data:raise ValueError(f'Channel not found: {c}')
    names=channel_cols if channel_names is None else ([channel_names] if isinstance(channel_names,str) else list(channel_names));types=[_ch_type(c) for c in channel_cols] if channel_types is None else ([channel_types] if isinstance(channel_types,str) else list(channel_types))
    if len(names)!=len(channel_cols) or len(types)!=len(channel_cols):raise ValueError('Channel metadata lengths must match.')
    scales=np.ones(len(channel_cols)) if scale_factors is None else np.broadcast_to(np.asarray(scale_factors,float), (len(channel_cols),)).copy()
    mat=np.vstack([pd.to_numeric(data[c],errors='coerce').to_numpy(float)*sc for c,sc in zip(channel_cols,scales)])
    if not np.isfinite(mat).all() and missing=='error':raise ValueError('Non-finite channel values were found.')
    info=pd.DataFrame({'source_col':channel_cols,'channel_name':names,'channel_type':types,'scale_factor':scales})
    return {'data':mat,'channel_info':info,'info_spec':{'ch_names':names,'ch_types':types,'sfreq':float(sampling_rate_hz)},'sampling':{'sampling_rate_hz':float(sampling_rate_hz),'irregular_interval_count':irregular_count,'time_unit':unit},'first_samp':int(first_samp),'time_s':tt,'class':'gazepoint_mne_input'}


def _infer_time(df,preferred,candidates,unit='auto',fs=None):
    col=preferred or next((c for c in candidates if c in df),None)
    if col is None:raise ValueError('Could not identify time column.')
    a=pd.to_numeric(df[col],errors='coerce').to_numpy(float)
    if unit=='samples':
        if fs is None or fs<=0:raise ValueError('Sampling rate is required for sample time.')
        return a/fs,col
    return _time_unit(a,unit,col)[0],col


def align_gazepoint_to_eeg(gazepoint,gazepoint_events,eeg_events,gazepoint_time_col=None,gazepoint_event_time_col=None,eeg_event_time_col=None,eeg_event_sample_col=None,gazepoint_event_id_col=None,eeg_event_id_col=None,gazepoint_time_unit='auto',eeg_time_unit='auto',eeg_sampling_rate_hz=None,method='offset',match_by='auto',robust=True,maximum_residual_s=None,residual_action='error',output_col='time_eeg_s'):
    if method not in {'offset','linear'} or match_by not in {'auto','id','row'} or residual_action not in {'error','allow'}:raise ValueError('Invalid option.')
    if not all(isinstance(x,pd.DataFrame) for x in [gazepoint,gazepoint_events,eeg_events]):raise TypeError('Inputs must be data frames.')
    gt,gcol=_infer_time(gazepoint,gazepoint_time_col,['time_s','time_ms','time','MSTIMER'],gazepoint_time_unit)
    gpe,_=_infer_time(gazepoint_events,gazepoint_event_time_col,['event_time_s','time_s','time_ms','time','MSTIMER'],gazepoint_time_unit)
    if eeg_event_sample_col is not None:
        if eeg_sampling_rate_hz is None or eeg_sampling_rate_hz<=0:raise ValueError('`eeg_sampling_rate_hz` is required with sample events.')
        ee=pd.to_numeric(eeg_events[eeg_event_sample_col],errors='coerce').to_numpy(float)/eeg_sampling_rate_hz
    else:ee,_=_infer_time(eeg_events,eeg_event_time_col,['event_time_s','time_s','time_ms','time'],eeg_time_unit,eeg_sampling_rate_hz)
    gid=gazepoint_event_id_col or next((c for c in ['event_id','id','label'] if c in gazepoint_events),None);eid=eeg_event_id_col or next((c for c in ['event_id','id','label'] if c in eeg_events),None)
    use_id=(match_by=='id') or (match_by=='auto' and gid and eid)
    if use_id:
        left=pd.DataFrame({'id':gazepoint_events[gid].astype(str),'gp':gpe});right=pd.DataFrame({'id':eeg_events[eid].astype(str),'eeg':ee});pairs=left.merge(right,on='id');x=pairs.gp.to_numpy(float);y=pairs.eeg.to_numpy(float)
    else:
        n=min(len(gpe),len(ee));x=gpe[:n];y=ee[:n]
    ok=np.isfinite(x)&np.isfinite(y);x=x[ok];y=y[ok]
    if len(x)<1:raise ValueError('No matched finite events.')
    if method=='offset': slope=1.0;intercept=float(np.median(y-x) if robust else np.mean(y-x))
    else:
        if len(x)<2:raise ValueError('At least two events are required for linear alignment.')
        slope,intercept=np.polyfit(x,y,1);slope=float(slope);intercept=float(intercept)
    residual=y-(intercept+slope*x);maxres=float(np.max(np.abs(residual))) if len(residual) else np.nan
    if maximum_residual_s is not None and maxres>maximum_residual_s and residual_action=='error':raise ValueError('Alignment residual exceeds maximum_residual_s.')
    out=gazepoint.copy();out[output_col]=intercept+slope*gt
    if eeg_event_sample_col is not None:out[f'{output_col}_sample']=np.rint(out[output_col]*eeg_sampling_rate_hz).astype(int)
    return {'data':out,'pairs':pd.DataFrame({'gazepoint_time_s':x,'eeg_time_s':y,'residual_s':residual}),'mapping':{'intercept_s':intercept,'slope':slope},'audit':{'n_matched_events':len(x),'maximum_abs_residual_s':maxres,'drift_ppm':(slope-1)*1e6},'settings':{'method':method,'match_by':'id' if use_id else 'row'},'class':'gazepoint_eeg_alignment'}


class EyeMethodsText(str):
    pass


def create_gazepoint_eye_methods_text(sampling_rate_hz,device_model='Gazepoint GP3',calibration_points=9,binocular=True,software='Gazepoint Analysis',screen_resolution=None,viewing_distance_cm=None,coordinate_space=None,preprocessing=None,fixation_detection=None,aoi_definition=None,synchronization=None,exclusions=None,tense='past',include_package_version=True):
    verb='will be recorded' if tense=='future' else 'were recorded'; parts=[f'Eye-tracking data {verb} at {sampling_rate_hz:g} Hz using a {device_model} with a {int(calibration_points)}-point calibration']
    parts[0]+= ' in binocular mode' if binocular else ' in monocular mode';parts[0]+=f' using {software}.'
    if screen_resolution is not None:parts.append(f"The display resolution was {int(screen_resolution[0])} x {int(screen_resolution[1])} pixels.")
    if viewing_distance_cm is not None:parts.append(f'Viewing distance was approximately {viewing_distance_cm:g} cm.')
    if coordinate_space:parts.append(f'Coordinates were represented in {coordinate_space}.')
    if preprocessing:parts.append('Preprocessing included '+', '.join(preprocessing if isinstance(preprocessing,(list,tuple)) else [str(preprocessing)])+'.')
    if fixation_detection:parts.append('Fixation detection: '+str(fixation_detection)+'.')
    if aoi_definition:parts.append('AOI definition: '+str(aoi_definition)+'.')
    if synchronization:parts.append('Synchronization used '+str(synchronization)+'.')
    if exclusions:parts.append('Exclusions: '+str(exclusions)+'.')
    if include_package_version:parts.append('Processing used gpbiometrics/gpbiometricspy workflow utilities.')
    return EyeMethodsText(' '.join(parts))


def session_info_gazepoint(packages=None,include_loaded=True,timestamp=None):
    names=[] if packages is None else ([packages] if isinstance(packages,str) else list(packages));names=['gpbiometrics','gpbiometricspy']+names
    rows=[]
    for n in dict.fromkeys(names):
        try:v=metadata.version('gpbiometricspy' if n=='gpbiometrics' else n)
        except metadata.PackageNotFoundError:v='not_installed' if n!='gpbiometrics' else '2.0.0-reference'
        rows.append({'package':n,'version':v})
    system=pd.DataFrame({'field':['python_version','platform','r_version','timestamp'],'value':[sys.version.split()[0],platform.platform(),'not_applicable_python_port',str(timestamp or datetime.now(timezone.utc).isoformat())]})
    return {'packages':pd.DataFrame(rows),'system':system,'include_loaded':include_loaded,'class':'gazepoint_session_info'}


def _stream_df(x,name,time_col=None):
    if isinstance(x,pd.DataFrame):
        d=x.copy();tc=time_col or next((c for c in ['time_s','timestamp','time','time_stamps'] if c in d),None)
        if tc is None:raise ValueError(f'Could not identify time column for stream `{name}`.')
        d['.lsl_time_raw_s']=pd.to_numeric(d[tc],errors='coerce');return d
    if isinstance(x,dict) and 'time_stamps' in x and 'time_series' in x:
        ts=np.asarray(x['time_stamps'],float);arr=np.asarray(x['time_series'])
        if arr.ndim==1:arr=arr[:,None]
        cols=list(getattr(x['time_series'],'columns',[]))
        if not cols:
            # numpy dimnames are not preserved; common x/y fallback for two-column gaze streams.
            cols=['x','y'] if arr.shape[1]==2 else [f'value_{i+1}' for i in range(arr.shape[1])]
        d=pd.DataFrame(arr,columns=cols);d['.lsl_time_raw_s']=ts;return d
    raise TypeError(f'Unsupported stream format for `{name}`.')


def sync_gazepoint_signals_via_lsl(streams,reference=None,time_cols=None,clock_offsets_s=None,known_lags_s=None,relative_zero='reference',dejitter='none',nominal_rates_hz=None,merge='none',tolerance_s=None):
    if not isinstance(streams,dict) or not streams:raise ValueError('`streams` must be a non-empty named mapping.')
    if relative_zero not in {'reference','global','none'} or dejitter not in {'none','linear'} or merge not in {'none','nearest'}:raise ValueError('Invalid option.')
    reference=reference or next(iter(streams)); tc={} if time_cols is None else time_cols; offsets={} if clock_offsets_s is None else dict(clock_offsets_s);lags={} if known_lags_s is None else dict(known_lags_s);rates={} if nominal_rates_hz is None else (dict(nominal_rates_hz) if isinstance(nominal_rates_hz,dict) else {n:nominal_rates_hz for n in streams});out={}
    for name,x in streams.items():
        d=_stream_df(x,name,tc.get(name) if isinstance(tc,dict) else None);raw=d['.lsl_time_raw_s'].to_numpy(float);corr=raw+float(offsets.get(name,0))-float(lags.get(name,0))
        if dejitter=='linear':
            rate=rates.get(name)
            if rate is None or rate<=0:raise ValueError(f'Nominal rate required for linear dejittering of `{name}`.')
            corr=corr[0]+np.arange(len(corr))/float(rate)
        d['.lsl_time_corrected_s']=corr;out[name]=d
    if relative_zero=='reference':zero=float(out[reference]['.lsl_time_corrected_s'].iloc[0])
    elif relative_zero=='global':zero=min(float(d['.lsl_time_corrected_s'].iloc[0]) for d in out.values())
    else:zero=0.0
    for d in out.values():d['.lsl_time_relative_s']=d['.lsl_time_corrected_s']-zero
    merged=None
    if merge=='nearest':
        base=out[reference].copy().reset_index(drop=True);merged=base.copy();rt=base['.lsl_time_relative_s'].to_numpy(float)
        for name,d in out.items():
            if name==reference:continue
            st=d['.lsl_time_relative_s'].to_numpy(float);idx=np.array([int(np.argmin(np.abs(st-v))) for v in rt]);diff=st[idx]-rt;valid=np.ones(len(idx),bool) if tolerance_s is None else np.abs(diff)<=tolerance_s
            for c in d.columns:
                if c.startswith('.lsl_'):continue
                vals=d.iloc[idx][c].to_numpy(object);vals[~valid]=np.nan;merged[f'{name}__{c}']=vals
            merged[f'{name}__time_difference_s']=np.where(valid,diff,np.nan)
    audit=pd.DataFrame([{'stream':n,'n_samples':len(d),'clock_offset_s':offsets.get(n,0),'known_lag_s':lags.get(n,0)} for n,d in out.items()])
    return {'streams':out,'reference':reference,'merged':merged,'audit':audit,'settings':{'relative_zero':relative_zero,'dejitter':dejitter,'merge':merge,'tolerance_s':tolerance_s},'class':'gazepoint_lsl_sync'}
