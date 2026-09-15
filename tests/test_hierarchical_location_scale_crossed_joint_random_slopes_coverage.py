from __future__ import annotations

import numpy as np
import pytest

import gpbiometricspy.hierarchical_location_scale_crossed_joint_random_slopes_core as core


def _minimal_laplace_inputs():
    y = np.array([0.1, 0.2], dtype=float)
    X = np.ones((2, 1), dtype=float)
    Z = np.ones((2, 1), dtype=float)
    theta = core._initial_theta(y, X, Z)
    participant_location = np.array([-1.0, 1.0], dtype=float)
    item_location = np.array([1.0, -1.0], dtype=float)
    participant_scale = np.array([-0.5, 0.5], dtype=float)
    item_scale = np.array([0.5, -0.5], dtype=float)
    participant_index = np.zeros(2, dtype=int)
    item_index = np.zeros(2, dtype=int)
    return (
        theta,
        y,
        X,
        Z,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
    )


def _posterior_inputs():
    y = np.array([0.1, -0.2], dtype=float)
    zeros = np.zeros(2, dtype=float)
    index = np.zeros(2, dtype=int)
    covariance_inverse = np.eye(4, dtype=float)
    return (
        y,
        zeros,
        zeros,
        np.array([-1.0, 1.0], dtype=float),
        np.array([1.0, -1.0], dtype=float),
        np.array([-0.5, 0.5], dtype=float),
        np.array([0.5, -0.5], dtype=float),
        index,
        index,
        1,
        1,
        covariance_inverse,
        0.0,
        covariance_inverse,
        0.0,
    )


def test_laplace_loglik_catches_posterior_mode_failure(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def fail_posterior_mode(*args, **kwargs):
        raise ValueError("synthetic posterior-mode failure")

    monkeypatch.setattr(core, "_posterior_mode", fail_posterior_mode)
    assert core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    ) == -np.inf
    assert core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
        return_state=True,
    ) == (-np.inf, None)


def test_laplace_loglik_rejects_nonconverged_or_jittered_mode(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def nonconverged(*args, **kwargs):
        return (
            np.zeros(8, dtype=float),
            np.eye(8, dtype=float),
            0.0,
            {
                "converged": False,
                "iterations": 1,
                "max_abs_gradient": 1.0,
                "hessian_jitter": 0.0,
                "logdet_negative_hessian": 0.0,
            },
        )

    monkeypatch.setattr(core, "_posterior_mode", nonconverged)
    assert core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    ) == -np.inf

    def jittered(*args, **kwargs):
        value = nonconverged(*args, **kwargs)
        diagnostics = dict(value[3])
        diagnostics["converged"] = True
        diagnostics["hessian_jitter"] = 1e-4
        return value[0], value[1], value[2], diagnostics

    monkeypatch.setattr(core, "_posterior_mode", jittered)
    assert core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    ) == -np.inf


def test_posterior_mode_rejected_step_large_gradient_exit(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension), -np.eye(dimension)

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    _mode, _hessian, _value, diagnostics = core._posterior_mode(
        *_posterior_inputs(), max_steps=1, tol=1e-12
    )
    assert not diagnostics["converged"]
    assert diagnostics["max_abs_gradient"] == 1.0


def test_posterior_mode_handles_linear_solve_failure(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension), -np.eye(dimension)

    def fail_solve(*args, **kwargs):
        raise np.linalg.LinAlgError("synthetic solve failure")

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    monkeypatch.setattr(core.np.linalg, "solve", fail_solve)
    _mode, _hessian, _value, diagnostics = core._posterior_mode(
        *_posterior_inputs(), max_steps=1, tol=1e-12
    )
    assert not diagnostics["converged"]


def test_posterior_mode_handles_nonfinite_newton_direction(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension), -np.eye(dimension)

    def nonfinite_solve(system, gradient):
        return np.full_like(gradient, np.nan)

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    monkeypatch.setattr(core.np.linalg, "solve", nonfinite_solve)
    _mode, _hessian, _value, diagnostics = core._posterior_mode(
        *_posterior_inputs(), max_steps=1, tol=1e-12
    )
    assert not diagnostics["converged"]


def test_posterior_mode_zero_step_exhaustion_is_deterministic(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension), -np.eye(dimension)

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    mode, negative_hessian, value, diagnostics = core._posterior_mode(
        *_posterior_inputs(), max_steps=0, tol=1e-12
    )
    assert mode.shape == (8,)
    assert negative_hessian.shape == (8, 8)
    assert value == 0.0
    assert diagnostics["iterations"] == 0
    assert diagnostics["max_abs_gradient"] == 1.0
    assert not diagnostics["converged"]


def test_laplace_loglik_rejects_nonfinite_final_value(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def infinite_posterior_mode(*args, **kwargs):
        return (
            np.zeros(8, dtype=float),
            np.eye(8, dtype=float),
            np.inf,
            {
                "converged": True,
                "iterations": 1,
                "max_abs_gradient": 0.0,
                "hessian_jitter": 0.0,
                "logdet_negative_hessian": 0.0,
            },
        )

    monkeypatch.setattr(core, "_posterior_mode", infinite_posterior_mode)
    assert core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    ) == -np.inf


def test_covariance_decoder_rejects_invalid_parameter_vector():
    with pytest.raises(ValueError, match="ten finite values"):
        core._covariance_from_cholesky_params(np.zeros(9, dtype=float))


def test_covariance_decoder_rejects_non_positive_definite_result(monkeypatch):
    monkeypatch.setattr(core.np.linalg, "slogdet", lambda matrix: (0.0, np.nan))
    with pytest.raises(np.linalg.LinAlgError, match="not positive definite"):
        core._covariance_from_cholesky_params(np.zeros(10, dtype=float))
