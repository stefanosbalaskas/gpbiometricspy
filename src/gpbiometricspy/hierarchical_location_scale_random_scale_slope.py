from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence
import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp

from .hierarchical_location_scale import (
    _apply_encoder,
    _canonical_frame_hash,
    _freeze_mapping,
    _normalise_predictor_list,
    _prepare_fit_data,
    _readonly,
)
from .hierarchical_location_scale_random_slope import (
    _canonical_random_effects_hash,
    _covariance_from_cholesky_params,
    _quadrature_nodes,
)

_LOG_2PI = float(np.log(2.0 * np.pi))
_MODEL_VERSION = "gaussian-hierarchical-location-scale-random-scale-slope-v1"


@dataclass(frozen=True)
class GazepointHierarchicalLocationScaleRandomScaleSlopeResult:
    mean_coef: tuple[float, ...]
    scale_coef: tuple[float, ...]
    mean_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    scale_random_slope_col: str
    tau_location_intercept: float
    tau_log_scale_intercept: float
    tau_log_scale_slope: float
    rho_location_log_scale_intercept: float
    rho_location_log_scale_slope: float
    rho_log_scale_intercept_slope: float
    random_effect_covariance: np.ndarray
    log_likelihood: float
    random_effects: pd.DataFrame
    metadata: Mapping
    diagnostics: Mapping
    encoder: Mapping
    parameter_vector: np.ndarray
    model_class: str = "gazepoint_hierarchical_location_scale_random_scale_slope"

    def __post_init__(self):
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        object.__setattr__(self, "diagnostics", _freeze_mapping(self.diagnostics))
        object.__setattr__(self, "encoder", _freeze_mapping(self.encoder))
        object.__setattr__(self, "parameter_vector", _readonly(self.parameter_vector))
        object.__setattr__(self, "random_effect_covariance", _readonly(self.random_effect_covariance))
        object.__setattr__(self, "random_effects", self.random_effects.copy(deep=True))


def _decode_theta(theta: np.ndarray, p: int, q: int):
    theta = np.asarray(theta, dtype=float)
    beta = theta[:p]
    gamma = theta[p:p + q]
    cov_params = theta[p + q:p + q + 6]
    cov, cov_inv, logdet, sds, corr = _covariance_from_cholesky_params(cov_params)
    return beta, gamma, cov, cov_inv, logdet, sds, corr


def _scale_random_slope_values(
    frame: pd.DataFrame,
    groups: np.ndarray,
    scale_random_slope_col: str,
    scale_cols: list[str],
    encoder: Mapping,
) -> np.ndarray:
    if scale_random_slope_col not in scale_cols:
        raise ValueError(
            "`scale_random_slope_col` must also be included in `scale_cols` as a fixed effect."
        )
    cfg = encoder["scale_spec"][scale_random_slope_col]
    if cfg["kind"] != "numeric":
        raise ValueError("`scale_random_slope_col` must be numeric.")
    raw = pd.to_numeric(frame[scale_random_slope_col], errors="coerce").to_numpy(float)
    values = (raw - float(cfg["center"])) / float(cfg["scale"])
    if not np.isfinite(values).all() or float(np.ptp(values)) <= 0:
        raise ValueError("`scale_random_slope_col` must contain finite within-sample variation.")
    if len(np.unique(groups)) < 6:
        raise ValueError("Random scale-slope covariance estimation requires at least six groups/participants.")
    nonvarying = [
        str(label)
        for label in np.unique(groups)
        if np.unique(values[groups == label]).size < 2
    ]
    if nonvarying:
        preview = ", ".join(nonvarying[:5])
        raise ValueError(
            "`scale_random_slope_col` must vary within every group/participant; non-varying groups: "
            + preview
        )
    return values


def _group_logposterior_and_derivatives(
    b,
    y,
    xb,
    zg,
    r,
    cov_inv,
    logdet_cov,
):
    u, v0, v1 = (float(x) for x in b)
    eta = np.clip(zg + v0 + v1 * r, -20.0, 20.0)
    inv_var = np.exp(-2.0 * eta)
    resid = y - xb - u
    ll = np.sum(-0.5 * _LOG_2PI - eta - 0.5 * resid * resid * inv_var)
    bvec = np.asarray(b, dtype=float)
    prior = -1.5 * _LOG_2PI - 0.5 * logdet_cov - 0.5 * float(bvec @ cov_inv @ bvec)
    common = -1.0 + resid * resid * inv_var
    gu = np.sum(resid * inv_var)
    gv0 = np.sum(common)
    gv1 = np.sum(r * common)
    grad = np.array([gu, gv0, gv1], dtype=float) - cov_inv @ bvec
    huu = -np.sum(inv_var)
    huv0 = -2.0 * np.sum(resid * inv_var)
    huv1 = -2.0 * np.sum(r * resid * inv_var)
    hv0v0 = -2.0 * np.sum(resid * resid * inv_var)
    hv0v1 = -2.0 * np.sum(r * resid * resid * inv_var)
    hv1v1 = -2.0 * np.sum(r * r * resid * resid * inv_var)
    hess = np.array(
        [
            [huu, huv0, huv1],
            [huv0, hv0v0, hv0v1],
            [huv1, hv0v1, hv1v1],
        ],
        dtype=float,
    ) - cov_inv
    return float(ll + prior), grad, hess


def _group_logposterior_nodes(u, v0, v1, y, xb, zg, r, cov_inv, logdet_cov):
    eta = np.clip(
        zg[:, None] + v0[None, :] + r[:, None] * v1[None, :],
        -20.0,
        20.0,
    )
    inv_var = np.exp(-2.0 * eta)
    resid = y[:, None] - xb[:, None] - u[None, :]
    ll = np.sum(-0.5 * _LOG_2PI - eta - 0.5 * resid * resid * inv_var, axis=0)
    B = np.vstack([u, v0, v1])
    q = np.einsum("in,ij,jn->n", B, cov_inv, B)
    prior = -1.5 * _LOG_2PI - 0.5 * logdet_cov - 0.5 * q
    return ll + prior


def _posterior_mode(y, xb, zg, r, cov_inv, logdet_cov, *, max_steps=35, tol=1e-9):
    b = np.zeros(3, dtype=float)
    h, grad, hess = _group_logposterior_and_derivatives(
        b, y, xb, zg, r, cov_inv, logdet_cov
    )
    for _ in range(max_steps):
        if float(np.max(np.abs(grad))) <= tol:
            break
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hess) @ grad
        if not np.isfinite(step).all():
            break
        alpha = 1.0
        accepted = False
        while alpha >= 1.0 / 128.0:
            candidate = b - alpha * step
            h_new, grad_new, hess_new = _group_logposterior_and_derivatives(
                candidate, y, xb, zg, r, cov_inv, logdet_cov
            )
            if np.isfinite(h_new) and h_new >= h - 1e-12:
                b, h, grad, hess = candidate, h_new, grad_new, hess_new
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            break
    neg_hess = -hess
    eig = np.linalg.eigvalsh(neg_hess)
    if not np.isfinite(eig).all():
        neg_hess = np.eye(3, dtype=float)
    elif eig.min() <= 1e-10:
        neg_hess = neg_hess + np.eye(3) * (-float(eig.min()) + 1e-8)
    try:
        cov_post = np.linalg.inv(neg_hess)
    except np.linalg.LinAlgError:
        cov_post = np.linalg.pinv(neg_hess)
    return b, cov_post, float(h)


def _adaptive_group_integral(
    y,
    xb,
    zg,
    r,
    cov_inv,
    logdet_cov,
    x0,
    x1,
    x2,
    logw,
    *,
    moments=False,
):
    mode, cov_post, _ = _posterior_mode(y, xb, zg, r, cov_inv, logdet_cov)
    try:
        L = np.linalg.cholesky(cov_post)
    except np.linalg.LinAlgError:
        eigval, eigvec = np.linalg.eigh(cov_post)
        eigval = np.clip(eigval, 1e-10, None)
        L = eigvec @ np.diag(np.sqrt(eigval))
    coords = np.sqrt(2.0) * np.vstack([x0, x1, x2])
    B = mode[:, None] + L @ coords
    h = _group_logposterior_nodes(
        B[0], B[1], B[2], y, xb, zg, r, cov_inv, logdet_cov
    )
    sign, logdetL = np.linalg.slogdet(L)
    if sign == 0 or not np.isfinite(logdetL):
        return (-np.inf, None) if moments else -np.inf
    log_terms = logw + h + x0 * x0 + x1 * x1 + x2 * x2
    norm = logsumexp(log_terms)
    log_integral = float(norm + 1.5 * np.log(2.0) + logdetL)
    if not moments:
        return log_integral
    probs = np.exp(log_terms - norm)
    means = np.sum(B * probs[None, :], axis=1)
    centered = B - means[:, None]
    covariance = (centered * probs[None, :]) @ centered.T
    sds = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    return log_integral, (means, sds, covariance, mode, cov_post)


def _marginal_loglik(
    theta,
    y,
    X,
    Z,
    r,
    group_index,
    n_groups,
    x0,
    x1,
    x2,
    logw,
):
    p, q = X.shape[1], Z.shape[1]
    try:
        beta, gamma, _, cov_inv, logdet_cov, _, _ = _decode_theta(theta, p, q)
    except (ValueError, np.linalg.LinAlgError):
        return -np.inf
    if not (np.isfinite(beta).all() and np.isfinite(gamma).all()):
        return -np.inf
    xb = X @ beta
    zg = Z @ gamma
    total = 0.0
    for g in range(n_groups):
        idx = group_index == g
        val = _adaptive_group_integral(
            y[idx], xb[idx], zg[idx], r[idx],
            cov_inv, logdet_cov, x0, x1, x2, logw
        )
        if not np.isfinite(val):
            return -np.inf
        total += float(val)
    return total


def _initial_theta(y, X, Z):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ddof = max(1, min(X.shape[1], len(y) - 1))
    sd = float(np.std(resid, ddof=ddof))
    if not np.isfinite(sd) or sd <= 1e-6:
        sd = max(float(np.std(y)), 1.0)
    gamma = np.zeros(Z.shape[1], dtype=float)
    gamma[0] = np.log(max(sd, 1e-4))
    return np.r_[
        beta,
        gamma,
        np.log(max(sd * 0.35, 1e-3)),
        np.log(0.15),
        np.log(0.10),
        0.0,
        0.0,
        0.0,
    ]


def _estimate_random_effects(
    result_theta,
    y,
    X,
    Z,
    r,
    group_index,
    unique_groups,
    x0,
    x1,
    x2,
    logw,
):
    p, q = X.shape[1], Z.shape[1]
    beta, gamma, _, cov_inv, logdet_cov, _, _ = _decode_theta(result_theta, p, q)
    xb = X @ beta
    zg = Z @ gamma
    rows = []
    for g, label in enumerate(unique_groups):
        idx = group_index == g
        _, moments = _adaptive_group_integral(
            y[idx], xb[idx], zg[idx], r[idx],
            cov_inv, logdet_cov, x0, x1, x2, logw, moments=True
        )
        means, sds, covariance, mode, _ = moments
        rows.append(
            {
                "group": str(label),
                "location_intercept_re": float(means[0]),
                "log_scale_intercept_re": float(means[1]),
                "log_scale_slope_re": float(means[2]),
                "location_intercept_re_sd": float(sds[0]),
                "log_scale_intercept_re_sd": float(sds[1]),
                "log_scale_slope_re_sd": float(sds[2]),
                "location_log_scale_intercept_re_cov": float(covariance[0, 1]),
                "location_log_scale_slope_re_cov": float(covariance[0, 2]),
                "log_scale_intercept_slope_re_cov": float(covariance[1, 2]),
                "location_intercept_mode": float(mode[0]),
                "log_scale_intercept_mode": float(mode[1]),
                "log_scale_slope_mode": float(mode[2]),
                "n_obs": int(np.sum(idx)),
            }
        )
    return pd.DataFrame(rows)


def fit_gazepoint_hierarchical_location_scale_random_scale_slope(
    data: pd.DataFrame,
    outcome_col: str,
    group_col: str,
    mean_cols: Sequence[str] | str | None = None,
    scale_cols: Sequence[str] | str | None = None,
    *,
    scale_random_slope_col: str,
    quadrature_points: int = 5,
    standardize_numeric: bool = True,
    maxiter: int = 300,
    tolerance: float = 1e-7,
    require_convergence: bool = True,
) -> GazepointHierarchicalLocationScaleRandomScaleSlopeResult:
    """Fit a Gaussian location-scale model with one group-specific log-scale slope.

    The random-effects vector is ``(location intercept, log-scale intercept,
    log-scale slope)`` with a full 3x3 covariance matrix. The slope variable must
    be numeric, vary within every group, and also appear in the fixed log-scale
    equation. This model estimates heterogeneity in conditional residual-scale
    associations; it is not artifact correction, sensor-validity weighting,
    causal inference, or a latent-state model.
    """
    mean_cols = _normalise_predictor_list(mean_cols)
    scale_cols = _normalise_predictor_list(scale_cols)
    scale_random_slope_col = str(scale_random_slope_col)
    if not isinstance(quadrature_points, (int, np.integer)) or not (3 <= quadrature_points <= 11):
        raise ValueError("`quadrature_points` must be an integer between 3 and 11.")
    if not isinstance(maxiter, (int, np.integer)) or maxiter < 1:
        raise ValueError("`maxiter` must be a positive integer.")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("`tolerance` must be a positive finite scalar.")
    (
        frame,
        y,
        groups,
        unique_groups,
        group_index,
        X,
        Z,
        mean_terms,
        scale_terms,
        encoder,
    ) = _prepare_fit_data(
        data,
        outcome_col,
        group_col,
        mean_cols,
        scale_cols,
        standardize_numeric=standardize_numeric,
    )
    r = _scale_random_slope_values(
        frame, groups, scale_random_slope_col, scale_cols, encoder
    )
    x0, x1, x2, logw = _quadrature_nodes(int(quadrature_points))
    theta0 = _initial_theta(y, X, Z)
    p, q = X.shape[1], Z.shape[1]
    bounds = (
        [(None, None)] * (p + q)
        + [(-9.0, 5.0), (-9.0, 3.0), (-9.0, 3.0)]
        + [(-5.0, 5.0)] * 3
    )

    def objective(theta):
        ll = _marginal_loglik(
            theta, y, X, Z, r, group_index, len(unique_groups),
            x0, x1, x2, logw
        )
        return 1e100 if not np.isfinite(ll) else -ll

    opt = minimize(
        objective,
        theta0,
        method="L-BFGS-B",
        bounds=bounds,
        options={
            "maxiter": int(maxiter),
            "ftol": float(tolerance),
            "gtol": float(tolerance),
        },
    )
    if require_convergence and not bool(opt.success):
        raise RuntimeError(
            f"Random scale-slope location-scale optimization did not converge: {opt.message}"
        )
    theta = np.asarray(opt.x, dtype=float)
    beta, gamma, cov, _, _, sds, corr = _decode_theta(theta, p, q)
    ll = -float(opt.fun)
    re = _estimate_random_effects(
        theta, y, X, Z, r, group_index, unique_groups, x0, x1, x2, logw
    )
    selected = frame.loc[
        :,
        list(dict.fromkeys([outcome_col, group_col, *mean_cols, *scale_cols])),
    ].copy()
    selected[group_col] = selected[group_col].astype(str)
    group_sizes = pd.Series(groups).value_counts()
    warnings = (
        "Gaussian conditional outcome model with one random slope in the log-scale equation only.",
        "The random scale slope is participant/group-specific residual-heterogeneity association, not a causal effect.",
        "The log-scale equation models conditional residual heterogeneity; it is not artifact correction or sensor-validity weighting.",
        "Random-effect estimates are empirical-Bayes summaries conditional on the fitted model.",
        "Predictions for unseen groups are population-level.",
        "Crossed random effects, additional random slopes, and simultaneous location-and-scale random slopes are outside this model.",
    )
    metadata = {
        "model_version": _MODEL_VERSION,
        "outcome_col": str(outcome_col),
        "group_col": str(group_col),
        "mean_cols": tuple(mean_cols),
        "scale_cols": tuple(scale_cols),
        "scale_random_slope_col": scale_random_slope_col,
        "n_obs": int(len(y)),
        "n_groups": int(len(unique_groups)),
        "min_group_size": int(group_sizes.min()),
        "max_group_size": int(group_sizes.max()),
        "quadrature_points": int(quadrature_points),
        "quadrature_scheme": "three-dimensional adaptive Gauss-Hermite",
        "standardize_numeric": bool(standardize_numeric),
        "require_convergence": bool(require_convergence),
        "data_sha256": _canonical_frame_hash(selected),
        "claim_boundaries": warnings,
    }
    grad = np.asarray(getattr(opt, "jac", np.array([])), dtype=float)
    diagnostics = {
        "converged": bool(opt.success),
        "optimizer_status": int(opt.status),
        "optimizer_message": str(opt.message),
        "n_iterations": int(getattr(opt, "nit", 0)),
        "n_function_evaluations": int(getattr(opt, "nfev", 0)),
        "gradient_max_abs": float(np.max(np.abs(grad))) if grad.size else np.nan,
        "log_likelihood": ll,
    }
    encoder_payload = {
        "mean_cols": tuple(mean_cols),
        "scale_cols": tuple(scale_cols),
        "mean_spec": encoder["mean_spec"],
        "scale_spec": encoder["scale_spec"],
        "standardize_numeric": encoder["standardize_numeric"],
    }
    return GazepointHierarchicalLocationScaleRandomScaleSlopeResult(
        mean_coef=tuple(float(x) for x in beta),
        scale_coef=tuple(float(x) for x in gamma),
        mean_terms=tuple(mean_terms),
        scale_terms=tuple(scale_terms),
        scale_random_slope_col=scale_random_slope_col,
        tau_location_intercept=float(sds[0]),
        tau_log_scale_intercept=float(sds[1]),
        tau_log_scale_slope=float(sds[2]),
        rho_location_log_scale_intercept=float(corr[0, 1]),
        rho_location_log_scale_slope=float(corr[0, 2]),
        rho_log_scale_intercept_slope=float(corr[1, 2]),
        random_effect_covariance=cov,
        log_likelihood=ll,
        random_effects=re,
        metadata=metadata,
        diagnostics=diagnostics,
        encoder=encoder_payload,
        parameter_vector=theta,
    )


def _prediction_design(result, data: pd.DataFrame):
    if not isinstance(result, GazepointHierarchicalLocationScaleRandomScaleSlopeResult):
        raise TypeError(
            "`result` must be returned by fit_gazepoint_hierarchical_location_scale_random_scale_slope()."
        )
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    mean_cols = list(result.encoder["mean_cols"])
    scale_cols = list(result.encoder["scale_cols"])
    X, mt = _apply_encoder(
        data, mean_cols, result.encoder["mean_spec"], allow_unknown=False
    )
    Z, st = _apply_encoder(
        data, scale_cols, result.encoder["scale_spec"], allow_unknown=False
    )
    if mt != result.mean_terms or st != result.scale_terms:
        raise ValueError("Prediction design does not match fitted design terms.")
    cfg = result.encoder["scale_spec"][result.scale_random_slope_col]
    raw = pd.to_numeric(data[result.scale_random_slope_col], errors="coerce").to_numpy(float)
    if not np.isfinite(raw).all():
        raise ValueError("Random scale-slope predictor contains missing or non-finite values.")
    r = (raw - float(cfg["center"])) / float(cfg["scale"])
    return X, Z, r


def predict_gazepoint_hierarchical_location_scale_random_scale_slope(
    result: GazepointHierarchicalLocationScaleRandomScaleSlopeResult,
    data: pd.DataFrame,
    *,
    group_col: str | None = None,
    include_random_effects: bool = True,
) -> pd.DataFrame:
    X, Z, r = _prediction_design(result, data)
    beta = np.asarray(result.mean_coef, dtype=float)
    gamma = np.asarray(result.scale_coef, dtype=float)
    u = np.zeros(len(data), dtype=float)
    v0 = np.zeros(len(data), dtype=float)
    v1 = np.zeros(len(data), dtype=float)
    source = np.full(len(data), "population", dtype=object)
    use_group = result.metadata["group_col"] if group_col is None else group_col
    if include_random_effects:
        if use_group not in data:
            raise ValueError(f"Missing group column `{use_group}` for conditional prediction.")
        lookup = result.random_effects.set_index("group")
        labels = data[use_group].astype(str).to_numpy()
        for i, label in enumerate(labels):
            if label in lookup.index:
                row = lookup.loc[label]
                u[i] = float(row["location_intercept_re"])
                v0[i] = float(row["log_scale_intercept_re"])
                v1[i] = float(row["log_scale_slope_re"])
                source[i] = "empirical_bayes"
            else:
                source[i] = "population_unseen_group"
    random_log_scale = v0 + v1 * r
    mean = X @ beta + u
    log_scale = np.clip(Z @ gamma + random_log_scale, -20.0, 20.0)
    return pd.DataFrame(
        {
            "predicted_mean": mean,
            "predicted_scale": np.exp(log_scale),
            "predicted_log_scale": log_scale,
            "random_scale_slope_value": r,
            "random_location_effect": u,
            "random_log_scale_effect": random_log_scale,
            "random_effect_source": source,
        },
        index=data.index,
    )


def summarize_gazepoint_hierarchical_location_scale_random_scale_slope(
    result: GazepointHierarchicalLocationScaleRandomScaleSlopeResult,
) -> dict:
    if not isinstance(result, GazepointHierarchicalLocationScaleRandomScaleSlopeResult):
        raise TypeError(
            "`result` must be returned by fit_gazepoint_hierarchical_location_scale_random_scale_slope()."
        )
    mean = pd.DataFrame(
        {"term": result.mean_terms, "estimate": result.mean_coef, "equation": "location"}
    )
    scale = pd.DataFrame(
        {"term": result.scale_terms, "estimate": result.scale_coef, "equation": "log_scale"}
    )
    labels = ["location_intercept", "log_scale_intercept", "log_scale_slope"]
    covariance = pd.DataFrame(
        np.asarray(result.random_effect_covariance),
        index=labels,
        columns=labels,
    )
    return {
        "fixed_effects": pd.concat([mean, scale], ignore_index=True),
        "random_effect_parameters": pd.DataFrame(
            [
                {
                    "tau_location_intercept": result.tau_location_intercept,
                    "tau_log_scale_intercept": result.tau_log_scale_intercept,
                    "tau_log_scale_slope": result.tau_log_scale_slope,
                    "rho_location_log_scale_intercept": result.rho_location_log_scale_intercept,
                    "rho_location_log_scale_slope": result.rho_location_log_scale_slope,
                    "rho_log_scale_intercept_slope": result.rho_log_scale_intercept_slope,
                }
            ]
        ),
        "random_effect_covariance": covariance,
        "random_effects": result.random_effects.copy(deep=True),
        "diagnostics": dict(result.diagnostics),
        "metadata": dict(result.metadata),
        "class": "gazepoint_hierarchical_location_scale_random_scale_slope_summary",
    }


def create_gazepoint_hierarchical_location_scale_random_scale_slope_certificate(
    result: GazepointHierarchicalLocationScaleRandomScaleSlopeResult,
) -> dict:
    if not isinstance(result, GazepointHierarchicalLocationScaleRandomScaleSlopeResult):
        raise TypeError(
            "`result` must be returned by fit_gazepoint_hierarchical_location_scale_random_scale_slope()."
        )
    if not bool(result.diagnostics.get("converged", False)):
        raise ValueError("Cannot create a reproducibility certificate from a non-converged fit.")
    payload = {
        "model_version": result.metadata["model_version"],
        "data_sha256": result.metadata["data_sha256"],
        "random_effects_sha256": _canonical_random_effects_hash(result.random_effects),
        "mean_terms": list(result.mean_terms),
        "scale_terms": list(result.scale_terms),
        "scale_random_slope_col": result.scale_random_slope_col,
        "mean_coef": list(result.mean_coef),
        "scale_coef": list(result.scale_coef),
        "random_effect_covariance": np.asarray(result.random_effect_covariance).tolist(),
        "quadrature_points": result.metadata["quadrature_points"],
        "converged": True,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return {"payload": payload, "sha256": sha256(canonical.encode("utf-8")).hexdigest()}


def validate_gazepoint_hierarchical_location_scale_random_scale_slope_certificate(
    result,
    certificate,
) -> bool:
    if not isinstance(certificate, Mapping) or "payload" not in certificate or "sha256" not in certificate:
        return False
    try:
        expected = create_gazepoint_hierarchical_location_scale_random_scale_slope_certificate(result)
        supplied_payload = dict(certificate["payload"])
        canonical = json.dumps(
            supplied_payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (KeyError, TypeError, ValueError):
        return False
    supplied_digest = sha256(canonical.encode("utf-8")).hexdigest()
    return (
        supplied_digest == certificate["sha256"]
        and supplied_payload == expected["payload"]
    )


def _correlation_matrix(
    rho_location_log_scale_intercept,
    rho_location_log_scale_slope,
    rho_log_scale_intercept_slope,
):
    corr = np.array(
        [
            [1.0, rho_location_log_scale_intercept, rho_location_log_scale_slope],
            [rho_location_log_scale_intercept, 1.0, rho_log_scale_intercept_slope],
            [rho_location_log_scale_slope, rho_log_scale_intercept_slope, 1.0],
        ],
        dtype=float,
    )
    if not np.isfinite(corr).all() or np.any(np.abs(corr[np.triu_indices(3, 1)]) >= 0.99):
        raise ValueError("Random-effect correlations must be finite and strictly between -0.99 and 0.99.")
    if np.linalg.eigvalsh(corr).min() <= 1e-8:
        raise ValueError("Random-effect correlation matrix must be positive definite.")
    return corr


def simulate_gazepoint_hierarchical_location_scale_random_scale_slope(
    n_groups: int = 24,
    observations_per_group: int = 10,
    *,
    beta: Sequence[float] = (0.0, 0.6),
    gamma: Sequence[float] = (-0.2, 0.25),
    tau_location_intercept: float = 0.5,
    tau_log_scale_intercept: float = 0.2,
    tau_log_scale_slope: float = 0.15,
    rho_location_log_scale_intercept: float = 0.10,
    rho_location_log_scale_slope: float = -0.05,
    rho_log_scale_intercept_slope: float = 0.10,
    seed: int | None = None,
) -> pd.DataFrame:
    if n_groups < 6 or observations_per_group < 3:
        raise ValueError("Need at least six groups and three observations per group.")
    beta = np.asarray(beta, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    if beta.shape != (2,) or gamma.shape != (2,) or not np.isfinite(beta).all() or not np.isfinite(gamma).all():
        raise ValueError("`beta` and `gamma` must each contain two finite values.")
    sds = np.array(
        [tau_location_intercept, tau_log_scale_intercept, tau_log_scale_slope],
        dtype=float,
    )
    if not np.isfinite(sds).all() or np.any(sds <= 0):
        raise ValueError("Random-effect standard deviations must be positive finite values.")
    corr = _correlation_matrix(
        rho_location_log_scale_intercept,
        rho_location_log_scale_slope,
        rho_log_scale_intercept_slope,
    )
    cov = np.outer(sds, sds) * corr
    rng = np.random.default_rng(seed)
    effects = rng.multivariate_normal(np.zeros(3), cov, size=n_groups)
    rows = []
    for g in range(n_groups):
        x = rng.normal(size=observations_per_group)
        mu = beta[0] + beta[1] * x + effects[g, 0]
        log_sigma = (
            gamma[0]
            + gamma[1] * x
            + effects[g, 1]
            + effects[g, 2] * x
        )
        y = rng.normal(mu, np.exp(log_sigma))
        for j in range(observations_per_group):
            rows.append(
                {
                    "participant": f"P{g + 1:03d}",
                    "x": float(x[j]),
                    "outcome": float(y[j]),
                }
            )
    out = pd.DataFrame(rows)
    out.attrs["known_truth"] = {
        "beta": tuple(float(v) for v in beta),
        "gamma": tuple(float(v) for v in gamma),
        "random_effect_covariance": cov.tolist(),
        "tau_location_intercept": float(tau_location_intercept),
        "tau_log_scale_intercept": float(tau_log_scale_intercept),
        "tau_log_scale_slope": float(tau_log_scale_slope),
        "rho_location_log_scale_intercept": float(rho_location_log_scale_intercept),
        "rho_location_log_scale_slope": float(rho_location_log_scale_slope),
        "rho_log_scale_intercept_slope": float(rho_log_scale_intercept_slope),
        "seed": seed,
    }
    return out
