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


def test_fit_is_deterministic_and_prediction_outputs_are_valid():
    data = frame()
    m1 = fit_default(data)
    m2 = fit_default(data)
    assert m1 == m2
    assert m1.training_rows == len(data)
    assert m1.training_groups == 8
    assert m1.category_order == ("low", "mid", "high")
    assert np.all(np.diff(m1.thresholds) > 0)
    assert m1.random_intercept_variance >= 0
    assert np.isfinite(m1.training_ordinal_log_loss)
    assert np.isfinite(m1.training_ranked_probability_score)
    assert len(m1.training_outcome_sha256) == 64
    assert len(m1.training_feature_sha256) == 64
    probability = go.predict_grouped_ordinal_boosting(m1, data, mode="conditional")
    cumulative = go.predict_grouped_ordinal_boosting(
        m1, data, mode="conditional", output="cumulative_probability"
    )
    category = go.predict_grouped_ordinal_boosting(m1, data, mode="conditional", output="category")
    assert probability.shape == (len(data), 3)
    assert cumulative.shape == (len(data), 2)
    assert probability.sum(axis=1) == pytest.approx(np.ones(len(data)))
    assert np.all(np.diff(cumulative, axis=1) >= 0)
    assert set(category).issubset(set(m1.category_order))
    with pytest.raises(FrozenInstanceError):
        m1.n_iterations = 99


def test_conditional_marginal_and_unseen_semantics():
    data = frame()
    model = fit_default(data)
    seen = data.iloc[:8].copy()
    marginal = go.predict_grouped_ordinal_boosting(model, seen, mode="marginal")
    conditional = go.predict_grouped_ordinal_boosting(model, seen, mode="conditional")
    assert not np.allclose(marginal, conditional)
    unseen = seen.copy()
    unseen["group"] = "NEW"
    assert go.predict_grouped_ordinal_boosting(model, unseen, mode="conditional") == pytest.approx(
        go.predict_grouped_ordinal_boosting(model, unseen, mode="marginal")
    )
    with pytest.raises(ValueError, match="unseen groups"):
        go.predict_grouped_ordinal_boosting(model, unseen, mode="conditional", unseen_group="error")
    with pytest.raises(ValueError, match="requires group"):
        go.predict_grouped_ordinal_boosting(model, seen.drop(columns="group"), mode="conditional")
    missing = seen.copy()
    missing.loc[missing.index[0], "group"] = None
    with pytest.raises(ValueError, match="must not be missing"):
        go.predict_grouped_ordinal_boosting(model, missing, mode="conditional")


def test_prediction_guardrails():
    data = frame()
    model = fit_default(data)
    with pytest.raises(ValueError, match="output"):
        go.predict_grouped_ordinal_boosting(model, data, output="bad")
    with pytest.raises(TypeError, match="model"):
        go.predict_grouped_ordinal_boosting(object(), data)
    with pytest.raises(ValueError, match="mode"):
        go.predict_grouped_ordinal_boosting(model, data, mode="bad")
    with pytest.raises(ValueError, match="unseen_group"):
        go.predict_grouped_ordinal_boosting(model, data, unseen_group="bad")


def test_category_order_requires_explicit_order_or_ordered_categorical():
    data = frame()
    with pytest.raises(ValueError, match="category_order"):
        go.fit_grouped_ordinal_boosting(
            data,
            outcome_col="y",
            group_col="group",
            feature_cols=["x"],
            n_estimators=2,
            min_samples_leaf=2,
            max_iterations=1,
        )
    ordered = data.copy()
    ordered["y"] = pd.Categorical(ordered["y"], categories=["low", "mid", "high"], ordered=True)
    model = go.fit_grouped_ordinal_boosting(
        ordered,
        outcome_col="y",
        group_col="group",
        feature_cols=["x"],
        n_estimators=2,
        min_samples_leaf=2,
        max_iterations=1,
    )
    assert model.category_order == ("low", "mid", "high")


def test_training_frame_guardrails():
    data = frame()
    common = dict(category_order=["low", "mid", "high"], n_estimators=2, min_samples_leaf=2, max_iterations=1)
    with pytest.raises(TypeError, match="DataFrame"):
        go.fit_grouped_ordinal_boosting([], outcome_col="y", group_col="group", feature_cols=["x"], **common)
    with pytest.raises(ValueError, match="distinct"):
        go.fit_grouped_ordinal_boosting(data, outcome_col="y", group_col="y", feature_cols=["x"], **common)
    with pytest.raises(ValueError, match="non-empty sequence"):
        go.fit_grouped_ordinal_boosting(data, outcome_col="y", group_col="group", feature_cols=[], **common)
    with pytest.raises(ValueError, match="non-empty sequence"):
        go.fit_grouped_ordinal_boosting(data, outcome_col="y", group_col="group", feature_cols="x", **common)
    with pytest.raises(ValueError, match="duplicates"):
        go.fit_grouped_ordinal_boosting(data, outcome_col="y", group_col="group", feature_cols=["x", "x"], **common)
    with pytest.raises(ValueError, match="cannot also"):
        go.fit_grouped_ordinal_boosting(data, outcome_col="y", group_col="group", feature_cols=["y"], **common)
    with pytest.raises(ValueError, match="Missing required"):
        go.fit_grouped_ordinal_boosting(data, outcome_col="missing", group_col="group", feature_cols=["x"], **common)
    with pytest.raises(ValueError, match="at least one row"):
        go.fit_grouped_ordinal_boosting(data.iloc[0:0], outcome_col="y", group_col="group", feature_cols=["x"], **common)
    bad_x = data.copy()
    bad_x.loc[bad_x.index[0], "x"] = np.nan
    with pytest.raises(ValueError, match="finite numeric"):
        go.fit_grouped_ordinal_boosting(bad_x, outcome_col="y", group_col="group", feature_cols=["x"], **common)
    bad_g = data.copy()
    bad_g.loc[bad_g.index[0], "group"] = None
    with pytest.raises(ValueError, match="Group identifiers"):
        go.fit_grouped_ordinal_boosting(bad_g, outcome_col="y", group_col="group", feature_cols=["x"], **common)
    collision = data.copy()
    collision["group"] = collision["group"].astype(object)
    collision.loc[collision.group == "G0", "group"] = 1
    collision.loc[collision.group == "G1", "group"] = "1"
    with pytest.raises(ValueError, match="unique after string normalization"):
        go.fit_grouped_ordinal_boosting(collision, outcome_col="y", group_col="group", feature_cols=["x"], **common)
    few = data[data.group.isin(["G0", "G1", "G2"])]
    with pytest.raises(ValueError, match="four distinct"):
        go.fit_grouped_ordinal_boosting(few, outcome_col="y", group_col="group", feature_cols=["x"], **common)


def test_category_guardrails():
    data = frame()
    s = data["y"]
    with pytest.raises(ValueError, match="sequence"):
        go._resolve_category_order(s, "low")
    with pytest.raises(ValueError, match="At least three"):
        go._resolve_category_order(s, ["low", "high"])
    with pytest.raises(ValueError, match="unique"):
        go._resolve_category_order(s, ["low", "mid", "mid"])
    missing = s.copy()
    missing.iloc[0] = None
    with pytest.raises(ValueError, match="must not be missing"):
        go._resolve_category_order(missing, ["low", "mid", "high"])
    with pytest.raises(ValueError, match="appear"):
        go._resolve_category_order(s, ["zero", "mid", "high"])
    only = pd.Series(["low", "mid", "low", "mid"])
    with pytest.raises(ValueError, match="observed at least once"):
        go._resolve_category_order(only, ["low", "mid", "high"])
    with pytest.raises(ValueError, match="strings or finite numeric"):
        go._normalize_label(True)
    with pytest.raises(ValueError, match="strings or finite numeric"):
        go._normalize_label([])
    with pytest.raises(ValueError, match="finite"):
        go._normalize_label(float("inf"))
    assert go._normalize_label(np.int64(3)) == 3


def test_hyperparameter_guardrails_and_convergence_flags():
    data = frame()
    base = dict(data=data, outcome_col="y", group_col="group", feature_cols=["x"], category_order=["low", "mid", "high"])
    with pytest.raises(ValueError, match="not exceed"):
        go.fit_grouped_ordinal_boosting(**base, learning_rate=1.1, n_estimators=2, min_samples_leaf=2, max_iterations=1)
    with pytest.raises(ValueError, match="limited to 3"):
        go.fit_grouped_ordinal_boosting(**base, max_depth=4, n_estimators=2, min_samples_leaf=2, max_iterations=1)
    with pytest.raises(ValueError, match="too large"):
        go.fit_grouped_ordinal_boosting(**base, n_estimators=2, min_samples_leaf=len(data), max_iterations=1)
    fast = fit_default(data, tolerance=1e6, max_iterations=3)
    assert fast.converged is True and fast.n_iterations == 1
    slow = fit_default(data, tolerance=1e-12, max_iterations=1)
    assert slow.converged is False and slow.n_iterations == 1


def test_probability_threshold_and_score_helpers_cover_edge_paths():
    y = np.array([0, 1, 2])
    theta = np.array([-0.5, 0.8])
    eta = np.array([-1.0, 0.0, 1.0])
    p = go._ordinal_probabilities(eta, theta)
    assert p.shape == (3, 3)
    assert p.sum(axis=1) == pytest.approx(np.ones(3))
    score = go._ordinal_score(y, eta, theta)
    assert np.all(np.isfinite(score))
    assert go._ordinal_log_loss(y, p) > 0
    assert go._ranked_probability_score(y, p) >= 0
    raw = go._raw_from_thresholds(theta)
    assert go._thresholds_from_raw(raw) == pytest.approx(theta)
    one = np.array([0.2])
    assert go._thresholds_from_raw(go._raw_from_thresholds(one)) == pytest.approx(one)
    p2 = go._ordinal_probabilities(np.array([0.0]), one)
    assert p2.shape == (1, 2)
    initial = go._initial_thresholds(np.array([0, 1, 2, 0, 1, 2]), 3)
    assert np.all(np.diff(initial) > 0)


def test_threshold_optimizer_fail_closed(monkeypatch):
    y = np.array([0, 1, 2, 0, 1, 2])
    eta = np.zeros(len(y))
    theta = np.array([-0.4, 0.6])
    monkeypatch.setattr(core, "minimize", lambda *a, **k: SimpleNamespace(success=False, x=np.array([0.0, 0.0])))
    with pytest.raises(RuntimeError, match="failed"):
        go._optimize_thresholds(y, eta, theta)

    monkeypatch.setattr(core, "minimize", lambda *a, **k: SimpleNamespace(success=True, x=np.array([np.nan, 0.0])))
    with pytest.raises(RuntimeError, match="failed"):
        go._optimize_thresholds(y, eta, theta)

    monkeypatch.setattr(core, "minimize", lambda *a, **k: SimpleNamespace(success=True, x=np.array([0.0, 0.0])))
    monkeypatch.setattr(core, "_thresholds_from_raw", lambda raw: np.array([1.0, 0.0]))
    with pytest.raises(RuntimeError, match="ordering"):
        go._optimize_thresholds(y, eta, theta)
