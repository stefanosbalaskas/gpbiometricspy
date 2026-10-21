"""Research-only external classifier and ablation validation contracts."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _metrics(y, probabilities, threshold):
    predicted = probabilities >= threshold
    positive = y == 1
    tp = np.count_nonzero(predicted & positive)
    fp = np.count_nonzero(predicted & ~positive)
    fn = np.count_nonzero(~predicted & positive)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    negatives = np.count_nonzero(~positive)
    specificity = np.count_nonzero(~predicted & ~positive) / negatives if negatives else np.nan
    balanced = (recall + specificity) / 2 if np.isfinite(specificity) else np.nan
    # Average precision with all tied scores grouped at the same threshold.
    levels = np.unique(probabilities)[::-1]
    ap = 0.0
    previous_recall = 0.0
    for score in levels:
        keep = probabilities >= score
        tp_k = np.count_nonzero(keep & positive)
        if np.count_nonzero(positive) == 0:
            break
        recall_k = tp_k / np.count_nonzero(positive)
        precision_k = tp_k / np.count_nonzero(keep)
        ap += (recall_k - previous_recall) * precision_k
        previous_recall = recall_k
    return {"precision": float(precision), "recall": float(recall),
            "f1": float(f1), "balanced_accuracy": float(balanced),
            "average_precision": float(ap),
            "positive_prevalence": float(np.mean(positive))}


def external_classifier_validation(
    evaluation: pd.DataFrame,
    *,
    training_participants,
    training_datasets,
    participant_col="participant_id",
    dataset_col="dataset_id",
    outcome_col="outcome",
    probability_col="probability",
    locked_threshold=0.5,
    bootstrap_replicates=199,
    seed=7,
) -> dict:
    """Compute prevalence-aware metrics and whole-participant bootstrap intervals.

    Requires a caller-declared frozen threshold; cannot independently establish
    when model fitting, threshold selection or hyperparameter tuning occurred.
    """
    cols = [participant_col, dataset_col, outcome_col, probability_col]
    if not set(cols).issubset(evaluation):
        raise ValueError("required external validation columns missing")
    if not 0 < locked_threshold < 1 or bootstrap_replicates < 99:
        raise ValueError("threshold/replication contract violated")
    if evaluation[cols].isna().any().any() or evaluation.empty:
        raise ValueError("evaluation must be complete and nonempty")
    if set(evaluation[participant_col]) & set(training_participants):
        raise ValueError("participant leakage between training and evaluation")
    if set(evaluation[dataset_col]) & set(training_datasets):
        raise ValueError("external validation requires disjoint dataset identities")
    y = evaluation[outcome_col].to_numpy(dtype=int)
    p = evaluation[probability_col].to_numpy(dtype=float)
    if not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("binary outcomes and probability scores required")
    if len(np.unique(y)) != 2:
        raise ValueError("both classes must be represented in external validation")
    raw = _metrics(y, p, locked_threshold)
    participants = evaluation[participant_col].unique()
    if len(participants) < 2:
        raise ValueError("at least two independent external participants required")
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(bootstrap_replicates):
        selection = rng.choice(participants, size=len(participants), replace=True)
        ix = np.concatenate([
            np.flatnonzero(evaluation[participant_col].to_numpy() == v) for v in selection])
        yy, pp = y[ix], p[ix]
        if np.unique(yy).size == 2:
            boot.append(_metrics(yy, pp, locked_threshold))
    intervals = {}
    for metric in raw:
        values = [record[metric] for record in boot if np.isfinite(record[metric])]
        intervals[metric] = (
            [float(v) for v in np.quantile(values, [.025, .975])] if values else None)
    return {"metrics": raw, "participant_bootstrap_interval": intervals,
            "n_bootstrap_accepted": len(boot), "n_participants": len(participants),
            "locked_threshold_declared": float(locked_threshold),
            "claim_boundary": "Evaluation of supplied frozen predictions; model lock provenance is not independently verified."}


def modality_ablation_audit(
    predictions: pd.DataFrame,
    *,
    participant_col="participant_id",
    outcome_col="outcome",
    full_col="full_probability",
    ablated_col="ablated_probability",
    threshold=0.5,
    bootstrap_replicates=199,
    seed=7,
) -> dict:
    """Paired model-ablation metric differences with participant resampling."""
    required = [participant_col, outcome_col, full_col, ablated_col]
    if not set(required).issubset(predictions):
        raise ValueError("matched prediction columns required")
    if predictions[required].isna().any().any():
        raise ValueError("matched predictions must be complete")
    y = predictions[outcome_col].to_numpy(dtype=int)
    a = predictions[full_col].to_numpy(dtype=float)
    b = predictions[ablated_col].to_numpy(dtype=float)
    if not np.isin(y, [0, 1]).all() or len(np.unique(y)) != 2 or (
        not np.isfinite(a).all() or not np.isfinite(b).all() or
        np.any((a < 0) | (a > 1)) or np.any((b < 0) | (b > 1))):
        raise ValueError("binary outcomes and finite probability predictions required")
    ids = predictions[participant_col].unique()
    if len(ids) < 2 or bootstrap_replicates < 99:
        raise ValueError("participant-level replication required")
    raw = _metrics(y, a, threshold)["balanced_accuracy"] - _metrics(y, b, threshold)["balanced_accuracy"]
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(bootstrap_replicates):
        selection = rng.choice(ids, size=len(ids), replace=True)
        ix = np.concatenate([np.flatnonzero(predictions[participant_col].to_numpy() == v)
                             for v in selection])
        if len(np.unique(y[ix])) == 2:
            am = _metrics(y[ix], a[ix], threshold)["balanced_accuracy"]
            bm = _metrics(y[ix], b[ix], threshold)["balanced_accuracy"]
            boot.append(am - bm)
    return {"delta_balanced_accuracy": float(raw),
            "participant_bootstrap_interval": (
                tuple(float(v) for v in np.quantile(boot, [.025, .975])) if boot else None),
            "accepted_bootstrap_replicates": len(boot),
            "claim_boundary": "Paired ablation association, not causal sensor complementarity."}


def external_device_placement_strata(
    evaluation: pd.DataFrame,
    *,
    participant_col="participant_id",
    device_col="device_id",
    placement_col="body_placement",
    outcome_col="outcome",
    probability_col="probability",
    locked_threshold=0.5,
    min_participants=2,
) -> pd.DataFrame:
    """Preserve all observed device-by-placement strata, including ineligible.

    This is not an AICOS-HAR loader, leave-device-out fit, or external domain
    validation by itself. Model-training provenance is required separately.
    """
    required=[participant_col,device_col,placement_col,outcome_col,probability_col]
    if not set(required).issubset(evaluation):
        raise ValueError("device, placement and prediction fields required")
    if evaluation.empty or evaluation[required].isna().any().any():
        raise ValueError("complete nonempty stratified predictions required")
    if not 0 < locked_threshold < 1 or min_participants < 2:
        raise ValueError("locked threshold or minimum participants invalid")
    rows=[]
    for (device, placement), group in evaluation.groupby(
        [device_col,placement_col],sort=True
    ):
        y=group[outcome_col].to_numpy()
        scores=pd.to_numeric(group[probability_col],errors="coerce").to_numpy(dtype=float)
        if not np.isin(y,[0,1]).all() or not np.isfinite(scores).all() or (
            np.any((scores<0)|(scores>1))
        ):
            raise ValueError("binary outcomes and valid probability scores required")
        n_people=group[participant_col].nunique()
        qualified=n_people>=min_participants and len(np.unique(y))==2
        row={
            "device_id":device,"body_placement":placement,
            "n_rows":len(group),"n_participants":n_people,
            "positive_prevalence":float(np.mean(y)),
            "status":"evaluable" if qualified else "insufficient_independent_evidence",
            "balanced_accuracy":np.nan,
            "average_precision":np.nan,
        }
        if qualified:
            result=_metrics(y,scores,locked_threshold)
            row["balanced_accuracy"]=result["balanced_accuracy"]
            row["average_precision"]=result["average_precision"]
        rows.append(row)
    return pd.DataFrame(rows)
