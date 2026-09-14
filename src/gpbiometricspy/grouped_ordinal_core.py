from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit

from .grouped_mixed_boosting import (
    _BoostedTree,
    _canonical_digest,
    _fit_tree,
    _group_folds,
    _hash_array,
    _nonempty_string,
    _positive_number,
    _predict_node,
    _prediction_matrix,
    _seed,
)

_SCHEMA_VERSION = "gpbiometricspy-grouped-ordinal-boosting-v1"
_MIN_THRESHOLD_GAP = 1e-4
_PROB_EPS = 1e-12


@dataclass(frozen=True)
class GroupedOrdinalBoostingResult:
    outcome_col: str
    group_col: str
    feature_cols: tuple[str, ...]
    category_order: tuple[object, ...]
    thresholds: tuple[float, ...]
    trees: tuple[_BoostedTree, ...]
    group_levels: tuple[str, ...]
    group_effects: tuple[float, ...]
    random_intercept_variance: float
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
    training_ordinal_log_loss: float
    training_ranked_probability_score: float
    schema_version: str = _SCHEMA_VERSION


def _normalize_label(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Ordinal category labels must be strings or finite numeric scalars, excluding booleans.")
    if isinstance(value, float) and not np.isfinite(value):
        raise ValueError("Ordinal category labels must be finite.")
    return value


def _resolve_category_order(series: pd.Series, category_order: Sequence[object] | None):
    if category_order is None:
        if not isinstance(series.dtype, pd.CategoricalDtype) or not series.dtype.ordered:
            raise ValueError("`category_order` is required unless the outcome is an ordered pandas categorical.")
        categories = tuple(_normalize_label(value) for value in series.cat.categories)
    else:
        if isinstance(category_order, (str, bytes)) or not isinstance(category_order, Sequence):
            raise ValueError("`category_order` must be a sequence of ordered category labels.")
        categories = tuple(_normalize_label(value) for value in category_order)
    if len(categories) < 3:
        raise ValueError("At least three ordered outcome categories are required.")
    if len(set(categories)) != len(categories):
        raise ValueError("`category_order` must contain unique category labels.")
    if series.isna().any():
        raise ValueError("Ordinal outcome values must not be missing.")
    normalized_values = [_normalize_label(value) for value in series.astype(object).tolist()]
    mapping = {value: index for index, value in enumerate(categories)}
    if any(value not in mapping for value in normalized_values):
        raise ValueError("Every observed ordinal outcome must appear in `category_order`.")
    codes = np.asarray([mapping[value] for value in normalized_values], dtype=int)
    counts = np.bincount(codes, minlength=len(categories))
    if np.any(counts == 0):
        raise ValueError("Every category in `category_order` must be observed at least once in training data.")
    return categories, codes


def _validate_training_frame(
    data,
    outcome_col: str,
    group_col: str,
    feature_cols: Sequence[str],
    category_order: Sequence[object] | None,
):
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
    X = data.loc[:, features].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.all(np.isfinite(X)):
        raise ValueError("Feature values must all be finite numeric values.")
    groups_raw = data[group_col].astype(object).to_numpy()
    if pd.isna(groups_raw).any():
        raise ValueError("Group identifiers must not be missing.")
    unique_raw = pd.unique(groups_raw)
    normalized = tuple(str(value) for value in unique_raw)
    if len(set(normalized)) != len(normalized):
        raise ValueError("Group identifiers must remain unique after string normalization.")
    groups = np.asarray([str(value) for value in groups_raw], dtype=object)
    if len(normalized) < 4:
        raise ValueError("At least four distinct groups are required.")
    categories, y = _resolve_category_order(data[outcome_col], category_order)
    return y, X, groups, features, outcome_col, group_col, categories


def _initial_thresholds(y: np.ndarray, n_categories: int) -> np.ndarray:
    cumulative = np.asarray([np.mean(y <= level) for level in range(n_categories - 1)], dtype=float)
    cumulative = np.clip(cumulative, 1e-6, 1 - 1e-6)
    thresholds = np.log(cumulative / (1 - cumulative))
    return np.asarray(thresholds, dtype=float)


def _thresholds_from_raw(raw: np.ndarray) -> np.ndarray:
    raw = np.asarray(raw, dtype=float)
    thresholds = np.empty_like(raw)
    thresholds[0] = raw[0]
    if len(raw) > 1:
        increments = np.exp(np.clip(raw[1:], -12.0, 12.0)) + _MIN_THRESHOLD_GAP
        thresholds[1:] = thresholds[0] + np.cumsum(increments)
    return thresholds


def _raw_from_thresholds(thresholds: np.ndarray) -> np.ndarray:
    thresholds = np.asarray(thresholds, dtype=float)
    raw = np.empty_like(thresholds)
    raw[0] = thresholds[0]
    if len(thresholds) > 1:
        increments = np.maximum(np.diff(thresholds) - _MIN_THRESHOLD_GAP, 1e-8)
        raw[1:] = np.log(increments)
    return raw


def _ordinal_probabilities(linear_predictor: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    eta = np.asarray(linear_predictor, dtype=float)
    theta = np.asarray(thresholds, dtype=float)
    cumulative = expit(theta[None, :] - eta[:, None])
    probabilities = np.empty((len(eta), len(theta) + 1), dtype=float)
    probabilities[:, 0] = cumulative[:, 0]
    if len(theta) > 1:
        probabilities[:, 1:-1] = cumulative[:, 1:] - cumulative[:, :-1]
    probabilities[:, -1] = 1.0 - cumulative[:, -1]
    probabilities = np.clip(probabilities, _PROB_EPS, 1.0)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    return probabilities


def _ordinal_log_loss(y: np.ndarray, probabilities: np.ndarray) -> float:
    chosen = probabilities[np.arange(len(y)), y]
    return float(-np.mean(np.log(np.clip(chosen, _PROB_EPS, 1.0))))


def _ranked_probability_score(y: np.ndarray, probabilities: np.ndarray) -> float:
    cumulative = np.cumsum(probabilities, axis=1)[:, :-1]
    levels = np.arange(probabilities.shape[1] - 1)[None, :]
    observed = (y[:, None] <= levels).astype(float)
    return float(np.mean(np.sum((cumulative - observed) ** 2, axis=1) / (probabilities.shape[1] - 1)))


def _ordinal_score(y: np.ndarray, linear_predictor: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    eta = np.asarray(linear_predictor, dtype=float)
    theta = np.asarray(thresholds, dtype=float)
    n_categories = len(theta) + 1
    score = np.empty(len(y), dtype=float)
    for index, category in enumerate(y):
        lower = expit(theta[category - 1] - eta[index]) if category > 0 else 0.0
        upper = expit(theta[category] - eta[index]) if category < n_categories - 1 else 1.0
        lower_slope = lower * (1.0 - lower)
        upper_slope = upper * (1.0 - upper)
        probability = max(upper - lower, _PROB_EPS)
        score[index] = (lower_slope - upper_slope) / probability
    return score


def _fit_ordinal_booster(
    X: np.ndarray,
    y: np.ndarray,
    thresholds: np.ndarray,
    group_effect: np.ndarray,
    *,
    n_estimators: int,
    learning_rate: float,
    max_depth: int,
    min_samples_leaf: int,
):
    prediction = np.zeros(len(y), dtype=float)
    trees: list[_BoostedTree] = []
    for _ in range(n_estimators):
        score = _ordinal_score(y, prediction + group_effect, thresholds)
        root = _fit_tree(X, score, max_depth=max_depth, min_samples_leaf=min_samples_leaf)
        prediction += learning_rate * _predict_node(root, X)
        trees.append(_BoostedTree(learning_rate=learning_rate, root=root))
    return tuple(trees), prediction


def _predict_booster(trees: tuple[_BoostedTree, ...], X: np.ndarray) -> np.ndarray:
    prediction = np.zeros(X.shape[0], dtype=float)
    for tree in trees:
        prediction += tree.learning_rate * _predict_node(tree.root, X)
    return prediction


def _optimize_thresholds(y: np.ndarray, linear_predictor: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    initial = _raw_from_thresholds(thresholds)

    def objective(raw):
        candidate = _thresholds_from_raw(raw)
        probabilities = _ordinal_probabilities(linear_predictor, candidate)
        return _ordinal_log_loss(y, probabilities)

    bounds = [(-12.0, 12.0)] + [(-12.0, 8.0)] * (len(initial) - 1)
    result = minimize(objective, initial, method="L-BFGS-B", bounds=bounds)
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError("Ordinal threshold optimization failed to produce a finite converged solution.")
    optimized = _thresholds_from_raw(result.x)
    if np.any(np.diff(optimized) <= 0):
        raise RuntimeError("Ordinal threshold optimization violated threshold ordering.")
    return optimized


def _group_offset_mode(y: np.ndarray, fixed_prediction: np.ndarray, thresholds: np.ndarray):
    def objective(offset):
        probabilities = _ordinal_probabilities(fixed_prediction + float(offset), thresholds)
        return _ordinal_log_loss(y, probabilities) * len(y)

    result = minimize_scalar(objective, bounds=(-8.0, 8.0), method="bounded", options={"xatol": 1e-7})
    if not result.success or not np.isfinite(result.x):
        raise RuntimeError("Group ordinal offset optimization failed.")
    mode = float(result.x)
    step = 1e-3
    center = objective(mode)
    information = (objective(mode + step) - 2.0 * center + objective(mode - step)) / (step**2)
    variance = 1.0 / information if np.isfinite(information) and information > 1e-8 else 1e8
    return mode, float(variance)


def _random_intercept_shrinkage(
    y: np.ndarray,
    fixed_prediction: np.ndarray,
    groups: np.ndarray,
    thresholds: np.ndarray,
):
    levels = pd.unique(groups)
    counts = np.asarray([np.sum(groups == level) for level in levels], dtype=float)
    modes = []
    variances = []
    for level in levels:
        mask = groups == level
        mode, variance = _group_offset_mode(y[mask], fixed_prediction[mask], thresholds)
        modes.append(mode)
        variances.append(variance)
    modes = np.asarray(modes, dtype=float)
    variances = np.asarray(variances, dtype=float)
    grand = float(np.average(modes, weights=counts))
    centered = modes - grand
    between = float(np.average(centered**2, weights=counts))
    sampling = float(np.average(variances, weights=counts))
    tau2 = max(between - sampling, 0.0)
    if tau2 == 0.0:
        effects = np.zeros_like(centered)
    else:
        effects = tau2 / (tau2 + variances) * centered
    return tuple(str(level) for level in levels), effects, float(tau2)


def _group_effect_vector(groups: np.ndarray, levels: tuple[str, ...], effects: tuple[float, ...]) -> np.ndarray:
    mapping = dict(zip(levels, effects))
    return np.asarray([mapping.get(str(group), 0.0) for group in groups], dtype=float)
