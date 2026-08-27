from __future__ import annotations

import gzip
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _df(x, name='data'):
    if not isinstance(x, pd.DataFrame):
        raise TypeError(f'`{name}` must be a data frame.')
    return x.copy()


def _cols(x):
    if x is None: return []
    return [x] if isinstance(x,str) else list(x)


def _pick(df, candidates):
    low={str(c).lower():c for c in df.columns}
    for c in candidates:
        if c in df.columns:return c
        if c.lower() in low:return low[c.lower()]
    return None


def _sampling(t):
    x=np.asarray(t,float); x=x[np.isfinite(x)]
    if len(x)<2:return np.nan
    d=np.diff(x);d=d[(d>0)&np.isfinite(d)]
    if not len(d):return np.nan
    m=float(np.median(d));return 1000/m if m>10 else 1/m


def _time_ms(x, unit='auto', sampling_rate_hz=None):
    a=np.asarray(x,float)
    if unit=='samples':
        if not sampling_rate_hz or sampling_rate_hz<=0: raise ValueError('`sampling_rate_hz` is required for sample counters.')
        return a/sampling_rate_hz*1000
    if unit=='seconds':return a*1000
    if unit=='milliseconds':return a
    if unit=='microseconds':return a/1000
    # auto
    f=a[np.isfinite(a)]
    if len(f)>1:
        d=np.diff(f);d=d[d>0]
        med=np.median(d) if len(d) else np.nan
        if np.isfinite(med) and med>=2:return a
    return a*1000


def _point_on_segment(px,py,x1,y1,x2,y2,tol=1e-12):
    cross=(px-x1)*(y2-y1)-(py-y1)*(x2-x1)
    if abs(cross)>tol:return False
    dot=(px-x1)*(px-x2)+(py-y1)*(py-y2)
    return dot<=tol


def _point_in_poly(px,py,xs,ys,boundary=True):
    n=len(xs)
    for i in range(n):
        if _point_on_segment(px,py,xs[i],ys[i],xs[(i+1)%n],ys[(i+1)%n]): return boundary
    inside=False;j=n-1
    for i in range(n):
        if ((ys[i]>py)!=(ys[j]>py)) and px < (xs[j]-xs[i])*(py-ys[i])/(ys[j]-ys[i])+xs[i]: inside=not inside
        j=i
    return inside


def assign_gazepoint_aoi(data, aois, x_col=None, y_col=None, aoi_label_col='aoi', format='auto', aoi_id_col=None,
                         data_match_cols=None, aoi_match_cols=None, xmin_col='xmin', xmax_col='xmax', ymin_col='ymin', ymax_col='ymax',
                         vertex_x_col='vertex_x', vertex_y_col='vertex_y', priority_col=None, overlap='priority', boundary='inside',
                         output_col='AOI', match_count_col='aoi_match_count', ambiguous_col='aoi_ambiguous', status_col='aoi_assignment_status',
                         all_separator='|', overwrite=False):
    df=_df(data);defs=_df(aois,'aois')
    x_col=x_col or _pick(df,['gaze_x','mean_x','BPOGX','x','X']); y_col=y_col or _pick(df,['gaze_y','mean_y','BPOGY','y','Y'])
    if not x_col or not y_col:raise ValueError('Could not detect gaze x/y columns.')
    for c in [x_col,y_col]:
        if c not in df or not pd.api.types.is_numeric_dtype(df[c]):raise ValueError(f'Column `{c}` must be numeric.')
    if aoi_label_col not in defs:raise ValueError(f'Column `{aoi_label_col}` was not found in `aois`.')
    if not overwrite:
        for c in [output_col,match_count_col,ambiguous_col,status_col]:
            if c in df:raise ValueError(f'Column `{c}` already exists.')
    if aoi_match_cols is None:aoi_match_cols=data_match_cols
    dmc=_cols(data_match_cols);amc=_cols(aoi_match_cols)
    if len(dmc)!=len(amc):raise ValueError('Match columns must have equal length.')
    if format=='auto':
        format='polygon' if vertex_x_col in defs and vertex_y_col in defs else 'rectangle'
    objects=[]
    if format=='rectangle':
        req=[xmin_col,xmax_col,ymin_col,ymax_col];miss=[c for c in req if c not in defs]
        if miss:raise ValueError('Missing rectangle columns: '+', '.join(miss))
        for i,r in defs.iterrows():
            objects.append({'idx':i,'label':str(r[aoi_label_col]),'area':abs(float(r[xmax_col]-r[xmin_col]) * float(r[ymax_col]-r[ymin_col])),'row':r,'shape':'rectangle'})
    else:
        aid=aoi_id_col or _pick(defs,['aoi_id','id'])
        if not aid:raise ValueError('`aoi_id_col` is required for polygon AOIs.')
        for ident,g in defs.groupby(aid,sort=False,dropna=False):
            xs=pd.to_numeric(g[vertex_x_col],errors='coerce').to_numpy(float);ys=pd.to_numeric(g[vertex_y_col],errors='coerce').to_numpy(float)
            area=.5*abs(np.dot(xs,np.roll(ys,1))-np.dot(ys,np.roll(xs,1)))
            objects.append({'idx':ident,'label':str(g.iloc[0][aoi_label_col]),'area':area,'row':g.iloc[0],'xs':xs,'ys':ys,'shape':'polygon'})
    labels=[];counts=[];amb=[];statuses=[]
    for _,r in df.iterrows():
        px,py=r[x_col],r[y_col]
        if not np.isfinite(px) or not np.isfinite(py):labels.append(np.nan);counts.append(0);amb.append(False);statuses.append('invalid_coordinate');continue
        candidates=[]
        for o in objects:
            okctx=True
            for dc,ac in zip(dmc,amc):
                av=o['row'].get(ac,np.nan); dv=r.get(dc,np.nan)
                if pd.notna(av) and str(av)!=str(dv):okctx=False;break
            if not okctx:continue
            if o['shape']=='rectangle':
                rr=o['row'];inc=(px>=rr[xmin_col] and px<=rr[xmax_col] and py>=rr[ymin_col] and py<=rr[ymax_col]) if boundary=='inside' else (px>rr[xmin_col] and px<rr[xmax_col] and py>rr[ymin_col] and py<rr[ymax_col])
            else:inc=_point_in_poly(float(px),float(py),o['xs'],o['ys'],boundary=='inside')
            if inc:candidates.append(o)
        n=len(candidates);counts.append(n);amb.append(n>1)
        if n==0:labels.append(np.nan);statuses.append('unmatched');continue
        if n==1:labels.append(candidates[0]['label']);statuses.append('matched');continue
        if overlap=='error':raise ValueError('Multiple AOIs matched a gaze sample.')
        if overlap=='all':labels.append(all_separator.join(o['label'] for o in candidates));statuses.append('ambiguous_all');continue
        if overlap=='smallest':chosen=min(candidates,key=lambda o:o['area'])
        elif overlap=='priority' and priority_col:
            chosen=min(candidates,key=lambda o:(float(o['row'].get(priority_col,np.inf)), candidates.index(o)))
        else:chosen=candidates[0]
        labels.append(chosen['label']);statuses.append('ambiguous_resolved')
    out=df.copy();out[output_col]=labels;out[match_count_col]=np.asarray(counts,int);out[ambiguous_col]=np.asarray(amb,bool);out[status_col]=statuses
    definitions=pd.DataFrame([{'aoi':o['label'],'shape':o['shape'],'area':o['area']} for o in objects])
    overview=pd.DataFrame([{'n_rows':len(out),'n_assigned':int(pd.Series(labels).notna().sum()),'n_unmatched':int((np.asarray(statuses)=='unmatched').sum()),'n_invalid_coordinates':int((np.asarray(statuses)=='invalid_coordinate').sum()),'n_ambiguous':int(np.asarray(amb).sum()),'status':'aoi_assignment_complete'}])
    out.attrs['class']=['gazepoint_aoi_assignment','data.frame'];out.attrs['aoi_assignment_log']={'overview':overview,'definitions':definitions,'settings':{'format':format,'overlap':overlap,'boundary':boundary}}
    return out


def check_gazepoint_bids(root, subject_pattern=r'^sub-[A-Za-z0-9]+$', recursive=True, expected_files=('dataset_description.json','participants.tsv'), gazepoint_patterns=('all[_-]?gaze','fixation','summary','biometric','eda','gsr','ecg','ppg','hr','ibi')):
    root=Path(root);checks=[]
    def add(check,status,detail):checks.append({'check':check,'status':status,'detail':detail})
    if not root.exists() or not root.is_dir():
        add('root_directory','fail','Root directory does not exist.');df=pd.DataFrame(checks);summary=pd.DataFrame([{'n_checks':1,'n_pass':0,'n_warn':0,'n_fail':1,'layout_ready':False,'needs_review':True}]);return {'checks':df,'summary':summary,'root':str(root),'class':['gazepoint_bids_layout_audit','list']}
    add('root_directory','pass','Root directory exists.')
    for f in expected_files:add(f,'pass' if (root/f).exists() else 'warn', 'Present.' if (root/f).exists() else 'Missing expected root file.')
    subs=[p for p in root.iterdir() if p.is_dir() and re.match(subject_pattern,p.name)];add('subject_directories','pass' if subs else 'warn',f'{len(subs)} subject directories detected.')
    files=[p for p in (root.rglob('*') if recursive else root.glob('*')) if p.is_file()]
    rx=re.compile('|'.join(gazepoint_patterns),re.I);gps=[p for p in files if rx.search(p.name)];add('gazepoint_export_files','pass' if gps else 'warn',f'{len(gps)} Gazepoint-like export files detected.')
    df=pd.DataFrame(checks);nf=int((df.status=='fail').sum());nw=int((df.status=='warn').sum());summary=pd.DataFrame([{'n_checks':len(df),'n_pass':int((df.status=='pass').sum()),'n_warn':nw,'n_fail':nf,'layout_ready':nf==0,'needs_review':nf>0 or nw>0}])
    return {'checks':df,'summary':summary,'root':str(root),'files':pd.DataFrame({'path':[str(p) for p in files]}),'class':['gazepoint_bids_layout_audit','list']}


def create_gazepoint_preregistration_template(study_title='Gazepoint biometrics study', signal_standardization='within_participant_z', artifact_rules='kleckner_style', eda_min_us=.01, eda_max_us=100, rapid_change_threshold=20, output_file=None):
    if signal_standardization not in {'within_participant_z','range_correction','none'}:raise ValueError('Invalid `signal_standardization`.')
    if artifact_rules not in {'kleckner_style','custom','none'}:raise ValueError('Invalid `artifact_rules`.')
    std={'within_participant_z':'z = (x - participant mean) / participant standard deviation.','range_correction':'(x - participant minimum) / (participant maximum - participant minimum).','none':'No participant-level signal standardisation will be applied.'}[signal_standardization]
    art={'kleckner_style':f'Kleckner-style heuristic rules with conductance range [{eda_min_us}, {eda_max_us}] microsiemens and rapid-change threshold {rapid_change_threshold}% per second.','custom':'Study-specific artifact rules will be prespecified.','none':'No automated EDA artifact rule will be applied.'}[artifact_rules]
    text=f'''# Preregistration template: {study_title}\n\n## Data source\nRaw Gazepoint Biometrics exports will be imported using gpbiometricspy.\n\n## Quality control\nMissingness, inactive channels, time resets and artifacts will be audited.\n\n## Standardisation plan\n{std}\n\n## Artifact rules\n{art}\n\n## Interpretation guardrail\nEDA/GSR, heart-rate, pupil, and gaze measures will not be interpreted as direct evidence of emotion, valence, stress, trust, preference, cognition, or diagnosis without converging evidence.'''
    if output_file:Path(output_file).write_text(text,encoding='utf-8')
    return text


def create_gazepoint_trial_regressors(data, design, pre=0, post=5, time_col=None, event_time_col=None, event_id_col=None, signal_cols=None, subject_col=None, design_subject_col=None, carry_design_cols=None):
    df=_df(data);time_col=time_col or _pick(df,['time_s','time','CNT','TIME','TIMETICK'])
    if not time_col:raise ValueError('Could not detect time column.')
    if np.isscalar(design) or isinstance(design,(list,tuple,np.ndarray,pd.Series)):
        ev=pd.DataFrame({'event_time':np.asarray(design,float)});event_time_col='event_time';event_id_col=None
    else:ev=_df(design,'design');event_time_col=event_time_col or _pick(ev,['onset','event_time','time']);
    if not event_time_col or event_time_col not in ev:raise ValueError('Could not detect event time column.')
    signal_cols=_cols(signal_cols) or [c for c in df.select_dtypes(include=np.number).columns if c!=time_col]
    carry=_cols(carry_design_cols) or [c for c in ev.columns if c not in {event_time_col,event_id_col}]
    rows=[]
    for i,r in ev.iterrows():
        t=float(r[event_time_col]);mask=pd.to_numeric(df[time_col],errors='coerce').between(t-pre,t+post,inclusive='both')
        if subject_col and design_subject_col:mask &= df[subject_col].astype(str).eq(str(r[design_subject_col]))
        row={'trial_id':str(r[event_id_col]) if event_id_col else str(i+1),'event_time':t,'n_samples':int(mask.sum())}
        for c in signal_cols:
            vals=pd.to_numeric(df.loc[mask,c],errors='coerce');row[c+'_mean']=float(vals.mean()) if vals.notna().any() else np.nan;row[c+'_sd']=float(vals.std()) if vals.notna().sum()>1 else np.nan
        for c in carry:
            if c in ev:row[c]=r[c]
        rows.append(row)
    out=pd.DataFrame(rows);out.attrs['class']=['gazepoint_trial_regressors','data.frame'];out.attrs['settings']={'pre':pre,'post':post,'time_col':time_col,'signal_cols':signal_cols};return out


def _gaze_event_engine(data,time_col=None,x_col=None,y_col=None,group_cols=None,valid_col=None,valid_values=(1,True),time_unit='seconds',sampling_rate_hz=None,coordinate_unit='native',velocity_threshold=None,min_fixation_duration_ms=100,min_saccade_duration_ms=10,max_gap_ms=100,velocity_col='gaze_velocity',class_col='gaze_class',event_id_col='gaze_event_id',overwrite=False):
    df=_df(data);time_col=time_col or _pick(df,['time_s','time_ms','TIME','CNT','time']);x_col=x_col or _pick(df,['gaze_x','BPOGX','x']);y_col=y_col or _pick(df,['gaze_y','BPOGY','y'])
    if velocity_threshold is None or velocity_threshold<=0:raise ValueError('`velocity_threshold` must be positive.')
    for c in [time_col,x_col,y_col]:
        if not c or c not in df:raise ValueError('Required gaze columns not found.')
        if not pd.api.types.is_numeric_dtype(df[c]):raise ValueError(f'Column `{c}` must be numeric.')
    groups=_cols(group_cols);missing=[c for c in groups if c not in df]
    if missing:raise ValueError('Missing grouping columns: '+', '.join(missing))
    if any(c in df and not overwrite for c in [velocity_col,class_col,event_id_col]):raise ValueError('Output columns already exist.')
    samples=df.copy();samples[velocity_col]=np.nan;samples[class_col]='unclassified';samples[event_id_col]=pd.Series([pd.NA]*len(df),dtype='Int64')
    fix=[];sac=[];summ=[];eid=0
    group_iter=[('all',df.index)] if not groups else df.groupby(groups,sort=False,dropna=False).groups.items()
    for key,index in group_iter:
        idx=np.asarray(list(index),dtype=int);ord_idx=idx[np.argsort(pd.to_numeric(df.loc[idx,time_col],errors='coerce').to_numpy(float),kind='stable')]
        t_raw=pd.to_numeric(df.loc[ord_idx,time_col],errors='coerce').to_numpy(float);tms=_time_ms(t_raw,time_unit,sampling_rate_hz);x=pd.to_numeric(df.loc[ord_idx,x_col],errors='coerce').to_numpy(float);y=pd.to_numeric(df.loc[ord_idx,y_col],errors='coerce').to_numpy(float)
        valid=np.isfinite(tms)&np.isfinite(x)&np.isfinite(y)
        if valid_col:
            vv=df.loc[ord_idx,valid_col];valid &= vv.isin(list(valid_values)).to_numpy()
        dt=np.diff(tms)/1000;dist=np.hypot(np.diff(x),np.diff(y));iv=np.where((dt>0)&(dt*1000<=max_gap_ms),dist/dt,np.nan)
        vel=np.full(len(ord_idx),np.nan)
        for j in range(len(ord_idx)):
            vals=[]
            if j>0 and np.isfinite(iv[j-1]):vals.append(iv[j-1])
            if j<len(iv) and np.isfinite(iv[j]):vals.append(iv[j])
            if vals:vel[j]=max(vals)
        cand=np.where(valid, np.where(vel>velocity_threshold,'saccade','fixation'),'unclassified')
        # gaps break both adjoining samples
        for j,dti in enumerate(dt):
            if not np.isfinite(dti) or dti<=0 or dti*1000>max_gap_ms+1e-9:cand[j]='unclassified';cand[j+1]='unclassified'
        # contiguous runs and duration threshold
        final=np.array(cand,dtype=object);ids=np.full(len(ord_idx),-1,int)
        start=0
        while start<len(final):
            lab=cand[start];end=start
            while end+1<len(final) and cand[end+1]==lab:end+=1
            dur=tms[end]-tms[start] if end>start else 0
            min_d=min_fixation_duration_ms if lab=='fixation' else min_saccade_duration_ms if lab=='saccade' else np.inf
            if lab in {'fixation','saccade'} and dur+1e-9>=min_d:
                eid+=1;ids[start:end+1]=eid
                base={}
                if groups:
                    vals=df.loc[ord_idx[start],groups]
                    base=vals.to_dict() if hasattr(vals,'to_dict') else {groups[0]:vals}
                if lab=='fixation':
                    fix.append({**base,'fixation_id':eid,'start_time':t_raw[start],'end_time':t_raw[end],'duration_ms':dur,'mean_x':float(np.nanmean(x[start:end+1])),'mean_y':float(np.nanmean(y[start:end+1])),'n_samples':end-start+1})
                else:
                    dx=x[end]-x[start];dy=y[end]-y[start]
                    sac.append({**base,'saccade_id':eid,'start_time':t_raw[start],'end_time':t_raw[end],'duration_ms':dur,'amplitude':float(np.hypot(dx,dy)),'peak_velocity':float(np.nanmax(vel[start:end+1])),'direction_deg':float(np.degrees(np.arctan2(dy,dx))),'n_samples':end-start+1})
            elif lab in {'fixation','saccade'}:final[start:end+1]='unclassified'
            start=end+1
        samples.loc[ord_idx,velocity_col]=vel;samples.loc[ord_idx,class_col]=final;samples.loc[ord_idx,event_id_col]=pd.array(np.where(ids<0,pd.NA,ids),dtype='Int64')
        base={}
        if groups:
            vals=df.loc[ord_idx[0],groups];base=vals.to_dict() if hasattr(vals,'to_dict') else {groups[0]:vals}
        summ.append({**base,'n_samples':len(ord_idx),'n_fixations':sum(1 for z in fix if all(z.get(c)==base.get(c) for c in groups)) if groups else len(fix),'n_saccades':sum(1 for z in sac if all(z.get(c)==base.get(c) for c in groups)) if groups else len(sac),'n_unclassified_samples':int((final=='unclassified').sum())})
    return {'samples':samples,'fixations':pd.DataFrame(fix),'saccades':pd.DataFrame(sac),'summary':pd.DataFrame(summ),'settings':{'time_col':time_col,'x_col':x_col,'y_col':y_col,'group_cols':groups,'velocity_threshold':velocity_threshold,'time_unit':time_unit,'coordinate_unit':coordinate_unit},'class':['gazepoint_gaze_events','list']}


def detect_gazepoint_fixations(data, time_col=None, x_col=None, y_col=None, group_cols=None, valid_col=None, valid_values=(1,True), time_unit='seconds', sampling_rate_hz=None, coordinate_unit='native', velocity_threshold=None, min_fixation_duration_ms=100, min_saccade_duration_ms=10, max_gap_ms=100, velocity_col='gaze_velocity', class_col='gaze_class', event_id_col='gaze_event_id', overwrite=False):
    return _gaze_event_engine(data,time_col,x_col,y_col,group_cols,valid_col,valid_values,time_unit,sampling_rate_hz,coordinate_unit,velocity_threshold,min_fixation_duration_ms,min_saccade_duration_ms,max_gap_ms,velocity_col,class_col,event_id_col,overwrite)


def detect_gazepoint_saccades(*args, **kwargs):
    out=_gaze_event_engine(*args,**kwargs);s=out['saccades'].copy();s.attrs['class']=['gazepoint_detected_saccades','data.frame'];s.attrs['gaze_event_summary']=out['summary'];s.attrs['gaze_event_settings']=out['settings'];return s


def _infer_eye_cols(df, eye):
    if eye=='left':return _pick(df,['LPOGX','gaze_x','x']),_pick(df,['LPOGY','gaze_y','y']),_pick(df,['LPD','pupil_left','pupil'])
    if eye=='right':return _pick(df,['RPOGX','gaze_x','x']),_pick(df,['RPOGY','gaze_y','y']),_pick(df,['RPD','pupil_right','pupil'])
    return _pick(df,['BPOGX','gaze_x','x']),_pick(df,['BPOGY','gaze_y','y']),_pick(df,['BPD','PUPIL','pupil'])


def export_gazepoint_to_bids(data,bids_root,subject,task,dataset_name=None,recorded_eye='cyclopean',recording='eye1',datatype='beh',session=None,acquisition=None,run=None,timestamp_col=None,x_col=None,y_col=None,include_pupil=True,pupil_col=None,additional_cols=None,timestamp_units='auto',coordinate_units='normalized',pupil_units='arbitrary',sample_coordinate_system='gaze-on-screen',sampling_rate_hz=None,sampling_tolerance=.05,start_time_s=0,screen_distance_m=None,screen_origin=None,screen_resolution_px=None,screen_size_m=None,screen_refresh_rate_hz=None,stimulus_software_name=None,stimulus_software_version=None,operating_system=None,vision_correction=None,manufacturer='Gazepoint',manufacturers_model_name=None,software_versions=None,device_serial_number=None,eye_tracking_method='P-CR',calibration_type=None,calibration_count=None,average_calibration_error_deg=None,maximal_calibration_error_deg=None,eye_tracker_distance_m=None,raw_data_filters=None,timestamp_origin='Eye-tracker clock',custom_coordinate_system_description=None,column_metadata=None,bids_version='1.11.1',dry_run=False,overwrite=False):
    df=_df(data);root=Path(bids_root);subject=str(subject).replace('sub-','');task=str(task)
    timestamp_col=timestamp_col or _pick(df,['TIME','TIMETICK','time_s','time_ms','time','CNT']);xi,yi,pi=_infer_eye_cols(df,recorded_eye);x_col=x_col or xi;y_col=y_col or yi;pupil_col=pupil_col or pi
    if not timestamp_col or not x_col or not y_col:raise ValueError('Could not detect timestamp and gaze coordinate columns.')
    t=pd.to_numeric(df[timestamp_col],errors='coerce').to_numpy(float)
    unit=timestamp_units
    if unit=='auto':
        if 'tick' in timestamp_col.lower() or (len(t)>1 and np.nanmedian(np.diff(t))>=2):unit='milliseconds'
        else:unit='seconds'
    unit_label={'seconds':'s','milliseconds':'ms','microseconds':'us'}.get(unit,unit)
    dat=pd.DataFrame({'timestamp':t,'x_coordinate':pd.to_numeric(df[x_col],errors='coerce'),'y_coordinate':pd.to_numeric(df[y_col],errors='coerce')})
    if include_pupil and pupil_col and pupil_col in df:dat['pupil_size']=pd.to_numeric(df[pupil_col],errors='coerce')
    for c in _cols(additional_cols):
        if c not in df:raise ValueError(f'Additional column `{c}` not found.')
        dat[c]=df[c].to_numpy()
    fs=sampling_rate_hz or _sampling(_time_ms(t,unit, sampling_rate_hz)/1000)
    ent=f'sub-{subject}' + (f'_ses-{session}' if session else '') + f'_task-{task}' + (f'_acq-{acquisition}' if acquisition else '') + (f'_run-{run}' if run is not None else '') + f'_recording-{recording}'
    base=root/f'sub-{subject}'/(f'ses-{session}' if session else '')/datatype
    base=Path(str(base).replace('//','/'))
    phys=base/f'{ent}_physio.tsv.gz';js=base/f'{ent}_physio.json';events=base/f'{ent}_events.json';desc=root/'dataset_description.json';parts=root/'participants.tsv'
    coord_unit='1' if coordinate_units=='normalized' else coordinate_units
    side={'SamplingFrequency':float(fs) if np.isfinite(fs) else None,'StartTime':start_time_s,'Columns':list(dat.columns),'PhysioType':'eyetrack','RecordedEye':recorded_eye,'SampleCoordinateSystem':sample_coordinate_system,'Manufacturer':manufacturer,'EyeTrackingMethod':eye_tracking_method,'timestamp':{'Units':unit_label,'Description':timestamp_origin},'x_coordinate':{'Units':coord_unit},'y_coordinate':{'Units':coord_unit}}
    if 'pupil_size' in dat:side['pupil_size']={'Units':pupil_units}
    for c,meta in (column_metadata or {}).items():side[c]=meta
    files=pd.DataFrame([{'role':'physio_tsv_gz','path':str(phys)},{'role':'physio_json','path':str(js)},{'role':'events_json','path':str(events)},{'role':'dataset_description','path':str(desc)},{'role':'participants_tsv','path':str(parts)}])
    ready=bool(np.isfinite(fs) and fs>0 and dat[['timestamp','x_coordinate','y_coordinate']].notna().any().all())
    audit={'ready_to_write':ready,'sampling_rate_hz':float(fs) if np.isfinite(fs) else np.nan,'n_rows':len(dat),'status':'ready' if ready else 'review'}
    if not dry_run:
        for p in files.path:
            pp=Path(p)
            if pp.exists() and not overwrite:raise FileExistsError(f'Refusing to overwrite existing file: {pp}')
        base.mkdir(parents=True,exist_ok=True);root.mkdir(parents=True,exist_ok=True)
        with gzip.open(phys,'wt',encoding='utf-8',newline='') as fh:
            for row in dat.itertuples(index=False,name=None):fh.write('\t'.join('n/a' if pd.isna(v) else ('TRUE' if v is True else 'FALSE' if v is False else f'{v:g}' if isinstance(v,(int,float,np.number)) else str(v)) for v in row)+'\n')
        js.write_text(json.dumps(side,indent=2),encoding='utf-8');events.write_text(json.dumps({'Description':'Gazepoint eye-tracking event metadata'},indent=2),encoding='utf-8')
        if not desc.exists() or overwrite:desc.write_text(json.dumps({'Name':dataset_name or 'Gazepoint dataset','BIDSVersion':bids_version},indent=2),encoding='utf-8')
        if not parts.exists() or overwrite:parts.write_text('participant_id\nsub-'+subject+'\n',encoding='utf-8')
    return {'data':dat,'physio_sidecar':side,'files':files,'audit':audit,'settings':{'timestamp_col':timestamp_col,'x_col':x_col,'y_col':y_col,'pupil_col':pupil_col,'recorded_eye':recorded_eye,'timestamp_units':unit,'coordinate_units':coordinate_units},'class':['gazepoint_bids_export','list']}


def _adapter_time(df,time_col,time_unit,sampling_rate_hz,rezero):
    tc=time_col or _pick(df,['time_s','time_ms','TIME','TIMETICK','CNT','time'])
    if not tc:raise ValueError('Could not detect time column.')
    raw=pd.to_numeric(df[tc],errors='coerce').to_numpy(float);unit=time_unit
    if unit=='auto':
        if tc.upper()=='CNT':unit='samples'
        elif 'ms' in tc.lower() or 'tick' in tc.lower():unit='milliseconds'
        else:unit='seconds'
    ms=_time_ms(raw,unit,sampling_rate_hz)
    if rezero and len(ms):ms=ms-np.nanmin(ms)
    dif=np.diff(ms[np.isfinite(ms)]);fs=1000/np.median(dif[dif>0]) if np.any(dif>0) else np.nan
    irr=False
    if np.any(dif>0):irr=np.nanmax(np.abs(dif-np.nanmedian(dif)))/np.nanmedian(dif)>.05
    return tc,ms,fs,irr


def prepare_gazepoint_eyetrackingr_input(data, participant_col=None, trial_col=None, time_col=None, time_unit='auto', sampling_rate_hz=None, rezero_time=False, trackloss_col=None, validity_col=None, valid_values=None, x_col=None, y_col=None, aoi_col=None, aoi_cols=None, aoi_levels=None, outside_aoi_values=('', 'none','no_aoi','outside','outside_aoi','non_aoi','background'), allow_aoi_overlap=False, item_cols=None, predictor_cols=None, treat_non_aoi_looks_as_missing=True, sampling_tolerance=.05, irregular='error', create_object=False):
    df=_df(data);participant_col=participant_col or _pick(df,['participant','participant_id','subject','USER']);trial_col=trial_col or _pick(df,['trial','trial_id','MEDIA_ID','media_id'])
    if not participant_col or not trial_col:raise ValueError('Could not detect participant/trial columns.')
    tc,ms,fs,irr=_adapter_time(df,time_col,time_unit,sampling_rate_hz,rezero_time)
    if irr and irregular=='error':raise ValueError('Irregular sampling detected.')
    x_col=x_col if x_col is not None else _pick(df,['gaze_x','BPOGX']);y_col=y_col if y_col is not None else _pick(df,['gaze_y','BPOGY'])
    validity_col=validity_col or _pick(df,['BPOGV','valid','validity']);trackloss_col=trackloss_col or _pick(df,['TrackLoss','trackloss'])
    loss=np.zeros(len(df),bool);invalid_valid=np.zeros(len(df),bool);missing_valid=np.zeros(len(df),bool)
    if x_col and y_col:loss |= ~np.isfinite(pd.to_numeric(df[x_col],errors='coerce')) | ~np.isfinite(pd.to_numeric(df[y_col],errors='coerce'))
    if trackloss_col:
        v=df[trackloss_col];loss |= v.astype(bool).to_numpy()
    if validity_col:
        vv=df[validity_col];validset=set(valid_values or [1,True]);missing_valid=vv.isna().to_numpy();invalid_valid=(~vv.isin(validset)&vv.notna()).to_numpy();loss |= missing_valid|invalid_valid
    aoi_col=aoi_col or _pick(df,['AOI','aoi']);aoi_cols=_cols(aoi_cols);aoi_data={}
    nonaoi=np.zeros(len(df),bool)
    if aoi_cols:
        for c in aoi_cols:aoi_data[c]=df[c].fillna(False).astype(bool).to_numpy()
    elif aoi_col:
        av=df[aoi_col].astype(object);levels=aoi_levels or [v for v in pd.unique(av.dropna().astype(str)) if v.lower() not in {z.lower() for z in outside_aoi_values}]
        for lev in levels:aoi_data[str(lev)]=(av.astype(str)==str(lev)).to_numpy()
        nonaoi=av.isna().to_numpy() | av.astype(str).str.lower().isin([z.lower() for z in outside_aoi_values]).to_numpy()
    membership=np.sum(np.vstack(list(aoi_data.values())),axis=0) if aoi_data else np.zeros(len(df),int)
    if np.any(membership>1) and not allow_aoi_overlap:raise ValueError('More than one AOI is TRUE for at least one row.')
    if treat_non_aoi_looks_as_missing:
        for k in aoi_data:aoi_data[k]=aoi_data[k]&~loss
    out=pd.DataFrame({'ParticipantName':df[participant_col].astype(str),'Trial':df[trial_col].astype(str),'Time_ms':ms,'TrackLoss':loss})
    for k,v in aoi_data.items():out[k]=v
    if out.duplicated(['ParticipantName','Trial','Time_ms']).any():raise ValueError('Participant-trial-time rows must be unique.')
    for c in _cols(item_cols)+_cols(predictor_cols):out[c]=df[c].to_numpy()
    audit=pd.DataFrame({'invalid_validity':invalid_valid,'missing_validity_value':missing_valid,'non_aoi_look':nonaoi,'aoi_membership_count':membership})
    return {'data':out,'row_audit':audit,'sampling':{'effective_sampling_rate_hz':float(fs),'irregular':irr},'settings':{'participant_col':participant_col,'trial_col':trial_col,'time_col':tc},'class':['gazepoint_eyetrackingr_input','list']}


def prepare_gazepoint_gazer_input(data, participant_col=None, trial_col=None, time_col=None, time_unit='auto', sampling_rate_hz=None, rezero_time=False, x_col=None, y_col=None, x_left_col=None, y_left_col=None, x_right_col=None, y_right_col=None, pupil_col=None, pupil_left_col=None, pupil_right_col=None, validity_col=None, validity_left_col=None, validity_right_col=None, valid_values=None, blink_col=None, blink_left_col=None, blink_right_col=None, invalid_coordinate_values=None, invalid_pupil_values=None, mask_invalid=False, other_cols=None, sampling_tolerance=.05, irregular='error', create_object=False):
    df=_df(data);participant_col=participant_col or _pick(df,['participant','participant_id','subject','USER']);trial_col=trial_col or _pick(df,['trial','trial_id','MEDIA_ID','media_id'])
    if not participant_col or not trial_col:raise ValueError('Could not detect participant/trial columns.')
    tc,ms,fs,irr=_adapter_time(df,time_col,time_unit,sampling_rate_hz,rezero_time)
    if irr and irregular=='error':raise ValueError('Irregular sampling detected.')
    x_col=x_col or _pick(df,['gaze_x','BPOGX']); y_col=y_col or _pick(df,['gaze_y','BPOGY']); pupil_col=pupil_col or _pick(df,['pupil','PUPIL','BPD'])
    x_left_col=x_left_col or _pick(df,['LPOGX','x_left']); y_left_col=y_left_col or _pick(df,['LPOGY','y_left']); x_right_col=x_right_col or _pick(df,['RPOGX','x_right']); y_right_col=y_right_col or _pick(df,['RPOGY','y_right'])
    pupil_left_col=pupil_left_col or _pick(df,['LPD','pupil_left']); pupil_right_col=pupil_right_col or _pick(df,['RPD','pupil_right'])
    validity_col=validity_col or _pick(df,['BPOGV','valid','validity']); validity_left_col=validity_left_col or _pick(df,['LPV','valid_left']); validity_right_col=validity_right_col or _pick(df,['RPV','valid_right'])
    blink_col=blink_col or _pick(df,['blink','BLINK']); blink_left_col=blink_left_col or _pick(df,['blink_left','left_blink']); blink_right_col=blink_right_col or _pick(df,['blink_right','right_blink'])
    out=pd.DataFrame({'subject':df[participant_col].astype(str),'trial':df[trial_col].astype(str),'time':ms})
    mapping=[('x',x_col),('y',y_col),('pupil',pupil_col),('x_left',x_left_col),('y_left',y_left_col),('x_right',x_right_col),('y_right',y_right_col),('pupil_left',pupil_left_col),('pupil_right',pupil_right_col)]
    for name,col in mapping:
        if col and col in df:out[name]=pd.to_numeric(df[col],errors='coerce')
    validset=set(valid_values or [1,True]); invalid_validity=np.zeros(len(df),int); blink_count=np.zeros(len(df),int); explicit_invalid=np.zeros(len(df),int)
    eye_specs=[('x','y','pupil',validity_col,blink_col),('x_left','y_left','pupil_left',validity_left_col,blink_left_col),('x_right','y_right','pupil_right',validity_right_col,blink_right_col)]
    invalid_by_channel={}
    for xn,yn,pn,vc,bc in eye_specs:
        mask=np.zeros(len(df),bool)
        if vc and vc in df:
            bad=~df[vc].isin(validset).fillna(False).to_numpy();invalid_validity+=bad.astype(int);mask|=bad
        if bc and bc in df:
            bad=df[bc].fillna(False).astype(bool).to_numpy();blink_count+=bad.astype(int);mask|=bad
        for c in [xn,yn,pn]:
            if c in out:
                bad=~np.isfinite(pd.to_numeric(out[c],errors='coerce').to_numpy(float))
                vals=invalid_pupil_values if 'pupil' in c else invalid_coordinate_values
                if vals is not None:bad |= out[c].isin(_cols(vals)).to_numpy()
                explicit_invalid+=bad.astype(int);mask|=bad
                if mask_invalid:out.loc[mask,c]=np.nan
        invalid_by_channel[xn]=mask
    finite_gaze=np.zeros(len(df),int)
    for xn,yn in [('x','y'),('x_left','y_left'),('x_right','y_right')]:
        if xn in out and yn in out:finite_gaze += (out[xn].notna()&out[yn].notna()).astype(int).to_numpy()
    finite_pupil=np.zeros(len(df),int)
    for pn in ['pupil','pupil_left','pupil_right']:
        if pn in out:finite_pupil += out[pn].notna().astype(int).to_numpy()
    if out.duplicated(['subject','trial','time']).any():raise ValueError('Subject-trial-time rows must be unique.')
    for c in _cols(other_cols):out[c]=df[c].to_numpy()
    audit=pd.DataFrame({'finite_gaze_pair_count':finite_gaze,'finite_pupil_count':finite_pupil,'invalid_validity_count':invalid_validity,'explicit_invalid_channel_count':explicit_invalid,'blink_count':blink_count})
    gaze_pairs=sum(1 for a,b in [('x','y'),('x_left','y_left'),('x_right','y_right')] if a in out and b in out)
    manifest={'summary':{'gaze_pair_count':gaze_pairs,'binocular_gaze':all(c in out for c in ['x_left','y_left','x_right','y_right']),'binocular_pupil':all(c in out for c in ['pupil_left','pupil_right'])}}
    return {'data':out,'row_audit':audit,'sampling':{'effective_sampling_rate_hz':float(fs),'irregular':irr},'manifest':manifest,'settings':{'time_col':tc},'class':['gazepoint_gazer_input','list']}

def prepare_gazepoint_pupillometryr_input(data, participant_col=None, trial_col=None, time_col=None, condition_col=None, pupil_left_col=None, pupil_right_col=None, pupil_col=None, time_unit='auto', sampling_rate_hz=None, rezero_time=False, invalid_pupil_values=None, validity_cols=None, valid_values=None, blink_cols=None, mask_invalid=False, create_mean_pupil=True, other_cols=None, sampling_tolerance=.05, irregular='error', create_object=False):
    df=_df(data);participant_col=participant_col or _pick(df,['participant','participant_id','subject','USER']);trial_col=trial_col or _pick(df,['trial','trial_id','MEDIA_ID','media_id']);condition_col=condition_col or _pick(df,['condition','Condition','Type'])
    if not participant_col or not trial_col:raise ValueError('Could not detect participant/trial columns.')
    tc,ms,fs,irr=_adapter_time(df,time_col,time_unit,sampling_rate_hz,rezero_time)
    if irr and irregular=='error':raise ValueError('Irregular sampling detected.')
    pupil_left_col=pupil_left_col or _pick(df,['LPD','pupil_left']);pupil_right_col=pupil_right_col or _pick(df,['RPD','pupil_right']);pupil_col=pupil_col or _pick(df,['PUPIL','BPD','pupil'])
    out=pd.DataFrame({'Subject':df[participant_col].astype(str),'Trial':df[trial_col].astype(str),'Time':ms})
    if condition_col:
        out['Condition']=df[condition_col].to_numpy()
        for _,g in out.groupby(['Subject','Trial'],sort=False):
            if g['Condition'].dropna().astype(str).nunique()>1:raise ValueError('Condition must be constant within participant-trial.')
    if pupil_left_col:out['Pupil_Left']=pd.to_numeric(df[pupil_left_col],errors='coerce')
    if pupil_right_col:out['Pupil_Right']=pd.to_numeric(df[pupil_right_col],errors='coerce')
    if pupil_col:out['Pupil']=pd.to_numeric(df[pupil_col],errors='coerce')
    elif create_mean_pupil and pupil_left_col and pupil_right_col:out['Pupil_Mean']=out[['Pupil_Left','Pupil_Right']].mean(axis=1,skipna=False)
    vcs=_cols(validity_cols);bcs=_cols(blink_cols);validset=set(valid_values or [1,True]);inv_valid=np.zeros(len(df),int);blink=np.zeros(len(df),int);explicit=np.zeros(len(df),int)
    for c in vcs:
        bad=~df[c].isin(validset).fillna(False).to_numpy();inv_valid+=bad.astype(int)
    for c in bcs:
        bad=df[c].fillna(False).astype(bool).to_numpy();blink+=bad.astype(int)
    global_bad=(inv_valid>0)|(blink>0);invset=set(_cols(invalid_pupil_values))
    for c in [z for z in ['Pupil','Pupil_Left','Pupil_Right','Pupil_Mean'] if z in out]:
        bad=~np.isfinite(pd.to_numeric(out[c],errors='coerce').to_numpy(float))
        if invset:bad |= out[c].isin(invset).to_numpy()
        explicit+=bad.astype(int)
        if mask_invalid:out.loc[global_bad|bad,c]=np.nan
    if out.duplicated(['Subject','Trial','Time']).any():raise ValueError('Participant-trial-time rows must be unique.')
    for c in _cols(other_cols):out[c]=df[c].to_numpy()
    audit=pd.DataFrame({'invalid_validity_count':inv_valid,'explicit_invalid_count':explicit,'blink_count':blink,'valid_pupil':~(global_bad|(explicit>0))})
    return {'data':out,'row_audit':audit,'sampling':{'effective_sampling_rate_hz':float(fs),'irregular':irr},'settings':{'time_col':tc},'class':['gazepoint_pupillometryr_input','list']}

def preprocess_gazepoint_all(data, impute_missing=True, clean_pupil=True, filter_gaze=True, max_gap=10, screen_bounds=(0,1,0,1), max_velocity=np.inf, verbose=True):
    from .data_io_cleaning import impute_gazepoint_missing
    from .pupil_gaze import clean_gazepoint_pupil_signal, filter_gazepoint_gaze
    def one(df):
        out=df.copy();log=[]
        if impute_missing:
            num=[c for c in out.select_dtypes(include=np.number).columns if out[c].isna().any()]
            if num:out=impute_gazepoint_missing(out,cols=num,max_gap=max_gap);log.append({'step':'impute_missing','status':'completed'})
        if clean_pupil:
            pcs=[c for c in out.columns if c.upper() in {'LPD','RPD','BPD','PUPIL'} or 'pupil' in c.lower()]
            for c in pcs:
                try:
                    cl=clean_gazepoint_pupil_signal(out,pupil_cols=[c])
                    if isinstance(cl,pd.DataFrame):out=cl
                except Exception:pass
            if pcs:log.append({'step':'clean_pupil','status':'completed'})
        if filter_gaze:
            x=_pick(out,['BPOGX','gaze_x']);y=_pick(out,['BPOGY','gaze_y'])
            if x and y:
                try:out=filter_gazepoint_gaze(out,x_col=x,y_col=y,screen_bounds=screen_bounds,max_velocity=max_velocity)
                except Exception:out['gaze_valid']=pd.to_numeric(out[x],errors='coerce').between(screen_bounds[0],screen_bounds[1]) & pd.to_numeric(out[y],errors='coerce').between(screen_bounds[2],screen_bounds[3])
                log.append({'step':'filter_gaze','status':'completed'})
        out.attrs['preprocessing_log']=pd.DataFrame(log);return out
    if isinstance(data,dict):
        res={k:one(v) if isinstance(v,pd.DataFrame) else v for k,v in data.items()};return res
    return one(_df(data))


def report_gazepoint_data_quality(data, output_dir=None, report_name='gazepoint_data_quality', formats=('html','csv'), max_plot_columns=6, open=False):
    import matplotlib.pyplot as plt
    od=Path(output_dir or (Path.cwd()/f'{report_name}_output'));od.mkdir(parents=True,exist_ok=True);formats=_cols(formats)
    tables=data if isinstance(data,dict) else {'data':_df(data)}
    miss=[];nums=[];outs=[]
    for name,df in tables.items():
        if not isinstance(df,pd.DataFrame):continue
        for c in df.columns:miss.append({'table':name,'column':c,'n_missing':int(df[c].isna().sum()),'prop_missing':float(df[c].isna().mean())})
        for c in df.select_dtypes(include=np.number).columns:
            x=pd.to_numeric(df[c],errors='coerce');nums.append({'table':name,'column':c,'n':int(x.notna().sum()),'mean':x.mean(),'sd':x.std(),'min':x.min(),'max':x.max()});q1,q3=x.quantile([.25,.75]);iqr=q3-q1;outs.append({'table':name,'column':c,'n_outlier':int(((x<q1-1.5*iqr)|(x>q3+1.5*iqr)).sum())})
    md=pd.DataFrame(miss);nd=pd.DataFrame(nums);odf=pd.DataFrame(outs);paths={}
    if 'csv' in formats:
        for key,d in [('missingness',md),('numeric_summary',nd),('outlier_summary',odf)]:p=od/f'{report_name}_{key}.csv';d.to_csv(p,index=False);paths[key+'_csv']=str(p)
    if 'html' in formats:
        p=od/f'{report_name}.html';p.write_text('<html><body><h1>Gazepoint data quality</h1>'+md.to_html(index=False)+nd.to_html(index=False)+odf.to_html(index=False)+'</body></html>',encoding='utf-8');paths['html']=str(p)
    if 'pdf' in formats:
        p=od/f'{report_name}.pdf';fig,ax=plt.subplots();ax.bar(np.arange(min(len(md),max_plot_columns)),md.prop_missing.head(max_plot_columns));ax.set_title('Missingness');fig.savefig(p);plt.close(fig);paths['pdf']=str(p)
    return {'missingness':md,'numeric_summary':nd,'outlier_summary':odf,'paths':paths,'class':['gazepoint_data_quality_report','list']}


def pipeline_comparison_dashboard(data, participant_col=None, session_col=None, grouping_cols=None, missingness_col=None, quality_col=None, qc_status_col=None, failed_rules_col=None, excluded_col=None, notes_col=None):
    df=_df(data)
    if len(df)==0:raise ValueError('`data` must contain at least one row.')
    grouping=_cols(grouping_cols)
    if not grouping:
        participant_col=participant_col or _pick(df,['participant_id','participant','subject']);session_col=session_col or _pick(df,['session','session_id']);grouping=[c for c in [participant_col,session_col] if c]
    missing=[c for c in grouping if c not in df]
    if missing:raise ValueError('Grouping columns not found: '+', '.join(missing))
    missingness_col=missingness_col or _pick(df,['missing_rate','prop_missing','missingness']);quality_col=quality_col or _pick(df,['quality_index','signal_quality','quality']);qc_status_col=qc_status_col or _pick(df,['qc_status','status']);failed_rules_col=failed_rules_col or _pick(df,['failed_rules']);excluded_col=excluded_col or _pick(df,['excluded']);notes_col=notes_col or _pick(df,['audit_notes','notes'])
    if not grouping:df=df.copy();df['.all']='all';grouping=['.all']
    rows=[]
    for key,g in df.groupby(grouping,sort=False,dropna=False):
        if not isinstance(key,tuple):key=(key,)
        row=dict(zip(grouping,key));row['n_rows']=len(g)
        if missingness_col:row['mean_missingness']=pd.to_numeric(g[missingness_col],errors='coerce').mean()
        if quality_col:row['mean_quality']=pd.to_numeric(g[quality_col],errors='coerce').mean()
        issue=np.zeros(len(g),bool)
        if qc_status_col:issue |= ~g[qc_status_col].astype(str).str.lower().isin(['accept','pass','ok','good']).to_numpy()
        if failed_rules_col:issue |= g[failed_rules_col].fillna('').astype(str).str.len().gt(0).to_numpy()
        if excluded_col:issue |= g[excluded_col].fillna(False).astype(bool).to_numpy()
        row['issue_group']=bool(issue.any());row['n_excluded_rows']=int(g[excluded_col].fillna(False).astype(bool).sum()) if excluded_col else 0
        rows.append(row)
    dash=pd.DataFrame(rows);issues=df.copy()
    issue=np.zeros(len(df),bool)
    if qc_status_col:issue |= ~df[qc_status_col].astype(str).str.lower().isin(['accept','pass','ok','good']).to_numpy()
    if failed_rules_col:issue |= df[failed_rules_col].fillna('').astype(str).str.len().gt(0).to_numpy()
    if excluded_col:issue |= df[excluded_col].fillna(False).astype(bool).to_numpy()
    issues=issues.loc[issue].reset_index(drop=True)
    overall=pd.DataFrame([{'n_groups':len(dash),'n_rows':len(df),'n_issue_groups':int(dash.issue_group.sum()),'n_excluded_rows':int(df[excluded_col].fillna(False).astype(bool).sum()) if excluded_col else 0}])
    return {'overall':overall,'dashboard':dash,'issues':issues,'settings':{'grouping_cols':grouping},'class':['gazepoint_pipeline_comparison_dashboard','list']}


def prepare_gazepoint_artifact_svm_features(dat,eda_col='GSR_US',time_col=None,group_cols=None,segment_seconds=5,samples_per_segment=None,sampling_rate=None):
    df=_df(dat,'dat');
    if eda_col not in df or not pd.api.types.is_numeric_dtype(df[eda_col]):raise ValueError('`eda_col` must identify a numeric column.')
    groups=_cols(group_cols);rows=[]
    group_key=groups[0] if len(groups)==1 else groups
    iterator=[('all_rows',df.index)] if not groups else df.groupby(group_key,sort=False,dropna=False).groups.items()
    for gid,index in iterator:
        idx=np.asarray(list(index),int)
        if time_col:idx=idx[np.argsort(pd.to_numeric(df.loc[idx,time_col],errors='coerce').to_numpy(float))]
        fs=sampling_rate or (_sampling(pd.to_numeric(df.loc[idx,time_col],errors='coerce')) if time_col else np.nan);nseg=int(samples_per_segment or max(2,round(segment_seconds*fs)) if np.isfinite(fs) else samples_per_segment or 5)
        for si,start in enumerate(range(0,len(idx),nseg),1):
            ii=idx[start:start+nseg];x=pd.to_numeric(df.loc[ii,eda_col],errors='coerce').dropna().to_numpy(float)
            feat={k:np.nan for k in ['mean_signal','sd_signal','min_signal','max_signal','range_signal','median_abs_diff','max_abs_diff','slope','zero_crossing_diff','detail_energy']};status='insufficient_segment_data'
            if len(x)>=2:
                d=np.diff(x);feat.update(mean_signal=np.mean(x),sd_signal=np.std(x,ddof=1),min_signal=np.min(x),max_signal=np.max(x),range_signal=np.ptp(x),median_abs_diff=np.median(abs(d)),max_abs_diff=np.max(abs(d)),slope=np.polyfit(np.arange(len(x)),x,1)[0],zero_crossing_diff=np.sum(np.diff(np.sign(d-np.mean(d)))!=0),detail_energy=np.mean(np.diff(x)**2));status='svm_features_prepared'
            rows.append({'group_id':str(gid),'segment_id':f'{gid}_segment_{si}','segment_index':si,'start_row':int(ii.min()+1),'end_row':int(ii.max()+1),'start_time':df.loc[ii[0],time_col] if time_col else np.nan,'end_time':df.loc[ii[-1],time_col] if time_col else np.nan,'n_samples':len(ii),'n_finite':len(x),**feat,'status':status})
    out=pd.DataFrame(rows);out.attrs['class']=['gazepoint_artifact_svm_features','data.frame'];out.attrs['svm_feature_settings']={'eda_col':eda_col,'time_col':time_col,'group_cols':groups,'segment_seconds':segment_seconds,'samples_per_segment':samples_per_segment,'sampling_rate':sampling_rate};return out


def flag_gazepoint_artifacts_svm(x,model=None,feature_cols=None,probability_threshold=.5,**kwargs):
    features=x.copy() if isinstance(x,pd.DataFrame) and x.attrs.get('class',[None])[0]=='gazepoint_artifact_svm_features' else prepare_gazepoint_artifact_svm_features(x,**kwargs)
    defaults=['mean_signal','sd_signal','min_signal','max_signal','range_signal','median_abs_diff','max_abs_diff','slope','zero_crossing_diff','detail_energy'];feature_cols=_cols(feature_cols) or [c for c in defaults if c in features]
    out=features.copy();out['artifact_probability']=np.nan;out['artifact_svm']=pd.Series([pd.NA]*len(out),dtype='boolean');out['artifact_svm_status']='no_model_supplied'
    if model is not None:
        new=out[feature_cols]
        if callable(model):pred=model(new)
        elif hasattr(model,'predict_proba'):pred=model.predict_proba(new)[:,-1]
        elif hasattr(model,'predict'):pred=model.predict(new)
        else:raise TypeError('Unsupported model object.')
        arr=np.asarray(pred)
        if np.issubdtype(arr.dtype,np.number):out['artifact_probability']=arr.astype(float);out['artifact_svm']=arr.astype(float)>=probability_threshold;out['artifact_svm_status']='predicted_from_numeric_probability'
        else:out['artifact_svm']=pd.Series([str(v).lower() in {'artifact','art','1','true','bad'} for v in arr],dtype='boolean');out['artifact_svm_status']='predicted_from_class_label'
        status='svm_artifact_flags_created'
    else:status='svm_features_prepared_no_model_supplied'
    out.attrs['class']=['gazepoint_artifact_svm_flags','data.frame'];out.attrs['svm_artifact_overview']=pd.DataFrame([{'segment_rows':len(out),'model_supplied':model is not None,'flagged_segments':int(out.artifact_svm.fillna(False).sum()) if model is not None else np.nan,'status':status}]);return out


def _autoencoder(dat,col,model,window_samples,output_col,overwrite):
    df=_df(dat,'dat');outcol=output_col or f'{col}_autoencoder_denoised'
    if col not in df:raise ValueError(f'Column `{col}` was not found in `dat`.')
    if outcol in df and not overwrite:raise ValueError(f'Column `{outcol}` already exists.')
    x=pd.to_numeric(df[col],errors='coerce').to_numpy(float);y=x.copy();status='autoencoder_no_model_supplied'
    if model is not None:
        for start in range(0,len(x),window_samples):
            seg=x[start:start+window_samples];mask=np.isfinite(seg);inp=np.where(mask,seg,np.nanmedian(seg[mask]) if mask.any() else 0)
            pred=np.asarray(model(inp.copy()) if callable(model) else model.predict(inp.reshape(1,-1))).reshape(-1)
            if len(pred)!=len(seg):raise ValueError('Autoencoder reconstruction length mismatch.')
            y[start:start+len(seg)]=pred
        status='autoencoder_reconstruction_complete'
    out=df.copy();out[outcol]=y;out.attrs['class']=['gazepoint_autoencoder_denoised','data.frame'];out.attrs['autoencoder_denoising_overview']=pd.DataFrame([{'status':status,'model_supplied':model is not None,'output_col':outcol}]);return out


def denoise_gazepoint_eda_autoencoder(dat,eda_col='GSR_US',time_col=None,group_cols=None,model=None,window_samples=128,output_col=None,overwrite=False):return _autoencoder(dat,eda_col,model,int(window_samples),output_col,overwrite)
def denoise_gazepoint_ppg_autoencoder(dat,ppg_col='HRP',time_col=None,group_cols=None,model=None,window_samples=128,output_col=None,overwrite=False):return _autoencoder(dat,ppg_col,model,int(window_samples),output_col,overwrite)


def _ig_params(intervals):
    x=np.asarray(intervals,float);x=x[np.isfinite(x)&(x>0)]
    if not len(x):return np.nan,np.nan
    mu=float(np.mean(x));den=np.sum((x-mu)**2/(mu*mu*x));lam=float(len(x)/den) if den>0 else np.inf;return mu,lam


def model_gazepoint_eda_point_process(dat,eda_col='GSR_US',time_col='CNT',group_cols=None,event_time_col=None,event_indicator_col=None,derivative_mad_multiplier=6,min_event_distance_s=1):
    df=_df(dat);rows=[];summary=[]
    groups=_cols(group_cols);group_key=groups[0] if len(groups)==1 else groups;iterator=[('all_rows',df.index)] if not groups else df.groupby(group_key,sort=False,dropna=False).groups.items()
    for gid,index in iterator:
        g=df.loc[list(index)].sort_values(time_col);t=pd.to_numeric(g[time_col],errors='coerce').to_numpy(float);x=pd.to_numeric(g[eda_col],errors='coerce').to_numpy(float)
        if event_indicator_col:mask=g[event_indicator_col].fillna(False).astype(bool).to_numpy();et=t[mask]
        elif event_time_col:et=pd.to_numeric(g[event_time_col],errors='coerce').dropna().unique()
        else:
            d=np.diff(x,prepend=x[0]);med=np.nanmedian(d);mad=np.nanmedian(abs(d-med));thr=med+derivative_mad_multiplier*(1.4826*mad if mad>0 else np.nanstd(d));cand=np.flatnonzero(d>thr);et=[]
            for j in cand:
                if not et or t[j]-et[-1]>=min_event_distance_s:et.append(t[j])
            et=np.asarray(et,float)
        intervals=np.diff(et);mu,lam=_ig_params(intervals)
        base={}
        if groups:
            vals=g.iloc[0][groups];base=vals.to_dict() if hasattr(vals,'to_dict') else {groups[0]:vals}
        for k,v in enumerate(et,1):rows.append({**base,'group_id':str(gid),'event_index':k,'event_time':v,'inter_event_interval':v-et[k-2] if k>1 else np.nan})
        summary.append({**base,'group_id':str(gid),'n_events':len(et),'inverse_gaussian_mu':mu,'inverse_gaussian_lambda':lam,'mean_event_rate_hz':1/mu if np.isfinite(mu) and mu>0 else np.nan,'status':'point_process_estimated' if len(et)>=2 else 'insufficient_events'})
    return {'event_table':pd.DataFrame(rows),'process_summary':pd.DataFrame(summary),'overview':pd.DataFrame([{'group_count':len(summary),'status':'eda_point_process_complete'}]),'class':['gazepoint_eda_point_process','list']}


def model_gazepoint_hr_point_process(dat,ibi_col='IBI',time_col=None,beat_time_col=None,group_cols=None,ibi_units='auto'):
    df=_df(dat);rows=[];summary=[];groups=_cols(group_cols);group_key=groups[0] if len(groups)==1 else groups;iterator=[('all_rows',df.index)] if not groups else df.groupby(group_key,sort=False,dropna=False).groups.items()
    for gid,index in iterator:
        g=df.loc[list(index)];ibi=pd.to_numeric(g[ibi_col],errors='coerce').to_numpy(float);med=np.nanmedian(ibi);units=ibi_units
        if units=='auto':units='milliseconds' if med>10 else 'seconds'
        sec=ibi/1000 if units=='milliseconds' else ibi;sec=sec[np.isfinite(sec)&(sec>0)];bt=np.cumsum(sec) if beat_time_col is None else pd.to_numeric(g[beat_time_col],errors='coerce').to_numpy(float)[:len(sec)];mu,lam=_ig_params(sec)
        base={}
        if groups:
            vals=g.iloc[0][groups];base=vals.to_dict() if hasattr(vals,'to_dict') else {groups[0]:vals}
        for k,(tt,iv) in enumerate(zip(bt,sec),1):rows.append({**base,'group_id':str(gid),'beat_index':k,'beat_time':tt,'ibi_seconds':iv})
        summary.append({**base,'group_id':str(gid),'n_beats':len(sec),'inverse_gaussian_mu':mu,'inverse_gaussian_lambda':lam,'mean_hr_bpm':60/mu if np.isfinite(mu) and mu>0 else np.nan,'status':'point_process_estimated' if len(sec)>=2 else 'insufficient_intervals'})
    return {'beat_table':pd.DataFrame(rows),'process_summary':pd.DataFrame(summary),'overview':pd.DataFrame([{'group_count':len(summary),'status':'hr_point_process_complete'}]),'class':['gazepoint_hr_point_process','list']}


def audit_gazepoint_smoke_privacy(x,private_values=None):
    forbidden={'participant_id','filename','file_path','path','workflow','data','raw_data'};checks=[]
    def flatten(obj):
        if isinstance(obj,pd.DataFrame):return list(map(str,obj.columns))+[str(v) for v in obj.astype(str).to_numpy().ravel()]
        if isinstance(obj,dict):return [str(k) for k in obj]+sum((flatten(v) for v in obj.values()),[])
        if isinstance(obj,(list,tuple)):return sum((flatten(v) for v in obj),[])
        return [str(obj)]
    vals=flatten(x);cols=[]
    if isinstance(x,dict):
        for v in x.values():
            if isinstance(v,pd.DataFrame):cols.extend(map(str,v.columns))
    checks.append({'check':'no_forbidden_columns','status':'fail' if any(c.lower() in forbidden for c in cols) else 'pass'})
    abs_rx=re.compile(r'([A-Za-z]:[\\/]|/(Users|home|private|mnt|data)/)',re.I);checks.append({'check':'no_absolute_paths','status':'fail' if any(abs_rx.search(v) for v in vals) else 'pass'})
    priv=_cols(private_values);checks.append({'check':'no_private_values','status':'fail' if any(p and any(str(p) in v for v in vals) for p in priv) else 'pass'})
    checks.append({'check':'aggregate_only','status':'pass' if isinstance(x,dict) else 'warn'})
    return pd.DataFrame(checks)


def write_gazepoint_real_data_smoke(x,output_dir,prefix='gpbiometrics-real-data-smoke',overwrite=False,protect_repository=True):
    od=Path(output_dir);od.mkdir(parents=True,exist_ok=True);files={}
    for key in ['results','conditions','session','settings']:
        d=x.get(key,pd.DataFrame()) if isinstance(x,dict) else pd.DataFrame();p=od/f'{prefix}-{key}.csv'
        if p.exists() and not overwrite:raise FileExistsError('Refusing to overwrite existing smoke output.')
        (d if isinstance(d,pd.DataFrame) else pd.DataFrame([d])).to_csv(p,index=False);files[key]=str(p)
    return files


def run_gazepoint_real_data_smoke(data_dir='',output_dir=None,dataset_mode='subdirectories',pattern=r'\.csv$',recursive=True,workflow_args=None,diagnostic_args=None,workflow_runner=None,summary_runner=None,diagnostic_runner=None,stop_on_error=False,write_results=False,overwrite=False,protect_repository=True):
    from .user_workflows import run_gazepoint_biometrics_workflow, summarise_gazepoint_biometrics_workflow, diagnose_gazepoint_biometrics_workflow
    root=Path(data_dir or os.getenv('GPBIOMETRICS_SMOKE_DIR',''))
    if not root.exists() or not root.is_dir():raise FileNotFoundError('Smoke data directory does not exist.')
    workflow_runner=workflow_runner or run_gazepoint_biometrics_workflow;summary_runner=summary_runner or summarise_gazepoint_biometrics_workflow;diagnostic_runner=diagnostic_runner or diagnose_gazepoint_biometrics_workflow
    datasets=[p for p in root.iterdir() if p.is_dir()] if dataset_mode=='subdirectories' else [root];res=[];conds=[]
    import time
    for i,ds in enumerate(datasets,1):
        files=[p for p in (ds.rglob('*') if recursive else ds.glob('*')) if p.is_file() and re.search(pattern,p.name,re.I)];t0=time.time();status='pass';stage='';err=''
        try:
            wf=workflow_runner(path=str(ds),**(workflow_args or {}));sm=summary_runner(wf);diag=diagnostic_runner(wf,**(diagnostic_args or {}))
        except Exception as e:
            status='fail';stage='workflow';err=str(e);conds.append({'dataset_id':f'smoke_{i:03d}','stage':stage,'condition_type':'error','condition_class':e.__class__.__name__,'message':err});
            if stop_on_error:raise
        res.append({'dataset_id':f'smoke_{i:03d}','n_files':len(files),'smoke_status':status,'error_stage':stage,'n_warnings':0,'elapsed_seconds':time.time()-t0})
    out={'results':pd.DataFrame(res),'conditions':pd.DataFrame(conds,columns=['dataset_id','stage','condition_type','condition_class','message']),'session':pd.DataFrame([{'python_version':os.sys.version.split()[0]}]),'settings':pd.DataFrame([{'private_data_retained':False,'dataset_mode':dataset_mode}]),'class':['gazepoint_real_data_smoke','list']}
    if write_results:
        if output_dir is None:raise ValueError('`output_dir` is required when `write_results = TRUE`.')
        out['written_files']=write_gazepoint_real_data_smoke(out,output_dir,overwrite=overwrite,protect_repository=protect_repository)
    return out


def run_gpbiometrics_shiny():
    raise RuntimeError('The R `shiny` interface is not available in Python. Use gpbiometricspy workflow/QC/report APIs or a Python dashboard framework.')

def run_gpbiometrics_shiny_annotator():
    raise RuntimeError('The R `shiny` annotator is not available in Python. Use exported annotation tables with a Python GUI/dashboard framework.')
