from __future__ import annotations

from dataclasses import FrozenInstanceError
import copy

import pytest

from gpbiometricspy import cardiac_provenance as cp


def test_ecg_nn_clean_source_supports_hrv_and_is_immutable():
    p = cp.declare_cardiac_variability_source(
        "ecg_nn_intervals",
        source_id="ecg_chest",
        site="chest",
        interval_unit="ms",
        sampling_rate_hz=1000,
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    assert p.modality == "ecg"
    assert p.variability_term == "HRV"
    assert p.status == "supported"
    assert p.warnings == ()
    assert p.beat_level is True
    assert cp.assert_cardiac_operation_supported(p, "hrv_features")
    assert cp.assert_cardiac_operation_supported(p, "beat_level_export")
    with pytest.raises(FrozenInstanceError):
        p.status = "x"


def test_ecg_nn_missing_processing_provenance_warns():
    p = cp.declare_cardiac_variability_source("ecg_nn_intervals", interval_unit="ms")
    assert p.status == "supported_with_warnings"
    assert p.warnings == (
        "beat_detection_provenance_undisclosed",
        "normal_beat_artifact_handling_undisclosed",
    )


def test_ecg_rr_is_not_silently_promoted_to_nn_hrv():
    p = cp.declare_cardiac_variability_source(
        "ecg_rr_intervals",
        interval_unit="ms",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    assert p.variability_term == "RR variability"
    assert "rr_not_nn_without_normal_beat_processing" in p.warnings
    assert "label_uncleaned_rr_as_nn_hrv" in p.prohibited_claims
    assert cp.assert_cardiac_operation_supported(p, "rr_variability_features")
    with pytest.raises(ValueError, match="not scientifically supported"):
        cp.assert_cardiac_operation_supported(p, "hrv_features")


def test_ppg_intervals_are_prv_not_ecg_hrv():
    p = cp.declare_cardiac_variability_source(
        "ppg_pulse_intervals",
        source_id="finger_ppg",
        site="finger",
        interval_unit="s",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    assert p.modality == "ppg"
    assert p.interval_unit == "s"
    assert p.variability_term == "PRV"
    assert p.warnings == ("prv_not_interchangeable_with_ecg_hrv_without_metric_validation",)
    assert cp.assert_cardiac_operation_supported(p, "prv_features")
    with pytest.raises(ValueError, match="not scientifically supported"):
        cp.assert_cardiac_operation_supported(p, "hrv_features")


def test_device_intervals_remain_generic_and_retain_unknown_modality_warning():
    p = cp.declare_cardiac_variability_source(
        "device_intervals_unspecified",
        interval_unit="ms",
        vendor="WearableCo",
    )
    assert p.modality == "unknown"
    assert p.canonical_label == "Device-reported beat intervals"
    assert p.status == "supported_with_warnings"
    assert set(p.warnings) == {
        "interval_origin_not_verified",
        "vendor_interval_semantics_require_documentation",
        "measurement_modality_unknown",
        "interval_generation_algorithm_undisclosed",
    }
    assert cp.assert_cardiac_operation_supported(p, "interval_variability_features")
    with pytest.raises(ValueError):
        cp.assert_cardiac_operation_supported(p, "prv_features")


def test_device_metric_is_metric_only_and_restricted():
    p = cp.declare_cardiac_variability_source(
        "device_variability_metric",
        source_id="watch_rmssd",
        modality="ppg",
        metric_name="RMSSD",
        vendor="WearableCo",
        algorithm_disclosed=False,
    )
    assert p.measurement_level == "precomputed_metric"
    assert p.beat_level is False
    assert p.status == "restricted"
    assert "vendor_metric_algorithm_undisclosed" in p.warnings
    assert cp.assert_cardiac_operation_supported(p, "report_vendor_metric")
    with pytest.raises(ValueError):
        cp.assert_cardiac_operation_supported(p, "beat_level_export")


def test_sampled_hr_series_cannot_be_promoted_to_hrv_or_prv():
    p = cp.declare_cardiac_variability_source(
        "heart_rate_series",
        source_id="wearable_hr_1min",
        modality="ppg",
        sampling_rate_hz=1 / 60,
    )
    assert p.measurement_level == "sampled_heart_rate"
    assert p.status == "restricted"
    assert "resampling_cannot_recover_beat_to_beat_variability" in p.warnings
    assert "reconstruct_rr_nn_ppi_from_sampled_hr" in p.prohibited_claims
    assert cp.assert_cardiac_operation_supported(p, "heart_rate_summary")
    with pytest.raises(ValueError):
        cp.assert_cardiac_operation_supported(p, "prv_features")


def test_source_validation_rejects_invalid_combinations_and_types():
    with pytest.raises(ValueError, match="source_id"):
        cp.declare_cardiac_variability_source("ecg_nn_intervals", source_id=" ", interval_unit="ms")
    with pytest.raises(ValueError, match="source_type"):
        cp.declare_cardiac_variability_source("mystery")
    with pytest.raises(ValueError, match="modality"):
        cp.declare_cardiac_variability_source("device_intervals_unspecified", modality="laser")
    with pytest.raises(ValueError, match="requires modality"):
        cp.declare_cardiac_variability_source("ppg_pulse_intervals", modality="ecg")
    with pytest.raises(ValueError, match="supplied explicitly"):
        cp.declare_cardiac_variability_source("ecg_nn_intervals")
    with pytest.raises(ValueError, match="interval_unit"):
        cp.declare_cardiac_variability_source("ecg_nn_intervals", interval_unit="ticks")
    with pytest.raises(ValueError, match="only valid for beat-interval"):
        cp.declare_cardiac_variability_source("heart_rate_series", interval_unit="ms")
    with pytest.raises(ValueError, match="metric_name"):
        cp.declare_cardiac_variability_source("device_variability_metric")
    with pytest.raises(ValueError, match="only valid"):
        cp.declare_cardiac_variability_source("ecg_nn_intervals", interval_unit="ms", metric_name="RMSSD")
    with pytest.raises(ValueError, match="sampling_rate_hz"):
        cp.declare_cardiac_variability_source("heart_rate_series", sampling_rate_hz=0)
    with pytest.raises(ValueError, match="site"):
        cp.declare_cardiac_variability_source("ecg_nn_intervals", interval_unit="ms", site=" ")
    with pytest.raises(ValueError, match="vendor"):
        cp.declare_cardiac_variability_source("device_intervals_unspecified", interval_unit="ms", vendor=" ")
    with pytest.raises(TypeError, match="algorithm_disclosed"):
        cp.declare_cardiac_variability_source(
            "device_intervals_unspecified",
            interval_unit="ms",
            algorithm_disclosed="yes",
        )
    with pytest.raises(TypeError, match="beat_detection_disclosed"):
        cp.declare_cardiac_variability_source(
            "ecg_nn_intervals",
            interval_unit="ms",
            beat_detection_disclosed=1,
        )
    with pytest.raises(TypeError, match="artifact_handling_disclosed"):
        cp.declare_cardiac_variability_source(
            "ecg_nn_intervals",
            interval_unit="ms",
            artifact_handling_disclosed=1,
        )


def test_fixed_modality_defaults_and_optional_disclosure_branches():
    rr = cp.declare_cardiac_variability_source("ecg_rr_intervals", interval_unit="ms")
    assert rr.modality == "ecg"
    assert "beat_detection_provenance_undisclosed" in rr.warnings
    assert "ectopic_artifact_handling_undisclosed" in rr.warnings

    ppg = cp.declare_cardiac_variability_source("ppg_pulse_intervals", interval_unit="ms")
    assert ppg.modality == "ppg"
    assert "pulse_detection_provenance_undisclosed" in ppg.warnings
    assert "pulse_interval_artifact_handling_undisclosed" in ppg.warnings

    generic = cp.declare_cardiac_variability_source(
        "device_intervals_unspecified",
        interval_unit="ms",
        modality="other",
        algorithm_disclosed=True,
    )
    assert "measurement_modality_unknown" not in generic.warnings
    assert "interval_generation_algorithm_undisclosed" not in generic.warnings

    metric = cp.declare_cardiac_variability_source(
        "device_variability_metric",
        metric_name="SDNN",
        algorithm_disclosed=True,
    )
    assert "vendor_metric_algorithm_undisclosed" not in metric.warnings


def test_certificate_determinism_reordering_and_tamper_detection():
    p = cp.declare_cardiac_variability_source(
        "ecg_nn_intervals",
        interval_unit="ms",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    cert = cp.create_cardiac_provenance_certificate(p)
    assert cert == cp.create_cardiac_provenance_certificate(p)
    assert cp.validate_cardiac_provenance_certificate(p, cert)
    reordered = {"sha256": cert["sha256"], "payload": dict(reversed(list(cert["payload"].items())))}
    assert cp.validate_cardiac_provenance_certificate(p, reordered)
    tampered = copy.deepcopy(cert)
    tampered["payload"]["variability_term"] = "PRV"
    assert not cp.validate_cardiac_provenance_certificate(p, tampered)
    tampered_digest = copy.deepcopy(cert)
    tampered_digest["sha256"] = "0" * 64
    assert not cp.validate_cardiac_provenance_certificate(p, tampered_digest)
    assert not cp.validate_cardiac_provenance_certificate(p, {})
    assert not cp.validate_cardiac_provenance_certificate(p, {"payload": [], "sha256": "x"})
    assert not cp.validate_cardiac_provenance_certificate(object(), cert)
    with pytest.raises(TypeError):
        cp.create_cardiac_provenance_certificate(object())


def test_operation_guard_rejects_unknown_or_malformed_operations_and_provenance():
    p = cp.declare_cardiac_variability_source("heart_rate_series")
    with pytest.raises(TypeError):
        cp.assert_cardiac_operation_supported(object(), "heart_rate_summary")
    with pytest.raises(ValueError, match="operation"):
        cp.assert_cardiac_operation_supported(p, " ")
    with pytest.raises(ValueError, match="Unknown cardiac operation"):
        cp.assert_cardiac_operation_supported(p, "invented")


def test_metric_comparison_binds_source_certificates_and_stays_metric_specific():
    ecg = cp.declare_cardiac_variability_source(
        "ecg_nn_intervals",
        source_id="ecg",
        interval_unit="ms",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    ppg = cp.declare_cardiac_variability_source(
        "ppg_pulse_intervals",
        source_id="ppg",
        interval_unit="ms",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    out = cp.audit_cardiac_metric_comparison(ecg, ppg, metric="RMSSD")
    assert out["metric"] == "RMSSD"
    assert out["comparison_scope"] == "metric_specific_only"
    assert out["global_interchangeability_supported"] is False
    assert len(out["reference_provenance_sha256"]) == 64
    assert len(out["candidate_provenance_sha256"]) == 64


def test_device_metric_comparison_requires_exact_metric_identity_case_insensitive():
    ref = cp.declare_cardiac_variability_source(
        "device_variability_metric",
        metric_name="RMSSD",
        source_id="watch",
    )
    candidate = cp.declare_cardiac_variability_source(
        "ecg_nn_intervals",
        source_id="ecg",
        interval_unit="ms",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    out = cp.audit_cardiac_metric_comparison(ref, candidate, metric="rmssd")
    assert out["reference_label"] == "Device-reported variability metric"
    with pytest.raises(ValueError, match="does not match"):
        cp.audit_cardiac_metric_comparison(ref, candidate, metric="SDNN")


def test_metric_comparison_validates_inputs_and_both_source_capabilities():
    ecg = cp.declare_cardiac_variability_source(
        "ecg_nn_intervals",
        interval_unit="ms",
        beat_detection_disclosed=True,
        artifact_handling_disclosed=True,
    )
    with pytest.raises(ValueError, match="metric"):
        cp.audit_cardiac_metric_comparison(ecg, ecg, metric=" ")
    bad = cp.CardiacVariabilityProvenance(
        source_id="bad",
        source_type="ecg_nn_intervals",
        modality="ecg",
        measurement_level="beat_interval",
        canonical_label="x",
        variability_term="HRV",
        beat_level=True,
        site=None,
        interval_unit="ms",
        sampling_rate_hz=None,
        metric_name=None,
        vendor=None,
        algorithm_disclosed=None,
        beat_detection_disclosed=None,
        artifact_handling_disclosed=None,
        allowed_operations=(),
        warnings=(),
        prohibited_claims=(),
        status="supported",
    )
    with pytest.raises(ValueError, match="not scientifically supported"):
        cp.audit_cardiac_metric_comparison(ecg, bad, metric="RMSSD")


def test_private_helpers_cover_none_and_nonfinite_numeric_cases():
    assert cp._nonempty_string(None, "x", allow_none=True) is None
    assert cp._optional_bool(None, "x") is None
    assert cp._positive_optional(None, "x") is None
    with pytest.raises(ValueError, match="finite positive"):
        cp._positive_optional(float("inf"), "x")
