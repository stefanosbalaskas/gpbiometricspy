from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.hierarchical_location_scale as hls
from gpbiometricspy.hierarchical_location_scale import (
    create_gazepoint_hierarchical_location_scale_certificate,
    fit_gazepoint_hierarchical_location_scale,
    predict_gazepoint_hierarchical_location_scale,
    simulate_gazepoint_hierarchical_location_scale,
    summarize_gazepoint_hierarchical_location_scale,
    validate_gazepoint_hierarchical_location_scale_certificate,
)


@pytest.fixture(scope="module")
def fitted_case():
    data = simulate_gazepoint_hierarchical_location_scale(
        n_groups=18,
        observations_per_group=10,
        seed=11,
    )
    result = fit_gazepoint_hierarchical_location_scale(
        data,
        outcome_col="outcome",
        group_col="participant",
        mean_cols=["x"],
        scale_cols=["x"],
        quadrature_points=5,
        maxiter=160,
    )
    return data, result


def test_known_truth_fit_has_expected_direction_and_diagnostics(fitted_case):
    data, result = fitted_case
    assert result.diagnostics["converged"] is True
    assert result.metadata["quadrature_scheme"] == "two-dimensional adaptive Gauss-Hermite"
    assert result.metadata["n_obs"] == len(data)
    assert result.metadata["n_groups"] == data["participant"].nunique()
    assert result.mean_terms == ("Intercept", "x")
    assert result.scale_terms == ("Intercept", "x")
    assert result.mean_coef[1] > 0.25
    assert result.scale_coef[1] > 0.05
    assert result.tau_location > 0
    assert result.tau_log_scale > 0
    assert -1 < result.rho < 1
    assert len(result.random_effects) == data["participant"].nunique()


def test_prediction_seen_unseen_population_and_custom_group_semantics(fitted_case):
    data, result = fitted_case
    seen = data.iloc[[0]].copy()
    unseen = seen.copy()
    unseen["participant"] = "NEW_PARTICIPANT"

    pred_seen = predict_gazepoint_hierarchical_location_scale(result, seen)
    pred_unseen = predict_gazepoint_hierarchical_location_scale(result, unseen)
    population = predict_gazepoint_hierarchical_location_scale(
        result,
        seen,
        include_random_effects=False,
    )
    custom = seen.rename(columns={"participant": "subject"})
    pred_custom = predict_gazepoint_hierarchical_location_scale(
        result,
        custom,
        group_col="subject",
    )

    assert pred_seen.random_effect_source.iloc[0] == "empirical_bayes"
    assert pred_unseen.random_effect_source.iloc[0] == "population_unseen_group"
    assert population.random_effect_source.iloc[0] == "population"
    assert pred_custom.random_effect_source.iloc[0] == "empirical_bayes"
    assert np.isfinite(pred_seen.predicted_mean.iloc[0])
    assert pred_seen.predicted_scale.iloc[0] > 0

    without_group = seen.drop(columns="participant")
    with pytest.raises(ValueError, match="Missing group column"):
        predict_gazepoint_hierarchical_location_scale(result, without_group)


def test_certificate_is_key_order_insensitive_and_tamper_evident(fitted_case):
    _, result = fitted_case
    cert = create_gazepoint_hierarchical_location_scale_certificate(result)
    reordered = {
        "sha256": cert["sha256"],
        "payload": dict(reversed(list(cert["payload"].items()))),
    }
    assert validate_gazepoint_hierarchical_location_scale_certificate(result, reordered)

    tampered = {"sha256": cert["sha256"], "payload": dict(cert["payload"])}
    tampered["payload"]["rho"] = 0.0
    assert not validate_gazepoint_hierarchical_location_scale_certificate(result, tampered)
    assert not validate_gazepoint_hierarchical_location_scale_certificate(result, [])
    assert not validate_gazepoint_hierarchical_location_scale_certificate(result, {"payload": {}})
    assert not validate_gazepoint_hierarchical_location_scale_certificate(
        result,
        {"payload": {"bad": object()}, "sha256": "bad"},
    )

    with pytest.raises(TypeError):
        create_gazepoint_hierarchical_location_scale_certificate(object())


def test_result_metadata_encoder_and_parameter_vector_are_immutable(fitted_case):
    _, result = fitted_case
    with pytest.raises(TypeError):
        result.metadata["n_obs"] = 0
    with pytest.raises(TypeError):
        result.encoder["mean_spec"]["x"]["center"] = 0.0
    with pytest.raises(ValueError):
        result.parameter_vector[0] = 0.0


def test_summary_and_prediction_design_contracts(fitted_case, monkeypatch):
    data, result = fitted_case
    summary = summarize_gazepoint_hierarchical_location_scale(result)
    assert summary["class"] == "gazepoint_hierarchical_location_scale_summary"
    assert set(summary["fixed_effects"]["equation"]) == {"location", "log_scale"}

    with pytest.raises(TypeError):
        summarize_gazepoint_hierarchical_location_scale(object())
    with pytest.raises(TypeError):
        hls._prediction_design(object(), data.head())
    with pytest.raises(TypeError):
        hls._prediction_design(result, object())

    original = hls._apply_encoder

    def mismatched_terms(frame, cols, spec, *, allow_unknown):
        matrix, _ = original(frame, cols, spec, allow_unknown=allow_unknown)
        return matrix, ("mismatch",)

    monkeypatch.setattr(hls, "_apply_encoder", mismatched_terms)
    with pytest.raises(ValueError, match="does not match"):
        hls._prediction_design(result, data.head())


def test_input_guardrails_and_categorical_prediction():
    data = simulate_gazepoint_hierarchical_location_scale(
        n_groups=8,
        observations_per_group=6,
        seed=5,
    )
    data["condition"] = np.tile(["A", "B", "A", "B", "A", "B"], 8)

    with pytest.raises(ValueError, match="distinct"):
        fit_gazepoint_hierarchical_location_scale(data, "outcome", "outcome")
    with pytest.raises(ValueError, match="unique"):
        fit_gazepoint_hierarchical_location_scale(
            data,
            "outcome",
            "participant",
            mean_cols=["x", "x"],
        )

    result = fit_gazepoint_hierarchical_location_scale(
        data,
        "outcome",
        "participant",
        mean_cols="condition",
        quadrature_points=3,
        maxiter=120,
    )
    new = data.iloc[[0]].copy()
    new["condition"] = "C"
    with pytest.raises(ValueError, match="unseen categorical levels"):
        predict_gazepoint_hierarchical_location_scale(
            result,
            new,
            include_random_effects=False,
        )


def test_encoder_and_prepare_data_defensive_paths():
    numeric = pd.DataFrame({"x": [2.0, 2.0, 2.0]})
    spec, terms = hls._fit_encoder(numeric, ["x"], standardize_numeric=True)
    assert terms == ("Intercept", "x")
    assert spec["x"]["scale"] == 1.0

    raw_spec, _ = hls._fit_encoder(numeric, ["x"], standardize_numeric=False)
    assert raw_spec["x"]["center"] == 0.0
    assert raw_spec["x"]["scale"] == 1.0

    with pytest.raises(ValueError, match="no finite"):
        hls._fit_encoder(
            pd.DataFrame({"x": [np.nan, np.inf]}),
            ["x"],
            standardize_numeric=True,
        )
    with pytest.raises(ValueError, match="at least two"):
        hls._fit_encoder(
            pd.DataFrame({"condition": ["A", "A"]}),
            ["condition"],
            standardize_numeric=True,
        )

    cat_spec, _ = hls._fit_encoder(
        pd.DataFrame({"condition": ["A", "B"]}),
        ["condition"],
        standardize_numeric=True,
    )
    matrix, terms = hls._apply_encoder(
        pd.DataFrame({"condition": ["C"]}),
        ["condition"],
        cat_spec,
        allow_unknown=True,
    )
    assert matrix.shape == (1, 2)
    assert terms == ("Intercept", "condition[B]")

    with pytest.raises(ValueError, match="Missing predictor"):
        hls._apply_encoder(
            pd.DataFrame({"other": [1.0]}),
            ["condition"],
            cat_spec,
            allow_unknown=False,
        )
    with pytest.raises(ValueError, match="non-finite"):
        hls._apply_encoder(
            pd.DataFrame({"x": [np.nan]}),
            ["x"],
            spec,
            allow_unknown=False,
        )

    with pytest.raises(TypeError, match="DataFrame"):
        hls._prepare_fit_data([], "outcome", "participant", [], [], standardize_numeric=True)

    base = simulate_gazepoint_hierarchical_location_scale(
        n_groups=4,
        observations_per_group=3,
        seed=17,
    )
    with pytest.raises(ValueError, match="Missing required"):
        hls._prepare_fit_data(
            base.drop(columns="outcome"),
            "outcome",
            "participant",
            [],
            [],
            standardize_numeric=True,
        )

    empty = base.copy()
    empty["outcome"] = np.nan
    with pytest.raises(ValueError, match="No complete finite"):
        hls._prepare_fit_data(
            empty,
            "outcome",
            "participant",
            [],
            [],
            standardize_numeric=True,
        )

    two_groups = base[base["participant"].isin(["P001", "P002"])]
    with pytest.raises(ValueError, match="At least three"):
        hls._prepare_fit_data(
            two_groups,
            "outcome",
            "participant",
            [],
            [],
            standardize_numeric=True,
        )


def test_fit_argument_and_convergence_guardrails(monkeypatch):
    data = simulate_gazepoint_hierarchical_location_scale(
        n_groups=4,
        observations_per_group=3,
        seed=23,
    )

    for bad_points in (2, 26, 3.0):
        with pytest.raises(ValueError, match="quadrature_points"):
            fit_gazepoint_hierarchical_location_scale(data, "outcome", "participant", quadrature_points=bad_points)
    for bad_maxiter in (0, 1.5):
        with pytest.raises(ValueError, match="maxiter"):
            fit_gazepoint_hierarchical_location_scale(data, "outcome", "participant", maxiter=bad_maxiter)
    for bad_tolerance in (0.0, np.nan):
        with pytest.raises(ValueError, match="tolerance"):
            fit_gazepoint_hierarchical_location_scale(data, "outcome", "participant", tolerance=bad_tolerance)

    def failed_minimize(fun, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0),
            fun=float(fun(x0)),
            success=False,
            status=9,
            message="forced non-convergence",
        )

    monkeypatch.setattr(hls, "minimize", failed_minimize)
    with pytest.raises(RuntimeError, match="did not converge"):
        fit_gazepoint_hierarchical_location_scale(
            data,
            "outcome",
            "participant",
            quadrature_points=3,
        )

    result = fit_gazepoint_hierarchical_location_scale(
        data,
        "outcome",
        "participant",
        quadrature_points=3,
        require_convergence=False,
    )
    assert result.diagnostics["converged"] is False
    assert np.isnan(result.diagnostics["gradient_max_abs"])


def test_covariance_marginal_likelihood_and_initialization_defensive_paths(monkeypatch):
    with pytest.raises(np.linalg.LinAlgError):
        hls._random_effect_covariance(0.0, 1.0, 0.0)

    y = np.array([0.0, 0.1])
    X = np.ones((2, 1))
    Z = np.ones((2, 1))
    groups = np.zeros(2, dtype=int)
    x1, x2, logw = hls._quadrature_nodes(3)

    with np.errstate(over="ignore", invalid="ignore"):
        assert hls._marginal_loglik(
            np.array([0.0, 0.0, 1000.0, 0.0, 0.0]),
            y,
            X,
            Z,
            groups,
            1,
            x1,
            x2,
            logw,
        ) == -np.inf
    assert hls._marginal_loglik(
        np.array([0.0, 0.0, -np.inf, 0.0, 0.0]),
        y,
        X,
        Z,
        groups,
        1,
        x1,
        x2,
        logw,
    ) == -np.inf

    monkeypatch.setattr(hls, "_adaptive_group_integral", lambda *args, **kwargs: -np.inf)
    assert hls._marginal_loglik(
        np.zeros(5),
        y,
        X,
        Z,
        groups,
        1,
        x1,
        x2,
        logw,
    ) == -np.inf

    theta = hls._initial_theta(np.ones(4), np.ones((4, 1)), np.ones((4, 1)))
    assert np.isclose(theta[1], 0.0)


def test_posterior_mode_numerical_fallback_paths(monkeypatch):
    y = np.array([0.0, 0.2, -0.1])
    xb = np.zeros(3)
    zg = np.zeros(3)
    cov_inv = np.eye(2)

    def singular_solve(*args, **kwargs):
        raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(hls.np.linalg, "solve", singular_solve)
    mode, cov, value = hls._posterior_mode(y, xb, zg, cov_inv, 0.0, max_steps=2)
    assert np.isfinite(mode).all()
    assert np.isfinite(cov).all()
    assert np.isfinite(value)


def test_posterior_mode_nonfinite_step_rejection_and_hessian_repair(monkeypatch):
    y = np.array([0.0])
    zeros = np.zeros(1)

    monkeypatch.setattr(hls.np.linalg, "solve", lambda *args, **kwargs: np.array([np.nan, 0.0]))
    mode, cov, _ = hls._posterior_mode(y, zeros, zeros, np.eye(2), 0.0)
    assert np.isfinite(mode).all()
    assert np.isfinite(cov).all()

    def rejects_candidates(b, *args):
        b = np.asarray(b)
        if np.allclose(b, 0.0):
            return 0.0, np.ones(2), -np.eye(2)
        return -1e6, np.ones(2), -np.eye(2)

    monkeypatch.setattr(hls, "_group_logposterior_and_derivatives", rejects_candidates)
    monkeypatch.setattr(hls.np.linalg, "solve", np.linalg.solve)
    mode, cov, _ = hls._posterior_mode(y, zeros, zeros, np.eye(2), 0.0, max_steps=1)
    assert np.allclose(mode, 0.0)
    assert np.isfinite(cov).all()

    def nonconcave_mode(b, *args):
        return 0.0, np.zeros(2), np.eye(2)

    monkeypatch.setattr(hls, "_group_logposterior_and_derivatives", nonconcave_mode)
    mode, cov, _ = hls._posterior_mode(y, zeros, zeros, np.eye(2), 0.0)
    assert np.allclose(mode, 0.0)
    assert np.isfinite(cov).all()


def test_adaptive_quadrature_fallback_and_invalid_jacobian(monkeypatch):
    y = np.array([0.0, 0.1])
    zeros = np.zeros(2)
    x1, x2, logw = hls._quadrature_nodes(3)

    original_cholesky = hls.np.linalg.cholesky

    def forced_cholesky_failure(*args, **kwargs):
        raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(hls.np.linalg, "cholesky", forced_cholesky_failure)
    value = hls._adaptive_group_integral(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        x1,
        x2,
        logw,
    )
    assert np.isfinite(value)
    monkeypatch.setattr(hls.np.linalg, "cholesky", original_cholesky)

    monkeypatch.setattr(
        hls,
        "_posterior_mode",
        lambda *args, **kwargs: (np.zeros(2), np.eye(2), 0.0),
    )
    monkeypatch.setattr(hls.np.linalg, "slogdet", lambda matrix: (0.0, -np.inf))
    assert hls._adaptive_group_integral(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        x1,
        x2,
        logw,
    ) == -np.inf
    assert hls._adaptive_group_integral(
        y,
        zeros,
        zeros,
        np.eye(2),
        0.0,
        x1,
        x2,
        logw,
        moments=True,
    ) == (-np.inf, None)


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
            simulate_gazepoint_hierarchical_location_scale(**kwargs)


def test_simulation_is_reproducible():
    first = simulate_gazepoint_hierarchical_location_scale(seed=123)
    second = simulate_gazepoint_hierarchical_location_scale(seed=123)
    pd.testing.assert_frame_equal(first, second)
    assert first.attrs["known_truth"] == second.attrs["known_truth"]
