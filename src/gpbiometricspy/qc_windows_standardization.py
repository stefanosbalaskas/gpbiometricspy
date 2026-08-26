from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd


def _coerce(data):
    if isinstance(data,pd.DataFrame): return data.copy()
    p=Path(data)
    first=p.read_text(errors='replace').splitlines()[0]
    counts={',':first.count(','),';':first.count(';'),'\t':first.count('\t')}
    return pd.read_csv(p,sep=max(counts,key=counts.get))


def standardise_gazepoint_zscore(dat,signal_col='SCR_Amplitude',group_col='source_participant',suffix='_Z',min_valid=2,overwrite=False):
    if not isinstance(dat,pd.DataFrame): raise TypeError('`dat` must be a data frame.')
    if signal_col not in dat: raise ValueError(f'Column `{signal_col}` was not found in `dat`.')
    if group_col not in dat: raise ValueError(f'Column `{group_col}` was not found in `dat`.')
    if not pd.api.types.is_numeric_dtype(dat[signal_col]): raise TypeError('`signal_col` must identify a numeric column.')
    out=dat.copy(); col=signal_col+suffix
    if col in out and not overwrite: raise ValueError(f'Output column `{col}` already exists. Use `overwrite = TRUE` to replace it.')
    out[col]=np.nan; pars=[]
    for g,idx in out.groupby(group_col,sort=False,dropna=False).groups.items():
        x=out.loc[idx,signal_col].to_numpy(float); finite=np.isfinite(x)
        status='standardized'; mu=sd=np.nan
        z=np.full(len(x),np.nan)
        if finite.sum()<min_valid: status='insufficient_finite_rows'
        else:
            mu=float(np.mean(x[finite]));sd=float(np.std(x[finite],ddof=1)) if finite.sum()>1 else np.nan
            if not np.isfinite(sd) or sd==0: status='zero_or_missing_sd'
            else:z[finite]=(x[finite]-mu)/sd
        out.loc[idx,col]=z;pars.append({'unit_id':str(g),'signal_col':signal_col,'output_col':col,'n_rows':len(x),'n_finite':int(finite.sum()),'mean':mu,'sd':sd,'status':status})
    out.attrs['standardization_method']='intra_individual_z_score';out.attrs['standardization_parameters']=pd.DataFrame(pars)
    out.attrs['interpretation']="Intra-individual z-scoring expresses each observation relative to the participant's own mean and standard deviation. It supports within-participant comparison but removes between-participant level and scale differences."
    return out

def standardize_gazepoint_zscore(*args,**kwargs): return standardise_gazepoint_zscore(*args,**kwargs)


def standardise_gazepoint_range_correction(dat,signal_col,group_col='source_participant',suffix='_Range_Corrected',min_valid=2,zero_range_action='NA',overwrite=False):
    if not isinstance(dat,pd.DataFrame): raise TypeError('`dat` must be a data frame.')
    if signal_col not in dat: raise ValueError(f'Column `{signal_col}` was not found in `dat`.')
    if group_col not in dat: raise ValueError(f'Column `{group_col}` was not found in `dat`.')
    if not pd.api.types.is_numeric_dtype(dat[signal_col]): raise TypeError('`signal_col` must identify a numeric column.')
    if zero_range_action not in {'NA','zero'}: raise ValueError('`zero_range_action` must be `NA` or `zero`.')
    out=dat.copy(); col=signal_col+suffix
    if col in out and not overwrite: raise ValueError(f'Output column `{col}` already exists. Use `overwrite = TRUE` to replace it.')
    out[col]=np.nan;rows=[]
    for g,idx in out.groupby(group_col,sort=False,dropna=False).groups.items():
        x=out.loc[idx,signal_col].to_numpy(float);finite=np.isfinite(x);vals=x[finite];mn=mx=rg=np.nan;status='range_corrected';corrected=np.full(len(x),np.nan)
        if len(vals)<min_valid:status='insufficient_finite_rows'
        else:
            mn=float(vals.min());mx=float(vals.max());rg=mx-mn
            if not np.isfinite(rg) or rg==0:
                status='zero_or_missing_range'
                if zero_range_action=='zero':corrected[finite]=0
            else:corrected[finite]=(x[finite]-mn)/rg
        out.loc[idx,col]=corrected;rows.append({'unit_id':str(g),'signal_col':signal_col,'output_col':col,'n_rows':len(x),'n_finite':len(vals),'min_val':mn,'max_val':mx,'range_val':rg,'status':status})
    pars=pd.DataFrame(rows);complete=int((pars.status=='range_corrected').sum());status='range_correction_complete' if complete==len(pars) else ('range_correction_partial' if complete else 'range_correction_failed')
    out.attrs['range_correction_summary']=pd.DataFrame([{'input_rows':len(dat),'group_count':len(pars),'signal_col':signal_col,'output_col':col,'corrected_groups':complete,'problem_groups':len(pars)-complete,'status':status,'interpretation':'Range correction expresses each value as a proportion of the observed within-unit signal range. It reduces between-unit range differences but depends strongly on the observed minimum and maximum.'}]);out.attrs['range_correction_parameters']=pars;out.attrs['range_correction_settings']={'signal_col':signal_col,'group_col':group_col,'suffix':suffix,'min_valid':min_valid,'zero_range_action':zero_range_action,'overwrite':overwrite};return out

def standardize_gazepoint_range_correction(*args,**kwargs):return standardise_gazepoint_range_correction(*args,**kwargs)


def _audit(data,signal,value_column,validity_column,min_value,max_value,jump_threshold):
    dat=_coerce(data);n=len(dat)
    if value_column is None or value_column not in dat:
        return pd.DataFrame([{'signal':signal,'issue':'value_column_missing','value_column':value_column,'validity_column':validity_column,'n_rows':n,'missing_rows':np.nan,'missing_pct':np.nan,'zero_rows':np.nan,'zero_pct':np.nan,'nonzero_rows':np.nan,'valid_rows':np.nan,'invalid_rows':np.nan,'low_rows':np.nan,'high_rows':np.nan,'large_jump_rows':np.nan,'flatline':np.nan,'usable_rows':0,'usable_pct':0.,'min_value':np.nan,'max_value':np.nan,'mean_value':np.nan}])
    x=pd.to_numeric(dat[value_column],errors='coerce').to_numpy(float);missing=np.isnan(x);zero=np.isfinite(x)&(x==0);valid=np.isfinite(x)
    vc=validity_column if validity_column in dat.columns else None
    if vc is not None:
        v=pd.to_numeric(dat[vc],errors='coerce').to_numpy(float);valid&=np.isfinite(v)&(v>0)
    low=np.isfinite(x)&(x<min_value);high=np.isfinite(x)&(x>max_value);usable=valid&~low&~high;u=x[usable]
    jumps=np.nan if jump_threshold is None or len(u)<=1 else int((np.abs(np.diff(u))>jump_threshold).sum())
    return pd.DataFrame([{'signal':signal,'issue':None,'value_column':value_column,'validity_column':vc,'n_rows':len(x),'missing_rows':int(missing.sum()),'missing_pct':100*missing.mean(),'zero_rows':int(zero.sum()),'zero_pct':100*zero.mean(),'nonzero_rows':int((np.isfinite(x)&(x!=0)).sum()),'valid_rows':int(valid.sum()),'invalid_rows':int(len(x)-valid.sum()),'low_rows':int(low.sum()),'high_rows':int(high.sum()),'large_jump_rows':jumps,'flatline':bool(len(u)>1 and len(np.unique(u))==1),'usable_rows':len(u),'usable_pct':100*len(u)/len(x) if len(x) else np.nan,'min_value':u.min() if len(u) else np.nan,'max_value':u.max() if len(u) else np.nan,'mean_value':u.mean() if len(u) else np.nan}])

def audit_gazepoint_gsr_quality(data,value_column=None,validity_column='GSRV',min_value=0,max_value=100,jump_threshold=None):
    dat=_coerce(data);value_column=value_column or ('GSR_US' if 'GSR_US' in dat else ('GSR' if 'GSR' in dat else None));return _audit(dat,'gsr_eda',value_column,validity_column,min_value,max_value,jump_threshold)
def audit_gazepoint_hr_quality(data,value_column='HR',validity_column='HRV',min_value=30,max_value=220,jump_threshold=25):return _audit(data,'heart_rate',value_column,validity_column,min_value,max_value,jump_threshold)
def audit_gazepoint_engagement_dial(data,value_column='DIAL',validity_column='DIALV',min_value=0,max_value=1,jump_threshold=None):return _audit(data,'engagement_dial',value_column,validity_column,min_value,max_value,jump_threshold)


def _window(data,signal,group_columns,value_column,validity_column=None,exclude_zero=True):
    dat=_coerce(data);groups=[] if group_columns is None else ([group_columns] if isinstance(group_columns,str) else list(group_columns))
    if value_column is None:raise ValueError('`value_column` could not be determined.')
    if value_column not in dat:raise ValueError(f'`value_column` was not found in `data`: {value_column}')
    miss=[g for g in groups if g not in dat]
    if miss:raise ValueError(f'`group_columns` were not found in `data`: {", ".join(miss)}')
    if groups: keys=dat[groups].astype(str).agg('||'.join,axis=1); uniq=keys.drop_duplicates().tolist()
    else: keys=pd.Series(['all']*len(dat));uniq=['all']
    rows=[]
    for key in uniq:
        mask=(keys==key).to_numpy();x=pd.to_numeric(dat.loc[mask,value_column],errors='coerce').to_numpy(float);valid=np.isfinite(x)
        if exclude_zero:valid&=x!=0
        vp=validity_column is not None and validity_column in dat
        if vp:
            v=pd.to_numeric(dat.loc[mask,validity_column],errors='coerce').to_numpy(float);valid&=np.isfinite(v)&(v>0)
        u=x[valid];row=dat.loc[mask,groups].iloc[0].to_dict() if groups else {'window':'all'}
        row.update({'signal':signal,'value_column':value_column,'validity_column':validity_column if vp else None,'n_rows':len(x),'usable_rows':len(u),'usable_pct':100*len(u)/len(x) if len(x) else np.nan,'missing_rows':int(np.isnan(x).sum()),'zero_rows':int((np.isfinite(x)&(x==0)).sum()),'mean_value':u.mean() if len(u) else np.nan,'median_value':np.median(u) if len(u) else np.nan,'sd_value':np.std(u,ddof=1) if len(u)>1 else np.nan,'min_value':u.min() if len(u) else np.nan,'max_value':u.max() if len(u) else np.nan,'first_value':u[0] if len(u) else np.nan,'last_value':u[-1] if len(u) else np.nan,'change_value':u[-1]-u[0] if len(u) else np.nan});rows.append(row)
    return pd.DataFrame(rows)

def summarise_gazepoint_gsr_windows(data,group_columns=None,value_column=None,validity_column='GSRV',exclude_zero=True):
    dat=_coerce(data);value_column=value_column or ('GSR_US' if 'GSR_US' in dat else ('GSR' if 'GSR' in dat else None));return _window(dat,'gsr_eda',group_columns,value_column,validity_column,exclude_zero)
def summarise_gazepoint_hr_windows(data,group_columns=None,value_column='HR',validity_column='HRV',exclude_zero=True):return _window(data,'heart_rate',group_columns,value_column,validity_column,exclude_zero)
def summarise_gazepoint_engagement_windows(data,group_columns=None,value_column='DIAL',validity_column='DIALV',exclude_zero=False):return _window(data,'engagement_dial',group_columns,value_column,validity_column,exclude_zero)
def summarise_gazepoint_multimodal_windows(data,group_columns=None,exclude_zero=True):
    g=summarise_gazepoint_gsr_windows(data,group_columns,exclude_zero=exclude_zero);h=summarise_gazepoint_hr_windows(data,group_columns,exclude_zero=exclude_zero);d=summarise_gazepoint_engagement_windows(data,group_columns,exclude_zero=False);groups=[] if group_columns is None else ([group_columns] if isinstance(group_columns,str) else list(group_columns));keys=groups or ['window']
    def pref(x,p):return x.rename(columns={c:f'{p}_{c}' for c in x.columns if c not in keys})
    return pref(g,'gsr').merge(pref(h,'hr'),on=keys,how='outer').merge(pref(d,'dial'),on=keys,how='outer')
