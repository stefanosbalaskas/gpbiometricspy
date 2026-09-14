from __future__ import annotations

from dataclasses import FrozenInstanceError
import copy

import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import grouped_mixed_boosting as gm


def frame(seed=3, groups=8, rows=18):
    rng = np.random.default_rng(seed)
    records = []
    group_effects = np.linspace(-1.4, 1.4, groups)
    group_level = np.linspace(-2.0, 2.0, groups)
    for g in range(groups):
        for _ in range(rows):
            x = rng.uniform(-2.5, 2.5)
            z = rng.normal()
            y = 1.2 * np.sin(1.4 * x) + 0.35 * z + group_effects[g] + rng.normal(0, 0.18)
            records.append({"group": f"G{g}", "x": x, "z": z, "gfeat": group_level[g], "y": y})
    return pd.DataFrame(records)


def fit_default(data=None, **kwargs):
    data = frame() if data is None else data
    params = dict(
        n_estimators=18,
        learning_rate=0.12,
        max_depth=2,
        min_samples_leaf=4,
        max_iterations=12,
        tolerance=1e-4,
    )
    params.update(kwargs)
    return gm.fit_grouped_mixed_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x", "z", "gfeat"],
        **params,
    )


def test_fit_known_structure_is_deterministic_and_captures_group_variance():
    data = frame()
    m1 = fit_default(data)
    m2 = fit_default(data)
    assert m1 == m2
    assert m1.training_rows == len(data)
    assert m1.training_groups == data.group.nunique()
    assert m1.random_intercept_variance > 0
    assert m1.residual_variance >= 0
    assert len(m1.trees) == 18
    assert len(m1.group_effects) == 8
    assert len(m1.training_outcome_sha256) == 64
    assert len(m1.training_feature_sha256) == 64
    pred = gm.predict_grouped_mixed_boosting(m1, data, mode="conditional")
    intercept_mse = float(np.mean((data.y - data.y.mean()) ** 2))
    model_mse = float(np.mean((data.y - pred) ** 2))
    assert model_mse < 0.35 * intercept_mse
    with pytest.raises(FrozenInstanceError):
        m1.intercept = 0


def test_marginal_and_conditional_prediction_have_explicit_unseen_semantics():
    data = frame()
    model = fit_default(data)
    seen = data.iloc[:6].copy()
    marginal = gm.predict_grouped_mixed_boosting(model, seen, mode="marginal")
    conditional = gm.predict_grouped_mixed_boosting(model, seen, mode="conditional")
    assert not np.allclose(marginal, conditional)

    unseen = seen.copy()
    unseen["group"] = "NEW"
    assert gm.predict_grouped_mixed_boosting(model, unseen, mode="conditional") == pytest.approx(
        gm.predict_grouped_mixed_boosting(model, unseen, mode="marginal")
    )
    with pytest.raises(ValueError, match="unseen groups"):
        gm.predict_grouped_mixed_boosting(model, unseen, mode="conditional", unseen_group="error")
    with pytest.raises(ValueError, match="requires group"):
        gm.predict_grouped_mixed_boosting(model, seen.drop(columns="group"), mode="conditional")


def test_prediction_guardrails():
    data = frame()
    model = fit_default(data)
    with pytest.raises(TypeError, match="model"):
        gm.predict_grouped_mixed_boosting(object(), data)
    with pytest.raises(ValueError, match="mode"):
        gm.predict_grouped_mixed_boosting(model, data, mode="bad")
    with pytest.raises(ValueError, match="unseen_group"):
        gm.predict_grouped_mixed_boosting(model, data, unseen_group="bad")
    with pytest.raises(TypeError, match="DataFrame"):
        gm.predict_grouped_mixed_boosting(model, [])
    with pytest.raises(ValueError, match="Missing required feature"):
        gm.predict_grouped_mixed_boosting(model, data.drop(columns="x"))
    bad = data.copy()
    bad.loc[0, "x"] = np.nan
    with pytest.raises(ValueError, match="finite numeric"):
        gm.predict_grouped_mixed_boosting(model, bad)


def test_training_frame_and_hyperparameter_guardrails():
    data = frame()
    base = dict(data=data, outcome_col="y", group_col="group", feature_cols=["x", "z"])
    with pytest.raises(TypeError, match="DataFrame"):
        gm.fit_grouped_mixed_boosting([], outcome_col="y", group_col="g", feature_cols=["x"])
    with pytest.raises(ValueError, match="non-empty string"):
        gm.fit_grouped_mixed_boosting(data, outcome_col=" ", group_col="group", feature_cols=["x"])
    with pytest.raises(ValueError, match="distinct"):
        gm.fit_grouped_mixed_boosting(data, outcome_col="y", group_col="y", feature_cols=["x"])
    with pytest.raises(ValueError, match="non-empty sequence"):
        gm.fit_grouped_mixed_boosting(data, outcome_col="y", group_col="group", feature_cols=[])
    with pytest.raises(ValueError, match="non-empty sequence"):
        gm.fit_grouped_mixed_boosting(data, outcome_col="y", group_col="group", feature_cols="x")
    with pytest.raises(ValueError, match="duplicates"):
        gm.fit_grouped_mixed_boosting(data, outcome_col="y", group_col="group", feature_cols=["x", "x"])
    with pytest.raises(ValueError, match="cannot also"):
        gm.fit_grouped_mixed_boosting(data, outcome_col="y", group_col="group", feature_cols=["y"])
    with pytest.raises(ValueError, match="Missing required"):
        gm.fit_grouped_mixed_boosting(data, outcome_col="missing", group_col="group", feature_cols=["x"])
    with pytest.raises(ValueError, match="at least one row"):
        gm.fit_grouped_mixed_boosting(data.iloc[0:0], outcome_col="y", group_col="group", feature_cols=["x"])
    bad_y = data.copy()
    bad_y.loc[0, "y"] = np.nan
    with pytest.raises(ValueError, match="Outcome values"):
        gm.fit_grouped_mixed_boosting(bad_y, outcome_col="y", group_col="group", feature_cols=["x"])
    bad_x = data.copy()
    bad_x.loc[0, "x"] = np.inf
    with pytest.raises(ValueError, match="Feature values"):
        gm.fit_grouped_mixed_boosting(bad_x, outcome_col="y", group_col="group", feature_cols=["x"])
    bad_g = data.copy()
    bad_g.loc[0, "group"] = None
    with pytest.raises(ValueError, match="Group identifiers"):
        gm.fit_grouped_mixed_boosting(bad_g, outcome_col="y", group_col="group", feature_cols=["x"])
    few = data[data.group.isin(["G0", "G1", "G2"])]
    with pytest.raises(ValueError, match="four distinct"):
        gm.fit_grouped_mixed_boosting(few, outcome_col="y", group_col="group", feature_cols=["x"])
    for name, value in [
        ("n_estimators", 0),
        ("learning_rate", 0),
        ("max_depth", 0),
        ("min_samples_leaf", 0),
        ("max_iterations", 0),
        ("tolerance", 0),
    ]:
        with pytest.raises(ValueError):
            gm.fit_grouped_mixed_boosting(**base, **{name: value})
    with pytest.raises(ValueError, match="integer"):
        gm.fit_grouped_mixed_boosting(**base, n_estimators=2.5)
    with pytest.raises(ValueError, match="not exceed"):
        gm.fit_grouped_mixed_boosting(**base, learning_rate=1.1)
    with pytest.raises(ValueError, match="limited to 3"):
        gm.fit_grouped_mixed_boosting(**base, max_depth=4)
    with pytest.raises(ValueError, match="too large"):
        gm.fit_grouped_mixed_boosting(**base, min_samples_leaf=len(data))


def test_tree_helpers_cover_leaf_no_gain_and_tie_paths():
    X = np.array([[0.], [1.], [2.], [3.]])
    y = np.array([1., 1., 1., 1.])
    tree = gm._fit_tree(X, y, max_depth=2, min_samples_leaf=1)
    assert tree.feature is None
    assert gm._predict_node(tree, X) == pytest.approx([1, 1, 1, 1])
    assert gm._best_split(X, y, np.arange(4), 3) is None
    assert gm._sse(np.array([])) == 0


def test_random_intercept_helper_zero_between_variance_and_group_vector_unknown():
    groups = np.array(["a", "a", "b", "b", "c", "c", "d", "d"], object)
    residual = np.array([1, -1, 1, -1, 1, -1, 1, -1.], float)
    labels, effects, sb, se = gm._random_intercept_blup(residual, groups)
    assert sb == pytest.approx(0)
    assert se > 0
    assert effects == pytest.approx(np.zeros(4))
    vec = gm._group_effect_vector(np.array(["a", "unknown"], object), tuple(map(str, labels)), tuple(effects))
    assert vec == pytest.approx([0, 0])


def test_grouped_cross_validation_holds_out_whole_groups_and_is_deterministic():
    data = frame(groups=8, rows=12)
    kwargs = dict(
        n_estimators=10,
        learning_rate=.12,
        max_depth=2,
        min_samples_leaf=3,
        max_iterations=8,
        tolerance=1e-4,
    )
    cv1 = gm.grouped_cross_validation_mixed_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x", "z", "gfeat"],
        n_splits=4,
        seed=7,
        **kwargs,
    )
    cv2 = gm.grouped_cross_validation_mixed_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x", "z", "gfeat"],
        n_splits=4,
        seed=7,
        **kwargs,
    )
    assert cv1["oof_prediction"] == pytest.approx(cv2["oof_prediction"])
    assert np.isfinite(cv1["oof_prediction"]).all()
    assert cv1["prediction_mode"] == "marginal_unseen_group"
    assert cv1["rmse"] > 0
    held = []
    for groups in cv1["folds"].held_out_groups:
        held.extend(groups)
    assert sorted(held) == sorted(data.group.unique())
    assert len(held) == len(set(held))


def test_group_fold_guardrails_and_balancing():
    groups = np.array(["a"] * 8 + ["b"] * 5 + ["c"] * 4 + ["d"] * 3 + ["e"] * 2, object)
    folds = gm._group_folds(groups, 3, 1)
    assert sum(len(f) for f in folds) == 5
    with pytest.raises(ValueError, match="between 2"):
        gm._group_folds(groups, 1, 1)
    with pytest.raises(ValueError, match="between 2"):
        gm._group_folds(groups, 6, 1)


def test_group_aware_permutation_distinguishes_within_and_group_predictors():
    data = frame(groups=8, rows=15)
    model = fit_default(data)
    importance = gm.group_aware_permutation_importance(
        model, data, repeats=4, seed=11, prediction_mode="conditional"
    )
    levels = dict(zip(importance.feature, importance.feature_level))
    assert levels["x"] == "within_group"
    assert levels["z"] == "within_group"
    assert levels["gfeat"] == "group"
    assert (importance.importance_mean_mse_increase > -1e-10).all()
    assert (importance.repeats == 4).all()
    one = gm.group_aware_permutation_importance(model, data, repeats=1, seed=2)
    assert (one.importance_sd == 0).all()


def test_permutation_importance_guardrails():
    data = frame()
    model = fit_default(data)
    with pytest.raises(TypeError, match="model"):
        gm.group_aware_permutation_importance(object(), data)
    with pytest.raises(TypeError, match="DataFrame"):
        gm.group_aware_permutation_importance(model, [])
    with pytest.raises(ValueError, match="Outcome column"):
        gm.group_aware_permutation_importance(model, data.drop(columns="y"))
    with pytest.raises(ValueError, match="Group column"):
        gm.group_aware_permutation_importance(model, data.drop(columns="group"))
    bad = data.copy()
    bad.loc[0, "y"] = np.nan
    with pytest.raises(ValueError, match="Outcome values"):
        gm.group_aware_permutation_importance(model, bad)
    with pytest.raises(ValueError):
        gm.group_aware_permutation_importance(model, data, repeats=0)
    with pytest.raises(ValueError, match="prediction_mode"):
        gm.group_aware_permutation_importance(model, data, prediction_mode="bad")


def test_certificate_is_deterministic_key_order_independent_and_tamper_evident():
    model = fit_default(frame(groups=6, rows=10))
    cert = gm.create_grouped_mixed_boosting_certificate(model)
    assert cert == gm.create_grouped_mixed_boosting_certificate(model)
    assert gm.validate_grouped_mixed_boosting_certificate(model, cert)
    reordered = {"sha256": cert["sha256"], "payload": dict(reversed(list(cert["payload"].items())))}
    assert gm.validate_grouped_mixed_boosting_certificate(model, reordered)
    tampered = copy.deepcopy(cert)
    tampered["payload"]["intercept"] += 1
    assert not gm.validate_grouped_mixed_boosting_certificate(model, tampered)
    badsha = copy.deepcopy(cert)
    badsha["sha256"] = "0" * 64
    assert not gm.validate_grouped_mixed_boosting_certificate(model, badsha)
    assert not gm.validate_grouped_mixed_boosting_certificate(model, {})
    assert not gm.validate_grouped_mixed_boosting_certificate(model, {"payload": [], "sha256": "x"})
    assert not gm.validate_grouped_mixed_boosting_certificate(object(), cert)
    with pytest.raises(TypeError):
        gm.create_grouped_mixed_boosting_certificate(object())


def test_nonconvergence_is_reported_not_hidden():
    model = fit_default(frame(), max_iterations=1)
    assert model.n_iterations == 1
    assert model.converged is False


def test_cross_validation_runtime_invariant_failure_branch(monkeypatch):
    data = frame(groups=6, rows=8)
    original = gm.predict_grouped_mixed_boosting

    def bad_predict(model, test, mode="marginal", **kwargs):
        out = original(model, test, mode=mode, **kwargs)
        out[0] = np.nan
        return out

    monkeypatch.setattr(gm, "predict_grouped_mixed_boosting", bad_predict)
    with pytest.raises(RuntimeError, match="one finite OOF"):
        gm.grouped_cross_validation_mixed_boosting(
            data,
            outcome_col="y",
            group_col="group",
            feature_cols=["x", "z"],
            n_splits=3,
            n_estimators=3,
            min_samples_leaf=2,
            max_iterations=2,
        )


def test_misc_private_validation_branches():
    with pytest.raises(ValueError, match="non-empty string"):
        gm._nonempty_string(None, "x")
    with pytest.raises(ValueError, match="finite"):
        gm._positive_number(np.inf, "x")
    assert gm._hash_array(np.array([1., 2.])) != gm._hash_array(np.array([1., 3.]))


def test_convergence_is_reported_when_tolerance_is_met():
    model = fit_default(frame(), tolerance=1e6, max_iterations=3)
    assert model.converged is True
    assert model.n_iterations == 1


def test_group_identifier_normalization_and_cv_design_guardrails():
    data = frame(groups=6, rows=6)
    collision = data.copy()
    collision["group"] = collision["group"].astype(object)
    collision.loc[collision.group == "G0", "group"] = 1
    collision.loc[collision.group == "G1", "group"] = "1"
    with pytest.raises(ValueError, match="unique after string normalization"):
        gm.fit_grouped_mixed_boosting(collision, outcome_col="y", group_col="group", feature_cols=["x"])
    with pytest.raises(ValueError, match="n_splits.*integer"):
        gm.grouped_cross_validation_mixed_boosting(
            data, outcome_col="y", group_col="group", feature_cols=["x"], n_splits=2.5
        )
    with pytest.raises(ValueError, match="non-negative integer"):
        gm.grouped_cross_validation_mixed_boosting(
            data, outcome_col="y", group_col="group", feature_cols=["x"], n_splits=3, seed=-1
        )
    four = frame(groups=4, rows=6)
    with pytest.raises(ValueError, match="retain at least four"):
        gm.grouped_cross_validation_mixed_boosting(
            four, outcome_col="y", group_col="group", feature_cols=["x"], n_splits=2
        )
