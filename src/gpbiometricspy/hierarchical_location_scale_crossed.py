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
    _fit_encoder,
    _freeze_mapping,
    _normalise_predictor_list,
    _readonly,
)

_LOG_2PI = float(np.log(2.0 * np.pi))
_MODEL_VERSION = "gaussian-crossed-hierarchical-location-scale-v1"


@dataclass(frozen=True)
class GazepointCrossedHierarchicalLocationScaleResult:
    mean_coef: tuple[float, ...]
    scale_coef: tuple[float, ...]
    mean_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    participant_tau_location: float
    participant_tau_log_scale: float
    participant_rho: float
    item_tau_location: float
    item_tau_log_scale: float
    item_rho: float
    participant_covariance: np.ndarray
    item_covariance: np.ndarray
    log_likelihood: float
    participant_random_effects: pd.DataFrame
    item_random_effects: pd.DataFrame
    metadata: Mapping
    diagnostics: Mapping
    encoder: Mapping
    parameter_vector: np.ndarray
    model_class: str = "gazepoint_crossed_hierarchical_location_scale"

    def __post_init__(self):
        object.__setattr__(self, "participant_covariance", _readonly(self.participant_covariance))
        object.__setattr__(self, "item_covariance", _readonly(self.item_covariance))
        object.__setattr__(self, "parameter_vector", _readonly(self.parameter_vector))
        object.__setattr__(self, "participant_random_effects", self.participant_random_effects.copy(deep=True))
        object.__setattr__(self, "item_random_effects", self.item_random_effects.copy(deep=True))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        object.__setattr__(self, "diagnostics", _freeze_mapping(self.diagnostics))
        object.__setattr__(self, "encoder", _freeze_mapping(self.encoder))


def _covariance_from_params(log_tau_location: float, log_tau_scale: float, atanh_rho: float):
    if not np.isfinite([log_tau_location, log_tau_scale, atanh_rho]).all():
        raise ValueError("Random-effect covariance parameters must be finite.")
    tau_location = float(np.exp(np.clip(log_tau_location, -20.0, 20.0)))
    tau_log_scale = float(np.exp(np.clip(log_tau_scale, -20.0, 20.0)))
    rho = float(np.tanh(atanh_rho))
    cov = np.array(
        [
            [tau_location * tau_location, rho * tau_location * tau_log_scale],
            [rho * tau_location * tau_log_scale, tau_log_scale * tau_log_scale],
        ],
        dtype=float,
    )
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0 or not np.isfinite(logdet):
        raise np.linalg.LinAlgError("Random-effect covariance is not positive definite.")
    return cov, np.linalg.inv(cov), float(logdet), tau_location, tau_log_scale, rho


def _decode_theta(theta: np.ndarray, p: int, q: int):
    theta = np.asarray(theta, dtype=float)
    if theta.shape != (p + q + 6,) or not np.isfinite(theta).all():
        raise ValueError("Parameter vector has invalid size or contains non-finite values.")
    beta = theta[:p]
    gamma = theta[p : p + q]
    participant = _covariance_from_params(*theta[p + q : p + q + 3])
    item = _covariance_from_params(*theta[p + q + 3 : p + q + 6])
    return beta, gamma, participant, item


def _incidence_connected(
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
    n_items: int,
) -> bool:
    participant_to_items = [set() for _ in range(n_participants)]
    item_to_participants = [set() for _ in range(n_items)]
    for participant, item in zip(participant_index, item_index, strict=True):
        participant_to_items[int(participant)].add(int(item))
        item_to_participants[int(item)].add(int(participant))
    seen_participants = {0}
    seen_items: set[int] = set()
    stack: list[tuple[str, int]] = [("participant", 0)]
    while stack:
        kind, node = stack.pop()
        if kind == "participant":
            for item in participant_to_items[node]:
                if item not in seen_items:
                    seen_items.add(item)
                    stack.append(("item", item))
        else:
            for participant in item_to_participants[node]:
                if participant not in seen_participants:
                    seen_participants.add(participant)
                    stack.append(("participant", participant))
    return len(seen_participants) == n_participants and len(seen_items) == n_items


def _prepare_fit_data(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    mean_cols: list[str],
    scale_cols: list[str],
    *,
    standardize_numeric: bool,
):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    roles = [str(outcome_col), str(participant_col), str(item_col)]
    if len(set(roles)) != 3:
        raise ValueError("`outcome_col`, `participant_col`, and `item_col` must be distinct.")
    aliased = [
        col
        for col in dict.fromkeys([*mean_cols, *scale_cols])
        if col in set(roles)
    ]
    if aliased:
        raise ValueError(
            "Predictor columns must not reuse outcome/participant/item columns: "
            + ", ".join(aliased)
        )
    needed = list(
        dict.fromkeys([outcome_col, participant_col, item_col, *mean_cols, *scale_cols])
    )
    missing = [col for col in needed if col not in data]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))
    frame = data.loc[:, needed].copy()
    outcome = pd.to_numeric(frame[outcome_col], errors="coerce")
    keep = (
        outcome.notna()
        & np.isfinite(outcome.to_numpy(float))
        & frame[participant_col].notna()
        & frame[item_col].notna()
    )
    for col in set(mean_cols + scale_cols):
        keep &= frame[col].notna()
        if pd.api.types.is_numeric_dtype(frame[col]):
            values = pd.to_numeric(frame[col], errors="coerce")
            keep &= values.notna() & np.isfinite(values.to_numpy(float))
    frame = frame.loc[keep].reset_index(drop=True)
    if frame.empty:
        raise ValueError("No complete finite rows remain after filtering.")
    y = pd.to_numeric(frame[outcome_col], errors="raise").to_numpy(float)
    participants = frame[participant_col].astype(str).to_numpy()
    items = frame[item_col].astype(str).to_numpy()
    participant_levels, participant_index = np.unique(participants, return_inverse=True)
    item_levels, item_index = np.unique(items, return_inverse=True)
    if len(participant_levels) < 4 or len(item_levels) < 4:
        raise ValueError(
            "Crossed location-scale modelling requires at least four participants and four items."
        )
    participant_item_counts = [
        np.unique(item_index[participant_index == index]).size
        for index in range(len(participant_levels))
    ]
    item_participant_counts = [
        np.unique(participant_index[item_index == index]).size
        for index in range(len(item_levels))
    ]
    if min(participant_item_counts) < 2:
        raise ValueError(
            "Every participant must contribute observations on at least two distinct items."
        )
    if min(item_participant_counts) < 2:
        raise ValueError(
            "Every item must be observed for at least two distinct participants."
        )
    if not _incidence_connected(
        participant_index,
        item_index,
        len(participant_levels),
        len(item_levels),
    ):
        raise ValueError(
            "Participant-item incidence graph must be connected for crossed-effect estimation."
        )
    mean_spec, mean_terms = _fit_encoder(
        frame, mean_cols, standardize_numeric=standardize_numeric
    )
    scale_spec, scale_terms = _fit_encoder(
        frame, scale_cols, standardize_numeric=standardize_numeric
    )
    X, mean_terms_check = _apply_encoder(
        frame, mean_cols, mean_spec, allow_unknown=False
    )
    Z, scale_terms_check = _apply_encoder(
        frame, scale_cols, scale_spec, allow_unknown=False
    )
    if mean_terms != mean_terms_check or scale_terms != scale_terms_check:
        raise RuntimeError("Internal design encoding mismatch.")
    encoder = {
        "mean_cols": tuple(mean_cols),
        "scale_cols": tuple(scale_cols),
        "mean_spec": mean_spec,
        "scale_spec": scale_spec,
        "standardize_numeric": bool(standardize_numeric),
    }
    return (
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
    )


def _latent_indices(
    participant_index: np.ndarray,
    item_index: np.ndarray,
    n_participants: int,
):
    participant_location = 2 * participant_index
    participant_scale = participant_location + 1
    item_base = 2 * n_participants
    item_location = item_base + 2 * item_index
    item_scale = item_location + 1
    return (
        participant_location.astype(int),
        participant_scale.astype(int),
        item_location.astype(int),
        item_scale.astype(int),
    )


def _joint_logposterior_grad_hess(
    b: np.ndarray,
    y: np.ndarray,
    xb: np.ndarray,
    zg: np.ndarray,
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
    latent_dimension = 2 * (n_participants + n_items)
    if b.shape != (latent_dimension,):
        raise ValueError("Latent vector has the wrong dimension.")
    participant_location, participant_scale, item_location, item_scale = _latent_indices(
        participant_index, item_index, n_participants
    )
    mean_shift = b[participant_location] + b[item_location]
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
    np.add.at(gradient, item_location, grad_location)
    np.add.at(gradient, participant_scale, grad_scale)
    np.add.at(gradient, item_scale, grad_scale)
    for participant_loc, participant_scl, item_loc, item_scl, h_ll, h_ls, h_ss in zip(
        participant_location,
        participant_scale,
        item_location,
        item_scale,
        hess_location,
        hess_location_scale,
        hess_scale,
        strict=True,
    ):
        location_indices = (int(participant_loc), int(item_loc))
        scale_indices = (int(participant_scl), int(item_scl))
        for row in location_indices:
            for col in location_indices:
                hessian[row, col] += h_ll
        for row in scale_indices:
            for col in scale_indices:
                hessian[row, col] += h_ss
        for row in location_indices:
            for col in scale_indices:
                hessian[row, col] += h_ls
                hessian[col, row] += h_ls
    prior = 0.0
    for participant in range(n_participants):
        indices = np.array([2 * participant, 2 * participant + 1])
        effects = b[indices]
        prior += (
            -_LOG_2PI
            - 0.5 * participant_logdet
            - 0.5 * float(effects @ participant_cov_inv @ effects)
        )
        gradient[indices] -= participant_cov_inv @ effects
        hessian[np.ix_(indices, indices)] -= participant_cov_inv
    item_base = 2 * n_participants
    for item in range(n_items):
        indices = np.array([item_base + 2 * item, item_base + 2 * item + 1])
        effects = b[indices]
        prior += (
            -_LOG_2PI
            - 0.5 * item_logdet
            - 0.5 * float(effects @ item_cov_inv @ effects)
        )
        gradient[indices] -= item_cov_inv @ effects
        hessian[np.ix_(indices, indices)] -= item_cov_inv
    return float(loglik + prior), gradient, hessian


def _positive_definite_system(matrix: np.ndarray):
    matrix = 0.5 * (np.asarray(matrix, dtype=float) + np.asarray(matrix, dtype=float).T)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] == 0:
        raise ValueError("Curvature matrix must be a non-empty square matrix.")
    if not np.isfinite(matrix).all():
        raise np.linalg.LinAlgError("Curvature matrix contains non-finite values.")
    scale = max(1.0, float(np.max(np.abs(np.diag(matrix)))))
    jitter = 0.0
    identity = np.eye(matrix.shape[0])
    for _ in range(14):
        candidate = matrix + jitter * identity
        try:
            chol = np.linalg.cholesky(candidate)
            return candidate, chol, float(jitter)
        except np.linalg.LinAlgError:
            jitter = 1e-10 * scale if jitter == 0.0 else jitter * 10.0
    raise np.linalg.LinAlgError("Posterior curvature could not be made positive definite.")


def _posterior_mode(
    y: np.ndarray,
    xb: np.ndarray,
    zg: np.ndarray,
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
    latent_dimension = 2 * (n_participants + n_items)
    b = np.zeros(latent_dimension, dtype=float)
    value, gradient, hessian = _joint_logposterior_grad_hess(
        b,
        y,
        xb,
        zg,
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
    return np.r_[
        beta,
        gamma,
        np.log(max(residual_sd * 0.30, 1e-3)),
        np.log(0.12),
        0.0,
        np.log(max(residual_sd * 0.20, 1e-3)),
        np.log(0.08),
        0.0,
    ]


def _parameter_bounds(p: int, q: int):
    return [
        *[(None, None)] * (p + q),
        (-8.0, 4.0),
        (-8.0, 2.0),
        (-3.0, 3.0),
        (-8.0, 4.0),
        (-8.0, 2.0),
        (-3.0, 3.0),
    ]


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
        location = 2 * index
        scale = location + 1
        participant_rows.append(
            {
                "participant": str(label),
                "location_mode": float(mode[location]),
                "log_scale_mode": float(mode[scale]),
                "location_sd": float(posterior_sd[location]),
                "log_scale_sd": float(posterior_sd[scale]),
                "location_log_scale_cov": float(posterior_covariance[location, scale]),
            }
        )
    item_base = 2 * len(participant_levels)
    item_rows = []
    for index, label in enumerate(item_levels):
        location = item_base + 2 * index
        scale = location + 1
        item_rows.append(
            {
                "item": str(label),
                "location_mode": float(mode[location]),
                "log_scale_mode": float(mode[scale]),
                "location_sd": float(posterior_sd[location]),
                "log_scale_sd": float(posterior_sd[scale]),
                "location_log_scale_cov": float(posterior_covariance[location, scale]),
            }
        )
    return pd.DataFrame(participant_rows), pd.DataFrame(item_rows)


def fit_gazepoint_crossed_hierarchical_location_scale(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    *,
    mean_cols: Sequence[str] | str | None = None,
    scale_cols: Sequence[str] | str | None = None,
    standardize_numeric: bool = True,
    maxiter: int = 160,
    mode_max_steps: int = 50,
    mode_tol: float = 1e-6,
    max_latent_dimension: int = 400,
) -> GazepointCrossedHierarchicalLocationScaleResult:
    mean_cols = _normalise_predictor_list(mean_cols)
    scale_cols = _normalise_predictor_list(scale_cols)
    if not isinstance(maxiter, int) or maxiter < 1:
        raise ValueError("`maxiter` must be a positive integer.")
    if not isinstance(mode_max_steps, int) or mode_max_steps < 1:
        raise ValueError("`mode_max_steps` must be a positive integer.")
    if not np.isfinite(mode_tol) or mode_tol <= 0:
        raise ValueError("`mode_tol` must be a positive finite number.")
    if not isinstance(max_latent_dimension, int) or max_latent_dimension < 16:
        raise ValueError("`max_latent_dimension` must be an integer of at least 16.")
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
    ) = _prepare_fit_data(
        data,
        outcome_col,
        participant_col,
        item_col,
        mean_cols,
        scale_cols,
        standardize_numeric=bool(standardize_numeric),
    )
    latent_dimension = 2 * (len(participant_levels) + len(item_levels))
    if latent_dimension > max_latent_dimension:
        raise ValueError(
            f"Crossed latent dimension {latent_dimension} exceeds `max_latent_dimension` "
            f"({max_latent_dimension}); increase the limit only after considering dense Laplace cost."
        )
    theta0 = _initial_theta(y, X, Z)

    def objective(theta):
        value = _laplace_loglik(
            theta,
            y,
            X,
            Z,
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
        mode, negative_hessian, participant_levels, item_levels
    )
    participant_covariance, _, _, p_tau_location, p_tau_scale, p_rho = participant
    item_covariance, _, _, i_tau_location, i_tau_scale, i_rho = item
    converged = bool(optimization.success and mode_diagnostics["converged"])
    metadata = {
        "model_version": _MODEL_VERSION,
        "outcome_col": str(outcome_col),
        "participant_col": str(participant_col),
        "item_col": str(item_col),
        "n_rows": int(len(frame)),
        "n_participants": int(len(participant_levels)),
        "n_items": int(len(item_levels)),
        "latent_dimension": int(latent_dimension),
        "training_sha256": _canonical_frame_hash(frame),
        "approximation": "joint Laplace approximation over crossed participant/item effects",
        "conditional_distribution": "Gaussian",
        "random_effect_structure": (
            "independent participant and item bivariate random intercepts for location and log-scale"
        ),
        "scientific_boundary": (
            "crossed random effects model association heterogeneity; it does not identify artifacts, "
            "establish sensor validity, or identify causal effects"
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
    return GazepointCrossedHierarchicalLocationScaleResult(
        mean_coef=tuple(float(value) for value in beta),
        scale_coef=tuple(float(value) for value in gamma),
        mean_terms=tuple(mean_terms),
        scale_terms=tuple(scale_terms),
        participant_tau_location=float(p_tau_location),
        participant_tau_log_scale=float(p_tau_scale),
        participant_rho=float(p_rho),
        item_tau_location=float(i_tau_location),
        item_tau_log_scale=float(i_tau_scale),
        item_rho=float(i_rho),
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


def predict_gazepoint_crossed_hierarchical_location_scale(
    result: GazepointCrossedHierarchicalLocationScaleResult,
    new_data: pd.DataFrame,
    *,
    include_random_effects: bool = True,
    unknown_levels: str = "population",
) -> pd.DataFrame:
    if not isinstance(result, GazepointCrossedHierarchicalLocationScaleResult):
        raise TypeError("`result` must be a GazepointCrossedHierarchicalLocationScaleResult.")
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
                predicted_mean[row_index] += float(
                    participant_lookup.loc[participant, "location_mode"]
                )
                predicted_log_scale[row_index] += float(
                    participant_lookup.loc[participant, "log_scale_mode"]
                )
            if seen_item:
                predicted_mean[row_index] += float(item_lookup.loc[item, "location_mode"])
                predicted_log_scale[row_index] += float(item_lookup.loc[item, "log_scale_mode"])
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


def _simulation_covariance(tau_location: float, tau_log_scale: float, rho: float):
    values = np.array([tau_location, tau_log_scale, rho], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Simulation covariance parameters must be finite.")
    if tau_location <= 0 or tau_log_scale <= 0:
        raise ValueError("Simulation random-effect standard deviations must be positive.")
    if not -0.999 < rho < 0.999:
        raise ValueError("Simulation random-effect correlations must lie strictly inside (-0.999, 0.999).")
    covariance = np.array(
        [
            [tau_location * tau_location, rho * tau_location * tau_log_scale],
            [rho * tau_location * tau_log_scale, tau_log_scale * tau_log_scale],
        ],
        dtype=float,
    )
    if np.linalg.det(covariance) <= 0:
        raise ValueError("Simulation covariance must be positive definite.")
    return covariance


def simulate_gazepoint_crossed_hierarchical_location_scale(
    *,
    n_participants: int = 10,
    n_items: int = 8,
    repeats: int = 1,
    mean_intercept: float = 0.4,
    mean_slope: float = 0.7,
    log_scale_intercept: float = -0.2,
    log_scale_slope: float = 0.15,
    participant_tau_location: float = 0.50,
    participant_tau_log_scale: float = 0.18,
    participant_rho: float = 0.25,
    item_tau_location: float = 0.35,
    item_tau_log_scale: float = 0.12,
    item_rho: float = -0.20,
    seed: int = 123,
) -> pd.DataFrame:
    if not isinstance(n_participants, int) or n_participants < 4:
        raise ValueError("`n_participants` must be an integer of at least four.")
    if not isinstance(n_items, int) or n_items < 4:
        raise ValueError("`n_items` must be an integer of at least four.")
    if not isinstance(repeats, int) or repeats < 1:
        raise ValueError("`repeats` must be a positive integer.")
    fixed = np.array(
        [mean_intercept, mean_slope, log_scale_intercept, log_scale_slope],
        dtype=float,
    )
    if not np.isfinite(fixed).all():
        raise ValueError("Simulation fixed-effect parameters must be finite.")
    participant_covariance = _simulation_covariance(
        participant_tau_location,
        participant_tau_log_scale,
        participant_rho,
    )
    item_covariance = _simulation_covariance(
        item_tau_location,
        item_tau_log_scale,
        item_rho,
    )
    rng = np.random.default_rng(seed)
    participant_index = np.repeat(
        np.arange(n_participants), n_items * repeats
    )
    item_index = np.tile(
        np.repeat(np.arange(n_items), repeats), n_participants
    )
    n_rows = len(participant_index)
    mean_predictor = rng.normal(size=n_rows)
    scale_predictor = rng.normal(size=n_rows)
    participant_effects = rng.multivariate_normal(
        np.zeros(2), participant_covariance, size=n_participants
    )
    item_effects = rng.multivariate_normal(
        np.zeros(2), item_covariance, size=n_items
    )
    mean = (
        mean_intercept
        + mean_slope * mean_predictor
        + participant_effects[participant_index, 0]
        + item_effects[item_index, 0]
    )
    log_scale = (
        log_scale_intercept
        + log_scale_slope * scale_predictor
        + participant_effects[participant_index, 1]
        + item_effects[item_index, 1]
    )
    outcome = mean + np.exp(log_scale) * rng.normal(size=n_rows)
    frame = pd.DataFrame(
        {
            "outcome": outcome,
            "participant": [f"p{index:03d}" for index in participant_index],
            "item": [f"i{index:03d}" for index in item_index],
            "mean_predictor": mean_predictor,
            "scale_predictor": scale_predictor,
        }
    )
    frame.attrs["truth"] = {
        "mean_coef": (float(mean_intercept), float(mean_slope)),
        "scale_coef": (float(log_scale_intercept), float(log_scale_slope)),
        "participant_covariance": participant_covariance.copy(),
        "item_covariance": item_covariance.copy(),
        "seed": int(seed),
    }
    return frame


def _certificate_payload(result: GazepointCrossedHierarchicalLocationScaleResult) -> dict:
    return {
        "model_version": str(result.metadata["model_version"]),
        "model_class": result.model_class,
        "training_sha256": str(result.metadata["training_sha256"]),
        "outcome_col": str(result.metadata["outcome_col"]),
        "participant_col": str(result.metadata["participant_col"]),
        "item_col": str(result.metadata["item_col"]),
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


def create_gazepoint_crossed_hierarchical_location_scale_certificate(
    result: GazepointCrossedHierarchicalLocationScaleResult,
) -> dict:
    if not isinstance(result, GazepointCrossedHierarchicalLocationScaleResult):
        raise TypeError("`result` must be a GazepointCrossedHierarchicalLocationScaleResult.")
    if not bool(result.diagnostics["converged"]):
        raise ValueError("Cannot certify a non-converged crossed location-scale fit.")
    payload = _certificate_payload(result)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return {"payload": payload, "sha256": sha256(encoded).hexdigest()}


def validate_gazepoint_crossed_hierarchical_location_scale_certificate(
    result: GazepointCrossedHierarchicalLocationScaleResult,
    certificate,
) -> bool:
    if not isinstance(result, GazepointCrossedHierarchicalLocationScaleResult):
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
        expected = create_gazepoint_crossed_hierarchical_location_scale_certificate(
            result
        )
        expected_encoded = json.dumps(
            expected["payload"],
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        provided_canonical = provided_encoded.decode("utf-8")
        return provided_canonical == expected_encoded
    except (TypeError, ValueError, OverflowError):
        return False
