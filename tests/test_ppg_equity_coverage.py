import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.ppg_equity as pe
from gpbiometricspy.ppg_equity import (
    compare_ppg_reference_by_pigmentation,
    ppg_pigmentation_audit,
    summarize_ppg_quality_by_pigmentation,
    validate_skin_pigmentation_metadata,
)


def _small_demo(n_participants=2, fs=20, seconds=4):
    parts = []
    for i, ita in enumerate([60, 20][:n_participants]):
        t = np.arange(0, seconds, 1 / fs)
        rng = np.random.default_rng(100 + i)
        ppg = 1 + 0.1 * np.sin(2 * np.pi * 1.2 * t) + 0.01 * rng.normal(size=len(t))
        ref = 70 + np.sin(2 * np.pi * 0.1 * t)
        cand = ref + rng.normal(scale=0.4, size=len(t))
        parts.append(
            pd.DataFrame(
                {
                    "participant": f"p{i + 1}",
                    "time_s": t,
                    "PPG": ppg,
                    "ITA": ita,
                    "reference_hr": ref,
                    "candidate_hr": cand,
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def test_ppg_equity_statement_edge_paths(monkeypatch):
    with pytest.raises(ValueError):
        pe._frame(pd.DataFrame())
    with pytest.raises(ValueError):
        pe._metric_name("")
    with pytest.raises(ValueError):
        pe._require_columns(pd.DataFrame({"x": [1]}), ["missing"])

    d = pd.DataFrame({"ITA": [10.0, 20.0]})
    out = validate_skin_pigmentation_metadata(
        d,
        metric="ita",
        pigmentation_col="ITA",
        method=["colorimetry", "colorimetry"],
        measurement_site=["finger", "finger"],
        sensor_site=["finger", "finger"],
    )
    assert out["normalized"]["ita_category"].notna().all()
    with pytest.raises(ValueError):
        pe._metadata_series(d, ["only-one"], "method")

    melanin = validate_skin_pigmentation_metadata(
        pd.DataFrame({"mi": [20.0, np.nan]}), metric="melanin_index", pigmentation_col="mi"
    )
    assert melanin["overview"].loc[0, "measured_rows"] == 1

    assert pe._sampling_rate(d, None, None) is None
    assert pe._sampling_rate(pd.DataFrame({"t": [1.0]}), "t", None) is None
    assert pe._sampling_rate(pd.DataFrame({"t": [0.0, 10.0, 20.0]}), "t", None) == pytest.approx(100.0)
    assert np.isnan(pe._template_correlation(np.arange(5.0), 20.0))
    assert np.isnan(pe._template_correlation(np.sin(np.linspace(0, 1, 50)), 20.0))

    original_find_peaks = pe.signal.find_peaks
    monkeypatch.setattr(pe.signal, "find_peaks", lambda *args, **kwargs: (np.array([10, 20, 30]), {}))
    forced = pe._template_correlation(np.ones(50), 10.0)
    assert np.isfinite(forced) or np.isnan(forced)
    monkeypatch.setattr(pe.signal, "find_peaks", original_find_peaks)

    empty_sqi = pe._ppg_sqi(np.array([np.nan, np.nan]), None, 1e-8)
    assert np.isnan(empty_sqi["ac_amplitude"])
    assert np.isnan(pe._slope(np.array([1.0, 1.0]), np.array([1.0, 2.0])))
    assert np.isnan(pe._ccc(np.array([1.0]), np.array([1.0])))

    mixed = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [0, 1, 0, 1], "p": ["a", "a", "b", "b"]})
    no_boot = pe._cluster_bootstrap_retention_logit(mixed, "x", "y", "p", 0, np.random.default_rng(1))
    assert np.isnan(no_boot["ci_low"])


def test_ppg_equity_small_sample_consistency_and_cielab_reference_guards():
    d = _small_demo()
    d.loc[d.index[1], "ITA"] = d.loc[d.index[1], "ITA"] - 5
    quality = summarize_ppg_quality_by_pigmentation(
        d,
        participant_col="participant",
        ppg_col="PPG",
        pigmentation_col="ITA",
        time_col="time_s",
        sampling_rate_hz=20,
        n_boot=0,
    )
    assert "pigmentation_varies_within_one_or_more_analysis_groups" in quality["warnings"]
    assert "fewer_than_five_participants_limits_stratified_inference" in quality["warnings"]

    with pytest.raises(ValueError):
        compare_ppg_reference_by_pigmentation(
            d,
            participant_col="participant",
            reference_col="reference_hr",
            candidate_col="candidate_hr",
            pigmentation_col="ITA",
            pigmentation_metric="cielab",
        )

    small = compare_ppg_reference_by_pigmentation(
        d,
        participant_col="participant",
        reference_col="reference_hr",
        candidate_col="candidate_hr",
        pigmentation_col="ITA",
        n_boot=0,
    )
    assert "fewer_than_five_participants_limits_reference_validation" in small["warnings"]


def test_ppg_equity_proxy_with_reference_columns_skips_reference_agreement():
    d = _small_demo().assign(race="group-a")
    out = ppg_pigmentation_audit(
        d,
        participant_col="participant",
        ppg_col="PPG",
        pigmentation_metric="race",
        pigmentation_col="race",
        reference_col="reference_hr",
        candidate_col="candidate_hr",
        n_boot=0,
    )
    assert out["reference_agreement"] == {"status": "not_assessed", "reason": "pigmentation_not_measured"}
