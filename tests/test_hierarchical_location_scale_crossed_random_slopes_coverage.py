from __future__ import annotations

import numpy as np

import gpbiometricspy.hierarchical_location_scale_crossed_random_slopes as c


def _minimal_laplace_inputs():
    y = np.array([0.1, 0.2], dtype=float)
    X = np.ones((2, 1), dtype=float)
    Z = np.ones((2, 1), dtype=float)
    theta = c._initial_theta(y, X, Z)
    participant_slope = np.array([-1.0, 1.0], dtype=float)
    item_slope = np.array([1.0, -1.0], dtype=float)
    participant_index = np.zeros(2, dtype=int)
    item_index = np.zeros(2, dtype=int)
    return (
        theta,
        y,
        X,
        Z,
        participant_slope,
        item_slope,
        participant_index,
        item_index,
    )


def test_laplace_loglik_catches_posterior_mode_failure(monkeypatch):
    inputs = _minimal_laplace_inputs()

    def fail_posterior_mode(*args, **kwargs):
        raise ValueError("synthetic posterior-mode failure")

    monkeypatch.setattr(c, "_posterior_mode", fail_posterior_mode)
    value = c._laplace_loglik(
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

    monkeypatch.setattr(c, "_posterior_mode", nonconverged_posterior_mode)
    value = c._laplace_loglik(
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

    monkeypatch.setattr(c, "_joint_logposterior_grad_hess", fixed_surface)
    y = np.array([0.1, -0.2], dtype=float)
    zeros = np.zeros(2, dtype=float)
    index = np.zeros(2, dtype=int)
    covariance_inverse = np.eye(3, dtype=float)
    _mode, _hessian, _value, diagnostics = c._posterior_mode(
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
