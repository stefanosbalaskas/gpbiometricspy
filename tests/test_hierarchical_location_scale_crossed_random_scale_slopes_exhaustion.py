from __future__ import annotations

import numpy as np

import gpbiometricspy.hierarchical_location_scale_crossed_random_scale_core as core


def test_posterior_mode_zero_step_exhaustion(monkeypatch):
    """Cover the loop no-entry edge independently of optimizer numerics."""

    def fixed_surface(b, *args, **kwargs):
        dimension = len(b)
        return 0.0, np.ones(dimension, dtype=float), -np.eye(dimension, dtype=float)

    monkeypatch.setattr(core, "_joint_logposterior_grad_hess", fixed_surface)
    y = np.array([0.1, -0.2], dtype=float)
    zeros = np.zeros(2, dtype=float)
    index = np.zeros(2, dtype=int)
    covariance_inverse = np.eye(3, dtype=float)

    mode, hessian, value, diagnostics = core._posterior_mode(
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
        max_steps=0,
        tol=1e-12,
    )

    assert diagnostics["iterations"] == 0
    assert not diagnostics["converged"]
    assert diagnostics["max_abs_gradient"] == 1.0
    assert mode.shape == (6,)
    assert hessian.shape == (6, 6)
    assert value == 0.0
