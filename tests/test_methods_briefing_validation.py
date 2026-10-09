import pandas as pd
import pytest

from research.methods_briefing_2026.methods_briefing_validation import (
    summarize_acquisition_rate_lineage,
    validate_biosignal_measurement,
)


def test_rate_lineage_does_not_relabel_declared_rates():
    result = summarize_acquisition_rate_lineage(
        [0, .01, .02, .03], device_native_rate_hz=120,
        sdk_declared_rate_hz=100, analysis_stream_rate_hz=50,
    )
    assert result["device_native_rate_hz"] == 120
    assert result["observed_median_rate_hz"] == pytest.approx(100)
    assert result["analysis_stream_rate_hz"] == 50
    with pytest.raises(ValueError, match="strictly"):
        summarize_acquisition_rate_lineage([0, 1, 1])


def test_agreement_responsiveness_and_recovery_are_distinct():
    frame = pd.DataFrame({
        "participant_id": ["p1"] * 3 + ["p2"] * 3,
        "phase": ["baseline", "perturbation", "recovery"] * 2,
        "reference": [1.0, 3.0, 2.0, 2.0, 4.0, 3.0],
        "candidate": [1.5, 3.5, 2.5, 2.5, 4.5, 3.5],
    })
    r = validate_biosignal_measurement(
        frame, reference_col="reference", candidate_col="candidate"
    )
    assert r["agreement"]["n_independent_participants"] == 2
    assert r["agreement"]["mean_bias_candidate_minus_reference"] == pytest.approx(.5)
    assert r["construct_responsiveness"]["candidate_change"].tolist() == [2, 2]
    assert r["recovery"]["reference_recovery_change"].tolist() == [-1, -1]
    assert "No equivalence" in r["claim_boundary"]


def test_unpaired_samples_counted_without_false_validity():
    data = pd.DataFrame({
        "participant_id": ["a", "a", "b"],
        "phase": ["baseline", "perturbation", "baseline"],
        "reference": [1.0, 2.0, 3.0],
        "candidate": [1.0, None, 3.0],
    })
    out = validate_biosignal_measurement(
        data, reference_col="reference", candidate_col="candidate"
    )
    assert out["agreement"]["unpaired_or_nonfinite_rows"] == 1
    assert out["construct_responsiveness"].empty
