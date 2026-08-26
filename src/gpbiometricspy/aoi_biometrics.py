from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ._helpers import as_list, r_sd

_DEFAULT_SIGNALS=["GSR_US","GSR_US_TONIC","GSR_US_PHASIC","GSR","HR","HRP","IBI","IBI_clean_ms","DIAL"]
_DEFAULT_GROUPS=["source_file","source_participant","participant","subject","MEDIA_ID","MEDIA_NAME","trial","trial_id","trial_global"]


def _group_ids(df,cols):
    if not cols: return pd.Series(["all"]*len(df),index=df.index)
    x=df[cols].astype(object).where(pd.notna(df[cols]),"<NA>").astype(str)
    return x.agg("||".join,axis=1)


def summarise_gazepoint_aoi_biometrics(data,aoi_col="AOI",signal_cols=None,group_cols=None,time_col=None,valid_aoi_values=None,drop_missing_aoi=True,min_rows=1):
    if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame.")
    dat=data.copy()
    if aoi_col not in dat.columns: raise ValueError("`aoi_col` was not found in `data`.")
    signals=[c for c in _DEFAULT_SIGNALS if c in dat.columns] if signal_cols is None else list(dict.fromkeys(as_list(signal_cols)))
    missing=[c for c in signals if c not in dat.columns]
    if missing: raise ValueError("`signal_cols` were not found in `data`: "+", ".join(missing))
    if not signals: raise ValueError("No biometric signal columns were supplied or detected.")
    groups=[c for c in _DEFAULT_GROUPS if c in dat.columns] if group_cols is None else as_list(group_cols)
    missing=[c for c in groups if c not in dat.columns]
    if missing: raise ValueError("`group_cols` were not found in `data`: "+", ".join(missing))
    if time_col is not None and time_col not in dat.columns: raise ValueError("`time_col` was not found in `data`.")
    if not isinstance(drop_missing_aoi,(bool,np.bool_)): raise TypeError("`drop_missing_aoi` must be TRUE or FALSE.")
    if not isinstance(min_rows,(int,float,np.number)) or not np.isfinite(min_rows) or min_rows<1: raise ValueError("`min_rows` must be a single positive finite number.")
    min_rows=int(min_rows)
    labels=dat[aoi_col].astype("string").str.strip(); labels=labels.where(labels.notna()&(labels.str.len()>0),pd.NA); dat[".aoi_label"]=labels
    if drop_missing_aoi: dat=dat[dat[".aoi_label"].notna()].copy()
    if valid_aoi_values is not None: dat=dat[dat[".aoi_label"].isin([str(x) for x in as_list(valid_aoi_values)])].copy()
    settings={"aoi_col":aoi_col,"signal_cols":signals,"group_cols":groups,"time_col":time_col,"valid_aoi_values":valid_aoi_values,"drop_missing_aoi":bool(drop_missing_aoi),"min_rows":min_rows}
    if dat.empty:
        ov=pd.DataFrame([{"input_rows":len(data),"retained_rows":0,"aoi_count":0,"signal_count":len(signals),"summary_rows":0,"group_count":0,"status":"fail_no_aoi_rows"}])
        return {"overview":ov,"summary":pd.DataFrame(),"signal_summary":pd.DataFrame(),"aoi_summary":pd.DataFrame(),"data":dat,"settings":settings,"class":["gazepoint_aoi_biometrics_summary","list"]}
    dat[".group_id"]=_group_ids(dat,groups)
    rows=[]
    for (gid,aoi),d in dat.groupby([".group_id",".aoi_label"],sort=False,dropna=False):
        for sig in signals:
            value=pd.to_numeric(d[sig],errors="coerce").to_numpy(float); finite=value[np.isfinite(value)]
            row={"aoi_label":str(aoi),"group_id":str(gid),"signal":sig,"n_rows":len(d),"n_finite":len(finite),"missing_rows":int((~np.isfinite(value)).sum()),"missing_prop":float((~np.isfinite(value)).mean()),
                 "mean_value":float(np.mean(finite)) if len(finite) else np.nan,"median_value":float(np.median(finite)) if len(finite) else np.nan,"sd_value":r_sd(finite) if len(finite)>1 else np.nan,
                 "min_value":float(np.min(finite)) if len(finite) else np.nan,"max_value":float(np.max(finite)) if len(finite) else np.nan,"first_value":float(finite[0]) if len(finite) else np.nan,"last_value":float(finite[-1]) if len(finite) else np.nan,
                 "delta_value":float(finite[-1]-finite[0]) if len(finite)>1 else np.nan,"auc_value":float(np.sum(finite)) if len(finite) else np.nan,"summary_status":"warn_low_rows" if len(d)<min_rows or len(finite)<min_rows else "usable"}
            for c in groups: row[c]=d.iloc[0][c]
            rows.append(row)
    summary=pd.DataFrame(rows)
    ss=[]
    for sig,d in summary.groupby("signal",sort=False):
        means=pd.to_numeric(d.mean_value,errors="coerce")
        ss.append({"signal":sig,"summary_rows":len(d),"usable_rows":int((d.summary_status=="usable").sum()),"aoi_count":d.aoi_label.nunique(),"mean_of_means":float(means.mean()),"median_of_means":float(means.median())})
    aa=[]
    for aoi,d in summary.groupby("aoi_label",sort=False): aa.append({"aoi_label":aoi,"summary_rows":len(d),"usable_rows":int((d.summary_status=="usable").sum()),"signal_count":d.signal.nunique(),"total_rows_contributing":int(d.n_rows.sum())})
    low=int((summary.summary_status=="warn_low_rows").sum()); status="fail_no_aoi_biometric_summaries" if summary.empty else ("warn_low_rows_in_some_summaries" if low else "aoi_biometrics_summarised")
    ov=pd.DataFrame([{"input_rows":len(data),"retained_rows":len(dat),"aoi_count":dat[".aoi_label"].nunique(),"signal_count":len(signals),"summary_rows":len(summary),"group_count":dat[".group_id"].nunique(),"usable_summary_rows":int((summary.summary_status=="usable").sum()),"low_row_summary_rows":low,"status":status}])
    settings["interpretation_notes"]=["AOI-linked biometrics summarise signals while AOI labels are active.","EDA/GSR and HR summaries should not be interpreted as emotional valence.","AOI dwell and biometric timing should be checked before confirmatory modelling."]
    return {"overview":ov,"summary":summary,"signal_summary":pd.DataFrame(ss),"aoi_summary":pd.DataFrame(aa),"data":dat,"settings":settings,"class":["gazepoint_aoi_biometrics_summary","list"]}


def _extract_summary(x):
    if isinstance(x,dict) and isinstance(x.get("summary"),pd.DataFrame): return x["summary"].copy()
    if isinstance(x,pd.DataFrame): return x.copy()
    raise TypeError("`x` must be an AOI-biometric summary object or a data frame.")


def _standardise(x):
    a=pd.to_numeric(pd.Series(x),errors="coerce").to_numpy(float); m=np.nanmean(a) if np.isfinite(a).any() else np.nan; sd=r_sd(a)
    if np.isfinite(sd) and sd>0: return (a-m)/sd
    return np.where(np.isnan(a),np.nan,0.0)


def prepare_gazepoint_aoi_biometrics_model_data(x,outcome_col="mean_value",predictor_cols=("aoi_label","signal"),factor_cols=("aoi_label","signal"),numeric_cols=None,group_cols=None,drop_missing_outcome=True,min_rows=None,standardise_outcome=False,standardise_within="signal"):
    if standardise_within not in {"signal","all"}: raise ValueError("`standardise_within` must be 'signal' or 'all'.")
    dat=_extract_summary(x)
    if outcome_col not in dat.columns: raise ValueError("`outcome_col` was not found in the summary data.")
    groups=[c for c in ["source_participant","participant","subject","source_file","MEDIA_ID","MEDIA_NAME"] if c in dat.columns] if group_cols is None else as_list(group_cols)
    predictors=as_list(predictor_cols); factors=as_list(factor_cols); nums=as_list(numeric_cols)
    if standardise_outcome and standardise_within=="signal" and "signal" not in dat.columns: raise ValueError('`standardise_within = "signal"` requires a `signal` column.')
    keep=[]
    for c in [*predictors,*factors,*nums,*groups,outcome_col,"n_rows","n_finite","summary_status"]+(["signal"] if standardise_outcome and standardise_within=="signal" else []):
        if c in dat.columns and c not in keep: keep.append(c)
    md=dat[keep].copy()
    if min_rows is not None:
        if not isinstance(min_rows,(int,float,np.number)) or not np.isfinite(min_rows) or min_rows<1: raise ValueError("`min_rows` must be NULL or a single positive finite number.")
        if "n_rows" in md.columns: md=md[pd.to_numeric(md.n_rows,errors="coerce")>=min_rows].copy()
    md[outcome_col]=pd.to_numeric(md[outcome_col],errors="coerce")
    if drop_missing_outcome: md=md[np.isfinite(md[outcome_col])].copy()
    for c in factors:
        if c in md.columns: md[c]=md[c].astype("category")
    for c in nums:
        if c in md.columns: md[c]=pd.to_numeric(md[c],errors="coerce")
    zcol=None
    if standardise_outcome:
        zcol=f"{outcome_col}_z"; md[zcol]=np.nan
        if standardise_within=="signal":
            for sig,idx in md.groupby("signal",dropna=False,observed=False).groups.items(): md.loc[idx,zcol]=_standardise(md.loc[idx,outcome_col])
        else: md[zcol]=_standardise(md[outcome_col])
    vars=[]
    for c in dict.fromkeys([outcome_col,*predictors,*factors,*groups]):
        if c not in md.columns: continue
        s=md[c]; isnum=pd.api.types.is_numeric_dtype(s); vars.append({"variable":c,"class":str(s.dtype),"n":len(s),"missing":int(s.isna().sum()),"unique_values":int(s.dropna().nunique()),"mean":float(pd.to_numeric(s,errors="coerce").mean()) if isnum else np.nan,"sd":r_sd(pd.to_numeric(s,errors="coerce")) if isnum else np.nan})
    fixed=[c for c in predictors if c in md.columns]; random=[c for c in groups if c in md.columns]; fixed_part=" + ".join(fixed) if fixed else "1"; random_part=" + ".join(f"(1 | {c})" for c in random); rhs=" + ".join([x for x in [fixed_part,random_part] if x])
    formulas=pd.DataFrame([{"outcome":outcome_col,"formula":f"{outcome_col} ~ {rhs}","z_outcome":zcol if standardise_outcome else np.nan,"z_formula":f"{zcol} ~ {rhs}" if standardise_outcome else np.nan}])
    ov=pd.DataFrame([{"input_rows":len(dat),"model_rows":len(md),"outcome_col":outcome_col,"predictor_count":len(fixed),"factor_count":sum(c in md.columns for c in factors),"group_count":len(random),"standardise_outcome":bool(standardise_outcome),"standardise_within":standardise_within if standardise_outcome else np.nan,"status":"fail_no_model_rows" if md.empty else "aoi_biometrics_model_data_prepared"}])
    return {"overview":ov,"model_data":md,"variable_summary":pd.DataFrame(vars),"model_formulas":formulas,"settings":{"outcome_col":outcome_col,"predictor_cols":predictors,"factor_cols":factors,"numeric_cols":nums,"group_cols":groups,"drop_missing_outcome":bool(drop_missing_outcome),"min_rows":min_rows,"standardise_outcome":bool(standardise_outcome),"standardise_within":standardise_within},"class":["gazepoint_aoi_biometrics_model_data","list"]}


def plot_gazepoint_aoi_biometrics(x,value_col="mean_value",aoi_col="aoi_label",signal_col="signal",group_col=None,plot_type="boxplot",title=None):
    if plot_type not in {"boxplot","point","line"}: raise ValueError("`plot_type` must be boxplot, point, or line.")
    if isinstance(x,dict) and isinstance(x.get("summary"),pd.DataFrame): dat=x["summary"].copy()
    elif isinstance(x,dict) and isinstance(x.get("model_data"),pd.DataFrame): dat=x["model_data"].copy()
    elif isinstance(x,pd.DataFrame): dat=x.copy()
    else: raise TypeError("`x` must be an AOI-biometric object or a data frame.")
    missing=[c for c in [value_col,aoi_col,signal_col] if c not in dat.columns]
    if missing: raise ValueError("Required plotting columns were not found: "+", ".join(missing))
    if group_col is not None and group_col not in dat.columns: raise ValueError("`group_col` was not found in the plotting data.")
    plot_data=dat.copy(); plot_data[".plot_value"]=pd.to_numeric(plot_data[value_col],errors="coerce"); plot_data=plot_data[np.isfinite(plot_data[".plot_value"])].copy()
    fig,ax=plt.subplots(); aois=list(pd.unique(plot_data[aoi_col].astype(str))); positions=np.arange(len(aois))
    if plot_type=="boxplot":
        vals=[plot_data.loc[plot_data[aoi_col].astype(str)==a,".plot_value"].to_numpy(float) for a in aois]; ax.boxplot(vals,positions=positions+1); ax.set_xticks(positions+1,aois)
    elif plot_type=="point":
        for i,a in enumerate(aois):
            y=plot_data.loc[plot_data[aoi_col].astype(str)==a,".plot_value"].to_numpy(float); ax.scatter(np.full(len(y),i),y); ax.set_xticks(positions,aois)
    else:
        groups=[("all",plot_data)] if group_col is None else list(plot_data.groupby(group_col,sort=False,dropna=False))
        for _,d in groups:
            means=[pd.to_numeric(d.loc[d[aoi_col].astype(str)==a,value_col],errors="coerce").mean() for a in aois]; ax.plot(positions,means,marker="o")
        ax.set_xticks(positions,aois)
    ax.set_title(title or "AOI-linked biometric summaries"); ax.set_xlabel(aoi_col); ax.set_ylabel(value_col)
    fig.plot_data=plot_data; fig.settings={"value_col":value_col,"aoi_col":aoi_col,"signal_col":signal_col,"group_col":group_col,"plot_type":plot_type}; fig.plot_type=plot_type
    return fig
