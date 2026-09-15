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

import gpbiometricspy.hierarchical_location_scale_crossed_random_scale_core as core
import gpbiometricspy.hierarchical_location_scale_crossed_random_scale_slopes as c


@pytest.fixture(scope="module")
def simulated():
    return c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
        n_participants=6,
        n_items=6,
        repeats=2,
        seed=901,
    )


@pytest.fixture(scope="module")
def fitted(simulated):
    return c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
        simulated,
        "outcome",
        "participant",
        "item",
        participant_scale_random_slope_col="participant_scale_predictor",
        item_scale_random_slope_col="item_scale_predictor",
        mean_cols=["mean_predictor"],
        scale_cols=["participant_scale_predictor", "item_scale_predictor"],
        standardize_numeric=False,
        maxiter=400,
    )


def test_simulation_reproducibility_truth_and_structure():
    a = c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
        seed=9
    )
    b = c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
        seed=9
    )
    pd.testing.assert_frame_equal(a, b)
    assert a.attrs["truth"]["seed"] == 9
    assert a.shape == (64, 6)
    assert a.attrs["truth"]["participant_covariance"].shape == (3, 3)
    assert a.attrs["truth"]["item_covariance"].shape == (3, 3)


def test_fit_result_contract(fitted):
    assert fitted.diagnostics["converged"]
    assert fitted.metadata["n_participants"] == 6
    assert fitted.metadata["n_items"] == 6
    assert fitted.metadata["latent_dimension"] == 36
    assert fitted.metadata["conditional_distribution"] == "Gaussian"
    assert fitted.participant_covariance.shape == (3, 3)
    assert fitted.item_covariance.shape == (3, 3)
    assert len(fitted.participant_random_effects) == 6
    assert len(fitted.item_random_effects) == 6
    assert np.isfinite(fitted.log_likelihood)
    assert fitted.participant_scale_random_slope_col == "participant_scale_predictor"
    assert fitted.item_scale_random_slope_col == "item_scale_predictor"


def test_prediction_levels_and_population_semantics(fitted, simulated):
    rows = simulated.iloc[:4].copy()
    rows.loc[rows.index[1], "participant"] = "new_participant"
    rows.loc[rows.index[2], "item"] = "new_item"
    rows.loc[rows.index[3], ["participant", "item"]] = ["new_p2", "new_i2"]

    pred = c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
        fitted, rows
    )
    assert pred["prediction_level"].tolist() == [
        "conditional_participant_item",
        "population_participant_conditional_item",
        "conditional_participant_population_item",
        "population_participant_item",
    ]
    population = (
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted,
            rows,
            include_random_effects=False,
        )
    )
    assert set(population["prediction_level"]) == {"population_fixed_effects"}
    assert np.isfinite(population["predicted_scale"]).all()
    with pytest.raises(ValueError, match="unseen participant or item"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted,
            rows,
            unknown_levels="error",
        )


def test_conditional_log_scale_random_slope_effect(fitted, simulated):
    row = simulated.iloc[[0]].copy()
    baseline_conditional = (
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, row
        )
    )
    baseline_population = (
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, row, include_random_effects=False
        )
    )

    changed = row.copy()
    changed["participant_scale_predictor"] += 1.0
    shifted_conditional = (
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, changed
        )
    )
    shifted_population = (
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, changed, include_random_effects=False
        )
    )
    participant = str(row.iloc[0]["participant"])
    random_slope = float(
        fitted.participant_random_effects.set_index("participant").loc[
            participant, "log_scale_slope_mode"
        ]
    )
    conditional_delta = (
        shifted_conditional["predicted_log_scale"].iloc[0]
        - baseline_conditional["predicted_log_scale"].iloc[0]
    )
    population_delta = (
        shifted_population["predicted_log_scale"].iloc[0]
        - baseline_population["predicted_log_scale"].iloc[0]
    )
    assert np.isclose(conditional_delta - population_delta, random_slope, atol=1e-7)


def test_certificate_roundtrip_key_order_and_mutation(fitted):
    cert = c.create_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted
    )
    assert c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, cert
    )
    reversed_payload = dict(reversed(list(cert["payload"].items())))
    digest = hashlib.sha256(
        json.dumps(
            reversed_payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    reordered = {"payload": reversed_payload, "sha256": digest}
    assert c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, reordered
    )
    bad = copy.deepcopy(cert)
    bad["payload"]["n_rows"] += 1
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, bad
    )
    bad2 = copy.deepcopy(cert)
    bad2["sha256"] = "0" * 64
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, bad2
    )


def test_result_immutability_contract(fitted):
    assert not fitted.parameter_vector.flags.writeable
    assert not fitted.participant_covariance.flags.writeable
    assert not fitted.item_covariance.flags.writeable
    with pytest.raises((TypeError, FrozenInstanceError)):
        fitted.metadata["new"] = "x"
    with pytest.raises(FrozenInstanceError):
        fitted.log_likelihood = 0.0


def test_analytic_latent_derivatives_match_finite_difference(simulated):
    (
        _frame,
        y,
        plev,
        pidx,
        ilev,
        iidx,
        X,
        Z,
        *_rest,
        participant_scale,
        item_scale,
    ) = core._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["mean_predictor"],
        ["participant_scale_predictor", "item_scale_predictor"],
        "participant_scale_predictor",
        "item_scale_predictor",
        standardize_numeric=False,
    )
    theta = core._initial_theta(y, X, Z)
    beta, gamma, participant, item = core._decode_theta(theta, X.shape[1], Z.shape[1])
    rng = np.random.default_rng(4)
    b = rng.normal(scale=0.02, size=3 * (len(plev) + len(ilev)))
    args = (
        y,
        X @ beta,
        Z @ gamma,
        participant_scale,
        item_scale,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        participant[1],
        participant[2],
        item[1],
        item[2],
    )
    value, grad, hess = core._joint_logposterior_grad_hess(b, *args)
    numeric_grad = approx_derivative(
        lambda x: np.array([core._joint_logposterior_grad_hess(x, *args)[0]]),
        b,
        method="3-point",
    ).ravel()
    numeric_hess = approx_derivative(
        lambda x: core._joint_logposterior_grad_hess(x, *args)[1],
        b,
        method="3-point",
    )
    assert np.isfinite(value)
    assert np.max(np.abs(grad - numeric_grad)) < 1e-5
    assert np.max(np.abs(hess - numeric_hess)) < 1e-5
    assert np.allclose(hess, hess.T)


def test_scale_slope_must_be_in_scale_cols(simulated):
    with pytest.raises(ValueError, match="included in `scale_cols`"):
        core._prepare_fit_data(
            simulated,
            "outcome",
            "participant",
            "item",
            ["mean_predictor"],
            ["item_scale_predictor"],
            "participant_scale_predictor",
            "item_scale_predictor",
            standardize_numeric=False,
        )


def test_scale_slope_numeric_and_minimum_level_guardrails(simulated):
    categorical = simulated.copy()
    categorical["scale_category"] = np.where(np.arange(len(categorical)) % 2, "B", "A")
    with pytest.raises(ValueError, match="must be numeric"):
        core._prepare_fit_data(
            categorical,
            "outcome",
            "participant",
            "item",
            ["mean_predictor"],
            ["scale_category", "item_scale_predictor"],
            "scale_category",
            "item_scale_predictor",
            standardize_numeric=False,
        )

    few = simulated[simulated["participant"].isin(simulated["participant"].unique()[:5])]
    with pytest.raises(ValueError, match="at least six participant"):
        core._prepare_fit_data(
            few,
            "outcome",
            "participant",
            "item",
            ["mean_predictor"],
            ["participant_scale_predictor", "item_scale_predictor"],
            "participant_scale_predictor",
            "item_scale_predictor",
            standardize_numeric=False,
        )


def test_scale_slope_variation_and_scaling_guardrails(simulated):
    nonvarying = simulated.copy()
    first = nonvarying["participant"].unique()[0]
    nonvarying.loc[
        nonvarying["participant"] == first, "participant_scale_predictor"
    ] = 1.0
    with pytest.raises(ValueError, match="must vary within every participant"):
        core._prepare_fit_data(
            nonvarying,
            "outcome",
            "participant",
            "item",
            ["mean_predictor"],
            ["participant_scale_predictor", "item_scale_predictor"],
            "participant_scale_predictor",
            "item_scale_predictor",
            standardize_numeric=False,
        )

    nonvarying_item = simulated.copy()
    first_item = nonvarying_item["item"].unique()[0]
    nonvarying_item.loc[
        nonvarying_item["item"] == first_item, "item_scale_predictor"
    ] = 2.0
    with pytest.raises(ValueError, match="must vary within every item"):
        core._prepare_fit_data(
            nonvarying_item,
            "outcome",
            "participant",
            "item",
            ["mean_predictor"],
            ["participant_scale_predictor", "item_scale_predictor"],
            "participant_scale_predictor",
            "item_scale_predictor",
            standardize_numeric=False,
        )

    frame = simulated.copy()
    labels = frame["participant"].astype(str).to_numpy()
    encoder = {
        "scale_spec": {
            "participant_scale_predictor": {
                "kind": "numeric",
                "center": 0.0,
                "scale": np.nan,
            }
        }
    }
    with pytest.raises(ValueError, match="invalid fitted scaling factor"):
        core._scale_slope_values(
            frame,
            labels,
            "participant_scale_predictor",
            ["participant_scale_predictor"],
            encoder,
            role_name="participant",
        )
    encoder["scale_spec"]["participant_scale_predictor"]["scale"] = 1.0
    frame["participant_scale_predictor"] = 1.0
    with pytest.raises(ValueError, match="within-sample variation"):
        core._scale_slope_values(
            frame,
            labels,
            "participant_scale_predictor",
            ["participant_scale_predictor"],
            encoder,
            role_name="participant",
        )


def test_fit_argument_guardrails_and_latent_limit(simulated):
    common = dict(
        data=simulated,
        outcome_col="outcome",
        participant_col="participant",
        item_col="item",
        participant_scale_random_slope_col="participant_scale_predictor",
        item_scale_random_slope_col="item_scale_predictor",
        mean_cols=["mean_predictor"],
        scale_cols=["participant_scale_predictor", "item_scale_predictor"],
        standardize_numeric=False,
    )
    with pytest.raises(ValueError, match="participant_scale_random_slope_col"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            **{**common, "participant_scale_random_slope_col": ""}
        )
    with pytest.raises(ValueError, match="item_scale_random_slope_col"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            **{**common, "item_scale_random_slope_col": ""}
        )
    with pytest.raises(ValueError, match="maxiter"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            **common, maxiter=0
        )
    with pytest.raises(ValueError, match="mode_max_steps"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            **common, mode_max_steps=0
        )
    with pytest.raises(ValueError, match="mode_tol"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            **common, mode_tol=np.nan
        )
    with pytest.raises(ValueError, match="max_latent_dimension"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            **common, max_latent_dimension=35
        )
    larger = c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
        n_participants=7, n_items=6, seed=17
    )
    with pytest.raises(ValueError, match="exceeds"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            larger,
            "outcome",
            "participant",
            "item",
            participant_scale_random_slope_col="participant_scale_predictor",
            item_scale_random_slope_col="item_scale_predictor",
            mean_cols=["mean_predictor"],
            scale_cols=["participant_scale_predictor", "item_scale_predictor"],
            standardize_numeric=False,
            max_latent_dimension=36,
        )


def test_prediction_guardrails(fitted, simulated, monkeypatch):
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            object(), simulated
        )
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, []
        )
    with pytest.raises(ValueError, match="unknown_levels"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, simulated, unknown_levels="x"
        )
    with pytest.raises(ValueError, match="Missing required prediction"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, simulated.drop(columns="item")
        )
    bad = simulated.copy()
    bad.loc[bad.index[0], "item"] = None
    with pytest.raises(ValueError, match="must be non-missing"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, bad
        )
    with pytest.raises(ValueError, match="Missing required random scale-slope"):
        c._prediction_scale_slope_values(
            simulated.drop(columns="participant_scale_predictor"),
            "participant_scale_predictor",
            fitted.encoder,
        )
    bad_slope = simulated.iloc[:2].copy()
    bad_slope["participant_scale_predictor"] = np.nan
    with pytest.raises(ValueError, match="finite numeric"):
        c._prediction_scale_slope_values(
            bad_slope,
            "participant_scale_predictor",
            fitted.encoder,
        )

    original = c._apply_encoder
    calls = {"n": 0}

    def wrong(*args, **kwargs):
        matrix, terms = original(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 1:
            terms = tuple([*terms, "wrong"])
        return matrix, terms

    monkeypatch.setattr(c, "_apply_encoder", wrong)
    with pytest.raises(RuntimeError, match="does not match"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            fitted, simulated.iloc[:2]
        )


def test_covariance_and_simulation_guardrails():
    cov = c._simulation_covariance(1, 1, 1, 0.1, -0.1, 0.05)
    assert cov.shape == (3, 3)
    assert np.all(np.linalg.eigvalsh(cov) > 0)

    decoded = core._decode_theta(
        np.r_[np.zeros(2), np.zeros(12)],
        1,
        1,
    )
    assert decoded[2][0].shape == decoded[3][0].shape == (3, 3)
    with pytest.raises(ValueError, match="invalid size"):
        core._decode_theta(np.zeros(2), 1, 1)
    with pytest.raises(ValueError, match="non-finite"):
        core._decode_theta(np.r_[np.zeros(13), np.nan], 1, 1)

    with pytest.raises(ValueError, match="n_participants"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            n_participants=5
        )
    with pytest.raises(ValueError, match="n_items"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            n_items=5
        )
    with pytest.raises(ValueError, match="repeats"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            repeats=0
        )
    with pytest.raises(ValueError, match="seed"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            seed=-1
        )
    with pytest.raises(ValueError, match="fixed-effect"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            mean_slope=np.nan
        )
    with pytest.raises(ValueError, match="finite"):
        c._simulation_covariance(np.nan, 1, 1, 0, 0, 0)
    with pytest.raises(ValueError, match="positive"):
        c._simulation_covariance(0, 1, 1, 0, 0, 0)
    with pytest.raises(ValueError, match="strictly inside"):
        c._simulation_covariance(1, 1, 1, 1, 0, 0)
    with pytest.raises(ValueError, match="positive definite"):
        c._simulation_covariance(1, 1, 1, 0.9, 0.9, -0.9)


def test_core_low_level_failure_paths_and_pinv_fallback(simulated, monkeypatch):
    (
        _frame,
        y,
        plev,
        pidx,
        ilev,
        iidx,
        X,
        Z,
        *_rest,
        participant_scale,
        item_scale,
    ) = core._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["mean_predictor"],
        ["participant_scale_predictor", "item_scale_predictor"],
        "participant_scale_predictor",
        "item_scale_predictor",
        standardize_numeric=False,
    )
    theta = core._initial_theta(y, X, Z)
    beta, gamma, participant, item = core._decode_theta(theta, X.shape[1], Z.shape[1])
    with pytest.raises(ValueError, match="wrong dimension"):
        core._joint_logposterior_grad_hess(
            np.zeros(1),
            y,
            X @ beta,
            Z @ gamma,
            participant_scale,
            item_scale,
            pidx,
            iidx,
            len(plev),
            len(ilev),
            participant[1],
            participant[2],
            item[1],
            item[2],
        )
    with pytest.raises(ValueError, match="same length"):
        core._joint_logposterior_grad_hess(
            np.zeros(3 * (len(plev) + len(ilev))),
            y[:-1],
            (X @ beta)[:-1],
            (Z @ gamma)[:-1],
            participant_scale,
            item_scale[:-1],
            pidx[:-1],
            iidx[:-1],
            len(plev),
            len(ilev),
            participant[1],
            participant[2],
            item[1],
            item[2],
        )

    malformed = np.full_like(theta, np.nan)
    assert core._laplace_loglik(
        malformed,
        y,
        X,
        Z,
        participant_scale,
        item_scale,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        mode_max_steps=2,
        mode_tol=1e-6,
    ) == -np.inf
    assert core._laplace_loglik(
        malformed,
        y,
        X,
        Z,
        participant_scale,
        item_scale,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        mode_max_steps=2,
        mode_tol=1e-6,
        return_state=True,
    ) == (-np.inf, None)

    original_inv = np.linalg.inv
    calls = {"n": 0}

    def fail_once(x):
        calls["n"] += 1
        if calls["n"] == 1:
            raise np.linalg.LinAlgError
        return original_inv(x)

    monkeypatch.setattr(core.np.linalg, "inv", fail_once)
    ptab, itab = core._random_effect_tables(
        np.zeros(6), np.eye(6), np.array(["p"]), np.array(["i"])
    )
    assert len(ptab) == len(itab) == 1


def test_certificate_defensive_paths(fitted):
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        object(), {}
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, []
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, {"payload": {}}
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, {"payload": [], "sha256": 3}
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
        fitted, {"payload": {"x": np.nan}, "sha256": "x"}
    )
    with pytest.raises(TypeError):
        c.create_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
            object()
        )
    diagnostics = dict(fitted.diagnostics)
    diagnostics["converged"] = False
    bad_result = core.GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult(
        **{**fitted.__dict__, "diagnostics": diagnostics}
    )
    with pytest.raises(ValueError, match="non-converged"):
        c.create_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
            bad_result
        )


def test_internal_covariance_consistency_guard(simulated, monkeypatch):
    prepared = core._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["mean_predictor"],
        ["participant_scale_predictor", "item_scale_predictor"],
        "participant_scale_predictor",
        "item_scale_predictor",
        standardize_numeric=False,
    )
    (
        _frame,
        y,
        plev,
        pidx,
        ilev,
        iidx,
        X,
        Z,
        *_rest,
        participant_scale,
        item_scale,
    ) = prepared
    theta0 = core._initial_theta(y, X, Z)
    loglik, state = core._laplace_loglik(
        theta0,
        y,
        X,
        Z,
        participant_scale,
        item_scale,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        mode_max_steps=50,
        mode_tol=1e-6,
        return_state=True,
    )
    assert state is not None and np.isfinite(loglik)
    original_decode = c._decode_theta

    def inconsistent(theta, p, q):
        beta, gamma, participant, item = original_decode(theta, p, q)
        changed = list(participant)
        changed[0] = participant[0] + np.eye(3)
        return beta, gamma, tuple(changed), item

    def fake_minimize(fun, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            success=True,
            status=0,
            message="synthetic",
            nit=0,
            nfev=1,
        )

    monkeypatch.setattr(c, "minimize", fake_minimize)
    monkeypatch.setattr(
        c,
        "_laplace_loglik",
        lambda *args, **kwargs: (loglik, state)
        if kwargs.get("return_state")
        else loglik,
    )
    monkeypatch.setattr(c, "_decode_theta", inconsistent)
    with pytest.raises(RuntimeError, match="covariance decoding mismatch"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            simulated,
            "outcome",
            "participant",
            "item",
            participant_scale_random_slope_col="participant_scale_predictor",
            item_scale_random_slope_col="item_scale_predictor",
            mean_cols=["mean_predictor"],
            scale_cols=["participant_scale_predictor", "item_scale_predictor"],
            standardize_numeric=False,
            maxiter=1,
        )


def test_fit_rejects_nonfinite_final_laplace_state(simulated, monkeypatch):
    def fake_minimize(fun, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            success=True,
            status=0,
            message="synthetic",
            nit=0,
            nfev=1,
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
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
            simulated,
            "outcome",
            "participant",
            "item",
            participant_scale_random_slope_col="participant_scale_predictor",
            item_scale_random_slope_col="item_scale_predictor",
            mean_cols=["mean_predictor"],
            scale_cols=["participant_scale_predictor", "item_scale_predictor"],
            standardize_numeric=False,
            maxiter=1,
        )


def test_initial_theta_and_parameter_bounds():
    X = np.column_stack([np.ones(4), np.arange(4.0)])
    y_exact = 1.0 + 2.0 * np.arange(4.0)
    Z = np.ones((4, 1))
    theta = core._initial_theta(y_exact, X, Z)
    assert np.isfinite(theta).all()
    bounds = core._parameter_bounds(X.shape[1], Z.shape[1])
    assert len(bounds) == len(theta)
    assert bounds[: X.shape[1] + Z.shape[1]] == [(None, None)] * 3
