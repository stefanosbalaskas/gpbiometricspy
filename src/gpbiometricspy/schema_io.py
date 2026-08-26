from __future__ import annotations

from io import StringIO
from pathlib import Path
import re

import numpy as np
import pandas as pd


_CANONICAL_MAP = {
    "CNT": ["cnt","counter","sample","sample_index","sample_number","sample_no","sample_id"],
    "TIME": ["time","timestamp","time_s","time_sec","timestamp_s","timestamp_sec","recording_time","recording_time_s"],
    "TIME_MS": ["time_ms","timestamp_ms","recording_time_ms"],
    "TIME_TICK": ["time_tick","time_ticks","tick","ticks"],
    "TRIAL_TIME": ["trial_time","trial_time_s","time_in_trial"],
    "MEDIA_TIME": ["media_time","stimulus_time","stimulus_time_s"],
    "USER": ["user","participant","participant_id","subject","subject_id","id"],
    "USER_FILE": ["user_file","file","filename","source_file"],
    "MEDIA_ID": ["media_id","stimulus_id"],
    "MEDIA_NAME": ["media_name","stimulus","stimulus_name","image","video"],
    "TRIAL": ["trial","trial_id","trial_number"],
    "CONDITION": ["condition","group","experimental_condition"],
    "GSR": ["gsr","eda","electrodermal_activity","skin_conductance","skin_response"],
    "GSR_US": ["gsr_us","gsr_u_s","gsr_microsiemens","gsr_micro_siemens","eda_us","eda_u_s","eda_microsiemens","conductance","conductance_us","skin_conductance_us"],
    "GSR_OHMS": ["gsr_ohm","gsr_ohms","eda_ohm","eda_ohms","resistance","resistance_ohm","resistance_ohms","skin_resistance","skin_resistance_ohms"],
    "HR": ["hr","heart_rate","heartrate","bpm","pulse","pulse_rate"],
    "HRV": ["hrv","hr_valid","hr_validity","heart_rate_valid","heart_rate_validity"],
    "IBI": ["ibi","rr","rr_interval","rr_intervals","interbeat_interval","inter_beat_interval","interbeat_interval_ms","rr_ms"],
    "ENGAGEMENT": ["engagement","engagement_dial","dial","dial_value","engagement_value","rotary","self_reported_engagement"],
    "TTL": ["ttl","ttl_value","ttl_signal","ttl_marker","event_marker","marker","trigger","digital_marker"],
    "EVENT": ["event","event_name","event_label"],
}
_REVERSE = {alias: target for target, aliases in _CANONICAL_MAP.items() for alias in aliases}
_SCHEMA_GROUPS = {
    "CNT":"timing","SAMPLE":"timing","SAMPLE_INDEX":"timing","TIME":"timing","TIME_S":"timing","TIMESTAMP_S":"timing",
    "TIME_MS":"timing","TIMESTAMP_MS":"timing","TIME_TICK":"timing","TIME_TICKS":"timing","TICK":"timing","TICKS":"timing",
    "TRIAL_TIME":"timing","MEDIA_TIME":"timing","STIMULUS_TIME":"timing","USER":"identifier","USER_FILE":"identifier",
    "MEDIA_ID":"stimulus","MEDIA_NAME":"stimulus","TRIAL":"trial","CONDITION":"condition","GSR":"gsr_eda","GSR_US":"gsr_eda",
    "GSR_OHMS":"gsr_eda","HR":"heart_rate","HRV":"heart_rate_validity_flag","IBI":"ibi","ENGAGEMENT":"engagement_dial",
    "TTL":"ttl_marker","TTLV":"ttl_validity_flag","EVENT":"event",
}


def _clean_name(x):
    x = str(x).strip().replace("µ", "u")
    x = re.sub(r"[^A-Za-z0-9]+", "_", x)
    x = re.sub(r"_+", "_", x).strip("_")
    return x.lower()


def _canonical(cleaned):
    if re.fullmatch(r"ttl[0-9]+", cleaned):
        return "TTL"
    if cleaned in {"ttlv","ttl_valid","ttl_validity"}:
        return "TTLV"
    return _REVERSE.get(cleaned, cleaned.upper())


def _make_unique(names):
    result=[]; counts={}
    for name in names:
        if name not in result:
            result.append(name); counts[name]=0; continue
        counts[name]=counts.get(name,0)+1
        candidate=f"{name}_{counts[name]}"
        while candidate in result:
            counts[name]+=1; candidate=f"{name}_{counts[name]}"
        result.append(candidate)
    return result


def standardise_gazepoint_biometric_names(data, style="canonical", rename=True):
    if style not in {"canonical","snake"}:
        raise ValueError("`style` must be 'canonical' or 'snake'.")
    is_df=isinstance(data,pd.DataFrame)
    if is_df:
        original=[str(c) for c in data.columns]
    elif isinstance(data,(list,tuple,np.ndarray,pd.Index)) and all(isinstance(x,str) for x in data):
        original=list(data)
    else:
        raise TypeError("`data` must be a data frame or a character vector of column names.")
    canonical=[_canonical(_clean_name(x)) for x in original]
    standard=[x.lower() for x in canonical] if style=="snake" else canonical
    standard=_make_unique(standard)
    if not is_df:
        return standard
    mapping=pd.DataFrame({"original_name":original,"standard_name":standard,"changed":[a!=b for a,b in zip(original,standard)]})
    if not rename:
        return mapping
    out=data.copy(); out.columns=standard
    return out


def _empty_time_columns():
    return pd.DataFrame(columns=["column","standard_name","role","unit_hint","confidence","reason"])


def detect_gazepoint_time_columns(data):
    if isinstance(data,pd.DataFrame): names=[str(c) for c in data.columns]
    elif isinstance(data,(list,tuple,np.ndarray,pd.Index)) and all(isinstance(x,str) for x in data): names=list(data)
    else: raise TypeError("`data` must be a data frame or a character vector of column names.")
    if not names: return _empty_time_columns()
    canon=[_canonical(_clean_name(x)) for x in names]
    rows=[]
    for original, standard in zip(names,canon):
        if standard in {"CNT","SAMPLE","SAMPLE_INDEX"}:
            rows.append((original,standard,"sample_counter","samples",1.0,"Recognised sample counter column."))
        elif standard in {"TIME","TIME_S","TIMESTAMP_S"}:
            rows.append((original,standard,"timestamp","seconds",.95,"Recognised time column with seconds-like name."))
        elif standard in {"TIME_MS","TIMESTAMP_MS"}:
            rows.append((original,standard,"timestamp","milliseconds",.95,"Recognised time column with milliseconds-like name."))
        elif standard in {"TIME_TICK","TIME_TICKS","TICK","TICKS"}:
            rows.append((original,standard,"timestamp","ticks",.90,"Recognised tick-style timing column."))
        elif standard in {"TRIAL_TIME","MEDIA_TIME","STIMULUS_TIME"}:
            rows.append((original,standard,"trial_or_media_time","unknown",.80,"Recognised trial/media-relative timing column."))
        elif re.search(r"(^|_)time($|_)",_clean_name(original)):
            rows.append((original,standard,"candidate_time","unknown",.60,"Column name contains a generic time token."))
    if not rows: return _empty_time_columns()
    out=pd.DataFrame(rows,columns=["column","standard_name","role","unit_hint","confidence","reason"])
    return out.sort_values(["confidence","column"],ascending=[False,True],kind="stable").reset_index(drop=True)


def _empty_interval():
    return pd.DataFrame([{"unit":np.nan,"n_intervals":0,"n_valid_intervals":0,"n_zero_or_negative_intervals":0,
                          "min_interval":np.nan,"median_interval":np.nan,"mean_interval":np.nan,"max_interval":np.nan}])


def detect_gazepoint_biometric_timebase(data,time_col=None,counter_col=None):
    if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame.")
    tc=detect_gazepoint_time_columns(data); warnings=[]
    if time_col is not None:
        if time_col not in data.columns: raise ValueError("`time_col` was not found in `data`.")
        primary=time_col
    else:
        primary=None
        usable=tc[[c in data.columns and pd.api.types.is_numeric_dtype(data[c]) and data[c].notna().sum()>=2 for c in tc.column]] if len(tc) else tc
        for role in ["timestamp","trial_or_media_time","sample_counter","candidate_time"]:
            z=usable[usable.role==role]
            if len(z): primary=z.loc[z.confidence.idxmax(),"column"]; break
    if counter_col is not None:
        if counter_col not in data.columns: raise ValueError("`counter_col` was not found in `data`.")
        counter=counter_col
    else:
        z=tc[tc.role=="sample_counter"]
        counter=next((c for c in z.column if c in data.columns and pd.api.types.is_numeric_dtype(data[c])),None)
    if primary is None:
        warnings.append("No usable numeric time or counter column detected.")
        overview=pd.DataFrame([{"n_rows":len(data),"primary_time_column":np.nan,"primary_time_role":np.nan,"unit":np.nan,
                                "median_interval":np.nan,"sampling_rate_hz":np.nan,"counter_column":counter if counter else np.nan,
                                "n_valid_intervals":0,"status":"no_timebase_detected"}])
        return {"overview":overview,"time_columns":tc,"interval_summary":_empty_interval(),"warnings":warnings}
    row=tc[tc.column==primary]
    role=row.iloc[0].role if len(row) else "unknown"
    hint=row.iloc[0].unit_hint if len(row) else "unknown"
    vals=pd.to_numeric(data[primary],errors="coerce").to_numpy(float)
    if hint not in {"unknown","samples"}: unit=hint
    elif hint=="samples": unit="samples"
    else:
        finite=vals[np.isfinite(vals)]; diffs=np.diff(np.sort(np.unique(finite))) if len(finite)>=2 else np.array([]); diffs=diffs[np.isfinite(diffs)&(diffs>0)]
        med=np.median(diffs) if len(diffs) else np.nan
        unit="seconds" if np.isfinite(med) and 0<med<1 else ("milliseconds" if np.isfinite(med) and 1<=med<=1000 else "unknown")
    finite=vals[np.isfinite(vals)]
    if len(finite)>=2:
        diffs=np.diff(finite); valid=diffs[np.isfinite(diffs)&(diffs>0)]
    else: diffs=np.array([]); valid=np.array([])
    if len(valid):
        interval=pd.DataFrame([{"unit":unit,"n_intervals":len(diffs),"n_valid_intervals":len(valid),"n_zero_or_negative_intervals":int(np.sum(np.isfinite(diffs)&(diffs<=0))),
                                "min_interval":float(np.min(valid)),"median_interval":float(np.median(valid)),"mean_interval":float(np.mean(valid)),"max_interval":float(np.max(valid))}])
    else: interval=_empty_interval()
    med=float(interval.iloc[0].median_interval) if len(valid) else np.nan
    rate=1/med if unit=="seconds" and np.isfinite(med) and med>0 else (1000/med if unit=="milliseconds" and np.isfinite(med) and med>0 else np.nan)
    if not np.isfinite(rate): warnings.append("Sampling rate could not be estimated from the selected timebase.")
    overview=pd.DataFrame([{"n_rows":len(data),"primary_time_column":primary,"primary_time_role":role,"unit":unit,"median_interval":med,
                            "sampling_rate_hz":rate,"counter_column":counter if counter else np.nan,"n_valid_intervals":int(interval.iloc[0].n_valid_intervals),
                            "status":"timebase_detected" if np.isfinite(rate) else "timebase_detected_without_rate"}])
    return {"overview":overview,"time_columns":tc,"interval_summary":interval,"warnings":warnings}


def _schema_group(std):
    if std in _SCHEMA_GROUPS: return _SCHEMA_GROUPS[std]
    if re.fullmatch(r"TTL(_[0-9]+)?",std): return "ttl_marker"
    if re.fullmatch(r"TTLV(_[0-9]+)?",std): return "ttl_validity_flag"
    return "other"


def _schema_note(std):
    if std=="HRV": return "Treat as a validity/vendor flag unless documentation proves this column contains HRV metrics."
    if std=="IBI": return "May support IBI/RR-derived HRV summaries if values are genuine inter-beat intervals."
    if std in {"GSR","GSR_US","GSR_OHMS"}: return "GSR/EDA unit interpretation depends on export documentation and column naming."
    if std=="ENGAGEMENT": return "Engagement dial/self-report signal; do not interpret as physiological arousal."
    return np.nan


def detect_gazepoint_biometric_schema(data):
    if not isinstance(data,pd.DataFrame): raise TypeError("`data` must be a data frame.")
    name_map=standardise_gazepoint_biometric_names(data,rename=False); standards=name_map.standard_name.tolist()
    rows=[]
    for col,std in zip(data.columns,standards):
        values=data[col]; non=int(values.notna().sum()); uniq=int(values.dropna().nunique())
        rows.append({"column":col,"standard_name":std,"signal_group":_schema_group(std),"present":True,"active":bool(non>0 and uniq>0),
                     "n_non_missing":non,"n_unique_non_missing":uniq,"interpretation_note":_schema_note(std)})
    columns=pd.DataFrame(rows)
    tc=detect_gazepoint_time_columns(list(data.columns)); tb=detect_gazepoint_biometric_timebase(data)
    def has(g): return bool((columns.signal_group==g).any())
    def active(g): return bool((columns.loc[columns.signal_group==g,"active"]).any())
    active_groups=set(columns.loc[columns.active & columns.signal_group.isin(["gsr_eda","heart_rate","ibi","engagement_dial","ttl_marker"]),"signal_group"])
    status="biometric_schema_detected" if has("timing") and any(has(g) for g in ["gsr_eda","heart_rate","ibi","engagement_dial"]) else ("timing_detected_without_clear_biometric_signal" if has("timing") else "limited_schema_detected")
    overview=pd.DataFrame([{"n_rows":len(data),"n_columns":len(data.columns),"time_column_count":len(tc),"has_counter":"CNT" in standards,
                            "has_gsr_eda":has("gsr_eda"),"has_gsr_conductance":"GSR_US" in standards,"has_gsr_resistance":"GSR_OHMS" in standards,
                            "has_heart_rate":has("heart_rate"),"has_hrv_flag":"HRV" in standards,"has_ibi":has("ibi"),"has_engagement_dial":has("engagement_dial"),
                            "has_ttl_marker":has("ttl_marker"),"active_gsr_eda":active("gsr_eda"),"active_heart_rate":active("heart_rate"),"active_ibi":active("ibi"),
                            "active_engagement_dial":active("engagement_dial"),"active_ttl_marker":active("ttl_marker"),"active_signal_count":len(active_groups),"status":status}])
    notes=["Treat raw HRV columns as validity or vendor flags unless documentation proves they contain HRV metrics.",
           "IBI-derived HRV summaries should be computed only from genuine IBI/RR interval columns.",
           "GSR/EDA units should not be overclaimed unless the export column or study documentation identifies them."]
    return {"overview":overview,"columns":columns,"time_columns":tc,"timebase":tb,"name_map":name_map,"notes":notes}


def _drop_trailing(df):
    drops=[]
    for c in df.columns:
        if (c is None or str(c)=="" or str(c).lower().startswith("unnamed:")) and (df[c].isna()|df[c].astype("string").fillna("").str.strip().eq("")).all(): drops.append(c)
    return df.drop(columns=drops) if drops else df


def _section(lines, pattern, source_file):
    trimmed=[line.strip() for line in lines]
    idx=next((i for i,x in enumerate(trimmed) if re.search(pattern,x,re.I)),None)
    if idx is None: return pd.DataFrame({"source_file":pd.Series(dtype="object")})
    header=next((i for i in range(idx+1,len(lines)) if trimmed[i]),None)
    if header is None: return pd.DataFrame({"source_file":pd.Series(dtype="object")})
    end=header
    for i in range(header+1,len(lines)):
        if not trimmed[i]: break
        end=i
    text="\n".join(lines[header:end+1])
    df=pd.read_csv(StringIO(text),na_values=["","NA","NaN"],skipinitialspace=True)
    df=_drop_trailing(df)
    for c in df.columns:
        if df[c].dtype==object or pd.api.types.is_string_dtype(df[c]):
            numeric=pd.to_numeric(df[c],errors="coerce")
            nonempty=df[c].notna() & df[c].astype(str).str.strip().ne("")
            if nonempty.any() and numeric[nonempty].notna().all(): df[c]=numeric
    df["source_file"]=source_file
    return df


def import_gazepoint_data_summary(file):
    if not isinstance(file,(str,Path)) or not str(file): raise ValueError("`file` must be a single non-empty file path.")
    path=Path(file)
    if not path.exists(): raise FileNotFoundError(f"File does not exist: {path}")
    lines=path.read_text(encoding="utf-8").splitlines()
    def split(line):
        parts=line.split(",") if line else []
        return ((parts[0].strip() if parts else np.nan),(" ,".join([]) if False else (",".join(parts[1:]).strip() if len(parts)>1 else np.nan)))
    first=split(lines[0] if lines else ""); second=split(lines[1] if len(lines)>1 else "")
    notes=" | ".join(line.strip() for line in lines if re.match(r"^\s*Note:",line,re.I))
    metadata=pd.DataFrame([{"source_file":path.name,"software":first[0],"version":first[1],"processed_label":second[0],"processed_on":second[1],"notes":notes}])
    return {"metadata":metadata,"aoi_summary":_section(lines,r"^AOI Summary$",path.name),"aoi_statistics":_section(lines,r"^AOI Statistics",path.name),"class":["gazepoint_data_summary","list"]}
