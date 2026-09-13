from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.hierarchical_location_scale_random_slope as rs


@pytest.fixture(scope="module")
def fitted_case():
    data = rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
        n_groups=10, observations_per_group=7, seed=42
    )
    result = rs.fit_gazepoint_hierarchical_location_scale_random_slope(
        data,
        "outcome",
        "participant",
        mean_cols=["x"],
        scale_cols=["x"],
        random_slope_col="x",
        quadrature_points=3,
        maxiter=100,
        standardize_numeric=False,
    )
    return data, result


def test_fit_prediction_summary_certificate_and_immutability(fitted_case):
    data, result = fitted_case
    assert result.diagnostics["converged"] is True
    assert result.metadata["quadrature_scheme"] == "three-dimensional adaptive Gauss-Hermite"
    assert result.mean_terms == ("Intercept", "x")
    assert result.scale_terms == ("Intercept", "x")
    assert result.random_effect_covariance.shape == (3, 3)
    assert np.linalg.eigvalsh(result.random_effect_covariance).min() > 0
    assert result.tau_location_intercept > 0
    assert result.tau_location_slope > 0
    assert result.tau_log_scale > 0
    assert len(result.random_effects) == 10

    seen = data.iloc[[0]].copy()
    unseen = seen.copy()
    unseen["participant"] = "NEW"
    pop = rs.predict_gazepoint_hierarchical_location_scale_random_slope(
        result, seen, include_random_effects=False
    )
    p_seen = rs.predict_gazepoint_hierarchical_location_scale_random_slope(result, seen)
    p_unseen = rs.predict_gazepoint_hierarchical_location_scale_random_slope(result, unseen)
    custom = seen.rename(columns={"participant": "subject"})
    p_custom = rs.predict_gazepoint_hierarchical_location_scale_random_slope(
        result, custom, group_col="subject"
    )
    assert pop.random_effect_source.iloc[0] == "population"
    assert p_seen.random_effect_source.iloc[0] == "empirical_bayes"
    assert p_unseen.random_effect_source.iloc[0] == "population_unseen_group"
    assert p_custom.random_effect_source.iloc[0] == "empirical_bayes"
    assert np.isfinite(p_seen.predicted_mean.iloc[0])
    assert p_seen.predicted_scale.iloc[0] > 0

    summary = rs.summarize_gazepoint_hierarchical_location_scale_random_slope(result)
    assert summary["class"] == "gazepoint_hierarchical_location_scale_random_slope_summary"
    assert summary["random_effect_covariance"].shape == (3, 3)
    assert set(summary["fixed_effects"]["equation"]) == {"location", "log_scale"}

    cert = rs.create_gazepoint_hierarchical_location_scale_random_slope_certificate(result)
    assert len(cert["sha256"]) == 64
    assert len(cert["payload"]["random_effects_sha256"]) == 64
    reordered = {
        "sha256": cert["sha256"],
        "payload": dict(reversed(list(cert["payload"].items()))),
    }
    assert rs.validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
        result, reordered
    )
    shuffled = replace(
        result,
        random_effects=result.random_effects.sample(frac=1, random_state=1),
    )
    assert (
        rs.create_gazepoint_hierarchical_location_scale_random_slope_certificate(shuffled)[
            "payload"
        ]["random_effects_sha256"]
        == cert["payload"]["random_effects_sha256"]
    )
    mutated_re = result.random_effects.copy()
    mutated_re.loc[0, "location_slope_re"] += 0.2
    mutated = replace(result, random_effects=mutated_re)
    assert not rs.validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
        mutated, cert
    )

    with pytest.raises(TypeError):
        result.metadata["n_obs"] = 0
    with pytest.raises(ValueError):
        result.parameter_vector[0] = 0
    with pytest.raises(ValueError):
        result.random_effect_covariance[0, 0] = 0


def test_derivatives_and_nodes_match_finite_differences():
    rng = np.random.default_rng(3)
    y = rng.normal(size=7)
    xb = rng.normal(size=7)
    zg = rng.normal(scale=0.1, size=7)
    r = rng.normal(size=7)
    params = np.array(
        [np.log(0.5), np.log(0.3), np.log(0.2), 0.05, -0.03, 0.02]
    )
    cov, inv, ld, sds, corr = rs._covariance_from_cholesky_params(params)
    assert cov.shape == (3, 3)
    assert inv.shape == (3, 3)
    assert sds.shape == (3,)
    assert corr.shape == (3, 3)
    b = np.array([0.1, -0.05, 0.08])
    h, grad, hess = rs._group_logposterior_and_derivatives(
        b, y, xb, zg, r, inv, ld
    )
    eps = 1e-6
    gn = np.zeros(3)
    hn = np.zeros((3, 3))
    for k in range(3):
        e = np.zeros(3)
        e[k] = eps
        hp = rs._group_logposterior_and_derivatives(
            b + e, y, xb, zg, r, inv, ld
        )
        hm = rs._group_logposterior_and_derivatives(
            b - e, y, xb, zg, r, inv, ld
        )
        gn[k] = (hp[0] - hm[0]) / (2 * eps)
        hn[:, k] = (hp[1] - hm[1]) / (2 * eps)
    assert np.max(np.abs(grad - gn)) < 1e-5
    assert np.max(np.abs(hess - hn)) < 1e-5
    nodes = rs._group_logposterior_nodes(
        np.array([b[0]]),
        np.array([b[1]]),
        np.array([b[2]]),
        y,
        xb,
        zg,
        r,
        inv,
        ld,
    )
    assert nodes[0] == pytest.approx(h)


def test_input_guardrails_and_random_slope_identifiability():
    data = rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
        n_groups=6, observations_per_group=4, seed=7
    )
    common = dict(
        data=data,
        outcome_col="outcome",
        group_col="participant",
        mean_cols=["x"],
        random_slope_col="x",
        quadrature_points=3,
        maxiter=2,
        require_convergence=False,
    )
    for bad in (2, 12, 3.5):
        with pytest.raises(ValueError, match="quadrature_points"):
            rs.fit_gazepoint_hierarchical_location_scale_random_slope(
                **{**common, "quadrature_points": bad}
            )
    with pytest.raises(ValueError, match="maxiter"):
        rs.fit_gazepoint_hierarchical_location_scale_random_slope(
            **{**common, "maxiter": 0}
        )
    for bad in (0, np.nan):
        with pytest.raises(ValueError, match="tolerance"):
            rs.fit_gazepoint_hierarchical_location_scale_random_slope(
                **{**common, "tolerance": bad}
            )

    with pytest.raises(ValueError, match="also be included"):
        rs.fit_gazepoint_hierarchical_location_scale_random_slope(
            data,
            "outcome",
            "participant",
            mean_cols=[],
            random_slope_col="x",
            quadrature_points=3,
            maxiter=2,
            require_convergence=False,
        )
    cat = data.copy()
    cat["condition"] = np.tile(["A", "B", "A", "B"], 6)
    with pytest.raises(ValueError, match="must be numeric"):
        rs.fit_gazepoint_hierarchical_location_scale_random_slope(
            cat,
            "outcome",
            "participant",
            mean_cols=["condition"],
            random_slope_col="condition",
            quadrature_points=3,
            maxiter=2,
            require_convergence=False,
        )
    five = data[data.participant != "P006"]
    with pytest.raises(ValueError, match="at least six"):
        rs.fit_gazepoint_hierarchical_location_scale_random_slope(
            five,
            "outcome",
            "participant",
            mean_cols=["x"],
            random_slope_col="x",
            quadrature_points=3,
            maxiter=2,
            require_convergence=False,
        )
    flat = data.copy()
    flat.loc[flat.participant == "P001", "x"] = 1.0
    with pytest.raises(ValueError, match="must vary within every"):
        rs.fit_gazepoint_hierarchical_location_scale_random_slope(
            flat,
            "outcome",
            "participant",
            mean_cols=["x"],
            random_slope_col="x",
            quadrature_points=3,
            maxiter=2,
            require_convergence=False,
        )
    allflat = data.copy()
    allflat["x"] = 1.0
    frame, _, groups, _, _, _, _, _, _, enc = rs._prepare_fit_data(
        allflat,
        "outcome",
        "participant",
        ["x"],
        [],
        standardize_numeric=True,
    )
    with pytest.raises(ValueError, match="within-sample variation"):
        rs._random_slope_values(frame, groups, "x", ["x"], enc)


def test_covariance_and_simulator_guardrails():
    with pytest.raises(ValueError, match="six finite"):
        rs._covariance_from_cholesky_params(np.zeros(5))
    with pytest.raises(ValueError, match="six finite"):
        rs._covariance_from_cholesky_params(np.r_[np.nan, np.zeros(5)])
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(np.linalg.LinAlgError):
            rs._covariance_from_cholesky_params(
                np.array([1000, 0, 0, 0, 0, 0], float)
            )

    with pytest.raises(ValueError, match="six groups"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(n_groups=5)
    with pytest.raises(ValueError, match="three observations"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
            observations_per_group=2
        )
    with pytest.raises(ValueError, match="two finite"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(beta=(1,))
    with pytest.raises(ValueError, match="two finite"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
            gamma=(0, np.nan)
        )
    with pytest.raises(ValueError, match="positive finite"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
            tau_location_slope=0
        )
    with pytest.raises(ValueError, match="positive finite"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
            tau_log_scale=np.nan
        )
    with pytest.raises(ValueError, match="strictly between"):
        rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
            rho_intercept_slope=0.99
        )
    with pytest.raises(ValueError, match="strictly between"):
        rs._correlation_matrix(np.nan, 0, 0)
    with pytest.raises(ValueError, match="positive definite"):
        rs._correlation_matrix(0.9, 0.9, -0.9)


def test_prediction_summary_and_certificate_type_guardrails(fitted_case, monkeypatch):
    data, result = fitted_case
    with pytest.raises(TypeError):
        rs._prediction_design(object(), data.head())
    with pytest.raises(TypeError):
        rs._prediction_design(result, object())
    with pytest.raises(TypeError):
        rs.summarize_gazepoint_hierarchical_location_scale_random_slope(object())
    with pytest.raises(TypeError):
        rs.create_gazepoint_hierarchical_location_scale_random_slope_certificate(object())
    nonconv = replace(result, diagnostics={"converged": False})
    with pytest.raises(ValueError, match="non-converged"):
        rs.create_gazepoint_hierarchical_location_scale_random_slope_certificate(
            nonconv
        )
    assert not rs.validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
        result, []
    )
    assert not rs.validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
        result, {"payload": {}}
    )
    assert not rs.validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
        result, {"payload": {"x": object()}, "sha256": "bad"}
    )
    cert = rs.create_gazepoint_hierarchical_location_scale_random_slope_certificate(result)
    bad = {"payload": dict(cert["payload"]), "sha256": cert["sha256"]}
    bad["payload"]["random_slope_col"] = "other"
    assert not rs.validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
        result, bad
    )

    with pytest.raises(ValueError, match="Missing group"):
        rs.predict_gazepoint_hierarchical_location_scale_random_slope(
            result, data.head().drop(columns="participant")
        )

    original = rs._apply_encoder

    def mismatch(frame, cols, spec, *, allow_unknown):
        matrix, _ = original(frame, cols, spec, allow_unknown=allow_unknown)
        return matrix, ("bad",)

    monkeypatch.setattr(rs, "_apply_encoder", mismatch)
    with pytest.raises(ValueError, match="does not match"):
        rs._prediction_design(result, data.head())
    monkeypatch.setattr(rs, "_apply_encoder", original)

    def permissive(frame, cols, spec, *, allow_unknown):
        is_mean = cols == list(result.encoder["mean_cols"])
        terms = result.mean_terms if is_mean else result.scale_terms
        return np.ones((len(frame), len(terms))), terms

    monkeypatch.setattr(rs, "_apply_encoder", permissive)
    bad_data = data.head().copy()
    bad_data["x"] = np.nan
    with pytest.raises(ValueError, match="Random-slope predictor"):
        rs._prediction_design(result, bad_data)


def test_internal_fallbacks_and_objective_paths(monkeypatch, fitted_case):
    data, _ = fitted_case
    y = np.ones(8)
    X = np.ones((8, 1))
    Z = np.ones((8, 1))
    theta0 = rs._initial_theta(y, X, Z)
    assert np.isfinite(theta0).all()

    _, inv, ld, _, _ = rs._covariance_from_cholesky_params(
        np.array([np.log(0.4), np.log(0.3), np.log(0.2), 0, 0, 0])
    )
    yv = np.array([0.2, -0.1, 0.4])
    xb = np.zeros(3)
    zg = np.zeros(3)
    rv = np.array([-1.0, 0.0, 1.0])
    original_solve = rs.np.linalg.solve
    monkeypatch.setattr(
        rs.np.linalg,
        "solve",
        lambda *args, **kwargs: (_ for _ in ()).throw(np.linalg.LinAlgError()),
    )
    b, cp, _ = rs._posterior_mode(yv, xb, zg, rv, inv, ld, max_steps=2)
    assert np.isfinite(b).all() and np.isfinite(cp).all()
    monkeypatch.setattr(rs.np.linalg, "solve", original_solve)

    monkeypatch.setattr(
        rs.np.linalg, "solve", lambda *args, **kwargs: np.full(3, np.nan)
    )
    b, _, _ = rs._posterior_mode(yv, xb, zg, rv, inv, ld, max_steps=2)
    assert np.isfinite(b).all()
    monkeypatch.setattr(rs.np.linalg, "solve", original_solve)

    orig_eig = rs.np.linalg.eigvalsh
    orig_inv = rs.np.linalg.inv
    monkeypatch.setattr(
        rs.np.linalg, "eigvalsh", lambda x: np.array([np.nan, 1, 1])
    )
    _, cp, _ = rs._posterior_mode(yv, xb, zg, rv, inv, ld, max_steps=0)
    assert np.allclose(cp, np.eye(3))
    monkeypatch.setattr(
        rs.np.linalg, "eigvalsh", lambda x: np.array([-1.0, 1.0, 2.0])
    )
    monkeypatch.setattr(
        rs.np.linalg,
        "inv",
        lambda x: (_ for _ in ()).throw(np.linalg.LinAlgError()),
    )
    _, cp, _ = rs._posterior_mode(yv, xb, zg, rv, inv, ld, max_steps=0)
    assert np.isfinite(cp).all()
    monkeypatch.setattr(rs.np.linalg, "eigvalsh", orig_eig)
    monkeypatch.setattr(rs.np.linalg, "inv", orig_inv)

    x0, x1, x2, logw = rs._quadrature_nodes(3)
    orig_chol = rs.np.linalg.cholesky
    monkeypatch.setattr(
        rs.np.linalg,
        "cholesky",
        lambda x: (_ for _ in ()).throw(np.linalg.LinAlgError()),
    )
    val, moments = rs._adaptive_group_integral(
        yv, xb, zg, rv, inv, ld, x0, x1, x2, logw, moments=True
    )
    assert np.isfinite(val) and moments is not None
    monkeypatch.setattr(rs.np.linalg, "cholesky", orig_chol)

    orig_slog = rs.np.linalg.slogdet
    monkeypatch.setattr(rs.np.linalg, "slogdet", lambda x: (0.0, np.nan))
    assert (
        rs._adaptive_group_integral(
            yv, xb, zg, rv, inv, ld, x0, x1, x2, logw
        )
        == -np.inf
    )
    assert rs._adaptive_group_integral(
        yv, xb, zg, rv, inv, ld, x0, x1, x2, logw, moments=True
    ) == (-np.inf, None)
    monkeypatch.setattr(rs.np.linalg, "slogdet", orig_slog)

    badtheta = np.r_[0.0, 0.0, np.nan, np.zeros(5)]
    assert (
        rs._marginal_loglik(
            badtheta,
            yv,
            X[:3],
            Z[:3],
            rv,
            np.array([0, 0, 0]),
            1,
            x0,
            x1,
            x2,
            logw,
        )
        == -np.inf
    )
    theta = np.r_[
        np.nan,
        0.0,
        np.log(0.4),
        np.log(0.3),
        np.log(0.2),
        0,
        0,
        0,
    ]
    assert (
        rs._marginal_loglik(
            theta,
            yv,
            X[:3],
            Z[:3],
            rv,
            np.array([0, 0, 0]),
            1,
            x0,
            x1,
            x2,
            logw,
        )
        == -np.inf
    )
    orig_adaptive = rs._adaptive_group_integral
    monkeypatch.setattr(rs, "_adaptive_group_integral", lambda *a, **k: -np.inf)
    theta = np.r_[
        0.0,
        0.0,
        np.log(0.4),
        np.log(0.3),
        np.log(0.2),
        0,
        0,
        0,
    ]
    assert (
        rs._marginal_loglik(
            theta,
            yv,
            X[:3],
            Z[:3],
            rv,
            np.array([0, 0, 0]),
            1,
            x0,
            x1,
            x2,
            logw,
        )
        == -np.inf
    )
    monkeypatch.setattr(rs, "_adaptive_group_integral", orig_adaptive)

    def failed_minimize(objective, theta0, **kwargs):
        assert np.isfinite(objective(theta0))
        return SimpleNamespace(
            success=False,
            message="forced",
            x=theta0,
            fun=objective(theta0),
            status=9,
            nit=0,
            nfev=2,
            jac=np.zeros_like(theta0),
        )

    monkeypatch.setattr(rs, "minimize", failed_minimize)
    with pytest.raises(RuntimeError, match="did not converge"):
        rs.fit_gazepoint_hierarchical_location_scale_random_slope(
            data,
            "outcome",
            "participant",
            mean_cols=["x"],
            random_slope_col="x",
            quadrature_points=3,
            maxiter=2,
        )
    out = rs.fit_gazepoint_hierarchical_location_scale_random_slope(
        data,
        "outcome",
        "participant",
        mean_cols=["x"],
        random_slope_col="x",
        quadrature_points=3,
        maxiter=2,
        require_convergence=False,
    )
    assert out.diagnostics["converged"] is False


def test_synthetic_known_truth_random_slope_recovery():
    data = rs.simulate_gazepoint_hierarchical_location_scale_random_slope(
        n_groups=16,
        observations_per_group=8,
        tau_location_intercept=0.5,
        tau_location_slope=0.45,
        tau_log_scale=0.22,
        rho_intercept_slope=0.2,
        rho_intercept_log_scale=0.1,
        rho_slope_log_scale=-0.05,
        seed=21,
    )
    result = rs.fit_gazepoint_hierarchical_location_scale_random_slope(
        data,
        "outcome",
        "participant",
        mean_cols=["x"],
        scale_cols=["x"],
        random_slope_col="x",
        quadrature_points=3,
        maxiter=120,
        standardize_numeric=False,
    )
    assert result.diagnostics["converged"] is True
    assert result.mean_coef[1] > 0.25
    assert result.scale_coef[1] > 0.05
    assert result.tau_location_slope > 0.10
    assert np.linalg.eigvalsh(result.random_effect_covariance).min() > 0
