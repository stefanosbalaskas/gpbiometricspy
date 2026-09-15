from __future__ import annotations

import json
from hashlib import sha256
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .hierarchical_location_scale import (
    _apply_encoder,
    _canonical_frame_hash,
    _normalise_predictor_list,
)
from .hierarchical_location_scale_crossed_random_scale_core import (
    GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult,
    _MODEL_VERSION,
    _decode_theta,
    _initial_theta,
    _laplace_loglik,
    _parameter_bounds,
    _prepare_fit_data,
    _random_effect_tables,
)
from .hierarchical_location_scale_crossed_random_slopes import _simulation_covariance


def fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    *,
    participant_scale_random_slope_col: str,
    item_scale_random_slope_col: str,
    mean_cols: Sequence[str] | str | None = None,
    scale_cols: Sequence[str] | str | None = None,
    standardize_numeric: bool = True,
    maxiter: int = 160,
    mode_max_steps: int = 50,
    mode_tol: float = 1e-6,
    max_latent_dimension: int = 450,
) -> GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult:
    """Fit Gaussian crossed participant-item random slopes in the log-scale equation."""
    mean_cols, scale_cols = (
        _normalise_predictor_list(mean_cols),
        _normalise_predictor_list(scale_cols),
    )
    for name, value in (
        ("participant_scale_random_slope_col", participant_scale_random_slope_col),
        ("item_scale_random_slope_col", item_scale_random_slope_col),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"`{name}` must be a non-empty column name.")
    participant_scale_random_slope_col = participant_scale_random_slope_col.strip()
    item_scale_random_slope_col = item_scale_random_slope_col.strip()
    if not isinstance(maxiter, int) or isinstance(maxiter, bool) or maxiter < 1:
        raise ValueError("`maxiter` must be a positive integer.")
    if (
        not isinstance(mode_max_steps, int)
        or isinstance(mode_max_steps, bool)
        or mode_max_steps < 1
    ):
        raise ValueError("`mode_max_steps` must be a positive integer.")
    if not np.isfinite(mode_tol) or mode_tol <= 0:
        raise ValueError("`mode_tol` must be a positive finite number.")
    if (
        not isinstance(max_latent_dimension, int)
        or isinstance(max_latent_dimension, bool)
        or max_latent_dimension < 36
    ):
        raise ValueError("`max_latent_dimension` must be an integer of at least 36.")

    prepared = _prepare_fit_data(
        data,
        outcome_col,
        participant_col,
        item_col,
        mean_cols,
        scale_cols,
        participant_scale_random_slope_col,
        item_scale_random_slope_col,
        standardize_numeric=bool(standardize_numeric),
    )
    (
        frame,
        y,
        plevels,
        pidx,
        ilevels,
        iidx,
        X,
        Z,
        mean_terms,
        scale_terms,
        encoder,
        pr,
        ir,
    ) = prepared
    dim = 3 * (len(plevels) + len(ilevels))
    if dim > max_latent_dimension:
        raise ValueError(
            f"Crossed random scale-slope latent dimension {dim} exceeds "
            f"`max_latent_dimension` ({max_latent_dimension}); increase the limit only "
            "after considering dense Laplace cost."
        )
    theta0 = _initial_theta(y, X, Z)
    bounds = _parameter_bounds(X.shape[1], Z.shape[1])

    def objective(theta):
        value = _laplace_loglik(
            theta,
            y,
            X,
            Z,
            pr,
            ir,
            pidx,
            iidx,
            len(plevels),
            len(ilevels),
            mode_max_steps=mode_max_steps,
            mode_tol=mode_tol,
        )
        return 1e30 if not np.isfinite(value) else -float(value)

    primary_opt = minimize(
        objective,
        theta0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": maxiter, "ftol": 1e-9, "gtol": 1e-6, "maxls": 30},
    )
    opt = (
        primary_opt
        if primary_opt.success
        else minimize(
            objective,
            np.asarray(primary_opt.x, dtype=float),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": maxiter, "ftol": 1e-8, "gtol": 1e-4, "maxls": 100},
        )
    )
    optimizer_gradient = np.asarray(
        getattr(opt, "jac", np.full_like(opt.x, np.nan)), dtype=float
    )
    optimizer_gradient_inf_norm = float(
        np.max(np.abs(np.nan_to_num(optimizer_gradient, nan=np.inf)))
    )
    optimizer_stationary = bool(optimizer_gradient_inf_norm <= 1e-4)
    optimizer_converged = bool(opt.success or optimizer_stationary)
    ll, state = _laplace_loglik(
        opt.x,
        y,
        X,
        Z,
        pr,
        ir,
        pidx,
        iidx,
        len(plevels),
        len(ilevels),
        mode_max_steps=mode_max_steps,
        mode_tol=mode_tol,
        return_state=True,
    )
    if state is None or not np.isfinite(ll):
        raise RuntimeError("Optimizer did not produce a finite converged Laplace solution.")
    mode, nh, mode_diag, participant, item = state
    beta, gamma, pcheck, icheck = _decode_theta(opt.x, X.shape[1], Z.shape[1])
    if not (
        np.allclose(participant[0], pcheck[0]) and np.allclose(item[0], icheck[0])
    ):
        raise RuntimeError("Internal covariance decoding mismatch.")
    pe, ie = _random_effect_tables(mode, nh, plevels, ilevels)
    pcov, _, _, psd, pcorr = participant
    icov, _, _, isd, icorr = item
    metadata = {
        "model_version": _MODEL_VERSION,
        "outcome_col": str(outcome_col),
        "participant_col": str(participant_col),
        "item_col": str(item_col),
        "participant_scale_random_slope_col": participant_scale_random_slope_col,
        "item_scale_random_slope_col": item_scale_random_slope_col,
        "n_rows": int(len(frame)),
        "n_participants": int(len(plevels)),
        "n_items": int(len(ilevels)),
        "latent_dimension": int(dim),
        "training_sha256": _canonical_frame_hash(frame),
        "approximation": (
            "joint Laplace approximation over crossed participant/item location "
            "intercepts, log-scale intercepts, and log-scale slopes"
        ),
        "conditional_distribution": "Gaussian",
        "random_effect_structure": (
            "independent participant and item trivariate blocks: location intercept, "
            "log-scale intercept, log-scale slope"
        ),
        "scientific_boundary": (
            "crossed log-scale random slopes model residual-dispersion association "
            "heterogeneity; they do not identify causal effects, artifacts, sensor "
            "validity, measurement quality, or latent psychological/clinical states"
        ),
    }
    diagnostics = {
        "converged": bool(optimizer_converged and mode_diag["converged"]),
        "optimizer_success": bool(opt.success),
        "optimizer_status": int(opt.status),
        "optimizer_message": str(opt.message),
        "optimizer_iterations": int(getattr(opt, "nit", -1)),
        "optimizer_function_evaluations": int(getattr(opt, "nfev", -1)),
        "optimizer_restarted": bool(opt is not primary_opt),
        "optimizer_stationary": optimizer_stationary,
        "optimizer_gradient_inf_norm": optimizer_gradient_inf_norm,
        "posterior_mode_converged": bool(mode_diag["converged"]),
        "posterior_mode_iterations": int(mode_diag["iterations"]),
        "posterior_mode_max_abs_gradient": float(mode_diag["max_abs_gradient"]),
        "posterior_hessian_jitter": float(mode_diag["hessian_jitter"]),
        "logdet_negative_hessian": float(mode_diag["logdet_negative_hessian"]),
        "incidence_connected": True,
        "laplace_dense_hessian": True,
        "max_latent_dimension": int(max_latent_dimension),
    }
    return GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult(
        tuple(map(float, beta)),
        tuple(map(float, gamma)),
        tuple(mean_terms),
        tuple(scale_terms),
        participant_scale_random_slope_col,
        item_scale_random_slope_col,
        float(psd[0]),
        float(psd[1]),
        float(psd[2]),
        float(pcorr[0, 1]),
        float(pcorr[0, 2]),
        float(pcorr[1, 2]),
        float(isd[0]),
        float(isd[1]),
        float(isd[2]),
        float(icorr[0, 1]),
        float(icorr[0, 2]),
        float(icorr[1, 2]),
        pcov,
        icov,
        float(ll),
        pe,
        ie,
        metadata,
        diagnostics,
        encoder,
        np.asarray(opt.x, float),
    )


def _prediction_scale_slope_values(data, slope_col, encoder):
    if slope_col not in data:
        raise ValueError(
            f"Missing required random scale-slope prediction column `{slope_col}`."
        )
    cfg = encoder["scale_spec"][slope_col]
    raw = pd.to_numeric(data[slope_col], errors="coerce").to_numpy(float)
    if not np.isfinite(raw).all():
        raise ValueError(
            f"Prediction random scale-slope column `{slope_col}` must be finite numeric."
        )
    return (raw - float(cfg["center"])) / float(cfg["scale"])


def predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
    result,
    new_data,
    *,
    include_random_effects=True,
    unknown_levels="population",
):
    if not isinstance(
        result, GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult
    ):
        raise TypeError(
            "`result` must be a "
            "GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult."
        )
    if not isinstance(new_data, pd.DataFrame):
        raise TypeError("`new_data` must be a pandas DataFrame.")
    if unknown_levels not in {"population", "error"}:
        raise ValueError("`unknown_levels` must be 'population' or 'error'.")
    pcol, icol = (
        str(result.metadata["participant_col"]),
        str(result.metadata["item_col"]),
    )
    required = [
        pcol,
        icol,
        *result.encoder["mean_cols"],
        *result.encoder["scale_cols"],
    ]
    missing = [col for col in dict.fromkeys(required) if col not in new_data]
    if missing:
        raise ValueError("Missing required prediction column(s): " + ", ".join(missing))
    if new_data[pcol].isna().any() or new_data[icol].isna().any():
        raise ValueError("Participant and item identifiers must be non-missing for prediction.")
    X, mt = _apply_encoder(
        new_data,
        list(result.encoder["mean_cols"]),
        result.encoder["mean_spec"],
        allow_unknown=False,
    )
    Z, st = _apply_encoder(
        new_data,
        list(result.encoder["scale_cols"]),
        result.encoder["scale_spec"],
        allow_unknown=False,
    )
    if tuple(mt) != result.mean_terms or tuple(st) != result.scale_terms:
        raise RuntimeError("Prediction design encoding does not match the fitted model.")
    pr = _prediction_scale_slope_values(
        new_data, result.participant_scale_random_slope_col, result.encoder
    )
    ir = _prediction_scale_slope_values(
        new_data, result.item_scale_random_slope_col, result.encoder
    )
    mean = X @ np.asarray(result.mean_coef, float)
    logscale = Z @ np.asarray(result.scale_coef, float)
    plook = result.participant_random_effects.set_index("participant")
    ilook = result.item_random_effects.set_index("item")
    pseen, iseen, levels = ([], [], [])
    for n, (p, i) in enumerate(
        zip(new_data[pcol].astype(str), new_data[icol].astype(str), strict=True)
    ):
        sp, si = (p in plook.index, i in ilook.index)
        pseen.append(sp)
        iseen.append(si)
        if unknown_levels == "error" and (not sp or not si):
            raise ValueError(
                "Conditional prediction encountered an unseen participant or item while "
                "`unknown_levels='error'`."
            )
        if include_random_effects:
            for seen, key, lookup, r in (
                (sp, p, plook, pr[n]),
                (si, i, ilook, ir[n]),
            ):
                if seen:
                    row = lookup.loc[key]
                    mean[n] += float(row["location_intercept_mode"])
                    logscale[n] += float(row["log_scale_intercept_mode"]) + float(
                        row["log_scale_slope_mode"]
                    ) * r
            levels.append(
                "conditional_participant_item"
                if sp and si
                else "conditional_participant_population_item"
                if sp
                else "population_participant_conditional_item"
                if si
                else "population_participant_item"
            )
        else:
            levels.append("population_fixed_effects")
    return pd.DataFrame(
        {
            "predicted_mean": mean,
            "predicted_log_scale": logscale,
            "predicted_scale": np.exp(np.clip(logscale, -20, 20)),
            "participant_seen": pseen,
            "item_seen": iseen,
            "prediction_level": levels,
        },
        index=new_data.index,
    )


def simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
    *,
    n_participants=8,
    n_items=8,
    repeats=1,
    mean_intercept=0.4,
    mean_slope=0.55,
    log_scale_intercept=-0.2,
    participant_scale_fixed_slope=0.2,
    item_scale_fixed_slope=-0.15,
    participant_tau_location_intercept=0.5,
    participant_tau_log_scale_intercept=0.18,
    participant_tau_log_scale_slope=0.12,
    participant_rho_location_log_scale_intercept=0.15,
    participant_rho_location_log_scale_slope=-0.1,
    participant_rho_log_scale_intercept_slope=0.1,
    item_tau_location_intercept=0.35,
    item_tau_log_scale_intercept=0.12,
    item_tau_log_scale_slope=0.1,
    item_rho_location_log_scale_intercept=-0.2,
    item_rho_location_log_scale_slope=0.1,
    item_rho_log_scale_intercept_slope=-0.1,
    seed=123,
):
    if (
        not isinstance(n_participants, int)
        or isinstance(n_participants, bool)
        or n_participants < 6
    ):
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
            mean_slope,
            log_scale_intercept,
            participant_scale_fixed_slope,
            item_scale_fixed_slope,
        ],
        float,
    )
    if not np.isfinite(fixed).all():
        raise ValueError("Simulation fixed-effect parameters must be finite.")
    pcov = _simulation_covariance(
        participant_tau_location_intercept,
        participant_tau_log_scale_intercept,
        participant_tau_log_scale_slope,
        participant_rho_location_log_scale_intercept,
        participant_rho_location_log_scale_slope,
        participant_rho_log_scale_intercept_slope,
    )
    icov = _simulation_covariance(
        item_tau_location_intercept,
        item_tau_log_scale_intercept,
        item_tau_log_scale_slope,
        item_rho_location_log_scale_intercept,
        item_rho_location_log_scale_slope,
        item_rho_log_scale_intercept_slope,
    )
    rng = np.random.default_rng(seed)
    pidx = np.repeat(np.arange(n_participants), n_items * repeats)
    iidx = np.tile(np.repeat(np.arange(n_items), repeats), n_participants)
    mp, pr, ir = (rng.normal(size=len(pidx)) for _ in range(3))
    pe = rng.multivariate_normal(np.zeros(3), pcov, size=n_participants)
    ie = rng.multivariate_normal(np.zeros(3), icov, size=n_items)
    mean = mean_intercept + mean_slope * mp + pe[pidx, 0] + ie[iidx, 0]
    logscale = (
        log_scale_intercept
        + participant_scale_fixed_slope * pr
        + item_scale_fixed_slope * ir
        + pe[pidx, 1]
        + pe[pidx, 2] * pr
        + ie[iidx, 1]
        + ie[iidx, 2] * ir
    )
    frame = pd.DataFrame(
        {
            "outcome": mean + np.exp(logscale) * rng.normal(size=len(pidx)),
            "participant": [f"p{x:03d}" for x in pidx],
            "item": [f"i{x:03d}" for x in iidx],
            "mean_predictor": mp,
            "participant_scale_predictor": pr,
            "item_scale_predictor": ir,
        }
    )
    frame.attrs["truth"] = {
        "mean_coef": (float(mean_intercept), float(mean_slope)),
        "scale_coef": (
            float(log_scale_intercept),
            float(participant_scale_fixed_slope),
            float(item_scale_fixed_slope),
        ),
        "participant_covariance": pcov.copy(),
        "item_covariance": icov.copy(),
        "seed": int(seed),
    }
    return frame


def _certificate_payload(result):
    return {
        "model_version": str(result.metadata["model_version"]),
        "model_class": result.model_class,
        "training_sha256": str(result.metadata["training_sha256"]),
        "outcome_col": str(result.metadata["outcome_col"]),
        "participant_col": str(result.metadata["participant_col"]),
        "item_col": str(result.metadata["item_col"]),
        "participant_scale_random_slope_col": result.participant_scale_random_slope_col,
        "item_scale_random_slope_col": result.item_scale_random_slope_col,
        "n_rows": int(result.metadata["n_rows"]),
        "n_participants": int(result.metadata["n_participants"]),
        "n_items": int(result.metadata["n_items"]),
        "latent_dimension": int(result.metadata["latent_dimension"]),
        "mean_terms": list(result.mean_terms),
        "scale_terms": list(result.scale_terms),
        "mean_coef": list(map(float, result.mean_coef)),
        "scale_coef": list(map(float, result.scale_coef)),
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


def create_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
    result,
):
    if not isinstance(
        result, GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult
    ):
        raise TypeError(
            "`result` must be a "
            "GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult."
        )
    if not bool(result.diagnostics["converged"]):
        raise ValueError(
            "Cannot certify a non-converged crossed random scale-slope location-scale fit."
        )
    payload = _certificate_payload(result)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return {"payload": payload, "sha256": sha256(encoded).hexdigest()}


def validate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
    result,
    certificate,
):
    if not isinstance(
        result, GazepointCrossedHierarchicalLocationScaleRandomScaleSlopesResult
    ) or not isinstance(certificate, Mapping):
        return False
    if "payload" not in certificate or "sha256" not in certificate:
        return False
    if not isinstance(certificate["payload"], Mapping) or not isinstance(
        certificate["sha256"], str
    ):
        return False
    try:
        payload = dict(certificate["payload"])
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        if sha256(encoded).hexdigest() != certificate["sha256"]:
            return False
        expected = (
            create_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes_certificate(
                result
            )
        )
        return encoded.decode() == json.dumps(
            expected["payload"],
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        return False
