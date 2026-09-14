from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from scipy.optimize._numdiff import approx_derivative

import gpbiometricspy.hierarchical_location_scale_crossed_random_slopes as c


@pytest.fixture(scope="module")
def simulated():
    return c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(
        n_participants=6,
        n_items=6,
        repeats=2,
        seed=456,
    )


@pytest.fixture(scope="module")
def fitted(simulated):
    return c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
        simulated,
        "outcome",
        "participant",
        "item",
        participant_random_slope_col="participant_slope_predictor",
        item_random_slope_col="item_slope_predictor",
        mean_cols=["participant_slope_predictor", "item_slope_predictor"],
        scale_cols=["scale_predictor"],
        standardize_numeric=False,
        maxiter=160,
    )


def test_simulation_reproducibility_truth_and_structure():
    a = c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(seed=9)
    b = c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(seed=9)
    pd.testing.assert_frame_equal(a, b)
    assert a.attrs["truth"]["seed"] == 9
    assert a.shape == (64, 6)
    assert a.attrs["truth"]["participant_covariance"].shape == (3, 3)
    assert a.attrs["truth"]["item_covariance"].shape == (3, 3)


def test_fit_result_contract_prediction_levels_and_random_slope_effect(fitted, simulated):
    result = fitted
    assert result.diagnostics["converged"]
    assert result.metadata["n_participants"] == 6
    assert result.metadata["n_items"] == 6
    assert result.metadata["latent_dimension"] == 36
    assert result.participant_covariance.shape == (3, 3)
    assert result.item_covariance.shape == (3, 3)
    assert not result.parameter_vector.flags.writeable
    assert not result.participant_covariance.flags.writeable
    assert not result.item_covariance.flags.writeable
    assert len(result.participant_random_effects) == 6
    assert len(result.item_random_effects) == 6
    assert result.mean_coef[1] > 0
    assert result.mean_coef[2] < 0

    rows = simulated.iloc[:4].copy()
    rows.loc[rows.index[1], "participant"] = "new_participant"
    rows.loc[rows.index[2], "item"] = "new_item"
    rows.loc[rows.index[3], ["participant", "item"]] = ["new_p2", "new_i2"]
    pred = c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(result, rows)
    assert pred["prediction_level"].tolist() == [
        "conditional_participant_item",
        "population_participant_conditional_item",
        "conditional_participant_population_item",
        "population_participant_item",
    ]
    population = c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
        result,
        rows,
        include_random_effects=False,
    )
    assert set(population["prediction_level"]) == {"population_fixed_effects"}
    assert np.isfinite(population["predicted_scale"]).all()

    changed = rows.iloc[[0]].copy()
    baseline = c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(result, changed)
    changed["participant_slope_predictor"] += 1.0
    shifted = c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(result, changed)
    participant = str(changed.iloc[0]["participant"])
    slope_mode = float(
        result.participant_random_effects.set_index("participant").loc[
            participant, "location_slope_mode"
        ]
    )
    marginal_base = c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
        result, rows.iloc[[0]], include_random_effects=False
    )["predicted_mean"].iloc[0]
    marginal_shift = c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
        result, changed, include_random_effects=False
    )["predicted_mean"].iloc[0]
    conditional_delta = shifted["predicted_mean"].iloc[0] - baseline["predicted_mean"].iloc[0]
    marginal_delta = marginal_shift - marginal_base
    assert np.isclose(conditional_delta - marginal_delta, slope_mode, atol=1e-7)

    with pytest.raises(ValueError, match="unseen participant or item"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            result,
            rows,
            unknown_levels="error",
        )


def test_certificate_roundtrip_key_order_and_mutation(fitted):
    cert = c.create_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted
    )
    assert c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
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
    assert c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, reordered
    )
    bad = copy.deepcopy(cert)
    bad["payload"]["n_rows"] += 1
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, bad
    )
    bad2 = copy.deepcopy(cert)
    bad2["sha256"] = "0" * 64
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, bad2
    )


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
        participant_slope,
        item_slope,
    ) = c._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["participant_slope_predictor", "item_slope_predictor"],
        ["scale_predictor"],
        "participant_slope_predictor",
        "item_slope_predictor",
        standardize_numeric=False,
    )
    theta = c._initial_theta(y, X, Z)
    beta, gamma, participant, item = c._decode_theta(theta, X.shape[1], Z.shape[1])
    rng = np.random.default_rng(4)
    b = rng.normal(scale=0.02, size=3 * (len(plev) + len(ilev)))
    args = (
        y,
        X @ beta,
        Z @ gamma,
        participant_slope,
        item_slope,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        participant[1],
        participant[2],
        item[1],
        item[2],
    )
    value, grad, hess = c._joint_logposterior_grad_hess(b, *args)
    numeric_grad = approx_derivative(
        lambda x: np.array([c._joint_logposterior_grad_hess(x, *args)[0]]),
        b,
        method="3-point",
    ).ravel()
    numeric_hess = approx_derivative(
        lambda x: c._joint_logposterior_grad_hess(x, *args)[1],
        b,
        method="3-point",
    )
    assert np.isfinite(value)
    assert np.max(np.abs(grad - numeric_grad)) < 1e-5
    assert np.max(np.abs(hess - numeric_hess)) < 1e-5
    assert np.allclose(hess, hess.T)


def test_slope_design_guardrails(simulated):
    with pytest.raises(ValueError, match="included in `mean_cols`"):
        c._prepare_fit_data(
            simulated,
            "outcome",
            "participant",
            "item",
            ["item_slope_predictor"],
            ["scale_predictor"],
            "participant_slope_predictor",
            "item_slope_predictor",
            standardize_numeric=False,
        )

    categorical = simulated.copy()
    categorical["slope_category"] = np.where(np.arange(len(categorical)) % 2, "B", "A")
    with pytest.raises(ValueError, match="must be numeric"):
        c._prepare_fit_data(
            categorical,
            "outcome",
            "participant",
            "item",
            ["slope_category", "item_slope_predictor"],
            [],
            "slope_category",
            "item_slope_predictor",
            standardize_numeric=False,
        )

    few = simulated[simulated["participant"].isin(simulated["participant"].unique()[:5])]
    with pytest.raises(ValueError, match="at least six participant"):
        c._prepare_fit_data(
            few,
            "outcome",
            "participant",
            "item",
            ["participant_slope_predictor", "item_slope_predictor"],
            [],
            "participant_slope_predictor",
            "item_slope_predictor",
            standardize_numeric=False,
        )

    nonvarying = simulated.copy()
    first = nonvarying["participant"].unique()[0]
    nonvarying.loc[
        nonvarying["participant"] == first, "participant_slope_predictor"
    ] = 1.0
    with pytest.raises(ValueError, match="must vary within every participant"):
        c._prepare_fit_data(
            nonvarying,
            "outcome",
            "participant",
            "item",
            ["participant_slope_predictor", "item_slope_predictor"],
            [],
            "participant_slope_predictor",
            "item_slope_predictor",
            standardize_numeric=False,
        )

    nonvarying_item = simulated.copy()
    first_item = nonvarying_item["item"].unique()[0]
    nonvarying_item.loc[
        nonvarying_item["item"] == first_item, "item_slope_predictor"
    ] = 2.0
    with pytest.raises(ValueError, match="must vary within every item"):
        c._prepare_fit_data(
            nonvarying_item,
            "outcome",
            "participant",
            "item",
            ["participant_slope_predictor", "item_slope_predictor"],
            [],
            "participant_slope_predictor",
            "item_slope_predictor",
            standardize_numeric=False,
        )


def test_fit_argument_guardrails_and_latent_limit(simulated):
    common = dict(
        data=simulated,
        outcome_col="outcome",
        participant_col="participant",
        item_col="item",
        participant_random_slope_col="participant_slope_predictor",
        item_random_slope_col="item_slope_predictor",
        mean_cols=["participant_slope_predictor", "item_slope_predictor"],
    )
    with pytest.raises(ValueError, match="participant_random_slope_col"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            **{**common, "participant_random_slope_col": ""}
        )
    with pytest.raises(ValueError, match="item_random_slope_col"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            **{**common, "item_random_slope_col": ""}
        )
    with pytest.raises(ValueError, match="maxiter"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(**common, maxiter=0)
    with pytest.raises(ValueError, match="mode_max_steps"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            **common, mode_max_steps=0
        )
    with pytest.raises(ValueError, match="mode_tol"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            **common, mode_tol=np.nan
        )
    with pytest.raises(ValueError, match="max_latent_dimension"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            **common, max_latent_dimension=35
        )
    larger = c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(
        n_participants=7, n_items=6, seed=17
    )
    with pytest.raises(ValueError, match="exceeds"):
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            larger,
            "outcome",
            "participant",
            "item",
            participant_random_slope_col="participant_slope_predictor",
            item_random_slope_col="item_slope_predictor",
            mean_cols=["participant_slope_predictor", "item_slope_predictor"],
            max_latent_dimension=36,
        )


def test_prediction_guardrails(fitted, simulated, monkeypatch):
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            object(), simulated
        )
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(fitted, [])
    with pytest.raises(ValueError, match="unknown_levels"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            fitted, simulated, unknown_levels="x"
        )
    with pytest.raises(ValueError, match="Missing required prediction"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            fitted, simulated.drop(columns="item")
        )
    bad = simulated.copy()
    bad.loc[bad.index[0], "item"] = None
    with pytest.raises(ValueError, match="must be non-missing"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(fitted, bad)

    bad_slope = simulated.iloc[:2].copy()
    bad_slope["participant_slope_predictor"] = np.nan
    with pytest.raises(ValueError, match="missing or non-finite"):
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            fitted, bad_slope
        )
    with pytest.raises(ValueError, match="finite numeric"):
        c._prediction_slope_values(
            bad_slope,
            "participant_slope_predictor",
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
        c.predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            fitted, simulated.iloc[:2]
        )


def test_covariance_decode_simulation_and_seed_guardrails():
    cov, inv, logdet, sds, corr = c._covariance_from_cholesky_params(
        np.array([0.0, -0.1, -0.2, 0.1, -0.1, 0.05])
    )
    assert cov.shape == inv.shape == corr.shape == (3, 3)
    assert np.all(np.linalg.eigvalsh(cov) > 0)
    assert np.all(sds > 0)
    assert np.isfinite(logdet)
    with pytest.raises(ValueError, match="six finite"):
        c._covariance_from_cholesky_params(np.zeros(5))
    with pytest.raises(ValueError, match="six finite"):
        c._covariance_from_cholesky_params(np.array([0, 0, 0, 0, 0, np.nan]))
    with pytest.raises(ValueError, match="invalid size"):
        c._decode_theta(np.zeros(2), 1, 1)

    with pytest.raises(ValueError, match="n_participants"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            n_participants=5
        )
    with pytest.raises(ValueError, match="n_items"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(n_items=5)
    with pytest.raises(ValueError, match="repeats"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(repeats=0)
    with pytest.raises(ValueError, match="seed"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(seed=-1)
    with pytest.raises(ValueError, match="fixed-effect"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            participant_mean_slope=np.nan
        )
    with pytest.raises(ValueError, match="finite"):
        c._simulation_covariance(np.nan, 1, 1, 0, 0, 0)
    with pytest.raises(ValueError, match="positive"):
        c._simulation_covariance(0, 1, 1, 0, 0, 0)
    with pytest.raises(ValueError, match="strictly inside"):
        c._simulation_covariance(1, 1, 1, 1, 0, 0)
    with pytest.raises(ValueError, match="positive definite"):
        c._simulation_covariance(1, 1, 1, 0.9, 0.9, -0.9)


def test_low_level_failure_paths_and_pinv_fallback(simulated, fitted, monkeypatch):
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
        participant_slope,
        item_slope,
    ) = c._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["participant_slope_predictor", "item_slope_predictor"],
        ["scale_predictor"],
        "participant_slope_predictor",
        "item_slope_predictor",
        standardize_numeric=False,
    )
    theta = c._initial_theta(y, X, Z)
    beta, gamma, participant, item = c._decode_theta(theta, X.shape[1], Z.shape[1])

    with pytest.raises(ValueError, match="wrong dimension"):
        c._joint_logposterior_grad_hess(
            np.zeros(1),
            y,
            X @ beta,
            Z @ gamma,
            participant_slope,
            item_slope,
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
        c._joint_logposterior_grad_hess(
            np.zeros(3 * (len(plev) + len(ilev))),
            y[:-1],
            (X @ beta)[:-1],
            (Z @ gamma)[:-1],
            participant_slope,
            item_slope[:-1],
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
    assert (
        c._laplace_loglik(
            malformed,
            y,
            X,
            Z,
            participant_slope,
            item_slope,
            pidx,
            iidx,
            len(plev),
            len(ilev),
            mode_max_steps=2,
            mode_tol=1e-6,
        )
        == -np.inf
    )
    assert c._laplace_loglik(
        malformed,
        y,
        X,
        Z,
        participant_slope,
        item_slope,
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

    monkeypatch.setattr(c.np.linalg, "inv", fail_once)
    ptab, itab = c._random_effect_tables(
        np.zeros(6),
        np.eye(6),
        np.array(["p"]),
        np.array(["i"]),
    )
    assert len(ptab) == len(itab) == 1
    monkeypatch.setattr(c.np.linalg, "inv", original_inv)

    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        object(), {}
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, []
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, {"payload": {}}
    )
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, {"payload": [], "sha256": 3}
    )
    malformed_cert = {"payload": {"x": np.nan}, "sha256": "x"}
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
        fitted, malformed_cert
    )
    with pytest.raises(TypeError):
        c.create_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
            object()
        )
    diagnostics = dict(fitted.diagnostics)
    diagnostics["converged"] = False
    bad_result = c.GazepointCrossedHierarchicalLocationScaleRandomSlopesResult(
        **{**fitted.__dict__, "diagnostics": diagnostics}
    )
    with pytest.raises(ValueError, match="non-converged"):
        c.create_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
            bad_result
        )


def test_posterior_mode_defensive_branches(monkeypatch):
    y = np.array([0.1, -0.2])
    xb = np.zeros(2)
    zg = np.zeros(2)
    rp = np.array([-1.0, 1.0])
    ri = np.array([1.0, -1.0])
    pidx = np.zeros(2, dtype=int)
    iidx = np.zeros(2, dtype=int)
    cov_inv = np.eye(3)

    original_system = c._positive_definite_system
    calls = {"n": 0}

    def fail_first(matrix):
        calls["n"] += 1
        if calls["n"] == 1:
            raise np.linalg.LinAlgError
        return original_system(matrix)

    monkeypatch.setattr(c, "_positive_definite_system", fail_first)
    _mode, _hessian, _value, diagnostics = c._posterior_mode(
        y,
        xb,
        zg,
        rp,
        ri,
        pidx,
        iidx,
        1,
        1,
        cov_inv,
        0.0,
        cov_inv,
        0.0,
        max_steps=2,
        tol=1e-12,
    )
    assert not diagnostics["converged"]


def test_internal_covariance_consistency_guard(simulated, monkeypatch):
    prepared = c._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["participant_slope_predictor", "item_slope_predictor"],
        ["scale_predictor"],
        "participant_slope_predictor",
        "item_slope_predictor",
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
        participant_slope,
        item_slope,
    ) = prepared
    theta0 = c._initial_theta(y, X, Z)
    loglik, state = c._laplace_loglik(
        theta0,
        y,
        X,
        Z,
        participant_slope,
        item_slope,
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
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            simulated,
            "outcome",
            "participant",
            "item",
            participant_random_slope_col="participant_slope_predictor",
            item_random_slope_col="item_slope_predictor",
            mean_cols=["participant_slope_predictor", "item_slope_predictor"],
            scale_cols=["scale_predictor"],
            standardize_numeric=False,
            maxiter=1,
        )


def test_remaining_defensive_branches(simulated, monkeypatch):
    original_slogdet = c.np.linalg.slogdet
    monkeypatch.setattr(c.np.linalg, "slogdet", lambda matrix: (-1.0, np.nan))
    with pytest.raises(np.linalg.LinAlgError, match="not positive definite"):
        c._covariance_from_cholesky_params(np.zeros(6))
    monkeypatch.setattr(c.np.linalg, "slogdet", original_slogdet)

    frame = simulated.iloc[:6].copy()
    encoder = {
        "mean_spec": {
            "participant_slope_predictor": {
                "kind": "numeric",
                "center": 0.0,
                "scale": np.nan,
            }
        }
    }
    with pytest.raises(ValueError, match="invalid fitted scaling factor"):
        c._slope_values(
            frame,
            frame["participant"].astype(str).to_numpy(),
            "participant_slope_predictor",
            ["participant_slope_predictor"],
            encoder,
            role_name="participant",
        )
    encoder["mean_spec"]["participant_slope_predictor"]["scale"] = 1.0
    frame["participant_slope_predictor"] = 1.0
    with pytest.raises(ValueError, match="within-sample variation"):
        c._slope_values(
            frame,
            frame["participant"].astype(str).to_numpy(),
            "participant_slope_predictor",
            ["participant_slope_predictor"],
            encoder,
            role_name="participant",
        )

    y = np.array([0.1, -0.2])
    xb = np.zeros(2)
    zg = np.zeros(2)
    rp = np.array([-1.0, 1.0])
    ri = np.array([1.0, -1.0])
    pidx = np.zeros(2, dtype=int)
    iidx = np.zeros(2, dtype=int)
    cov_inv = np.eye(3)
    _mode, _hessian, _value, diagnostics = c._posterior_mode(
        y,
        xb,
        zg,
        rp,
        ri,
        pidx,
        iidx,
        1,
        1,
        cov_inv,
        0.0,
        cov_inv,
        0.0,
        max_steps=0,
        tol=1e-12,
    )
    assert diagnostics["iterations"] == 0

    original_solve = c.np.linalg.solve
    monkeypatch.setattr(
        c.np.linalg,
        "solve",
        lambda matrix, vector: np.full_like(vector, np.nan, dtype=float),
    )
    _mode, _hessian, _value, diagnostics = c._posterior_mode(
        y,
        xb,
        zg,
        rp,
        ri,
        pidx,
        iidx,
        1,
        1,
        cov_inv,
        0.0,
        cov_inv,
        0.0,
        max_steps=2,
        tol=1e-12,
    )
    assert not diagnostics["converged"]
    monkeypatch.setattr(c.np.linalg, "solve", original_solve)

    X = np.column_stack([np.ones(4), np.arange(4.0)])
    y_exact = 1.0 + 2.0 * np.arange(4.0)
    Z = np.ones((4, 1))
    theta = c._initial_theta(y_exact, X, Z)
    assert np.isfinite(theta).all()

    good_theta = c._initial_theta(np.array([0.1, 0.2]), np.ones((2, 1)), np.ones((2, 1)))
    monkeypatch.setattr(
        c,
        "_posterior_mode",
        lambda *args, **kwargs: (
            np.zeros(6),
            np.eye(6),
            np.nan,
            {
                "converged": True,
                "iterations": 1,
                "max_abs_gradient": 0.0,
                "hessian_jitter": 0.0,
                "logdet_negative_hessian": 0.0,
            },
        ),
    )
    assert c._laplace_loglik(
        good_theta,
        np.array([0.1, 0.2]),
        np.ones((2, 1)),
        np.ones((2, 1)),
        rp,
        ri,
        pidx,
        iidx,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    ) == -np.inf

    with pytest.raises(ValueError, match="Missing required random-slope"):
        c._prediction_slope_values(
            simulated.drop(columns="participant_slope_predictor"),
            "participant_slope_predictor",
            {"mean_spec": {}},
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
        c.fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
            simulated,
            "outcome",
            "participant",
            "item",
            participant_random_slope_col="participant_slope_predictor",
            item_random_slope_col="item_slope_predictor",
            mean_cols=["participant_slope_predictor", "item_slope_predictor"],
            scale_cols=["scale_predictor"],
            standardize_numeric=False,
            maxiter=1,
        )