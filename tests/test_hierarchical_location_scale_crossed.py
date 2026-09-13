from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from scipy.optimize._numdiff import approx_derivative

import gpbiometricspy.hierarchical_location_scale_crossed as c


@pytest.fixture(scope="module")
def simulated():
    return c.simulate_gazepoint_crossed_hierarchical_location_scale(
        n_participants=6, n_items=6, seed=456
    )


@pytest.fixture(scope="module")
def fitted(simulated):
    return c.fit_gazepoint_crossed_hierarchical_location_scale(
        simulated,
        "outcome",
        "participant",
        "item",
        mean_cols=["mean_predictor"],
        scale_cols=["scale_predictor"],
        standardize_numeric=False,
        maxiter=100,
    )


def test_simulation_reproducibility_and_truth():
    a = c.simulate_gazepoint_crossed_hierarchical_location_scale(seed=9)
    b = c.simulate_gazepoint_crossed_hierarchical_location_scale(seed=9)
    pd.testing.assert_frame_equal(a, b)
    assert a.attrs["truth"]["seed"] == 9
    assert a.shape == (80, 5)


def test_fit_result_contract_and_prediction_levels(fitted, simulated):
    result = fitted
    assert result.diagnostics["converged"]
    assert result.metadata["n_participants"] == 6
    assert result.metadata["n_items"] == 6
    assert result.metadata["latent_dimension"] == 24
    assert result.participant_covariance.shape == (2, 2)
    assert result.item_covariance.shape == (2, 2)
    assert not result.parameter_vector.flags.writeable
    assert not result.participant_covariance.flags.writeable
    assert len(result.participant_random_effects) == 6
    assert len(result.item_random_effects) == 6
    assert result.mean_coef[1] > 0
    assert result.scale_coef[1] > 0

    rows = simulated.iloc[:4].copy()
    rows.loc[rows.index[1], "participant"] = "new_participant"
    rows.loc[rows.index[2], "item"] = "new_item"
    rows.loc[rows.index[3], ["participant", "item"]] = ["new_p2", "new_i2"]
    pred = c.predict_gazepoint_crossed_hierarchical_location_scale(result, rows)
    assert pred["prediction_level"].tolist() == [
        "conditional_participant_item",
        "population_participant_conditional_item",
        "conditional_participant_population_item",
        "population_participant_item",
    ]
    population = c.predict_gazepoint_crossed_hierarchical_location_scale(
        result, rows, include_random_effects=False
    )
    assert set(population["prediction_level"]) == {"population_fixed_effects"}
    assert np.isfinite(population["predicted_scale"]).all()
    with pytest.raises(ValueError, match="unseen participant or item"):
        c.predict_gazepoint_crossed_hierarchical_location_scale(
            result, rows, unknown_levels="error"
        )


def test_certificate_roundtrip_and_key_order(fitted):
    cert = c.create_gazepoint_crossed_hierarchical_location_scale_certificate(fitted)
    assert c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, cert)
    reversed_payload = dict(reversed(list(cert["payload"].items())))
    import json, hashlib
    digest = hashlib.sha256(json.dumps(reversed_payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    reordered = {"payload": reversed_payload, "sha256": digest}
    assert c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, reordered)
    bad = copy.deepcopy(cert); bad["payload"]["n_rows"] += 1
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, bad)
    bad2 = copy.deepcopy(cert); bad2["sha256"] = "0" * 64
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, bad2)


def test_analytic_latent_derivatives_match_finite_difference(simulated):
    _frame, y, plev, pidx, ilev, iidx, X, Z, *_ = c._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        ["mean_predictor"],
        ["scale_predictor"],
        standardize_numeric=False,
    )
    theta = c._initial_theta(y, X, Z)
    beta, gamma, participant, item = c._decode_theta(theta, X.shape[1], Z.shape[1])
    rng = np.random.default_rng(4)
    b = rng.normal(scale=0.02, size=2 * (len(plev) + len(ilev)))
    args = (y, X @ beta, Z @ gamma, pidx, iidx, len(plev), len(ilev), participant[1], participant[2], item[1], item[2])
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


def test_prepare_design_guardrails(simulated, monkeypatch):
    with pytest.raises(TypeError):
        c._prepare_fit_data([], "outcome", "participant", "item", [], [], standardize_numeric=True)
    with pytest.raises(ValueError, match="must be distinct"):
        c._prepare_fit_data(simulated, "outcome", "participant", "participant", [], [], standardize_numeric=True)
    with pytest.raises(ValueError, match="must not reuse"):
        c._prepare_fit_data(simulated, "outcome", "participant", "item", ["participant"], [], standardize_numeric=True)
    with pytest.raises(ValueError, match="Missing required"):
        c._prepare_fit_data(simulated.drop(columns="outcome"), "outcome", "participant", "item", [], [], standardize_numeric=True)
    empty = simulated.copy(); empty["outcome"] = np.nan
    with pytest.raises(ValueError, match="No complete"):
        c._prepare_fit_data(empty, "outcome", "participant", "item", [], [], standardize_numeric=True)
    few_p = simulated[simulated.participant.isin(simulated.participant.unique()[:3])]
    with pytest.raises(ValueError, match="at least four"):
        c._prepare_fit_data(few_p, "outcome", "participant", "item", [], [], standardize_numeric=True)
    bad = simulated.copy()
    p0 = bad.participant.unique()[0]
    bad = bad[~((bad.participant == p0) & (bad.item != bad.item.unique()[0]))]
    with pytest.raises(ValueError, match="Every participant"):
        c._prepare_fit_data(bad, "outcome", "participant", "item", [], [], standardize_numeric=True)
    bad = simulated.copy(); i0 = bad.item.unique()[0]
    p0 = bad.participant.unique()[0]
    bad = bad[~((bad.item == i0) & (bad.participant != p0))]
    with pytest.raises(ValueError, match="Every item"):
        c._prepare_fit_data(bad, "outcome", "participant", "item", [], [], standardize_numeric=True)
    monkeypatch.setattr(c, "_incidence_connected", lambda *args: False)
    with pytest.raises(ValueError, match="must be connected"):
        c._prepare_fit_data(simulated, "outcome", "participant", "item", [], [], standardize_numeric=True)


def test_fit_argument_guardrails_and_latent_limit(simulated):
    common = dict(data=simulated, outcome_col="outcome", participant_col="participant", item_col="item")
    with pytest.raises(ValueError, match="maxiter"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(**common, maxiter=0)
    with pytest.raises(ValueError, match="mode_max_steps"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(**common, mode_max_steps=0)
    with pytest.raises(ValueError, match="mode_tol"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(**common, mode_tol=np.nan)
    with pytest.raises(ValueError, match="max_latent_dimension"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(**common, max_latent_dimension=15)
    with pytest.raises(ValueError, match="exceeds"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(**common, max_latent_dimension=16)


def test_prediction_guardrails(fitted, simulated, monkeypatch):
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale(object(), simulated)
    with pytest.raises(TypeError):
        c.predict_gazepoint_crossed_hierarchical_location_scale(fitted, [])
    with pytest.raises(ValueError, match="unknown_levels"):
        c.predict_gazepoint_crossed_hierarchical_location_scale(fitted, simulated, unknown_levels="x")
    with pytest.raises(ValueError, match="Missing required prediction"):
        c.predict_gazepoint_crossed_hierarchical_location_scale(fitted, simulated.drop(columns="item"))
    bad = simulated.copy(); bad.loc[0, "item"] = None
    with pytest.raises(ValueError, match="must be non-missing"):
        c.predict_gazepoint_crossed_hierarchical_location_scale(fitted, bad)
    original = c._apply_encoder
    calls = {"n": 0}
    def wrong(*args, **kwargs):
        matrix, terms = original(*args, **kwargs); calls["n"] += 1
        if calls["n"] == 1: terms = tuple([*terms, "wrong"])
        return matrix, terms
    monkeypatch.setattr(c, "_apply_encoder", wrong)
    with pytest.raises(RuntimeError, match="does not match"):
        c.predict_gazepoint_crossed_hierarchical_location_scale(fitted, simulated.iloc[:2])


def test_simulation_guardrails():
    with pytest.raises(ValueError, match="n_participants"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale(n_participants=3)
    with pytest.raises(ValueError, match="n_items"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale(n_items=3)
    with pytest.raises(ValueError, match="repeats"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale(repeats=0)
    with pytest.raises(ValueError, match="fixed-effect"):
        c.simulate_gazepoint_crossed_hierarchical_location_scale(mean_slope=np.nan)
    with pytest.raises(ValueError, match="finite"):
        c._simulation_covariance(np.nan, 1, 0)
    with pytest.raises(ValueError, match="positive"):
        c._simulation_covariance(0, 1, 0)
    with pytest.raises(ValueError, match="strictly inside"):
        c._simulation_covariance(1, 1, 1)
    assert np.linalg.det(c._simulation_covariance(1, 1, 0.998)) > 0


def test_low_level_failure_and_fallback_branches(simulated, fitted, monkeypatch):
    with pytest.raises(ValueError, match="must be finite"):
        c._covariance_from_params(np.nan, 0, 0)
    with pytest.raises(ValueError, match="invalid size"):
        c._decode_theta(np.zeros(2), 1, 1)
    assert c._incidence_connected(np.array([0,0,1,1]), np.array([0,1,0,1]), 2, 2)
    assert not c._incidence_connected(np.array([0,1]), np.array([0,1]), 2, 2)
    with pytest.raises(ValueError, match="wrong dimension"):
        c._joint_logposterior_grad_hess(np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1,dtype=int), np.zeros(1,dtype=int), 1, 1, np.eye(2), 0, np.eye(2), 0)
    with pytest.raises(ValueError, match="non-empty square"):
        c._positive_definite_system(np.array([1.0]))
    with pytest.raises(np.linalg.LinAlgError, match="non-finite"):
        c._positive_definite_system(np.array([[np.nan]]))
    system, chol, jitter = c._positive_definite_system(np.array([[1.0,0.0],[0.0,-1e-9]]))
    assert jitter > 0 and np.all(np.linalg.eigvalsh(system) > 0) and chol.shape == (2,2)
    original_inv = np.linalg.inv
    count = {"n":0}
    def fail_once(x):
        count["n"] += 1
        if count["n"] == 1: raise np.linalg.LinAlgError
        return original_inv(x)
    monkeypatch.setattr(c.np.linalg, "inv", fail_once)
    mode = np.zeros(4); H = np.eye(4)
    ptab, itab = c._random_effect_tables(mode, H, np.array(["p"]), np.array(["i"]))
    assert len(ptab) == len(itab) == 1
    monkeypatch.setattr(c.np.linalg, "inv", original_inv)

    _frame, y, plev, pidx, ilev, iidx, X, Z, *_ = c._prepare_fit_data(simulated, "outcome", "participant", "item", [], [], standardize_numeric=True)
    assert c._laplace_loglik(np.array([np.nan]*8), y, X, Z, pidx, iidx, len(plev), len(ilev), mode_max_steps=2, mode_tol=1e-6) == -np.inf
    pair = c._laplace_loglik(np.array([np.nan]*8), y, X, Z, pidx, iidx, len(plev), len(ilev), mode_max_steps=2, mode_tol=1e-6, return_state=True)
    assert pair == (-np.inf, None)

    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(object(), {})
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, [])
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, {"payload": {}})
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, {"payload": [], "sha256": 3})
    malformed = {"payload": {"x": np.nan}, "sha256": "x"}
    assert not c.validate_gazepoint_crossed_hierarchical_location_scale_certificate(fitted, malformed)
    with pytest.raises(TypeError):
        c.create_gazepoint_crossed_hierarchical_location_scale_certificate(object())
    diag = dict(fitted.diagnostics); diag["converged"] = False
    bad_result = c.GazepointCrossedHierarchicalLocationScaleResult(
        **{**fitted.__dict__, "diagnostics": diag}
    )
    with pytest.raises(ValueError, match="non-converged"):
        c.create_gazepoint_crossed_hierarchical_location_scale_certificate(bad_result)


def test_remaining_defensive_branches(simulated, monkeypatch):
    original_slogdet = c.np.linalg.slogdet
    monkeypatch.setattr(c.np.linalg, "slogdet", lambda x: (-1.0, np.nan))
    with pytest.raises(np.linalg.LinAlgError, match="not positive definite"):
        c._covariance_from_params(0.0, 0.0, 0.0)
    monkeypatch.setattr(c.np.linalg, "slogdet", original_slogdet)

    categorical = simulated.copy()
    categorical["condition"] = np.where(np.arange(len(categorical)) % 2, "B", "A")
    prepared = c._prepare_fit_data(
        categorical,
        "outcome",
        "participant",
        "item",
        ["condition"],
        [],
        standardize_numeric=True,
    )
    assert "condition[B]" in prepared[8]
    original_apply = c._apply_encoder
    call = {"n": 0}
    def mismatch(*args, **kwargs):
        matrix, terms = original_apply(*args, **kwargs)
        call["n"] += 1
        if call["n"] == 1:
            terms = tuple([*terms, "mismatch"])
        return matrix, terms
    monkeypatch.setattr(c, "_apply_encoder", mismatch)
    with pytest.raises(RuntimeError, match="encoding mismatch"):
        c._prepare_fit_data(
            simulated,
            "outcome",
            "participant",
            "item",
            ["mean_predictor"],
            [],
            standardize_numeric=True,
        )
    monkeypatch.setattr(c, "_apply_encoder", original_apply)

    with pytest.raises(np.linalg.LinAlgError, match="could not be made"):
        c._positive_definite_system(np.array([[0.0, 1e20], [1e20, 0.0]]))

    _frame, y, plev, pidx, ilev, iidx, X, Z, *_ = c._prepare_fit_data(
        simulated,
        "outcome",
        "participant",
        "item",
        [],
        [],
        standardize_numeric=True,
    )
    theta = c._initial_theta(y, X, Z)
    beta, gamma, participant, item = c._decode_theta(theta, X.shape[1], Z.shape[1])
    mode_args = (
        y,
        X @ beta,
        Z @ gamma,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        participant[1],
        participant[2],
        item[1],
        item[2],
    )
    _, _, _, diag0 = c._posterior_mode(*mode_args, max_steps=0, tol=1e-6)
    assert diag0["iterations"] == 0

    original_solve = c.np.linalg.solve
    monkeypatch.setattr(c.np.linalg, "solve", lambda *args, **kwargs: (_ for _ in ()).throw(np.linalg.LinAlgError()))
    _, _, _, diag_solve = c._posterior_mode(*mode_args, max_steps=2, tol=1e-12)
    assert not diag_solve["converged"]
    monkeypatch.setattr(c.np.linalg, "solve", lambda *args, **kwargs: np.full(args[1].shape, np.nan))
    _, _, _, diag_nan = c._posterior_mode(*mode_args, max_steps=2, tol=1e-12)
    assert not diag_nan["converged"]
    monkeypatch.setattr(c.np.linalg, "solve", original_solve)

    original_mode = c._posterior_mode
    d = 2 * (len(plev) + len(ilev))
    fake_diag = {
        "converged": True,
        "iterations": 1,
        "max_abs_gradient": 0.0,
        "hessian_jitter": 0.0,
        "logdet_negative_hessian": 0.0,
    }
    monkeypatch.setattr(
        c,
        "_posterior_mode",
        lambda *args, **kwargs: (np.zeros(d), np.eye(d), np.inf, fake_diag),
    )
    assert c._laplace_loglik(
        theta,
        y,
        X,
        Z,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        mode_max_steps=2,
        mode_tol=1e-6,
    ) == -np.inf
    monkeypatch.setattr(c, "_posterior_mode", original_mode)

    flat_y = np.ones(5)
    flat_X = np.ones((5, 1))
    flat_Z = np.ones((5, 1))
    init = c._initial_theta(flat_y, flat_X, flat_Z)
    assert np.isfinite(init).all()

    original_det = c.np.linalg.det
    monkeypatch.setattr(c.np.linalg, "det", lambda x: 0.0)
    with pytest.raises(ValueError, match="positive definite"):
        c._simulation_covariance(1.0, 1.0, 0.0)
    monkeypatch.setattr(c.np.linalg, "det", original_det)


def test_fit_defensive_failure_states(simulated, monkeypatch):
    original_laplace = c._laplace_loglik
    original_minimize = c.minimize
    def invalid_laplace(*args, return_state=False, **kwargs):
        return (-np.inf, None) if return_state else -np.inf
    monkeypatch.setattr(c, "_laplace_loglik", invalid_laplace)
    monkeypatch.setattr(
        c,
        "minimize",
        lambda fun, x0, **kwargs: SimpleNamespace(
            x=np.asarray(x0), success=False, status=2, message="synthetic", nit=0, nfev=1
        ),
    )
    with pytest.raises(RuntimeError, match="finite converged Laplace"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(
            simulated,
            "outcome",
            "participant",
            "item",
            maxiter=1,
        )

    monkeypatch.setattr(c, "_laplace_loglik", original_laplace)
    monkeypatch.setattr(c, "minimize", original_minimize)
    baseline = c.fit_gazepoint_crossed_hierarchical_location_scale(
        simulated,
        "outcome",
        "participant",
        "item",
        maxiter=80,
    )
    _frame, y, plev, pidx, ilev, iidx, X, Z, *_ = c._prepare_fit_data(
        simulated, "outcome", "participant", "item", [], [], standardize_numeric=True
    )
    ll, state = original_laplace(
        baseline.parameter_vector,
        y,
        X,
        Z,
        pidx,
        iidx,
        len(plev),
        len(ilev),
        mode_max_steps=50,
        mode_tol=1e-6,
        return_state=True,
    )
    assert state is not None
    monkeypatch.setattr(
        c,
        "minimize",
        lambda fun, x0, **kwargs: SimpleNamespace(
            x=baseline.parameter_vector.copy(), success=True, status=0, message="ok", nit=1, nfev=1
        ),
    )
    monkeypatch.setattr(
        c,
        "_laplace_loglik",
        lambda *args, return_state=False, **kwargs: (ll, state) if return_state else ll,
    )
    original_decode = c._decode_theta
    def mismatched_decode(theta, p, q):
        beta, gamma, participant, item = original_decode(theta, p, q)
        changed = list(participant)
        changed[0] = participant[0] + np.eye(2)
        return beta, gamma, tuple(changed), item
    monkeypatch.setattr(c, "_decode_theta", mismatched_decode)
    with pytest.raises(RuntimeError, match="covariance decoding mismatch"):
        c.fit_gazepoint_crossed_hierarchical_location_scale(
            simulated,
            "outcome",
            "participant",
            "item",
            maxiter=1,
        )
