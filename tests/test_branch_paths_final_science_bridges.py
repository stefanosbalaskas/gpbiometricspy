from __future__ import annotations

import sys
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_automated_statistics_validation_and_nonholm_paths():
    with pytest.raises(ValueError, match="Missing required"):
        gp.run_gazepoint_automated_statistics(
            pd.DataFrame({"group": ["a", "b"]}),
            ["outcome"],
            "group",
        )

    with pytest.raises(TypeError, match="not numeric"):
        gp.run_gazepoint_automated_statistics(
            pd.DataFrame({"group": ["a", "a", "a", "b", "b", "b"], "outcome": list("abcdef")}),
            ["outcome"],
            "group",
        )

    dat = pd.DataFrame(
        {
            "group": ["a"] * 6 + ["b"] * 6,
            "complete": [1.0, 1.2, 0.8, 1.1, 0.9, 1.05, 2.0, 2.2, 1.8, 2.1, 1.9, 2.05],
            "sparse": [1.0, np.nan, np.nan, np.nan, np.nan, np.nan] + [2.0, np.nan, np.nan, np.nan, np.nan, np.nan],
        }
    )
    out = gp.run_gazepoint_automated_statistics(
        dat,
        ["complete", "sparse"],
        "group",
        p_adjust_method="none",
        min_group_n=3,
    )
    assert out["overview"].iloc[0]["status"] == "automated_statistics_partial"
    assert set(out["test_table"]["status"]) == {"test_completed", "insufficient_group_data"}


def test_cardiorespiratory_validation_nonstandardized_and_partial_paths():
    with pytest.raises(ValueError, match="Missing required"):
        gp.analyze_gazepoint_cardiorespiratory_causality(
            pd.DataFrame({"resp": [1.0, 2.0]}),
            "resp",
            "card",
        )

    n = 40
    t = np.arange(n, dtype=float)
    sufficient = pd.DataFrame(
        {
            "group": ["good"] * n,
            "time": t,
            "resp": np.sin(t / 4.0) + 0.05 * np.cos(t),
            "card": np.cos(t / 5.0) + 0.1 * np.sin(t / 3.0),
        }
    )
    short = pd.DataFrame(
        {
            "group": ["short"] * 5,
            "time": np.arange(5, dtype=float),
            "resp": np.arange(5, dtype=float),
            "card": np.arange(5, dtype=float) + 1.0,
        }
    )
    out = gp.analyze_gazepoint_cardiorespiratory_causality(
        pd.concat([sufficient, short], ignore_index=True),
        "resp",
        "card",
        time_col="time",
        group_cols="group",
        lag_order=2,
        min_rows=10,
        standardise=False,
    )
    assert out["overview"].iloc[0]["status"] == "cardiorespiratory_directionality_partial"
    assert set(out["causality_summary"]["status"]) == {"directionality_estimated", "insufficient_rows"}


def test_bootstrap_validation_median_and_empty_finite_paths():
    empty = pd.DataFrame(columns=["y", "condition"])
    with pytest.raises(ValueError, match="no rows"):
        gp.compare_gazepoint_conditions_bootstrap(empty, "y", "condition")

    with pytest.raises(ValueError, match="Missing columns"):
        gp.compare_gazepoint_conditions_bootstrap(
            pd.DataFrame({"condition": ["a", "b"]}),
            "y",
            "condition",
        )

    dat = pd.DataFrame(
        {
            "participant": ["p1", "p1", "p2", "p2", "p3", "p3"],
            "condition": ["a", "b"] * 3,
            "y": [1.0, 2.0, 2.0, 4.0, 3.0, 6.0],
        }
    )
    with pytest.raises(ValueError, match="participant_col"):
        gp.compare_gazepoint_conditions_bootstrap(dat, "y", "condition", paired=True)
    with pytest.raises(ValueError, match="n_boot"):
        gp.compare_gazepoint_conditions_bootstrap(dat, "y", "condition", n_boot=0)
    with pytest.raises(ValueError, match="conf_level"):
        gp.compare_gazepoint_conditions_bootstrap(dat, "y", "condition", conf_level=1.0)
    with pytest.raises(ValueError, match="exactly two"):
        gp.compare_gazepoint_conditions_bootstrap(
            pd.DataFrame({"condition": ["a", "b", "c"], "y": [1.0, 2.0, 3.0]}),
            "y",
            "condition",
            n_boot=2,
        )

    median = gp.compare_gazepoint_conditions_bootstrap(
        dat,
        "y",
        "condition",
        condition_levels=["a", "b"],
        statistic="median_difference",
        n_boot=5,
        seed=11,
    )
    assert median.iloc[0]["statistic"] == "median_difference"
    assert np.isfinite(median.iloc[0]["estimate"])

    nan_dat = pd.DataFrame(
        {
            "condition": ["a", "a", "b", "b"],
            "y": [1.0, 2.0, np.nan, np.nan],
        }
    )
    nan_out = gp.compare_gazepoint_conditions_bootstrap(
        nan_dat,
        "y",
        "condition",
        condition_levels=["a", "b"],
        n_boot=3,
        seed=12,
        na_rm=False,
    )
    assert nan_out.iloc[0]["n_valid_boot"] == 0
    assert np.isnan(nan_out.iloc[0]["ci_low"])


def test_ctsi_and_cvxeda_tau_validation_and_failure_paths():
    with pytest.raises(ValueError, match="Missing required"):
        gp.prepare_gazepoint_ctsi_input(pd.DataFrame({"CNT": [0.0, 100.0]}))

    ctsi = gp.prepare_gazepoint_ctsi_input(
        pd.DataFrame({"CNT": [0.0, 100.0, 200.0], "GSR_US": [1.0, 1.1, 1.2]})
    )
    assert ctsi["event_table"].empty
    assert ctsi["written_files"] == []
    assert ctsi["overview"].iloc[0]["status"] == "ctsi_input_prepared"

    with pytest.raises(ValueError, match="tau0_grid"):
        gp.optimize_gazepoint_cvxeda_tau(
            pd.DataFrame({"CNT": [0.0, 1.0], "GSR_US": [1.0, 1.1]}),
            tau0_grid=[0.5],
            tau1=0.7,
        )

    short = gp.optimize_gazepoint_cvxeda_tau(
        pd.DataFrame({"CNT": np.arange(5, dtype=float), "GSR_US": np.linspace(1.0, 1.2, 5)}),
        tau0_grid=[2.0],
        tau1=0.7,
        sampling_rate=10.0,
    )
    assert short["overview"].iloc[0]["status"] == "cvxeda_tau_optimization_failed"
    assert short["best_tau"].iloc[0]["status"] == "best_tau_not_selected"

    good = pd.DataFrame(
        {
            "group": ["good"] * 24,
            "CNT": np.arange(24, dtype=float) / 10.0,
            "GSR_US": 1.0 + 0.05 * np.sin(np.arange(24) / 3.0),
        }
    )
    bad = pd.DataFrame(
        {
            "group": ["bad"] * 5,
            "CNT": np.arange(5, dtype=float) / 10.0,
            "GSR_US": np.linspace(1.0, 1.1, 5),
        }
    )
    partial = gp.optimize_gazepoint_cvxeda_tau(
        pd.concat([good, bad], ignore_index=True),
        group_cols="group",
        tau0_grid=[2.0],
        tau1=0.7,
        sampling_rate=10.0,
        max_irf_seconds=1.0,
    )
    assert partial["overview"].iloc[0]["status"] == "cvxeda_tau_optimization_partial"


def test_pipeline_blueprint_and_runner_validation_paths():
    with pytest.raises(ValueError, match="include_external_bridges"):
        gp.create_gazepoint_eda_analysis_pipeline(include_external_bridges="yes")
    with pytest.raises(ValueError, match="Invalid `style`"):
        gp.create_gazepoint_eda_analysis_pipeline(style="wide")

    blueprint = gp.create_gazepoint_eda_analysis_pipeline(
        include_external_bridges=False,
        include_model_templates=False,
        include_reporting_guidance=False,
    )
    assert blueprint["model_templates"].empty
    assert blueprint["reporting_guidance"].empty
    assert not (blueprint["function_map"]["phase"] == 3).any()

    with pytest.raises(ValueError, match="was not found"):
        gp.run_gazepoint_eda_analysis_pipeline(
            data=pd.DataFrame({"CNT": np.arange(5, dtype=float)}),
            eda_col="missing",
        )

    with pytest.raises(ValueError, match="was not found"):
        gp.run_gazepoint_eda_analysis_pipeline(
            data=pd.DataFrame({"CNT": np.arange(5, dtype=float), "GSR_US": np.linspace(1.0, 1.2, 5)}),
            group_cols="missing_group",
        )


def test_xdf_nonflattened_public_path(tmp_path, monkeypatch):
    path = tmp_path / "branch.xdf"
    path.write_bytes(b"xdf")
    fake = ModuleType("fake_pyxdf_branch")
    fake.load_xdf = lambda _: (
        [
            {
                "info": {"name": ["Gazepoint Gaze"]},
                "time_stamps": [1.0, 2.0],
                "time_series": [[10.0], [20.0]],
            }
        ],
        {"header": "ok"},
    )
    monkeypatch.setitem(sys.modules, "fake_pyxdf_branch", fake)

    out = gp.import_gazepoint_lsl_xdf(
        path,
        flatten=False,
        pyxdf_module="fake_pyxdf_branch",
    )
    assert out["overview"].iloc[0]["selected_stream_count"] == 1
    assert out["overview"].iloc[0]["flattened_rows"] == 0
    assert out["data"] is None


def test_online_design_and_pspm_dcm_validation_and_default_paths():
    with pytest.raises(ValueError, match="Missing required"):
        gp.run_gazepoint_online_design_optimization(
            pd.DataFrame({"condition": ["a", "b"]})
        )

    candidates = pd.DataFrame(
        {
            "condition": ["a", "b"],
            "expected_utility": [1.0, 1.2],
            "cost": [0.1, 0.0],
        }
    )
    previous = pd.DataFrame({"condition": ["a", "a", "b"]})
    ranked = gp.run_gazepoint_online_design_optimization(
        candidates,
        cost_col="cost",
        previous_assignments=previous,
        maximise=False,
    )
    assert len(ranked["ranked_candidates"]) == 2
    assert ranked["overview"].iloc[0]["previous_assignment_count"] == 3

    with pytest.raises(ValueError, match="Missing required"):
        gp.prepare_gazepoint_pspm_dcm_input(pd.DataFrame({"CNT": [0.0, 1.0]}))

    dcm = gp.prepare_gazepoint_pspm_dcm_input(
        pd.DataFrame({"CNT": [0.0, 100.0, 200.0], "GSR_US": [1.0, 1.1, 1.2]})
    )
    assert dcm["event_table"].empty
    assert dcm["written_files"] == []
    assert dcm["overview"].iloc[0]["status"] == "pspm_dcm_input_prepared"


def test_scr_multiverse_validation_failed_partial_and_model_paths():
    with pytest.raises(ValueError, match="Missing required"):
        gp.run_gazepoint_scr_multiverse(pd.DataFrame({"time": [0.0, 1.0]}))

    failed = gp.run_gazepoint_scr_multiverse(
        pd.DataFrame({"time": [-1.0, 0.0], "GSR_US": [1.0, 1.1]}),
        latency_windows=((1.0, 2.0),),
        thresholds=(0.01,),
        baseline_methods=("none",),
        response_metrics=("range",),
    )
    assert failed["overview"].iloc[0]["status"] == "scr_multiverse_failed"
    assert (failed["scored_trials"]["status"] == "no_response_window_samples").all()

    partial_dat = pd.DataFrame(
        {
            "trial": ["t1", "t1", "t1", "t2", "t2"],
            "time": [-1.0, 0.0, 1.5, -1.0, 0.0],
            "event": [0.0] * 5,
            "GSR_US": [1.0, 1.0, 1.5, 2.0, 2.0],
        }
    )
    partial = gp.run_gazepoint_scr_multiverse(
        partial_dat,
        trial_cols="trial",
        event_time_col="event",
        latency_windows=((1.0, 2.0),),
        thresholds=(0.01,),
        baseline_methods=("median",),
        response_metrics=("range",),
        model_function=lambda d: {"rows": len(d)},
    )
    assert partial["overview"].iloc[0]["status"] == "scr_multiverse_partial"
    assert partial["model_results"]["spec_1"]["rows"] == 2
