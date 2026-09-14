from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping
import json

_SCHEMA_VERSION = "gpbiometricspy-cardiac-source-provenance-v1"
_SOURCE_TYPES = {
    "ecg_nn_intervals",
    "ecg_rr_intervals",
    "ppg_pulse_intervals",
    "device_intervals_unspecified",
    "device_variability_metric",
    "heart_rate_series",
}
_MODALITIES = {"ecg", "ppg", "other", "unknown"}
_INTERVAL_UNITS = {"ms", "s"}
_OPERATIONS = {
    "interval_qc",
    "interval_variability_features",
    "hrv_features",
    "rr_variability_features",
    "prv_features",
    "metric_specific_agreement",
    "beat_level_export",
    "report_vendor_metric",
    "heart_rate_summary",
}


def _nonempty_string(value, name: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{name}` must be a non-empty string.")
    return value.strip()


def _optional_bool(value, name: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise TypeError(f"`{name}` must be True, False, or None.")


def _positive_optional(value, name: str) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not (number > 0 and number < float("inf")):
        raise ValueError(f"`{name}` must be a finite positive number when supplied.")
    return number


def _canonical_digest(payload: Mapping) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CardiacVariabilityProvenance:
    source_id: str
    source_type: str
    modality: str
    measurement_level: str
    canonical_label: str
    variability_term: str
    beat_level: bool
    site: str | None
    interval_unit: str | None
    sampling_rate_hz: float | None
    metric_name: str | None
    vendor: str | None
    algorithm_disclosed: bool | None
    beat_detection_disclosed: bool | None
    artifact_handling_disclosed: bool | None
    allowed_operations: tuple[str, ...]
    warnings: tuple[str, ...]
    prohibited_claims: tuple[str, ...]
    status: str
    schema_version: str = _SCHEMA_VERSION


def declare_cardiac_variability_source(
    source_type: str,
    *,
    source_id: str = "cardiac_source",
    modality: str | None = None,
    site: str | None = None,
    interval_unit: str | None = None,
    sampling_rate_hz: float | None = None,
    metric_name: str | None = None,
    vendor: str | None = None,
    algorithm_disclosed: bool | None = None,
    beat_detection_disclosed: bool | None = None,
    artifact_handling_disclosed: bool | None = None,
) -> CardiacVariabilityProvenance:
    """Declare the scientific provenance of a cardiac-variability input.

    The function is intentionally declarative rather than inferential: it does
    not guess ECG/PPG origin from column names or convert sampled heart-rate
    series into beat-to-beat intervals.
    """
    source_id = _nonempty_string(source_id, "source_id")
    source_type = _nonempty_string(source_type, "source_type")
    if source_type not in _SOURCE_TYPES:
        raise ValueError(f"`source_type` must be one of {sorted(_SOURCE_TYPES)}.")
    site = _nonempty_string(site, "site", allow_none=True)
    metric_name = _nonempty_string(metric_name, "metric_name", allow_none=True)
    vendor = _nonempty_string(vendor, "vendor", allow_none=True)
    sampling_rate_hz = _positive_optional(sampling_rate_hz, "sampling_rate_hz")
    algorithm_disclosed = _optional_bool(algorithm_disclosed, "algorithm_disclosed")
    beat_detection_disclosed = _optional_bool(beat_detection_disclosed, "beat_detection_disclosed")
    artifact_handling_disclosed = _optional_bool(artifact_handling_disclosed, "artifact_handling_disclosed")

    fixed_modality = {
        "ecg_nn_intervals": "ecg",
        "ecg_rr_intervals": "ecg",
        "ppg_pulse_intervals": "ppg",
    }.get(source_type)
    if modality is None:
        modality = fixed_modality or "unknown"
    else:
        modality = _nonempty_string(modality, "modality").lower()
        if modality not in _MODALITIES:
            raise ValueError(f"`modality` must be one of {sorted(_MODALITIES)}.")
        if fixed_modality is not None and modality != fixed_modality:
            raise ValueError(f"`source_type={source_type}` requires modality `{fixed_modality}`.")

    interval_source = source_type in {
        "ecg_nn_intervals",
        "ecg_rr_intervals",
        "ppg_pulse_intervals",
        "device_intervals_unspecified",
    }
    if interval_source:
        if interval_unit is None:
            raise ValueError("`interval_unit` must be supplied explicitly for beat-interval sources.")
        interval_unit = _nonempty_string(interval_unit, "interval_unit").lower()
        if interval_unit not in _INTERVAL_UNITS:
            raise ValueError("`interval_unit` must be 'ms' or 's' for interval sources.")
    elif interval_unit is not None:
        raise ValueError("`interval_unit` is only valid for beat-interval sources.")

    if source_type == "device_variability_metric" and metric_name is None:
        raise ValueError("`metric_name` is required for a device-reported variability metric.")
    if source_type != "device_variability_metric" and metric_name is not None:
        raise ValueError("`metric_name` is only valid for `device_variability_metric`.")

    common_prohibited = (
        "sensor_validity_from_variability_alone",
        "causal_inference_from_variability_alone",
    )
    warnings: list[str] = []

    if source_type == "ecg_nn_intervals":
        measurement_level = "beat_interval"
        canonical_label = "ECG-NN intervals"
        variability_term = "HRV"
        beat_level = True
        allowed = (
            "interval_qc",
            "interval_variability_features",
            "hrv_features",
            "metric_specific_agreement",
            "beat_level_export",
        )
        if beat_detection_disclosed is not True:
            warnings.append("beat_detection_provenance_undisclosed")
        if artifact_handling_disclosed is not True:
            warnings.append("normal_beat_artifact_handling_undisclosed")
        prohibited = common_prohibited
    elif source_type == "ecg_rr_intervals":
        measurement_level = "beat_interval"
        canonical_label = "ECG-RR intervals"
        variability_term = "RR variability"
        beat_level = True
        allowed = (
            "interval_qc",
            "interval_variability_features",
            "rr_variability_features",
            "metric_specific_agreement",
            "beat_level_export",
        )
        warnings.append("rr_not_nn_without_normal_beat_processing")
        if beat_detection_disclosed is not True:
            warnings.append("beat_detection_provenance_undisclosed")
        if artifact_handling_disclosed is not True:
            warnings.append("ectopic_artifact_handling_undisclosed")
        prohibited = common_prohibited + ("label_uncleaned_rr_as_nn_hrv",)
    elif source_type == "ppg_pulse_intervals":
        measurement_level = "beat_interval"
        canonical_label = "PPG pulse-to-pulse intervals"
        variability_term = "PRV"
        beat_level = True
        allowed = (
            "interval_qc",
            "interval_variability_features",
            "prv_features",
            "metric_specific_agreement",
            "beat_level_export",
        )
        warnings.append("prv_not_interchangeable_with_ecg_hrv_without_metric_validation")
        if beat_detection_disclosed is not True:
            warnings.append("pulse_detection_provenance_undisclosed")
        if artifact_handling_disclosed is not True:
            warnings.append("pulse_interval_artifact_handling_undisclosed")
        prohibited = common_prohibited + ("label_ppg_prv_as_ecg_hrv_without_validation",)
    elif source_type == "device_intervals_unspecified":
        measurement_level = "beat_interval"
        canonical_label = "Device-reported beat intervals"
        variability_term = "interval variability"
        beat_level = True
        allowed = (
            "interval_qc",
            "interval_variability_features",
            "metric_specific_agreement",
            "beat_level_export",
        )
        warnings.extend(("interval_origin_not_verified", "vendor_interval_semantics_require_documentation"))
        if modality == "unknown":
            warnings.append("measurement_modality_unknown")
        if algorithm_disclosed is not True:
            warnings.append("interval_generation_algorithm_undisclosed")
        prohibited = common_prohibited + (
            "label_unspecified_intervals_as_ecg_hrv",
            "label_unspecified_intervals_as_ppg_prv",
        )
    elif source_type == "device_variability_metric":
        measurement_level = "precomputed_metric"
        canonical_label = "Device-reported variability metric"
        variability_term = "vendor metric"
        beat_level = False
        allowed = ("metric_specific_agreement", "report_vendor_metric")
        warnings.append("precomputed_metric_has_no_beat_level_lineage")
        if algorithm_disclosed is not True:
            warnings.append("vendor_metric_algorithm_undisclosed")
        prohibited = common_prohibited + (
            "recompute_beat_level_hrv_from_metric",
            "infer_hidden_vendor_algorithm",
            "treat_precomputed_metric_as_intervals",
        )
    else:
        measurement_level = "sampled_heart_rate"
        canonical_label = "Sampled heart-rate series"
        variability_term = "heart-rate series variability"
        beat_level = False
        allowed = ("heart_rate_summary",)
        warnings.extend((
            "sampled_hr_not_beat_intervals",
            "resampling_cannot_recover_beat_to_beat_variability",
        ))
        prohibited = common_prohibited + (
            "reconstruct_rr_nn_ppi_from_sampled_hr",
            "label_sampled_hr_variability_as_hrv_or_prv",
        )

    if source_type in {"device_variability_metric", "heart_rate_series"}:
        status = "restricted"
    elif warnings:
        status = "supported_with_warnings"
    else:
        status = "supported"

    return CardiacVariabilityProvenance(
        source_id=source_id,
        source_type=source_type,
        modality=modality,
        measurement_level=measurement_level,
        canonical_label=canonical_label,
        variability_term=variability_term,
        beat_level=beat_level,
        site=site,
        interval_unit=interval_unit,
        sampling_rate_hz=sampling_rate_hz,
        metric_name=metric_name,
        vendor=vendor,
        algorithm_disclosed=algorithm_disclosed,
        beat_detection_disclosed=beat_detection_disclosed,
        artifact_handling_disclosed=artifact_handling_disclosed,
        allowed_operations=allowed,
        warnings=tuple(warnings),
        prohibited_claims=prohibited,
        status=status,
    )


def _payload(provenance: CardiacVariabilityProvenance) -> dict:
    if not isinstance(provenance, CardiacVariabilityProvenance):
        raise TypeError("`provenance` must be returned by declare_cardiac_variability_source().")
    return {
        "schema_version": provenance.schema_version,
        "source_id": provenance.source_id,
        "source_type": provenance.source_type,
        "modality": provenance.modality,
        "measurement_level": provenance.measurement_level,
        "canonical_label": provenance.canonical_label,
        "variability_term": provenance.variability_term,
        "beat_level": provenance.beat_level,
        "site": provenance.site,
        "interval_unit": provenance.interval_unit,
        "sampling_rate_hz": provenance.sampling_rate_hz,
        "metric_name": provenance.metric_name,
        "vendor": provenance.vendor,
        "algorithm_disclosed": provenance.algorithm_disclosed,
        "beat_detection_disclosed": provenance.beat_detection_disclosed,
        "artifact_handling_disclosed": provenance.artifact_handling_disclosed,
        "allowed_operations": list(provenance.allowed_operations),
        "warnings": list(provenance.warnings),
        "prohibited_claims": list(provenance.prohibited_claims),
        "status": provenance.status,
    }


def create_cardiac_provenance_certificate(provenance: CardiacVariabilityProvenance) -> dict:
    payload = _payload(provenance)
    return {"payload": payload, "sha256": _canonical_digest(payload)}


def validate_cardiac_provenance_certificate(provenance: CardiacVariabilityProvenance, certificate) -> bool:
    if not isinstance(certificate, Mapping) or set(certificate) != {"payload", "sha256"}:
        return False
    try:
        supplied_payload = dict(certificate["payload"])
        expected = create_cardiac_provenance_certificate(provenance)
        supplied_digest = _canonical_digest(supplied_payload)
    except (TypeError, ValueError):
        return False
    return supplied_payload == expected["payload"] and supplied_digest == certificate["sha256"]


def assert_cardiac_operation_supported(
    provenance: CardiacVariabilityProvenance,
    operation: str,
) -> bool:
    if not isinstance(provenance, CardiacVariabilityProvenance):
        raise TypeError("`provenance` must be returned by declare_cardiac_variability_source().")
    operation = _nonempty_string(operation, "operation")
    if operation not in _OPERATIONS:
        raise ValueError(f"Unknown cardiac operation `{operation}`.")
    if operation not in provenance.allowed_operations:
        raise ValueError(
            f"Operation `{operation}` is not scientifically supported for source type "
            f"`{provenance.source_type}`."
        )
    return True


def audit_cardiac_metric_comparison(
    reference: CardiacVariabilityProvenance,
    candidate: CardiacVariabilityProvenance,
    *,
    metric: str,
) -> dict:
    metric = _nonempty_string(metric, "metric")
    assert_cardiac_operation_supported(reference, "metric_specific_agreement")
    assert_cardiac_operation_supported(candidate, "metric_specific_agreement")
    for provenance in (reference, candidate):
        if provenance.source_type == "device_variability_metric":
            if provenance.metric_name.casefold() != metric.casefold():
                raise ValueError(
                    f"Device metric `{provenance.metric_name}` does not match requested comparison metric `{metric}`."
                )
    reference_certificate = create_cardiac_provenance_certificate(reference)
    candidate_certificate = create_cardiac_provenance_certificate(candidate)
    return {
        "metric": metric,
        "comparison_scope": "metric_specific_only",
        "reference_source_id": reference.source_id,
        "candidate_source_id": candidate.source_id,
        "reference_provenance_sha256": reference_certificate["sha256"],
        "candidate_provenance_sha256": candidate_certificate["sha256"],
        "reference_label": reference.canonical_label,
        "candidate_label": candidate.canonical_label,
        "global_interchangeability_supported": False,
        "interpretation": (
            "This provenance check supports only a named metric comparison. It does not establish "
            "global interchangeability between acquisition modalities or devices."
        ),
    }


__all__ = [
    "CardiacVariabilityProvenance",
    "declare_cardiac_variability_source",
    "create_cardiac_provenance_certificate",
    "validate_cardiac_provenance_certificate",
    "assert_cardiac_operation_supported",
    "audit_cardiac_metric_comparison",
]
