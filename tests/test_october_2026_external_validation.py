import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.october_2026.external_validation import (  # noqa: E402
    external_classifier_validation,
    external_device_placement_strata,
    modality_ablation_audit,
)


def _data():
    return pd.DataFrame({
        "participant_id": ["a", "a", "b", "b", "c", "c", "d", "d"],
        "dataset_id": ["external"] * 8,
        "outcome": [0, 1] * 4,
        "probability": [.1, .9] * 4,
        "full_probability": [.1, .9] * 4,
        "ablated_probability": [.1, .4] * 4,
    })


def test_external_prevalence_and_bootstrap():
    a = external_classifier_validation(
        _data(), training_participants=["train"],
        training_datasets=["development"], seed=3)
    assert a["metrics"]["f1"] == pytest.approx(1)
    assert a["metrics"]["average_precision"] == pytest.approx(1)
    assert a["metrics"]["positive_prevalence"] == pytest.approx(.5)
    assert a["n_bootstrap_accepted"] == 199


def test_refuse_participant_or_dataset_overlap():
    with pytest.raises(ValueError, match="participant leakage"):
        external_classifier_validation(
            _data(), training_participants=["a"],
            training_datasets=["development"])
    with pytest.raises(ValueError, match="dataset identities"):
        external_classifier_validation(
            _data(), training_participants=["train"],
            training_datasets=["external"])


def test_modality_ablation_uses_paired_participant_units():
    result = modality_ablation_audit(_data(), seed=4)
    assert result["delta_balanced_accuracy"] == pytest.approx(.5)
    assert result["participant_bootstrap_interval"] == pytest.approx((.5, .5))


def test_device_placement_unqualified_strata_not_silently_dropped():
    d = _data()
    d["device_id"] = ["a"] * 4 + ["b"] * 4
    d["body_placement"] = ["wrist"] * 4 + ["pocket"] * 4
    d.loc[d.device_id == "b", "outcome"] = 1
    result = external_device_placement_strata(d)
    assert len(result) == 2
    assert set(result.status) == {
        "evaluable", "insufficient_independent_evidence",
    }
    assert result.loc[result.device_id == "b", "balanced_accuracy"].isna().all()
