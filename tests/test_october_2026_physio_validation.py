import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.october_2026.physiological_validation import (  # noqa: E402
    baseline_stability_audit,
    baseline_window_sensitivity,
    preprocessing_to_inference_audit,
)


def test_baseline_stability_and_missingness():
    data = pd.DataFrame({
        "participant_id": ["a"] * 6 + ["b"] * 6,
        "time_s": list(range(6)) * 2,
        "value": [1, 2, np.nan, 4, 5, 6] + [2] * 6,
    })
    result = baseline_stability_audit(data)
    assert result.iloc[0].missing_fraction == pytest.approx(1 / 6)
    assert result.iloc[0].slope_per_s == pytest.approx(1.0)
    assert result.iloc[1].slope_per_s == pytest.approx(0.0)
    assert (result.stability_decision == "not_inferred").all()


def test_baseline_rejects_nonmonotone_and_missing():
    d = pd.DataFrame({"participant_id": ["a"] * 4,
                      "time_s": [0, 1, 1, 3], "value": [1, 2, 3, 4]})
    with pytest.raises(ValueError):
        baseline_stability_audit(d)


def test_three_layer_comparison_is_participant_bootstrapped():
    d = pd.DataFrame({
        "participant_id": ["a"] * 4 + ["b"] * 4 + ["c"] * 4,
        "reference": [0., 1., 0., 1.] * 3,
        "raw": [0.5, 1.5, 0.5, 1.5] * 3,
        "processed": [0.1, 1.1, 0.1, 1.1] * 3,
        "reference_event": [0, 1, 0, 1] * 3,
        "raw_event": [0, 0, 0, 1] * 3,
        "processed_event": [0, 1, 0, 1] * 3,
        "raw_effect": [0.2] * 12,
        "processed_effect": [0.3] * 12,
    })
    a = preprocessing_to_inference_audit(d, seed=7)
    b = preprocessing_to_inference_audit(d, seed=7)
    pd.testing.assert_frame_equal(a["summary"], b["summary"])
    assert a["summary"].loc[0, "mean_delta"] == pytest.approx(-0.4)
    assert a["summary"].loc[1, "mean_delta"] == pytest.approx(-0.25)
    assert len(a["participant_results"]) == 3


def test_no_participant_replication_as_independent_evidence():
    d = pd.DataFrame({"participant_id": ["a"] * 4, "reference": [1.] * 4,
                      "raw": [2.] * 4, "processed": [1.] * 4,
                      "raw_event": [0] * 4, "processed_event": [1] * 4,
                      "reference_event": [1] * 4,
                      "raw_effect": [1.] * 4, "processed_effect": [2.] * 4})
    with pytest.raises(ValueError, match="independent participants"):
        preprocessing_to_inference_audit(d)


def test_baseline_sensitivity_retains_failed_windows():
    d = pd.DataFrame({
        "participant_id": ["p"] * 8,
        "time_s": list(range(8)),
        "value": [1., 2., 3., 4., 5., 6., 7., 8.],
    })
    result = baseline_window_sensitivity(d, [(0., 3.), (0., 1.), (4., 7.)])
    assert list(result.status) == [
        "evaluable", "insufficient_valid", "evaluable",
    ]
    assert result.iloc[0].slope_per_s == pytest.approx(1.)
    assert np.isnan(result.iloc[1].mean_value)
