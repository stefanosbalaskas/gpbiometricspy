from __future__ import annotations

from collections.abc import Iterable
import math
import numpy as np
import pandas as pd


def ensure_df(data, name="data") -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"`{name}` must be a data frame.")
    if data.empty:
        raise ValueError(f"`{name}` has no rows.")
    return data


def as_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def guess_col(df: pd.DataFrame, candidates, label, required=True):
    lower = {str(c).lower(): c for c in df.columns}
    for cand in candidates:
        if str(cand).lower() in lower:
            return lower[str(cand).lower()]
    if required:
        raise ValueError(f"Could not identify {label} column. Supply it explicitly.")
    return None


def require_cols(df, cols, what="columns"):
    cols = as_list(cols)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{what} not found: {', '.join(map(str, missing))}")
    return cols


def group_indices(df: pd.DataFrame, group_cols=None):
    cols = as_list(group_cols)
    if not cols:
        return [("all", np.arange(len(df), dtype=int))]
    require_cols(df, cols, "grouping columns")
    out=[]
    for key, block in df.groupby(cols, sort=False, dropna=False):
        if not isinstance(key, tuple): key=(key,)
        label=" | ".join(map(str,key))
        out.append((label, block.index.to_numpy()))
    return out


def time_seconds(values):
    arr=pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    finite=arr[np.isfinite(arr)]
    if finite.size < 2:
        return arr
    d=np.diff(finite); d=d[np.isfinite(d)&(d>0)]
    if d.size and np.median(d)>5:
        return arr/1000.0
    return arr


def mad(x, scale=1.0):
    a=np.asarray(x,dtype=float); a=a[np.isfinite(a)]
    if not a.size: return np.nan
    return float(np.median(np.abs(a-np.median(a)))*scale)


def max_run(flag):
    a=np.asarray(flag,dtype=bool)
    if not a.size or not a.any(): return 0
    best=cur=0
    for v in a:
        cur=cur+1 if v else 0; best=max(best,cur)
    return int(best)


def r_sd(x):
    a=np.asarray(x,dtype=float); a=a[np.isfinite(a)]
    return float(np.std(a,ddof=1)) if a.size>1 else np.nan


def trapz(time, value):
    t=np.asarray(time,float); v=np.asarray(value,float)
    ok=np.isfinite(t)&np.isfinite(v)
    if ok.sum()<2: return np.nan
    order=np.argsort(t[ok]); t=t[ok][order]; v=v[ok][order]
    return float(np.sum(np.diff(t)*(v[:-1]+v[1:])/2))
