import math

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


def test_scr_nonresponder_is_retained():
    out = scr_responsivity_sensitivity(["p1", "p1", "p2", "p2"], [0.03, 0.04, 0.0, 0.0])
    p2 = next(row for row in out if row["participant"] == "p2")
    assert p2["conventional_nonresponder"] is True
    assert p2["retain_for_modeling"] is True
    assert 0 < p2["posterior_response_probability"] < 1


def test_generalization_gate_requires_held_out_participants():
    out = validation_ladder(
        {"acquisition_qc": True, "analytical_qc": True, "construct_check": True,
         "within_person": True, "held_out_person": None},
        claim="generalizable",
    )
    assert out["claim_status"] == "not_supported"


def test_ppg_topology_is_labeled_experimental_structural_descriptor():
    signal = [math.sin(i / 5.0) for i in range(80)]
    out = ppg_topology_features(signal, delay=2, dimension=3)
    assert out["descriptor_status"] == "experimental_structural_descriptor"
    assert out["n_embedding_points"] > 10
    assert "participant-grouped" in out["ml_guardrail"]
