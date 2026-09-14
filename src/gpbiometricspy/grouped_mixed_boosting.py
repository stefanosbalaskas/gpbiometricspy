from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence
import json

import numpy as np
import pandas as pd

_SCHEMA_VERSION = "gpbiometricspy-grouped-mixed-boosting-v1"


def _positive_number(value, name: str, *, integer: bool = False, minimum: float = 0.0):
    number = float(value)
    if not np.isfinite(number) or number <= minimum:
        raise ValueError(f"`{name}` must be finite and greater than {minimum}.")
    if integer and int(number) != number:
        raise ValueError(f"`{name}` must be an integer.")
    return int(number) if integer else number


def _nonempty_string(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{name}` must be a non-empty string.")
    return value.strip()


def _seed(value) -> int:
    if isinstance(value, bool) or int(value) != value or int(value) < 0:
        raise ValueError("`seed` must be a non-negative integer.")
    return int(value)


def _canonical_digest(payload: Mapping) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(text.encode("utf-8")).hexdigest()


def _hash_array(values: np.ndarray) -> str:
    arr = np.asarray(values, dtype=float)
    return sha256(arr.astype("<f8", copy=False).tobytes()).hexdigest()


def _validate_training_frame(data, outcome_col: str, group_col: str, feature_cols: Sequence[str]):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    outcome_col = _nonempty_string(outcome_col, "outcome_col")
    group_col = _nonempty_string(group_col, "group_col")
    if outcome_col == group_col:
        raise ValueError("`outcome_col` and `group_col` must be distinct.")
    if isinstance(feature_cols, str) or not isinstance(feature_cols, Sequence) or not feature_cols:
        raise ValueError("`feature_cols` must be a non-empty sequence of column names.")
    features = tuple(_nonempty_string(col, "feature_cols") for col in feature_cols)
    if len(set(features)) != len(features):
        raise ValueError("`feature_cols` must not contain duplicates.")
    if outcome_col in features or group_col in features:
        raise ValueError("Outcome and group columns cannot also be feature columns.")
    missing = [col for col in (outcome_col, group_col, *features) if col not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if data.empty:
        raise ValueError("`data` must contain at least one row.")
    y = pd.to_numeric(data[outcome_col], errors="coerce").to_numpy(float)
    X = data.loc[:, features].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    groups_raw = data[group_col].astype(object).to_numpy()
    if not np.all(np.isfinite(y)):
        raise ValueError("Outcome values must all be finite numeric values.")
    if not np.all(np.isfinite(X)):
        raise ValueError("Feature values must all be finite numeric values.")
    if pd.isna(groups_raw).any():
        raise ValueError("Group identifiers must not be missing.")
    unique_raw = pd.unique(groups_raw)
    normalized = tuple(str(value) for value in unique_raw)
    if len(set(normalized)) != len(normalized):
        raise ValueError("Group identifiers must remain unique after string normalization.")
    mapping = {value: str(value) for value in unique_raw}
    groups = np.asarray([mapping[value] for value in groups_raw], dtype=object)
    if len(normalized) < 4:
        raise ValueError("At least four distinct groups are required.")
    return y, X, groups, features, outcome_col, group_col


@dataclass(frozen=True)
class _TreeNode:
    value: float
    feature: int | None = None
    threshold: float | None = None
    left: "_TreeNode | None" = None
    right: "_TreeNode | None" = None


@dataclass(frozen=True)
class _BoostedTree:
    learning_rate: float
    root: _TreeNode


@dataclass(frozen=True)
class GroupedMixedBoostingResult:
    outcome_col: str
    group_col: str
    feature_cols: tuple[str, ...]
    intercept: float
    trees: tuple[_BoostedTree, ...]
    group_levels: tuple[str, ...]
    group_effects: tuple[float, ...]
    random_intercept_variance: float
    residual_variance: float
    n_iterations: int
    converged: bool
    tolerance: float
    n_estimators: int
    learning_rate: float
    max_depth: int
    min_samples_leaf: int
    training_rows: int
    training_groups: int
    training_outcome_sha256: str
    training_feature_sha256: str
    schema_version: str = _SCHEMA_VERSION


def _sse(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    mean = float(np.mean(values))
    return float(np.sum((values - mean) ** 2))


def _best_split(X: np.ndarray, y: np.ndarray, indices: np.ndarray, min_samples_leaf: int):
    parent_sse = _sse(y[indices])
    best = None
    for feature in range(X.shape[1]):
        values = X[indices, feature]
        order = np.argsort(values, kind="mergesort")
        ordered_values = values[order]
        ordered_indices = indices[order]
        if ordered_values.size < 2 * min_samples_leaf:
            continue
        for pos in range(min_samples_leaf, ordered_values.size - min_samples_leaf + 1):
            if pos == ordered_values.size or ordered_values[pos - 1] == ordered_values[pos]:
                continue
            left_idx = ordered_indices[:pos]
            right_idx = ordered_indices[pos:]
            loss = _sse(y[left_idx]) + _sse(y[right_idx])
            gain = parent_sse - loss
            threshold = float((ordered_values[pos - 1] + ordered_values[pos]) / 2.0)
            candidate = (gain, -feature, -threshold, feature, threshold, left_idx, right_idx)
            if best is None or candidate[:3] > best[:3]:
                best = candidate
    return best


def _fit_tree(X: np.ndarray, y: np.ndarray, *, max_depth: int, min_samples_leaf: int) -> _TreeNode:
    def build(indices: np.ndarray, depth: int) -> _TreeNode:
        value = float(np.mean(y[indices]))
        if depth >= max_depth or len(indices) < 2 * min_samples_leaf:
            return _TreeNode(value=value)
        split = _best_split(X, y, indices, min_samples_leaf)
        if split is None or split[0] <= 0:
            return _TreeNode(value=value)
        _, _, _, feature, threshold, left_idx, right_idx = split
        return _TreeNode(
            value=value,
            feature=feature,
            threshold=threshold,
            left=build(left_idx, depth + 1),
            right=build(right_idx, depth + 1),
        )

    return build(np.arange(len(y), dtype=int), 0)


def _predict_node(node: _TreeNode, X: np.ndarray) -> np.ndarray:
    if node.feature is None:
        return np.full(X.shape[0], node.value, dtype=float)
    mask = X[:, node.feature] <= node.threshold
    out = np.empty(X.shape[0], dtype=float)
    out[mask] = _predict_node(node.left, X[mask])
    out[~mask] = _predict_node(node.right, X[~mask])
    return out


def _fit_booster(
    X: np.ndarray,
    target: np.ndarray,
    *,
    n_estimators: int,
    learning_rate: float,
    max_depth: int,
    min_samples_leaf: int,
):
    intercept = float(np.mean(target))
    prediction = np.full(len(target), intercept, dtype=float)
    trees: list[_BoostedTree] = []
    for _ in range(n_estimators):
        residual = target - prediction
        root = _fit_tree(X, residual, max_depth=max_depth, min_samples_leaf=min_samples_leaf)
        step = _predict_node(root, X)
        prediction = prediction + learning_rate * step
        trees.append(_BoostedTree(learning_rate=learning_rate, root=root))
    return intercept, tuple(trees), prediction


def _predict_booster(intercept: float, trees: tuple[_BoostedTree, ...], X: np.ndarray) -> np.ndarray:
    out = np.full(X.shape[0], intercept, dtype=float)
    for tree in trees:
        out += tree.learning_rate * _predict_node(tree.root, X)
    return out


def _random_intercept_blup(residual: np.ndarray, groups: np.ndarray):
    labels = pd.unique(groups)
    counts = np.array([np.sum(groups == label) for label in labels], dtype=float)
    means = np.array([np.mean(residual[groups == label]) for label in labels], dtype=float)
    within_ss = sum(float(np.sum((residual[groups == label] - means[i]) ** 2)) for i, label in enumerate(labels))
    within_df = len(residual) - len(labels)
    sigma_e2 = within_ss / within_df if within_df > 0 else 0.0
    grand = float(np.average(means, weights=counts))
    between_ss = float(np.sum(counts * (means - grand) ** 2))
    ms_between = between_ss / (len(labels) - 1)
    n0 = (len(residual) - float(np.sum(counts**2)) / len(residual)) / (len(labels) - 1)
    sigma_b2 = max((ms_between - sigma_e2) / n0, 0.0) if n0 > 0 else 0.0
    effects = []
    for count, mean in zip(counts, means):
        denom = sigma_e2 + count * sigma_b2
        shrinkage = count * sigma_b2 / denom if denom > 0 else 0.0
        effects.append(float(shrinkage * (mean - grand)))
    return labels, np.asarray(effects, dtype=float), float(sigma_b2), float(sigma_e2)


def _group_effect_vector(groups: np.ndarray, levels: tuple[str, ...], effects: tuple[float, ...]) -> np.ndarray:
    mapping = dict(zip(levels, effects))
    return np.asarray([mapping.get(str(group), 0.0) for group in groups], dtype=float)


def fit_grouped_mixed_boosting(
    data: pd.DataFrame,
    *,
    outcome_col: str,
    group_col: str,
    feature_cols: Sequence[str],
    n_estimators: int = 50,
    learning_rate: float = 0.05,
    max_depth: int = 2,
    min_samples_leaf: int = 5,
    max_iterations: int = 20,
    tolerance: float = 1e-5,
) -> GroupedMixedBoostingResult:
    """Fit deterministic shallow-tree boosting plus a Gaussian random intercept.

    The alternating estimator is intended for nonlinear clustered prediction,
    not causal inference. Conditional predictions use empirical-Bayes random
    intercepts only for groups observed in the training data.
    """
    y, X, groups, features, outcome_col, group_col = _validate_training_frame(
        data, outcome_col, group_col, feature_cols
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

    group_effect = np.zeros(len(y), dtype=float)
    previous = group_effect.copy()
    converged = False
    intercept = float(np.mean(y))
    trees: tuple[_BoostedTree, ...] = ()
    sigma_b2 = 0.0
    sigma_e2 = float(np.var(y, ddof=1)) if len(y) > 1 else 0.0
    levels_raw = pd.unique(groups)
    effects = np.zeros(len(levels_raw), dtype=float)

    for iteration in range(1, max_iterations + 1):
        intercept, trees, fixed_prediction = _fit_booster(
            X,
            y - group_effect,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
        )
        levels_raw, effects, sigma_b2, sigma_e2 = _random_intercept_blup(y - fixed_prediction, groups)
        levels = tuple(str(level) for level in levels_raw)
        group_effect = _group_effect_vector(groups, levels, tuple(float(x) for x in effects))
        delta = float(np.max(np.abs(group_effect - previous)))
        if delta <= tolerance:
            converged = True
            break
        previous = group_effect.copy()

    return GroupedMixedBoostingResult(
        outcome_col=outcome_col,
        group_col=group_col,
        feature_cols=features,
        intercept=intercept,
        trees=trees,
        group_levels=tuple(str(level) for level in levels_raw),
        group_effects=tuple(float(value) for value in effects),
        random_intercept_variance=sigma_b2,
        residual_variance=sigma_e2,
        n_iterations=iteration,
        converged=converged,
        tolerance=tolerance,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        training_rows=len(data),
        training_groups=len(levels_raw),
        training_outcome_sha256=_hash_array(y),
        training_feature_sha256=_hash_array(X),
    )


def _prediction_matrix(data: pd.DataFrame, feature_cols: tuple[str, ...]) -> np.ndarray:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    missing = [col for col in feature_cols if col not in data.columns]
    if missing:
        raise ValueError("Missing required feature columns: " + ", ".join(missing))
    X = data.loc[:, feature_cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.all(np.isfinite(X)):
        raise ValueError("Prediction features must all be finite numeric values.")
    return X


def predict_grouped_mixed_boosting(
    model: GroupedMixedBoostingResult,
    data: pd.DataFrame,
    *,
    mode: str = "marginal",
    unseen_group: str = "marginal",
) -> np.ndarray:
    if not isinstance(model, GroupedMixedBoostingResult):
        raise TypeError("`model` must be returned by fit_grouped_mixed_boosting().")
    if mode not in {"marginal", "conditional"}:
        raise ValueError("`mode` must be 'marginal' or 'conditional'.")
    if unseen_group not in {"marginal", "error"}:
        raise ValueError("`unseen_group` must be 'marginal' or 'error'.")
    X = _prediction_matrix(data, model.feature_cols)
    prediction = _predict_booster(model.intercept, model.trees, X)
    if mode == "marginal":
        return prediction
    if model.group_col not in data.columns:
        raise ValueError(f"Conditional prediction requires group column `{model.group_col}`.")
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
        raise ValueError("Conditional prediction contains unseen groups: " + ", ".join(sorted(set(unseen))))
    return prediction + np.asarray(additions, dtype=float)


def _group_folds(groups: np.ndarray, n_splits: int, seed: int) -> list[np.ndarray]:
    unique = np.asarray(pd.unique(groups), dtype=object)
    if n_splits < 2 or n_splits > len(unique):
        raise ValueError("`n_splits` must be between 2 and the number of groups.")
    seed = _seed(seed)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(unique))
    unique = unique[order]
    bins: list[list[object]] = [[] for _ in range(n_splits)]
    counts = [0] * n_splits
    sizes = {group: int(np.sum(groups == group)) for group in unique}
    tie_rank = {group: rank for rank, group in enumerate(unique)}
    for group in sorted(unique, key=lambda g: (-sizes[g], tie_rank[g])):
        fold = min(range(n_splits), key=lambda idx: (counts[idx], idx))
        bins[fold].append(group)
        counts[fold] += sizes[group]
    return [np.asarray(values, dtype=object) for values in bins]


def grouped_cross_validation_mixed_boosting(
    data: pd.DataFrame,
    *,
    outcome_col: str,
    group_col: str,
    feature_cols: Sequence[str],
    n_splits: int = 5,
    seed: int = 1,
    **fit_kwargs,
) -> dict:
    y, _, groups, features, outcome_col, group_col = _validate_training_frame(
        data, outcome_col, group_col, feature_cols
    )
    if int(n_splits) != n_splits:
        raise ValueError("`n_splits` must be an integer.")
    n_splits = int(n_splits)
    folds = _group_folds(groups, n_splits, seed)
    for held_groups in folds:
        if len(pd.unique(groups[~np.isin(groups, held_groups)])) < 4:
            raise ValueError("Each CV training fold must retain at least four distinct groups.")
    seed = _seed(seed)
    oof = np.full(len(data), np.nan, dtype=float)
    rows = []
    for fold_id, held_groups in enumerate(folds, start=1):
        test_mask = np.isin(groups, held_groups)
        train = data.loc[~test_mask].reset_index(drop=True)
        test = data.loc[test_mask]
        model = fit_grouped_mixed_boosting(
            train,
            outcome_col=outcome_col,
            group_col=group_col,
            feature_cols=features,
            **fit_kwargs,
        )
        pred = predict_grouped_mixed_boosting(model, test, mode="marginal")
        oof[np.flatnonzero(test_mask)] = pred
        residual = y[test_mask] - pred
        rows.append(
            {
                "fold": fold_id,
                "n_train": int((~test_mask).sum()),
                "n_test": int(test_mask.sum()),
                "held_out_groups": tuple(str(x) for x in held_groups),
                "mse": float(np.mean(residual**2)),
                "rmse": float(np.sqrt(np.mean(residual**2))),
            }
        )
    if not np.all(np.isfinite(oof)):
        raise RuntimeError("Group-aware CV failed to produce one finite OOF prediction per row.")
    residual = y - oof
    return {
        "folds": pd.DataFrame(rows),
        "oof_prediction": oof,
        "mse": float(np.mean(residual**2)),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "prediction_mode": "marginal_unseen_group",
        "n_splits": n_splits,
        "seed": seed,
    }


def _feature_level(data: pd.DataFrame, group_col: str, feature: str) -> str:
    counts = data.groupby(group_col, sort=False, dropna=False)[feature].nunique(dropna=False)
    return "group" if bool((counts <= 1).all()) else "within_group"


def group_aware_permutation_importance(
    model: GroupedMixedBoostingResult,
    data: pd.DataFrame,
    *,
    outcome_col: str | None = None,
    repeats: int = 20,
    seed: int = 1,
    prediction_mode: str = "marginal",
) -> pd.DataFrame:
    if not isinstance(model, GroupedMixedBoostingResult):
        raise TypeError("`model` must be returned by fit_grouped_mixed_boosting().")
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    outcome_col = model.outcome_col if outcome_col is None else _nonempty_string(outcome_col, "outcome_col")
    if outcome_col not in data.columns:
        raise ValueError(f"Outcome column `{outcome_col}` was not found.")
    if model.group_col not in data.columns:
        raise ValueError(f"Group column `{model.group_col}` was not found.")
    y = pd.to_numeric(data[outcome_col], errors="coerce").to_numpy(float)
    if not np.all(np.isfinite(y)):
        raise ValueError("Outcome values must all be finite numeric values.")
    repeats = _positive_number(repeats, "repeats", integer=True)
    if prediction_mode not in {"marginal", "conditional"}:
        raise ValueError("`prediction_mode` must be 'marginal' or 'conditional'.")
    baseline = predict_grouped_mixed_boosting(model, data, mode=prediction_mode)
    baseline_mse = float(np.mean((y - baseline) ** 2))
    seed = _seed(seed)
    rng = np.random.default_rng(seed)
    rows = []
    for feature in model.feature_cols:
        level = _feature_level(data, model.group_col, feature)
        losses = []
        for _ in range(repeats):
            permuted = data.copy()
            if level == "within_group":
                values = permuted[feature].to_numpy(copy=True)
                for _, idx in permuted.groupby(model.group_col, sort=False, dropna=False).indices.items():
                    idx = np.asarray(idx, dtype=int)
                    values[idx] = values[idx][rng.permutation(len(idx))]
                permuted[feature] = values
            else:
                grouped = permuted.groupby(model.group_col, sort=False, dropna=False)[feature].first()
                shuffled = grouped.to_numpy()[rng.permutation(len(grouped))]
                mapping = dict(zip(grouped.index.astype(str), shuffled))
                permuted[feature] = [mapping[str(g)] for g in permuted[model.group_col]]
            prediction = predict_grouped_mixed_boosting(model, permuted, mode=prediction_mode)
            losses.append(float(np.mean((y - prediction) ** 2) - baseline_mse))
        rows.append(
            {
                "feature": feature,
                "feature_level": level,
                "baseline_mse": baseline_mse,
                "importance_mean_mse_increase": float(np.mean(losses)),
                "importance_sd": float(np.std(losses, ddof=1)) if len(losses) > 1 else 0.0,
                "repeats": repeats,
                "prediction_mode": prediction_mode,
            }
        )
    return pd.DataFrame(rows)


def _tree_payload(node: _TreeNode) -> dict:
    if node.feature is None:
        return {"value": node.value}
    return {
        "value": node.value,
        "feature": node.feature,
        "threshold": node.threshold,
        "left": _tree_payload(node.left),
        "right": _tree_payload(node.right),
    }


def create_grouped_mixed_boosting_certificate(model: GroupedMixedBoostingResult) -> dict:
    if not isinstance(model, GroupedMixedBoostingResult):
        raise TypeError("`model` must be returned by fit_grouped_mixed_boosting().")
    payload = {
        "schema_version": model.schema_version,
        "outcome_col": model.outcome_col,
        "group_col": model.group_col,
        "feature_cols": list(model.feature_cols),
        "intercept": model.intercept,
        "trees": [
            {"learning_rate": tree.learning_rate, "root": _tree_payload(tree.root)} for tree in model.trees
        ],
        "group_levels": list(model.group_levels),
        "group_effects": list(model.group_effects),
        "random_intercept_variance": model.random_intercept_variance,
        "residual_variance": model.residual_variance,
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
    }
    return {"payload": payload, "sha256": _canonical_digest(payload)}


def validate_grouped_mixed_boosting_certificate(model: GroupedMixedBoostingResult, certificate) -> bool:
    if not isinstance(certificate, Mapping) or set(certificate) != {"payload", "sha256"}:
        return False
    try:
        expected = create_grouped_mixed_boosting_certificate(model)
        supplied_payload = dict(certificate["payload"])
        supplied_digest = _canonical_digest(supplied_payload)
    except (TypeError, ValueError):
        return False
    return supplied_payload == expected["payload"] and supplied_digest == certificate["sha256"]


__all__ = [
    "GroupedMixedBoostingResult",
    "fit_grouped_mixed_boosting",
    "predict_grouped_mixed_boosting",
    "grouped_cross_validation_mixed_boosting",
    "group_aware_permutation_importance",
    "create_grouped_mixed_boosting_certificate",
    "validate_grouped_mixed_boosting_certificate",
]
