from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

import gpbiometricspy.hierarchical_location_scale_joint_random_slopes as j


@pytest.fixture(scope="module")
def fitted_case():
    data = j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
        n_groups=8, observations_per_group=5, seed=42
    )
    result = j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
        data,
        "outcome",
        "participant",
        mean_cols=["x_location"],
        scale_cols=["x_scale"],
        location_random_slope_col="x_location",
        scale_random_slope_col="x_scale",
        quadrature_points=3,
        maxiter=80,
        standardize_numeric=False,
    )
    return data, result


def test_fit_prediction_summary_certificate_and_immutability(fitted_case):
    data, result = fitted_case
    assert result.diagnostics["converged"] is True
    assert result.metadata["quadrature_scheme"] == "four-dimensional adaptive Gauss-Hermite"
    assert result.metadata["quadrature_nodes_per_group"] == 81
    assert result.random_effect_covariance.shape == (4, 4)
    assert result.random_effect_correlation.shape == (4, 4)
    assert np.linalg.eigvalsh(result.random_effect_covariance).min() > 0
    assert len(result.random_effects) == 8

    seen = data.iloc[[0]].copy()
    unseen = seen.copy()
    unseen["participant"] = "NEW"
    pop = j.predict_gazepoint_hierarchical_location_scale_joint_random_slopes(
        result, seen, include_random_effects=False
    )
    p_seen = j.predict_gazepoint_hierarchical_location_scale_joint_random_slopes(result, seen)
    p_unseen = j.predict_gazepoint_hierarchical_location_scale_joint_random_slopes(result, unseen)
    custom = seen.rename(columns={"participant": "subject"})
    p_custom = j.predict_gazepoint_hierarchical_location_scale_joint_random_slopes(
        result, custom, group_col="subject"
    )
    assert pop.random_effect_source.iloc[0] == "population"
    assert p_seen.random_effect_source.iloc[0] == "empirical_bayes"
    assert p_unseen.random_effect_source.iloc[0] == "population_unseen_group"
    assert p_custom.random_effect_source.iloc[0] == "empirical_bayes"
    assert p_seen.predicted_scale.iloc[0] > 0

    summary = j.summarize_gazepoint_hierarchical_location_scale_joint_random_slopes(result)
    assert summary["class"] == "gazepoint_hierarchical_location_scale_joint_random_slopes_summary"
    assert summary["random_effect_covariance"].shape == (4, 4)
    assert summary["random_effect_correlation"].shape == (4, 4)

    cert = j.create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(result)
    assert len(cert["sha256"]) == 64
    reordered = {
        "sha256": cert["sha256"],
        "payload": dict(reversed(list(cert["payload"].items()))),
    }
    assert j.validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
        result, reordered
    )
    shuffled = replace(
        result,
        random_effects=result.random_effects.sample(frac=1, random_state=1),
    )
    assert (
        j.create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(shuffled)[
            "payload"
        ]["random_effects_sha256"]
        == cert["payload"]["random_effects_sha256"]
    )
    mutated_re = result.random_effects.copy()
    mutated_re.loc[0, "location_slope_re"] += 0.2
    mutated = replace(result, random_effects=mutated_re)
    assert not j.validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
        mutated, cert
    )

    with pytest.raises(TypeError):
        result.metadata["n_obs"] = 0
    with pytest.raises(ValueError):
        result.parameter_vector[0] = 0
    with pytest.raises(ValueError):
        result.random_effect_covariance[0, 0] = 0
    with pytest.raises(ValueError):
        result.random_effect_correlation[0, 0] = 0


def test_derivatives_nodes_and_quadrature():
    rng = np.random.default_rng(3)
    n = 7
    y = rng.normal(size=n)
    xb = rng.normal(size=n)
    zg = rng.normal(scale=0.1, size=n)
    r_location = rng.normal(size=n)
    r_scale = rng.normal(size=n)
    params = np.array(
        [
            np.log(0.5),
            np.log(0.3),
            np.log(0.2),
            np.log(0.15),
            0.05,
            -0.03,
            0.02,
            0.01,
            -0.01,
            0.02,
        ]
    )
    cov, inv, logdet, sds, corr = j._covariance_from_cholesky_params(params)
    assert cov.shape == (4, 4)
    assert inv.shape == (4, 4)
    assert sds.shape == (4,)
    assert corr.shape == (4, 4)

    b = np.array([0.1, -0.05, 0.08, 0.03])
    h, grad, hess = j._group_logposterior_and_derivatives(
        b, y, xb, zg, r_location, r_scale, inv, logdet
    )
    eps = 1e-6
    grad_num = np.zeros(4)
    hess_num = np.zeros((4, 4))
    for k in range(4):
        e = np.zeros(4)
        e[k] = eps
        hp = j._group_logposterior_and_derivatives(
            b + e, y, xb, zg, r_location, r_scale, inv, logdet
        )
        hm = j._group_logposterior_and_derivatives(
            b - e, y, xb, zg, r_location, r_scale, inv, logdet
        )
        grad_num[k] = (hp[0] - hm[0]) / (2 * eps)
        hess_num[:, k] = (hp[1] - hm[1]) / (2 * eps)
    assert np.max(np.abs(grad - grad_num)) < 1e-5
    assert np.max(np.abs(hess - hess_num)) < 1e-5

    nodes = j._group_logposterior_nodes(
        np.array([b[0]]),
        np.array([b[1]]),
        np.array([b[2]]),
        np.array([b[3]]),
        y,
        xb,
        zg,
        r_location,
        r_scale,
        inv,
        logdet,
    )
    assert nodes[0] == pytest.approx(h)
    *_, logw = j._quadrature_nodes(3)
    assert len(logw) == 81


def test_input_guardrails_and_identifiability():
    data = j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
        n_groups=8, observations_per_group=4, seed=7
    )
    common = dict(
        data=data,
        outcome_col="outcome",
        group_col="participant",
        mean_cols=["x_location"],
        scale_cols=["x_scale"],
        location_random_slope_col="x_location",
        scale_random_slope_col="x_scale",
        maxiter=1,
        require_convergence=False,
    )
    for bad in (2, 8, 3.5):
        with pytest.raises(ValueError, match="quadrature_points"):
            j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
                **{**common, "quadrature_points": bad}
            )
    with pytest.raises(ValueError, match="maxiter"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
            **{**common, "maxiter": 0}
        )
    for bad in (0, np.nan):
        with pytest.raises(ValueError, match="tolerance"):
            j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
                **{**common, "tolerance": bad}
            )

    with pytest.raises(ValueError, match="mean_cols"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
            **{**common, "mean_cols": []}
        )
    with pytest.raises(ValueError, match="scale_cols"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
            **{**common, "scale_cols": []}
        )

    categorical = data.copy()
    categorical["condition"] = np.tile(["A", "B", "A", "B"], 8)
    with pytest.raises(ValueError, match="numeric"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
            categorical,
            "outcome",
            "participant",
            mean_cols=["condition"],
            scale_cols=["x_scale"],
            location_random_slope_col="condition",
            scale_random_slope_col="x_scale",
            maxiter=1,
            require_convergence=False,
        )

    seven = data[data.participant != "P008"]
    with pytest.raises(ValueError, match="at least eight"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
            seven,
            "outcome",
            "participant",
            mean_cols=["x_location"],
            scale_cols=["x_scale"],
            location_random_slope_col="x_location",
            scale_random_slope_col="x_scale",
            maxiter=1,
            require_convergence=False,
        )

    flat = data.copy()
    flat.loc[flat.participant == "P001", "x_scale"] = 1.0
    with pytest.raises(ValueError, match="must vary within every"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
            flat,
            "outcome",
            "participant",
            mean_cols=["x_location"],
            scale_cols=["x_scale"],
            location_random_slope_col="x_location",
            scale_random_slope_col="x_scale",
            maxiter=1,
            require_convergence=False,
        )

    all_flat = data.copy()
    all_flat["x_location"] = 1.0
    frame, _, groups, _, _, _, _, _, _, encoder = j._prepare_fit_data(
        all_flat,
        "outcome",
        "participant",
        ["x_location"],
        ["x_scale"],
        standardize_numeric=True,
    )
    with pytest.raises(ValueError, match="within-sample variation"):
        j._encoded_random_slope_values(
            frame,
            groups,
            "x_location",
            ["x_location"],
            encoder["mean_spec"],
            argument_name="location_random_slope_col",
            equation_name="mean_cols",
        )


def test_covariance_correlation_and_simulator_guardrails():
    with pytest.raises(ValueError, match="ten finite"):
        j._covariance_from_cholesky_params(np.zeros(9))
    with pytest.raises(ValueError, match="ten finite"):
        j._covariance_from_cholesky_params(np.r_[np.nan, np.zeros(9)])
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(np.linalg.LinAlgError):
            j._covariance_from_cholesky_params(np.r_[1000.0, np.zeros(9)])

    with pytest.raises(ValueError, match="eight groups"):
        j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(n_groups=7)
    with pytest.raises(ValueError, match="four observations"):
        j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
            observations_per_group=3
        )
    with pytest.raises(ValueError, match="two finite"):
        j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(beta=(1,))
    with pytest.raises(ValueError, match="two finite"):
        j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
            gamma=(0, np.nan)
        )
    with pytest.raises(ValueError, match="positive finite"):
        j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
            tau_location_slope=0
        )
    with pytest.raises(ValueError, match="strictly between"):
        j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
            rho_location_intercept_location_slope=0.99
        )
    with pytest.raises(ValueError, match="strictly between"):
        j._correlation_matrix(np.nan, 0, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="positive definite"):
        j._correlation_matrix(0.9, 0.9, 0.9, 0.9, 0.9, -0.9)

    out = j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
        n_groups=8, observations_per_group=4, seed=1
    )
    assert out.attrs["known_truth"]["random_effect_covariance"]


def test_prediction_and_certificate_guardrails(fitted_case, monkeypatch):
    data, result = fitted_case
    with pytest.raises(TypeError):
        j._prediction_design(object(), data.head())
    with pytest.raises(TypeError):
        j._prediction_design(result, object())
    with pytest.raises(TypeError):
        j.summarize_gazepoint_hierarchical_location_scale_joint_random_slopes(object())
    with pytest.raises(TypeError):
        j.create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(object())

    nonconv = replace(result, diagnostics={"converged": False})
    with pytest.raises(ValueError, match="non-converged"):
        j.create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(nonconv)
    assert not j.validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
        result, []
    )
    assert not j.validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
        result, {"payload": {}}
    )
    assert not j.validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
        result, {"payload": {"x": object()}, "sha256": "bad"}
    )
    cert = j.create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(result)
    bad = {"payload": dict(cert["payload"]), "sha256": cert["sha256"]}
    bad["payload"]["scale_random_slope_col"] = "other"
    assert not j.validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
        result, bad
    )

    with pytest.raises(ValueError, match="Missing group"):
        j.predict_gazepoint_hierarchical_location_scale_joint_random_slopes(
            result, data.head().drop(columns="participant")
        )

    original = j._apply_encoder

    def mismatch(frame, cols, spec, *, allow_unknown):
        matrix, _ = original(frame, cols, spec, allow_unknown=allow_unknown)
        return matrix, ("bad",)

    monkeypatch.setattr(j, "_apply_encoder", mismatch)
    with pytest.raises(ValueError, match="does not match"):
        j._prediction_design(result, data.head())
    monkeypatch.setattr(j, "_apply_encoder", original)

    def permissive(frame, cols, spec, *, allow_unknown):
        is_mean = cols == list(result.encoder["mean_cols"])
        terms = result.mean_terms if is_mean else result.scale_terms
        return np.ones((len(frame), len(terms))), terms

    monkeypatch.setattr(j, "_apply_encoder", permissive)
    bad_data = data.head().copy()
    bad_data["x_location"] = np.nan
    with pytest.raises(ValueError, match="Location random-slope predictor"):
        j._prediction_design(result, bad_data)
    bad_data = data.head().copy()
    bad_data["x_scale"] = np.nan
    with pytest.raises(ValueError, match="Scale random-slope predictor"):
        j._prediction_design(result, bad_data)


def test_internal_fallbacks_and_objective(monkeypatch, fitted_case):
    data, _ = fitted_case
    y = np.ones(8)
    X = np.ones((8, 1))
    Z = np.ones((8, 1))
    theta0 = j._initial_theta(y, X, Z)
    assert np.isfinite(theta0).all()

    _, inv, logdet, _, _ = j._covariance_from_cholesky_params(
        np.r_[np.log([0.4, 0.3, 0.2, 0.15]), np.zeros(6)]
    )
    yv = np.array([0.2, -0.1, 0.4])
    xb = np.zeros(3)
    zg = np.zeros(3)
    r_location = np.array([-1.0, 0.0, 1.0])
    r_scale = np.array([0.5, -0.3, 0.8])

    original_solve = j.np.linalg.solve
    monkeypatch.setattr(
        j.np.linalg,
        "solve",
        lambda *args, **kwargs: (_ for _ in ()).throw(np.linalg.LinAlgError()),
    )
    b, cov_post, _ = j._posterior_mode(
        yv, xb, zg, r_location, r_scale, inv, logdet, max_steps=2
    )
    assert np.isfinite(b).all() and np.isfinite(cov_post).all()
    monkeypatch.setattr(j.np.linalg, "solve", lambda *args, **kwargs: np.full(4, np.nan))
    b, _, _ = j._posterior_mode(
        yv, xb, zg, r_location, r_scale, inv, logdet, max_steps=2
    )
    assert np.isfinite(b).all()
    monkeypatch.setattr(j.np.linalg, "solve", original_solve)

    original_eig = j.np.linalg.eigvalsh
    original_inv = j.np.linalg.inv
    monkeypatch.setattr(j.np.linalg, "eigvalsh", lambda x: np.array([np.nan, 1, 1, 1]))
    _, cov_post, _ = j._posterior_mode(
        yv, xb, zg, r_location, r_scale, inv, logdet, max_steps=0
    )
    assert np.allclose(cov_post, np.eye(4))
    monkeypatch.setattr(j.np.linalg, "eigvalsh", lambda x: np.array([-1.0, 1, 2, 3]))
    monkeypatch.setattr(
        j.np.linalg,
        "inv",
        lambda x: (_ for _ in ()).throw(np.linalg.LinAlgError()),
    )
    _, cov_post, _ = j._posterior_mode(
        yv, xb, zg, r_location, r_scale, inv, logdet, max_steps=0
    )
    assert np.isfinite(cov_post).all()
    monkeypatch.setattr(j.np.linalg, "eigvalsh", original_eig)
    monkeypatch.setattr(j.np.linalg, "inv", original_inv)

    x0, x1, x2, x3, logw = j._quadrature_nodes(3)
    original_chol = j.np.linalg.cholesky
    monkeypatch.setattr(
        j.np.linalg,
        "cholesky",
        lambda x: (_ for _ in ()).throw(np.linalg.LinAlgError()),
    )
    val, moments = j._adaptive_group_integral(
        yv,
        xb,
        zg,
        r_location,
        r_scale,
        inv,
        logdet,
        x0,
        x1,
        x2,
        x3,
        logw,
        moments=True,
    )
    assert np.isfinite(val) and moments is not None
    monkeypatch.setattr(j.np.linalg, "cholesky", original_chol)

    original_slogdet = j.np.linalg.slogdet
    monkeypatch.setattr(j.np.linalg, "slogdet", lambda x: (0.0, np.nan))
    assert (
        j._adaptive_group_integral(
            yv,
            xb,
            zg,
            r_location,
            r_scale,
            inv,
            logdet,
            x0,
            x1,
            x2,
            x3,
            logw,
        )
        == -np.inf
    )
    assert j._adaptive_group_integral(
        yv,
        xb,
        zg,
        r_location,
        r_scale,
        inv,
        logdet,
        x0,
        x1,
        x2,
        x3,
        logw,
        moments=True,
    ) == (-np.inf, None)
    monkeypatch.setattr(j.np.linalg, "slogdet", original_slogdet)

    bad_theta = np.r_[0.0, 0.0, np.nan, np.zeros(9)]
    assert (
        j._marginal_loglik(
            bad_theta,
            yv,
            X[:3],
            Z[:3],
            r_location,
            r_scale,
            np.zeros(3, dtype=int),
            1,
            x0,
            x1,
            x2,
            x3,
            logw,
        )
        == -np.inf
    )
    theta = np.r_[np.nan, 0.0, np.log([0.4, 0.3, 0.2, 0.15]), np.zeros(6)]
    assert (
        j._marginal_loglik(
            theta,
            yv,
            X[:3],
            Z[:3],
            r_location,
            r_scale,
            np.zeros(3, dtype=int),
            1,
            x0,
            x1,
            x2,
            x3,
            logw,
        )
        == -np.inf
    )
    original_adaptive = j._adaptive_group_integral
    monkeypatch.setattr(j, "_adaptive_group_integral", lambda *args, **kwargs: -np.inf)
    theta = np.r_[0.0, 0.0, np.log([0.4, 0.3, 0.2, 0.15]), np.zeros(6)]
    assert (
        j._marginal_loglik(
            theta,
            yv,
            X[:3],
            Z[:3],
            r_location,
            r_scale,
            np.zeros(3, dtype=int),
            1,
            x0,
            x1,
            x2,
            x3,
            logw,
        )
        == -np.inf
    )
    monkeypatch.setattr(j, "_adaptive_group_integral", original_adaptive)

    def failed_minimize(objective, theta0, **kwargs):
        return SimpleNamespace(
            success=False,
            message="forced",
            x=theta0,
            fun=objective(theta0),
            status=9,
            nit=0,
            nfev=2,
            jac=np.zeros_like(theta0),
        )

    monkeypatch.setattr(j, "minimize", failed_minimize)
    common = dict(
        data=data,
        outcome_col="outcome",
        group_col="participant",
        mean_cols=["x_location"],
        scale_cols=["x_scale"],
        location_random_slope_col="x_location",
        scale_random_slope_col="x_scale",
        quadrature_points=3,
        maxiter=2,
        standardize_numeric=False,
    )
    with pytest.raises(RuntimeError, match="did not converge"):
        j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(**common)
    out = j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
        **common, require_convergence=False
    )
    assert out.diagnostics["converged"] is False


def test_known_truth_signal_recovery():
    data = j.simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
        n_groups=12,
        observations_per_group=6,
        tau_location_slope=0.45,
        tau_log_scale_slope=0.30,
        seed=21,
    )
    result = j.fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
        data,
        "outcome",
        "participant",
        mean_cols=["x_location"],
        scale_cols=["x_scale"],
        location_random_slope_col="x_location",
        scale_random_slope_col="x_scale",
        quadrature_points=3,
        maxiter=100,
        standardize_numeric=False,
    )
    assert result.diagnostics["converged"] is True
    assert result.mean_coef[1] > 0.15
    assert result.tau_location_slope > 0.05
    assert result.tau_log_scale_slope > 0.05
    assert np.linalg.eigvalsh(result.random_effect_covariance).min() > 0
