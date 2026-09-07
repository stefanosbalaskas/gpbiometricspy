import math

import pytest

import gpbiometricspy.measurement_accountability as ma
from gpbiometricspy.measurement_accountability import (
    compare_hrv_prv_devices,
    ppg_topology_features,
    scr_responsivity_sensitivity,
    validation_ladder,
)


def test_device_agreement_is_metric_specific():
    out = compare_hrv_prv_devices([20, 30, 40, 50], [21, 29, 42, 48], metric="RMSSD")
    assert out["metric"] == "RMSSD"
    assert out["n"] == 4
    assert -1 <= out["lin_ccc"] <= 1
    assert len(out["bland_altman_loa95"]) == 2
    assert "does not establish global" in out["interpretation"]


def test_device_agreement_filters_bad_pairs_and_requires_three_finite_pairs():
    assert ma._finite_pairs([1, "bad", math.nan], [1, 2, 3]) == [(1.0, 1.0)]
    with pytest.raises(ValueError, match="at least 3 paired finite observations"):
        compare_hrv_prv_devices([1, "bad", math.nan], [1, 2, 3], metric="RMSSD")


def test_device_agreement_handles_degenerate_constant_series():
    out = compare_hrv_prv_devices([1, 1, 1], [1, 1, 1], metric="constant")
    assert math.isnan(out["lin_ccc"])
    assert math.isnan(out["icc_a1"])


def test_private_numeric_helpers_cover_small_and_empty_inputs():
    assert math.isnan(ma._var([1.0]))
    assert ma._var([1.0, 3.0]) == 2.0
    assert math.isnan(ma._quantile([], 0.5))
    assert ma._quantile([0.0, 10.0], 0.25) == 2.5


def test_scr_nonresponder_is_retained():
    out = scr_responsivity_sensitivity(["p1", "p1", "p2", "p2"], [0.03, 0.04, 0.0, 0.0])
    p2 = next(row for row in out if row["participant"] == "p2")
    assert p2["conventional_nonresponder"] is True
    assert p2["retain_for_modeling"] is True
    assert 0 < p2["posterior_response_probability"] < 1


def test_scr_responsivity_validates_inputs_and_skips_non_numeric_amplitudes():
    with pytest.raises(ValueError, match="equal length"):
        scr_responsivity_sensitivity(["p1"], [0.1, 0.2])
    with pytest.raises(ValueError, match="invalid threshold or prior"):
        scr_responsivity_sensitivity(["p1"], [0.1], threshold=-0.01)

    out = scr_responsivity_sensitivity(
        ["p1", "p1", "p2", "p2"],
        ["bad", 0.03, math.nan, -0.5],
    )
    assert out == [
        {
            "participant": "p1",
            "n_trials": 1,
            "responses": 1,
            "response_rate": 1.0,
            "posterior_response_probability": 2 / 3,
            "posterior_alpha": 2.0,
            "posterior_beta": 1.0,
            "conventional_nonresponder": False,
            "retain_for_modeling": True,
        },
        {
            "participant": "p2",
            "n_trials": 1,
            "responses": 0,
            "response_rate": 0.0,
            "posterior_response_probability": 1 / 3,
            "posterior_alpha": 1.0,
            "posterior_beta": 2.0,
            "conventional_nonresponder": True,
            "retain_for_modeling": True,
        },
    ]


def test_generalization_gate_requires_held_out_participants():
    out = validation_ladder(
        {
            "acquisition_qc": True,
            "analytical_qc": True,
            "construct_check": True,
            "within_person": True,
            "held_out_person": None,
        },
        claim="generalizable",
    )
    assert out["claim_status"] == "not_supported"


def test_validation_ladder_normalizes_aliases_and_covers_all_claim_states():
    failed = validation_ladder(
        {
            "acquisition_qc": False,
            "analytical_qc": True,
            "construct_check": True,
            "within_person": True,
            "held_out_person": True,
        }
    )
    assert failed["claim_status"] == "not_supported"

    qualified = validation_ladder(
        {
            "acquisition_qc": "ok",
            "analytical_qc": "passed",
            "construct_check": "warn",
            "within_person": "pass",
            "held_out_person": "na",
        }
    )
    assert qualified["claim_status"] == "qualified"
    assert qualified["stages"]["construct_check"] == "warning"
    assert qualified["stages"]["held_out_person"] == "not_assessed"

    supported = validation_ladder(
        {
            "acquisition_qc": True,
            "analytical_qc": True,
            "construct_check": True,
            "within_person": True,
            "held_out_person": True,
        },
        claim="population",
    )
    assert supported["claim_status"] == "supported"
    assert supported["held_out_person_generalization"] is True

    with pytest.raises(ValueError, match="invalid stage status"):
        validation_ladder({"acquisition_qc": "unknown"})


def test_ppg_topology_is_labeled_experimental_structural_descriptor():
    signal = [math.sin(i / 5.0) for i in range(80)]
    out = ppg_topology_features(signal, delay=2, dimension=3)
    assert out["descriptor_status"] == "experimental_structural_descriptor"
    assert out["n_embedding_points"] > 10
    assert "participant-grouped" in out["ml_guardrail"]


def test_topology_helpers_and_input_guards_cover_edge_paths():
    assert ma._mst_edges([]) == []

    with pytest.raises(ValueError, match="delay >= 1"):
        ppg_topology_features([0, 1, 2, 3], delay=0)
    with pytest.raises(ValueError, match="signal is too short"):
        ppg_topology_features([0, 1], delay=1, dimension=2)

    out = ppg_topology_features(
        [0, "bad", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        delay=1,
        dimension=2,
        max_points=3,
    )
    assert out["n_embedding_points"] == 3

    one_edge = ppg_topology_features([0, 1, 2], delay=1, dimension=2)
    assert one_edge["n_embedding_points"] == 2
    assert one_edge["h0_lifetime_sd"] == 0.0

    flat = ppg_topology_features([1, 1, 1], delay=1, dimension=2)
    assert flat["h0_entropy"] == 0.0
    assert flat["h0_energy"] == 0.0
