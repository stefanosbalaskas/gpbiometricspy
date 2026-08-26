from __future__ import annotations

import numpy as np
import pandas as pd

from .physiology_qc import estimate_gazepoint_respiration_from_ppg

_DEFAULT_DICTIONARY = {
    "time_s":["time_s","time","timestamp","TIME","TIME_TICK","MSTIMER","CNT"],
    "participant":["participant","participant_id","subject","subject_id","SUBJECT","P"],
    "trial":["trial","trial_id","TRIAL","stimulus","stimulus_id","screen"],
    "pupil_left":["pupil_left","left_pupil","LPD","LPMM","left_pupil_diameter"],
    "pupil_right":["pupil_right","right_pupil","RPD","RPMM","right_pupil_diameter"],
    "gaze_x":["gaze_x","x","BPOGX","FPOGX","GPOGX","CX"],
    "gaze_y":["gaze_y","y","BPOGY","FPOGY","GPOGY","CY"],
    "validity_left":["validity_left","left_validity","LPV","LVALID","left_valid"],
    "validity_right":["validity_right","right_validity","RPV","RVALID","right_valid"],
    "fixation_id":["fixation_id","fix_id","FPOGID","fixation"],
    "AOI":["AOI","aoi","aoi_name","AOI_NAME","area_of_interest"],
    "GSR":["GSR","GSR_US","EDA","eda","skin_conductance","conductance"],
    "PPG":["PPG","BVP","HRP","ppg","bvp","pulse"],
    "HR":["HR","heart_rate","heartrate","bpm"],
    "IBI":["IBI","RRI","RR","NN","ibi_ms","rr_ms"],
    "DIAL":["DIAL","dial","engagement","engagement_dial"],
    "TTL":["TTL","TTL0","TTL1","marker","event_marker","USER","USER_DATA"],
}


def _check_df(data, arg="data"):
    if not isinstance(data,pd.DataFrame): raise TypeError(f"`{arg}` must be a data frame.")
    if data.empty: raise ValueError(f"`{arg}` has no rows.")
    return data


def _unique_name(existing,target):
    if target not in existing: return target
    i=2
    while f"{target}_{i}" in existing: i+=1
    return f"{target}_{i}"


def standardize_gazepoint_column_names(data,dictionary=None,conflict="suffix",ignore_case=True):
    if conflict not in {"suffix","error","keep"}: raise ValueError("`conflict` must be 'suffix', 'error', or 'keep'.")
    dictionary=_DEFAULT_DICTIONARY if dictionary is None else dictionary
    if isinstance(data,dict) and all(isinstance(v,pd.DataFrame) for v in data.values()):
        return {k:standardize_gazepoint_column_names(v,dictionary,conflict,ignore_case) for k,v in data.items()}
    df=_check_df(data).copy(); original=list(df.columns); new=list(original)
    audit=pd.DataFrame({"original_name":original,"standardized_name":original,"role":[None]*len(original),"changed":[False]*len(original)})
    lookup=[str(x).lower() if ignore_case else str(x) for x in original]
    for role,aliases0 in dictionary.items():
        aliases=list(dict.fromkeys([role,*list(aliases0)])); aliases=[str(x).lower() if ignore_case else str(x) for x in aliases]
        hits=[i for i,x in enumerate(lookup) if x in aliases]
        for idx in hits:
            target=role
            if new[idx]==role:
                audit.loc[idx,"role"]=role; continue
            if target in new[:idx]+new[idx+1:]:
                if conflict=="error": raise ValueError(f"Column rename conflict for canonical name `{target}`.")
                if conflict=="keep": audit.loc[idx,"role"]=role; continue
                target=_unique_name(new[:idx]+new[idx+1:],target)
            new[idx]=target; audit.loc[idx,"standardized_name"]=target; audit.loc[idx,"role"]=role; audit.loc[idx,"changed"]=target!=original[idx]
    df.columns=new; df.attrs["gazepoint_column_standardization"]=audit
    return df


def standardize_gazepoint_columns(data,**kwargs):
    return standardize_gazepoint_column_names(data,**kwargs)


def validate_gazepoint_format(data,required_cols=None,optional_cols=None,expected_modalities=None,standardize=False,strict=False,**kwargs):
    df=_check_df(data).copy(); original=list(df.columns)
    if standardize: df=standardize_gazepoint_column_names(df)
    required=[] if required_cols is None else ([required_cols] if isinstance(required_cols,str) else list(required_cols))
    optional=[] if optional_cols is None else ([optional_cols] if isinstance(optional_cols,str) else list(optional_cols))
    missing_required=[c for c in required if c not in df.columns]; present_required=[c for c in required if c in df.columns]
    missing_optional=[c for c in optional if c not in df.columns]; present_optional=[c for c in optional if c in df.columns]
    # The R helper optionally attaches richer audits. The compatibility contract remains useful without them.
    out={"valid":len(missing_required)==0,"n_rows":len(df),"n_cols":len(df.columns),"original_columns":original,"current_columns":list(df.columns),
         "required":pd.DataFrame({"column":required,"present":[c in df.columns for c in required]}),
         "optional":pd.DataFrame({"column":optional,"present":[c in df.columns for c in optional]}),
         "missing_required":missing_required,"present_required":present_required,"missing_optional":missing_optional,"present_optional":present_optional,
         "schema":None,"schema_error":None,"audit":None,"warnings":[],"class":["gazepoint_format_validation","list"]}
    if strict and out["warnings"]: out["valid"]=False
    return out


def _time_seconds(x):
    arr=pd.to_numeric(pd.Series(x),errors="coerce").to_numpy(float); finite=arr[np.isfinite(arr)]
    if len(finite)<2:return arr
    d=np.diff(finite); d=d[np.isfinite(d)&(d>0)]
    return arr/1000 if len(d) and np.median(d)>5 else arr


def _guess_pupil_cols(df):
    hits=[]
    for c in df.columns:
        low=str(c).lower()
        if ("pupil" in low or low in {"lpd","rpd","lpmm","rpmm","left_pupil","right_pupil"}) and pd.api.types.is_numeric_dtype(df[c]): hits.append(c)
    return hits


def _interpolate_one(x,time=None,mask=None,max_gap_s=None,method="linear"):
    x=pd.to_numeric(pd.Series(x),errors="coerce").to_numpy(float)
    invalid=~np.isfinite(x) if mask is None else (pd.Series(mask).fillna(False).astype(bool).to_numpy()|~np.isfinite(x))
    if not invalid.any(): return x,np.zeros(len(x),bool)
    good=~invalid & np.isfinite(x)
    if good.sum()<2:return x,np.zeros(len(x),bool)
    eligible=np.zeros(len(x),bool); i=0; sec=_time_seconds(time) if time is not None else None
    while i<len(x):
        if not invalid[i]: i+=1; continue
        s=i
        while i+1<len(x) and invalid[i+1]:i+=1
        e=i; internal=s>0 and e<len(x)-1 and good[s-1] and good[e+1]
        if internal:
            ok=True
            if max_gap_s is not None and sec is not None and np.isfinite(sec[s]) and np.isfinite(sec[e]):
                d=np.diff(sec[np.isfinite(sec)]); d=d[d>0]; med=np.median(d) if len(d) else np.nan
                duration=max(0,float(sec[e]-sec[s]))+(float(med) if np.isfinite(med) else 0)
                ok=np.isfinite(duration) and duration<=max_gap_s
            if ok:eligible[s:e+1]=True
        i+=1
    out=x.copy()
    if eligible.any():
        idx=np.arange(len(x)); gi=idx[good]
        if method=="linear": interp=np.interp(idx,gi,x[good])
        else:
            interp=np.full(len(x),np.nan)
            for j in idx:
                left=gi[gi<=j]; interp[j]=x[left[-1]] if len(left) else np.nan
        out[eligible]=interp[eligible]
    return out,eligible


def interpolate_gazepoint_pupil_blinks(data,pupil_cols=None,time_col=None,blink_col=None,max_gap_s=None,method="linear",suffix="_interp"):
    if method not in {"linear","constant"}: raise ValueError("`method` must be 'linear' or 'constant'.")
    df=_check_df(data).copy(); pupils=_guess_pupil_cols(df) if pupil_cols is None else ([pupil_cols] if isinstance(pupil_cols,str) else list(pupil_cols))
    if not pupils:raise ValueError("No pupil columns were supplied or detected.")
    missing=[c for c in pupils if c not in df.columns]
    if missing:raise ValueError("Missing columns: "+", ".join(missing))
    if time_col is None:
        time_col=next((c for c in ["time_s","time","timestamp","event_time","MSTIMER","TIME","CNT"] if c in df.columns),None)
    if time_col is not None and time_col not in df.columns:raise ValueError("`time_col` was not found in `data`.")
    if blink_col is not None and blink_col not in df.columns:raise ValueError("`blink_col` was not found in `data`.")
    time=df[time_col] if time_col is not None else None; blink=df[blink_col] if blink_col is not None else None
    for c in pupils:
        value,flag=_interpolate_one(df[c],time,blink,max_gap_s,method); df[c+suffix]=value; df[c+"_was_interpolated"]=flag
    df.attrs["gazepoint_pupil_interpolation"]={"pupil_cols":pupils,"time_col":time_col,"blink_col":blink_col,"max_gap_s":max_gap_s,"method":method,"suffix":suffix}
    return df


def clean_gazepoint_pupil(data,pupil_cols=None,time_col=None,blink_col=None,max_gap_s=None,method="linear",suffix="_clean",prefer_existing=False,**kwargs):
    # R's short-name helper defaults to transparent gap interpolation.
    return interpolate_gazepoint_pupil_blinks(data,pupil_cols,time_col,blink_col,max_gap_s,method,suffix)


def respiration_from_ppg(data,**kwargs):
    return estimate_gazepoint_respiration_from_ppg(data,**kwargs)


def prepare_gazepoint_mixed_model_data(data,outcome_cols=None,participant_col=None,trial_col=None,condition_cols=None,factor_cols=None,numeric_cols=None,center_numeric=True,scale_numeric=False,drop_missing_outcomes=True,**kwargs):
    df=_check_df(data).copy()
    def L(x): return [] if x is None else ([x] if isinstance(x,str) else list(x))
    outcomes=L(outcome_cols); factors=list(dict.fromkeys(L(participant_col)+L(trial_col)+L(condition_cols)+L(factor_cols)))
    requested=outcomes+factors+L(numeric_cols); missing=[c for c in requested if c not in df.columns]
    if missing:raise ValueError("Missing columns: "+", ".join(missing))
    if drop_missing_outcomes and outcomes:
        keep=np.ones(len(df),bool)
        for c in outcomes:
            if pd.api.types.is_numeric_dtype(df[c]):keep&=np.isfinite(pd.to_numeric(df[c],errors="coerce"))
            else:keep&=df[c].notna().to_numpy()
        df=df.loc[keep].copy()
    for c in factors:df[c]=pd.Categorical(df[c])
    numerics=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in outcomes] if numeric_cols is None else L(numeric_cols)
    numerics=[c for c in numerics if c in df.columns]
    for c in numerics:
        x=pd.to_numeric(df[c],errors="coerce").to_numpy(float); mean=np.nanmean(x)
        if center_numeric:df[c+"_c"]=x-mean
        if scale_numeric:
            sd=np.nanstd(x,ddof=1); df[c+"_z"]=(x-mean)/sd if np.isfinite(sd) and sd>0 else np.nan
    df.attrs["gazepoint_mixed_model_data"]={"outcome_cols":outcomes,"participant_col":participant_col,"trial_col":trial_col,"condition_cols":L(condition_cols),"factor_cols":factors,"numeric_cols":numerics,"center_numeric":bool(center_numeric),"scale_numeric":bool(scale_numeric),"drop_missing_outcomes":bool(drop_missing_outcomes)}
    df.attrs["class"]=["gazepoint_mixed_model_data","data.frame"]
    return df
