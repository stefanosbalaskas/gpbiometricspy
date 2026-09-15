from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

from .hierarchical_location_scale import _freeze_mapping, _readonly
from .hierarchical_location_scale_crossed import (
    _positive_definite_system,
    _prepare_fit_data as _prepare_crossed_fit_data,
)
from .hierarchical_location_scale_crossed_random_scale_core import _scale_slope_values
from .hierarchical_location_scale_crossed_random_slopes import _slope_values

_LOG_2PI = float(np.log(2.0 * np.pi))
_MODEL_VERSION = "gaussian-crossed-hierarchical-location-scale-joint-random-slopes-v1"


@dataclass(frozen=True)
class GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult:
    mean_coef: tuple[float, ...]
    scale_coef: tuple[float, ...]
    mean_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    participant_location_random_slope_col: str
    item_location_random_slope_col: str
    participant_scale_random_slope_col: str
    item_scale_random_slope_col: str
    participant_random_effect_sd: tuple[float, float, float, float]
    item_random_effect_sd: tuple[float, float, float, float]
    participant_covariance: np.ndarray
    participant_correlation: np.ndarray
    item_covariance: np.ndarray
    item_correlation: np.ndarray
    log_likelihood: float
    participant_random_effects: pd.DataFrame
    item_random_effects: pd.DataFrame
    metadata: Mapping
    diagnostics: Mapping
    encoder: Mapping
    parameter_vector: np.ndarray
    model_class: str = "gazepoint_crossed_hierarchical_location_scale_joint_random_slopes"

    def __post_init__(self):
        for name in (
            "participant_covariance",
            "participant_correlation",
            "item_covariance",
            "item_correlation",
            "parameter_vector",
        ):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        for name in ("participant_random_effects", "item_random_effects"):
            object.__setattr__(self, name, getattr(self, name).copy(deep=True))
        for name in ("metadata", "diagnostics", "encoder"):
            object.__setattr__(self, name, _freeze_mapping(getattr(self, name)))


def _covariance_from_cholesky_params(params: np.ndarray):
    params = np.asarray(params, dtype=float)
    if params.shape != (10,) or not np.isfinite(params).all():
        raise ValueError("Random-effect covariance parameters must contain ten finite values.")
    log_d0, log_d1, log_d2, log_d3, l10, l20, l21, l30, l31, l32 = params
    L = np.array(
        [
            [np.exp(np.clip(log_d0, -20.0, 20.0)), 0.0, 0.0, 0.0],
            [l10, np.exp(np.clip(log_d1, -20.0, 20.0)), 0.0, 0.0],
            [l20, l21, np.exp(np.clip(log_d2, -20.0, 20.0)), 0.0],
            [l30, l31, l32, np.exp(np.clip(log_d3, -20.0, 20.0))],
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
    if theta.shape != (p + q + 20,) or not np.isfinite(theta).all():
        raise ValueError("Parameter vector has invalid size or contains non-finite values.")
    beta = theta[:p]
    gamma = theta[p : p + q]
    participant = _covariance_from_cholesky_params(theta[p + q : p + q + 10])
    item = _covariance_from_cholesky_params(theta[p + q + 10 : p + q + 20])
    return beta, gamma, participant, item


def _prepare_fit_data(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    mean_cols: list[str],
    scale_cols: list[str],
    participant_location_random_slope_col: str,
    item_location_random_slope_col: str,
    participant_scale_random_slope_col: str,
    item_scale_random_slope_col: str,
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
    frame, *_rest, encoder = prepared
    participant_labels = frame[participant_col].astype(str).to_numpy()
    item_labels = frame[item_col].astype(str).to_numpy()
    if len(np.unique(participant_labels)) < 8:
        raise ValueError(
            "Crossed joint random-slope covariance estimation requires at least eight participant levels."
        )
    if len(np.unique(item_labels)) < 8:
        raise ValueError(
            "Crossed joint random-slope covariance estimation requires at least eight item levels."
        )
    participant_location = _slope_values(
        frame,
        participant_labels,
        participant_location_random_slope_col,
        mean_cols,
        encoder,
        role_name="participant",
    )
    item_location = _slope_values(
        frame,
        item_labels,
        item_location_random_slope_col,
        mean_cols,
        encoder,
        role_name="item",
    )
    participant_scale = _scale_slope_values(
        frame,
        participant_labels,
        participant_scale_random_slope_col,
        scale_cols,
        encoder,
        role_name="participant",
    )
    item_scale = _scale_slope_values(
        frame,
        item_labels,
        item_scale_random_slope_col,
        scale_cols,
        encoder,
        role_name="item",
    )
    return (
        *prepared,
        participant_location,
        item_location,
        participant_scale,
        item_scale,
    )


def _latent_indices(
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
):
    participant_location = 4 * participant_index
    participant_location_slope = participant_location + 1
    participant_scale = participant_location + 2
    participant_scale_slope = participant_location + 3
    item_base = 4 * n_participants
    item_location = item_base + 4 * item_index
    item_location_slope = item_location + 1
    item_scale = item_location + 2
    item_scale_slope = item_location + 3
    return tuple(
        np.asarray(values, dtype=int)
        for values in (
            participant_location,
            participant_location_slope,
            participant_scale,
            participant_scale_slope,
            item_location,
            item_location_slope,
            item_scale,
            item_scale_slope,
        )
    )


def _joint_logposterior_grad_hess(
    b: np.ndarray,
    y: np.ndarray,
    xb: np.ndarray,
    zg: np.ndarray,
    participant_location_values: np.ndarray,
    item_location_values: np.ndarray,
    participant_scale_values: np.ndarray,
    item_scale_values: np.ndarray,
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
    latent_dimension = 4 * (n_participants + n_items)
    if b.shape != (latent_dimension,):
        raise ValueError("Latent vector has the wrong dimension.")
    lengths = {
        len(y),
        len(xb),
        len(zg),
        len(participant_location_values),
        len(item_location_values),
        len(participant_scale_values),
        len(item_scale_values),
        len(participant_index),
        len(item_index),
    }
    if len(lengths) != 1:
        raise ValueError("Observation-level inputs must have the same length.")
    (
        participant_location,
        participant_location_slope,
        participant_scale,
        participant_scale_slope,
        item_location,
        item_location_slope,
        item_scale,
        item_scale_slope,
    ) = _latent_indices(participant_index, item_index, n_participants)
    mean_shift = (
        b[participant_location]
        + b[participant_location_slope] * participant_location_values
        + b[item_location]
        + b[item_location_slope] * item_location_values
    )
    scale_shift = (
        b[participant_scale]
        + b[participant_scale_slope] * participant_scale_values
        + b[item_scale]
        + b[item_scale_slope] * item_scale_values
    )
    eta = np.clip(zg + scale_shift, -20.0, 20.0)
    inv_var = np.exp(-2.0 * eta)
    residual = y - xb - mean_shift
    value = float(
        np.sum(-0.5 * _LOG_2PI - eta - 0.5 * residual * residual * inv_var)
    )
    gradient = np.zeros(latent_dimension, dtype=float)
    hessian = np.zeros((latent_dimension, latent_dimension), dtype=float)
    grad_location = residual * inv_var
    grad_scale = -1.0 + residual * residual * inv_var
    hess_location = -inv_var
    hess_location_scale = -2.0 * residual * inv_var
    hess_scale = -2.0 * residual * residual * inv_var

    location_indices = (
        participant_location,
        participant_location_slope,
        item_location,
        item_location_slope,
    )
    location_coefficients = (
        np.ones(len(y), dtype=float),
        participant_location_values,
        np.ones(len(y), dtype=float),
        item_location_values,
    )
    scale_indices = (
        participant_scale,
        participant_scale_slope,
        item_scale,
        item_scale_slope,
    )
    scale_coefficients = (
        np.ones(len(y), dtype=float),
        participant_scale_values,
        np.ones(len(y), dtype=float),
        item_scale_values,
    )
    for indices, coefficient in zip(location_indices, location_coefficients, strict=True):
        np.add.at(gradient, indices, coefficient * grad_location)
    for indices, coefficient in zip(scale_indices, scale_coefficients, strict=True):
        np.add.at(gradient, indices, coefficient * grad_scale)

    for row_values in zip(
        *location_indices,
        *scale_indices,
        participant_location_values,
        item_location_values,
        participant_scale_values,
        item_scale_values,
        hess_location,
        hess_location_scale,
        hess_scale,
        strict=True,
    ):
        (
            participant_loc,
            participant_loc_slope,
            item_loc,
            item_loc_slope,
            participant_scl,
            participant_scl_slope,
            item_scl,
            item_scl_slope,
            participant_r_location,
            item_r_location,
            participant_r_scale,
            item_r_scale,
            h_ll,
            h_ls,
            h_ss,
        ) = row_values
        loc = (
            int(participant_loc),
            int(participant_loc_slope),
            int(item_loc),
            int(item_loc_slope),
        )
        loc_coef = (
            1.0,
            float(participant_r_location),
            1.0,
            float(item_r_location),
        )
        scl = (
            int(participant_scl),
            int(participant_scl_slope),
            int(item_scl),
            int(item_scl_slope),
        )
        scl_coef = (
            1.0,
            float(participant_r_scale),
            1.0,
            float(item_r_scale),
        )
        for row, row_coefficient in zip(loc, loc_coef, strict=True):
            for col, col_coefficient in zip(loc, loc_coef, strict=True):
                hessian[row, col] += h_ll * row_coefficient * col_coefficient
            for col, col_coefficient in zip(scl, scl_coef, strict=True):
                value_ls = h_ls * row_coefficient * col_coefficient
                hessian[row, col] += value_ls
                hessian[col, row] += value_ls
        for row, row_coefficient in zip(scl, scl_coef, strict=True):
            for col, col_coefficient in zip(scl, scl_coef, strict=True):
                hessian[row, col] += h_ss * row_coefficient * col_coefficient

    for count, covariance_inv, logdet, offset in (
        (n_participants, participant_cov_inv, participant_logdet, 0),
        (n_items, item_cov_inv, item_logdet, 4 * n_participants),
    ):
        for level in range(count):
            indices = np.arange(offset + 4 * level, offset + 4 * level + 4)
            effects = b[indices]
            value += (
                -2.0 * _LOG_2PI
                - 0.5 * logdet
                - 0.5 * float(effects @ covariance_inv @ effects)
            )
            gradient[indices] -= covariance_inv @ effects
            hessian[np.ix_(indices, indices)] -= covariance_inv
    return value, gradient, hessian


def _posterior_mode(
    y: np.ndarray,
    xb: np.ndarray,
    zg: np.ndarray,
    participant_location_values: np.ndarray,
    item_location_values: np.ndarray,
    participant_scale_values: np.ndarray,
    item_scale_values: np.ndarray,
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
    latent_dimension = 4 * (n_participants + n_items)
    b = np.zeros(latent_dimension, dtype=float)
    args = (
        y,
        xb,
        zg,
        participant_location_values,
        item_location_values,
        participant_scale_values,
        item_scale_values,
        participant_index,
        item_index,
        n_participants,
        n_items,
        participant_cov_inv,
        participant_logdet,
        item_cov_inv,
        item_logdet,
    )
    value, gradient, hessian = _joint_logposterior_grad_hess(b, *args)
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
                candidate, *args
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
            converged = float(np.max(np.abs(gradient))) <= max(10.0 * tol, 1e-5)
            break
    max_abs_gradient = float(np.max(np.abs(gradient)))
    converged = bool(converged or max_abs_gradient <= tol)
    negative_hessian, chol, jitter = _positive_definite_system(-hessian)
    diagnostics = {
        "converged": converged,
        "iterations": int(iterations),
        "max_abs_gradient": max_abs_gradient,
        "hessian_jitter": float(jitter),
        "logdet_negative_hessian": float(2.0 * np.log(np.diag(chol)).sum()),
    }
    return b, negative_hessian, float(value), diagnostics


def _laplace_loglik(
    theta: np.ndarray,
    y: np.ndarray,
    X: np.ndarray,
    Z: np.ndarray,
    participant_location_values: np.ndarray,
    item_location_values: np.ndarray,
    participant_scale_values: np.ndarray,
    item_scale_values: np.ndarray,
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
    n_items: int,
    *,
    mode_max_steps: int,
    mode_tol: float,
    return_state: bool = False,
):
    try:
        beta, gamma, participant, item = _decode_theta(theta, X.shape[1], Z.shape[1])
        mode, negative_hessian, posterior_value, mode_diagnostics = _posterior_mode(
            y,
            X @ beta,
            Z @ gamma,
            participant_location_values,
            item_location_values,
            participant_scale_values,
            item_scale_values,
            participant_index,
            item_index,
            n_participants,
            n_items,
            participant[1],
            participant[2],
            item[1],
            item[2],
            max_steps=mode_max_steps,
            tol=mode_tol,
        )
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        return (-np.inf, None) if return_state else -np.inf
    if not mode_diagnostics["converged"] or mode_diagnostics["hessian_jitter"] > 1e-5:
        return (-np.inf, None) if return_state else -np.inf
    value = float(
        posterior_value
        + 0.5 * mode.size * _LOG_2PI
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
    sd = float(np.std(residual, ddof=ddof))
    if not np.isfinite(sd) or sd <= 1e-6:
        sd = max(float(np.std(y)), 1.0)
    gamma = np.zeros(Z.shape[1], dtype=float)
    gamma[0] = np.log(max(sd, 0.0001))

    def block(location_intercept: float, location_slope: float, scale_intercept: float, scale_slope: float):
        return [
            np.log(max(sd * location_intercept, 0.001)),
            np.log(location_slope),
            np.log(scale_intercept),
            np.log(scale_slope),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

    return np.r_[
        beta,
        gamma,
        block(0.30, 0.12, 0.12, 0.08),
        block(0.20, 0.10, 0.08, 0.06),
    ]


def _parameter_bounds(p: int, q: int):
    block = [
        (-8.0, 4.0),
        (-8.0, 2.0),
        (-8.0, 2.0),
        (-8.0, 2.0),
        *[(-4.0, 4.0)] * 6,
    ]
    return [*[(None, None)] * (p + q), *block, *block]


def _random_effect_tables(
    mode: np.ndarray,
    negative_hessian: np.ndarray,
    participant_levels: np.ndarray,
    item_levels: np.ndarray,
):
    try:
        covariance = np.linalg.inv(negative_hessian)
    except np.linalg.LinAlgError:
        covariance = np.linalg.pinv(negative_hessian)
    sd = np.sqrt(np.maximum(np.diag(covariance), 0.0))

    def table(levels: np.ndarray, offset: int, label: str):
        rows = []
        for number, level in enumerate(levels):
            a = offset + 4 * number
            b = a + 1
            c = a + 2
            d = a + 3
            rows.append(
                {
                    label: str(level),
                    "location_intercept_mode": float(mode[a]),
                    "location_slope_mode": float(mode[b]),
                    "log_scale_intercept_mode": float(mode[c]),
                    "log_scale_slope_mode": float(mode[d]),
                    "location_intercept_sd": float(sd[a]),
                    "location_slope_sd": float(sd[b]),
                    "log_scale_intercept_sd": float(sd[c]),
                    "log_scale_slope_sd": float(sd[d]),
                    "location_intercept_slope_cov": float(covariance[a, b]),
                    "location_intercept_log_scale_intercept_cov": float(covariance[a, c]),
                    "location_intercept_log_scale_slope_cov": float(covariance[a, d]),
                    "location_slope_log_scale_intercept_cov": float(covariance[b, c]),
                    "location_slope_log_scale_slope_cov": float(covariance[b, d]),
                    "log_scale_intercept_slope_cov": float(covariance[c, d]),
                }
            )
        return pd.DataFrame(rows)

    return (
        table(participant_levels, 0, "participant"),
        table(item_levels, 4 * len(participant_levels), "item"),
    )
