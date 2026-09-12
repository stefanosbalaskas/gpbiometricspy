import numpy as np

import gpbiometricspy.robust_hierarchical_location_scale as rls


def test_posterior_mode_exhausts_rejected_line_search(monkeypatch):
    def rejects_candidates(b, *args):
        b = np.asarray(b, dtype=float)
        if np.allclose(b, 0.0):
            return 0.0, np.ones(2), -np.eye(2)
        return -1e6, np.ones(2), -np.eye(2)

    monkeypatch.setattr(rls, "_group_logposterior_and_derivatives", rejects_candidates)
    mode, covariance, value = rls._posterior_mode(
        np.array([0.0]),
        np.zeros(1),
        np.zeros(1),
        np.eye(2),
        0.0,
        5.0,
        max_steps=1,
    )
    assert np.allclose(mode, 0.0)
    assert np.isfinite(covariance).all()
    assert value == 0.0
