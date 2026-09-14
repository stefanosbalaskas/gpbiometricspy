from __future__ import annotations

from dataclasses import FrozenInstanceError
import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import grouped_ordinal_boosting as go
from gpbiometricspy import grouped_ordinal_core as core


def frame(seed=7, groups=8, rows=16):
    rng = np.random.default_rng(seed)
    records = []
    group_effects = np.linspace(-1.1, 1.1, groups)
    group_level = np.linspace(-2.0, 2.0, groups)
    for g in range(groups):
        for _ in range(rows):
            x = rng.uniform(-2.5, 2.5)
            z = rng.normal()
            latent = 1.25 * np.sin(1.2 * x) + 0.35 * z + group_effects[g] + rng.logistic(scale=0.65)
            y = "low" if latent < -0.6 else "mid" if latent < 0.7 else "high"
            records.append({"group": f"G{g}", "x": x, "z": z, "gfeat": group_level[g], "y": y})
    data = pd.DataFrame(records)
    # Deterministically guarantee every category in small test frames.
    data.loc[data.index[0], "y"] = "low"
    data.loc[data.index[1], "y"] = "mid"
    data.loc[data.index[2], "y"] = "high"
    return data


def fit_default(data=None, **kwargs):
    data = frame() if data is None else data
    params = dict(
        category_order=["low", "mid", "high"],
        n_estimators=8,
        learning_rate=0.12,
        max_depth=2,
        min_samples_leaf=3,
        max_iterations=4,
        tolerance=1e-4,
    )
    params.update(kwargs)
    return go.fit_grouped_ordinal_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x", "z", "gfeat"],
        **params,
    )


def test_group_offset_failure_and_shrinkage_branches(monkeypatch):
    y = np.array([0, 1, 2, 1])
    fixed = np.zeros(4)
    theta = np.array([-0.5, 0.5])
    monkeypatch.setattr(core, "minimize_scalar", lambda *a, **k: SimpleNamespace(success=False, x=0.0))
    with pytest.raises(RuntimeError, match="offset"):
        go._group_offset_mode(y, fixed, theta)

    monkeypatch.setattr(core, "minimize_scalar", lambda *a, **k: SimpleNamespace(success=True, x=np.nan))
    with pytest.raises(RuntimeError, match="offset"):
        go._group_offset_mode(y, fixed, theta)

    groups = np.array(["a", "a", "b", "b", "c", "c", "d", "d"], object)
    yy = np.tile([0, 2], 4)
    ff = np.zeros(8)
    calls = iter([(0.0, 10.0), (0.0, 10.0), (0.0, 10.0), (0.0, 10.0)])
    monkeypatch.setattr(core, "_group_offset_mode", lambda *a, **k: next(calls))
    levels, effects, tau2 = go._random_intercept_shrinkage(yy, ff, groups, theta)
    assert levels == ("a", "b", "c", "d") and tau2 == 0 and effects == pytest.approx(np.zeros(4))

    calls = iter([(-2.0, 0.01), (-0.5, 0.01), (0.5, 0.01), (2.0, 0.01)])
    monkeypatch.setattr(core, "_group_offset_mode", lambda *a, **k: next(calls))
    _, effects, tau2 = go._random_intercept_shrinkage(yy, ff, groups, theta)
    assert tau2 > 0 and np.max(np.abs(effects)) > 0


def test_group_offset_mode_information_fallback(monkeypatch):
    y = np.array([0, 1, 2, 1])
    fixed = np.zeros(4)
    theta = np.array([-0.5, 0.5])
    # Constant objective creates zero observed information and exercises the large-variance fallback.
    monkeypatch.setattr(core, "_ordinal_log_loss", lambda *a, **k: 1.0)
    mode, variance = go._group_offset_mode(y, fixed, theta)
    assert np.isfinite(mode) and variance == 1e8


def test_cross_validation_group_holdout_and_guardrails(monkeypatch):
    data = frame(groups=8, rows=10)
    kwargs = dict(n_estimators=3, learning_rate=0.1, min_samples_leaf=2, max_iterations=2, tolerance=1e-3)
    cv1 = go.grouped_cross_validation_ordinal_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x", "z", "gfeat"],
        category_order=["low", "mid", "high"],
        n_splits=2,
        seed=9,
        **kwargs,
    )
    cv2 = go.grouped_cross_validation_ordinal_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x", "z", "gfeat"],
        category_order=["low", "mid", "high"],
        n_splits=2,
        seed=9,
        **kwargs,
    )
    assert cv1["oof_probabilities"] == pytest.approx(cv2["oof_probabilities"])
    assert np.isfinite(cv1["oof_probabilities"]).all()
    assert cv1["prediction_mode"] == "marginal_unseen_group"
    assert cv1["ordinal_log_loss"] > 0 and cv1["ranked_probability_score"] >= 0
    assert cv1["mean_absolute_category_error"] >= 0
    held = [g for fold in cv1["folds"] for g in fold]
    assert sorted(held) == sorted(data.group.unique())
    with pytest.raises(ValueError, match="integer"):
        go.grouped_cross_validation_ordinal_boosting(
            data,
            outcome_col="y",
            group_col="group",
            feature_cols=["x"],
            category_order=["low", "mid", "high"],
            n_splits=2.5,
        )
    five = frame(groups=5, rows=8)
    with pytest.raises(ValueError, match="retain at least four"):
        go.grouped_cross_validation_ordinal_boosting(
            five,
            outcome_col="y",
            group_col="group",
            feature_cols=["x"],
            category_order=["low", "mid", "high"],
            n_splits=2,
            n_estimators=2,
            min_samples_leaf=2,
            max_iterations=1,
        )

    original = go.predict_grouped_ordinal_boosting
    def bad_predict(model, test, **kwargs):
        out = original(model, test, **kwargs)
        out[0, 0] = np.nan
        return out
    monkeypatch.setattr(go, "predict_grouped_ordinal_boosting", bad_predict)
    with pytest.raises(RuntimeError, match="finite probability"):
        go.grouped_cross_validation_ordinal_boosting(
            data,
            outcome_col="y",
            group_col="group",
            feature_cols=["x"],
            category_order=["low", "mid", "high"],
            n_splits=2,
            n_estimators=2,
            min_samples_leaf=2,
            max_iterations=1,
        )


def test_permutation_importance_group_aware_and_guardrails():
    data = frame(groups=8, rows=10)
    model = fit_default(data, n_estimators=4, max_iterations=2)
    importance = go.group_aware_ordinal_permutation_importance(model, data, repeats=3, seed=12)
    levels = dict(zip(importance.feature, importance.feature_level))
    assert levels["x"] == "within_group"
    assert levels["z"] == "within_group"
    assert levels["gfeat"] == "group"
    assert (importance.repeats == 3).all()
    one = go.group_aware_ordinal_permutation_importance(model, data, repeats=1, seed=2, prediction_mode="marginal")
    assert (one.importance_sd == 0).all()
    with pytest.raises(TypeError, match="model"):
        go.group_aware_ordinal_permutation_importance(object(), data)
    with pytest.raises(TypeError, match="DataFrame"):
        go.group_aware_ordinal_permutation_importance(model, [])
    with pytest.raises(ValueError, match="Outcome column"):
        go.group_aware_ordinal_permutation_importance(model, data.drop(columns="y"))
    with pytest.raises(ValueError, match="Group column"):
        go.group_aware_ordinal_permutation_importance(model, data.drop(columns="group"))
    with pytest.raises(ValueError, match="prediction_mode"):
        go.group_aware_ordinal_permutation_importance(model, data, prediction_mode="bad")
    with pytest.raises(ValueError):
        go.group_aware_ordinal_permutation_importance(model, data, repeats=0)
    missing = data.drop(columns="x")
    with pytest.raises(ValueError, match="Missing required feature"):
        go.group_aware_ordinal_permutation_importance(model, missing)


def test_model_outcome_encoding_guardrails():
    data = frame()
    model = fit_default(data)
    missing = data["y"].copy()
    missing.iloc[0] = None
    with pytest.raises(ValueError, match="must not be missing"):
        go._encode_with_model(model, missing)
    unknown = data["y"].copy()
    unknown.iloc[0] = "other"
    with pytest.raises(ValueError, match="absent"):
        go._encode_with_model(model, unknown)


def test_certificate_is_deterministic_key_order_independent_and_tamper_evident():
    model = fit_default(frame(groups=6, rows=10), n_estimators=4, max_iterations=2)
    cert = go.create_grouped_ordinal_boosting_certificate(model)
    assert cert == go.create_grouped_ordinal_boosting_certificate(model)
    assert go.validate_grouped_ordinal_boosting_certificate(model, cert)
    reordered = {"sha256": cert["sha256"], "payload": dict(reversed(list(cert["payload"].items())))}
    assert go.validate_grouped_ordinal_boosting_certificate(model, reordered)
    tampered = copy.deepcopy(cert)
    tampered["payload"]["thresholds"][0] += 1
    assert not go.validate_grouped_ordinal_boosting_certificate(model, tampered)
    badsha = copy.deepcopy(cert)
    badsha["sha256"] = "0" * 64
    assert not go.validate_grouped_ordinal_boosting_certificate(model, badsha)
    assert not go.validate_grouped_ordinal_boosting_certificate(object(), cert)
    assert not go.validate_grouped_ordinal_boosting_certificate(model, [])
    assert not go.validate_grouped_ordinal_boosting_certificate(model, {})
    assert not go.validate_grouped_ordinal_boosting_certificate(model, {"payload": [], "sha256": "x"})
    with pytest.raises(TypeError, match="model"):
        go.create_grouped_ordinal_boosting_certificate(object())


def test_tree_payload_leaf_and_split():
    from gpbiometricspy.grouped_mixed_boosting import _TreeNode
    leaf = _TreeNode(value=1.0)
    assert go._tree_payload(leaf) == {"value": 1.0}
    split = _TreeNode(value=0.0, feature=0, threshold=0.5, left=leaf, right=_TreeNode(value=-1.0))
    payload = go._tree_payload(split)
    assert payload["feature"] == 0 and payload["left"]["value"] == 1.0


def test_known_truth_group_heterogeneity_is_recovered_and_improves_rps():
    data = frame(seed=11, groups=10, rows=25)
    model = fit_default(
        data,
        n_estimators=15,
        learning_rate=0.10,
        min_samples_leaf=4,
        max_iterations=6,
    )
    expected = np.linspace(-1.1, 1.1, 10)
    effect_map = dict(zip(model.group_levels, model.group_effects))
    estimated = np.asarray([effect_map[f"G{index}"] for index in range(10)], dtype=float)
    assert np.corrcoef(expected, estimated)[0, 1] > 0.85
    y = data.y.map({"low": 0, "mid": 1, "high": 2}).to_numpy()
    class_frequency = np.bincount(y, minlength=3) / len(y)
    null_probability = np.tile(class_frequency, (len(y), 1))
    fitted_probability = go.predict_grouped_ordinal_boosting(model, data, mode="conditional")
    assert go._ranked_probability_score(y, fitted_probability) < go._ranked_probability_score(y, null_probability)
