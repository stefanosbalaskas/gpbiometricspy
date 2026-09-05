from __future__ import annotations

from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_plot_contract_validation_fallback_and_collection_paths():
    fig = Figure()

    with pytest.raises(TypeError, match="matplotlib Figure"):
        gp.standardise_gazepoint_plot_contract("not-a-figure")
    with pytest.raises(TypeError, match="plot_data"):
        gp.standardise_gazepoint_plot_contract(fig, plot_data=[1, 2])
    with pytest.raises(TypeError, match="settings"):
        gp.standardise_gazepoint_plot_contract(fig, settings=["bad"])
    with pytest.raises(TypeError, match="interpretation_notes"):
        gp.standardise_gazepoint_plot_contract(fig, interpretation_notes=1)
    with pytest.raises(TypeError, match="plot_type"):
        gp.standardise_gazepoint_plot_contract(fig, plot_type=1)

    with pytest.raises(TypeError, match="require_plot_data"):
        gp.check_gazepoint_plot_contract(fig, require_plot_data="yes")
    with pytest.raises(TypeError, match="require_settings"):
        gp.check_gazepoint_plot_contract(fig, require_settings="yes")

    raw = gp.check_gazepoint_plot_contract(
        fig, require_plot_data=False, require_settings=False
    )
    assert raw["overview"].loc[0, "status"] == "warn_partial_plot_contract"
    with pytest.raises(ValueError, match="plot_data"):
        gp.get_gazepoint_plot_data(fig)
    with pytest.raises(ValueError, match="settings"):
        gp.get_gazepoint_plot_settings(fig)

    data = pd.DataFrame({"x": [1, 2]})
    fig._gazepoint_plot_data = data
    fig._gazepoint_settings = {
        "plot_type": "trace",
        "interpretation_notes": ["descriptive"],
    }
    contracted = gp.standardise_gazepoint_plot_contract(fig)
    checked = gp.check_gazepoint_plot_contract(contracted)
    assert checked["overview"].loc[0, "status"] == "pass_plot_contract"
    assert gp.get_gazepoint_plot_data(contracted).equals(data)
    assert gp.get_gazepoint_plot_settings(contracted)["plot_type"] == "trace"

    singleton = gp.standardize_gazepoint_plot_contracts(
        Figure(),
        settings={"plot_type": "single"},
        interpretation_notes="single",
    )
    assert singleton._gazepoint_plot_contract is True
    assert singleton._gazepoint_plot_type == "single"

    with pytest.raises(TypeError, match="list of plot objects"):
        gp.standardize_gazepoint_plot_contracts(123)
    assert gp.standardize_gazepoint_plot_contracts([]) == []
    assert gp.standardize_gazepoint_plot_contracts({}) == {}

    f1, f2 = Figure(), Figure()
    collection = gp.standardize_gazepoint_plot_contracts(
        {"a": f1, "b": f2},
        plot_data=[pd.DataFrame({"v": [1]}), pd.DataFrame({"v": [2]})],
        settings=[{"source": "a"}, {"source": "b"}],
        interpretation_notes=["first", "second"],
        plot_type=["line", "points"],
    )
    assert set(collection) == {"a", "b"}
    assert gp.get_gazepoint_plot_settings(collection["b"])["source"] == "b"
    assert collection["a"]._gazepoint_plot_type == "line"


def test_within_unit_standardization_validation_reference_and_zero_sd_paths():
    with pytest.raises(ValueError, match="zero_sd_action"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), zero_sd_action="bad"
        )
    with pytest.raises(ValueError, match="suffix"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), suffix=""
        )
    with pytest.raises(ValueError, match="min_valid"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), min_valid=0
        )
    with pytest.raises(ValueError, match="No common numeric"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"label": ["a", "b"]})
        )
    with pytest.raises(TypeError, match="not numeric"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"sig": ["a", "b"]}), signal_cols="sig"
        )
    with pytest.raises(ValueError, match="unit_cols"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"sig": [1.0, 2.0]}),
            signal_cols="sig",
            unit_cols="missing",
        )
    with pytest.raises(ValueError, match="not found"):
        gp.standardize_gazepoint_biometrics_within_unit(
            pd.DataFrame({"sig": [1.0, 2.0]}),
            signal_cols="sig",
            reference_col="missing",
        )

    existing = pd.DataFrame({"sig": [1.0, 2.0], "sig_z_within": [0.0, 0.0]})
    with pytest.raises(ValueError, match="already exist"):
        gp.standardize_gazepoint_biometrics_within_unit(
            existing, signal_cols="sig"
        )

    mixed = pd.DataFrame(
        {
            "participant": ["P1", "P1", "P1", "P2", "P2"],
            "baseline": [True, True, False, True, False],
            "sig": [1.0, 3.0, 5.0, 10.0, 12.0],
        }
    )
    partial = gp.standardize_gazepoint_biometrics_within_unit(
        mixed,
        signal_cols="sig",
        unit_cols="participant",
        reference_col="baseline",
        min_valid=2,
    )
    params = partial.attrs["standardization_parameters"]
    assert set(params.status) == {"standardized", "insufficient_reference_rows"}
    assert partial.attrs["standardization_summary"].loc[0, "status"] == "within_unit_standardization_partial"

    zero_sd = gp.standardize_gazepoint_biometrics_within_unit(
        pd.DataFrame({"participant": ["P1", "P1"], "sig": [2.0, 2.0]}),
        signal_cols="sig",
        unit_cols="participant",
        zero_sd_action="zero",
    )
    assert zero_sd.sig_z_within.tolist() == [0.0, 0.0]
    assert zero_sd.attrs["standardization_parameters"].loc[0, "status"] == "zero_or_missing_sd"

    unchanged_scale = gp.standardise_gazepoint_biometrics_within_unit(
        pd.DataFrame({"sig": [2.0, 4.0, 6.0]}),
        signal_cols="sig",
        unit_cols=[],
        center=False,
        scale=False,
    )
    assert unchanged_scale.sig_z_within.tolist() == [2.0, 4.0, 6.0]


def test_rhrv_export_unit_filter_collapse_and_file_paths(tmp_path):
    with pytest.raises(ValueError, match="unit"):
        gp.export_gazepoint_rhrv_input(
            pd.DataFrame({"IBI_clean_ms": [800.0]}), unit="minutes"
        )
    with pytest.raises(ValueError, match="ibi_col"):
        gp.export_gazepoint_rhrv_input(pd.DataFrame({"x": [1.0]}))

    seconds = gp.export_gazepoint_rhrv_input(
        {
            "data": pd.DataFrame(
                {
                    "participant": ["P 1/?"] * 4,
                    "IBI_clean_ms": [0.8, 0.8, 0.9, 1.0],
                }
            )
        },
        unit="seconds",
        output_dir=tmp_path / "rhrv",
    )
    assert seconds["overview"].loc[0, "status"] == "rhrv_input_exported"
    assert seconds["overview"].loc[0, "detected_ibi_unit"] == "seconds"
    assert len(seconds["beat_table"]) == 3
    assert seconds["manifest"].file_path.notna().all()
    assert all("P_1" in p for p in seconds["manifest"].file_path)

    uncollapsed = gp.prepare_gazepoint_rhrv_input(
        pd.DataFrame({"IBI_clean_ms": [800.0, 800.0, 900.0]}),
        unit="ms",
        group_cols=[],
        collapse_repeated_intervals=False,
    )
    assert len(uncollapsed["beat_table"]) == 3

    empty = gp.export_gazepoint_rhrv_input(
        pd.DataFrame({"IBI_clean_ms": [100.0, 5000.0]}), group_cols=[]
    )
    assert empty["overview"].loc[0, "status"] == "fail_no_ibi_rows_for_export"


def test_neurokit_input_time_modes_files_and_crosscheck_skip(tmp_path):
    with pytest.raises(ValueError, match="eda_col"):
        gp.prepare_gazepoint_neurokit_eda_input(pd.DataFrame({"x": [1.0]}))
    with pytest.raises(ValueError, match="time_col"):
        gp.prepare_gazepoint_neurokit_eda_input(
            pd.DataFrame({"GSR_US": [1.0]}), time_col="missing"
        )

    sampled = gp.prepare_gazepoint_neurokit_eda_input(
        pd.DataFrame({"participant": ["P1"] * 3, "GSR_US": [1.0, 1.1, 1.2]}),
        sampling_rate=10,
        output_dir=tmp_path / "nk",
    )
    assert sampled["eda_table"].time_s.tolist() == [0.0, 0.1, 0.2]
    assert sampled["manifest"].file_path.notna().all()

    millis = gp.prepare_gazepoint_neurokit_eda_input(
        pd.DataFrame({"time": [100.0, 120.0, 140.0], "GSR_US": [1.0, 1.1, 1.2]}),
        time_col="time",
        group_cols=[],
    )
    assert millis["eda_table"].time_s.tolist() == [0.0, 0.02, 0.04]

    no_time = gp.prepare_gazepoint_neurokit_eda_input(
        pd.DataFrame({"GSR_US": [1.0, 2.0]}), group_cols=[]
    )
    assert no_time["eda_table"].time_s.isna().all()

    no_finite_time = gp.prepare_gazepoint_neurokit_eda_input(
        pd.DataFrame({"time": [np.nan, np.nan], "GSR_US": [np.nan, np.nan]}),
        time_col="time",
        group_cols=[],
    )
    assert no_finite_time["eda_table"].time_s.isna().all()
    assert no_finite_time["group_summary"].loc[0, "status"] == "no_finite_eda"

    with pytest.raises(TypeError, match="execute"):
        gp.run_gazepoint_neurokit_eda_crosscheck(sampled, execute="yes")
    skipped = gp.run_gazepoint_neurokit_eda_crosscheck(sampled, execute=False)
    assert skipped["overview"].loc[0, "status"] == "skipped_execute_false"


def test_signal_lag_positive_negative_zero_spearman_and_insufficient_paths():
    frame = pd.DataFrame(
        {
            "x": [0.0, 1.0, 2.0, 4.0, 7.0, 11.0],
            "y": [1.0, 2.0, 4.0, 7.0, 11.0, 16.0],
            "time": np.arange(6.0),
        }
    )
    with pytest.raises(ValueError, match="Missing"):
        gp.estimate_gazepoint_signal_lag(frame, "x", "missing")
    with pytest.raises(ValueError, match="Missing"):
        gp.estimate_gazepoint_signal_lag(frame, "x", "y", time_col="missing")

    lag = gp.estimate_gazepoint_signal_lag(
        frame,
        "x",
        "y",
        time_col="time",
        max_lag=1,
        lag_step=1,
        method="spearman",
        min_complete_pairs=3,
    )
    assert lag["overview"].loc[0, "status"] == "estimated"
    assert set(lag["lag_profile"].lag) == {-1.0, 0.0, 1.0}

    differenced = gp.estimate_gazepoint_signal_lag(
        frame,
        "x",
        "y",
        max_lag=1,
        lag_step=1,
        min_complete_pairs=2,
        use_first_difference=True,
    )
    assert differenced["settings"]["use_first_difference"] is True

    insufficient = gp.estimate_gazepoint_signal_lag(
        pd.DataFrame({"x": [1.0, 1.0, 1.0], "y": [2.0, 2.0, 2.0]}),
        "x",
        "y",
        max_lag=1,
        min_complete_pairs=2,
    )
    assert insufficient["overview"].loc[0, "status"] == "no_valid_estimates"


def test_sync_drift_pair_construction_dataframe_and_status_paths():
    no_pairs = gp.audit_gazepoint_biometric_sync_drift(
        pd.DataFrame({"x": [1.0, 2.0]}), signal_cols="x"
    )
    assert no_pairs["overview"].loc[0, "status"] == "no_signal_pairs"

    df = pd.DataFrame(
        {
            "participant": ["A"] * 6 + ["B"] * 6,
            "x": [0, 1, 2, 4, 7, 11] * 2,
            "y": [1, 2, 4, 7, 11, 16] + [0, 0, 1, 2, 4, 7],
            "z": [0, 1, 2, 4, 7, 11] * 2,
        }
    )
    ref = gp.audit_gazepoint_biometric_sync_drift(
        df,
        group_cols="participant",
        signal_cols=["x", "y", "z"],
        reference_signal_col="x",
        max_lag=1,
        lag_step=1,
        min_complete_pairs=3,
        drift_tolerance=-1,
    )
    assert ref["overview"].loc[0, "signal_pair_count"] == 2
    assert ref["overview"].loc[0, "status"] == "review_sync_drift"

    automatic = gp.audit_gazepoint_biometric_sync_drift(
        df.iloc[:6],
        signal_cols=["x", "y"],
        max_lag=1,
        lag_step=1,
        min_complete_pairs=3,
    )
    assert automatic["overview"].loc[0, "signal_pair_count"] == 1

    pair_frame = pd.DataFrame({"signal_x": ["x"], "signal_y": ["y"]})
    framed = gp.audit_gazepoint_biometric_sync_drift(
        df.iloc[:6],
        signal_pairs=pair_frame,
        max_lag=1,
        lag_step=1,
        min_complete_pairs=3,
    )
    assert framed["drift_summary"].loc[0, "status"] == "within_tolerance"

    bad = gp.audit_gazepoint_biometric_sync_drift(
        pd.DataFrame({"x": [1.0, 1.0], "y": [2.0, 2.0]}),
        signal_pairs=[("x", "y")],
        max_lag=1,
        min_complete_pairs=2,
    )
    assert bad["drift_summary"].loc[0, "status"] == "insufficient_estimates"


def test_pyppg_input_time_finite_and_export_paths(tmp_path):
    with pytest.raises(ValueError, match="No usable HRP/PPG"):
        gp.prepare_gazepoint_pyppg_input(pd.DataFrame({"x": [1.0]}))
    with pytest.raises(ValueError, match="No usable HRP/PPG"):
        gp.prepare_gazepoint_pyppg_input(
            pd.DataFrame({"HRP": [1.0]}), ppg_col="missing"
        )
    with pytest.raises(ValueError, match="time_col"):
        gp.prepare_gazepoint_pyppg_input(
            pd.DataFrame({"HRP": [1.0]}), time_col="missing"
        )

    sample_only = gp.prepare_gazepoint_pyppg_input(
        pd.DataFrame({"HRP": [1.0, 2.0, 3.0]})
    )
    assert sample_only["group_summary"].loc[0, "status"] == "prepared_with_sample_index_only"
    assert sample_only["waveform_table"].time_s.isna().all()

    sampled = gp.prepare_gazepoint_pyppg_input(
        pd.DataFrame({"HRP": [1.0, 2.0, 3.0]}),
        sampling_rate=2,
        output_dir=tmp_path / "pyppg",
    )
    assert sampled["waveform_table"].time_s.tolist() == [0.0, 0.5, 1.0]
    assert len(sampled["manifest"]) == 2

    millis = gp.prepare_gazepoint_pyppg_input(
        pd.DataFrame({"time": [0.0, 20.0, 40.0], "PPG": [1.0, 2.0, 3.0]}),
        time_col="time",
        time_unit="auto",
    )
    assert millis["waveform_table"].time_s.tolist() == [0.0, 0.02, 0.04]

    all_missing_time = gp.prepare_gazepoint_pyppg_input(
        pd.DataFrame({"time": [np.nan, np.nan], "HRP": [1.0, np.nan]}),
        time_col="time",
        min_finite_prop=0.75,
    )
    assert all_missing_time["waveform_table"].time_s.isna().all()
    assert all_missing_time["group_summary"].loc[0, "status"] == "insufficient_finite_ppg"


def test_hrp_waveform_quality_fail_flat_gap_and_pass_paths():
    failed = gp.assess_gazepoint_hrp_waveform_quality(
        pd.DataFrame({"HRP": [1.0, np.nan, np.nan]}), min_rows=5
    )
    assert failed["overview"].loc[0, "status"] == "fail_review_required"

    flat = gp.assess_gazepoint_hrp_waveform_quality(
        pd.DataFrame({"HRP": [1.0] * 6}), min_rows=3, max_flat_prop=0.8
    )
    assert flat["group_quality"].loc[0, "status"] == "review_flat_signal"

    gap = gp.assess_gazepoint_hrp_waveform_quality(
        pd.DataFrame(
            {
                "time": [0.0, 1.0, 2.0, 20.0, 21.0, 22.0],
                "HRP": [0.0, 1.0, 0.0, 2.0, 0.0, 3.0],
            }
        ),
        time_col="time",
        min_rows=3,
        max_flat_prop=0.95,
        max_gap_multiplier=3,
    )
    assert gap["group_quality"].loc[0, "status"] == "review_time_gaps"
    assert gap["row_flags"].flag_large_time_gap.any()

    passed = gp.assess_gazepoint_hrp_waveform_quality(
        pd.DataFrame({"HRP": [0.0, 1.0, 0.0, 2.0, 0.0, 3.0]}),
        min_rows=3,
        max_flat_prop=0.95,
    )
    assert passed["overview"].loc[0, "status"] == "pass"


def test_eda_decomposition_validation_existing_components_and_time_sort_paths():
    with pytest.raises(ValueError, match="signal_col"):
        gp.decompose_gazepoint_eda(pd.DataFrame({"x": [1.0]}))
    with pytest.raises(TypeError, match="numeric"):
        gp.decompose_gazepoint_eda(
            pd.DataFrame({"sig": ["a", "b"]}), signal_col="sig"
        )
    with pytest.raises(ValueError, match="window_size"):
        gp.decompose_gazepoint_eda(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), window_size=0
        )
    with pytest.raises(ValueError, match="output_prefix"):
        gp.decompose_gazepoint_eda(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), output_prefix=""
        )
    with pytest.raises(ValueError, match="already exist"):
        gp.decompose_gazepoint_eda(
            pd.DataFrame({"GSR_US": [1.0], "eda_tonic": [1.0]}),
            output_prefix="eda",
        )

    existing = gp.decompose_gazepoint_eda(
        pd.DataFrame(
            {
                "GSR_US": [1.0, 2.0],
                "GSR_US_TONIC": [0.8, 1.8],
                "GSR_US_PHASIC": [0.2, 0.2],
            }
        )
    )
    assert existing.attrs["overview"].loc[0, "used_existing_components"]

    with pytest.raises(ValueError, match="time_col"):
        gp.decompose_gazepoint_eda(
            pd.DataFrame({"GSR_US": [1.0, 2.0]}), time_col="missing"
        )

    rolled = gp.decompose_gazepoint_eda(
        pd.DataFrame(
            {
                "participant": ["P1"] * 4,
                "time": [3.0, 1.0, np.nan, 2.0],
                "GSR_US": [3.0, 1.0, 4.0, 2.0],
            }
        ),
        time_col="time",
        group_cols="participant",
        window_size=4,
        output_prefix="custom",
    )
    assert rolled.attrs["settings"]["window_size"] == 5
    assert set(rolled.custom_decomposition_method) == {"rolling_median_residual"}


def test_scr_event_validation_decomposition_threshold_and_peak_replacement_paths():
    base = pd.DataFrame({"GSR_US": [0.0, 1.0, 0.0]})
    with pytest.raises(ValueError, match="phasic_col"):
        gp.detect_gazepoint_scr_events(base, phasic_col="missing")
    with pytest.raises(ValueError, match="signal_col"):
        gp.detect_gazepoint_scr_events(base, signal_col="missing")
    with pytest.raises(ValueError, match="threshold"):
        gp.detect_gazepoint_scr_events(base, threshold=np.nan)
    with pytest.raises(ValueError, match="min_peak_distance"):
        gp.detect_gazepoint_scr_events(base, min_peak_distance=0)
    with pytest.raises(ValueError, match="window_size"):
        gp.detect_gazepoint_scr_events(base, window_size=0)
    with pytest.raises(TypeError, match="phasic_col"):
        gp.detect_gazepoint_scr_events(
            pd.DataFrame({"bad": ["a", "b", "c"]}), phasic_col="bad"
        )

    decomp = gp.detect_gazepoint_scr_events(
        pd.DataFrame({"GSR_US": [0.0, 0.0, 2.0, 0.0, 0.0]}),
        signal_col="GSR_US",
        threshold=0.1,
        min_peak_distance=1,
        window_size=3,
    )
    assert decomp["overview"].loc[0, "decomposition_used"]

    replaced = gp.detect_gazepoint_scr_events(
        pd.DataFrame(
            {
                "time": np.arange(7.0),
                "GSR_US_PHASIC": [0.0, 2.0, 0.0, 3.0, 0.0, 0.0, 0.0],
            }
        ),
        time_col="time",
        threshold=0.5,
        min_peak_distance=4,
    )
    assert replaced["overview"].loc[0, "n_events"] == 1
    assert replaced["events"].peak_value.iloc[0] == 3.0

    empty_mad = gp.detect_gazepoint_scr_events(
        pd.DataFrame({"GSR_US_PHASIC": [np.nan, np.nan, np.nan]})
    )
    assert empty_mad["overview"].loc[0, "status"] == "no_scr_events_detected"

    none = gp.detect_gazepoint_scr_events(
        pd.DataFrame({"GSR_US_PHASIC": [0.0, 0.0, 0.0]}), threshold=1.0
    )
    assert none["overview"].loc[0, "status"] == "no_scr_events_detected"


def test_checklist_and_methods_active_inactive_and_caution_paths():
    failed = gp.create_gazepoint_biometrics_checklist(pd.DataFrame({"x": [1.0]}))
    assert failed["overview"].loc[0, "status"] == "fail_no_active_signal"

    review = gp.create_gazepoint_biometrics_checklist(
        pd.DataFrame({"x": [1.0]}), require_active_signal=False
    )
    assert review["overview"].loc[0, "status"] == "review_no_active_signal"

    active = gp.create_gazepoint_biometrics_checklist(
        pd.DataFrame(
            {
                "GSR_US": [1.0],
                "HR": [70.0],
                "DIAL": [0.5],
                "HRP": [0.2],
                "IBI": [800.0],
            }
        )
    )
    assert active["overview"].loc[0, "status"] == "ready"

    with pytest.raises(ValueError, match="Either"):
        gp.create_gazepoint_biometrics_methods_text()
    with pytest.raises(ValueError, match="checklist"):
        gp.create_gazepoint_biometrics_methods_text(checklist={})

    text = gp.create_gazepoint_biometrics_methods_text(
        checklist=active, include_cautions=False
    )
    assert "GSR/EDA channels" in text
    assert "heart rate channel" in text
    assert "engagement dial" in text
    assert "interpreted conservatively" not in text

    cautious = gp.create_gazepoint_biometrics_methods_text(
        data=pd.DataFrame({"GSR_US": [1.0]})
    )
    assert "interpreted conservatively" in cautious
