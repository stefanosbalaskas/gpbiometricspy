from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping, Sequence
import json

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import minimize
from scipy.special import logsumexp

_LOG_2PI = float(np.log(2.0 * np.pi))
_MODEL_VERSION = "gaussian-hierarchical-location-scale-v1"


def _deep_freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(v) for v in value)
    return value


def _freeze_mapping(values: Mapping) -> Mapping:
    return _deep_freeze(dict(values))


def _readonly(values) -> np.ndarray:
    arr = np.asarray(values, dtype=float).copy()
    arr.setflags(write=False)
    return arr


@dataclass(frozen=True)
class GazepointHierarchicalLocationScaleResult:
    mean_coef: tuple[float, ...]
    scale_coef: tuple[float, ...]
    mean_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    tau_location: float
    tau_log_scale: float
    rho: float
    log_likelihood: float
    random_effects: pd.DataFrame
    metadata: Mapping
    diagnostics: Mapping
    encoder: Mapping
    parameter_vector: np.ndarray
    model_class: str = "gazepoint_hierarchical_location_scale"

    def __post_init__(self):
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        object.__setattr__(self, "diagnostics", _freeze_mapping(self.diagnostics))
        object.__setattr__(self, "encoder", _freeze_mapping(self.encoder))
        object.__setattr__(self, "parameter_vector", _readonly(self.parameter_vector))
        re = self.random_effects.copy(deep=True)
        object.__setattr__(self, "random_effects", re)


def _normalise_predictor_list(cols: Sequence[str] | str | None) -> list[str]:
    if cols is None:
        return []
    if isinstance(cols, str):
        cols = [cols]
    out = [str(x) for x in cols]
    if len(out) != len(set(out)):
        raise ValueError("Predictor columns must be unique within each equation.")
    return out


def _fit_encoder(data: pd.DataFrame, cols: list[str], *, standardize_numeric: bool) -> tuple[dict, tuple[str, ...]]:
    spec: dict[str, dict] = {}
    terms = ["Intercept"]
    for col in cols:
        s = data[col]
        if pd.api.types.is_numeric_dtype(s):
            x = pd.to_numeric(s, errors="coerce").to_numpy(float)
            finite = x[np.isfinite(x)]
            if finite.size == 0:
                raise ValueError(f"Predictor `{col}` has no finite values.")
            center = float(np.mean(finite)) if standardize_numeric else 0.0
            scale = float(np.std(finite, ddof=0)) if standardize_numeric else 1.0
            if not np.isfinite(scale) or scale <= 0:
                scale = 1.0
            spec[col] = {"kind": "numeric", "center": center, "scale": scale}
            terms.append(col)
        else:
            vals = s.dropna().astype(str)
            levels = tuple(sorted(vals.unique().tolist()))
            if len(levels) < 2:
                raise ValueError(f"Categorical predictor `{col}` must contain at least two observed levels.")
            spec[col] = {"kind": "categorical", "levels": levels, "reference": levels[0]}
            terms.extend(f"{col}[{level}]" for level in levels[1:])
    return spec, tuple(terms)


def _apply_encoder(data: pd.DataFrame, cols: list[str], spec: Mapping, *, allow_unknown: bool) -> tuple[np.ndarray, tuple[str, ...]]:
    pieces = [np.ones((len(data), 1), dtype=float)]
    terms = ["Intercept"]
    for col in cols:
        if col not in data:
            raise ValueError(f"Missing predictor column `{col}`.")
        cfg = spec[col]
        if cfg["kind"] == "numeric":
            x = pd.to_numeric(data[col], errors="coerce").to_numpy(float)
            if not np.isfinite(x).all():
                raise ValueError(f"Predictor `{col}` contains missing or non-finite values.")
            pieces.append(((x - float(cfg["center"])) / float(cfg["scale"]))[:, None])
            terms.append(col)
        else:
            x = data[col].astype(str).to_numpy()
            levels = tuple(cfg["levels"])
            unknown = sorted(set(x) - set(levels))
            if unknown and not allow_unknown:
                raise ValueError(f"Predictor `{col}` contains unseen categorical levels: {unknown}.")
            for level in levels[1:]:
                pieces.append((x == level).astype(float)[:, None])
                terms.append(f"{col}[{level}]")
    return np.concatenate(pieces, axis=1), tuple(terms)


def _canonical_frame_hash(frame: pd.DataFrame) -> str:
    text = frame.to_csv(index=False, lineterminator="\n", float_format="%.17g")
    return sha256(text.encode("utf-8")).hexdigest()


def _prepare_fit_data(
    data: pd.DataFrame,
    outcome_col: str,
    group_col: str,
    mean_cols: list[str],
    scale_cols: list[str],
    *,
    standardize_numeric: bool,
):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    if outcome_col == group_col:
        raise ValueError("`outcome_col` and `group_col` must be distinct.")
    reserved = {outcome_col, group_col}
    aliased = [c for c in dict.fromkeys([*mean_cols, *scale_cols]) if c in reserved]
    if aliased:
        raise ValueError(
            "Predictor columns must not reuse `outcome_col` or `group_col`: "
            + ", ".join(aliased)
        )
    needed = [outcome_col, group_col, *mean_cols, *scale_cols]
    missing = [c for c in dict.fromkeys(needed) if c not in data]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))
    frame = data.loc[:, list(dict.fromkeys(needed))].copy()
    y = pd.to_numeric(frame[outcome_col], errors="coerce")
    keep = y.notna() & np.isfinite(y.to_numpy(float)) & frame[group_col].notna()
    for col in set(mean_cols + scale_cols):
        keep &= frame[col].notna()
        if pd.api.types.is_numeric_dtype(frame[col]):
            xv = pd.to_numeric(frame[col], errors="coerce")
            keep &= xv.notna() & np.isfinite(xv.to_numpy(float))
    frame = frame.loc[keep].reset_index(drop=True)
    if frame.empty:
        raise ValueError("No complete finite rows remain after filtering.")
    yv = pd.to_numeric(frame[outcome_col], errors="raise").to_numpy(float)
    groups = frame[group_col].astype(str).to_numpy()
    unique_groups, group_index = np.unique(groups, return_inverse=True)
    if len(unique_groups) < 3:
        raise ValueError("At least three groups/participants are required.")
    mean_spec, mean_terms = _fit_encoder(frame, mean_cols, standardize_numeric=standardize_numeric)
    scale_spec, scale_terms = _fit_encoder(frame, scale_cols, standardize_numeric=standardize_numeric)
    X, mean_terms2 = _apply_encoder(frame, mean_cols, mean_spec, allow_unknown=False)
    Z, scale_terms2 = _apply_encoder(frame, scale_cols, scale_spec, allow_unknown=False)
    assert mean_terms == mean_terms2 and scale_terms == scale_terms2
    enc = {
        "mean_cols": tuple(mean_cols),
        "scale_cols": tuple(scale_cols),
        "mean_spec": mean_spec,
        "scale_spec": scale_spec,
        "standardize_numeric": bool(standardize_numeric),
    }
    return frame, yv, groups, unique_groups, group_index, X, Z, mean_terms, scale_terms, enc


def _decode_theta(theta: np.ndarray, p: int, q: int):
    beta = theta[:p]
    gamma = theta[p:p + q]
    log_tau_loc, log_tau_scale, atanh_rho = theta[p + q:p + q + 3]
    tau_loc = float(np.exp(log_tau_loc))
    tau_scale = float(np.exp(log_tau_scale))
    rho = float(np.tanh(atanh_rho))
    return beta, gamma, tau_loc, tau_scale, rho


def _random_effect_covariance(tau_loc: float, tau_scale: float, rho: float):
    cov = np.array([
        [tau_loc * tau_loc, rho * tau_loc * tau_scale],
        [rho * tau_loc * tau_scale, tau_scale * tau_scale],
    ], dtype=float)
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0 or not np.isfinite(logdet):
        raise np.linalg.LinAlgError("Random-effect covariance is not positive definite.")
    inv = np.linalg.inv(cov)
    return cov, inv, float(logdet)


def _group_logposterior_and_derivatives(b, y, xb, zg, cov_inv, logdet_cov):
    u, v = float(b[0]), float(b[1])
    eta = np.clip(zg + v, -20.0, 20.0)
    inv_var = np.exp(-2.0 * eta)
    resid = y - xb - u
    ll = np.sum(-0.5 * _LOG_2PI - eta - 0.5 * resid * resid * inv_var)
    prior = -_LOG_2PI - 0.5 * logdet_cov - 0.5 * float(np.asarray(b) @ cov_inv @ np.asarray(b))
    grad_ll = np.array([
        np.sum(resid * inv_var),
        np.sum(-1.0 + resid * resid * inv_var),
    ])
    hess_ll = np.array([
        [-np.sum(inv_var), -2.0 * np.sum(resid * inv_var)],
        [-2.0 * np.sum(resid * inv_var), -2.0 * np.sum(resid * resid * inv_var)],
    ])
    grad = grad_ll - cov_inv @ np.asarray(b)
    hess = hess_ll - cov_inv
    return float(ll + prior), grad, hess


def _group_logposterior_nodes(u, v, y, xb, zg, cov_inv, logdet_cov):
    eta = np.clip(zg[:, None] + v[None, :], -20.0, 20.0)
    inv_var = np.exp(-2.0 * eta)
    resid = y[:, None] - xb[:, None] - u[None, :]
    ll = np.sum(-0.5 * _LOG_2PI - eta - 0.5 * resid * resid * inv_var, axis=0)
    q = cov_inv[0, 0] * u * u + 2.0 * cov_inv[0, 1] * u * v + cov_inv[1, 1] * v * v
    prior = -_LOG_2PI - 0.5 * logdet_cov - 0.5 * q
    return ll + prior


def _posterior_mode(y, xb, zg, cov_inv, logdet_cov, *, max_steps=30, tol=1e-9):
    b = np.zeros(2, dtype=float)
    h, grad, hess = _group_logposterior_and_derivatives(b, y, xb, zg, cov_inv, logdet_cov)
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
                candidate, y, xb, zg, cov_inv, logdet_cov
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
    if not np.isfinite(eig).all() or eig.min() <= 1e-10:
        neg_hess = neg_hess + np.eye(2) * (max(1e-8, -float(np.nanmin(eig)) + 1e-8))
    cov_post = np.linalg.inv(neg_hess)
    return b, cov_post, float(h)


def _quadrature_nodes(points: int):
    nodes, weights = hermgauss(points)
    x1, x2 = np.meshgrid(nodes, nodes, indexing="ij")
    logw = np.log(np.outer(weights, weights).ravel())
    return x1.ravel(), x2.ravel(), logw


def _adaptive_group_integral(y, xb, zg, cov_inv, logdet_cov, x1, x2, logw, *, moments=False):
    mode, cov_post, _ = _posterior_mode(y, xb, zg, cov_inv, logdet_cov)
    try:
        L = np.linalg.cholesky(cov_post)
    except np.linalg.LinAlgError:
        eigval, eigvec = np.linalg.eigh(cov_post)
        eigval = np.clip(eigval, 1e-10, None)
        L = eigvec @ np.diag(np.sqrt(eigval))
    dx1 = np.sqrt(2.0) * x1
    dx2 = np.sqrt(2.0) * x2
    u = mode[0] + L[0, 0] * dx1 + L[0, 1] * dx2
    v = mode[1] + L[1, 0] * dx1 + L[1, 1] * dx2
    h = _group_logposterior_nodes(u, v, y, xb, zg, cov_inv, logdet_cov)
    sign, logdetL = np.linalg.slogdet(L)
    if sign == 0 or not np.isfinite(logdetL):
        return (-np.inf, None) if moments else -np.inf
    log_terms = logw + h + x1 * x1 + x2 * x2
    log_integral = float(logsumexp(log_terms) + np.log(2.0) + logdetL)
    if not moments:
        return log_integral
    probs = np.exp(log_terms - logsumexp(log_terms))
    mu_u = float(np.sum(probs * u)); mu_v = float(np.sum(probs * v))
    sd_u = float(np.sqrt(max(np.sum(probs * (u - mu_u) ** 2), 0.0)))
    sd_v = float(np.sqrt(max(np.sum(probs * (v - mu_v) ** 2), 0.0)))
    cov_uv = float(np.sum(probs * (u - mu_u) * (v - mu_v)))
    return log_integral, (mu_u, mu_v, sd_u, sd_v, cov_uv, mode, cov_post)


def _marginal_loglik(theta, y, X, Z, group_index, n_groups, x1, x2, logw):
    p, q = X.shape[1], Z.shape[1]
    beta, gamma, tau_loc, tau_scale, rho = _decode_theta(theta, p, q)
    if not (np.isfinite(tau_loc) and np.isfinite(tau_scale) and np.isfinite(rho)):
        return -np.inf
    try:
        _, cov_inv, logdet_cov = _random_effect_covariance(tau_loc, tau_scale, rho)
    except np.linalg.LinAlgError:
        return -np.inf
    xb = X @ beta; zg = Z @ gamma
    total = 0.0
    for g in range(n_groups):
        idx = group_index == g
        val = _adaptive_group_integral(y[idx], xb[idx], zg[idx], cov_inv, logdet_cov, x1, x2, logw)
        if not np.isfinite(val):
            return -np.inf
        total += float(val)
    return total


def _initial_theta(y, X, Z):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sd = float(np.std(resid, ddof=max(1, min(X.shape[1], len(y) - 1))))
    if not np.isfinite(sd) or sd <= 1e-6:
        sd = max(float(np.std(y)), 1.0)
    gamma = np.zeros(Z.shape[1], dtype=float)
    gamma[0] = np.log(max(sd, 1e-4))
    return np.r_[beta, gamma, np.log(max(sd * 0.35, 1e-3)), np.log(0.15), 0.0]


def _estimate_random_effects(result_theta, y, X, Z, group_index, unique_groups, x1, x2, logw):
    p, q = X.shape[1], Z.shape[1]
    beta, gamma, tau_loc, tau_scale, rho = _decode_theta(result_theta, p, q)
    _, cov_inv, logdet_cov = _random_effect_covariance(tau_loc, tau_scale, rho)
    xb = X @ beta; zg = Z @ gamma
    rows = []
    for g, label in enumerate(unique_groups):
        idx = group_index == g
        _, moments = _adaptive_group_integral(
            y[idx], xb[idx], zg[idx], cov_inv, logdet_cov, x1, x2, logw, moments=True
        )
        mu_u, mu_v, sd_u, sd_v, cov_uv, mode, cov_post = moments
        rows.append({
            "group": str(label), "location_re": mu_u, "log_scale_re": mu_v,
            "location_re_sd": sd_u, "log_scale_re_sd": sd_v,
            "location_log_scale_re_cov": cov_uv,
            "location_mode": float(mode[0]), "log_scale_mode": float(mode[1]),
            "n_obs": int(np.sum(idx)),
        })
    return pd.DataFrame(rows)


def fit_gazepoint_hierarchical_location_scale(
    data: pd.DataFrame,
    outcome_col: str,
    group_col: str,
    mean_cols: Sequence[str] | str | None = None,
    scale_cols: Sequence[str] | str | None = None,
    *,
    quadrature_points: int = 7,
    standardize_numeric: bool = True,
    maxiter: int = 300,
    tolerance: float = 1e-7,
    require_convergence: bool = True,
) -> GazepointHierarchicalLocationScaleResult:
    """Fit a Gaussian random-intercept location-scale model by 2D adaptive Gauss-Hermite quadrature.

    The mean and log-residual-scale equations each receive a participant/group random
    intercept. Their correlation is estimated. The method models distributional
    heterogeneity; it does not identify sensor validity, artifact mechanisms, causal
    effects, or latent psychological states.
    """
    mean_cols = _normalise_predictor_list(mean_cols)
    scale_cols = _normalise_predictor_list(scale_cols)
    if not isinstance(quadrature_points, (int, np.integer)) or quadrature_points < 3 or quadrature_points > 25:
        raise ValueError("`quadrature_points` must be an integer between 3 and 25.")
    if not isinstance(maxiter, (int, np.integer)) or maxiter < 1:
        raise ValueError("`maxiter` must be a positive integer.")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("`tolerance` must be a positive finite scalar.")
    (frame, y, groups, unique_groups, group_index, X, Z, mean_terms, scale_terms, encoder) = _prepare_fit_data(
        data, outcome_col, group_col, mean_cols, scale_cols, standardize_numeric=standardize_numeric
    )
    x1, x2, logw = _quadrature_nodes(int(quadrature_points))
    theta0 = _initial_theta(y, X, Z)
    p, q = X.shape[1], Z.shape[1]
    bounds = [(None, None)] * (p + q) + [(-9.0, 5.0), (-9.0, 3.0), (-3.5, 3.5)]

    def objective(theta):
        ll = _marginal_loglik(theta, y, X, Z, group_index, len(unique_groups), x1, x2, logw)
        return 1e100 if not np.isfinite(ll) else -ll

    opt = minimize(
        objective,
        theta0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": int(maxiter), "ftol": float(tolerance), "gtol": float(tolerance)},
    )
    if require_convergence and not bool(opt.success):
        raise RuntimeError(f"Hierarchical location-scale optimization did not converge: {opt.message}")
    theta = np.asarray(opt.x, dtype=float)
    beta, gamma, tau_loc, tau_scale, rho = _decode_theta(theta, p, q)
    ll = -float(opt.fun)
    re = _estimate_random_effects(theta, y, X, Z, group_index, unique_groups, x1, x2, logw)
    selected = frame.loc[:, list(dict.fromkeys([outcome_col, group_col, *mean_cols, *scale_cols]))].copy()
    selected[group_col] = selected[group_col].astype(str)
    group_sizes = pd.Series(groups).value_counts()
    warnings = [
        "Gaussian conditional outcome model with random intercepts only.",
        "The log-scale equation models residual heterogeneity; it is not an artifact-correction or sensor-validity model.",
        "Random-effect estimates are empirical-Bayes summaries conditional on the fitted model.",
        "Predictions for unseen groups are population-level unless external random effects are supplied.",
    ]
    metadata = {
        "model_version": _MODEL_VERSION,
        "outcome_col": str(outcome_col),
        "group_col": str(group_col),
        "mean_cols": tuple(mean_cols),
        "scale_cols": tuple(scale_cols),
        "n_obs": int(len(y)),
        "n_groups": int(len(unique_groups)),
        "min_group_size": int(group_sizes.min()),
        "max_group_size": int(group_sizes.max()),
        "quadrature_points": int(quadrature_points),
        "quadrature_scheme": "two-dimensional adaptive Gauss-Hermite",
        "standardize_numeric": bool(standardize_numeric),
        "require_convergence": bool(require_convergence),
        "data_sha256": _canonical_frame_hash(selected),
        "claim_boundaries": tuple(warnings),
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
    return GazepointHierarchicalLocationScaleResult(
        mean_coef=tuple(float(x) for x in beta),
        scale_coef=tuple(float(x) for x in gamma),
        mean_terms=tuple(mean_terms),
        scale_terms=tuple(scale_terms),
        tau_location=float(tau_loc),
        tau_log_scale=float(tau_scale),
        rho=float(rho),
        log_likelihood=ll,
        random_effects=re,
        metadata=metadata,
        diagnostics=diagnostics,
        encoder=encoder_payload,
        parameter_vector=theta,
    )


def _prediction_design(result, data: pd.DataFrame):
    if not isinstance(result, GazepointHierarchicalLocationScaleResult):
        raise TypeError("`result` must be returned by fit_gazepoint_hierarchical_location_scale().")
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    mean_cols = list(result.encoder["mean_cols"])
    scale_cols = list(result.encoder["scale_cols"])
    X, mt = _apply_encoder(data, mean_cols, result.encoder["mean_spec"], allow_unknown=False)
    Z, st = _apply_encoder(data, scale_cols, result.encoder["scale_spec"], allow_unknown=False)
    if mt != result.mean_terms or st != result.scale_terms:
        raise ValueError("Prediction design does not match fitted design terms.")
    return X, Z


def predict_gazepoint_hierarchical_location_scale(
    result: GazepointHierarchicalLocationScaleResult,
    data: pd.DataFrame,
    *,
    group_col: str | None = None,
    include_random_effects: bool = True,
) -> pd.DataFrame:
    X, Z = _prediction_design(result, data)
    beta = np.asarray(result.mean_coef, dtype=float)
    gamma = np.asarray(result.scale_coef, dtype=float)
    loc_re = np.zeros(len(data), dtype=float)
    scale_re = np.zeros(len(data), dtype=float)
    source = np.full(len(data), "population", dtype=object)
    use_group = result.metadata["group_col"] if group_col is None else group_col
    if include_random_effects:
        if use_group not in data:
            raise ValueError(f"Missing group column `{use_group}` for conditional prediction.")
        lookup = result.random_effects.set_index("group")
        labels = data[use_group].astype(str).to_numpy()
        for i, label in enumerate(labels):
            if label in lookup.index:
                loc_re[i] = float(lookup.loc[label, "location_re"])
                scale_re[i] = float(lookup.loc[label, "log_scale_re"])
                source[i] = "empirical_bayes"
            else:
                source[i] = "population_unseen_group"
    mean = X @ beta + loc_re
    log_scale = np.clip(Z @ gamma + scale_re, -20.0, 20.0)
    return pd.DataFrame({
        "predicted_mean": mean,
        "predicted_scale": np.exp(log_scale),
        "predicted_log_scale": log_scale,
        "random_effect_source": source,
    }, index=data.index)


def summarize_gazepoint_hierarchical_location_scale(result: GazepointHierarchicalLocationScaleResult) -> dict:
    if not isinstance(result, GazepointHierarchicalLocationScaleResult):
        raise TypeError("`result` must be returned by fit_gazepoint_hierarchical_location_scale().")
    mean = pd.DataFrame({"term": result.mean_terms, "estimate": result.mean_coef, "equation": "location"})
    scale = pd.DataFrame({"term": result.scale_terms, "estimate": result.scale_coef, "equation": "log_scale"})
    return {
        "fixed_effects": pd.concat([mean, scale], ignore_index=True),
        "random_effect_parameters": pd.DataFrame([{
            "tau_location": result.tau_location,
            "tau_log_scale": result.tau_log_scale,
            "rho": result.rho,
        }]),
        "random_effects": result.random_effects.copy(deep=True),
        "diagnostics": dict(result.diagnostics),
        "metadata": dict(result.metadata),
        "class": "gazepoint_hierarchical_location_scale_summary",
    }


def create_gazepoint_hierarchical_location_scale_certificate(result: GazepointHierarchicalLocationScaleResult) -> dict:
    if not isinstance(result, GazepointHierarchicalLocationScaleResult):
        raise TypeError("`result` must be returned by fit_gazepoint_hierarchical_location_scale().")
    if not bool(result.diagnostics.get("converged", False)):
        raise ValueError("Cannot create a reproducibility certificate from a non-converged fit.")
    payload = {
        "model_version": result.metadata["model_version"],
        "data_sha256": result.metadata["data_sha256"],
        "mean_terms": list(result.mean_terms),
        "scale_terms": list(result.scale_terms),
        "mean_coef": list(result.mean_coef),
        "scale_coef": list(result.scale_coef),
        "tau_location": result.tau_location,
        "tau_log_scale": result.tau_log_scale,
        "rho": result.rho,
        "quadrature_points": result.metadata["quadrature_points"],
        "converged": True,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"payload": payload, "sha256": sha256(canonical.encode("utf-8")).hexdigest()}


def validate_gazepoint_hierarchical_location_scale_certificate(result, certificate) -> bool:
    if not isinstance(certificate, Mapping) or "payload" not in certificate or "sha256" not in certificate:
        return False
    try:
        expected = create_gazepoint_hierarchical_location_scale_certificate(result)
        supplied_payload = dict(certificate["payload"])
        canonical = json.dumps(supplied_payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        return False
    supplied_digest = sha256(canonical.encode("utf-8")).hexdigest()
    return supplied_digest == certificate["sha256"] and supplied_payload == expected["payload"]


def simulate_gazepoint_hierarchical_location_scale(
    n_groups: int = 24,
    observations_per_group: int = 10,
    *,
    beta: Sequence[float] = (0.0, 0.6),
    gamma: Sequence[float] = (-0.2, 0.25),
    tau_location: float = 0.5,
    tau_log_scale: float = 0.25,
    rho: float = 0.2,
    seed: int | None = None,
) -> pd.DataFrame:
    if n_groups < 3 or observations_per_group < 2:
        raise ValueError("Need at least three groups and two observations per group.")
    beta = np.asarray(beta, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    if beta.shape != (2,) or gamma.shape != (2,):
        raise ValueError("`beta` and `gamma` must each contain intercept and one predictor coefficient.")
    if tau_location < 0 or tau_log_scale < 0 or not (-0.99 < rho < 0.99):
        raise ValueError("Invalid random-effect distribution parameters.")
    rng = np.random.default_rng(seed)
    cov = np.array([
        [tau_location ** 2, rho * tau_location * tau_log_scale],
        [rho * tau_location * tau_log_scale, tau_log_scale ** 2],
    ])
    effects = rng.multivariate_normal(np.zeros(2), cov, size=n_groups)
    rows = []
    for g in range(n_groups):
        x = rng.normal(size=observations_per_group)
        mu = beta[0] + beta[1] * x + effects[g, 0]
        log_sigma = gamma[0] + gamma[1] * x + effects[g, 1]
        y = rng.normal(mu, np.exp(log_sigma))
        for j in range(observations_per_group):
            rows.append({"participant": f"P{g + 1:03d}", "x": float(x[j]), "outcome": float(y[j])})
    out = pd.DataFrame(rows)
    out.attrs["known_truth"] = {
        "beta": tuple(float(v) for v in beta),
        "gamma": tuple(float(v) for v in gamma),
        "tau_location": float(tau_location),
        "tau_log_scale": float(tau_log_scale),
        "rho": float(rho),
        "seed": seed,
    }
    return out