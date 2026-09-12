from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from gpbiometricspy.hierarchical_location_scale import _random_effect_covariance
from gpbiometricspy.robust_hierarchical_location_scale import (
    GazepointRobustHierarchicalLocationScaleResult,
    _group_logposterior_and_derivatives,
    create_gazepoint_robust_hierarchical_location_scale_certificate,
    fit_gazepoint_robust_hierarchical_location_scale,
    predict_gazepoint_robust_hierarchical_location_scale,
    simulate_gazepoint_robust_hierarchical_location_scale,
    summarize_gazepoint_robust_hierarchical_location_scale,
    validate_gazepoint_robust_hierarchical_location_scale_certificate,
)


def _finite_difference_gradient(fun, x, eps=1e-6):
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    for j in range(len(x)):
        plus = x.copy()
        plus[j] += eps
        minus = x.copy()
        minus[j] -= eps
        out[j] = (fun(plus) - fun(minus)) / (2.0 * eps)
    return out


def _finite_difference_jacobian(fun, x, eps=1e-6):
    x = np.asarray(x, dtype=float)
    base = np.asarray(fun(x), dtype=float)
    out = np.empty((base.size, x.size), dtype=float)
    for j in range(len(x)):
        plus = x.copy()
        plus[j] += eps
        minus = x.copy()
        minus[j] -= eps
        out[:, j] = (np.asarray(fun(plus)) - np.asarray(fun(minus))) / (2.0 * eps)
    return out


def _stub_result(*, converged=True, degrees_of_freedom=6.0):
    encoder = {
        "mean_cols": ("x",),
        "scale_cols": ("x",),
        "mean_spec": {"x": {"kind": "numeric", "center": 0.0, "scale": 1.0}},
        "scale_spec": {"x": {"kind": "numeric", "center": 0.0, "scale": 1.0}},
        "standardize_numeric": False,
    }
    return GazepointRobustHierarchicalLocationScaleResult(
        mean_coef=(1.0, 0.5),
        scale_coef=(np.log(2.0), 0.0),
        mean_terms=("Intercept", "x"),
        scale_terms=("Intercept", "x"),
        tau_location=0.4,
        tau_log_scale=0.2,
        rho=0.1,
        degrees_of_freedom=float(degrees_of_freedom),
        log_likelihood=-12.0,
        random_effects=pd.DataFrame([
            {
                "group": "P001",
                "location_re": 0.25,
                "log_scale_re": np.log(1.5),
                "location_re_sd": 0.1,
                "log_scale_re_sd": 0.05,
                "location_log_scale_re_cov": 0.0,
                "location_mode": 0.2,
                "log_scale_mode": 0.3,
                "n_obs": 5,
            }
        ]),
        metadata={
            "model_version": "student-t-hierarchical-location-scale-v1",
            "data_sha256": "a" * 64,
            "quadrature_points": 5,
            "group_col": "participant",
            "claim_boundaries": ("distributional robustness only",),
        },
        diagnostics={"converged": bool(converged), "log_likelihood": -12.0},
        encoder=encoder,
        parameter_vector=np.array([
            1.0,
            0.5,
            np.log(2.0),
            0.0,
            -1.0,
            -1.6,
            0.1,
            np.log(4.0),
        ]),
    )


def test_student_t_group_derivatives_match_finite_differences():
    y = np.array([-0.4, 0.2, 1.5, 2.4, 4.5])
    xb = np.array([-0.2, 0.1, 0.7, 1.4, 1.8])
    zg = np.array([-0.3, -0.1, 0.0, 0.15, 0.25])
    _, cov_inv, logdet_cov = _random_effect_covariance(0.7, 0.35, 0.25)
    nu = 5.5
    b = np.array([0.2, -0.15])

    def scalar(z):
        return _group_logposterior_and_derivatives(
            z, y, xb, zg, cov_inv, logdet_cov, nu
        )[0]

    def analytic_gradient(z):
        return _group_logposterior_and_derivatives(
            z, y, xb, zg, cov_inv, logdet_cov, nu
        )[1]

    _, grad, hess = _group_logposterior_and_derivatives(
        b, y, xb, zg, cov_inv, logdet_cov, nu
    )
    fd_grad = _finite_difference_gradient(scalar, b)
    fd_hess = _finite_difference_jacobian(analytic_gradient, b)
    assert np.allclose(grad, fd_grad, rtol=2e-5, atol=2e-6)
    assert np.allclose(hess, fd_hess, rtol=3e-5, atol=3e-6)
    assert np.allclose(hess, hess.T, atol=1e-12)


def test_robust_simulator_is_deterministic_and_records_known_truth():
    first = simulate_gazepoint_robust_hierarchical_location_scale(
        n_groups=5, observations_per_group=4, degrees_of_freedom=4.5, seed=42
    )
    second = simulate_gazepoint_robust_hierarchical_location_scale(
        n_groups=5, observations_per_group=4, degrees_of_freedom=4.5, seed=42
    )
    pd.testing.assert_frame_equal(first, second)
    assert first.attrs["known_truth"]["degrees_of_freedom"] == 4.5
    assert first.attrs["known_truth"]["scale_parameterization"] == "Student-t scale sigma"


@pytest.mark.parametrize("bad_df", [2.0, 2.049, 1.5, 200.001, np.nan, np.inf])
def test_robust_simulator_rejects_df_outside_model_bounds(bad_df):
    with pytest.raises(ValueError, match="between 2.05 and 200 inclusive"):
        simulate_gazepoint_robust_hierarchical_location_scale(degrees_of_freedom=bad_df)


@pytest.mark.parametrize("boundary_df", [2.05, 200.0])
def test_robust_simulator_accepts_fitted_df_boundaries(boundary_df):
    data = simulate_gazepoint_robust_hierarchical_location_scale(
        n_groups=3,
        observations_per_group=2,
        degrees_of_freedom=boundary_df,
        seed=8,
    )
    assert data.attrs["known_truth"]["degrees_of_freedom"] == boundary_df
    assert len(data) == 6


def test_prediction_distinguishes_student_t_scale_from_residual_sd_and_unseen_groups():
    result = _stub_result(degrees_of_freedom=6.0)
    new = pd.DataFrame({
        "participant": ["P001", "NEW"],
        "x": [0.0, 0.0],
    })
    pred = predict_gazepoint_robust_hierarchical_location_scale(result, new)
    assert pred.loc[0, "random_effect_source"] == "empirical_bayes"
    assert pred.loc[1, "random_effect_source"] == "population_unseen_group"
    assert pred.loc[0, "predicted_scale"] == pytest.approx(3.0)
    expected_sd = pred["predicted_scale"] * np.sqrt(6.0 / 4.0)
    assert np.allclose(pred["predicted_residual_sd"], expected_sd)
    assert np.all(pred["degrees_of_freedom"] == 6.0)


def test_population_prediction_ignores_known_group_random_effects():
    result = _stub_result()
    new = pd.DataFrame({"participant": ["P001"], "x": [2.0]})
    pred = predict_gazepoint_robust_hierarchical_location_scale(
        result, new, include_random_effects=False
    )
    assert pred.loc[0, "predicted_mean"] == pytest.approx(2.0)
    assert pred.loc[0, "predicted_scale"] == pytest.approx(2.0)
    assert pred.loc[0, "random_effect_source"] == "population"


def test_certificate_binds_degrees_of_freedom_random_effects_and_convergence():
    result = _stub_result(degrees_of_freedom=5.25)
    cert = create_gazepoint_robust_hierarchical_location_scale_certificate(result)
    assert cert["payload"]["degrees_of_freedom"] == 5.25
    assert len(cert["payload"]["random_effects_sha256"]) == 64
    assert cert["payload"]["converged"] is True
    assert validate_gazepoint_robust_hierarchical_location_scale_certificate(result, cert)

    tampered = {"payload": dict(cert["payload"]), "sha256": cert["sha256"]}
    tampered["payload"]["degrees_of_freedom"] = 12.0
    assert not validate_gazepoint_robust_hierarchical_location_scale_certificate(result, tampered)

    changed_effects = result.random_effects.copy(deep=True)
    changed_effects.loc[0, "location_re"] += 0.01
    changed = replace(result, random_effects=changed_effects)
    assert not validate_gazepoint_robust_hierarchical_location_scale_certificate(changed, cert)

    second = result.random_effects.copy(deep=True)
    second.loc[0, "group"] = "P002"
    second.loc[0, "location_re"] = -0.4
    forward = replace(
        result,
        random_effects=pd.concat([result.random_effects, second], ignore_index=True),
    )
    reversed_rows = replace(
        result,
        random_effects=pd.concat([second, result.random_effects], ignore_index=True),
    )
    forward_cert = create_gazepoint_robust_hierarchical_location_scale_certificate(forward)
    reverse_cert = create_gazepoint_robust_hierarchical_location_scale_certificate(reversed_rows)
    assert forward_cert["payload"]["random_effects_sha256"] == reverse_cert["payload"]["random_effects_sha256"]

    malformed_result = replace(
        result,
        metadata={
            "model_version": "student-t-hierarchical-location-scale-v1",
            "data_sha256": "a" * 64,
            "group_col": "participant",
        },
    )
    assert not validate_gazepoint_robust_hierarchical_location_scale_certificate(
        malformed_result,
        cert,
    )

    nonconverged = _stub_result(converged=False)
    with pytest.raises(ValueError, match="non-converged"):
        create_gazepoint_robust_hierarchical_location_scale_certificate(nonconverged)
    assert not validate_gazepoint_robust_hierarchical_location_scale_certificate(nonconverged, cert)


def test_summary_exposes_distribution_parameter_separately():
    result = _stub_result(degrees_of_freedom=7.0)
    summary = summarize_gazepoint_robust_hierarchical_location_scale(result)
    assert summary["distribution_parameters"].loc[0, "degrees_of_freedom"] == 7.0
    assert set(summary["fixed_effects"]["equation"]) == {"location", "log_scale"}


def test_fit_inherits_reserved_column_leakage_guards_before_optimization():
    data = simulate_gazepoint_robust_hierarchical_location_scale(
        n_groups=4, observations_per_group=3, seed=11
    )
    with pytest.raises(ValueError, match="must not reuse"):
        fit_gazepoint_robust_hierarchical_location_scale(
            data,
            outcome_col="outcome",
            group_col="participant",
            mean_cols=["outcome"],
            quadrature_points=3,
        )
    with pytest.raises(ValueError, match="must not reuse"):
        fit_gazepoint_robust_hierarchical_location_scale(
            data,
            outcome_col="outcome",
            group_col="participant",
            scale_cols=["participant"],
            quadrature_points=3,
        )


def test_fit_smoke_returns_finite_heavy_tail_model_without_claim_inflation():
    data = simulate_gazepoint_robust_hierarchical_location_scale(
        n_groups=8,
        observations_per_group=5,
        degrees_of_freedom=5.0,
        seed=91,
    )
    fit = fit_gazepoint_robust_hierarchical_location_scale(
        data,
        outcome_col="outcome",
        group_col="participant",
        mean_cols=["x"],
        scale_cols=["x"],
        quadrature_points=3,
        maxiter=80,
        tolerance=1e-6,
        require_convergence=False,
    )
    assert np.isfinite(fit.log_likelihood)
    assert fit.degrees_of_freedom > 2.0
    assert fit.degrees_of_freedom <= 200.0 + 1e-8
    assert fit.metadata["distribution"] == "Student-t"
    boundaries = " ".join(fit.metadata["claim_boundaries"]).lower()
    assert "do not identify which observations are artifacts" in boundaries
    assert "sensor validity" in boundaries
    assert fit.random_effects.shape[0] == 8
