from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ._helpers import as_list, ensure_df, mad, max_run, r_sd, require_cols


def _spike_count(x, spike_z):
    a=np.asarray(x,float); a=a[np.isfinite(a)]
    if len(a)<3: return 0
    dx=np.diff(a); scale=mad(dx,1.0)
    if not np.isfinite(scale) or scale==0: scale=r_sd(dx)
    if not np.isfinite(scale) or scale==0: return 0
    return int(np.sum(np.abs(dx-np.median(dx))/scale>spike_z))


def _extreme_count(x, extreme_z):
    a=np.asarray(x,float); a=a[np.isfinite(a)]
    if len(a)<3: return 0
    scale=mad(a,1.0)
    if not np.isfinite(scale) or scale==0: scale=r_sd(a)
    if not np.isfinite(scale) or scale==0: return 0
    return int(np.sum(np.abs(a-np.median(a))/scale>extreme_z))


def _quality_one(x,flatline_tolerance,long_missing_run_threshold,long_constant_run_threshold,spike_z,extreme_z):
    a=pd.to_numeric(pd.Series(x),errors='coerce').to_numpy(float); n=len(a); missing=~np.isfinite(a); finite=a[np.isfinite(a)]; nf=len(finite)
    adj=np.abs(np.diff(a)); finite_adj=np.isfinite(a[1:])&np.isfinite(a[:-1]); const=finite_adj&(adj<=flatline_tolerance)
    cpoint=np.zeros(n,bool)
    if n>1: cpoint[1:]|=const; cpoint[:-1]|=const
    lr=max_run(missing); lc=max_run(cpoint)
    return {
        'n_samples':n,'n_missing':int(missing.sum()),'prop_missing':float(missing.mean()) if n else np.nan,'n_finite':nf,'finite_prop':nf/n if n else np.nan,
        'mean':float(np.mean(finite)) if nf else np.nan,'sd':r_sd(finite),'median':float(np.median(finite)) if nf else np.nan,'mad':mad(finite,1.0),'min':float(np.min(finite)) if nf else np.nan,'max':float(np.max(finite)) if nf else np.nan,'range':float(np.ptp(finite)) if nf else np.nan,'iqr':float(np.percentile(finite,75)-np.percentile(finite,25)) if nf else np.nan,
        'flatline_prop':float(const.sum()/len(adj)) if len(adj) else np.nan,'long_missing_run':lr,'long_constant_run':lc,'contains_long_missing_run':lr>=long_missing_run_threshold,'contains_long_constant_run':lc>=long_constant_run_threshold,'spike_count':_spike_count(a,spike_z),'extreme_z_count':_extreme_count(a,extreme_z)
    }


def compute_gazepoint_signal_quality(data,signal_cols,group_cols=None,flatline_tolerance=0,long_missing_run_threshold=10,long_constant_run_threshold=10,spike_z=4,extreme_z=4):
    df=ensure_df(data); cols=as_list(signal_cols)
    if not cols: raise ValueError('`signal_cols` must contain at least one column name.')
    require_cols(df,cols,'signal_cols')
    bad=[c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
    if bad: raise TypeError('All `signal_cols` must be numeric. Non-numeric columns: '+', '.join(bad))
    groups=as_list(group_cols); require_cols(df,groups,'group_cols')
    if not np.isfinite(flatline_tolerance) or flatline_tolerance<0: raise ValueError('`flatline_tolerance` must be a single non-negative number.')
    if not np.isfinite(spike_z) or spike_z<=0: raise ValueError('`spike_z` must be a single positive number.')
    if not np.isfinite(extreme_z) or extreme_z<=0: raise ValueError('`extreme_z` must be a single positive number.')
    rows=[]; iterator=df.groupby(groups,sort=True,dropna=False) if groups else [('all',df)]
    for key,piece in iterator:
        key=key if isinstance(key,tuple) else (key,)
        gvals=dict(zip(groups,key,strict=True)) if groups else {'segment_id':'all'}
        for sig in cols: rows.append({**gvals,'signal':sig,**_quality_one(piece[sig],flatline_tolerance,long_missing_run_threshold,long_constant_run_threshold,spike_z,extreme_z)})
    out=pd.DataFrame(rows); out.attrs['_gpbiometricspy_class']='gazepoint_signal_quality'; return out

_DEFAULT_RULES={
'n_samples_review_below':10,'prop_missing_review_at_or_above':0.20,'prop_missing_exclude_at_or_above':0.50,'finite_prop_review_below':0.80,'finite_prop_exclude_below':0.50,'flatline_prop_review_at_or_above':0.20,'flatline_prop_exclude_at_or_above':0.50,'long_missing_run_review_at_or_above':10,'long_missing_run_exclude_at_or_above':50,'long_constant_run_review_at_or_above':10,'long_constant_run_exclude_at_or_above':50,'spike_count_review_at_or_above':5,'extreme_z_count_review_at_or_above':5}


def classify_gazepoint_signal_quality(quality,rules=None):
    if not isinstance(quality,pd.DataFrame): raise TypeError('`quality` must be a data frame.')
    rr=dict(_DEFAULT_RULES)
    if rules is not None:
        if not isinstance(rules,dict) or any(not k for k in rules): raise ValueError('`rules` must be a named list.')
        for k,v in rules.items():
            if v is None: rr.pop(k,None)
            else: rr[k]=v
    bad=[k for k,v in rr.items() if not isinstance(v,(int,float,np.integer,np.floating)) or not np.isfinite(v)]
    if bad: raise ValueError('All quality rules must be single finite numeric values. Invalid rules: '+', '.join(bad))
    out=quality.copy(); labels=[]; fails=[]; warns=[]
    checks=[('n_samples','n_samples_review_below','below','Low sample count'),('prop_missing','prop_missing_review_at_or_above','above','Missingness review threshold'),('prop_missing','prop_missing_exclude_at_or_above','above','Missingness exclude-candidate threshold'),('finite_prop','finite_prop_review_below','below','Finite-value review threshold'),('finite_prop','finite_prop_exclude_below','below','Finite-value exclude-candidate threshold'),('flatline_prop','flatline_prop_review_at_or_above','above','Flatline review threshold'),('flatline_prop','flatline_prop_exclude_at_or_above','above','Flatline exclude-candidate threshold'),('long_missing_run','long_missing_run_review_at_or_above','above','Long missing-run review threshold'),('long_missing_run','long_missing_run_exclude_at_or_above','above','Long missing-run exclude-candidate threshold'),('long_constant_run','long_constant_run_review_at_or_above','above','Long constant-run review threshold'),('long_constant_run','long_constant_run_exclude_at_or_above','above','Long constant-run exclude-candidate threshold'),('spike_count','spike_count_review_at_or_above','above','Spike-count review threshold'),('extreme_z_count','extreme_z_count_review_at_or_above','above','Extreme-value review threshold')]
    for _,row in out.iterrows():
        rev=[]; exc=[]; ww=[]
        for col,rn,op,label in checks:
            if rn not in rr: continue
            if col not in out.columns: ww.append('Metric unavailable: '+col); continue
            val=row[col]
            if pd.isna(val): ww.append('Metric missing: '+col); continue
            failed=val<rr[rn] if op=='below' else val>=rr[rn]
            if failed:
                txt=f"{label} [{col} {'below' if op=='below' else 'at_or_above'} {rr[rn]}]"
                (exc if 'exclude' in rn else rev).append(txt)
        labels.append('exclude_candidate' if exc else 'review' if rev else 'pass'); fails.append('; '.join(exc+rev)); warns.append('; '.join(dict.fromkeys(ww)))
    out['quality_label']=labels; out['failing_rules']=fails; out['quality_warnings']=warns; out.attrs['rules']=rr; out.attrs['_gpbiometricspy_class']='gazepoint_signal_quality_classification'; return out


def summarize_gazepoint_signal_quality(quality,by='signal'):
    if not isinstance(quality,pd.DataFrame): raise TypeError('`quality` must be a data frame.')
    by=as_list(by); require_cols(quality,by,'by'); rows=[]
    for key,p in quality.groupby(by,sort=True,dropna=False):
        key=key if isinstance(key,tuple) else (key,); row=dict(zip(by,key,strict=True));
        row.update(n_segments=len(p),n_samples_total=float(p['n_samples'].sum()),n_samples_median=float(p['n_samples'].median()),prop_missing_mean=float(p['prop_missing'].mean()),prop_missing_max=float(p['prop_missing'].max()),finite_prop_mean=float(p['finite_prop'].mean()),finite_prop_min=float(p['finite_prop'].min()),flatline_prop_mean=float(p['flatline_prop'].mean()),flatline_prop_max=float(p['flatline_prop'].max()),long_missing_run_max=float(p['long_missing_run'].max()),long_constant_run_max=float(p['long_constant_run'].max()),spike_count_total=float(p['spike_count'].sum()),extreme_z_count_total=float(p['extreme_z_count'].sum()))
        if 'quality_label' in p: row.update(pass_n=int((p.quality_label=='pass').sum()),review_n=int((p.quality_label=='review').sum()),exclude_candidate_n=int((p.quality_label=='exclude_candidate').sum()))
        rows.append(row)
    return pd.DataFrame(rows)


def plot_gazepoint_signal_quality(quality,metric='prop_missing',x=None,colour=None,facet=None):
    if not isinstance(quality,pd.DataFrame): raise TypeError('`quality` must be a data frame.')
    if metric not in quality.columns: raise ValueError('`metric` was not found in `quality`.')
    if x is None:
        x=next((c for c in ['participant','participant_id','trial','trial_id','segment','segment_id','session','signal'] if c in quality.columns),None)
    if x is None: raise ValueError('Could not infer `x`; please provide an x-axis column.')
    require_cols(quality,[x],"x");
    if colour is not None: require_cols(quality,[colour],"colour")
    if facet is None and 'signal' in quality and x!='signal': facet='signal'
    if facet is not None: require_cols(quality,[facet],"facet")
    fig,ax=plt.subplots(figsize=(7,4))
    if metric=='quality_label':
        tab=pd.crosstab(quality[x],quality[metric]); tab.plot(kind='bar',ax=ax); ax.set_ylabel('Number of segments')
    else:
        if colour is None: ax.scatter(quality[x].astype(str),quality[metric])
        else:
            for val,p in quality.groupby(colour,sort=False): ax.scatter(p[x].astype(str),p[metric],label=str(val))
            ax.legend(title=colour)
        ax.set_ylabel(metric)
    ax.set_xlabel(x); fig.tight_layout(); return fig
