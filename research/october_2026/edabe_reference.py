"""Fail-closed intake for user-supplied EDABE-like reference exports.

Field names follow the published EDABE description. This adapter does not
redistribute recordings, infer study permissions, or call artifact labels SCR.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


EDABE_FIELDS = (
    "time", "rawdata", "cleandata", "binarytarget",
    "signal_automatic", "predArtifacts", "postProcessedPredArtifacts",
)


def audit_edabe_reference_export(
    frame: pd.DataFrame,
    *,
    participant_col="participant_id",
    recording_col="recording_id",
    split_col="benchmark_split",
) -> dict:
    """Compare supplied raw/automatic EDA to expert-corrected EDABE reference.

    Splits are a user-supplied training/test declaration and cannot be
    independently authenticated from copied columns. Event labels refer to
    artifacts, not physiological SCR; no downstream task inference is made.
    """
    columns=[participant_col,recording_col,split_col,*EDABE_FIELDS]
    if not set(columns).issubset(frame.columns):
        raise ValueError("EDABE reference export requires metadata and published field names")
    if frame[columns].isna().any().any() or frame.empty:
        raise ValueError("EDABE rows, identities and measurements must be complete")
    if not frame[split_col].isin(["train", "test"]).all():
        raise ValueError("benchmark split must be declared as train or test")
    people_by_split={
        key:set(group[participant_col])
        for key,group in frame.groupby(split_col)
    }
    if people_by_split.get("train",set()) & people_by_split.get("test",set()):
        raise ValueError("participant identity leakage across EDABE train/test")
    if len(people_by_split.get("train",set()))==0 or len(
        people_by_split.get("test",set())
    )==0:
        raise ValueError("both EDABE training and test participants required")
    if not frame["binarytarget"].isin([0,1]).all() or not frame[
        ["predArtifacts","postProcessedPredArtifacts"]
    ].isin([0,1]).all().all():
        raise ValueError("EDABE binary artifact markers must be zero/one")
    for col in ("time","rawdata","cleandata","signal_automatic"):
        values=pd.to_numeric(frame[col],errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("EDABE signal and timestamp values must be finite")
    rows=[]
    for key,group in frame.groupby([participant_col,recording_col,split_col],sort=False):
        t=group["time"].to_numpy(dtype=float)
        if len(t)<3 or np.any(np.diff(t)<=0):
            raise ValueError("each recording needs >=3 strictly increasing timestamps")
        reference=group["cleandata"].to_numpy(dtype=float)
        raw=group["rawdata"].to_numpy(dtype=float)
        processed=group["signal_automatic"].to_numpy(dtype=float)
        truth=group["binarytarget"].to_numpy(dtype=int)
        predicted=group["postProcessedPredArtifacts"].to_numpy(dtype=int)
        tp=int(np.count_nonzero((predicted==1)&(truth==1)))
        fp=int(np.count_nonzero((predicted==1)&(truth==0)))
        fn=int(np.count_nonzero((predicted==0)&(truth==1)))
        rows.append({
            "participant_id":key[0],"recording_id":key[1],"benchmark_split":key[2],
            "n_samples":len(t),"artifact_fraction":float(truth.mean()),
            "raw_expert_mae":float(np.abs(raw-reference).mean()),
            "automatic_expert_mae":float(np.abs(processed-reference).mean()),
            "automatic_minus_raw_mae":float(
                np.abs(processed-reference).mean()-np.abs(raw-reference).mean()),
            "artifact_precision":tp/(tp+fp) if tp+fp else np.nan,
            "artifact_recall":tp/(tp+fn) if tp+fn else np.nan,
        })
    return {
        "recording_metrics":pd.DataFrame(rows),
        "participant_disjoint_by_declared_id":True,
        "reference_kind":"human_edited_eda_signal_and_artifact_annotations",
        "claim_boundary":(
            "Expert-reference waveform and artifact labels only; not ground "
            "truth physiology, SCR retention, device validity, classification "
            "improvement, independent source permissions, or clinical utility."
        ),
    }
