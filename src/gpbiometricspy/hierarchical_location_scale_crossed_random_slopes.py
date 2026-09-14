from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence
import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .hierarchical_location_scale import (
    _apply_encoder,
    _canonical_frame_hash,
    _freeze_mapping,
    _normalise_predictor_list,
    _readonly,
)
from .hierarchical_location_scale_crossed import (
    _positive_definite_system,
    _prepare_fit_data as _prepare_crossed_fit_data,
)

_LOG_2PI = float(np.log(2.0 * np.pi))
_MODEL_VERSION = "gaussian-crossed-hierarchical-location-scale-random-slopes-v1"


@dataclass(frozen=True)
class GazepointCrossedHierarchicalLocationScaleRandomSlopesResult:
    mean_coef: tuple[float, ...]
    scale_coef: tuple[float, ...]
    mean_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    participant_random_slope_col: str
    item_random_slope_col: str
    participant_tau_location_intercept: float
    participant_tau_location_slope: float
    participant_tau_log_scale: float
    participant_rho_intercept_slope: float
    participant_rho_intercept_log_scale: float
    participant_rho_slope_log_scale: float
    item_tau_location_intercept: float
    item_tau_location_slope: float
    item_tau_log_scale: float
    item_rho_intercept_slope: float
    item_rho_intercept_log_scale: float
    item_rho_slope_log_scale: float
    participant_covariance: np.ndarray
    item_covariance: np.ndarray
    log_likelihood: float
    participant_random_effects: pd.DataFrame
    item_random_effects: pd.DataFrame
    metadata: Mapping
    diagnostics: Mapping
    encoder: Mapping
    parameter_vector: np.ndarray
    model_class: str = "gazepoint_crossed_hierarchical_location_scale_random_slopes"

    def __post_init__(self):
        object.__setattr__(self, "participant_covariance", _readonly(self.participant_covariance))
        object.__setattr__(self, "item_covariance", _readonly(self.item_covariance))
        object.__setattr__(self, "parameter_vector", _readonly(self.parameter_vector))
        object.__setattr__(
            self,
            "participant_random_effects",
            self.participant_random_effects.copy(deep=True),
        )
        object.__setattr__(self, "item_random_effects", self.item_random_effects.copy(deep=True))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        object.__setattr__(self, "diagnostics", _freeze_mapping(self.diagnostics))
        object.__setattr__(self, "encoder", _freeze_mapping(self.encoder))


def _covariance_from_cholesky_params(params: np.ndarray):
    params = np.asarray(params, dtype=float)
    if params.shape != (6,) or not np.isfinite(params).all():
        raise ValueError("Random-effect covariance parameters must contain six finite values.")
    log_d0, log_d1, log_d2, l10, l20, l21 = params
    L = np.array(
        [
            [np.exp(np.clip(log_d0, -20.0, 20.0)), 0.0, 0.0],
            [l10, np.exp(np.clip(log_d1, -20.0, 20.0)), 0.0],
            [l20, l21, np.exp(np.clip(log_d2, -20.0, 20.0))],
        ],
        dtype=float,
    )
    covariance = L @ L.T
    sign, logdet = np.linalg.slogdet(covariance)
    if sign <= 0 or not np.isfinite(logdet):
        raise np.linalg.LinAlgError("Random-effect covariance is not positive definite.")
    covariance_inv = np.linalg.inv(covariance)
    sds = np.sqrt(np.diag(covariance))
    correlation = covariance / np.outer(sds, sds)
    return covariance, covariance_inv, float(logdet), sds, correlation


def _decode_theta(theta: np.ndarray, p: int, q: int):
    theta = np.asarray(theta, dtype=float)
    if theta.shape != (p + q + 12,) or not np.isfinite(theta).all():
        raise ValueError("Parameter vector has invalid size or contains non-finite values.")
    beta = theta[:p]
    gamma = theta[p : p + q]
    participant = _covariance_from_cholesky_params(theta[p + q : p + q + 6])
    item = _covariance_from_cholesky_params(theta[p + q + 6 : p + q + 12])
    return beta, gamma, participant, item


def _slope_values(
    frame: pd.DataFrame,
    labels: np.ndarray,
    slope_col: str,
    mean_cols: list[str],
    encoder: Mapping,
    *,
    role_name: str,
) -> np.ndarray:
    if slope_col not in mean_cols:
        raise ValueError(f"`{role_name}_random_slope_col` must also be included in `mean_cols` as a fixed effect.")
    cfg = encoder["mean_spec"][slope_col]
    if cfg["kind"] != "numeric":
        raise ValueError(f"`{role_name}_random_slope_col` must be numeric.")
    raw = pd.to_numeric(frame[slope_col], errors="coerce").to_numpy(float)
    scale = float(cfg["scale"])
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(f"`{role_name}_random_slope_col` has an invalid fitted scaling factor.")
    values = (raw - float(cfg["center"])) / scale
    if not np.isfinite(values).all() or float(np.ptp(values)) <= 0:
        raise ValueError(f"`{role_name}_random_slope_col` must contain finite within-sample variation.")
    if len(np.unique(labels)) < 6:
        raise ValueError(
            f"Crossed random-slope covariance estimation requires at least six {role_name} levels."
        )
    nonvarying = [
        str(label)
        for label in np.unique(labels)
        if np.unique(values[labels == label]).size < 2
    ]
    if nonvarying:
        preview = ", ".join(nonvarying[:5])
        raise ValueError(
            f"`{role_name}_random_slope_col` must vary within every {role_name}; "
            f"non-varying levels: {preview}"
        )
    return values


def _prepare_fit_data(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    mean_cols: list[str],
    scale_cols: list[str],
    participant_random_slope_col: str,
    item_random_slope_col: str,
    *,
    standardize_numeric: bool,
):
    prepared = _prepare_crossed_fit_data(
        data,
        outcome_col,
        participant_col,
        item_col,
        mean_cols,
        scale_cols,
        standardize_numeric=standardize_numeric,
    )
    (
        frame,
        y,
        participant_levels,
        participant_index,
        item_levels,
        item_index,
        X,
        Z,
        mean_terms,
        scale_terms,
        encoder,
    ) = prepared
    participant_labels = frame[participant_col].astype(str).to_numpy()
    item_labels = frame[item_col].astype(str).to_numpy()
    participant_slope = _slope_values(
        frame,
        participant_labels,
        str(participant_random_slope_col),
        mean_cols,
        encoder,
        role_name="participant",
    )
    item_slope = _slope_values(
        frame,
        item_labels,
        str(item_random_slope_col),
        mean_cols,
        encoder,
        role_name="item",
    )
    return (*prepared, participant_slope, item_slope)


def _latent_indices(
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
):
    participant_location = 3 * participant_index
    participant_slope = participant_location + 1
    participant_scale = participant_location + 2
    item_base = 3 * n_participants
    item_location = item_base + 3 * item_index
    item_slope = item_location + 1
    item_scale = item_location + 2
    return tuple(
        np.asarray(values, dtype=int)
        for values in (
            participant_location,
            participant_slope,
            participant_scale,
            item_location,
            item_slope,
            item_scale,
        )
    )


def _joint_logposterior_grad_hess(
    b: np.ndarray,
    y: np.ndarray,
    xb: np.ndarray,
    zg: np.ndarray,
    participant_slope_values: np.ndarray,
    item_slope_values: np.ndarray,
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
    n_items: int,
    participant_cov_inv: np.ndarray,
    participant_logdet: float,
    item_cov_inv: np.ndarray,
    item_logdet: float,
):
    b = np.asarray(b, dtype=float)
    latent_dimension = 3 * (n_participants + n_items)
    if b.shape != (latent_dimension,):
        raise ValueError("Latent vector has the wrong dimension.")
    if not (
        len(y)
        == len(xb)
        == len(zg)
        == len(participant_slope_values)
        == len(item_slope_values)
        == len(participant_index)
        == len(item_index)
    ):
        raise ValueError("Observation-level inputs must have the same length.")
    (
        participant_location,
        participant_slope,
        participant_scale,
        item_location,
        item_slope,
        item_scale,
    ) = _latent_indices(participant_index, item_index, n_participants)
    mean_shift = (
        b[participant_location]
        + b[participant_slope] * participant_slope_values
        + b[item_location]
        + b[item_slope] * item_slope_values
    )
    scale_shift = b[participant_scale] + b[item_scale]
    eta = np.clip(zg + scale_shift, -20.0, 20.0)
    inv_var = np.exp(-2.0 * eta)
    residual = y - xb - mean_shift
    loglik = float(
        np.sum(-0.5 * _LOG_2PI - eta - 0.5 * residual * residual * inv_var)
    )
    gradient = np.zeros(latent_dimension, dtype=float)
    hessian = np.zeros((latent_dimension, latent_dimension), dtype=float)
    grad_location = residual * inv_var
    grad_scale = -1.0 + residual * residual * inv_var
    hess_location = -inv_var
    hess_location_scale = -2.0 * residual * inv_var
    hess_scale = -2.0 * residual * residual * inv_var

    np.add.at(gradient, participant_location, grad_location)
    np.add.at(gradient, participant_slope, participant_slope_values * grad_location)
    np.add.at(gradient, item_location, grad_location)
    np.add.at(gradient, item_slope, item_slope_values * grad_location)
    np.add.at(gradient, participant_scale, grad_scale)
    np.add.at(gradient, item_scale, grad_scale)

    for (
        participant_loc,
        participant_slp,
        participant_scl,
        item_loc,
        item_slp,
        item_scl,
        participant_r,
        item_r,
        h_ll,
        h_ls,
        h_ss,
    ) in zip(
        participant_location,
        participant_slope,
        participant_scale,
        item_location,
        item_slope,
        item_scale,
        participant_slope_values,
        item_slope_values,
        hess_location,
        hess_location_scale,
        hess_scale,
        strict=True,
    ):
        location_indices = (
            int(participant_loc),
            int(participant_slp),
            int(item_loc),
            int(item_slp),
        )
        location_coefficients = (1.0, float(participant_r), 1.0, float(item_r))
        scale_indices = (int(participant_scl), int(item_scl))
        for row, row_coefficient in zip(location_indices, location_coefficients, strict=True):
            for col, col_coefficient in zip(location_indices, location_coefficients, strict=True):
                hessian[row, col] += h_ll * row_coefficient * col_coefficient
        for row, row_coefficient in zip(location_indices, location_coefficients, strict=True):
            for col in scale_indices:
                value = h_ls * row_coefficient
                hessian[row, col] += value
                hessian[col, row] += value
        for row in scale_indices:
            for col in scale_indices:
                hessian[row, col] += h_ss

    prior = 0.0
    for participant in range(n_participants):
        indices = np.array([3 * participant, 3 * participant + 1, 3 * participant + 2])
        effects = b[indices]
        prior += (
            -1.5 * _LOG_2PI
            - 0.5 * participant_logdet
            - 0.5 * float(effects @ participant_cov_inv @ effects)
        )
        gradient[indices] -= participant_cov_inv @ effects
        hessian[np.ix_(indices, indices)] -= participant_cov_inv

    item_base = 3 * n_participants
    for item in range(n_items):
        indices = np.array(
            [item_base + 3 * item, item_base + 3 * item + 1, item_base + 3 * item + 2]
        )
        effects = b[indices]
        prior += (
            -1.5 * _LOG_2PI
            - 0.5 * item_logdet
            - 0.5 * float(effects @ item_cov_inv @ effects)
        )
        gradient[indices] -= item_cov_inv @ effects
        hessian[np.ix_(indices, indices)] -= item_cov_inv
    return float(loglik + prior), gradient, hessian


def _posterior_mode(
    y: np.ndarray,
    xb: np.ndarray,
    zg: np.ndarray,
    participant_slope_values: np.ndarray,
    item_slope_values: np.ndarray,
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
    n_items: int,
    participant_cov_inv: np.ndarray,
    participant_logdet: float,
    item_cov_inv: np.ndarray,
    item_logdet: float,
    *,
    max_steps: int,
    tol: float,
):
    latent_dimension = 3 * (n_participants + n_items)
    b = np.zeros(latent_dimension, dtype=float)
    value, gradient, hessian = _joint_logposterior_grad_hess(
        b,
        y,
        xb,
        zg,
        participant_slope_values,
        item_slope_values,
        participant_index,
        item_index,
        n_participants,
        n_items,
        participant_cov_inv,
        participant_logdet,
        item_cov_inv,
        item_logdet,
    )
    converged = False
    iterations = 0
    for iterations in range(1, max_steps + 1):
        if float(np.max(np.abs(gradient))) <= tol:
            converged = True
            break
        try:
            system, _, _ = _positive_definite_system(-hessian)
            direction = np.linalg.solve(system, gradient)
        except np.linalg.LinAlgError:
            break
        if not np.isfinite(direction).all():
            break
        alpha = 1.0
        accepted = False
        while alpha >= 1.0 / 256.0:
            candidate = b + alpha * direction
            new_value, new_gradient, new_hessian = _joint_logposterior_grad_hess(
                candidate,
                y,
                xb,
                zg,
                participant_slope_values,
                item_slope_values,
                participant_index,
                item_index,
                n_participants,
                n_items,
                participant_cov_inv,
                participant_logdet,
                item_cov_inv,
                item_logdet,
            )
            if np.isfinite(new_value) and new_value >= value + 1e-12:
                b = candidate
                value = new_value
                gradient = new_gradient
                hessian = new_hessian
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            if float(np.max(np.abs(gradient))) <= max(10.0 * tol, 1e-5):
                converged = True
            break
    max_abs_gradient = float(np.max(np.abs(gradient)))
    if max_abs_gradient <= tol:
        converged = True
    negative_hessian, chol, jitter = _positive_definite_system(-hessian)
    logdet = float(2.0 * np.sum(np.log(np.diag(chol))))
    diagnostics = {
        "converged": bool(converged),
        "iterations": int(iterations),
        "max_abs_gradient": max_abs_gradient,
        "hessian_jitter": float(jitter),
        "logdet_negative_hessian": logdet,
    }
    return b, negative_hessian, float(value), diagnostics


def _laplace_loglik(
    theta: np.ndarray,
    y: np.ndarray,
    X: np.ndarray,
    Z: np.ndarray,
    participant_slope_values: np.ndarray,
    item_slope_values: np.ndarray,
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
    n_items: int,
    *,
    mode_max_steps: int,
    mode_tol: float,
    return_state: bool = False,
):
    p, q = X.shape[1], Z.shape[1]
    try:
        beta, gamma, participant, item = _decode_theta(theta, p, q)
        _, participant_cov_inv, participant_logdet, *_ = participant
        _, item_cov_inv, item_logdet, *_ = item
        mode, negative_hessian, posterior_value, mode_diagnostics = _posterior_mode(
            y,
            X @ beta,
            Z @ gamma,
            participant_slope_values,
            item_slope_values,
            participant_index,
            item_index,
            n_participants,
            n_items,
            participant_cov_inv,
            participant_logdet,
            item_cov_inv,
            item_logdet,
            max_steps=mode_max_steps,
            tol=mode_tol,
        )
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        return (-np.inf, None) if return_state else -np.inf
    if not mode_diagnostics["converged"] or mode_diagnostics["hessian_jitter"] > 1e-5:
        return (-np.inf, None) if return_state else -np.inf
    latent_dimension = mode.size
    value = float(
        posterior_value
        + 0.5 * latent_dimension * _LOG_2PI
        - 0.5 * mode_diagnostics["logdet_negative_hessian"]
    )
    if not np.isfinite(value):
        return (-np.inf, None) if return_state else -np.inf
    state = (mode, negative_hessian, mode_diagnostics, participant, item)
    return (value, state) if return_state else value


def _initial_theta(y: np.ndarray, X: np.ndarray, Z: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residual = y - X @ beta
    ddof = min(max(X.shape[1], 1), max(len(y) - 1, 1))
    residual_sd = float(np.std(residual, ddof=ddof))
    if not np.isfinite(residual_sd) or residual_sd <= 1e-6:
        residual_sd = max(float(np.std(y)), 1.0)
    gamma = np.zeros(Z.shape[1], dtype=float)
    gamma[0] = np.log(max(residual_sd, 1e-4))

    def covariance_start(location_fraction: float, slope_fraction: float, scale_sd: float):
        return [
            np.log(max(residual_sd * location_fraction, 1e-3)),
            np.log(max(residual_sd * slope_fraction, 1e-3)),
            np.log(scale_sd),
            0.0,
            0.0,
            0.0,
        ]

    return np.r_[
        beta,
        gamma,
        covariance_start(0.30, 0.15, 0.12),
        covariance_start(0.20, 0.10, 0.08),
    ]


def _parameter_bounds(p: int, q: int):
    covariance_bounds = [
        (-8.0, 4.0),
        (-8.0, 4.0),
        (-8.0, 2.0),
        (-4.0, 4.0),
        (-4.0, 4.0),
        (-4.0, 4.0),
    ]
    return [*[(None, None)] * (p + q), *covariance_bounds, *covariance_bounds]


def _random_effect_tables(
    mode: np.ndarray,
    negative_hessian: np.ndarray,
    participant_levels: np.ndarray,
    item_levels: np.ndarray,
):
    try:
        posterior_covariance = np.linalg.inv(negative_hessian)
    except np.linalg.LinAlgError:
        posterior_covariance = np.linalg.pinv(negative_hessian)
    posterior_sd = np.sqrt(np.maximum(np.diag(posterior_covariance), 0.0))

    participant_rows = []
    for index, label in enumerate(participant_levels):
        location = 3 * index
        slope = location + 1
        scale = location + 2
        participant_rows.append(
            {
                "participant": str(label),
                "location_intercept_mode": float(mode[location]),
                "location_slope_mode": float(mode[slope]),
                "log_scale_intercept_mode": float(mode[scale]),
                "location_intercept_sd": float(posterior_sd[location]),
                "location_slope_sd": float(posterior_sd[slope]),
                "log_scale_intercept_sd": float(posterior_sd[scale]),
                "intercept_slope_cov": float(posterior_covariance[location, slope]),
                "intercept_log_scale_cov": float(posterior_covariance[location, scale]),
                "slope_log_scale_cov": float(posterior_covariance[slope, scale]),
            }
        )

    item_base = 3 * len(participant_levels)
    item_rows = []
    for index, label in enumerate(item_levels):
        location = item_base + 3 * index
        slope = location + 1
        scale = location + 2
        item_rows.append(
            {
                "item": str(label),
                "location_intercept_mode": float(mode[location]),
                "location_slope_mode": float(mode[slope]),
                "log_scale_intercept_mode": float(mode[scale]),
                "location_intercept_sd": float(posterior_sd[location]),
                "location_slope_sd": float(posterior_sd[slope]),
                "log_scale_intercept_sd": float(posterior_sd[scale]),
                "intercept_slope_cov": float(posterior_covariance[location, slope]),
                "intercept_log_scale_cov": float(posterior_covariance[location, scale]),
                "slope_log_scale_cov": float(posterior_covariance[slope, scale]),
            }
        )
    return pd.DataFrame(participant_rows), pd.DataFrame(item_rows)


def fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    *,
    participant_random_slope_col: str,
    item_random_slope_col: str,
    mean_cols: Sequence[str] | str | None = None,
    scale_cols: Sequence[str] | str | None = None,
    standardize_numeric: bool = True,
    maxiter: int = 160,
    mode_max_steps: int = 50,
    mode_tol: float = 1e-6,
    max_latent_dimension: int = 450,
) -> GazepointCrossedHierarchicalLocationScaleRandomSlopesResult:
    """Fit crossed participant-item Gaussian location-scale random slopes.

    The participant and item factors each receive a location intercept, one
    location slope, and a log-scale intercept. Random slopes represent
    association heterogeneity only; they are not causal effects or sensor
    validity scores.
    """
    mean_cols = _normalise_predictor_list(mean_cols)
    scale_cols = _normalise_predictor_list(scale_cols)
    if not isinstance(participant_random_slope_col, str) or not participant_random_slope_col.strip():
        raise ValueError("`participant_random_slope_col` must be a non-empty column name.")
    if not isinstance(item_random_slope_col, str) or not item_random_slope_col.strip():
        raise ValueError("`item_random_slope_col` must be a non-empty column name.")
    participant_random_slope_col = participant_random_slope_col.strip()
    item_random_slope_col = item_random_slope_col.strip()
    if not isinstance(maxiter, int) or isinstance(maxiter, bool) or maxiter < 1:
        raise ValueError("`maxiter` must be a positive integer.")
    if not isinstance(mode_max_steps, int) or isinstance(mode_max_steps, bool) or mode_max_steps < 1:
        raise ValueError("`mode_max_steps` must be a positive integer.")
    if not np.isfinite(mode_tol) or mode_tol <= 0:
        raise ValueError("`mode_tol` must be a positive finite number.")
    if not isinstance(max_latent_dimension, int) or isinstance(max_latent_dimension, bool) or max_latent_dimension < 36:
        raise ValueError("`max_latent_dimension` must be an integer of at least 36.")

    (
        frame,
        y,
        participant_levels,
        participant_index,
        item_levels,
        item_index,
        X,
        Z,
        mean_terms,
        scale_terms,
        encoder,
        participant_slope_values,
        item_slope_values,
    ) = _prepare_fit_data(
        data,
        outcome_col,
        participant_col,
        item_col,
        mean_cols,
        scale_cols,
        participant_random_slope_col,
        item_random_slope_col,
        standardize_numeric=bool(standardize_numeric),
    )
    latent_dimension = 3 * (len(participant_levels) + len(item_levels))
    if latent_dimension > max_latent_dimension:
        raise ValueError(
            f"Crossed random-slope latent dimension {latent_dimension} exceeds "
            f"`max_latent_dimension` ({max_latent_dimension}); increase the limit only "
            "after considering dense Laplace cost."
        )
    theta0 = _initial_theta(y, X, Z)

    def objective(theta):
        value = _laplace_loglik(
            theta,
            y,
            X,
            Z,
            participant_slope_values,
            item_slope_values,
            participant_index,
            item_index,
            len(participant_levels),
            len(item_levels),
            mode_max_steps=mode_max_steps,
            mode_tol=mode_tol,
        )
        return 1e30 if not np.isfinite(value) else -float(value)

    optimization = minimize(
        objective,
        theta0,
        method="L-BFGS-B",
        bounds=_parameter_bounds(X.shape[1], Z.shape[1]),
        options={"maxiter": maxiter, "ftol": 1e-9, "gtol": 1e-6, "maxls": 30},
    )
    log_likelihood, state = _laplace_loglik(
        optimization.x,
        y,
        X,
        Z,
        participant_slope_values,
        item_slope_values,
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
        mode_max_steps=mode_max_steps,
        mode_tol=mode_tol,
        return_state=True,
    )
    if state is None or not np.isfinite(log_likelihood):
        raise RuntimeError("Optimizer did not produce a finite converged Laplace solution.")
    mode, negative_hessian, mode_diagnostics, participant, item = state
    beta, gamma, participant_check, item_check = _decode_theta(
        optimization.x, X.shape[1], Z.shape[1]
    )
    if not (
        np.allclose(participant[0], participant_check[0])
        and np.allclose(item[0], item_check[0])
    ):
        raise RuntimeError("Internal covariance decoding mismatch.")

    participant_effects, item_effects = _random_effect_tables(
        mode,
        negative_hessian,
        participant_levels,
        item_levels,
    )
    participant_covariance, _, _, participant_sds, participant_corr = participant
    item_covariance, _, _, item_sds, item_corr = item
    converged = bool(optimization.success and mode_diagnostics["converged"])

    metadata = {
        "model_version": _MODEL_VERSION,
        "outcome_col": str(outcome_col),
        "participant_col": str(participant_col),
        "item_col": str(item_col),
        "participant_random_slope_col": participant_random_slope_col,
        "item_random_slope_col": item_random_slope_col,
        "n_rows": int(len(frame)),
        "n_participants": int(len(participant_levels)),
        "n_items": int(len(item_levels)),
        "latent_dimension": int(latent_dimension),
        "training_sha256": _canonical_frame_hash(frame),
        "approximation": "joint Laplace approximation over crossed participant/item random intercepts and location slopes",
        "conditional_distribution": "Gaussian",
        "random_effect_structure": (
            "independent participant and item trivariate blocks: location intercept, "
            "location slope, log-scale intercept"
        ),
        "scientific_boundary": (
            "crossed random slopes model association heterogeneity; they do not identify "
            "causal effects, artifacts, latent psychological states, or sensor validity"
        ),
    }
    diagnostics = {
        "converged": converged,
        "optimizer_success": bool(optimization.success),
        "optimizer_status": int(optimization.status),
        "optimizer_message": str(optimization.message),
        "optimizer_iterations": int(getattr(optimization, "nit", -1)),
        "optimizer_function_evaluations": int(getattr(optimization, "nfev", -1)),
        "posterior_mode_converged": bool(mode_diagnostics["converged"]),
        "posterior_mode_iterations": int(mode_diagnostics["iterations"]),
        "posterior_mode_max_abs_gradient": float(mode_diagnostics["max_abs_gradient"]),
        "posterior_hessian_jitter": float(mode_diagnostics["hessian_jitter"]),
        "logdet_negative_hessian": float(mode_diagnostics["logdet_negative_hessian"]),
        "incidence_connected": True,
        "laplace_dense_hessian": True,
        "max_latent_dimension": int(max_latent_dimension),
    }
    return GazepointCrossedHierarchicalLocationScaleRandomSlopesResult(
        mean_coef=tuple(float(value) for value in beta),
        scale_coef=tuple(float(value) for value in gamma),
        mean_terms=tuple(mean_terms),
        scale_terms=tuple(scale_terms),
        participant_random_slope_col=participant_random_slope_col,
        item_random_slope_col=item_random_slope_col,
        participant_tau_location_intercept=float(participant_sds[0]),
        participant_tau_location_slope=float(participant_sds[1]),
        participant_tau_log_scale=float(participant_sds[2]),
        participant_rho_intercept_slope=float(participant_corr[0, 1]),
        participant_rho_intercept_log_scale=float(participant_corr[0, 2]),
        participant_rho_slope_log_scale=float(participant_corr[1, 2]),
        item_tau_location_intercept=float(item_sds[0]),
        item_tau_location_slope=float(item_sds[1]),
        item_tau_log_scale=float(item_sds[2]),
        item_rho_intercept_slope=float(item_corr[0, 1]),
        item_rho_intercept_log_scale=float(item_corr[0, 2]),
        item_rho_slope_log_scale=float(item_corr[1, 2]),
        participant_covariance=participant_covariance,
        item_covariance=item_covariance,
        log_likelihood=float(log_likelihood),
        participant_random_effects=participant_effects,
        item_random_effects=item_effects,
        metadata=metadata,
        diagnostics=diagnostics,
        encoder=encoder,
        parameter_vector=np.asarray(optimization.x, dtype=float),
    )


def _prediction_slope_values(
    data: pd.DataFrame,
    slope_col: str,
    encoder: Mapping,
) -> np.ndarray:
    if slope_col not in data:
        raise ValueError(f"Missing required random-slope prediction column `{slope_col}`.")
    cfg = encoder["mean_spec"][slope_col]
    raw = pd.to_numeric(data[slope_col], errors="coerce").to_numpy(float)
    if not np.isfinite(raw).all():
        raise ValueError(f"Prediction random-slope column `{slope_col}` must be finite numeric.")
    return (raw - float(cfg["center"])) / float(cfg["scale"])


def predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
    result: GazepointCrossedHierarchicalLocationScaleRandomSlopesResult,
    new_data: pd.DataFrame,
    *,
    include_random_effects: bool = True,
    unknown_levels: str = "population",
) -> pd.DataFrame:
    if not isinstance(result, GazepointCrossedHierarchicalLocationScaleRandomSlopesResult):
        raise TypeError(
            "`result` must be a GazepointCrossedHierarchicalLocationScaleRandomSlopesResult."
        )
    if not isinstance(new_data, pd.DataFrame):
        raise TypeError("`new_data` must be a pandas DataFrame.")
    if unknown_levels not in {"population", "error"}:
        raise ValueError("`unknown_levels` must be 'population' or 'error'.")
    participant_col = str(result.metadata["participant_col"])
    item_col = str(result.metadata["item_col"])
    required = [
        participant_col,
        item_col,
        *result.encoder["mean_cols"],
        *result.encoder["scale_cols"],
    ]
    missing = [col for col in dict.fromkeys(required) if col not in new_data]
    if missing:
        raise ValueError("Missing required prediction column(s): " + ", ".join(missing))
    if new_data[participant_col].isna().any() or new_data[item_col].isna().any():
        raise ValueError("Participant and item identifiers must be non-missing for prediction.")

    X, mean_terms = _apply_encoder(
        new_data,
        list(result.encoder["mean_cols"]),
        result.encoder["mean_spec"],
        allow_unknown=False,
    )
    Z, scale_terms = _apply_encoder(
        new_data,
        list(result.encoder["scale_cols"]),
        result.encoder["scale_spec"],
        allow_unknown=False,
    )
    if tuple(mean_terms) != result.mean_terms or tuple(scale_terms) != result.scale_terms:
        raise RuntimeError("Prediction design encoding does not match the fitted model.")

    participant_slope_values = _prediction_slope_values(
        new_data,
        result.participant_random_slope_col,
        result.encoder,
    )
    item_slope_values = _prediction_slope_values(
        new_data,
        result.item_random_slope_col,
        result.encoder,
    )
    predicted_mean = X @ np.asarray(result.mean_coef, dtype=float)
    predicted_log_scale = Z @ np.asarray(result.scale_coef, dtype=float)

    participant_lookup = result.participant_random_effects.set_index("participant")
    item_lookup = result.item_random_effects.set_index("item")
    participant_seen = []
    item_seen = []
    levels = []
    for row_index, (participant, item) in enumerate(
        zip(
            new_data[participant_col].astype(str),
            new_data[item_col].astype(str),
            strict=True,
        )
    ):
        seen_participant = participant in participant_lookup.index
        seen_item = item in item_lookup.index
        participant_seen.append(seen_participant)
        item_seen.append(seen_item)
        if unknown_levels == "error" and (not seen_participant or not seen_item):
            raise ValueError(
                "Conditional prediction encountered an unseen participant or item while "
                "`unknown_levels='error'`."
            )
        if include_random_effects:
            if seen_participant:
                row = participant_lookup.loc[participant]
                predicted_mean[row_index] += float(row["location_intercept_mode"]) + float(
                    row["location_slope_mode"]
                ) * participant_slope_values[row_index]
                predicted_log_scale[row_index] += float(row["log_scale_intercept_mode"])
            if seen_item:
                row = item_lookup.loc[item]
                predicted_mean[row_index] += float(row["location_intercept_mode"]) + float(
                    row["location_slope_mode"]
                ) * item_slope_values[row_index]
                predicted_log_scale[row_index] += float(row["log_scale_intercept_mode"])
            if seen_participant and seen_item:
                levels.append("conditional_participant_item")
            elif seen_participant:
                levels.append("conditional_participant_population_item")
            elif seen_item:
                levels.append("population_participant_conditional_item")
            else:
                levels.append("population_participant_item")
        else:
            levels.append("population_fixed_effects")
    return pd.DataFrame(
        {
            "predicted_mean": predicted_mean,
            "predicted_log_scale": predicted_log_scale,
            "predicted_scale": np.exp(np.clip(predicted_log_scale, -20.0, 20.0)),
            "participant_seen": participant_seen,
            "item_seen": item_seen,
            "prediction_level": levels,
        },
        index=new_data.index,
    )


def _simulation_covariance(
    tau_location_intercept: float,
    tau_location_slope: float,
    tau_log_scale: float,
    rho_intercept_slope: float,
    rho_intercept_log_scale: float,
    rho_slope_log_scale: float,
) -> np.ndarray:
    sds = np.array(
        [tau_location_intercept, tau_location_slope, tau_log_scale],
        dtype=float,
    )
    correlations = np.array(
        [rho_intercept_slope, rho_intercept_log_scale, rho_slope_log_scale],
        dtype=float,
    )
    if not np.isfinite(np.r_[sds, correlations]).all():
        raise ValueError("Simulation covariance parameters must be finite.")
    if np.any(sds <= 0):
        raise ValueError("Simulation random-effect standard deviations must be positive.")
    if np.any(np.abs(correlations) >= 0.999):
        raise ValueError("Simulation random-effect correlations must lie strictly inside (-0.999, 0.999).")
    corr = np.array(
        [
            [1.0, correlations[0], correlations[1]],
            [correlations[0], 1.0, correlations[2]],
            [correlations[1], correlations[2], 1.0],
        ],
        dtype=float,
    )
    covariance = np.diag(sds) @ corr @ np.diag(sds)
    sign, _ = np.linalg.slogdet(covariance)
    if sign <= 0:
        raise ValueError("Simulation covariance must be positive definite.")
    return covariance


def simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(
    *,
    n_participants: int = 8,
    n_items: int = 8,
    repeats: int = 1,
    mean_intercept: float = 0.4,
    participant_mean_slope: float = 0.65,
    item_mean_slope: float = -0.35,
    log_scale_intercept: float = -0.2,
    log_scale_slope: float = 0.15,
    participant_tau_location_intercept: float = 0.50,
    participant_tau_location_slope: float = 0.24,
    participant_tau_log_scale: float = 0.18,
    participant_rho_intercept_slope: float = 0.20,
    participant_rho_intercept_log_scale: float = 0.15,
    participant_rho_slope_log_scale: float = -0.10,
    item_tau_location_intercept: float = 0.35,
    item_tau_location_slope: float = 0.18,
    item_tau_log_scale: float = 0.12,
    item_rho_intercept_slope: float = -0.15,
    item_rho_intercept_log_scale: float = -0.20,
    item_rho_slope_log_scale: float = 0.10,
    seed: int = 123,
) -> pd.DataFrame:
    if not isinstance(n_participants, int) or isinstance(n_participants, bool) or n_participants < 6:
        raise ValueError("`n_participants` must be an integer of at least six.")
    if not isinstance(n_items, int) or isinstance(n_items, bool) or n_items < 6:
        raise ValueError("`n_items` must be an integer of at least six.")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("`repeats` must be a positive integer.")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("`seed` must be a non-negative integer.")
    fixed = np.array(
        [
            mean_intercept,
            participant_mean_slope,
            item_mean_slope,
            log_scale_intercept,
            log_scale_slope,
        ],
        dtype=float,
    )
    if not np.isfinite(fixed).all():
        raise ValueError("Simulation fixed-effect parameters must be finite.")

    participant_covariance = _simulation_covariance(
        participant_tau_location_intercept,
        participant_tau_location_slope,
        participant_tau_log_scale,
        participant_rho_intercept_slope,
        participant_rho_intercept_log_scale,
        participant_rho_slope_log_scale,
    )
    item_covariance = _simulation_covariance(
        item_tau_location_intercept,
        item_tau_location_slope,
        item_tau_log_scale,
        item_rho_intercept_slope,
        item_rho_intercept_log_scale,
        item_rho_slope_log_scale,
    )

    rng = np.random.default_rng(seed)
    participant_index = np.repeat(np.arange(n_participants), n_items * repeats)
    item_index = np.tile(np.repeat(np.arange(n_items), repeats), n_participants)
    n_rows = len(participant_index)
    participant_slope_predictor = rng.normal(size=n_rows)
    item_slope_predictor = rng.normal(size=n_rows)
    scale_predictor = rng.normal(size=n_rows)
    participant_effects = rng.multivariate_normal(
        np.zeros(3),
        participant_covariance,
        size=n_participants,
    )
    item_effects = rng.multivariate_normal(
        np.zeros(3),
        item_covariance,
        size=n_items,
    )
    mean = (
        mean_intercept
        + participant_mean_slope * participant_slope_predictor
        + item_mean_slope * item_slope_predictor
        + participant_effects[participant_index, 0]
        + participant_effects[participant_index, 1] * participant_slope_predictor
        + item_effects[item_index, 0]
        + item_effects[item_index, 1] * item_slope_predictor
    )
    log_scale = (
        log_scale_intercept
        + log_scale_slope * scale_predictor
        + participant_effects[participant_index, 2]
        + item_effects[item_index, 2]
    )
    outcome = mean + np.exp(log_scale) * rng.normal(size=n_rows)
    frame = pd.DataFrame(
        {
            "outcome": outcome,
            "participant": [f"p{index:03d}" for index in participant_index],
            "item": [f"i{index:03d}" for index in item_index],
            "participant_slope_predictor": participant_slope_predictor,
            "item_slope_predictor": item_slope_predictor,
            "scale_predictor": scale_predictor,
        }
    )
    frame.attrs["truth"] = {
        "mean_coef": (
            float(mean_intercept),
            float(participant_mean_slope),
            float(item_mean_slope),
        ),
        "scale_coef": (float(log_scale_intercept), float(log_scale_slope)),
        "participant_covariance": participant_covariance.copy(),
        "item_covariance": item_covariance.copy(),
        "seed": int(seed),
    }
    return frame


def _certificate_payload(
    result: GazepointCrossedHierarchicalLocationScaleRandomSlopesResult,
) -> dict:
    return {
        "model_version": str(result.metadata["model_version"]),
        "model_class": result.model_class,
        "training_sha256": str(result.metadata["training_sha256"]),
        "outcome_col": str(result.metadata["outcome_col"]),
        "participant_col": str(result.metadata["participant_col"]),
        "item_col": str(result.metadata["item_col"]),
        "participant_random_slope_col": result.participant_random_slope_col,
        "item_random_slope_col": result.item_random_slope_col,
        "n_rows": int(result.metadata["n_rows"]),
        "n_participants": int(result.metadata["n_participants"]),
        "n_items": int(result.metadata["n_items"]),
        "latent_dimension": int(result.metadata["latent_dimension"]),
        "mean_terms": list(result.mean_terms),
        "scale_terms": list(result.scale_terms),
        "mean_coef": [float(value) for value in result.mean_coef],
        "scale_coef": [float(value) for value in result.scale_coef],
        "participant_covariance": result.participant_covariance.tolist(),
        "item_covariance": result.item_covariance.tolist(),
        "log_likelihood": float(result.log_likelihood),
        "participant_effects_sha256": _canonical_frame_hash(
            result.participant_random_effects
        ),
        "item_effects_sha256": _canonical_frame_hash(result.item_random_effects),
        "parameter_vector": result.parameter_vector.tolist(),
        "approximation": str(result.metadata["approximation"]),
    }


def create_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
    result: GazepointCrossedHierarchicalLocationScaleRandomSlopesResult,
) -> dict:
    if not isinstance(result, GazepointCrossedHierarchicalLocationScaleRandomSlopesResult):
        raise TypeError(
            "`result` must be a GazepointCrossedHierarchicalLocationScaleRandomSlopesResult."
        )
    if not bool(result.diagnostics["converged"]):
        raise ValueError("Cannot certify a non-converged crossed random-slope location-scale fit.")
    payload = _certificate_payload(result)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {"payload": payload, "sha256": sha256(encoded).hexdigest()}


def validate_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
    result: GazepointCrossedHierarchicalLocationScaleRandomSlopesResult,
    certificate,
) -> bool:
    if not isinstance(result, GazepointCrossedHierarchicalLocationScaleRandomSlopesResult):
        return False
    if not isinstance(certificate, Mapping):
        return False
    if "payload" not in certificate or "sha256" not in certificate:
        return False
    if not isinstance(certificate["payload"], Mapping) or not isinstance(
        certificate["sha256"], str
    ):
        return False
    try:
        provided_payload = dict(certificate["payload"])
        provided_encoded = json.dumps(
            provided_payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if sha256(provided_encoded).hexdigest() != certificate["sha256"]:
            return False
        expected = (
            create_gazepoint_crossed_hierarchical_location_scale_random_slopes_certificate(
                result
            )
        )
        expected_encoded = json.dumps(
            expected["payload"],
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return provided_encoded.decode("utf-8") == expected_encoded
    except (TypeError, ValueError, OverflowError):
        return False
