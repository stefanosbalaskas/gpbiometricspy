from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import copy

import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import timebase_provenance as tb


def clean_audits():
    reference = np.arange(0.0, 10.0, 0.1)
    target = 0.25 + 1.001 * reference
    reference_audit = tb.audit_gazepoint_timebase(
        reference,
        time_unit="seconds",
        nominal_rate_hz=10.0,
        clock_id="reference",
    )
    target_audit = tb.audit_gazepoint_timebase(
        target,
        time_unit="seconds",
        nominal_rate_hz=10.0,
        clock_id="target",
    )
    alignment = tb.fit_gazepoint_clock_alignment(
        reference[::10],
        target[::10],
        reference_time_unit="seconds",
        target_time_unit="seconds",
        reference_clock="reference",
        target_clock="target",
    )
    return reference, target, reference_audit, target_audit, alignment


def test_clean_seconds_audit_metrics_and_immutability():
    times = np.arange(0.0, 1.0, 0.1)
    audit = tb.audit_gazepoint_timebase(
        times,
        time_unit="seconds",
        nominal_rate_hz=10.0,
        clock_id="sensor-A",
    )
    assert audit.status == "pass"
    assert audit.issues == ()
    assert audit.input_unit == "seconds"
    assert audit.unit_source == "explicit"
    assert audit.n_samples == audit.n_finite_samples == 10
    assert audit.n_nonfinite_timestamps == 0
    assert audit.first_time_s == pytest.approx(0.0)
    assert audit.last_time_s == pytest.approx(0.9)
    assert audit.duration_s == pytest.approx(0.9)
    assert audit.observed_median_rate_hz == pytest.approx(10.0)
    assert audit.observed_mean_rate_hz == pytest.approx(10.0)
    assert audit.observed_span_rate_hz == pytest.approx(10.0)
    assert audit.observed_rate_sd_hz >= 0
    assert audit.min_instantaneous_rate_hz == pytest.approx(10.0)
    assert audit.max_instantaneous_rate_hz == pytest.approx(10.0)
    assert audit.median_interval_s == pytest.approx(0.1)
    assert audit.mean_interval_s == pytest.approx(0.1)
    assert audit.interval_jitter_sd_s >= 0
    assert audit.interval_jitter_mad_s >= 0
    assert audit.interval_cv >= 0
    assert audit.estimated_missing_samples == 0
    assert audit.nominal_rate_error_fraction == pytest.approx(0.0)
    assert abs(audit.nominal_rate_deviation_ppm) < 1e-8
    assert len(audit.time_sha256) == 64
    with pytest.raises(FrozenInstanceError):
        audit.status = "warning"


def test_dataframe_auto_unit_resolution_for_seconds_milliseconds_and_samples():
    sec = pd.DataFrame({"time_s": [0.0, 0.1, 0.2, 0.3]})
    sec_audit = tb.audit_gazepoint_timebase(sec, clock_id="sec")
    assert sec_audit.input_unit == "seconds" and sec_audit.unit_source == "column_name"
    assert sec_audit.rate_evidence == "timestamp_observed"

    ms = pd.DataFrame({"MSTIMER": [0, 100, 200, 300]})
    ms_audit = tb.audit_gazepoint_timebase(ms, clock_id="ms")
    assert ms_audit.input_unit == "milliseconds" and ms_audit.observed_median_rate_hz == pytest.approx(10)

    samples = pd.DataFrame({"CNT": [0, 1, 2, 3]})
    sample_audit = tb.audit_gazepoint_timebase(samples, nominal_rate_hz=50, clock_id="cnt")
    assert sample_audit.input_unit == "samples" and sample_audit.observed_median_rate_hz == pytest.approx(50)
    assert sample_audit.status == "warning"
    assert sample_audit.issues == ("counter_scaled_timebase",)
    assert sample_audit.rate_evidence == "counter_scaled_by_nominal_rate"

    generic_ms = tb.audit_gazepoint_timebase([0, 10, 20, 30], clock_id="heuristic")
    assert generic_ms.input_unit == "milliseconds" and generic_ms.unit_source == "interval_heuristic"
    assert "heuristic_time_unit" in generic_ms.issues
    generic_s = tb.audit_gazepoint_timebase([0, 1, 2, 3], clock_id="heuristic-s")
    assert generic_s.input_unit == "seconds" and generic_s.unit_source == "interval_heuristic"


def test_timebase_warning_and_fail_states_cover_anomalies():
    warning = tb.audit_gazepoint_timebase(
        [0.0, 0.1, np.nan, 0.2, 0.2, 1.0, 1.11],
        time_unit="seconds",
        nominal_rate_hz=20,
        clock_id="warning",
        gap_factor=2,
        rate_tolerance_fraction=0.01,
        jitter_warning_cv=0.01,
    )
    assert warning.status == "warning"
    assert set(warning.issues) == {
        "nonfinite_timestamps",
        "duplicate_timestamps",
        "large_sampling_gaps",
        "high_interval_jitter",
        "nominal_rate_mismatch",
    }
    assert warning.n_duplicate_timestamps == 1
    assert warning.n_large_gaps == 1
    assert warning.estimated_missing_samples > 0

    backwards = tb.audit_gazepoint_timebase(
        [0.0, 0.1, 0.05, 0.2], time_unit="seconds", clock_id="backward"
    )
    assert backwards.status == "fail"
    assert "backward_timestamps" in backwards.issues

    duplicate_only = tb.audit_gazepoint_timebase(
        [1.0, 1.0, 1.0], time_unit="seconds", clock_id="duplicate-only"
    )
    assert duplicate_only.status == "fail"
    assert duplicate_only.issues == ("no_positive_intervals", "duplicate_timestamps")

    decreasing = tb.audit_gazepoint_timebase(
        [3.0, 2.0, 1.0], time_unit="seconds", clock_id="decreasing"
    )
    assert decreasing.status == "fail"
    assert decreasing.issues == ("no_positive_intervals", "backward_timestamps")

    one = tb.audit_gazepoint_timebase([1.0], time_unit="seconds", clock_id="one")
    assert one.status == "fail" and one.issues == ("insufficient_finite_timestamps",)
    empty = tb.audit_gazepoint_timebase([], time_unit="seconds", clock_id="empty")
    assert empty.first_time_s is None and empty.last_time_s is None


def test_timebase_parameter_and_input_guardrails():
    with pytest.raises(ValueError, match="clock_id"):
        tb.audit_gazepoint_timebase([0, 1], clock_id=" ")
    with pytest.raises(ValueError, match="gap_factor"):
        tb.audit_gazepoint_timebase([0, 1], gap_factor=1)
    with pytest.raises(ValueError, match="positive"):
        tb.audit_gazepoint_timebase([0, 1], nominal_rate_hz=0)
    with pytest.raises(ValueError, match="non-negative"):
        tb.audit_gazepoint_timebase([0, 1], rate_tolerance_fraction=-1)
    with pytest.raises(ValueError, match="non-negative"):
        tb.audit_gazepoint_timebase([0, 1], jitter_warning_cv=-1)
    with pytest.raises(ValueError, match="time_unit"):
        tb.audit_gazepoint_timebase([0, 1], time_unit="ticks")
    with pytest.raises(ValueError, match="nominal_rate_hz"):
        tb.audit_gazepoint_timebase([0, 1], time_unit="samples")
    with pytest.raises(ValueError, match="sample-counter"):
        tb.audit_gazepoint_timebase(pd.DataFrame({"CNT": [0, 1, 2]}))
    with pytest.raises(ValueError, match="Could not identify"):
        tb.audit_gazepoint_timebase(pd.DataFrame({"x": [0, 1]}))
    with pytest.raises(ValueError, match="not found"):
        tb.audit_gazepoint_timebase(pd.DataFrame({"time": [0, 1]}), time_col="missing")
    with pytest.raises(ValueError, match="only be used"):
        tb._coerce_raw_time([0, 1], "time", name="reference")
    with pytest.raises(TypeError, match="numeric timestamp"):
        tb.audit_gazepoint_timebase("not-a-sequence")
    with pytest.raises(TypeError, match="numeric timestamp"):
        tb._coerce_raw_time(object(), None, name="data")
    with pytest.raises(ValueError, match="Unsupported"):
        tb._to_seconds(np.array([0.0, 1.0]), "ticks", None)


def test_timebase_certificate_is_deterministic_and_detects_tampering():
    audit = tb.audit_gazepoint_timebase([0, 0.1, 0.2], time_unit="seconds", clock_id="clock")
    cert = tb.create_gazepoint_timebase_certificate(audit)
    assert cert == tb.create_gazepoint_timebase_certificate(audit)
    assert tb.validate_gazepoint_timebase_certificate(audit, cert)
    reordered = {"sha256": cert["sha256"], "payload": dict(reversed(list(cert["payload"].items())))}
    assert tb.validate_gazepoint_timebase_certificate(audit, reordered)
    tampered = copy.deepcopy(cert)
    tampered["payload"]["clock_id"] = "other"
    assert not tb.validate_gazepoint_timebase_certificate(audit, tampered)
    tampered_digest = copy.deepcopy(cert)
    tampered_digest["sha256"] = "0" * 64
    assert not tb.validate_gazepoint_timebase_certificate(audit, tampered_digest)
    assert not tb.validate_gazepoint_timebase_certificate(audit, {})
    assert not tb.validate_gazepoint_timebase_certificate(audit, {"payload": [], "sha256": "x"})
    assert not tb.validate_gazepoint_timebase_certificate(object(), cert)
    with pytest.raises(TypeError):
        tb.create_gazepoint_timebase_certificate(object())


def test_affine_alignment_and_application_with_dataframe_units():
    ref = pd.DataFrame({"time_s": [0, 1, 2, 3, 4]})
    tar = pd.DataFrame({"TIME_MS": (0.2 + 1.002 * ref.time_s.to_numpy()) * 1000})
    alignment = tb.fit_gazepoint_clock_alignment(
        ref,
        tar,
        reference_clock="ref",
        target_clock="tar",
    )
    assert alignment.method == "affine"
    assert alignment.intercept_s == pytest.approx(0.2)
    assert alignment.slope_target_per_reference == pytest.approx(1.002)
    assert alignment.drift_ppm == pytest.approx(2000)
    assert alignment.residual_max_abs_s < 1e-12
    assert alignment.r_squared == pytest.approx(1.0)
    assert alignment.estimator == "ordinary_least_squares"
    assert alignment.anchor_match_method == "row_order"
    assert alignment.reference_time_unit == "seconds"
    assert alignment.target_time_unit == "milliseconds"
    corrected = tb.apply_gazepoint_clock_alignment(
        [200, 1202, 2204], alignment, time_unit="milliseconds"
    )
    assert corrected == pytest.approx([0, 1, 2])
    sample_corrected = tb.apply_gazepoint_clock_alignment(
        [10, 20, 30],
        replace(alignment, intercept_s=0.0, slope_target_per_reference=1.0),
        time_unit="samples",
        nominal_rate_hz=10,
    )
    assert sample_corrected == pytest.approx([1, 2, 3])


def test_offset_alignment_finite_pair_filtering_and_max_pairs():
    ref = [0, 1, np.nan, 3, 4]
    tar = [0.5, 1.5, 2.5, 3.5, 5.0]
    alignment = tb.fit_gazepoint_clock_alignment(
        ref,
        tar,
        reference_time_unit="seconds",
        target_time_unit="seconds",
        reference_clock="r",
        target_clock="t",
        method="offset",
        max_pairs=4,
    )
    assert alignment.n_matched_anchors == 3
    assert alignment.intercept_s == pytest.approx(0.5)
    assert alignment.slope_target_per_reference == 1
    assert alignment.r_squared is not None
    assert alignment.estimator == "median_offset"
    assert len(alignment.reference_anchor_sha256) == 64


def test_alignment_guardrails_cover_invalid_cases(monkeypatch):
    with pytest.raises(ValueError, match="distinct clocks"):
        tb.fit_gazepoint_clock_alignment([0, 1], [0, 1], reference_clock="same", target_clock="same")
    with pytest.raises(ValueError, match="method"):
        tb.fit_gazepoint_clock_alignment([0, 1], [0, 1], method="bad")
    with pytest.raises(ValueError, match="reference_nominal_rate_hz"):
        tb.fit_gazepoint_clock_alignment([0, 1], [0, 1], reference_nominal_rate_hz=0)
    with pytest.raises(ValueError, match="target_nominal_rate_hz"):
        tb.fit_gazepoint_clock_alignment([0, 1], [0, 1], target_nominal_rate_hz=0)
    with pytest.raises(ValueError, match="max_pairs"):
        tb.fit_gazepoint_clock_alignment([0, 1, 2], [0, 1, 2], max_pairs=1)
    with pytest.raises(ValueError, match="max_pairs"):
        tb.fit_gazepoint_clock_alignment([0, 1, 2], [0, 1, 2], max_pairs=2.5)
    with pytest.raises(ValueError, match="At least two matched"):
        tb.fit_gazepoint_clock_alignment([0], [0])
    with pytest.raises(ValueError, match="finite matched"):
        tb.fit_gazepoint_clock_alignment([0, np.nan], [0, np.nan])
    with pytest.raises(ValueError, match="distinct time point"):
        tb.fit_gazepoint_clock_alignment([1, 1], [2, 3])
    with pytest.raises(ValueError, match="positive"):
        tb.fit_gazepoint_clock_alignment(
            [0, 1, 2],
            [2, 1, 0],
            reference_time_unit="seconds",
            target_time_unit="seconds",
        )
    with pytest.raises(TypeError, match="alignment"):
        tb.apply_gazepoint_clock_alignment([0, 1], object())
    with pytest.raises(ValueError, match="nominal_rate_hz"):
        _, _, _, _, alignment = clean_audits()
        tb.apply_gazepoint_clock_alignment([0, 1], alignment, nominal_rate_hz=0)

    original_lstsq = np.linalg.lstsq
    monkeypatch.setattr(np.linalg, "lstsq", lambda *args, **kwargs: (np.array([0.0, np.nan]), None, None, None))
    with pytest.raises(ValueError, match="positive"):
        tb.fit_gazepoint_clock_alignment([0, 1], [0, 1])
    monkeypatch.setattr(np.linalg, "lstsq", original_lstsq)


def test_alignment_constant_target_sets_r_squared_none():
    alignment = tb.fit_gazepoint_clock_alignment(
        [0, 1, 2],
        [5, 5, 5],
        reference_time_unit="seconds",
        target_time_unit="seconds",
        reference_clock="r",
        target_clock="t",
        method="offset",
    )
    assert alignment.r_squared is None


def test_alignment_certificate_clean_case_and_fail_closed_gate():
    _, _, reference_audit, target_audit, alignment = clean_audits()
    cert = tb.create_gazepoint_multimodal_alignment_certificate(
        reference_audit,
        target_audit,
        alignment,
        tolerance_s=1e-10,
    )
    payload = cert["payload"]
    assert payload["status"] == "certified"
    assert payload["alignment_reference"] == "reference"
    assert payload["alignment_method"] == "affine"
    assert payload["correction_applied"] is True
    assert payload["resampling_operation"] == "none"
    assert payload["overlap_duration_s"] > 0
    assert payload["timebase_warnings"] == []
    assert tb.validate_gazepoint_multimodal_alignment_certificate(
        reference_audit, target_audit, alignment, cert, max_tolerance_s=1e-10
    )
    assert tb.assert_gazepoint_multimodal_fusion_ready(
        reference_audit, target_audit, alignment, cert, max_tolerance_s=1e-10
    )
    assert not tb.validate_gazepoint_multimodal_alignment_certificate(
        reference_audit, target_audit, alignment, cert, max_tolerance_s=1e-12
    )
    with pytest.raises(ValueError, match="valid multimodal"):
        tb.assert_gazepoint_multimodal_fusion_ready(
            reference_audit, target_audit, alignment, cert, max_tolerance_s=1e-12
        )


def test_alignment_certificate_warning_override_and_identity_correction():
    ref = tb.audit_gazepoint_timebase(
        [0, 0.1, 0.2, 0.2, 0.3], time_unit="seconds", clock_id="ref"
    )
    tar = tb.audit_gazepoint_timebase(
        [0, 0.1, 0.2, 0.3], time_unit="seconds", clock_id="tar"
    )
    alignment = tb.fit_gazepoint_clock_alignment(
        [0, 1, 2],
        [0, 1, 2],
        reference_time_unit="seconds",
        target_time_unit="seconds",
        reference_clock="ref",
        target_clock="tar",
    )
    assert ref.status == "warning"
    with pytest.raises(ValueError, match="explicitly allowed"):
        tb.create_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, tolerance_s=1e-9)
    cert = tb.create_gazepoint_multimodal_alignment_certificate(
        ref,
        tar,
        alignment,
        tolerance_s=1e-9,
        allow_timebase_warnings=True,
        resampling_operation="none; clocks only",
    )
    heuristic_alignment = replace(
        alignment,
        reference_unit_source="interval_heuristic",
        target_unit_source="interval_heuristic",
    )
    heuristic_cert = tb.create_gazepoint_multimodal_alignment_certificate(
        ref,
        tar,
        heuristic_alignment,
        tolerance_s=1e-9,
        allow_timebase_warnings=True,
    )
    assert "alignment_reference_unit_heuristic" in heuristic_cert["payload"]["timebase_warnings"]
    assert "alignment_target_unit_heuristic" in heuristic_cert["payload"]["timebase_warnings"]
    assert cert["payload"]["status"] == "certified_with_warnings"
    assert cert["payload"]["correction_applied"] is False
    assert cert["payload"]["timebase_warnings"] == ["duplicate_timestamps"]
    assert tb.validate_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, cert)


def test_alignment_certificate_guardrails_and_tampering():
    _, _, ref, tar, alignment = clean_audits()
    with pytest.raises(TypeError, match="reference_audit"):
        tb.create_gazepoint_multimodal_alignment_certificate(object(), tar, alignment, tolerance_s=1)
    with pytest.raises(TypeError, match="alignment"):
        tb.create_gazepoint_multimodal_alignment_certificate(ref, tar, object(), tolerance_s=1)
    with pytest.raises(ValueError, match="tolerance_s"):
        tb.create_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, tolerance_s=-1)
    with pytest.raises(ValueError, match="resampling_operation"):
        tb.create_gazepoint_multimodal_alignment_certificate(
            ref, tar, alignment, tolerance_s=1, resampling_operation=" "
        )
    with pytest.raises(ValueError, match="Reference audit clock"):
        tb.create_gazepoint_multimodal_alignment_certificate(
            replace(ref, clock_id="wrong"), tar, alignment, tolerance_s=1
        )
    with pytest.raises(ValueError, match="Target audit clock"):
        tb.create_gazepoint_multimodal_alignment_certificate(
            ref, replace(tar, clock_id="wrong"), alignment, tolerance_s=1
        )
    failed = tb.audit_gazepoint_timebase([1], time_unit="seconds", clock_id="reference")
    with pytest.raises(ValueError, match="audit has failed"):
        tb.create_gazepoint_multimodal_alignment_certificate(failed, tar, alignment, tolerance_s=1)
    noisy = replace(alignment, residual_max_abs_s=0.2)
    with pytest.raises(ValueError, match="residual exceeds"):
        tb.create_gazepoint_multimodal_alignment_certificate(ref, tar, noisy, tolerance_s=0.1)

    cert = tb.create_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, tolerance_s=1e-10)
    assert not tb.validate_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, {})
    malformed = {"payload": {}, "sha256": "x"}
    assert not tb.validate_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, malformed)
    bad_type = {"payload": [], "sha256": "x"}
    assert not tb.validate_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, bad_type)
    tampered = copy.deepcopy(cert)
    tampered["payload"]["alignment_method"] = "offset"
    assert not tb.validate_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, tampered)
    bad_tolerance = copy.deepcopy(cert)
    bad_tolerance["payload"]["tolerance_s"] = "not-a-number"
    assert not tb.validate_gazepoint_multimodal_alignment_certificate(ref, tar, alignment, bad_tolerance)
    with pytest.raises(TypeError):
        tb._alignment_payload(object())


def test_no_overlap_is_recorded_as_zero_duration():
    ref = tb.audit_gazepoint_timebase([0, 1, 2], time_unit="seconds", clock_id="ref")
    tar = tb.audit_gazepoint_timebase([10, 11, 12], time_unit="seconds", clock_id="tar")
    identity = tb.GazepointClockAlignment(
        reference_clock="ref",
        target_clock="tar",
        method="offset",
        n_matched_anchors=2,
        intercept_s=0.0,
        slope_target_per_reference=1.0,
        drift_ppm=0.0,
        residual_mean_s=0.0,
        residual_sd_s=0.0,
        residual_max_abs_s=0.0,
        r_squared=1.0,
        reference_anchor_sha256="a" * 64,
        target_anchor_sha256="b" * 64,
    )
    cert = tb.create_gazepoint_multimodal_alignment_certificate(ref, tar, identity, tolerance_s=0)
    assert cert["payload"]["overlap_duration_s"] == 0


def test_internal_helpers_cover_remaining_edge_branches():
    assert tb._positive_differences(np.array([np.nan])).size == 0
    with pytest.raises(ValueError, match="finite positive"):
        tb._validate_positive_number(np.inf, "x")
    assert tb._validate_positive_number(0, "x", allow_zero=True) == 0
    assert tb._finite_or_none(None) is None
    assert tb._finite_or_none(np.nan) is None
