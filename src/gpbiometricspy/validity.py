from __future__ import annotations
import numpy as np, pandas as pd

_SIGNAL_CANDS=['GSR','GSR_US','GSR_OHMS','HR','IBI','ENGAGEMENT']

def summarise_gazepoint_biometric_validity(data,signal_cols=None,validity_cols=None,group_cols=None,active_min_unique=2):
    if not isinstance(data,pd.DataFrame):raise TypeError('`data` must be a data frame.')
    if active_min_unique<1:raise ValueError('`active_min_unique` must be a positive number.')
    signals=([signal_cols] if isinstance(signal_cols,str) else list(signal_cols)) if signal_cols is not None else [c for c in _SIGNAL_CANDS if c in data.columns]
    valid=([validity_cols] if isinstance(validity_cols,str) else list(validity_cols)) if validity_cols is not None else [c for c in data.columns if c.upper()=='HRV' or 'valid' in c.lower() or 'quality' in c.lower()]
    groups=[] if group_cols is None else ([group_cols] if isinstance(group_cols,str) else list(group_cols))
    for label,cols in [('signal_cols',signals),('validity_cols',valid),('group_cols',groups)]:
        miss=[c for c in cols if c not in data]
        if miss:raise ValueError(f'`{label}` contains columns not found in `data`: {", ".join(miss)}')
    rows=[]
    for c in signals:
        x=pd.to_numeric(data[c],errors='coerce').to_numpy(float);finite=x[np.isfinite(x)];nuniq=len(np.unique(finite));status='active_signal' if nuniq>=active_min_unique else ('constant_or_low_variability_signal' if len(finite) else 'no_finite_signal')
        rows.append({'column':c,'signal_type':'gsr_eda' if c.startswith('GSR') else ('heart_rate' if c=='HR' else ('ibi' if c=='IBI' else ('engagement_dial' if c=='ENGAGEMENT' else 'other'))),'n':len(x),'n_missing':int(np.isnan(x).sum()),'missing_rate':float(np.isnan(x).mean()) if len(x) else np.nan,'n_non_missing':int(np.isfinite(x).sum()),'n_finite':int(np.isfinite(x).sum()),'finite_rate':float(np.isfinite(x).mean()) if len(x) else np.nan,'n_unique_finite':nuniq,'mean':np.mean(finite) if len(finite) else np.nan,'sd':np.std(finite,ddof=1) if len(finite)>1 else np.nan,'min':np.min(finite) if len(finite) else np.nan,'max':np.max(finite) if len(finite) else np.nan,'status':status})
    sig=pd.DataFrame(rows)
    vr=[]
    for c in valid:
        x=pd.to_numeric(data[c],errors='coerce').to_numpy(float);finite=x[np.isfinite(x)];vr.append({'column':c,'standard_name':'HRV' if c.upper()=='HRV' else c,'n':len(x),'n_missing':int(np.isnan(x).sum()),'missing_rate':float(np.isnan(x).mean()) if len(x) else np.nan,'n_unique_finite':len(np.unique(finite)),'mean':np.mean(finite) if len(finite) else np.nan,'interpretation_note':'Treat as a validity/vendor flag; do not interpret as an HRV metric.' if c.upper()=='HRV' else 'Validity/quality flag.'})
    vf=pd.DataFrame(vr)
    gs=[]
    if groups:
        keys=data[groups].astype(str).agg(' | '.join,axis=1)
        for k in keys.drop_duplicates():
            d=data.loc[keys==k];active=0
            for c in signals:
                x=pd.to_numeric(d[c],errors='coerce').to_numpy(float);active+=len(np.unique(x[np.isfinite(x)]))>=active_min_unique
            gs.append({'group':k,'n_rows':len(d),'signal_column_count':len(signals),'active_signal_count':int(active),'status':'no_active_signals_in_group' if active==0 else ('some_signals_inactive_or_limited_in_group' if active<len(signals) else 'signals_available_in_group')})
    group_summary=pd.DataFrame(gs)
    active=int((sig['status']=='active_signal').sum()) if len(sig) else 0;inactive=len(sig)-active
    status='no_biometric_signal_columns_detected' if not signals else ('no_active_biometric_signals_detected' if active==0 else ('some_biometric_signals_inactive_or_limited' if inactive else 'biometric_signals_available'))
    overview=pd.DataFrame([{'n_rows':len(data),'n_columns':data.shape[1],'signal_column_count':len(signals),'active_signal_count':active,'inactive_signal_count':inactive,'validity_flag_column_count':len(valid),'group_column_count':len(groups),'status':status}])
    return {'overview':overview,'signals':sig,'validity_flags':vf,'group_summary':group_summary,'settings':{'signal_cols':signals,'validity_cols':valid,'group_cols':groups or None,'active_min_unique':int(active_min_unique),'notes':['GSR/EDA availability does not identify emotional valence.','Heart-rate availability requires baseline/task context for interpretation.','Raw HRV columns are treated as validity/vendor flags unless independently documented as HRV metrics.']}}
