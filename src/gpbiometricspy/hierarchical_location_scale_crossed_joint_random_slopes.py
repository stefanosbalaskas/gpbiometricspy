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
from .hierarchical_location_scale_crossed_joint_random_slopes_core import (
    GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult,
    _MODEL_VERSION,
    _decode_theta,
    _initial_theta,
    _laplace_loglik,
    _parameter_bounds,
    _prepare_fit_data,
    _random_effect_tables,
)


def _normalise_slope_column(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{name}` must be a non-empty column name.")
    return value.strip()


def fit_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
    data: pd.DataFrame,
    outcome_col: str,
    participant_col: str,
    item_col: str,
    *,
    participant_location_random_slope_col: str,
    item_location_random_slope_col: str,
    participant_scale_random_slope_col: str,
    item_scale_random_slope_col: str,
    mean_cols: Sequence[str] | str | None = None,
    scale_cols: Sequence[str] | str | None = None,
    standardize_numeric: bool = True,
    maxiter: int = 180,
    mode_max_steps: int = 50,
    mode_tol: float = 1e-6,
    max_latent_dimension: int = 512,
) -> GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult:
    """Fit crossed participant-item joint random slopes in location and log-scale equations."""
    mean_cols = _normalise_predictor_list(mean_cols)
    scale_cols = _normalise_predictor_list(scale_cols)
    participant_location_random_slope_col = _normalise_slope_column(
        "participant_location_random_slope_col",
        participant_location_random_slope_col,
    )
    item_location_random_slope_col = _normalise_slope_column(
        "item_location_random_slope_col", item_location_random_slope_col
    )
    participant_scale_random_slope_col = _normalise_slope_column(
        "participant_scale_random_slope_col", participant_scale_random_slope_col
    )
    item_scale_random_slope_col = _normalise_slope_column(
        "item_scale_random_slope_col", item_scale_random_slope_col
    )
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
        or max_latent_dimension < 64
    ):
        raise ValueError("`max_latent_dimension` must be an integer of at least 64.")

    prepared = _prepare_fit_data(
        data,
        outcome_col,
        participant_col,
        item_col,
        mean_cols,
        scale_cols,
        participant_location_random_slope_col,
        item_location_random_slope_col,
        participant_scale_random_slope_col,
        item_scale_random_slope_col,
        standardize_numeric=bool(standardize_numeric),
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
        participant_location_values,
        item_location_values,
        participant_scale_values,
        item_scale_values,
    ) = prepared
    latent_dimension = 4 * (len(participant_levels) + len(item_levels))
    if latent_dimension > max_latent_dimension:
        raise ValueError(
            f"Crossed joint random-slope latent dimension {latent_dimension} exceeds "
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
            participant_location_values,
            item_location_values,
            participant_scale_values,
            item_scale_values,
            participant_index,
            item_index,
            len(participant_levels),
            len(item_levels),
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
    log_likelihood, state = _laplace_loglik(
        opt.x,
        y,
        X,
        Z,
        participant_location_values,
        item_location_values,
        participant_scale_values,
        item_scale_values,
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
        opt.x, X.shape[1], Z.shape[1]
    )
    if not (
        np.allclose(participant[0], participant_check[0])
        and np.allclose(item[0], item_check[0])
    ):
        raise RuntimeError("Internal covariance decoding mismatch.")
    participant_effects, item_effects = _random_effect_tables(
        mode, negative_hessian, participant_levels, item_levels
    )
    participant_covariance, _, _, participant_sd, participant_correlation = participant
    item_covariance, _, _, item_sd, item_correlation = item
    metadata = {
        "model_version": _MODEL_VERSION,
        "outcome_col": str(outcome_col),
        "participant_col": str(participant_col),
        "item_col": str(item_col),
        "participant_location_random_slope_col": participant_location_random_slope_col,
        "item_location_random_slope_col": item_location_random_slope_col,
        "participant_scale_random_slope_col": participant_scale_random_slope_col,
        "item_scale_random_slope_col": item_scale_random_slope_col,
        "n_rows": int(len(frame)),
        "n_participants": int(len(participant_levels)),
        "n_items": int(len(item_levels)),
        "latent_dimension": int(latent_dimension),
        "training_sha256": _canonical_frame_hash(frame),
        "approximation": (
            "joint dense Laplace approximation over crossed participant/item location "
            "intercepts, location slopes, log-scale intercepts, and log-scale slopes"
        ),
        "conditional_distribution": "Gaussian",
        "random_effect_structure": (
            "independent participant and item four-dimensional blocks: location "
            "intercept, location slope, log-scale intercept, log-scale slope"
        ),
        "scientific_boundary": (
            "crossed location and log-scale random slopes estimate association "
            "heterogeneity under the fitted model; they do not identify causal effects, "
            "artifacts, reliability, sensor validity, measurement quality, or latent "
            "psychological/clinical states"
        ),
    }
    diagnostics = {
        "converged": bool(optimizer_converged and mode_diagnostics["converged"]),
        "optimizer_success": bool(opt.success),
        "optimizer_status": int(opt.status),
        "optimizer_message": str(opt.message),
        "optimizer_iterations": int(getattr(opt, "nit", -1)),
        "optimizer_function_evaluations": int(getattr(opt, "nfev", -1)),
        "optimizer_restarted": bool(opt is not primary_opt),
        "optimizer_stationary": optimizer_stationary,
        "optimizer_gradient_inf_norm": optimizer_gradient_inf_norm,
        "posterior_mode_converged": bool(mode_diagnostics["converged"]),
        "posterior_mode_iterations": int(mode_diagnostics["iterations"]),
        "posterior_mode_max_abs_gradient": float(
            mode_diagnostics["max_abs_gradient"]
        ),
        "posterior_hessian_jitter": float(mode_diagnostics["hessian_jitter"]),
        "logdet_negative_hessian": float(
            mode_diagnostics["logdet_negative_hessian"]
        ),
        "incidence_connected": True,
        "laplace_dense_hessian": True,
        "max_latent_dimension": int(max_latent_dimension),
    }
    return GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult(
        mean_coef=tuple(map(float, beta)),
        scale_coef=tuple(map(float, gamma)),
        mean_terms=tuple(mean_terms),
        scale_terms=tuple(scale_terms),
        participant_location_random_slope_col=participant_location_random_slope_col,
        item_location_random_slope_col=item_location_random_slope_col,
        participant_scale_random_slope_col=participant_scale_random_slope_col,
        item_scale_random_slope_col=item_scale_random_slope_col,
        participant_random_effect_sd=tuple(map(float, participant_sd)),
        item_random_effect_sd=tuple(map(float, item_sd)),
        participant_covariance=participant_covariance,
        participant_correlation=participant_correlation,
        item_covariance=item_covariance,
        item_correlation=item_correlation,
        log_likelihood=float(log_likelihood),
        participant_random_effects=participant_effects,
        item_random_effects=item_effects,
        metadata=metadata,
        diagnostics=diagnostics,
        encoder=encoder,
        parameter_vector=np.asarray(opt.x, dtype=float),
    )


def _prediction_slope_values(
    data: pd.DataFrame,
    slope_col: str,
    encoder: Mapping,
    *,
    equation: str,
) -> np.ndarray:
    if slope_col not in data:
        raise ValueError(f"Missing required random {equation}-slope prediction column `{slope_col}`.")
    spec_name = "mean_spec" if equation == "location" else "scale_spec"
    cfg = encoder[spec_name][slope_col]
    raw = pd.to_numeric(data[slope_col], errors="coerce").to_numpy(float)
    if not np.isfinite(raw).all():
        raise ValueError(
            f"Prediction random {equation}-slope column `{slope_col}` must be finite numeric."
        )
    scale = float(cfg["scale"])
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(
            f"Prediction random {equation}-slope column `{slope_col}` has an invalid fitted scaling factor."
        )
    return (raw - float(cfg["center"])) / scale


def predict_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
    result,
    new_data,
    *,
    include_random_effects: bool = True,
    unknown_levels: str = "population",
):
    if not isinstance(
        result, GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult
    ):
        raise TypeError(
            "`result` must be a GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult."
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
    missing = [column for column in dict.fromkeys(required) if column not in new_data]
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
    participant_location = _prediction_slope_values(
        new_data,
        result.participant_location_random_slope_col,
        result.encoder,
        equation="location",
    )
    item_location = _prediction_slope_values(
        new_data,
        result.item_location_random_slope_col,
        result.encoder,
        equation="location",
    )
    participant_scale = _prediction_slope_values(
        new_data,
        result.participant_scale_random_slope_col,
        result.encoder,
        equation="scale",
    )
    item_scale = _prediction_slope_values(
        new_data,
        result.item_scale_random_slope_col,
        result.encoder,
        equation="scale",
    )
    mean = X @ np.asarray(result.mean_coef, dtype=float)
    log_scale = Z @ np.asarray(result.scale_coef, dtype=float)
    participant_lookup = result.participant_random_effects.set_index("participant")
    item_lookup = result.item_random_effects.set_index("item")
    participant_seen = []
    item_seen = []
    prediction_level = []
    for number, (participant, item) in enumerate(
        zip(
            new_data[participant_col].astype(str),
            new_data[item_col].astype(str),
            strict=True,
        )
    ):
        participant_is_seen = participant in participant_lookup.index
        item_is_seen = item in item_lookup.index
        participant_seen.append(participant_is_seen)
        item_seen.append(item_is_seen)
        if unknown_levels == "error" and (not participant_is_seen or not item_is_seen):
            raise ValueError(
                "Conditional prediction encountered an unseen participant or item while "
                "`unknown_levels='error'`."
            )
        if include_random_effects:
            for seen, key, lookup, location_value, scale_value in (
                (
                    participant_is_seen,
                    participant,
                    participant_lookup,
                    participant_location[number],
                    participant_scale[number],
                ),
                (
                    item_is_seen,
                    item,
                    item_lookup,
                    item_location[number],
                    item_scale[number],
                ),
            ):
                if seen:
                    row = lookup.loc[key]
                    mean[number] += float(row["location_intercept_mode"]) + float(
                        row["location_slope_mode"]
                    ) * location_value
                    log_scale[number] += float(
                        row["log_scale_intercept_mode"]
                    ) + float(row["log_scale_slope_mode"]) * scale_value
            prediction_level.append(
                "conditional_participant_item"
                if participant_is_seen and item_is_seen
                else "conditional_participant_population_item"
                if participant_is_seen
                else "population_participant_conditional_item"
                if item_is_seen
                else "population_participant_item"
            )
        else:
            prediction_level.append("population_fixed_effects")
    return pd.DataFrame(
        {
            "predicted_mean": mean,
            "predicted_log_scale": log_scale,
            "predicted_scale": np.exp(np.clip(log_scale, -20.0, 20.0)),
            "participant_seen": participant_seen,
            "item_seen": item_seen,
            "prediction_level": prediction_level,
        },
        index=new_data.index,
    )


def _simulation_covariance(
    sds: Sequence[float], correlations: Sequence[float], *, role_name: str
) -> np.ndarray:
    sds = np.asarray(tuple(sds), dtype=float)
    correlations = np.asarray(tuple(correlations), dtype=float)
    if sds.shape != (4,) or not np.isfinite(sds).all():
        raise ValueError(f"`{role_name}_sds` must contain four finite values.")
    if np.any(sds <= 0):
        raise ValueError(f"`{role_name}_sds` must be strictly positive.")
    if correlations.shape != (6,) or not np.isfinite(correlations).all():
        raise ValueError(f"`{role_name}_correlations` must contain six finite values.")
    if np.any(np.abs(correlations) >= 1):
        raise ValueError(f"`{role_name}_correlations` must lie strictly inside (-1, 1).")
    r01, r02, r03, r12, r13, r23 = correlations
    correlation = np.array(
        [
            [1.0, r01, r02, r03],
            [r01, 1.0, r12, r13],
            [r02, r12, 1.0, r23],
            [r03, r13, r23, 1.0],
        ],
        dtype=float,
    )
    covariance = np.outer(sds, sds) * correlation
    if not np.all(np.linalg.eigvalsh(covariance) > 1e-10):
        raise ValueError(f"`{role_name}` random-effect covariance must be positive definite.")
    return covariance


def simulate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes(
    *,
    n_participants: int = 8,
    n_items: int = 8,
    repeats: int = 1,
    mean_intercept: float = 0.4,
    mean_predictor_slope: float = 0.45,
    participant_location_fixed_slope: float = 0.20,
    item_location_fixed_slope: float = -0.15,
    log_scale_intercept: float = -0.25,
    participant_scale_fixed_slope: float = 0.16,
    item_scale_fixed_slope: float = -0.12,
    participant_sds: Sequence[float] = (0.50, 0.16, 0.18, 0.12),
    participant_correlations: Sequence[float] = (0.15, -0.10, 0.05, 0.10, -0.05, 0.10),
    item_sds: Sequence[float] = (0.35, 0.12, 0.13, 0.10),
    item_correlations: Sequence[float] = (-0.15, 0.10, -0.05, 0.05, 0.10, -0.10),
    seed: int = 123,
) -> pd.DataFrame:
    if (
        not isinstance(n_participants, int)
        or isinstance(n_participants, bool)
        or n_participants < 8
    ):
        raise ValueError("`n_participants` must be an integer of at least eight.")
    if not isinstance(n_items, int) or isinstance(n_items, bool) or n_items < 8:
        raise ValueError("`n_items` must be an integer of at least eight.")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("`repeats` must be a positive integer.")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("`seed` must be a non-negative integer.")
    fixed = np.array(
        [
            mean_intercept,
            mean_predictor_slope,
            participant_location_fixed_slope,
            item_location_fixed_slope,
            log_scale_intercept,
            participant_scale_fixed_slope,
            item_scale_fixed_slope,
        ],
        dtype=float,
    )
    if not np.isfinite(fixed).all():
        raise ValueError("Simulation fixed-effect parameters must be finite.")
    participant_covariance = _simulation_covariance(
        participant_sds, participant_correlations, role_name="participant"
    )
    item_covariance = _simulation_covariance(
        item_sds, item_correlations, role_name="item"
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
    participant_location_predictor = rng.normal(size=n_rows)
    item_location_predictor = rng.normal(size=n_rows)
    participant_scale_predictor = rng.normal(size=n_rows)
    item_scale_predictor = rng.normal(size=n_rows)
    participant_effects = rng.multivariate_normal(
        np.zeros(4), participant_covariance, size=n_participants
    )
    item_effects = rng.multivariate_normal(
        np.zeros(4), item_covariance, size=n_items
    )
    mean = (
        mean_intercept
        + mean_predictor_slope * mean_predictor
        + participant_location_fixed_slope * participant_location_predictor
        + item_location_fixed_slope * item_location_predictor
        + participant_effects[participant_index, 0]
        + participant_effects[participant_index, 1] * participant_location_predictor
        + item_effects[item_index, 0]
        + item_effects[item_index, 1] * item_location_predictor
    )
    log_scale = (
        log_scale_intercept
        + participant_scale_fixed_slope * participant_scale_predictor
        + item_scale_fixed_slope * item_scale_predictor
        + participant_effects[participant_index, 2]
        + participant_effects[participant_index, 3] * participant_scale_predictor
        + item_effects[item_index, 2]
        + item_effects[item_index, 3] * item_scale_predictor
    )
    frame = pd.DataFrame(
        {
            "outcome": mean + np.exp(log_scale) * rng.normal(size=n_rows),
            "participant": [f"p{x:03d}" for x in participant_index],
            "item": [f"i{x:03d}" for x in item_index],
            "mean_predictor": mean_predictor,
            "participant_location_predictor": participant_location_predictor,
            "item_location_predictor": item_location_predictor,
            "participant_scale_predictor": participant_scale_predictor,
            "item_scale_predictor": item_scale_predictor,
        }
    )
    frame.attrs["truth"] = {
        "mean_coef": (
            float(mean_intercept),
            float(mean_predictor_slope),
            float(participant_location_fixed_slope),
            float(item_location_fixed_slope),
        ),
        "scale_coef": (
            float(log_scale_intercept),
            float(participant_scale_fixed_slope),
            float(item_scale_fixed_slope),
        ),
        "participant_covariance": participant_covariance.copy(),
        "item_covariance": item_covariance.copy(),
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
        "participant_location_random_slope_col": result.participant_location_random_slope_col,
        "item_location_random_slope_col": result.item_location_random_slope_col,
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
        "participant_correlation": result.participant_correlation.tolist(),
        "item_covariance": result.item_covariance.tolist(),
        "item_correlation": result.item_correlation.tolist(),
        "log_likelihood": float(result.log_likelihood),
        "participant_effects_sha256": _canonical_frame_hash(
            result.participant_random_effects
        ),
        "item_effects_sha256": _canonical_frame_hash(result.item_random_effects),
        "parameter_vector": result.parameter_vector.tolist(),
        "approximation": str(result.metadata["approximation"]),
    }


def create_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate(
    result,
):
    if not isinstance(
        result, GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult
    ):
        raise TypeError(
            "`result` must be a GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult."
        )
    if not bool(result.diagnostics["converged"]):
        raise ValueError("Cannot certify a non-converged crossed joint random-slope fit.")
    payload = _certificate_payload(result)
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return {"payload": payload, "sha256": sha256(canonical).hexdigest()}


def validate_gazepoint_crossed_hierarchical_location_scale_joint_random_slopes_certificate(
    result,
    certificate,
) -> bool:
    if not isinstance(
        result, GazepointCrossedHierarchicalLocationScaleJointRandomSlopesResult
    ) or not isinstance(certificate, Mapping):
        return False
    payload = certificate.get("payload")
    digest = certificate.get("sha256")
    if not isinstance(payload, Mapping) or not isinstance(digest, str):
        return False
    try:
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        expected = sha256(canonical).hexdigest()
        if digest != expected:
            return False
        return payload == _certificate_payload(result)
    except (TypeError, ValueError, OverflowError):
        return False
