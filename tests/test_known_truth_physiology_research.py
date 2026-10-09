import pandas as pd
import pytest

from research.methods_briefing_2026.known_truth_physiology import (
    simulate_known_truth_physiology,
)


def test_truth_is_separate_from_observed_and_reproducible():
    args = dict(duration_s=5., sampling_rate_hz=100.,
                scr_onsets_s=[1., 3.], scr_amplitudes=[.5, .7], seed=8)
    a = simulate_known_truth_physiology(**args)
    b = simulate_known_truth_physiology(**args)
    for name in ("truth", "observed_signal", "artifacts", "event_truth"):
        pd.testing.assert_frame_equal(a[name], b[name])
    assert len(a["truth"]) == 500
    assert "scr_onset" in set(a["event_truth"]["event_type"])
    assert a["metadata"]["validation_status"] == "synthetic_phenomenological_truth_only"


def test_zero_artifacts_recover_exact_toy_truth():
    r = simulate_known_truth_physiology(
        duration_s=4, sampling_rate_hz=50, scr_onsets_s=(1,),
        scr_amplitudes=(.5,), noise_sd=0, dropout_fraction=0,
    )
    assert (r["observed_signal"]["ecg_like"] == r["truth"]["ecg_like"]).all()
    assert (r["observed_signal"]["eda_total"] == r["truth"]["eda_total"]).all()
    assert r["artifacts"]["dropout_mask"].sum() == 0


def test_invalid_scr_metadata_rejected():
    with pytest.raises(ValueError, match="SCR"):
        simulate_known_truth_physiology(scr_onsets_s=(2., 1.), scr_amplitudes=(1., 1.))
