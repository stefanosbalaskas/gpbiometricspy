from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from scipy.optimize._numdiff import approx_derivative

import gpbiometricspy.hierarchical_location_scale_crossed_joint_random_slopes as c
import gpbiometricspy.hierarchical_location_scale_crossed_joint_random_slopes_core as core


@pytest.fixture(scope="module")
def simulated():
    return c.simulate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        n_participants=8,
        n_items=8,
        repeats=2,
        seed=1201,
    )


@pytest.fixture(scope="module")
def fitted(simulated):
    return c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        simulated,
        "outcome",
        "participant",
        "item",
        participant_location_random_slope_col="participant_location_predictor",
        item_location_random_slope_col="item_location_predictor",
        participant_scale_random_slope_col="participant_scale_predictor",
        item_scale_random_slope_col="item_scale_predictor",
        mean_cols=[
            "mean_predictor",
            "participant_location_predictor",
            "item_location_predictor",
        ],
        scale_cols=["participant_scale_predictor", "item_scale_predictor"],
        standardize_numeric=False,
        maxiter=400,
    )


def _fit_kwargs(data):
    return dict(
        data=data,
        outcome_col="outcome",
        participant_col="participant",
        item_col="item",
        participant_location_random_slope_col="participant_location_predictor",
        item_location_random_slope_col="item_location_predictor",
        participant_scale_random_slope_col="participant_scale_predictor",
        item_scale_random_slope_col="item_scale_predictor",
        mean_cols=[
            "mean_predictor",
            "participant_location_predictor",
            "item_location_predictor",
        ],
        scale_cols=["participant_scale_predictor", "item_scale_predictor"],
        standardize_numeric=False,
    )


def _prepared(data):
    return core._prepare_fit_data(
        data,
        "outcome",
        "participant",
        "item",
        [
            "mean_predictor",
            "participant_location_predictor",
            "item_location_predictor",
        ],
        ["participant_scale_predictor", "item_scale_predictor"],
        "participant_location_predictor",
        "item_location_predictor",
        "participant_scale_predictor",
        "item_scale_predictor",
        standardize_numeric=False,
    )


def test_simulation_is_reproducible_and_binds_truth():
    a = c.simulate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(seed=9)
    b = c.simulate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(seed=9)
    pd.testing.assert_frame_equal(a, b)
    assert a.shape == (64, 8)
    assert a.attrs["truth"]["seed"] == 9
    assert a.attrs["truth"]["participant_covariance"].shape == (4, 4)
    assert a.attrs["truth"]["item_covariance"].shape == (4, 4)


def test_fit_result_contract_and_immutability(fitted):
    assert fitted.diagnostics["converged"]
    assert fitted.metadata["n_participants"] == 8
    assert fitted.metadata["n_items"] == 8
    assert fitted.metadata["latent_dimension"] == 64
    assert fitted.metadata["conditional_distribution"] == "Gaussian"
    assert fitted.participant_covariance.shape == (4, 4)
    assert fitted.item_covariance.shape == (4, 4)
    assert fitted.participant_correlation.shape == (4, 4)
    assert fitted.item_correlation.shape == (4, 4)
    assert len(fitted.participant_random_effects) == 8
    assert len(fitted.item_random_effects) == 8
    assert np.isfinite(fitted.log_likelihood)
    assert all(value > 0 for value in fitted.participant_random_effect_sd)
    assert all(value > 0 for value in fitted.item_random_effect_sd)
    for matrix in (
        fitted.parameter_vector,
        fitted.participant_covariance,
        fitted.participant_correlation,
        fitted.item_covariance,
        fitted.item_correlation,
    ):
        assert not matrix.flags.writeable
    with pytest.raises((TypeError, FrozenInstanceError)):
        fitted.metadata["new"] = "x"
    with pytest.raises(FrozenInstanceError):
        fitted.log_likelihood = 0.0


def test_prediction_levels_and_population_semantics(fitted, simulated):
    rows = simulated.iloc[:4].copy()
    rows.loc[rows.index[1], "participant"] = "new_participant"
    rows.loc[rows.index[2], "item"] = "new_item"
    rows.loc[rows.index[3], ["participant", "item"]] = ["new_p2", "new_i2"]
    prediction = c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        fitted, rows
    )
    assert prediction["prediction_level"].tolist() == [
        "conditional_participant_item",
        "population_participant_conditional_item",
        "conditional_participant_population_item",
        "population_participant_item",
    ]
    population = c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        fitted, rows, include_random_effects=False
    )
    assert set(population["prediction_level"]) == {"population_fixed_effects"}
    assert np.isfinite(population["predicted_scale"]).all()
    with pytest.raises(ValueError, match="unseen participant or item"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            fitted, rows, unknown_levels="error"
        )


def test_conditional_location_and_scale_slope_effects(fitted, simulated):
    row = simulated.iloc[[0]].copy()
    changed = row.copy()
    changed["participant_location_predictor"] += 1.0
    changed["participant_scale_predictor"] += 1.0
    base_conditional = c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        fitted, row
    )
    changed_conditional = c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        fitted, changed
    )
    base_population = c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        fitted, row, include_random_effects=False
    )
    changed_population = c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        fitted, changed, include_random_effects=False
    )
    participant = str(row.iloc[0]["participant"])
    random = fitted.participant_random_effects.set_index("participant").loc[participant]
    location_before = c._prediction_slope_values(
        row,
        fitted.participant_location_random_slope_col,
        fitted.encoder,
        equation="location",
    )[0]
    location_after = c._prediction_slope_values(
        changed,
        fitted.participant_location_random_slope_col,
        fitted.encoder,
        equation="location",
    )[0]
    scale_before = c._prediction_slope_values(
        row,
        fitted.participant_scale_random_slope_col,
        fitted.encoder,
        equation="scale",
    )[0]
    scale_after = c._prediction_slope_values(
        changed,
        fitted.participant_scale_random_slope_col,
        fitted.encoder,
        equation="scale",
    )[0]
    conditional_mean_delta = (
        changed_conditional["predicted_mean"].iloc[0]
        - base_conditional["predicted_mean"].iloc[0]
    )
    population_mean_delta = (
        changed_population["predicted_mean"].iloc[0]
        - base_population["predicted_mean"].iloc[0]
    )
    conditional_scale_delta = (
        changed_conditional["predicted_log_scale"].iloc[0]
        - base_conditional["predicted_log_scale"].iloc[0]
    )
    population_scale_delta = (
        changed_population["predicted_log_scale"].iloc[0]
        - base_population["predicted_log_scale"].iloc[0]
    )
    assert np.isclose(
        conditional_mean_delta - population_mean_delta,
        float(random["location_slope_mode"]) * (location_after - location_before),
        atol=1e-7,
    )
    assert np.isclose(
        conditional_scale_delta - population_scale_delta,
        float(random["log_scale_slope_mode"]) * (scale_after - scale_before),
        atol=1e-7,
    )


def test_certificate_roundtrip_order_and_mutation(fitted):
    certificate = c.create_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate(
        fitted
    )
    validator = c.validate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate
    assert validator(fitted, certificate)
    reversed_payload = dict(reversed(list(certificate["payload"].items())))
    digest = hashlib.sha256(
        json.dumps(
            reversed_payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    assert validator(fitted, {"payload": reversed_payload, "sha256": digest})
    changed = copy.deepcopy(certificate)
    changed["payload"]["n_rows"] += 1
    assert not validator(fitted, changed)
    changed["sha256"] = "0" * 64
    assert not validator(fitted, changed)


def test_analytic_latent_derivatives_match_finite_difference(simulated):
    (
        _frame,
        y,
        participant_levels,
        participant_index,
        item_levels,
        item_index,
        X,
        Z,
        *_rest,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
    ) = _prepared(simulated)
    theta = core._initial_theta(y, X, Z)
    beta, gamma, participant, item = core._decode_theta(theta, X.shape[1], Z.shape[1])
    rng = np.random.default_rng(4)
    b = rng.normal(scale=0.02, size=4 * (len(participant_levels) + len(item_levels)))
    args = (
        y,
        X @ beta,
        Z @ gamma,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
        participant[1],
        participant[2],
        item[1],
        item[2],
    )
    value, gradient, hessian = core._joint_logposterior_grad_hess(b, *args)
    numeric_gradient = approx_derivative(
        lambda x: np.array([core._joint_logposterior_grad_hess(x, *args)[0]]),
        b,
        method="3-point",
    ).ravel()
    numeric_hessian = approx_derivative(
        lambda x: core._joint_logposterior_grad_hess(x, *args)[1],
        b,
        method="3-point",
    )
    assert np.isfinite(value)
    assert np.max(np.abs(gradient - numeric_gradient)) < 1e-5
    assert np.max(np.abs(hessian - numeric_hessian)) < 1e-5
    assert np.allclose(hessian, hessian.T)


def test_fixed_effect_membership_guards(simulated):
    with pytest.raises(ValueError, match="included in `mean_cols`"):
        core._prepare_fit_data(
            simulated,
            "outcome",
            "participant",
            "item",
            ["mean_predictor", "item_location_predictor"],
            ["participant_scale_predictor", "item_scale_predictor"],
            "participant_location_predictor",
            "item_location_predictor",
            "participant_scale_predictor",
            "item_scale_predictor",
            standardize_numeric=False,
        )
    with pytest.raises(ValueError, match="included in `scale_cols`"):
        core._prepare_fit_data(
            simulated,
            "outcome",
            "participant",
            "item",
            [
                "mean_predictor",
                "participant_location_predictor",
                "item_location_predictor",
            ],
            ["item_scale_predictor"],
            "participant_location_predictor",
            "item_location_predictor",
            "participant_scale_predictor",
            "item_scale_predictor",
            standardize_numeric=False,
        )


def test_minimum_levels_and_within_level_variation(simulated):
    few_participants = simulated[
        simulated["participant"].isin(simulated["participant"].unique()[:7])
    ]
    with pytest.raises(ValueError, match="at least eight participant"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(few_participants), "maxiter": 1}
        )
    few_items = simulated[simulated["item"].isin(simulated["item"].unique()[:7])]
    with pytest.raises(ValueError, match="at least eight item"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(few_items), "maxiter": 1}
        )
    nonvarying_location = simulated.copy()
    first_participant = nonvarying_location["participant"].unique()[0]
    nonvarying_location.loc[
        nonvarying_location["participant"] == first_participant,
        "participant_location_predictor",
    ] = 1.0
    with pytest.raises(ValueError, match="must vary within every participant"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(nonvarying_location), "maxiter": 1}
        )
    nonvarying_scale = simulated.copy()
    first_item = nonvarying_scale["item"].unique()[0]
    nonvarying_scale.loc[
        nonvarying_scale["item"] == first_item,
        "item_scale_predictor",
    ] = 2.0
    with pytest.raises(ValueError, match="must vary within every item"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(nonvarying_scale), "maxiter": 1}
        )


def test_fit_argument_guards_and_latent_ceiling(simulated):
    common = _fit_kwargs(simulated)
    for name in (
        "participant_location_random_slope_col",
        "item_location_random_slope_col",
        "participant_scale_random_slope_col",
        "item_scale_random_slope_col",
    ):
        with pytest.raises(ValueError, match=name):
            c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
                **{**common, name: ""}
            )
    for kwargs, pattern in (
        ({"maxiter": 0}, "maxiter"),
        ({"mode_max_steps": 0}, "mode_max_steps"),
        ({"mode_tol": np.nan}, "mode_tol"),
        ({"max_latent_dimension": 63}, "max_latent_dimension"),
    ):
        with pytest.raises(ValueError, match=pattern):
            c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
                **common, **kwargs
            )
    larger = c.simulate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        n_participants=9, n_items=8, seed=17
    )
    with pytest.raises(ValueError, match="exceeds"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(larger), "max_latent_dimension": 64}
        )


def test_prediction_guards(fitted, simulated, monkeypatch):
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            object(), simulated
        )
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            fitted, []
        )
    with pytest.raises(ValueError, match="unknown_levels"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            fitted, simulated, unknown_levels="x"
        )
    with pytest.raises(ValueError, match="Missing required prediction"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            fitted, simulated.drop(columns="item")
        )
    missing_identifier = simulated.copy()
    missing_identifier.loc[missing_identifier.index[0], "item"] = None
    with pytest.raises(ValueError, match="must be non-missing"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            fitted, missing_identifier
        )
    with pytest.raises(ValueError, match="Missing required random location-slope"):
        c._prediction_slope_values(
            simulated.drop(columns="participant_location_predictor"),
            "participant_location_predictor",
            fitted.encoder,
            equation="location",
        )
    nonfinite = simulated.iloc[:2].copy()
    nonfinite["participant_scale_predictor"] = np.nan
    with pytest.raises(ValueError, match="finite numeric"):
        c._prediction_slope_values(
            nonfinite,
            "participant_scale_predictor",
            fitted.encoder,
            equation="scale",
        )
    cfg = dict(fitted.encoder["mean_spec"]["participant_location_predictor"])
    cfg["scale"] = np.nan
    minimal_encoder = {"mean_spec": {"participant_location_predictor": cfg}}
    with pytest.raises(ValueError, match="invalid fitted scaling factor"):
        c._prediction_slope_values(
            simulated.iloc[:2],
            "participant_location_predictor",
            minimal_encoder,
            equation="location",
        )

    original_apply_encoder = c._apply_encoder
    calls = {"n": 0}

    def wrong_terms(*args, **kwargs):
        matrix, terms = original_apply_encoder(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 1:
            terms = tuple([*terms, "wrong"])
        return matrix, terms

    monkeypatch.setattr(c, "_apply_encoder", wrong_terms)
    with pytest.raises(RuntimeError, match="does not match"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            fitted, simulated.iloc[:2]
        )


def test_covariance_decode_and_simulation_guards():
    covariance = c._simulation_covariance(
        (1.0, 0.5, 0.4, 0.3),
        (0.1, -0.1, 0.05, 0.1, 0.0, -0.1),
        role_name="participant",
    )
    assert covariance.shape == (4, 4)
    assert np.all(np.linalg.eigvalsh(covariance) > 0)
    decoded = core._decode_theta(np.r_[np.zeros(2), np.zeros(20)], 1, 1)
    assert decoded[2][0].shape == decoded[3][0].shape == (4, 4)
    with pytest.raises(ValueError, match="invalid size"):
        core._decode_theta(np.zeros(2), 1, 1)
    with pytest.raises(ValueError, match="non-finite"):
        core._decode_theta(np.r_[np.zeros(21), np.nan], 1, 1)
    for kwargs, pattern in (
        ({"n_participants": 7}, "n_participants"),
        ({"n_items": 7}, "n_items"),
        ({"repeats": 0}, "repeats"),
        ({"seed": -1}, "seed"),
        ({"mean_predictor_slope": np.nan}, "fixed-effect"),
    ):
        with pytest.raises(ValueError, match=pattern):
            c.simulate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
                **kwargs
            )
    with pytest.raises(ValueError, match="four finite"):
        c._simulation_covariance((1, 1, 1), (0, 0, 0, 0, 0, 0), role_name="x")
    with pytest.raises(ValueError, match="strictly positive"):
        c._simulation_covariance((1, 1, 1, 0), (0, 0, 0, 0, 0, 0), role_name="x")
    with pytest.raises(ValueError, match="six finite"):
        c._simulation_covariance((1, 1, 1, 1), (0, 0), role_name="x")
    with pytest.raises(ValueError, match="strictly inside"):
        c._simulation_covariance((1, 1, 1, 1), (1, 0, 0, 0, 0, 0), role_name="x")
    with pytest.raises(ValueError, match="positive definite"):
        c._simulation_covariance(
            (1, 1, 1, 1),
            (0.9, 0.9, -0.9, 0.9, -0.9, 0.9),
            role_name="x",
        )


def test_core_failure_paths_and_pinv_fallback(simulated, monkeypatch):
    (
        _frame,
        y,
        participant_levels,
        participant_index,
        item_levels,
        item_index,
        X,
        Z,
        *_rest,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
    ) = _prepared(simulated)
    theta = core._initial_theta(y, X, Z)
    beta, gamma, participant, item = core._decode_theta(theta, X.shape[1], Z.shape[1])
    args = (
        y,
        X @ beta,
        Z @ gamma,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
        participant[1],
        participant[2],
        item[1],
        item[2],
    )
    with pytest.raises(ValueError, match="wrong dimension"):
        core._joint_logposterior_grad_hess(np.zeros(1), *args)
    mismatched = list(args)
    mismatched[0] = y[:-1]
    with pytest.raises(ValueError, match="same length"):
        core._joint_logposterior_grad_hess(
            np.zeros(4 * (len(participant_levels) + len(item_levels))),
            *mismatched,
        )
    malformed = np.full_like(theta, np.nan)
    laplace_args = (
        malformed,
        y,
        X,
        Z,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
    )
    assert core._laplace_loglik(
        *laplace_args, mode_max_steps=2, mode_tol=1e-6
    ) == -np.inf
    assert core._laplace_loglik(
        *laplace_args,
        mode_max_steps=2,
        mode_tol=1e-6,
        return_state=True,
    ) == (-np.inf, None)

    original_inv = np.linalg.inv
    calls = {"n": 0}

    def fail_once(matrix):
        calls["n"] += 1
        if calls["n"] == 1:
            raise np.linalg.LinAlgError
        return original_inv(matrix)

    monkeypatch.setattr(core.np.linalg, "inv", fail_once)
    participant_table, item_table = core._random_effect_tables(
        np.zeros(8), np.eye(8), np.array(["p"]), np.array(["i"])
    )
    assert len(participant_table) == len(item_table) == 1


def test_certificate_defensive_paths(fitted):
    validator = c.validate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate
    assert not validator(object(), {})
    assert not validator(fitted, [])
    assert not validator(fitted, {"payload": {}})
    assert not validator(fitted, {"payload": [], "sha256": 3})
    assert not validator(fitted, {"payload": {"x": np.nan}, "sha256": "x"})
    with pytest.raises(TypeError):
        c.create_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate(
            object()
        )
    diagnostics = dict(fitted.diagnostics)
    diagnostics["converged"] = False
    nonconverged = core.GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult(
        **{**fitted.__dict__, "diagnostics": diagnostics}
    )
    with pytest.raises(ValueError, match="non-converged"):
        c.create_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate(
            nonconverged
        )


def test_internal_covariance_consistency_guard(simulated, monkeypatch):
    (
        _frame,
        y,
        participant_levels,
        participant_index,
        item_levels,
        item_index,
        X,
        Z,
        *_rest,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
    ) = _prepared(simulated)
    theta0 = core._initial_theta(y, X, Z)
    log_likelihood, state = core._laplace_loglik(
        theta0,
        y,
        X,
        Z,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
        mode_max_steps=50,
        mode_tol=1e-6,
        return_state=True,
    )
    assert state is not None and np.isfinite(log_likelihood)
    original_decode = c._decode_theta

    def inconsistent(theta, p, q):
        beta, gamma, participant, item = original_decode(theta, p, q)
        changed = list(participant)
        changed[0] = participant[0] + np.eye(4)
        return beta, gamma, tuple(changed), item

    def fake_minimize(fun, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            success=True,
            status=0,
            message="synthetic",
            nit=0,
            nfev=1,
            jac=np.zeros_like(x0, dtype=float),
        )

    monkeypatch.setattr(c, "minimize", fake_minimize)
    monkeypatch.setattr(
        c,
        "_laplace_loglik",
        lambda *args, **kwargs: (log_likelihood, state)
        if kwargs.get("return_state")
        else log_likelihood,
    )
    monkeypatch.setattr(c, "_decode_theta", inconsistent)
    with pytest.raises(RuntimeError, match="covariance decoding mismatch"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(simulated), "maxiter": 1}
        )


def test_fit_rejects_nonfinite_final_state(simulated, monkeypatch):
    def fake_minimize(fun, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            success=True,
            status=0,
            message="synthetic",
            nit=0,
            nfev=1,
            jac=np.zeros_like(x0, dtype=float),
        )

    monkeypatch.setattr(c, "minimize", fake_minimize)
    monkeypatch.setattr(
        c,
        "_laplace_loglik",
        lambda *args, **kwargs: (-np.inf, None)
        if kwargs.get("return_state")
        else -np.inf,
    )
    with pytest.raises(RuntimeError, match="finite converged Laplace"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
            **{**_fit_kwargs(simulated), "maxiter": 1}
        )


def test_optimizer_restart_and_stationary_acceptance(simulated, monkeypatch):
    (
        _frame,
        y,
        participant_levels,
        participant_index,
        item_levels,
        item_index,
        X,
        Z,
        *_rest,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
    ) = _prepared(simulated)
    theta0 = core._initial_theta(y, X, Z)
    log_likelihood, state = core._laplace_loglik(
        theta0,
        y,
        X,
        Z,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
        mode_max_steps=50,
        mode_tol=1e-6,
        return_state=True,
    )
    assert state is not None
    calls = {"n": 0}

    def fake_minimize(fun, x0, **kwargs):
        calls["n"] += 1
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            success=False,
            status=1,
            message="synthetic",
            nit=1,
            nfev=1,
            jac=np.zeros_like(x0, dtype=float),
        )

    monkeypatch.setattr(c, "minimize", fake_minimize)
    monkeypatch.setattr(
        c,
        "_laplace_loglik",
        lambda *args, **kwargs: (log_likelihood, state)
        if kwargs.get("return_state")
        else log_likelihood,
    )
    result = c.fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
        **{**_fit_kwargs(simulated), "maxiter": 1}
    )
    assert calls["n"] == 2
    assert result.diagnostics["optimizer_restarted"]
    assert result.diagnostics["optimizer_stationary"]
    assert result.diagnostics["converged"]


def test_initial_theta_and_parameter_bounds():
    X = np.column_stack([np.ones(4), np.arange(4.0)])
    y_exact = 1.0 + 2.0 * np.arange(4.0)
    Z = np.ones((4, 1))
    theta = core._initial_theta(y_exact, X, Z)
    assert np.isfinite(theta).all()
    bounds = core._parameter_bounds(X.shape[1], Z.shape[1])
    assert len(bounds) == len(theta)
    assert bounds[: X.shape[1] + Z.shape[1]] == [(None, None)] * 3
