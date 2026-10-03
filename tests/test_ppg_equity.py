import numpy as np
import pandas as pd
import pytest

from gpbiometricspy.ppg_equity import (
    compare_ppg_reference_by_pigmentation,
    compute_skin_ita,
    ppg_pigmentation_audit,
    summarize_ppg_quality_by_pigmentation,
    validate_skin_pigmentation_metadata,
)


def _demo(n_participants=6, fs=20, seconds=4):
    parts = []
    itas = [60, 45, 32, 18, 0, -20][:n_participants]
    for i, ita in enumerate(itas):
        t = np.arange(0, seconds, 1 / fs)
        rng = np.random.default_rng(i + 1)
        ppg = 1 + 0.12 * np.sin(2 * np.pi * 1.2 * t) + 0.01 * rng.normal(size=len(t))
        ref = 70 + 3 * np.sin(2 * np.pi * 0.1 * t)
        cand = ref + (60 - ita) * 0.01 + rng.normal(scale=0.5, size=len(t))
        if i == 5:
            ppg[::5] = np.nan
            cand[::4] = np.nan
        parts.append(
            pd.DataFrame(
                {
                    "participant": f"p{i + 1}",
                    "time_s": t,
                    "PPG": ppg,
                    "ITA": ita,
                    "reference_hr": ref,
                    "candidate_hr": cand,
                    "device": "demo",
                    "condition": "rest",
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def test_compute_skin_ita_continuous_categories_and_statuses():
    out = compute_skin_ita([70, 50, 30, 101, np.nan], [20, 0, 20, 10, 10], classify=True)
    assert out.loc[0, "ita_degrees"] == pytest.approx(45)
    assert out.loc[0, "ita_category"] == "light"
    assert out.loc[1, "status"] == "undefined_zero_over_zero"
    assert out.loc[2, "ita_category"] == "dark"
    assert out.loc[3, "status"] == "invalid_l_star"
    assert out.loc[4, "status"] == "missing_or_nonfinite"
    scalar = compute_skin_ita(60, 0, classify=False)
    assert scalar.loc[0, "ita_degrees"] == pytest.approx(90)
    assert scalar.loc[0, "status"] == "b_star_zero_limit"
    assert "ita_category" not in scalar


def test_validate_cielab_preserves_provenance_and_site_match():
    d = pd.DataFrame({"L": [70, 60, 55], "a": [1, 2, 3], "b": [20, 15, 10], "site": ["finger"] * 3, "sensor": ["finger"] * 3})
    out = validate_skin_pigmentation_metadata(
        d,
        metric="cielab",
        l_star_col="L",
        a_star_col="a",
        b_star_col="b",
        method="colorimetry",
        measurement_site="site",
        sensor_site="sensor",
        instrument_manufacturer="demo-maker",
        instrument_model="demo-model",
        assessor="trained-rater",
    )
    assert out["overview"].loc[0, "pigmentation_evidence"] == "objective"
    assert out["overview"].loc[0, "site_match_rows"] == 3
    assert {"l_star", "a_star", "b_star", "ita_category"} <= set(out["normalized"].columns)
    assert not out["warnings"]


def test_validate_proxy_never_becomes_pigmentation_and_tracks_missingness():
    d = pd.DataFrame({"race": ["A", None, "B"], "why": [None, "not_collected", None]})
    out = validate_skin_pigmentation_metadata(d, metric="race", pigmentation_col="race", missing_reason_col="why")
    assert out["overview"].loc[0, "pigmentation_evidence"] == "not_measured_proxy_only"
    assert "race_or_ethnicity_is_not_an_optical_pigmentation_measurement" in out["warnings"]
    assert out["normalized"].loc[0, "status"] == "proxy_not_pigmentation"
    assert out["missingness"].loc[0, "missing_reason"] == "not_collected"


def test_metadata_validation_rejects_bad_inputs():
    with pytest.raises(TypeError):
        validate_skin_pigmentation_metadata([], metric="ita", pigmentation_col="ITA")
    with pytest.raises(ValueError):
        validate_skin_pigmentation_metadata(pd.DataFrame({"x": [1]}), metric="bogus", pigmentation_col="x")
    with pytest.raises(ValueError):
        validate_skin_pigmentation_metadata(pd.DataFrame({"L": [60]}), metric="cielab", l_star_col="L")
    with pytest.raises(ValueError):
        validate_skin_pigmentation_metadata(pd.DataFrame({"ITA": [1]}), metric="ita")


def test_quality_audit_computes_sqi_retention_and_clustered_associations():
    d = _demo()
    out = summarize_ppg_quality_by_pigmentation(
        d,
        participant_col="participant",
        ppg_col="PPG",
        pigmentation_col="ITA",
        time_col="time_s",
        sampling_rate_hz=20,
        n_boot=12,
        random_state=4,
    )
    assert out["overview"].loc[0, "n_participants"] == 6
    assert out["overview"].loc[0, "continuous_associations_run"]
    assert {"ppg_snr_db", "ac_amplitude", "dc_level", "ac_dc_ratio", "template_correlation", "quality_retained"} <= set(out["group_quality"].columns)
    assert set(out["associations"]["outcome"]) == {"finite_prop", "missing_prop", "quality_retained", "ppg_snr_db", "ac_dc_ratio", "template_correlation"}
    assert len(out["strata_summary"]) >= 4
    assert "observational" in out["reporting_text"]


def test_quality_audit_subjective_metric_stays_descriptive():
    d = _demo().assign(monk=lambda x: np.where(x["ITA"] > 30, 3, 8))
    out = summarize_ppg_quality_by_pigmentation(
        d,
        participant_col="participant",
        ppg_col="PPG",
        pigmentation_col="monk",
        pigmentation_metric="monk",
        time_col="time_s",
        sampling_rate_hz=20,
        n_boot=0,
    )
    assert not out["overview"].loc[0, "continuous_associations_run"]
    assert out["associations"].empty


def test_quality_audit_rejects_direct_cielab_and_bad_sampling_rate():
    d = _demo()
    with pytest.raises(ValueError):
        summarize_ppg_quality_by_pigmentation(d, participant_col="participant", ppg_col="PPG", pigmentation_col="ITA", pigmentation_metric="cielab")
    with pytest.raises(ValueError):
        summarize_ppg_quality_by_pigmentation(d, participant_col="participant", ppg_col="PPG", pigmentation_col="ITA", sampling_rate_hz=0)


def test_reference_comparison_separates_retention_from_accuracy():
    d = _demo()
    out = compare_ppg_reference_by_pigmentation(
        d,
        participant_col="participant",
        reference_col="reference_hr",
        candidate_col="candidate_hr",
        pigmentation_col="ITA",
        device_col="device",
        condition_col="condition",
        n_boot=12,
        random_state=9,
    )
    assert out["overview"].loc[0, "paired_measurements"] < out["overview"].loc[0, "reference_available"]
    assert {"bias", "mae", "rmse", "loa_lower", "loa_upper", "lin_ccc", "retention_rate"} <= set(out["agreement"].columns)
    assert set(out["agreement_ci"]["metric"]) == {"retention_rate", "bias", "mae", "rmse", "lin_ccc"}
    assert set(out["associations"]["outcome"]) == {"signed_error", "absolute_error"}
    assert out["retention_association"].loc[0, "method"] == "participant_cluster_bootstrap_logistic"
    assert "Bland-Altman" in out["reporting_text"]


def test_reference_nonobjective_metric_avoids_continuous_model():
    d = _demo().assign(monk=lambda x: np.where(x["ITA"] > 30, 3, 8))
    out = compare_ppg_reference_by_pigmentation(
        d,
        participant_col="participant",
        reference_col="reference_hr",
        candidate_col="candidate_hr",
        pigmentation_col="monk",
        pigmentation_metric="monk",
        n_boot=0,
    )
    assert out["associations"].empty
    assert out["retention_association"].empty
    assert "continuous_association_models_not_run_for_nonobjective_pigmentation_metric" in out["warnings"]


def test_integrated_audit_supports_objective_cielab_and_reference_path():
    d = _demo()
    d["L"] = 50 + np.tan(np.deg2rad(d["ITA"])) * 20
    d["b"] = 20.0
    out = ppg_pigmentation_audit(
        d,
        participant_col="participant",
        ppg_col="PPG",
        pigmentation_metric="cielab",
        l_star_col="L",
        b_star_col="b",
        pigmentation_method="colorimetry",
        pigmentation_site="finger",
        sensor_site="finger",
        time_col="time_s",
        sampling_rate_hz=20,
        reference_col="reference_hr",
        candidate_col="candidate_hr",
        device_col="device",
        condition_col="condition",
        n_boot=8,
        random_state=2,
    )
    assert out["provenance"].loc[0, "analysis_metric"] == "ita"
    assert out["reference_agreement"]["overview"].loc[0, "status"] in {"complete", "qualified"}
    assert "does not label a device fair or unfair" in out["reporting_text"]


def test_integrated_audit_proxy_and_reference_pair_guardrails():
    d = _demo().assign(race="group-a")
    proxy = ppg_pigmentation_audit(
        d,
        participant_col="participant",
        ppg_col="PPG",
        pigmentation_metric="race",
        pigmentation_col="race",
        time_col="time_s",
        sampling_rate_hz=20,
        n_boot=0,
    )
    assert proxy["acquisition_quality"]["overview"].loc[0, "status"] == "not_assessed_proxy_is_not_pigmentation"
    assert proxy["reference_agreement"]["status"] == "not_assessed"
    assert "pigmentation_not_measured" in proxy["warnings"]
    with pytest.raises(ValueError):
        ppg_pigmentation_audit(
            d,
            participant_col="participant",
            ppg_col="PPG",
            pigmentation_metric="race",
            pigmentation_col="race",
            reference_col="reference_hr",
            n_boot=0,
        )
