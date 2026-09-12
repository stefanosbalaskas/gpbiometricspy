from types import SimpleNamespace

import numpy as np

import gpbiometricspy.hierarchical_location_scale as hls


def test_posterior_mode_exhausts_rejected_line_search(monkeypatch):
    def rejects_candidates(b, *args):
        b = np.asarray(b, dtype=float)
        if np.allclose(b, 0.0):
            return 0.0, np.ones(2), -np.eye(2)
        return -1e6, np.ones(2), -np.eye(2)

    monkeypatch.setattr(hls, "_group_logposterior_and_derivatives", rejects_candidates)
    mode, covariance, value = hls._posterior_mode(
        np.array([0.0]),
        np.zeros(1),
        np.zeros(1),
        np.eye(2),
        0.0,
        max_steps=1,
    )
    assert np.allclose(mode, 0.0)
    assert np.isfinite(covariance).all()
    assert value == 0.0


def test_fit_objective_maps_nonfinite_likelihood_to_large_penalty(monkeypatch):
    data = hls.simulate_gazepoint_hierarchical_location_scale(
        n_groups=4,
        observations_per_group=3,
        seed=29,
    )

    def inspect_objective(fun, x0, **kwargs):
        bad = np.asarray(x0, dtype=float).copy()
        bad[-3] = 1000.0
        with np.errstate(over="ignore", invalid="ignore"):
            assert fun(bad) == 1e100
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            fun=float(fun(x0)),
            success=False,
            status=9,
            message="forced",
        )

    monkeypatch.setattr(hls, "minimize", inspect_objective)
    result = hls.fit_gazepoint_hierarchical_location_scale(
        data,
        "outcome",
        "participant",
        quadrature_points=3,
        require_convergence=False,
    )
    assert result.diagnostics["converged"] is False
