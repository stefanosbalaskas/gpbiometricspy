from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Sequence

from .grouped_mixed_boosting import _canonical_digest, _group_folds, _positive_number, _prediction_matrix, _seed
from .grouped_ordinal_core import (
    GroupedOrdinalBoostingResult,
    _group_effect_vector,
    _hash_array,
    _ordinal_log_loss,
    _ordinal_probabilities,
    _predict_booster,
    _random_intercept_shrinkage,
    _ranked_probability_score,
    _resolve_category_order,
    _validate_training_frame,
    _fit_ordinal_booster,
    _initial_thresholds,
    _optimize_thresholds,
    _normalize_label,
    _ordinal_score,
    _group_offset_mode,
    _raw_from_thresholds,
    _thresholds_from_raw,
)

def fit_grouped_ordinal_boosting(
    data: pd.DataFrame,
    *,
    outcome_col: str,
    group_col: str,
    feature_cols: Sequence[str],
    category_order: Sequence[object] | None = None,
    n_estimators: int = 50,
    learning_rate: float = 0.05,
    max_depth: int = 2,
    min_samples_leaf: int = 5,
    max_iterations: int = 20,
    tolerance: float = 1e-4,
) -> GroupedOrdinalBoostingResult:
    """Fit cumulative-logit shallow-tree boosting with shrinkage-estimated group intercepts.

    This is a deterministic predictive research method for one clustering factor.
    The random-intercept update is an empirical-Bayes-style approximation based on
    groupwise cumulative-logit modes; it is not an integrated-likelihood CLMM.
    """
    y, X, groups, features, outcome_col, group_col, categories = _validate_training_frame(
        data, outcome_col, group_col, feature_cols, category_order
    )
    n_estimators = _positive_number(n_estimators, "n_estimators", integer=True)
    learning_rate = _positive_number(learning_rate, "learning_rate")
    if learning_rate > 1:
        raise ValueError("`learning_rate` must not exceed 1.")
    max_depth = _positive_number(max_depth, "max_depth", integer=True)
    if max_depth > 3:
        raise ValueError("`max_depth` is limited to 3 to keep the learner intentionally shallow.")
    min_samples_leaf = _positive_number(min_samples_leaf, "min_samples_leaf", integer=True)
    if 2 * min_samples_leaf > len(data):
        raise ValueError("`min_samples_leaf` is too large for the training data.")
    max_iterations = _positive_number(max_iterations, "max_iterations", integer=True)
    tolerance = _positive_number(tolerance, "tolerance")

    thresholds = _initial_thresholds(y, len(categories))
    group_effect = np.zeros(len(y), dtype=float)
    previous_fixed = np.zeros(len(y), dtype=float)
    converged = False
    trees: tuple[_BoostedTree, ...] = ()
    levels = tuple(str(level) for level in pd.unique(groups))
    effects = np.zeros(len(levels), dtype=float)
    tau2 = 0.0

    for iteration in range(1, max_iterations + 1):
        old_thresholds = thresholds.copy()
        old_group_effect = group_effect.copy()
        trees, fixed_prediction = _fit_ordinal_booster(
            X,
            y,
            thresholds,
            group_effect,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
        )
        levels, effects_array, tau2 = _random_intercept_shrinkage(y, fixed_prediction, groups, thresholds)
        effects = np.asarray(effects_array, dtype=float)
        group_effect = _group_effect_vector(groups, levels, tuple(float(value) for value in effects))
        thresholds = _optimize_thresholds(y, fixed_prediction + group_effect, thresholds)
        delta = max(
            float(np.max(np.abs(fixed_prediction - previous_fixed))),
            float(np.max(np.abs(group_effect - old_group_effect))),
            float(np.max(np.abs(thresholds - old_thresholds))),
        )
        if delta <= tolerance:
            converged = True
            break
        previous_fixed = fixed_prediction.copy()

    probabilities = _ordinal_probabilities(fixed_prediction + group_effect, thresholds)
    return GroupedOrdinalBoostingResult(
        outcome_col=outcome_col,
        group_col=group_col,
        feature_cols=features,
        category_order=categories,
        thresholds=tuple(float(value) for value in thresholds),
        trees=trees,
        group_levels=levels,
        group_effects=tuple(float(value) for value in effects),
        random_intercept_variance=tau2,
        n_iterations=iteration,
        converged=converged,
        tolerance=tolerance,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        training_rows=len(data),
        training_groups=len(levels),
        training_outcome_sha256=_hash_array(y),
        training_feature_sha256=_hash_array(X),
        training_ordinal_log_loss=_ordinal_log_loss(y, probabilities),
        training_ranked_probability_score=_ranked_probability_score(y, probabilities),
    )


def _prediction_linear_predictor(
    model: GroupedOrdinalBoostingResult,
    data: pd.DataFrame,
    *,
    mode: str,
    unseen_group: str,
):
    if not isinstance(model, GroupedOrdinalBoostingResult):
        raise TypeError("`model` must be returned by fit_grouped_ordinal_boosting().")
    if mode not in {"marginal", "conditional"}:
        raise ValueError("`mode` must be 'marginal' or 'conditional'.")
    if unseen_group not in {"marginal", "error"}:
        raise ValueError("`unseen_group` must be 'marginal' or 'error'.")
    X = _prediction_matrix(data, model.feature_cols)
    prediction = _predict_booster(model.trees, X)
    if mode == "marginal":
        return prediction
    if model.group_col not in data.columns:
        raise ValueError(f"Conditional prediction requires group column `{model.group_col}`.")
    if data[model.group_col].isna().any():
        raise ValueError("Conditional prediction group identifiers must not be missing.")
    mapping = dict(zip(model.group_levels, model.group_effects))
    additions = []
    unseen = []
    for group in data[model.group_col].astype(object).to_numpy():
        key = str(group)
        if key in mapping:
            additions.append(mapping[key])
        else:
            unseen.append(key)
            additions.append(0.0)
    if unseen and unseen_group == "error":
        raise ValueError("Conditional prediction encountered unseen groups: " + ", ".join(sorted(set(unseen))))
    return prediction + np.asarray(additions, dtype=float)


def predict_grouped_ordinal_boosting(
    model: GroupedOrdinalBoostingResult,
    data: pd.DataFrame,
    *,
    mode: str = "marginal",
    unseen_group: str = "marginal",
    output: str = "probability",
):
    if output not in {"probability", "cumulative_probability", "category"}:
        raise ValueError("`output` must be 'probability', 'cumulative_probability', or 'category'.")
    linear_predictor = _prediction_linear_predictor(model, data, mode=mode, unseen_group=unseen_group)
    probabilities = _ordinal_probabilities(linear_predictor, np.asarray(model.thresholds, dtype=float))
    if output == "probability":
        return probabilities
    if output == "cumulative_probability":
        return np.cumsum(probabilities, axis=1)[:, :-1]
    indices = np.argmax(probabilities, axis=1)
    return np.asarray([model.category_order[index] for index in indices], dtype=object)


def _encode_with_model(model: GroupedOrdinalBoostingResult, series: pd.Series) -> np.ndarray:
    if series.isna().any():
        raise ValueError("Ordinal outcome values must not be missing.")
    mapping = {value: index for index, value in enumerate(model.category_order)}
    values = [_normalize_label(value) for value in series.astype(object).tolist()]
    if any(value not in mapping for value in values):
        raise ValueError("Observed outcome contains a category absent from the fitted model.")
    return np.asarray([mapping[value] for value in values], dtype=int)


def grouped_cross_validation_ordinal_boosting(
    data: pd.DataFrame,
    *,
    outcome_col: str,
    group_col: str,
    feature_cols: Sequence[str],
    category_order: Sequence[object] | None = None,
    n_splits: int = 5,
    seed: int = 0,
    **fit_kwargs,
):
    y, _, groups, _, outcome_col, group_col, categories = _validate_training_frame(
        data, outcome_col, group_col, feature_cols, category_order
    )
    if isinstance(n_splits, bool) or int(n_splits) != n_splits:
        raise ValueError("`n_splits` must be an integer.")
    n_splits = int(n_splits)
    folds = _group_folds(groups, n_splits, _seed(seed))
    probabilities = np.full((len(data), len(categories)), np.nan, dtype=float)
    held_out = []
    for fold_groups in folds:
        test_mask = np.isin(groups, fold_groups)
        train_mask = ~test_mask
        if len(pd.unique(groups[train_mask])) < 4:
            raise ValueError("Each training fold must retain at least four distinct groups.")
        model = fit_grouped_ordinal_boosting(
            data.loc[train_mask].copy(),
            outcome_col=outcome_col,
            group_col=group_col,
            feature_cols=feature_cols,
            category_order=categories,
            **fit_kwargs,
        )
        probabilities[test_mask] = predict_grouped_ordinal_boosting(
            model,
            data.loc[test_mask],
            mode="marginal",
            output="probability",
        )
        held_out.append(tuple(str(value) for value in fold_groups))
    if not np.all(np.isfinite(probabilities)):
        raise RuntimeError("Grouped cross-validation failed to assign one finite probability vector to every row.")
    predicted_index = np.argmax(probabilities, axis=1)
    return {
        "oof_probabilities": probabilities,
        "oof_category": np.asarray([categories[index] for index in predicted_index], dtype=object),
        "ordinal_log_loss": _ordinal_log_loss(y, probabilities),
        "ranked_probability_score": _ranked_probability_score(y, probabilities),
        "mean_absolute_category_error": float(np.mean(np.abs(predicted_index - y))),
        "folds": tuple(held_out),
        "prediction_mode": "marginal_unseen_group",
    }


def group_aware_ordinal_permutation_importance(
    model: GroupedOrdinalBoostingResult,
    data: pd.DataFrame,
    *,
    repeats: int = 5,
    seed: int = 0,
    prediction_mode: str = "conditional",
) -> pd.DataFrame:
    if not isinstance(model, GroupedOrdinalBoostingResult):
        raise TypeError("`model` must be returned by fit_grouped_ordinal_boosting().")
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    if model.outcome_col not in data.columns:
        raise ValueError(f"Outcome column `{model.outcome_col}` is required for permutation importance.")
    if model.group_col not in data.columns:
        raise ValueError(f"Group column `{model.group_col}` is required for group-aware permutation importance.")
    repeats = _positive_number(repeats, "repeats", integer=True)
    seed = _seed(seed)
    if prediction_mode not in {"marginal", "conditional"}:
        raise ValueError("`prediction_mode` must be 'marginal' or 'conditional'.")
    y = _encode_with_model(model, data[model.outcome_col])
    baseline_probability = predict_grouped_ordinal_boosting(
        model, data, mode=prediction_mode, output="probability"
    )
    baseline = _ranked_probability_score(y, baseline_probability)
    rng = np.random.default_rng(seed)
    rows = []
    for feature in model.feature_cols:
        group_nunique = data.groupby(model.group_col, sort=False)[feature].nunique(dropna=False)
        feature_level = "group" if bool((group_nunique == 1).all()) else "within_group"
        scores = []
        for _ in range(repeats):
            permuted = data.copy()
            if feature_level == "group":
                levels = list(pd.unique(permuted[model.group_col]))
                source = rng.permutation(levels)
                values = {
                    target: permuted.loc[permuted[model.group_col] == origin, feature].iloc[0]
                    for target, origin in zip(levels, source)
                }
                permuted[feature] = [values[group] for group in permuted[model.group_col]]
            else:
                for group in pd.unique(permuted[model.group_col]):
                    mask = permuted[model.group_col] == group
                    values = permuted.loc[mask, feature].to_numpy(copy=True)
                    permuted.loc[mask, feature] = rng.permutation(values)
            probability = predict_grouped_ordinal_boosting(
                model, permuted, mode=prediction_mode, output="probability"
            )
            scores.append(_ranked_probability_score(y, probability) - baseline)
        rows.append(
            {
                "feature": feature,
                "feature_level": feature_level,
                "importance_mean_rps_increase": float(np.mean(scores)),
                "importance_sd": float(np.std(scores, ddof=1)) if repeats > 1 else 0.0,
                "repeats": repeats,
                "baseline_rps": baseline,
                "prediction_mode": prediction_mode,
            }
        )
    return pd.DataFrame(rows)


def _tree_payload(node):
    payload = {"value": float(node.value)}
    if node.feature is not None:
        payload.update(
            {
                "feature": int(node.feature),
                "threshold": float(node.threshold),
                "left": _tree_payload(node.left),
                "right": _tree_payload(node.right),
            }
        )
    return payload


def _certificate_payload(model: GroupedOrdinalBoostingResult):
    return {
        "schema_version": model.schema_version,
        "outcome_col": model.outcome_col,
        "group_col": model.group_col,
        "feature_cols": list(model.feature_cols),
        "category_order": list(model.category_order),
        "thresholds": list(model.thresholds),
        "trees": [
            {"learning_rate": tree.learning_rate, "root": _tree_payload(tree.root)} for tree in model.trees
        ],
        "group_levels": list(model.group_levels),
        "group_effects": list(model.group_effects),
        "random_intercept_variance": model.random_intercept_variance,
        "n_iterations": model.n_iterations,
        "converged": model.converged,
        "tolerance": model.tolerance,
        "n_estimators": model.n_estimators,
        "learning_rate": model.learning_rate,
        "max_depth": model.max_depth,
        "min_samples_leaf": model.min_samples_leaf,
        "training_rows": model.training_rows,
        "training_groups": model.training_groups,
        "training_outcome_sha256": model.training_outcome_sha256,
        "training_feature_sha256": model.training_feature_sha256,
        "training_ordinal_log_loss": model.training_ordinal_log_loss,
        "training_ranked_probability_score": model.training_ranked_probability_score,
    }


def create_grouped_ordinal_boosting_certificate(model: GroupedOrdinalBoostingResult):
    if not isinstance(model, GroupedOrdinalBoostingResult):
        raise TypeError("`model` must be returned by fit_grouped_ordinal_boosting().")
    payload = _certificate_payload(model)
    return {"payload": payload, "sha256": _canonical_digest(payload)}


def validate_grouped_ordinal_boosting_certificate(model: GroupedOrdinalBoostingResult, certificate) -> bool:
    if not isinstance(model, GroupedOrdinalBoostingResult) or not isinstance(certificate, dict):
        return False
    payload = certificate.get("payload")
    digest = certificate.get("sha256")
    if not isinstance(payload, dict) or not isinstance(digest, str):
        return False
    expected = _certificate_payload(model)
    return payload == expected and digest == _canonical_digest(payload)
