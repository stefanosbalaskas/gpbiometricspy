from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import numpy as np
import pandas as pd
from .hierarchical_location_scale import _freeze_mapping, _readonly
from .hierarchical_location_scale_crossed import _positive_definite_system, _prepare_fit_data as _prepare_crossed_fit_data
from .hierarchical_location_scale_crossed_random_slopes import _covariance_from_cholesky_params
_LOG_2PI = float(np.log(2.0 * np.pi))
_MODEL_VERSION = 'gaussian-crossed-hierarchical-location-scale-random-scale-slopes-v1'

@dataclass(frozen=True)
class GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult:
    mean_coef: tuple[float, ...]
    scale_coef: tuple[float, ...]
    mean_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    participant_scale_random_slope_col: str
    item_scale_random_slope_col: str
    participant_tau_location_intercept: float
    participant_tau_log_scale_intercept: float
    participant_tau_log_scale_slope: float
    participant_rho_location_log_scale_intercept: float
    participant_rho_location_log_scale_slope: float
    participant_rho_log_scale_intercept_slope: float
    item_tau_location_intercept: float
    item_tau_log_scale_intercept: float
    item_tau_log_scale_slope: float
    item_rho_location_log_scale_intercept: float
    item_rho_location_log_scale_slope: float
    item_rho_log_scale_intercept_slope: float
    participant_covariance: np.ndarray
    item_covariance: np.ndarray
    log_likelihood: float
    participant_random_effects: pd.DataFrame
    item_random_effects: pd.DataFrame
    metadata: Mapping
    diagnostics: Mapping
    encoder: Mapping
    parameter_vector: np.ndarray
    model_class: str = 'gazepoint_crossed_hierarchical_location_scale_random_scale_slopes'

    def __post_init__(self):
        for name in ('participant_covariance', 'item_covariance', 'parameter_vector'):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        for name in ('participant_random_effects', 'item_random_effects'):
            object.__setattr__(self, name, getattr(self, name).copy(deep=True))
        for name in ('metadata', 'diagnostics', 'encoder'):
            object.__setattr__(self, name, _freeze_mapping(getattr(self, name)))

def _decode_theta(theta, p, q):
    theta = np.asarray(theta, float)
    if theta.shape != (p + q + 12,) or not np.isfinite(theta).all():
        raise ValueError('Parameter vector has invalid size or contains non-finite values.')
    return (theta[:p], theta[p:p + q], _covariance_from_cholesky_params(theta[p + q:p + q + 6]), _covariance_from_cholesky_params(theta[p + q + 6:p + q + 12]))

def _scale_slope_values(frame, labels, slope_col, scale_cols, encoder, *, role_name):
    field = f'{role_name}_scale_random_slope_col'
    if slope_col not in scale_cols:
        raise ValueError(f'`{field}` must also be included in `scale_cols` as a fixed effect.')
    cfg = encoder['scale_spec'][slope_col]
    if cfg['kind'] != 'numeric':
        raise ValueError(f'`{field}` must be numeric.')
    raw = pd.to_numeric(frame[slope_col], errors='coerce').to_numpy(float)
    scale = float(cfg['scale'])
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(f'`{field}` has an invalid fitted scaling factor.')
    values = (raw - float(cfg['center'])) / scale
    if not np.isfinite(values).all() or float(np.ptp(values)) <= 0:
        raise ValueError(f'`{field}` must contain finite within-sample variation.')
    levels = np.unique(labels)
    if len(levels) < 6:
        raise ValueError(f'Crossed random scale-slope covariance estimation requires at least six {role_name} levels.')
    bad = [str(level) for level in levels if np.unique(values[labels == level]).size < 2]
    if bad:
        raise ValueError(f"`{field}` must vary within every {role_name}; non-varying levels: {', '.join(bad[:5])}")
    return values

def _prepare_fit_data(data, outcome_col, participant_col, item_col, mean_cols, scale_cols, participant_scale_random_slope_col, item_scale_random_slope_col, *, standardize_numeric):
    prepared = _prepare_crossed_fit_data(data, outcome_col, participant_col, item_col, mean_cols, scale_cols, standardize_numeric=standardize_numeric)
    frame, *_, encoder = prepared
    p = _scale_slope_values(frame, frame[participant_col].astype(str).to_numpy(), str(participant_scale_random_slope_col), scale_cols, encoder, role_name='participant')
    i = _scale_slope_values(frame, frame[item_col].astype(str).to_numpy(), str(item_scale_random_slope_col), scale_cols, encoder, role_name='item')
    return (*prepared, p, i)

def _latent_indices(pidx, iidx, nparticipants):
    ploc = 3 * pidx
    iloc = 3 * nparticipants + 3 * iidx
    return tuple((np.asarray(x, int) for x in (ploc, ploc + 1, ploc + 2, iloc, iloc + 1, iloc + 2)))

def _joint_logposterior_grad_hess(b, y, xb, zg, pr, ir, pidx, iidx, nparticipants, nitems, pcov_inv, plogdet, icov_inv, ilogdet):
    b = np.asarray(b, float)
    dim = 3 * (nparticipants + nitems)
    if b.shape != (dim,):
        raise ValueError('Latent vector has the wrong dimension.')
    if len({len(y), len(xb), len(zg), len(pr), len(ir), len(pidx), len(iidx)}) != 1:
        raise ValueError('Observation-level inputs must have the same length.')
    pl, p0, p1, il, i0, i1 = _latent_indices(pidx, iidx, nparticipants)
    mean_shift = b[pl] + b[il]
    scale_shift = b[p0] + b[p1] * pr + b[i0] + b[i1] * ir
    eta = np.clip(zg + scale_shift, -20.0, 20.0)
    iv = np.exp(-2.0 * eta)
    resid = y - xb - mean_shift
    value = float(np.sum(-0.5 * _LOG_2PI - eta - 0.5 * resid * resid * iv))
    grad = np.zeros(dim)
    hess = np.zeros((dim, dim))
    gl, gs = (resid * iv, -1.0 + resid * resid * iv)
    hll, hls, hss = (-iv, -2.0 * resid * iv, -2.0 * resid * resid * iv)
    for idx in (pl, il):
        np.add.at(grad, idx, gl)
    for idx, coef in ((p0, 1.0), (p1, pr), (i0, 1.0), (i1, ir)):
        np.add.at(grad, idx, coef * gs)
    for ploc, ps0, ps1, iloc, is0, is1, rp, ri, ll, ls, ss in zip(pl, p0, p1, il, i0, i1, pr, ir, hll, hls, hss, strict=True):
        loc = (int(ploc), int(iloc))
        scl = (int(ps0), int(ps1), int(is0), int(is1))
        coeff = (1.0, float(rp), 1.0, float(ri))
        for row in loc:
            for col in loc:
                hess[row, col] += ll
            for col, cc in zip(scl, coeff, strict=True):
                hess[row, col] += ls * cc
                hess[col, row] += ls * cc
        for row, rc in zip(scl, coeff, strict=True):
            for col, cc in zip(scl, coeff, strict=True):
                hess[row, col] += ss * rc * cc
    for g, inv, logdet, offset in ((nparticipants, pcov_inv, plogdet, 0), (nitems, icov_inv, ilogdet, 3 * nparticipants)):
        for level in range(g):
            idx = np.arange(offset + 3 * level, offset + 3 * level + 3)
            eff = b[idx]
            value += -1.5 * _LOG_2PI - 0.5 * logdet - 0.5 * float(eff @ inv @ eff)
            grad[idx] -= inv @ eff
            hess[np.ix_(idx, idx)] -= inv
    return (value, grad, hess)

def _posterior_mode(y, xb, zg, pr, ir, pidx, iidx, nparticipants, nitems, pcov_inv, plogdet, icov_inv, ilogdet, *, max_steps, tol):
    dim = 3 * (nparticipants + nitems)
    b = np.zeros(dim)
    args = (y, xb, zg, pr, ir, pidx, iidx, nparticipants, nitems, pcov_inv, plogdet, icov_inv, ilogdet)
    value, grad, hess = _joint_logposterior_grad_hess(b, *args)
    converged = False
    iterations = 0
    for iterations in range(1, max_steps + 1):
        if float(np.max(np.abs(grad))) <= tol:
            converged = True
            break
        try:
            system, _, _ = _positive_definite_system(-hess)
            direction = np.linalg.solve(system, grad)
        except np.linalg.LinAlgError:
            break
        if not np.isfinite(direction).all():
            break
        alpha = 1.0
        accepted = False
        while alpha >= 1.0 / 256.0:
            candidate = b + alpha * direction
            nv, ng, nh = _joint_logposterior_grad_hess(candidate, *args)
            if np.isfinite(nv) and nv >= value + 1e-12:
                b, value, grad, hess, accepted = (candidate, nv, ng, nh, True)
                break
            alpha *= 0.5
        if not accepted:
            converged = float(np.max(np.abs(grad))) <= max(10.0 * tol, 1e-05)
            break
    max_grad = float(np.max(np.abs(grad)))
    converged = converged or max_grad <= tol
    nh, chol, jitter = _positive_definite_system(-hess)
    diagnostics = {'converged': bool(converged), 'iterations': int(iterations), 'max_abs_gradient': max_grad, 'hessian_jitter': float(jitter), 'logdet_negative_hessian': float(2.0 * np.log(np.diag(chol)).sum())}
    return (b, nh, float(value), diagnostics)

def _laplace_loglik(theta, y, X, Z, pr, ir, pidx, iidx, nparticipants, nitems, *, mode_max_steps, mode_tol, return_state=False):
    try:
        beta, gamma, participant, item = _decode_theta(theta, X.shape[1], Z.shape[1])
        mode, nh, pv, diag = _posterior_mode(y, X @ beta, Z @ gamma, pr, ir, pidx, iidx, nparticipants, nitems, participant[1], participant[2], item[1], item[2], max_steps=mode_max_steps, tol=mode_tol)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        return (-np.inf, None) if return_state else -np.inf
    if not diag['converged'] or diag['hessian_jitter'] > 1e-05:
        return (-np.inf, None) if return_state else -np.inf
    value = float(pv + 0.5 * mode.size * _LOG_2PI - 0.5 * diag['logdet_negative_hessian'])
    if not np.isfinite(value):
        return (-np.inf, None) if return_state else -np.inf
    state = (mode, nh, diag, participant, item)
    return (value, state) if return_state else value

def _initial_theta(y, X, Z):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residual = y - X @ beta
    ddof = min(max(X.shape[1], 1), max(len(y) - 1, 1))
    sd = float(np.std(residual, ddof=ddof))
    if not np.isfinite(sd) or sd <= 1e-06:
        sd = max(float(np.std(y)), 1.0)
    gamma = np.zeros(Z.shape[1])
    gamma[0] = np.log(max(sd, 0.0001))

    def block(loc, s0, s1):
        return [np.log(max(sd * loc, 0.001)), np.log(s0), np.log(s1), 0.0, 0.0, 0.0]
    return np.r_[beta, gamma, block(0.3, 0.12, 0.08), block(0.2, 0.08, 0.06)]

def _parameter_bounds(p, q):
    block = [(-8.0, 4.0), (-8.0, 2.0), (-8.0, 2.0), (-4.0, 4.0), (-4.0, 4.0), (-4.0, 4.0)]
    return [*[(None, None)] * (p + q), *block, *block]

def _random_effect_tables(mode, negative_hessian, participant_levels, item_levels):
    try:
        cov = np.linalg.inv(negative_hessian)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(negative_hessian)
    sd = np.sqrt(np.maximum(np.diag(cov), 0.0))

    def table(levels, offset, label):
        rows = []
        for n, level in enumerate(levels):
            a, b, d = (offset + 3 * n, offset + 3 * n + 1, offset + 3 * n + 2)
            rows.append({label: str(level), 'location_intercept_mode': float(mode[a]), 'log_scale_intercept_mode': float(mode[b]), 'log_scale_slope_mode': float(mode[d]), 'location_intercept_sd': float(sd[a]), 'log_scale_intercept_sd': float(sd[b]), 'log_scale_slope_sd': float(sd[d]), 'location_log_scale_intercept_cov': float(cov[a, b]), 'location_log_scale_slope_cov': float(cov[a, d]), 'log_scale_intercept_slope_cov': float(cov[b, d])})
        return pd.DataFrame(rows)
    return (table(participant_levels, 0, 'participant'), table(item_levels, 3 * len(participant_levels), 'item'))
