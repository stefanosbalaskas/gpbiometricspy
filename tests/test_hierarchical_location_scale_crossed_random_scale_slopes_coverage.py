from __future__ import annotations

import numpy as np

import gpbiometricspy.hierarchical_location_scale_crossed_random_scale_core as core


def _minimal_laplace_inputs():
    y = np.array([0.1, 0.2], dtype=float)
    X = np.ones((2, 1), dtype=float)
    Z = np.ones((2, 1), dtype=float)
    theta = core._initial_theta(y, X, Z)
    participant_scale = np.array([-1.0, 1.0], dtype=float)
    item_scale = np.array([1.0, -1.0], dtype=float)
    participant_index = np.zeros(2, dtype=int)
    item_index = np.zeros(2, dtype=int)
    return (
        theta,
        y,
        X,
        Z,
        participant_scale,
        item_scale,
        participant_index,
        item_index,
    )


def test_laplace_loglik_catches_posterior_mode_failure(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def fail_posterior_mode(*args, **kwargs):
        raise ValueError("synthetic posterior-mode failure")

    monkeypatch.setattr(core, "_posterior_mode", fail_posterior_mode)
    value = core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    )
    assert value == -np.inf


def test_laplace_loglik_rejects_nonconverged_posterior_mode(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def nonconverged_posterior_mode(*args, **kwargs):
        return (
            np.zeros(6, dtype=float),
            np.eye(6, dtype=float),
            0.0,
            {
                "converged": False,
                "iterations": 1,
                "max_abs_gradient": 1.0,
                "hessian_jitter": 0.0,
                "logdet_negative_hessian": 0.0,
            },
        )

    monkeypatch.setattr(core, "_posterior_mode", nonconverged_posterior_mode)
    value = core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    )
    assert value == -np.inf


def test_posterior_mode_rejected_step_large_gradient_exit(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension, dtype=float), -np.eye(dimension, dtype=float)

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    y = np.array([0.1, -0.2], dtype=float)
    zeros = np.zeros(2, dtype=float)
    index = np.zeros(2, dtype=int)
    covariance_inverse = np.eye(3, dtype=float)
    _mode, _hessian, _value, diagnostics = core._posterior_mode(
        y,
        zeros,
        zeros,
        np.array([-1.0, 1.0], dtype=float),
        np.array([1.0, -1.0], dtype=float),
        index,
        index,
        1,
        1,
        covariance_inverse,
        0.0,
        covariance_inverse,
        0.0,
        max_steps=1,
        tol=1e-12,
    )
    assert not diagnostics["converged"]
    assert diagnostics["max_abs_gradient"] == 1.0


def test_posterior_mode_handles_linear_solve_failure(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension, dtype=float), -np.eye(dimension, dtype=float)

    def fail_solve(*args, **kwargs):
        raise np.linalg.LinAlgError("synthetic solve failure")

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    monkeypatch.setattr(core.np.linalg, "solve", fail_solve)
    y = np.array([0.1, -0.2], dtype=float)
    zeros = np.zeros(2, dtype=float)
    index = np.zeros(2, dtype=int)
    covariance_inverse = np.eye(3, dtype=float)
    _mode, _hessian, _value, diagnostics = core._posterior_mode(
        y,
        zeros,
        zeros,
        np.array([-1.0, 1.0], dtype=float),
        np.array([1.0, -1.0], dtype=float),
        index,
        index,
        1,
        1,
        covariance_inverse,
        0.0,
        covariance_inverse,
        0.0,
        max_steps=1,
        tol=1e-12,
    )
    assert not diagnostics["converged"]
    assert diagnostics["max_abs_gradient"] == 1.0


def test_posterior_mode_handles_nonfinite_newton_direction(monkeypatch):
    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension, dtype=float), -np.eye(dimension, dtype=float)

    def nonfinite_solve(system, gradient):
        return np.full_like(gradient, np.nan)

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    monkeypatch.setattr(core.np.linalg, "solve", nonfinite_solve)
    y = np.array([0.1, -0.2], dtype=float)
    zeros = np.zeros(2, dtype=float)
    index = np.zeros(2, dtype=int)
    covariance_inverse = np.eye(3, dtype=float)
    _mode, _hessian, _value, diagnostics = core._posterior_mode(
        y,
        zeros,
        zeros,
        np.array([-1.0, 1.0], dtype=float),
        np.array([1.0, -1.0], dtype=float),
        index,
        index,
        1,
        1,
        covariance_inverse,
        0.0,
        covariance_inverse,
        0.0,
        max_steps=1,
        tol=1e-12,
    )
    assert not diagnostics["converged"]
    assert diagnostics["max_abs_gradient"] == 1.0


def test_laplace_loglik_rejects_nonfinite_final_value(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def infinite_posterior_mode(*args, **kwargs):
        return (
            np.zeros(6, dtype=float),
            np.eye(6, dtype=float),
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
    value = core._laplace_loglik(
        *inputs,
        1,
        1,
        mode_max_steps=1,
        mode_tol=1e-6,
    )
    assert value == -np.inf
