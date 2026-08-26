from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ._helpers import as_list, ensure_df, group_indices, mad, require_cols


def _pupil_cols(df, pupil_cols=None):
    if pupil_cols is None:
        cols=[c for c in df.columns if "pupil" in str(c).lower() and pd.api.types.is_numeric_dtype(df[c])]
    else:
        cols=as_list(pupil_cols); require_cols(df, cols, "pupil columns")
    if not cols:
        raise ValueError("Could not identify numeric pupil columns.")
    bad=[c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
    if bad: raise TypeError("All pupil columns must be numeric.")
    return cols


def _extend_flags(flag: np.ndarray, groups, n: int):
    out=flag.copy()
    for _, idx in groups:
        local=flag[idx]
        loc=np.flatnonzero(local)
        for j in loc:
            lo=max(0,j-n); hi=min(len(idx),j+n+1)
            out[idx[lo:hi]]=True
    return out


def detect_gazepoint_blinks(data, pupil_cols=None, id_cols=None, min_pupil=0, max_pupil=np.inf,
                             change_threshold=None, extend_samples=0, mask=True,
                             flag_suffix="_blink_flag", clean_suffix="_blink_clean"):
    df=ensure_df(data).copy()
    cols=_pupil_cols(df,pupil_cols)
    ids=as_list(id_cols); require_cols(df, ids, "id_cols")
    if int(extend_samples)!=extend_samples or extend_samples<0: raise ValueError("`extend_samples` must be a non-negative integer.")
    extend_samples=int(extend_samples)
    if change_threshold is not None and (not np.isfinite(change_threshold) or change_threshold<0):
        raise ValueError("`change_threshold` must be a non-negative finite number.")
    groups=group_indices(df,ids)
    rows=[]
    for col in cols:
        x=pd.to_numeric(df[col],errors="coerce").to_numpy(float)
        flag=~np.isfinite(x)
        if min_pupil is not None: flag |= np.isfinite(x)&(x<=float(min_pupil))
        if max_pupil is not None and np.isfinite(max_pupil): flag |= np.isfinite(x)&(x>=float(max_pupil))
        if change_threshold is not None:
            cf=np.zeros(len(df),dtype=bool)
            for _,idx in groups:
                if len(idx)>1:
                    dx=np.r_[np.nan,np.abs(np.diff(x[idx]))]
                    cf[idx]=np.isfinite(dx)&(dx>=change_threshold)
            flag |= cf
        if extend_samples>0 and flag.any(): flag=_extend_flags(flag,groups,extend_samples)
        df[f"{col}{flag_suffix}"]=flag
        if mask:
            cleaned=x.copy(); cleaned[flag]=np.nan; df[f"{col}{clean_suffix}"]=cleaned
        rows.append({"pupil_col":col,"n_samples":len(x),"n_flagged":int(flag.sum()),"prop_flagged":float(flag.mean()) if len(x) else np.nan})
    summary=pd.DataFrame(rows)
    warnings=[]
    if (summary["prop_flagged"]>0.5).any(): warnings.append("More than 50% of samples were flagged in at least one pupil column.")
    return {"data":df,"summary":summary,"settings":{"pupil_cols":cols,"id_cols":ids,"min_pupil":min_pupil,"max_pupil":max_pupil,"change_threshold":change_threshold,"extend_samples":extend_samples,"mask":bool(mask),"flag_suffix":flag_suffix,"clean_suffix":clean_suffix},"warnings":warnings,"_gpbiometricspy_class":"gazepoint_blink_audit"}


def _moving_average(x, window, min_nonmissing):
    s=pd.Series(pd.to_numeric(pd.Series(x),errors="coerce"))
    return s.rolling(window,center=True,min_periods=min_nonmissing).mean().to_numpy()


def smooth_gazepoint_pupil(data, pupil_cols=None, id_cols=None, window=5, suffix="_smooth", min_nonmissing=1):
    df=ensure_df(data).copy(); cols=_pupil_cols(df,pupil_cols); ids=as_list(id_cols); require_cols(df,ids,"id_cols")
    if int(window)!=window or window<=0 or int(window)%2==0: raise ValueError("`window` must be an odd integer.")
    if int(min_nonmissing)!=min_nonmissing or min_nonmissing<=0: raise ValueError("`min_nonmissing` must be a positive integer.")
    window=int(window); min_nonmissing=int(min_nonmissing)
    if min_nonmissing>window: raise ValueError("`min_nonmissing` cannot be larger than `window`.")
    groups=group_indices(df,ids); rows=[]
    for col in cols:
        sm=np.full(len(df),np.nan)
        for _,idx in groups: sm[idx]=_moving_average(df.loc[idx,col].to_numpy(),window,min_nonmissing)
        outcol=f"{col}{suffix}"; df[outcol]=sm
        rows.append({"pupil_col":col,"output_col":outcol,"n_samples":len(sm),"n_smoothed_nonmissing":int(np.isfinite(sm).sum())})
    return {"data":df,"summary":pd.DataFrame(rows),"settings":{"pupil_cols":cols,"id_cols":ids,"window":window,"suffix":suffix,"min_nonmissing":min_nonmissing},"_gpbiometricspy_class":"gazepoint_pupil_smoothing"}


def plot_gazepoint_missingness(data, cols=None, time_col=None, id_col=None, max_points=5000):
    df=ensure_df(data)
    if cols is None: cols=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cols=as_list(cols); require_cols(df,cols,"cols")
    if time_col is not None: require_cols(df,[time_col],"time_col")
    if id_col is not None: require_cols(df,[id_col],"id_col")
    if int(max_points)!=max_points or max_points<=0: raise ValueError("`max_points` must be a positive integer.")
    rows=np.arange(len(df));
    if len(rows)>max_points: rows=np.unique(np.rint(np.linspace(0,len(df)-1,int(max_points))).astype(int))
    fig,axes=plt.subplots(len(cols),1,figsize=(8,max(2,1.5*len(cols))),squeeze=False)
    x=rows if time_col is None else pd.to_numeric(df.iloc[rows][time_col],errors="coerce").to_numpy()
    for ax,col in zip(axes[:,0],cols,strict=True):
        miss=df.iloc[rows][col].isna().astype(int).to_numpy()
        ax.scatter(x,np.zeros_like(x),c=miss,cmap="binary",marker="s",s=20)
        ax.set_yticks([0]); ax.set_yticklabels([str(col)])
    axes[-1,0].set_xlabel("Row index" if time_col is None else str(time_col)); fig.suptitle("Gazepoint signal missingness"); fig.tight_layout()
    return fig


def validate_gazepoint_metadata(data, required_cols=(), expected_cols=(), id_cols=None, time_col=None, unique_cols=None, allow_missing_ids=False):
    df=ensure_df(data)
    required=as_list(required_cols); expected=as_list(expected_cols); ids=as_list(id_cols); unique=as_list(unique_cols)
    problems=[]; warnings=[]
    mr=[c for c in required if c not in df.columns]; me=[c for c in expected if c not in df.columns]
    if mr: problems.append("Missing required columns: "+", ".join(mr))
    if me: warnings.append("Missing expected columns: "+", ".join(me))
    existing_ids=[c for c in ids if c in df.columns]; missing_ids=[c for c in ids if c not in df.columns]
    if missing_ids: problems.append("Missing ID columns: "+", ".join(missing_ids))
    if not allow_missing_ids:
        for col in existing_ids:
            s=df[col]
            if (s.isna() | s.astype("string").fillna("").eq("")).any(): problems.append(f"Missing values detected in ID column `{col}`.")
    if time_col is not None:
        if isinstance(time_col,(list,tuple)) and len(time_col)!=1: problems.append("`time_col` must contain exactly one column name.")
        else:
            tc=time_col[0] if isinstance(time_col,(list,tuple)) else time_col
            if tc not in df.columns: problems.append(f"Missing time column: {tc}")
            else:
                bad=0
                for _,idx in group_indices(df,existing_ids):
                    tx=pd.to_numeric(df.loc[idx,tc],errors="coerce").to_numpy(float)
                    if len(tx)>1 and np.any(np.diff(tx)<0): bad+=1
                if bad: problems.append(f"Time column `{tc}` is not monotonically increasing in {bad} group(s).")
    missing_unique=[c for c in unique if c not in df.columns]
    if missing_unique: problems.append("Missing unique-key columns: "+", ".join(missing_unique))
    elif unique and df.duplicated(unique).any(): problems.append(f"Duplicate rows detected for unique key: {', '.join(unique)}")
    summary=pd.DataFrame([{"n_rows":len(df),"n_columns":len(df.columns),"n_missing_required":len(mr),"n_missing_expected":len(me),"n_problems":len(problems),"n_warnings":len(warnings)}])
    return {"status":"pass" if not problems else "review","problems":problems,"warnings":warnings,"summary":summary,"settings":{"required_cols":required,"expected_cols":expected,"id_cols":ids,"time_col":time_col,"unique_cols":unique,"allow_missing_ids":bool(allow_missing_ids)},"_gpbiometricspy_class":"gazepoint_metadata_validation"}
