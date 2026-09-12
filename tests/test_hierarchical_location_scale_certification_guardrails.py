from types import SimpleNamespace

import numpy as np
import pytest

import gpbiometricspy.hierarchical_location_scale as hls
from gpbiometricspy.hierarchical_location_scale import (
    create_gazepoint_hierarchical_location_scale_certificate,
    fit_gazepoint_hierarchical_location_scale,
    simulate_gazepoint_hierarchical_location_scale,
    validate_gazepoint_hierarchical_location_scale_certificate,
)


def _small_case():
    return simulate_gazepoint_hierarchical_location_scale(
        n_groups=5,
        observations_per_group=4,
        seed=901,
    )


def test_predictors_cannot_alias_outcome_or_group_columns():
    data = _small_case()

    with pytest.raises(ValueError, match="must not reuse"):
        fit_gazepoint_hierarchical_location_scale(
            data,
            outcome_col="outcome",
            group_col="participant",
            mean_cols=["outcome"],
            quadrature_points=3,
        )

    with pytest.raises(ValueError, match="must not reuse"):
        fit_gazepoint_hierarchical_location_scale(
            data,
            outcome_col="outcome",
            group_col="participant",
            scale_cols=["participant"],
            quadrature_points=3,
        )


def test_nonconverged_fit_cannot_be_certified(monkeypatch):
    data = _small_case()

    def failed_minimize(fun, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0, dtype=float),
            fun=float(fun(x0)),
            success=False,
            status=9,
            message="forced non-convergence",
        )

    monkeypatch.setattr(hls, "minimize", failed_minimize)
    result = fit_gazepoint_hierarchical_location_scale(
        data,
        outcome_col="outcome",
        group_col="participant",
        quadrature_points=3,
        require_convergence=False,
    )

    assert result.diagnostics["converged"] is False
    with pytest.raises(ValueError, match="non-converged"):
        create_gazepoint_hierarchical_location_scale_certificate(result)

    assert not validate_gazepoint_hierarchical_location_scale_certificate(
        result,
        {"payload": {}, "sha256": "not-a-certificate"},
    )


def test_converged_certificate_explicitly_binds_convergence_state():
    data = _small_case()
    result = fit_gazepoint_hierarchical_location_scale(
        data,
        outcome_col="outcome",
        group_col="participant",
        quadrature_points=3,
        maxiter=160,
    )

    certificate = create_gazepoint_hierarchical_location_scale_certificate(result)
    assert certificate["payload"]["converged"] is True
    assert validate_gazepoint_hierarchical_location_scale_certificate(result, certificate)
