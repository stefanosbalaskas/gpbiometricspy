from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence
import json
import re

import numpy as np
import pandas as pd

_TIMEBASE_SCHEMA_VERSION = "gpbiometricspy-timebase-audit-v1"
_ALIGNMENT_SCHEMA_VERSION = "gpbiometricspy-multimodal-alignment-v1"
_TIME_COLUMNS = (
    "time_s",
    "time",
    "timestamp",
    "TIME",
    "TIME_MS",
    "TIMESTAMP_MS",
    "MSTIMER",
    "TIME_TICK",
    "CNT",
    "sample",
    "sample_index",
)
_ALLOWED_UNITS = {"auto", "seconds", "milliseconds", "samples"}
_ALLOWED_ALIGNMENT_METHODS = {"affine", "offset"}


def _validate_positive_number(value, name: str, *, allow_zero: bool = False) -> float:
    number = float(value)
    if not np.isfinite(number) or number < 0 or (number == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"`{name}` must be a finite {qualifier} number.")
    return number


def _validate_clock_id(value, name: str) -> str:
    out = str(value).strip()
    if not out:
        raise ValueError(f"`{name}` must be a non-empty string.")
    return out


def _guess_time_column(data: pd.DataFrame) -> str:
    lower = {str(column).lower(): column for column in data.columns}
    for candidate in _TIME_COLUMNS:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    raise ValueError("Could not identify a time column. Supply `time_col` explicitly.")


def _coerce_raw_time(data, time_col: str | None, *, name: str) -> tuple[np.ndarray, str | None]:
    if isinstance(data, pd.DataFrame):
        column = _guess_time_column(data) if time_col is None else time_col
        if column not in data.columns:
            raise ValueError(f"`{time_col}` was not found in `{name}`.")
        raw = pd.to_numeric(data[column], errors="coerce").to_numpy(float)
        return raw, str(column)
    if time_col is not None:
        raise ValueError(f"`{name}_time_col` can only be used when `{name}` is a pandas DataFrame.")
    if isinstance(data, (str, bytes)) or not isinstance(data, Iterable):
        raise TypeError(f"`{name}` must be a numeric timestamp sequence or pandas DataFrame.")
    raw = pd.to_numeric(pd.Series(data), errors="coerce").to_numpy(float)
    return raw, None


def _positive_differences(values: np.ndarray) -> np.ndarray:
    finite = values[np.isfinite(values)]
    if finite.size < 2:
        return np.array([], dtype=float)
    diffs = np.diff(finite)
    return diffs[np.isfinite(diffs) & (diffs > 0)]


def _resolve_time_unit(
    raw: np.ndarray,
    requested: str,
    column: str | None,
    nominal_rate_hz: float | None,
) -> tuple[str, str]:
    if requested not in _ALLOWED_UNITS:
        raise ValueError("`time_unit` must be 'auto', 'seconds', 'milliseconds', or 'samples'.")
    if requested != "auto":
        if requested == "samples" and nominal_rate_hz is None:
            raise ValueError("`nominal_rate_hz` is required when `time_unit='samples'`.")
        return requested, "explicit"
    label = "" if column is None else re.sub(r"[^a-z0-9]+", "_", column.lower()).strip("_")
    if label in {"cnt", "sample", "sample_index", "sample_number", "sample_no"}:
        if nominal_rate_hz is None:
            raise ValueError(
                "A sample-counter timebase was detected but no `nominal_rate_hz` was supplied. "
                "Specify the rate or provide a timestamp column."
            )
        return "samples", "column_name"
    if label.endswith("_ms") or label in {"mstimer", "time_ms", "timestamp_ms"}:
        return "milliseconds", "column_name"
    if label.endswith("_s") or label in {"time", "timestamp"}:
        return "seconds", "column_name"
    positive = _positive_differences(raw)
    if positive.size and float(np.median(positive)) > 5.0:
        return "milliseconds", "interval_heuristic"
    return "seconds", "interval_heuristic"


def _to_seconds(raw: np.ndarray, unit: str, nominal_rate_hz: float | None) -> np.ndarray:
    if unit == "seconds":
        return raw.astype(float, copy=True)
    if unit == "milliseconds":
        return raw.astype(float, copy=True) / 1000.0
    if unit == "samples":
        return raw.astype(float, copy=True) / float(nominal_rate_hz)
    raise ValueError(f"Unsupported resolved time unit: {unit}.")


def _hash_numeric(values: np.ndarray) -> str:
    tokens = ["nan" if not np.isfinite(value) else format(float(value), ".17g") for value in values]
    return sha256(("\n".join(tokens) + "\n").encode("utf-8")).hexdigest()


def _finite_or_none(value: float | int | None):
    if value is None:
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _canonical_digest(payload: Mapping) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GazepointTimebaseAudit:
    clock_id: str
    time_column: str | None
    input_unit: str
    unit_source: str
    n_samples: int
    n_finite_samples: int
    n_nonfinite_timestamps: int
    first_time_s: float | None
    last_time_s: float | None
    duration_s: float | None
    nominal_rate_hz: float | None
    observed_median_rate_hz: float | None
    observed_mean_rate_hz: float | None
    observed_span_rate_hz: float | None
    observed_rate_sd_hz: float | None
    min_instantaneous_rate_hz: float | None
    max_instantaneous_rate_hz: float | None
    median_interval_s: float | None
    mean_interval_s: float | None
    interval_jitter_sd_s: float | None
    interval_jitter_mad_s: float | None
    interval_cv: float | None
    n_duplicate_timestamps: int
    n_backward_timestamps: int
    n_large_gaps: int
    estimated_missing_samples: int | None
    nominal_rate_error_fraction: float | None
    nominal_rate_deviation_ppm: float | None
    rate_evidence: str
    gap_factor: float
    rate_tolerance_fraction: float
    jitter_warning_cv: float
    status: str
    issues: tuple[str, ...]
    time_sha256: str
    schema_version: str = _TIMEBASE_SCHEMA_VERSION


@dataclass(frozen=True)
class GazepointClockAlignment:
    reference_clock: str
    target_clock: str
    method: str
    n_matched_anchors: int
    intercept_s: float
    slope_target_per_reference: float
    drift_ppm: float
    residual_mean_s: float
    residual_sd_s: float
    residual_max_abs_s: float
    r_squared: float | None
    reference_anchor_sha256: str
    target_anchor_sha256: str
    reference_time_unit: str = "seconds"
    target_time_unit: str = "seconds"
    reference_unit_source: str = "explicit"
    target_unit_source: str = "explicit"
    anchor_match_method: str = "row_order"
    estimator: str = "ordinary_least_squares"
    schema_version: str = _ALIGNMENT_SCHEMA_VERSION


def audit_gazepoint_timebase(
    data,
    time_col: str | None = None,
    *,
    time_unit: str = "auto",
    nominal_rate_hz: float | None = None,
    clock_id: str = "recording_clock",
    gap_factor: float = 3.0,
    rate_tolerance_fraction: float = 0.05,
    jitter_warning_cv: float = 0.10,
) -> GazepointTimebaseAudit:
    clock_id = _validate_clock_id(clock_id, "clock_id")
    gap_factor = _validate_positive_number(gap_factor, "gap_factor")
    if gap_factor <= 1.0:
        raise ValueError("`gap_factor` must be greater than 1.")
    rate_tolerance_fraction = _validate_positive_number(
        rate_tolerance_fraction, "rate_tolerance_fraction", allow_zero=True
    )
    jitter_warning_cv = _validate_positive_number(jitter_warning_cv, "jitter_warning_cv", allow_zero=True)
    if nominal_rate_hz is not None:
        nominal_rate_hz = _validate_positive_number(nominal_rate_hz, "nominal_rate_hz")

    raw, column = _coerce_raw_time(data, time_col, name="data")
    unit, unit_source = _resolve_time_unit(raw, time_unit, column, nominal_rate_hz)
    times = _to_seconds(raw, unit, nominal_rate_hz)
    finite = times[np.isfinite(times)]
    n_samples = int(times.size)
    n_finite = int(finite.size)
    n_nonfinite = n_samples - n_finite
    issues: list[str] = []
    rate_evidence = "counter_scaled_by_nominal_rate" if unit == "samples" else "timestamp_observed"
    if unit_source == "interval_heuristic":
        issues.append("heuristic_time_unit")
    if unit == "samples":
        issues.append("counter_scaled_timebase")

    if n_finite < 2:
        issues.append("insufficient_finite_timestamps")
        return GazepointTimebaseAudit(
            clock_id=clock_id,
            time_column=column,
            input_unit=unit,
            unit_source=unit_source,
            n_samples=n_samples,
            n_finite_samples=n_finite,
            n_nonfinite_timestamps=n_nonfinite,
            first_time_s=_finite_or_none(finite[0]) if n_finite else None,
            last_time_s=_finite_or_none(finite[-1]) if n_finite else None,
            duration_s=None,
            nominal_rate_hz=nominal_rate_hz,
            observed_median_rate_hz=None,
            observed_mean_rate_hz=None,
            observed_span_rate_hz=None,
            observed_rate_sd_hz=None,
            min_instantaneous_rate_hz=None,
            max_instantaneous_rate_hz=None,
            median_interval_s=None,
            mean_interval_s=None,
            interval_jitter_sd_s=None,
            interval_jitter_mad_s=None,
            interval_cv=None,
            n_duplicate_timestamps=0,
            n_backward_timestamps=0,
            n_large_gaps=0,
            estimated_missing_samples=None,
            nominal_rate_error_fraction=None,
            nominal_rate_deviation_ppm=None,
            rate_evidence=rate_evidence,
            gap_factor=gap_factor,
            rate_tolerance_fraction=rate_tolerance_fraction,
            jitter_warning_cv=jitter_warning_cv,
            status="fail",
            issues=tuple(issues),
            time_sha256=_hash_numeric(times),
        )

    diffs = np.diff(finite)
    duplicate_count = int(np.sum(diffs == 0))
    backward_count = int(np.sum(diffs < 0))
    positive = diffs[diffs > 0]
    if positive.size == 0:
        issues.append("no_positive_intervals")
        if duplicate_count:
            issues.append("duplicate_timestamps")
        if backward_count:
            issues.append("backward_timestamps")
        return GazepointTimebaseAudit(
            clock_id=clock_id,
            time_column=column,
            input_unit=unit,
            unit_source=unit_source,
            n_samples=n_samples,
            n_finite_samples=n_finite,
            n_nonfinite_timestamps=n_nonfinite,
            first_time_s=_finite_or_none(finite[0]),
            last_time_s=_finite_or_none(finite[-1]),
            duration_s=None,
            nominal_rate_hz=nominal_rate_hz,
            observed_median_rate_hz=None,
            observed_mean_rate_hz=None,
            observed_span_rate_hz=None,
            observed_rate_sd_hz=None,
            min_instantaneous_rate_hz=None,
            max_instantaneous_rate_hz=None,
            median_interval_s=None,
            mean_interval_s=None,
            interval_jitter_sd_s=None,
            interval_jitter_mad_s=None,
            interval_cv=None,
            n_duplicate_timestamps=duplicate_count,
            n_backward_timestamps=backward_count,
            n_large_gaps=0,
            estimated_missing_samples=None,
            nominal_rate_error_fraction=None,
            nominal_rate_deviation_ppm=None,
            rate_evidence=rate_evidence,
            gap_factor=gap_factor,
            rate_tolerance_fraction=rate_tolerance_fraction,
            jitter_warning_cv=jitter_warning_cv,
            status="fail",
            issues=tuple(issues),
            time_sha256=_hash_numeric(times),
        )

    median_interval = float(np.median(positive))
    mean_interval = float(np.mean(positive))
    jitter_sd = float(np.std(positive, ddof=1)) if positive.size > 1 else 0.0
    jitter_mad = float(np.median(np.abs(positive - median_interval)))
    interval_cv = jitter_sd / mean_interval if mean_interval > 0 else np.nan
    instantaneous = 1.0 / positive
    observed_median_rate = 1.0 / median_interval
    observed_mean_rate = 1.0 / mean_interval
    observed_rate_sd = float(np.std(instantaneous, ddof=1)) if instantaneous.size > 1 else 0.0
    first_time = float(finite[0])
    last_time = float(finite[-1])
    duration = last_time - first_time
    span_rate = (n_finite - 1) / duration if duration > 0 else np.nan
    gap_threshold = gap_factor * median_interval
    large_gap_mask = positive > gap_threshold
    large_gap_count = int(np.sum(large_gap_mask))
    estimated_missing = int(np.sum(np.maximum(0.0, np.rint(positive / median_interval) - 1.0)))
    rate_error = (
        abs(observed_median_rate - nominal_rate_hz) / nominal_rate_hz if nominal_rate_hz is not None else np.nan
    )
    nominal_deviation_ppm = (
        (observed_median_rate / nominal_rate_hz - 1.0) * 1e6 if nominal_rate_hz is not None else np.nan
    )

    if n_nonfinite:
        issues.append("nonfinite_timestamps")
    if duplicate_count:
        issues.append("duplicate_timestamps")
    if backward_count:
        issues.append("backward_timestamps")
    if large_gap_count:
        issues.append("large_sampling_gaps")
    if np.isfinite(interval_cv) and interval_cv > jitter_warning_cv:
        issues.append("high_interval_jitter")
    if np.isfinite(rate_error) and rate_error > rate_tolerance_fraction:
        issues.append("nominal_rate_mismatch")

    status = "fail" if backward_count else ("warning" if issues else "pass")
    return GazepointTimebaseAudit(
        clock_id=clock_id,
        time_column=column,
        input_unit=unit,
        unit_source=unit_source,
        n_samples=n_samples,
        n_finite_samples=n_finite,
        n_nonfinite_timestamps=n_nonfinite,
        first_time_s=first_time,
        last_time_s=last_time,
        duration_s=_finite_or_none(duration),
        nominal_rate_hz=nominal_rate_hz,
        observed_median_rate_hz=observed_median_rate,
        observed_mean_rate_hz=observed_mean_rate,
        observed_span_rate_hz=_finite_or_none(span_rate),
        observed_rate_sd_hz=observed_rate_sd,
        min_instantaneous_rate_hz=float(np.min(instantaneous)),
        max_instantaneous_rate_hz=float(np.max(instantaneous)),
        median_interval_s=median_interval,
        mean_interval_s=mean_interval,
        interval_jitter_sd_s=jitter_sd,
        interval_jitter_mad_s=jitter_mad,
        interval_cv=_finite_or_none(interval_cv),
        n_duplicate_timestamps=duplicate_count,
        n_backward_timestamps=backward_count,
        n_large_gaps=large_gap_count,
        estimated_missing_samples=estimated_missing,
        nominal_rate_error_fraction=_finite_or_none(rate_error),
        nominal_rate_deviation_ppm=_finite_or_none(nominal_deviation_ppm),
        rate_evidence=rate_evidence,
        gap_factor=gap_factor,
        rate_tolerance_fraction=rate_tolerance_fraction,
        jitter_warning_cv=jitter_warning_cv,
        status=status,
        issues=tuple(issues),
        time_sha256=_hash_numeric(times),
    )


def _timebase_payload(audit: GazepointTimebaseAudit) -> dict:
    if not isinstance(audit, GazepointTimebaseAudit):
        raise TypeError("`audit` must be returned by audit_gazepoint_timebase().")
    return {
        "schema_version": audit.schema_version,
        "clock_id": audit.clock_id,
        "time_column": audit.time_column,
        "input_unit": audit.input_unit,
        "unit_source": audit.unit_source,
        "n_samples": audit.n_samples,
        "n_finite_samples": audit.n_finite_samples,
        "n_nonfinite_timestamps": audit.n_nonfinite_timestamps,
        "first_time_s": audit.first_time_s,
        "last_time_s": audit.last_time_s,
        "duration_s": audit.duration_s,
        "nominal_rate_hz": audit.nominal_rate_hz,
        "observed_median_rate_hz": audit.observed_median_rate_hz,
        "observed_mean_rate_hz": audit.observed_mean_rate_hz,
        "observed_span_rate_hz": audit.observed_span_rate_hz,
        "observed_rate_sd_hz": audit.observed_rate_sd_hz,
        "min_instantaneous_rate_hz": audit.min_instantaneous_rate_hz,
        "max_instantaneous_rate_hz": audit.max_instantaneous_rate_hz,
        "median_interval_s": audit.median_interval_s,
        "mean_interval_s": audit.mean_interval_s,
        "interval_jitter_sd_s": audit.interval_jitter_sd_s,
        "interval_jitter_mad_s": audit.interval_jitter_mad_s,
        "interval_cv": audit.interval_cv,
        "n_duplicate_timestamps": audit.n_duplicate_timestamps,
        "n_backward_timestamps": audit.n_backward_timestamps,
        "n_large_gaps": audit.n_large_gaps,
        "estimated_missing_samples": audit.estimated_missing_samples,
        "nominal_rate_error_fraction": audit.nominal_rate_error_fraction,
        "nominal_rate_deviation_ppm": audit.nominal_rate_deviation_ppm,
        "rate_evidence": audit.rate_evidence,
        "gap_factor": audit.gap_factor,
        "rate_tolerance_fraction": audit.rate_tolerance_fraction,
        "jitter_warning_cv": audit.jitter_warning_cv,
        "status": audit.status,
        "issues": list(audit.issues),
        "time_sha256": audit.time_sha256,
    }


def create_gazepoint_timebase_certificate(audit: GazepointTimebaseAudit) -> dict:
    payload = _timebase_payload(audit)
    return {"payload": payload, "sha256": _canonical_digest(payload)}


def validate_gazepoint_timebase_certificate(audit: GazepointTimebaseAudit, certificate) -> bool:
    if not isinstance(certificate, Mapping) or set(certificate) != {"payload", "sha256"}:
        return False
    try:
        expected = create_gazepoint_timebase_certificate(audit)
        supplied_payload = dict(certificate["payload"])
        supplied_digest = _canonical_digest(supplied_payload)
    except (TypeError, ValueError):
        return False
    return supplied_digest == certificate["sha256"] and supplied_payload == expected["payload"]


def fit_gazepoint_clock_alignment(
    reference,
    target,
    *,
    reference_time_col: str | None = None,
    target_time_col: str | None = None,
    reference_time_unit: str = "auto",
    target_time_unit: str = "auto",
    reference_nominal_rate_hz: float | None = None,
    target_nominal_rate_hz: float | None = None,
    reference_clock: str = "reference_clock",
    target_clock: str = "target_clock",
    method: str = "affine",
    max_pairs: int | None = None,
) -> GazepointClockAlignment:
    reference_clock = _validate_clock_id(reference_clock, "reference_clock")
    target_clock = _validate_clock_id(target_clock, "target_clock")
    if reference_clock == target_clock:
        raise ValueError("`reference_clock` and `target_clock` must identify distinct clocks.")
    if method not in _ALLOWED_ALIGNMENT_METHODS:
        raise ValueError("`method` must be 'affine' or 'offset'.")
    if reference_nominal_rate_hz is not None:
        reference_nominal_rate_hz = _validate_positive_number(reference_nominal_rate_hz, "reference_nominal_rate_hz")
    if target_nominal_rate_hz is not None:
        target_nominal_rate_hz = _validate_positive_number(target_nominal_rate_hz, "target_nominal_rate_hz")

    ref_raw, ref_column = _coerce_raw_time(reference, reference_time_col, name="reference")
    tar_raw, tar_column = _coerce_raw_time(target, target_time_col, name="target")
    ref_unit, ref_unit_source = _resolve_time_unit(
        ref_raw, reference_time_unit, ref_column, reference_nominal_rate_hz
    )
    tar_unit, tar_unit_source = _resolve_time_unit(
        tar_raw, target_time_unit, tar_column, target_nominal_rate_hz
    )
    ref = _to_seconds(ref_raw, ref_unit, reference_nominal_rate_hz)
    tar = _to_seconds(tar_raw, tar_unit, target_nominal_rate_hz)
    n_pairs = min(len(ref), len(tar))
    if max_pairs is not None:
        if int(max_pairs) != max_pairs or int(max_pairs) < 2:
            raise ValueError("`max_pairs` must be an integer of at least 2 when supplied.")
        n_pairs = min(n_pairs, int(max_pairs))
    if n_pairs < 2:
        raise ValueError("At least two matched timestamp anchors are required.")
    ref = np.asarray(ref[:n_pairs], dtype=float)
    tar = np.asarray(tar[:n_pairs], dtype=float)
    finite = np.isfinite(ref) & np.isfinite(tar)
    ref = ref[finite]
    tar = tar[finite]
    if ref.size < 2:
        raise ValueError("At least two finite matched timestamp anchors are required.")
    if float(np.ptp(ref)) <= 0:
        raise ValueError("Reference anchors must span more than one distinct time point.")

    if method == "offset":
        slope = 1.0
        intercept = float(np.median(tar - ref))
        estimator = "median_offset"
    else:
        design = np.column_stack([np.ones(ref.size), ref])
        intercept, slope = np.linalg.lstsq(design, tar, rcond=None)[0]
        intercept, slope = float(intercept), float(slope)
        estimator = "ordinary_least_squares"
    if not np.isfinite(slope) or slope <= 0:
        raise ValueError("Estimated clock slope must be finite and positive.")
    fitted = intercept + slope * ref
    residual = tar - fitted
    residual_mean = float(np.mean(residual))
    residual_sd = float(np.std(residual, ddof=1)) if residual.size > 1 else 0.0
    residual_max = float(np.max(np.abs(residual)))
    sst = float(np.sum((tar - np.mean(tar)) ** 2))
    r_squared = 1.0 - float(np.sum(residual**2)) / sst if sst > 0 else np.nan
    return GazepointClockAlignment(
        reference_clock=reference_clock,
        target_clock=target_clock,
        method=method,
        n_matched_anchors=int(ref.size),
        intercept_s=intercept,
        slope_target_per_reference=slope,
        drift_ppm=(slope - 1.0) * 1e6,
        residual_mean_s=residual_mean,
        residual_sd_s=residual_sd,
        residual_max_abs_s=residual_max,
        r_squared=_finite_or_none(r_squared),
        reference_anchor_sha256=_hash_numeric(ref),
        target_anchor_sha256=_hash_numeric(tar),
        reference_time_unit=ref_unit,
        target_time_unit=tar_unit,
        reference_unit_source=ref_unit_source,
        target_unit_source=tar_unit_source,
        anchor_match_method="row_order",
        estimator=estimator,
    )


def apply_gazepoint_clock_alignment(
    target_times,
    alignment: GazepointClockAlignment,
    *,
    time_unit: str = "seconds",
    nominal_rate_hz: float | None = None,
) -> np.ndarray:
    if not isinstance(alignment, GazepointClockAlignment):
        raise TypeError("`alignment` must be returned by fit_gazepoint_clock_alignment().")
    if nominal_rate_hz is not None:
        nominal_rate_hz = _validate_positive_number(nominal_rate_hz, "nominal_rate_hz")
    raw, column = _coerce_raw_time(target_times, None, name="target_times")
    resolved, _ = _resolve_time_unit(raw, time_unit, column, nominal_rate_hz)
    seconds = _to_seconds(raw, resolved, nominal_rate_hz)
    return (seconds - alignment.intercept_s) / alignment.slope_target_per_reference


def _alignment_payload(alignment: GazepointClockAlignment) -> dict:
    if not isinstance(alignment, GazepointClockAlignment):
        raise TypeError("`alignment` must be returned by fit_gazepoint_clock_alignment().")
    return {
        "schema_version": alignment.schema_version,
        "reference_clock": alignment.reference_clock,
        "target_clock": alignment.target_clock,
        "method": alignment.method,
        "n_matched_anchors": alignment.n_matched_anchors,
        "intercept_s": alignment.intercept_s,
        "slope_target_per_reference": alignment.slope_target_per_reference,
        "drift_ppm": alignment.drift_ppm,
        "residual_mean_s": alignment.residual_mean_s,
        "residual_sd_s": alignment.residual_sd_s,
        "residual_max_abs_s": alignment.residual_max_abs_s,
        "r_squared": alignment.r_squared,
        "reference_anchor_sha256": alignment.reference_anchor_sha256,
        "target_anchor_sha256": alignment.target_anchor_sha256,
        "reference_time_unit": alignment.reference_time_unit,
        "target_time_unit": alignment.target_time_unit,
        "reference_unit_source": alignment.reference_unit_source,
        "target_unit_source": alignment.target_unit_source,
        "anchor_match_method": alignment.anchor_match_method,
        "estimator": alignment.estimator,
    }


def create_gazepoint_multimodal_alignment_certificate(
    reference_audit: GazepointTimebaseAudit,
    target_audit: GazepointTimebaseAudit,
    alignment: GazepointClockAlignment,
    *,
    tolerance_s: float,
    allow_timebase_warnings: bool = False,
    resampling_operation: str = "none",
) -> dict:
    if not isinstance(reference_audit, GazepointTimebaseAudit) or not isinstance(target_audit, GazepointTimebaseAudit):
        raise TypeError("`reference_audit` and `target_audit` must be GazepointTimebaseAudit objects.")
    if not isinstance(alignment, GazepointClockAlignment):
        raise TypeError("`alignment` must be returned by fit_gazepoint_clock_alignment().")
    tolerance_s = _validate_positive_number(tolerance_s, "tolerance_s", allow_zero=True)
    resampling_operation = str(resampling_operation).strip()
    if not resampling_operation:
        raise ValueError("`resampling_operation` must be a non-empty description.")
    if reference_audit.clock_id != alignment.reference_clock:
        raise ValueError("Reference audit clock does not match the alignment reference clock.")
    if target_audit.clock_id != alignment.target_clock:
        raise ValueError("Target audit clock does not match the alignment target clock.")
    if reference_audit.status == "fail" or target_audit.status == "fail":
        raise ValueError("Cannot certify alignment when a timebase audit has failed.")
    alignment_warnings = []
    if alignment.reference_unit_source == "interval_heuristic":
        alignment_warnings.append("alignment_reference_unit_heuristic")
    if alignment.target_unit_source == "interval_heuristic":
        alignment_warnings.append("alignment_target_unit_heuristic")
    warnings = tuple(
        dict.fromkeys([*reference_audit.issues, *target_audit.issues, *alignment_warnings])
    )
    if warnings and not allow_timebase_warnings:
        raise ValueError("Timebase warnings must be resolved or explicitly allowed before alignment certification.")
    if alignment.residual_max_abs_s > tolerance_s:
        raise ValueError("Alignment residual exceeds the requested certification tolerance.")

    reference_start = min(reference_audit.first_time_s, reference_audit.last_time_s)
    reference_end = max(reference_audit.first_time_s, reference_audit.last_time_s)
    target_bounds = apply_gazepoint_clock_alignment(
        [target_audit.first_time_s, target_audit.last_time_s], alignment, time_unit="seconds"
    )
    target_start = float(np.min(target_bounds))
    target_end = float(np.max(target_bounds))
    overlap_start = max(reference_start, target_start)
    overlap_end = min(reference_end, target_end)
    overlap_duration = max(0.0, overlap_end - overlap_start)
    correction_applied = not (
        np.isclose(alignment.intercept_s, 0.0, atol=1e-15, rtol=0.0)
        and np.isclose(alignment.slope_target_per_reference, 1.0, atol=1e-15, rtol=0.0)
    )
    payload = {
        "schema_version": _ALIGNMENT_SCHEMA_VERSION,
        "status": "certified_with_warnings" if warnings else "certified",
        "reference_clock": reference_audit.clock_id,
        "target_clock": target_audit.clock_id,
        "reference_timebase_sha256": create_gazepoint_timebase_certificate(reference_audit)["sha256"],
        "target_timebase_sha256": create_gazepoint_timebase_certificate(target_audit)["sha256"],
        "alignment": _alignment_payload(alignment),
        "alignment_reference": reference_audit.clock_id,
        "alignment_method": alignment.method,
        "correction_applied": correction_applied,
        "correction_equation": "reference_time_s=(target_time_s-intercept_s)/slope_target_per_reference",
        "resampling_operation": resampling_operation,
        "tolerance_s": tolerance_s,
        "overlap_start_s": overlap_start,
        "overlap_end_s": overlap_end,
        "overlap_duration_s": overlap_duration,
        "allow_timebase_warnings": bool(allow_timebase_warnings),
        "timebase_warnings": list(warnings),
    }
    return {"payload": payload, "sha256": _canonical_digest(payload)}


def validate_gazepoint_multimodal_alignment_certificate(
    reference_audit: GazepointTimebaseAudit,
    target_audit: GazepointTimebaseAudit,
    alignment: GazepointClockAlignment,
    certificate,
    *,
    max_tolerance_s: float | None = None,
) -> bool:
    if not isinstance(certificate, Mapping) or set(certificate) != {"payload", "sha256"}:
        return False
    try:
        supplied_payload = dict(certificate["payload"])
        tolerance = float(supplied_payload["tolerance_s"])
        allow_warnings = bool(supplied_payload["allow_timebase_warnings"])
        resampling_operation = str(supplied_payload["resampling_operation"])
        if max_tolerance_s is not None:
            max_tolerance_s = _validate_positive_number(max_tolerance_s, "max_tolerance_s", allow_zero=True)
            if tolerance > max_tolerance_s:
                return False
        expected = create_gazepoint_multimodal_alignment_certificate(
            reference_audit,
            target_audit,
            alignment,
            tolerance_s=tolerance,
            allow_timebase_warnings=allow_warnings,
            resampling_operation=resampling_operation,
        )
        supplied_digest = _canonical_digest(supplied_payload)
    except (KeyError, TypeError, ValueError):
        return False
    return supplied_digest == certificate["sha256"] and supplied_payload == expected["payload"]


def assert_gazepoint_multimodal_fusion_ready(
    reference_audit: GazepointTimebaseAudit,
    target_audit: GazepointTimebaseAudit,
    alignment: GazepointClockAlignment,
    certificate,
    *,
    max_tolerance_s: float | None = None,
) -> bool:
    if not validate_gazepoint_multimodal_alignment_certificate(
        reference_audit,
        target_audit,
        alignment,
        certificate,
        max_tolerance_s=max_tolerance_s,
    ):
        raise ValueError("A valid multimodal alignment certificate is required before fusion.")
    return True
