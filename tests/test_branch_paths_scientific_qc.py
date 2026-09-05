from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.figure
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_ibi_quality_validation_status_and_group_branches():
    with pytest.raises(TypeError, match="data frame"):
        gp.audit_gazepoint_ibi_quality([800, 810])
    with pytest.raises(ValueError, match="positive"):
        gp.audit_gazepoint_ibi_quality(pd.DataFrame({"IBI": [800]}), min_ibi_ms=0)
    with pytest.raises(ValueError, match="thresholds"):
        gp.audit_gazepoint_ibi_quality(pd.DataFrame({"IBI": [800]}), max_ibi_ms=0)
    with pytest.raises(ValueError, match="thresholds"):
        gp.audit_gazepoint_ibi_quality(pd.DataFrame({"IBI": [800]}), max_jump_ms=0)
    with pytest.raises(ValueError, match="smaller"):
        gp.audit_gazepoint_ibi_quality(
            pd.DataFrame({"IBI": [800]}), min_ibi_ms=1000, max_ibi_ms=1000
        )
    with pytest.raises(ValueError, match="time_col"):
        gp.audit_gazepoint_ibi_quality(pd.DataFrame({"IBI": [800]}), time_col="TIME")
    with pytest.raises(ValueError, match="ibi_col"):
        gp.audit_gazepoint_ibi_quality(
            pd.DataFrame({"IBI": [800]}), ibi_col="missing"
        )
    with pytest.raises(TypeError, match="must be numeric"):
        gp.audit_gazepoint_ibi_quality(pd.DataFrame({"IBI": ["800", "810"]}))
    with pytest.raises(ValueError, match="not found"):
        gp.audit_gazepoint_ibi_quality(
            pd.DataFrame({"IBI": [800, 810]}), group_cols="participant"
        )

    no_valid = gp.audit_gazepoint_ibi_quality(
        pd.DataFrame({"IBI": [np.nan, np.inf, 0, -1]})
    )
    assert no_valid["overview"].loc[0, "status"] == "no_valid_ibi_intervals"
    assert no_valid["group_summary"].loc[0, "status"] == "insufficient_ibi"

    mixed = gp.audit_gazepoint_ibi_quality(
        pd.DataFrame({"IBI": [800, 810, 2500]})
    )
    assert mixed["overview"].loc[0, "status"] == "ibi_quality_issues_detected"

    grouped = gp.audit_gazepoint_ibi_quality(
        pd.DataFrame(
            {
                "participant": ["P1", "P1", "P2"],
                "session": [1, 1, 1],
                "TIME": [2, 1, 1],
                "IBI": [810, 800, 900],
            }
        ),
        group_cols=["participant", "session"],
        time_col="TIME",
    )
    assert grouped["overview"].loc[0, "group_column_count"] == 2
    assert set(grouped["group_summary"]["status"]) == {
        "sufficient_ibi",
        "insufficient_ibi",
    }


def test_ibi_window_exclusion_and_sufficiency_branches():
    with pytest.raises(ValueError, match="exclude_large_jumps"):
        gp.summarise_gazepoint_ibi_windows(
            pd.DataFrame({"IBI": [800, 810]}), exclude_large_jumps="yes"
        )
    with pytest.raises(ValueError, match="positive integer"):
        gp.summarise_gazepoint_ibi_windows(
            pd.DataFrame({"IBI": [800, 810]}), min_valid_ibi=0
        )

    dat = pd.DataFrame(
        {
            "participant": ["P1"] * 4 + ["P2"] * 2,
            "IBI": [800, 810, 1500, 1510, 900, 2500],
        }
    )
    keep_jumps = gp.summarise_gazepoint_ibi_windows(
        dat,
        group_cols="participant",
        max_jump_ms=500,
        exclude_large_jumps=False,
        min_valid_ibi=2,
    )
    assert keep_jumps["overview"].loc[0, "status"] == "some_ibi_windows_insufficient"
    assert keep_jumps["overview"].loc[0, "sufficient_window_count"] == 1
    assert keep_jumps["overview"].loc[0, "insufficient_window_count"] == 1

    none_sufficient = gp.summarise_gazepoint_ibi_windows(
        pd.DataFrame({"participant": ["P1", "P2"], "IBI": [800, 900]}),
        group_cols="participant",
        min_valid_ibi=2,
    )
    assert none_sufficient["overview"].loc[0, "status"] == "no_sufficient_ibi_windows"


def test_scr_interval_direct_latency_boundaries_and_validation():
    dat = pd.DataFrame({"latency": [1.0, 3.999, 4.0, 6.999, 7.0, 10.0, 10.1, np.nan]})
    out = gp.classify_gazepoint_scr_intervals(dat, latency_col="latency")
    assert out["scr_interval"].tolist() == [
        "FIR",
        "FIR",
        "SIR",
        "SIR",
        "TIR",
        "TIR",
        "outside_defined_intervals",
        "missing_latency",
    ]

    with pytest.raises(TypeError, match="data frame"):
        gp.classify_gazepoint_scr_intervals([])
    with pytest.raises(ValueError, match="fir"):
        gp.classify_gazepoint_scr_intervals(dat, latency_col="latency", fir=(1, 1))
    with pytest.raises(ValueError, match="sir"):
        gp.classify_gazepoint_scr_intervals(
            dat, latency_col="latency", sir=(4, np.inf)
        )
    with pytest.raises(ValueError, match="tir"):
        gp.classify_gazepoint_scr_intervals(dat, latency_col="latency", tir=(7,))
    with pytest.raises(ValueError, match="Supply either"):
        gp.classify_gazepoint_scr_intervals(pd.DataFrame({"x": [1]}))
    with pytest.raises(ValueError, match="latency"):
        gp.classify_gazepoint_scr_intervals(
            pd.DataFrame({"x": [1]}), latency_col="latency"
        )
    with pytest.raises(ValueError, match="Column was not found"):
        gp.classify_gazepoint_scr_intervals(
            pd.DataFrame({"response": [2]}),
            response_time_col="response",
            stimulus_onset_col="onset",
        )


def test_kleckner_transition_padding_time_and_validation_branches():
    with pytest.raises(TypeError, match="data frame"):
        gp.flag_kleckner_eda_artifacts([])
    with pytest.raises(ValueError, match="was not found"):
        gp.flag_kleckner_eda_artifacts(pd.DataFrame({"EDA": [1.0]}))
    with pytest.raises(TypeError, match="numeric conductance"):
        gp.flag_kleckner_eda_artifacts(pd.DataFrame({"GSR_US": ["1.0"]}))
    with pytest.raises(ValueError, match="non-negative"):
        gp.flag_kleckner_eda_artifacts(
            pd.DataFrame({"GSR_US": [1.0]}), transition_padding=-1
        )

    padded = gp.flag_kleckner_eda_artifacts(
        pd.DataFrame(
            {
                "participant": ["P1"] * 5,
                "time": [0.0, 1.0, 1.0, 2.0, 3.0],
                "GSR_US": [1.0, 1.0, 200.0, 1.0, 1.0],
            }
        ),
        time_col="time",
        group_cols="participant",
        transition_padding=1,
        max_abs_percent_change_per_second=20,
    )
    assert bool(padded.loc[2, "kleckner_range_artifact"])
    assert bool(padded.loc[1, "kleckner_transition_artifact"])
    assert bool(padded.loc[3, "kleckner_transition_artifact"])

    clean_single = gp.flag_kleckner_eda_artifacts(
        pd.DataFrame({"GSR_US": [1.0]}), transition_padding=2
    )
    assert not bool(clean_single.loc[0, "kleckner_artifact"])
    assert clean_single.loc[0, "kleckner_artifact_status"] == "usable"


def test_gsr_conductance_detection_passthrough_and_validation():
    with pytest.raises(TypeError, match="data frame"):
        gp.convert_gazepoint_gsr_to_conductance([])
    with pytest.raises(ValueError, match="output_col"):
        gp.convert_gazepoint_gsr_to_conductance(pd.DataFrame({"GSR": [1]}), output_col="")

    no_source = gp.convert_gazepoint_gsr_to_conductance(pd.DataFrame({"HR": [70, 71]}))
    assert no_source.attrs["gsr_conversion_summary"].loc[0, "status"] == "no_resistance_source_detected"

    with pytest.raises(ValueError, match="gsr_col"):
        gp.convert_gazepoint_gsr_to_conductance(
            pd.DataFrame({"GSR": [1.0]}), gsr_col="missing", input_unit="ohms"
        )
    with pytest.raises(TypeError, match="must be numeric"):
        gp.convert_gazepoint_gsr_to_conductance(
            pd.DataFrame({"GSR_OHMS": ["1000000"]})
        )

    direct = gp.convert_gazepoint_gsr_to_conductance(
        pd.DataFrame({"conductance_us": [1.2, np.inf, np.nan]})
    )
    assert direct.GSR_US.iloc[0] == pytest.approx(1.2)
    assert direct.GSR_US.iloc[1:].isna().all()
    assert direct.attrs["gsr_conversion_summary"].loc[0, "input_unit"] == "microsiemens"
    assert direct.attrs["gsr_conversion_summary"].loc[0, "n_invalid"] == 1

    overwrite = gp.convert_gazepoint_gsr_to_conductance(
        pd.DataFrame({"GSR_US": [99.0], "GSR_OHMS": [1_000_000.0]}),
        gsr_col="GSR_OHMS",
        input_unit="ohms",
        overwrite=True,
    )
    assert overwrite.GSR_US.iloc[0] == pytest.approx(1.0)


def test_tonic_phasic_auto_threshold_and_validation_branches():
    with pytest.raises(TypeError, match="data frame"):
        gp.summarise_gazepoint_gsr_tonic_phasic([])
    with pytest.raises(ValueError, match="window_n"):
        gp.summarise_gazepoint_gsr_tonic_phasic(
            pd.DataFrame({"GSR_US": [1.0]}), window_n=0
        )
    with pytest.raises(ValueError, match="peak_threshold"):
        gp.summarise_gazepoint_gsr_tonic_phasic(
            pd.DataFrame({"GSR_US": [1.0]}), peak_threshold="auto"
        )
    with pytest.raises(ValueError, match="output_prefix"):
        gp.summarise_gazepoint_gsr_tonic_phasic(
            pd.DataFrame({"GSR_US": [1.0]}), output_prefix=""
        )
    with pytest.raises(ValueError, match="gsr_col"):
        gp.summarise_gazepoint_gsr_tonic_phasic(
            pd.DataFrame({"GSR_US": [1.0]}), gsr_col="missing"
        )
    with pytest.raises(TypeError, match="must be numeric"):
        gp.summarise_gazepoint_gsr_tonic_phasic(pd.DataFrame({"GSR_US": ["1"]}))

    all_missing = gp.summarise_gazepoint_gsr_tonic_phasic(
        pd.DataFrame({"GSR_US": [np.nan, np.nan, np.nan]}), window_n=3
    )
    assert np.isnan(all_missing["summary"].loc[0, "peak_threshold"])
    assert all_missing["summary"].loc[0, "n_phasic_peaks"] == 0

    constant = gp.summarise_gazepoint_gsr_tonic_phasic(
        pd.DataFrame({"GSR_US": [1.0, 1.0, 1.0, 1.0]}), window_n=3
    )
    assert np.isinf(constant["summary"].loc[0, "peak_threshold"])
    assert constant["summary"].loc[0, "n_phasic_peaks"] == 0

    automatic = gp.summarise_gazepoint_gsr_tonic_phasic(
        pd.DataFrame({"GSR_US": [1.0, 1.1, 1.0, 2.0, 1.0, 1.1, 1.0]}),
        window_n=3,
    )
    assert np.isfinite(automatic["summary"].loc[0, "peak_threshold"])


def test_standardization_validation_insufficient_zero_and_overwrite_branches():
    with pytest.raises(TypeError, match="data frame"):
        gp.standardise_gazepoint_zscore([])
    with pytest.raises(ValueError, match="signal"):
        gp.standardise_gazepoint_zscore(pd.DataFrame({"source_participant": ["P1"]}))
    with pytest.raises(ValueError, match="group"):
        gp.standardise_gazepoint_zscore(pd.DataFrame({"SCR_Amplitude": [1.0]}))
    with pytest.raises(TypeError, match="numeric"):
        gp.standardise_gazepoint_zscore(
            pd.DataFrame({"source_participant": ["P1"], "SCR_Amplitude": ["1"]})
        )

    dat = pd.DataFrame(
        {
            "source_participant": ["good", "good", "flat", "flat", "short"],
            "SCR_Amplitude": [1.0, 3.0, 2.0, 2.0, 5.0],
        }
    )
    z = gp.standardise_gazepoint_zscore(dat, min_valid=2)
    pars = z.attrs["standardization_parameters"].set_index("unit_id")
    assert pars.loc["good", "status"] == "standardized"
    assert pars.loc["flat", "status"] == "zero_or_missing_sd"
    assert pars.loc["short", "status"] == "insufficient_finite_rows"

    with pytest.raises(ValueError, match="already exists"):
        gp.standardise_gazepoint_zscore(z)
    replaced = gp.standardise_gazepoint_zscore(z, overwrite=True)
    assert "SCR_Amplitude_Z" in replaced

    with pytest.raises(TypeError, match="data frame"):
        gp.standardise_gazepoint_range_correction([], signal_col="x")
    with pytest.raises(ValueError, match="was not found"):
        gp.standardise_gazepoint_range_correction(
            pd.DataFrame({"source_participant": ["P1"]}), signal_col="x"
        )
    with pytest.raises(ValueError, match="group"):
        gp.standardise_gazepoint_range_correction(
            pd.DataFrame({"x": [1.0]}), signal_col="x"
        )
    with pytest.raises(TypeError, match="numeric"):
        gp.standardise_gazepoint_range_correction(
            pd.DataFrame({"source_participant": ["P1"], "x": ["1"]}),
            signal_col="x",
        )
    with pytest.raises(ValueError, match="zero_range_action"):
        gp.standardise_gazepoint_range_correction(
            pd.DataFrame({"source_participant": ["P1"], "x": [1.0]}),
            signal_col="x",
            zero_range_action="bad",
        )

    range_dat = pd.DataFrame(
        {
            "source_participant": ["good", "good", "flat", "flat", "short"],
            "x": [1.0, 3.0, 2.0, 2.0, 5.0],
        }
    )
    corrected = gp.standardise_gazepoint_range_correction(
        range_dat, signal_col="x", min_valid=2, zero_range_action="zero"
    )
    summary = corrected.attrs["range_correction_summary"].iloc[0]
    assert summary.status == "range_correction_partial"
    params = corrected.attrs["range_correction_parameters"].set_index("unit_id")
    assert params.loc["flat", "status"] == "zero_or_missing_range"
    assert params.loc["short", "status"] == "insufficient_finite_rows"
    np.testing.assert_allclose(
        corrected.loc[corrected.source_participant == "flat", "x_Range_Corrected"],
        [0.0, 0.0],
    )
    with pytest.raises(ValueError, match="already exists"):
        gp.standardise_gazepoint_range_correction(corrected, signal_col="x")


def test_quality_audit_file_missing_validity_flatline_and_empty_branches(tmp_path):
    path = tmp_path / "hr.txt"
    path.write_text("HR;group\n70;A\n70;A\n70;A\n", encoding="utf-8")
    hr = gp.audit_gazepoint_hr_quality(path, validity_column="missing", jump_threshold=None).iloc[0]
    assert hr.validity_column is None
    assert bool(hr.flatline)
    assert np.isnan(hr.large_jump_rows)
    assert hr.usable_rows == 3

    empty = gp.audit_gazepoint_engagement_dial(
        pd.DataFrame({"DIAL": pd.Series(dtype=float)})
    ).iloc[0]
    assert empty.n_rows == 0
    assert np.isnan(empty.usable_pct)

    no_validity = gp.audit_gazepoint_gsr_quality(
        pd.DataFrame({"GSR_US": [1.0, 2.0, 3.0]})
    ).iloc[0]
    assert no_validity.validity_column is None
    assert no_validity.usable_rows == 3


def test_window_summary_missing_validity_zero_and_empty_stat_branches(tmp_path):
    with pytest.raises(ValueError, match="could not be determined"):
        gp.summarise_gazepoint_gsr_windows(pd.DataFrame({"X": [1.0]}))
    with pytest.raises(ValueError, match="value_column"):
        gp.summarise_gazepoint_hr_windows(
            pd.DataFrame({"HR": [70.0]}), value_column="missing"
        )

    no_validity = gp.summarise_gazepoint_hr_windows(
        pd.DataFrame({"group": ["A", "A"], "HR": [0.0, 70.0]}),
        group_columns="group",
        validity_column="missing",
        exclude_zero=False,
    ).iloc[0]
    assert no_validity.validity_column is None
    assert no_validity.usable_rows == 2
    assert no_validity.first_value == 0
    assert no_validity.last_value == 70
    assert no_validity.change_value == 70

    one = gp.summarise_gazepoint_hr_windows(
        pd.DataFrame({"HR": [70.0, np.nan], "HRV": [1, 0]})
    ).iloc[0]
    assert one.usable_rows == 1
    assert np.isnan(one.sd_value)

    none = gp.summarise_gazepoint_hr_windows(
        pd.DataFrame({"HR": [0.0, np.nan], "HRV": [0, 0]})
    ).iloc[0]
    assert none.usable_rows == 0
    assert np.isnan(none.mean_value)
    assert np.isnan(none.change_value)

    path = tmp_path / "multi.csv"
    pd.DataFrame(
        {
            "GSR_US": [1.0, 2.0],
            "GSRV": [1, 1],
            "HR": [70.0, 72.0],
            "HRV": [1, 1],
            "DIAL": [0.0, 1.0],
            "DIALV": [1, 1],
        }
    ).to_csv(path, index=False)
    multimodal = gp.summarise_gazepoint_multimodal_windows(path)
    assert multimodal.loc[0, "window"] == "all"
    assert multimodal.loc[0, "hr_mean_value"] == pytest.approx(71.0)


def test_signal_quality_compute_validation_and_degenerate_signal_branches():
    frame = pd.DataFrame({"signal": [1.0, 1.0, 1.0]})
    with pytest.raises(ValueError, match="at least one"):
        gp.compute_gazepoint_signal_quality(frame, signal_cols=[])
    with pytest.raises(ValueError, match="signal_cols"):
        gp.compute_gazepoint_signal_quality(frame, signal_cols=["missing"])
    with pytest.raises(TypeError, match="must be numeric"):
        gp.compute_gazepoint_signal_quality(
            pd.DataFrame({"signal": ["a", "b"]}), signal_cols="signal"
        )
    with pytest.raises(ValueError, match="group_cols"):
        gp.compute_gazepoint_signal_quality(
            frame, signal_cols="signal", group_cols="participant"
        )
    with pytest.raises(ValueError, match="flatline_tolerance"):
        gp.compute_gazepoint_signal_quality(
            frame, signal_cols="signal", flatline_tolerance=-1
        )
    with pytest.raises(ValueError, match="spike_z"):
        gp.compute_gazepoint_signal_quality(frame, signal_cols="signal", spike_z=0)
    with pytest.raises(ValueError, match="extreme_z"):
        gp.compute_gazepoint_signal_quality(
            frame, signal_cols="signal", extreme_z=np.inf
        )

    constant = gp.compute_gazepoint_signal_quality(frame, signal_cols="signal")
    assert constant.loc[0, "spike_count"] == 0
    assert constant.loc[0, "extreme_z_count"] == 0
    assert constant.loc[0, "segment_id"] == "all"

    short = gp.compute_gazepoint_signal_quality(
        pd.DataFrame({"signal": [1.0, np.nan]}), signal_cols="signal"
    )
    assert short.loc[0, "spike_count"] == 0
    assert short.loc[0, "extreme_z_count"] == 0

    empty = gp.compute_gazepoint_signal_quality(
        pd.DataFrame({"signal": pd.Series(dtype=float)}), signal_cols="signal"
    )
    assert empty.loc[0, "n_samples"] == 0
    assert np.isnan(empty.loc[0, "prop_missing"])


def test_signal_quality_classification_rule_and_missing_metric_branches():
    with pytest.raises(TypeError, match="data frame"):
        gp.classify_gazepoint_signal_quality([])
    with pytest.raises(ValueError, match="named list"):
        gp.classify_gazepoint_signal_quality(pd.DataFrame(), rules=[])
    with pytest.raises(ValueError, match="named list"):
        gp.classify_gazepoint_signal_quality(pd.DataFrame(), rules={"": 1})
    with pytest.raises(ValueError, match="finite numeric"):
        gp.classify_gazepoint_signal_quality(
            pd.DataFrame(), rules={"n_samples_review_below": np.inf}
        )

    quality = pd.DataFrame(
        {
            "n_samples": [5, 100],
            "prop_missing": [np.nan, 0.0],
            "finite_prop": [1.0, 1.0],
        }
    )
    classified = gp.classify_gazepoint_signal_quality(
        quality,
        rules={
            "prop_missing_exclude_at_or_above": None,
            "finite_prop_exclude_below": None,
            "flatline_prop_exclude_at_or_above": None,
            "long_missing_run_exclude_at_or_above": None,
            "long_constant_run_exclude_at_or_above": None,
        },
    )
    assert classified.loc[0, "quality_label"] == "review"
    assert "Metric missing: prop_missing" in classified.loc[0, "quality_warnings"]
    assert "Metric unavailable: flatline_prop" in classified.loc[0, "quality_warnings"]
    assert "prop_missing_exclude_at_or_above" not in classified.attrs["rules"]


def test_signal_quality_summary_and_plot_alternative_branches():
    bare = pd.DataFrame(
        {
            "signal": ["pupil", "pupil"],
            "condition": ["A", "B"],
            "n_samples": [10, 20],
            "prop_missing": [0.0, 0.1],
            "finite_prop": [1.0, 0.9],
            "flatline_prop": [0.0, 0.1],
            "long_missing_run": [0, 1],
            "long_constant_run": [0, 2],
            "spike_count": [0, 1],
            "extreme_z_count": [0, 1],
        }
    )
    summary = gp.summarize_gazepoint_signal_quality(bare, by=["signal", "condition"])
    assert len(summary) == 2
    assert "pass_n" not in summary.columns

    with pytest.raises(TypeError, match="data frame"):
        gp.summarize_gazepoint_signal_quality([], by="signal")
    with pytest.raises(ValueError, match="by"):
        gp.summarize_gazepoint_signal_quality(bare, by="missing")
    with pytest.raises(TypeError, match="data frame"):
        gp.plot_gazepoint_signal_quality([])
    with pytest.raises(ValueError, match="metric"):
        gp.plot_gazepoint_signal_quality(bare, metric="missing")
    with pytest.raises(ValueError, match="infer"):
        gp.plot_gazepoint_signal_quality(
            pd.DataFrame({"value": [1.0]}), metric="value"
        )
    with pytest.raises(ValueError, match="x"):
        gp.plot_gazepoint_signal_quality(bare, x="missing")
    with pytest.raises(ValueError, match="colour"):
        gp.plot_gazepoint_signal_quality(bare, x="signal", colour="missing")
    with pytest.raises(ValueError, match="facet"):
        gp.plot_gazepoint_signal_quality(bare, x="signal", facet="missing")

    classified = bare.assign(quality_label=["pass", "review"])
    bar = gp.plot_gazepoint_signal_quality(
        classified, metric="quality_label", x="condition"
    )
    assert isinstance(bar, matplotlib.figure.Figure)
    scatter = gp.plot_gazepoint_signal_quality(
        classified,
        metric="prop_missing",
        x="condition",
        colour="quality_label",
    )
    assert isinstance(scatter, matplotlib.figure.Figure)
