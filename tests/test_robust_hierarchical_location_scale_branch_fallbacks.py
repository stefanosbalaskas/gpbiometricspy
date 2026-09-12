from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.robust_hierarchical_location_scale as rls


def _tiny_data(seed=17):
    return rls.simulate_gazepoint_robust_hierarchical_location_scale(
        n_groups=4,
        observations_per_group=3,
        seed=seed,
    )


def test_posterior_mode_numerical_fallbacks(monkeypatch):
    y = np.array([0.0, 0.2, -0.1])
    zeros = np.zeros(3)

    def singular_solve(*args, **kwargs):
        raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(rls.np.linalg, "solve", singular_solve)
    mode, cov, value = rls._posterior_mode(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        5.0,
        max_steps=2,
    )
    assert np.isfinite(mode).all()
    assert np.isfinite(cov).all()
    assert np.isfinite(value)


def test_posterior_mode_nonfinite_step_rejection_and_hessian_repair(monkeypatch):
    y = np.array([0.0])
    zeros = np.zeros(1)

    monkeypatch.setattr(
        rls.np.linalg,
        "solve",
        lambda *args, **kwargs: np.array([np.nan, 0.0]),
    )
    mode, cov, _ = rls._posterior_mode(
        y, zeros, zeros, np.eye(2), 0.0, 5.0
    )
    assert np.isfinite(mode).all()
    assert np.isfinite(cov).all()

    def rejects_candidates(b, *args):
        b = np.asarray(b, dtype=float)
        if np.allclose(b, 0.0):
            return 0.0, np.ones(2), -np.eye(2)
        return -1e6, np.ones(2), -np.eye(2)

    monkeypatch.setattr(rls, "_group_logposterior_and_derivatives", rejects_candidates)
    monkeypatch.setattr(rls.np.linalg, "solve", np.linalg.solve)
    mode, cov, _ = rls._posterior_mode(
        y, zeros, zeros, np.eye(2), 0.0, 5.0, max_steps=1
    )
    assert np.allclose(mode, 0.0)
    assert np.isfinite(cov).all()

    def nonconcave_mode(b, *args):
        return 0.0, np.zeros(2), np.eye(2)

    monkeypatch.setattr(rls, "_group_logposterior_and_derivatives", nonconcave_mode)
    mode, cov, _ = rls._posterior_mode(
        y, zeros, zeros, np.eye(2), 0.0, 5.0
    )
    assert np.allclose(mode, 0.0)
    assert np.isfinite(cov).all()


def test_posterior_mode_natural_iteration_exhaustion(monkeypatch):
    def always_accepts(b, *args):
        b = np.asarray(b, dtype=float)
        return float(np.sum(b)), np.ones(2), -np.eye(2)

    monkeypatch.setattr(rls, "_group_logposterior_and_derivatives", always_accepts)
    monkeypatch.setattr(
        rls.np.linalg,
        "solve",
        lambda *args, **kwargs: -np.ones(2),
    )
    mode, cov, _ = rls._posterior_mode(
        np.array([0.0]),
        np.zeros(1),
        np.zeros(1),
        np.eye(2),
        0.0,
        5.0,
        max_steps=1,
    )
    assert np.allclose(mode, np.ones(2))
    assert np.isfinite(cov).all()


def test_adaptive_quadrature_fallback_and_invalid_jacobian(monkeypatch):
    y = np.array([0.0, 0.1])
    zeros = np.zeros(2)
    x1, x2, logw = rls._quadrature_nodes(3)

    original_cholesky = rls.np.linalg.cholesky

    def forced_cholesky_failure(*args, **kwargs):
        raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(rls.np.linalg, "cholesky", forced_cholesky_failure)
    value = rls._adaptive_group_integral(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        5.0,
        x1,
        x2,
        logw,
    )
    assert np.isfinite(value)
    monkeypatch.setattr(rls.np.linalg, "cholesky", original_cholesky)

    monkeypatch.setattr(
        rls,
        "_posterior_mode",
        lambda *args, **kwargs: (np.zeros(2), np.eye(2), 0.0),
    )
    monkeypatch.setattr(rls.np.linalg, "slogdet", lambda matrix: (0.0, -np.inf))
    assert rls._adaptive_group_integral(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        5.0,
        x1,
        x2,
        logw,
    ) == -np.inf
    assert rls._adaptive_group_integral(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        5.0,
        x1,
        x2,
        logw,
        moments=True,
    ) == (-np.inf, None)


def test_marginal_likelihood_and_initializer_defensive_paths(monkeypatch):
    y = np.array([0.0, 0.1])
    X = np.ones((2, 1))
    Z = np.ones((2, 1))
    groups = np.zeros(2, dtype=int)
    x1, x2, logw = rls._quadrature_nodes(3)

    with np.errstate(over="ignore", invalid="ignore"):
        assert rls._marginal_loglik(
            np.array([0.0, 0.0, 1000.0, 0.0, 0.0, np.log(4.0)]),
            y,
            X,
            Z,
            groups,
            1,
            x1,
            x2,
            logw,
        ) == -np.inf

    bad_covariance = np.array([0.0, 0.0, -np.inf, 0.0, 0.0, np.log(4.0)])
    assert rls._marginal_loglik(
        bad_covariance, y, X, Z, groups, 1, x1, x2, logw
    ) == -np.inf

    monkeypatch.setattr(
        rls,
        "_adaptive_group_integral",
        lambda *args, **kwargs: -np.inf,
    )
    valid = np.array([0.0, 0.0, -1.0, -1.0, 0.0, np.log(4.0)])
    assert rls._marginal_loglik(
        valid, y, X, Z, groups, 1, x1, x2, logw
    ) == -np.inf

    theta = rls._initial_theta(
        np.ones(4), np.ones((4, 1)), np.ones((4, 1))
    )
    assert np.isfinite(theta).all()
    assert np.isclose(theta[1], 0.0)


def test_fit_argument_convergence_and_objective_guardrails(monkeypatch):
    data = _tiny_data(seed=23)

    for bad_points in (2, 26, 3.0):
        with pytest.raises(ValueError, match="quadrature_points"):
            rls.fit_gazepoint_robust_hierarchical_location_scale(
                data, "outcome", "participant", quadrature_points=bad_points
            )
    for bad_maxiter in (0, 1.5):
        with pytest.raises(ValueError, match="maxiter"):
            rls.fit_gazepoint_robust_hierarchical_location_scale(
                data, "outcome", "participant", maxiter=bad_maxiter
            )
    for bad_tolerance in (0.0, np.nan):
        with pytest.raises(ValueError, match="tolerance"):
            rls.fit_gazepoint_robust_hierarchical_location_scale(
                data, "outcome", "participant", tolerance=bad_tolerance
            )

    def failed_minimize(fun, x0, **kwargs):
        bad = np.asarray(x0, dtype=float).copy()
        bad[-4] = 1000.0
        with np.errstate(over="ignore", invalid="ignore"):
            assert fun(bad) == 1e100
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            fun=float(fun(x0)),
            success=False,
            status=9,
            message="forced non-convergence",
        )

    monkeypatch.setattr(rls, "minimize", failed_minimize)
    with pytest.raises(RuntimeError, match="did not converge"):
        rls.fit_gazepoint_robust_hierarchical_location_scale(
            data,
            "outcome",
            "participant",
            quadrature_points=3,
        )

    result = rls.fit_gazepoint_robust_hierarchical_location_scale(
        data,
        "outcome",
        "participant",
        quadrature_points=3,
        require_convergence=False,
    )
    assert result.diagnostics["converged"] is False
    assert np.isnan(result.diagnostics["gradient_max_abs"])


def test_prediction_design_summary_and_certificate_type_guards(monkeypatch):
    result = rls.GazepointRobustHierarchicalLocationScaleResult(
        mean_coef=(0.0,),
        scale_coef=(0.0,),
        mean_terms=("Intercept",),
        scale_terms=("Intercept",),
        tau_location=0.2,
        tau_log_scale=0.1,
        rho=0.0,
        degrees_of_freedom=5.0,
        log_likelihood=-1.0,
        random_effects=pd.DataFrame([
            {
                "group": "P001",
                "location_re": 0.0,
                "log_scale_re": 0.0,
            }
        ]),
        metadata={
            "model_version": "student-t-hierarchical-location-scale-v1",
            "data_sha256": "b" * 64,
            "quadrature_points": 3,
            "group_col": "participant",
        },
        diagnostics={"converged": True},
        encoder={
            "mean_cols": (),
            "scale_cols": (),
            "mean_spec": {},
            "scale_spec": {},
            "standardize_numeric": True,
        },
        parameter_vector=np.zeros(6),
    )
    frame = pd.DataFrame({"participant": ["P001"]})

    with pytest.raises(TypeError):
        rls._prediction_design(object(), frame)
    with pytest.raises(TypeError):
        rls._prediction_design(result, object())
    with pytest.raises(TypeError):
        rls.summarize_gazepoint_robust_hierarchical_location_scale(object())
    with pytest.raises(TypeError):
        rls.create_gazepoint_robust_hierarchical_location_scale_certificate(object())

    original = rls._apply_encoder

    def mismatched_terms(data, cols, spec, *, allow_unknown):
        matrix, _ = original(data, cols, spec, allow_unknown=allow_unknown)
        return matrix, ("mismatch",)

    monkeypatch.setattr(rls, "_apply_encoder", mismatched_terms)
    with pytest.raises(ValueError, match="does not match"):
        rls._prediction_design(result, frame)
    monkeypatch.setattr(rls, "_apply_encoder", original)

    with pytest.raises(ValueError, match="Missing group column"):
        rls.predict_gazepoint_robust_hierarchical_location_scale(
            result,
            pd.DataFrame(index=[0]),
        )

    assert not rls.validate_gazepoint_robust_hierarchical_location_scale_certificate(
        result, []
    )
    assert not rls.validate_gazepoint_robust_hierarchical_location_scale_certificate(
        result, {"payload": {}}
    )
    assert not rls.validate_gazepoint_robust_hierarchical_location_scale_certificate(
        result,
        {"payload": {"bad": object()}, "sha256": "bad"},
    )


def test_simulation_argument_guardrails():
    invalid_cases = [
        {"n_groups": 2},
        {"observations_per_group": 1},
        {"beta": (1.0,)},
        {"gamma": (1.0,)},
        {"tau_location": -0.1},
        {"tau_log_scale": -0.1},
        {"rho": 1.0},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(ValueError):
            rls.simulate_gazepoint_robust_hierarchical_location_scale(**kwargs)
