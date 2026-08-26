from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd


def _df(data):
    if not isinstance(data, pd.DataFrame):
        raise TypeError('`data` must be a data frame.')
    if len(data) == 0:
        raise ValueError('`data` must contain at least one row.')
    return data.copy()


def _cols(x):
    if x is None: return []
    return [x] if isinstance(x, str) else list(x)


def _numeric(data, cols, arg='metric_cols'):
    cols=_cols(cols)
    if not cols: raise ValueError(f'`{arg}` must contain at least one column.')
    miss=[c for c in cols if c not in data]
    if miss: raise ValueError(f'`{arg}` contains columns not found in `data`: {", ".join(miss)}')
    bad=[c for c in cols if not pd.api.types.is_numeric_dtype(data[c])]
    if bad: raise TypeError(f'All `{arg}` must be numeric. Non-numeric columns: {", ".join(bad)}')
    return cols


def _groups(data, cols):
    cols=_cols(cols)
    miss=[c for c in cols if c not in data]
    if miss: raise ValueError(f'`group_cols` contains columns not found in `data`: {", ".join(miss)}')
    return cols


def audit_gazepoint_beats(data, ibi_col=None, beat_time_col=None, group_cols=None,
                          min_ibi=300, max_ibi=2000, duplicate_tolerance=0,
                          max_relative_change=None):
    dat=_df(data)
    if ibi_col is None and beat_time_col is None: raise ValueError('Provide `ibi_col`, `beat_time_col`, or both.')
    for c,n in [(ibi_col,'ibi_col'),(beat_time_col,'beat_time_col')]:
        if c is not None:
            if c not in dat: raise ValueError(f'`{n}` was not found in `data`.')
            if not pd.api.types.is_numeric_dtype(dat[c]): raise TypeError(f'`{n}` must refer to a numeric column.')
    groups=_groups(dat,group_cols)
    if not np.isfinite(min_ibi) or min_ibi<=0 or not np.isfinite(max_ibi) or max_ibi<=0: raise ValueError('`min_ibi` and `max_ibi` must be positive.')
    if min_ibi>=max_ibi: raise ValueError('`min_ibi` must be smaller than `max_ibi`.')
    if duplicate_tolerance<0: raise ValueError('`duplicate_tolerance` must be non-negative.')
    if max_relative_change is not None and (not np.isfinite(max_relative_change) or max_relative_change<=0): raise ValueError('`max_relative_change` must be a single positive number.')
    dat=dat.copy();dat['_orig']=np.arange(1,len(dat)+1)
    pieces=[('all',dat)] if not groups else list(dat.groupby(groups[0] if len(groups)==1 else groups,sort=True,dropna=False))
    beats=[]; sums=[]
    for key,p in pieces:
        p=p.copy()
        if beat_time_col is not None: p=p.sort_values(beat_time_col,na_position='last',kind='stable')
        n=len(p)
        if ibi_col is not None: ibi=pd.to_numeric(p[ibi_col],errors='coerce').to_numpy(float)
        else: ibi=np.r_[np.nan,np.diff(pd.to_numeric(p[beat_time_col],errors='coerce').to_numpy(float))]
        has=np.ones(n,dtype=bool)
        if ibi_col is None and n: has[0]=False
        nonfinite=has & ~np.isfinite(ibi); short=has & np.isfinite(ibi)&(ibi<min_ibi); long=has & np.isfinite(ibi)&(ibi>max_ibi)
        dup=np.zeros(n,dtype=bool)
        if beat_time_col is not None and n>1:
            t=pd.to_numeric(p[beat_time_col],errors='coerce').to_numpy(float);d=np.abs(t[1:]-t[:-1]);dup[1:]=np.isfinite(t[1:])&np.isfinite(t[:-1])&(d<=duplicate_tolerance)
        abrupt=np.zeros(n,dtype=bool)
        if max_relative_change is not None and n>1:
            prev=np.r_[np.nan,ibi[:-1]]
            
            denom_ok=np.isfinite(prev)&(prev>0); rel=np.full(n,np.nan); rel[denom_ok]=np.abs(ibi[denom_ok]-prev[denom_ok])/prev[denom_ok]
            abrupt=has&np.isfinite(ibi)&denom_ok&(rel>max_relative_change)
        anyf=nonfinite|short|long|dup|abrupt
        reasons=[]
        for i in range(n):
            r=[]
            for flag,name in [(nonfinite[i],'nonfinite_ibi'),(short[i],'short_ibi'),(long[i],'long_ibi'),(dup[i],'duplicate_time'),(abrupt[i],'abrupt_change')]:
                if flag:r.append(name)
            reasons.append(';'.join(r))
        gvals={'segment_id':str(key)} if not groups else {c:p.iloc[0][c] for c in groups}
        bt=pd.DataFrame({**{k:[v]*n for k,v in gvals.items()},'beat_index':np.arange(1,n+1),'original_row':p['_orig'].to_numpy(int),'beat_time':p[beat_time_col].to_numpy(float) if beat_time_col else np.full(n,np.nan),'ibi':ibi,'has_interval':has,'nonfinite_ibi':nonfinite,'short_ibi':short,'long_ibi':long,'duplicate_time':dup,'abrupt_change':abrupt,'any_flag':anyf,'flag_reason':reasons})
        beats.append(bt);finite=has&np.isfinite(ibi)
        sums.append({**gvals,'n_beats':n,'n_intervals':int(has.sum()),'n_finite_intervals':int(finite.sum()),'n_flagged_beats':int(anyf.sum()),'prop_flagged_beats':float(anyf.mean()) if n else np.nan,'n_nonfinite_ibi':int(nonfinite.sum()),'n_short_ibi':int(short.sum()),'n_long_ibi':int(long.sum()),'n_duplicate_time':int(dup.sum()),'n_abrupt_change':int(abrupt.sum()),'median_ibi':float(np.median(ibi[finite])) if finite.any() else np.nan,'min_ibi_observed':float(np.min(ibi[finite])) if finite.any() else np.nan,'max_ibi_observed':float(np.max(ibi[finite])) if finite.any() else np.nan})
    return {'beats':pd.concat(beats,ignore_index=True),'summary':pd.DataFrame(sums),'parameters':{'ibi_col':ibi_col,'beat_time_col':beat_time_col,'group_cols':groups or None,'min_ibi':min_ibi,'max_ibi':max_ibi,'duplicate_tolerance':duplicate_tolerance,'max_relative_change':max_relative_change}}


def summarize_gazepoint_beat_corrections(correction, by=None):
    log=correction['correction_log'] if isinstance(correction,dict) and 'correction_log' in correction else correction
    if not isinstance(log,pd.DataFrame): raise TypeError('`correction` must be a gazepoint_beat_correction object or data frame.')
    req=['action','correction_note','flag_reason','original_ibi','corrected_ibi'];miss=[x for x in req if x not in log]
    if miss: raise ValueError(f'`correction` is missing required columns: {", ".join(miss)}')
    by=_cols(by)
    if len(log)==0:
        cols=by or ['segment_id'];return pd.DataFrame(columns=cols+['n_corrections','n_masked','n_local_median','n_group_median','n_unresolved'])
    if by:
        miss=[c for c in by if c not in log]
        if miss: raise ValueError(f'`by` contains columns not found in `correction`: {", ".join(miss)}')
        pieces=log.groupby(by[0] if len(by)==1 else by,sort=True,dropna=False)
    else:
        pieces=[('all',log)];by=['segment_id']
    rows=[]
    for key,p in pieces:
        if by==['segment_id'] and 'segment_id' not in p: g={'segment_id':'all'}
        else:
            vals=(key,) if len(by)==1 else key;g=dict(zip(by,vals))
        note=p['correction_note'].astype(str)
        rows.append({**g,'n_corrections':len(p),'n_masked':int((note=='masked_flagged_interval').sum()),'n_local_median':int((note=='replaced_with_local_median').sum()),'n_group_median':int((note=='replaced_with_group_median').sum()),'n_unresolved':int((note=='masked_no_reference_interval').sum())})
    return pd.DataFrame(rows)


def correct_gazepoint_beats(audit, action='mask', corrected_col='ibi_corrected', local_window=5, overwrite=False, **kwargs):
    if isinstance(audit,pd.DataFrame): audit=audit_gazepoint_beats(audit,**kwargs)
    if not isinstance(audit,dict) or 'beats' not in audit: raise TypeError('`audit` must be a gazepoint_beat_audit object or a data frame.')
    if action not in {'mask','local_median'}: raise ValueError('`action` must be mask or local_median.')
    if not isinstance(local_window,int) or local_window<1: raise ValueError('`local_window` must be a single positive integer.')
    beats=audit['beats'].copy()
    if corrected_col in beats and not overwrite: raise ValueError(f'Column `{corrected_col}` already exists.')
    beats[corrected_col]=beats['ibi'].astype(float)
    groups=_cols(audit.get('parameters',{}).get('group_cols'))
    if not groups and 'segment_id' in beats: groups=['segment_id']
    pieces=[('all',beats.index)] if not groups else list(beats.groupby(groups[0] if len(groups)==1 else groups,sort=True,dropna=False).groups.items())
    rows=[]
    for key,idx in pieces:
        idx=list(idx);piece=beats.loc[idx]
        good=(~piece.any_flag.astype(bool))&np.isfinite(piece.ibi.astype(float)); gm=float(np.median(piece.loc[good,'ibi'])) if good.any() else np.nan
        cand=piece.any_flag.astype(bool)&(piece[['nonfinite_ibi','short_ibi','long_ibi','duplicate_time','abrupt_change']].any(axis=1))
        for pos,j in enumerate(piece.index):
            if not bool(cand.loc[j]):continue
            new=np.nan;note='masked_flagged_interval'
            if action=='local_median':
                lo=max(0,pos-local_window);hi=min(len(piece),pos+local_window+1);loc=piece.iloc[lo:hi];lg=(~loc.any_flag.astype(bool))&np.isfinite(loc.ibi.astype(float))
                if lg.any():new=float(np.median(loc.loc[lg,'ibi']));note='replaced_with_local_median'
                elif np.isfinite(gm):new=gm;note='replaced_with_group_median'
                else:note='masked_no_reference_interval'
            beats.loc[j,corrected_col]=new
            g={c:piece.iloc[0][c] for c in groups} if groups else {'segment_id':'all'}
            rows.append({**g,'beat_index':int(piece.loc[j,'beat_index']),'original_row':int(piece.loc[j,'original_row']),'action':action,'correction_note':note,'flag_reason':piece.loc[j,'flag_reason'],'original_ibi':piece.loc[j,'ibi'],'corrected_ibi':new})
    log=pd.DataFrame(rows)
    if len(log)==0: log=pd.DataFrame(columns=(groups or ['segment_id'])+['beat_index','original_row','action','correction_note','flag_reason','original_ibi','corrected_ibi'])
    summary=summarize_gazepoint_beat_corrections(log,by=groups or None)
    return {'data':beats.reset_index(drop=True),'correction_log':log.reset_index(drop=True),'summary':summary,'parameters':{'action':action,'corrected_col':corrected_col,'local_window':local_window,'audit_parameters':audit.get('parameters')}}


def _prep_map(values, metrics, default, valid=None, name='values'):
    if values is None:return {m:default for m in metrics}
    if isinstance(values,dict): out={m:values.get(m,default) for m in metrics}
    elif isinstance(values,str) or np.isscalar(values): out={m:values for m in metrics}
    else:
        vals=list(values)
        if len(vals)==1:out={m:vals[0] for m in metrics}
        elif len(vals)==len(metrics):out=dict(zip(metrics,vals))
        else:raise ValueError(f'`{name}` must have length one or one value per metric.')
    if valid is not None and any(v not in valid for v in out.values()):raise ValueError(f'`{name}` must use {", ".join(valid)}.')
    return out


def compute_gazepoint_quality_index(data, metric_cols, directions=None, weights=None,index_col='quality_index',component_prefix='quality_component_',overwrite=False):
    dat=_df(data);metrics=_numeric(dat,metric_cols)
    dirs=_prep_map(directions,metrics,'higher',{'higher','lower'},'directions'); w=_prep_map(weights,metrics,1.0,None,'weights')
    if any((not np.isfinite(float(v)) or float(v)<0) for v in w.values()):raise ValueError('`weights` must be non-negative.')
    proposed=[index_col]+[component_prefix+m for m in metrics]
    existing=[c for c in proposed if c in dat]
    if existing and not overwrite:raise ValueError(f'Output column(s) already exist: {", ".join(existing)}.')
    comp=np.full((len(dat),len(metrics)),np.nan)
    for j,m in enumerate(metrics):
        x=pd.to_numeric(dat[m],errors='coerce').to_numpy(float);fin=np.isfinite(x)
        s=np.full(len(x),np.nan)
        if fin.any():
            lo=float(x[fin].min());hi=float(x[fin].max());s[fin]=0.5 if hi==lo else (x[fin]-lo)/(hi-lo)
            if dirs[m]=='lower':s[fin]=1-s[fin]
        comp[:,j]=s;dat[component_prefix+m]=s
    ww=np.array([float(w[m]) for m in metrics]);q=[]
    for row in comp:
        f=np.isfinite(row)&(ww>0);q.append(float(np.sum(row[f]*ww[f])/np.sum(ww[f])) if f.any() else np.nan)
    dat[index_col]=q;dat.attrs['quality_index_parameters']={'metric_cols':metrics,'directions':dirs,'weights':{m:float(w[m]) for m in metrics},'index_col':index_col,'component_cols':[component_prefix+m for m in metrics]};return dat


def audit_gazepoint_session_comparability(data, metric_cols, group_cols=None, method='both', z_threshold=2, iqr_multiplier=1.5):
    dat=_df(data);metrics=_numeric(dat,metric_cols);groups=_groups(dat,group_cols)
    if method not in {'both','z','iqr'}:raise ValueError('`method` must be both, z, or iqr.')
    if z_threshold<=0:raise ValueError('`z_threshold` must be positive.')
    if iqr_multiplier<0:raise ValueError('`iqr_multiplier` must be non-negative.')
    if groups: agg=dat.groupby(groups[0] if len(groups)==1 else groups,dropna=False,sort=True)[metrics].mean().reset_index()
    else: agg=dat[metrics].copy();agg.insert(0,'segment_id',np.arange(1,len(agg)+1));groups=['segment_id']
    flags=[]
    for m in metrics:
        x=agg[m].to_numpy(float);fin=np.isfinite(x);mu=np.nanmean(x) if fin.any() else np.nan;sd=np.std(x[fin],ddof=1) if fin.sum()>=2 else np.nan;med=np.nanmedian(x) if fin.any() else np.nan
        q1,q3=(np.quantile(x[fin],[.25,.75]) if fin.sum()>=2 else (np.nan,np.nan));iqr=q3-q1;low=q1-iqr_multiplier*iqr if np.isfinite(iqr) else np.nan;high=q3+iqr_multiplier*iqr if np.isfinite(iqr) else np.nan
        z=np.full(len(x),np.nan);z[fin]=0 if not np.isfinite(sd) or sd==0 else (x[fin]-mu)/sd
        zl=(method in {'z','both'})&np.isfinite(z)&(z<=-abs(z_threshold));zh=(method in {'z','both'})&np.isfinite(z)&(z>=abs(z_threshold));il=(method in {'iqr','both'})&fin&np.isfinite(low)&(x<low);ih=(method in {'iqr','both'})&fin&np.isfinite(high)&(x>high);missing=~fin;anyf=missing|zl|zh|il|ih
        for i in range(len(agg)):
            rr=[]
            for b,n in [(missing[i],'metric_missing'),(zl[i],'z_low'),(zh[i],'z_high'),(il[i],'iqr_low'),(ih[i],'iqr_high')]:
                if b:rr.append(n)
            flags.append({**agg.loc[i,groups].to_dict(),'metric':m,'value':x[i],'metric_mean':mu,'metric_sd':sd,'metric_median':med,'iqr_low':low,'iqr_high':high,'z_score':z[i],'metric_missing':bool(missing[i]),'z_low_flag':bool(zl[i]),'z_high_flag':bool(zh[i]),'iqr_low_flag':bool(il[i]),'iqr_high_flag':bool(ih[i]),'any_flag':bool(anyf[i]),'flag_reason':';'.join(rr)})
    fl=pd.DataFrame(flags)
    rows=[]
    for key,p in fl.groupby(groups[0] if len(groups)==1 else groups,sort=True,dropna=False):
        vals=(key,) if len(groups)==1 else key;g=dict(zip(groups,vals));rows.append({**g,'n_metrics':len(p),'n_missing_metrics':int(p.metric_missing.sum()),'n_flagged_metrics':int(p.any_flag.sum()),'prop_flagged_metrics':float(p.any_flag.mean())})
    return {'data':agg,'flags':fl,'summary':pd.DataFrame(rows),'parameters':{'metric_cols':metrics,'group_cols':groups,'method':method,'z_threshold':z_threshold,'iqr_multiplier':iqr_multiplier}}


def summarize_gazepoint_qc_overview(data, group_cols=None, quality_index_col=None, flag_cols=None, metric_cols=None):
    dat=_df(data);groups=_groups(dat,group_cols)
    if quality_index_col is not None:
        if quality_index_col not in dat:raise ValueError('`quality_index_col` was not found in `data`.')
        if not pd.api.types.is_numeric_dtype(dat[quality_index_col]):raise TypeError('`quality_index_col` must refer to a numeric column.')
    if flag_cols is None: flags=[c for c in dat if 'flag' in c.lower() and pd.api.types.is_bool_dtype(dat[c])]
    else:
        flags=_cols(flag_cols);miss=[c for c in flags if c not in dat]
        if miss:raise ValueError('`flag_cols` contains columns not found in `data`.')
        if any(not pd.api.types.is_bool_dtype(dat[c]) for c in flags):raise TypeError('All `flag_cols` must be logical.')
    metrics=[] if metric_cols is None else _numeric(dat,metric_cols)
    pieces=[('all',dat)] if not groups else list(dat.groupby(groups[0] if len(groups)==1 else groups,sort=True,dropna=False))
    rows=[]
    for key,p in pieces:
        g={'segment_id':str(key)} if not groups else {c:p.iloc[0][c] for c in groups};r={**g,'n_rows':len(p)}
        if flags:
            anyrow=np.zeros(len(p),dtype=bool)
            for f in flags:
                v=p[f].fillna(False).to_numpy(bool);r['n_'+f]=int(v.sum());anyrow|=v
            r['n_flagged_rows']=int(anyrow.sum());r['prop_flagged_rows']=float(anyrow.mean()) if len(p) else np.nan
        else:r.update(n_flagged_rows=np.nan,prop_flagged_rows=np.nan)
        if quality_index_col:
            q=pd.to_numeric(p[quality_index_col],errors='coerce').to_numpy(float);q=q[np.isfinite(q)];r.update(quality_index_mean=np.mean(q) if len(q) else np.nan,quality_index_min=np.min(q) if len(q) else np.nan,quality_index_max=np.max(q) if len(q) else np.nan)
        for m in metrics:
            x=pd.to_numeric(p[m],errors='coerce').to_numpy(float);x=x[np.isfinite(x)];r[m+'_mean']=np.mean(x) if len(x) else np.nan;r[m+'_min']=np.min(x) if len(x) else np.nan;r[m+'_max']=np.max(x) if len(x) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def _check_col(dat,c,label):
    if c is not None and c not in dat:raise ValueError(f'`{label}` was not found in `data`.')


def audit_gazepoint_experiment_design(data, participant_col='participant', trial_col=None, condition_col=None, session_col=None, expected_conditions=None, min_trials_per_condition=1):
    dat=_df(data);_check_col(dat,participant_col,'participant_col');_check_col(dat,trial_col,'trial_col');_check_col(dat,condition_col,'condition_col');_check_col(dat,session_col,'session_col')
    if expected_conditions is not None and any(not str(x) for x in expected_conditions):raise ValueError('`expected_conditions` must contain non-empty values.')
    participants=pd.unique(dat[participant_col].dropna()); conditions=pd.unique(dat[condition_col].dropna()) if condition_col else []
    part=dat.groupby(participant_col,dropna=False).size().rename('n_rows').reset_index()
    if trial_col: part=part.merge(dat.groupby(participant_col)[trial_col].nunique().rename('n_trials').reset_index(),on=participant_col)
    cond=pd.DataFrame()
    pc=pd.DataFrame();warnings=[]
    if condition_col:
        cond=dat.groupby(condition_col,dropna=False).size().rename('n_rows').reset_index()
        if trial_col: cond=cond.merge(dat.groupby(condition_col)[trial_col].nunique().rename('n_trials').reset_index(),on=condition_col)
        pc=dat.groupby([participant_col,condition_col],dropna=False).agg(n_rows=(participant_col,'size'),n_trials=(trial_col,'nunique') if trial_col else (participant_col,'size')).reset_index()
        exp=list(expected_conditions) if expected_conditions is not None else list(map(str,conditions))
        missing=[x for x in exp if x not in set(map(str,conditions))]
        if missing:warnings.append({'severity':'warning','issue':'missing_expected_conditions','message':'Expected conditions were not observed: '+', '.join(missing)})
        full=pd.MultiIndex.from_product([participants,exp],names=[participant_col,condition_col]).to_frame(index=False);grid=full.merge(pc,on=[participant_col,condition_col],how='left').fillna({'n_rows':0,'n_trials':0})
        if (grid.n_trials<min_trials_per_condition).any():warnings.append({'severity':'warning','issue':'low_participant_condition_cells','message':'Some participant-condition cells have fewer trials than required.'})
        pc=grid
    overview=pd.DataFrame([{'n_rows':len(dat),'n_participants':len(participants),'n_trials':dat[trial_col].nunique() if trial_col else np.nan,'n_conditions':len(conditions),'n_sessions':dat[session_col].nunique() if session_col else np.nan,'has_trial_column':trial_col is not None,'has_condition_column':condition_col is not None,'has_session_column':session_col is not None}])
    return {'overview':overview,'participant_summary':part,'condition_summary':cond,'participant_condition_counts':pc,'warnings':pd.DataFrame(warnings,columns=['severity','issue','message']),'settings':{'participant_col':participant_col,'trial_col':trial_col,'condition_col':condition_col,'session_col':session_col,'expected_conditions':expected_conditions,'min_trials_per_condition':min_trials_per_condition}}


def audit_gazepoint_event_coverage(data,event_col,participant_col=None,trial_col=None,unit_cols=None,expected_events=None):
    dat=_df(data);_check_col(dat,event_col,'event_col');
    if unit_cols is None: units=[c for c in [participant_col,trial_col] if c is not None]
    else: units=_cols(unit_cols)
    miss=[c for c in units if c not in dat]
    if miss:raise ValueError('`unit_cols` contains missing column(s): '+', '.join(miss))
    ev=dat[event_col].astype(str);expected=list(expected_events) if expected_events is not None else sorted(ev.dropna().unique())
    if units:
        keys=dat[units].drop_duplicates().reset_index(drop=True);rows=[]
        for _,u in keys.iterrows():
            mask=np.ones(len(dat),bool)
            for c in units:mask&=(dat[c].to_numpy()==u[c])
            obs=set(ev[mask]);r=u.to_dict();
            for e in expected:r[e]=e in obs
            r['n_expected_present']=sum(r[e] for e in expected);r['complete']=r['n_expected_present']==len(expected);rows.append(r)
        unit=pd.DataFrame(rows)
    else:
        obs=set(ev);unit=pd.DataFrame([{**{e:e in obs for e in expected},'n_expected_present':sum(e in obs for e in expected),'complete':all(e in obs for e in expected)}])
    es=[]
    for e in expected:
        n=int(unit[e].sum());es.append({'event':e,'n_units_present':n,'n_units':len(unit),'coverage_prop':n/len(unit) if len(unit) else np.nan})
    warnings=[];never=[r['event'] for r in es if r['n_units_present']==0];partial=[r['event'] for r in es if 0<r['n_units_present']<len(unit)]
    if never:warnings.append({'severity':'warning','issue':'events_never_observed','message':'Expected events were never observed: '+', '.join(never)})
    if partial:warnings.append({'severity':'warning','issue':'partial_event_coverage','message':'Some events have partial unit coverage.'})
    if not unit.complete.all():warnings.append({'severity':'warning','issue':'incomplete_event_units','message':'Some units do not contain all expected events.'})
    overview=pd.DataFrame([{'n_rows':len(dat),'n_units':len(unit),'n_expected_events':len(expected),'n_complete_units':int(unit.complete.sum()),'complete_unit_prop':float(unit.complete.mean()) if len(unit) else np.nan}])
    return {'overview':overview,'unit_summary':unit,'event_summary':pd.DataFrame(es),'warnings':pd.DataFrame(warnings,columns=['severity','issue','message']),'settings':{'event_col':event_col,'unit_cols':units,'expected_events':expected}}


def audit_gazepoint_condition_balance(data,participant_col,condition_col,trial_col=None,expected_conditions=None):
    dat=_df(data);_check_col(dat,participant_col,'participant_col');_check_col(dat,condition_col,'condition_col');_check_col(dat,trial_col,'trial_col')
    participants=list(pd.unique(dat[participant_col].dropna()));conditions=list(expected_conditions) if expected_conditions is not None else list(pd.unique(dat[condition_col].dropna()))
    counts=dat.groupby(condition_col).agg(n_rows=(participant_col,'size'),n_trials=(trial_col,'nunique') if trial_col else (participant_col,'size')).reset_index()
    pc=dat.groupby([participant_col,condition_col]).agg(n_rows=(participant_col,'size'),n_trials=(trial_col,'nunique') if trial_col else (participant_col,'size')).reset_index()
    grid=pd.MultiIndex.from_product([participants,conditions],names=[participant_col,condition_col]).to_frame(index=False).merge(pc,on=[participant_col,condition_col],how='left').fillna({'n_rows':0,'n_trials':0})
    cond_trials=[]
    for c in conditions:
        sub=dat[dat[condition_col].astype(str)==str(c)];cond_trials.append(sub[trial_col].nunique() if trial_col else len(sub))
    pos=[x for x in cond_trials if x>0];ratio=max(pos)/min(pos) if pos else np.nan;complete=bool((grid.n_trials>0).all())
    warnings=[]
    if (grid.n_trials==0).any():warnings.append({'severity':'warning','issue':'missing_participant_condition_cells','message':'Some participant-condition cells are missing.'})
    if np.isfinite(ratio) and ratio>1.5:warnings.append({'severity':'warning','issue':'condition_trial_imbalance','message':'Condition trial counts are imbalanced.'})
    if not complete:warnings.append({'severity':'warning','issue':'incomplete_participant_condition_grid','message':'Participant-condition grid is incomplete.'})
    overview=pd.DataFrame([{'n_rows':len(dat),'n_participants':len(participants),'n_conditions':len(conditions),'n_trials':dat[trial_col].nunique() if trial_col else len(dat),'trial_imbalance_ratio':ratio,'complete_participant_condition_grid':complete}])
    return {'overview':overview,'condition_summary':counts,'participant_condition_counts':grid,'warnings':pd.DataFrame(warnings,columns=['severity','issue','message']),'settings':{'participant_col':participant_col,'condition_col':condition_col,'trial_col':trial_col,'expected_conditions':conditions}}


def plot_gazepoint_design_coverage(audit,type='condition_counts'):
    import matplotlib.pyplot as plt
    if not isinstance(audit,dict):raise TypeError('`audit` must be a design/event audit object.')
    fig,ax=plt.subplots()
    if type=='condition_counts':
        d=audit.get('condition_summary',pd.DataFrame());ax.bar(d.iloc[:,0].astype(str),d['n_trials'] if 'n_trials' in d else d.get('n_rows',[]))
    elif type=='participant_trials':
        d=audit.get('participant_summary',pd.DataFrame());ax.bar(d.iloc[:,0].astype(str),d['n_trials'] if 'n_trials' in d else d.get('n_rows',[]))
    elif type=='event_coverage':
        d=audit.get('event_summary',pd.DataFrame());ax.bar(d['event'].astype(str),d['coverage_prop'])
    elif type=='warnings':
        d=audit.get('warnings',pd.DataFrame());counts=d['issue'].value_counts() if len(d) else pd.Series(dtype=int);ax.bar(counts.index.astype(str),counts.values)
    else:raise ValueError('Unsupported `type`.')
    fig.tight_layout();return fig
