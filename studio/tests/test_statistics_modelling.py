from __future__ import annotations

import importlib

import numpy as np
import pandas as pd

import gpbiometricspy as gp
from studio.statistics_services import (
    cluster_report_text,
    cluster_reproducibility_script,
    cluster_tables,
    lme_reproducibility_script,
    lme_tables,
    run_cluster_analysis,
    run_lme_preparation,
    statistics_source_choices,
    statistics_source_inventory,
    statistics_source_tables,
    unsupported_cluster_guardrails,
)


def _model_table() -> pd.DataFrame:
    rows = []
    for participant in ["P01", "P02", "P03", "P04"]:
        for trial, condition in [("T1", "control"), ("T2", "warning")]:
            rows.append(
                {
                    "participant": participant,
                    "trial": trial,
                    "condition": condition,
                    "summary_mean": 1.0 + (condition == "warning") * 0.25 + int(participant[-1]) * 0.01,
                    "baseline_mean": 0.8 + int(participant[-1]) * 0.01,
                    "age": 20 + int(participant[-1]),
                }
            )
    return pd.DataFrame(rows)


def _cluster_table(n_subjects: int = 8, n_time: int = 18) -> pd.DataFrame:
    return gp.simulate_gazepoint_cluster_timecourse_data(
        n_subjects=n_subjects,
        n_time=n_time,
        conditions=("control", "warning"),
        effect_start=7,
        effect_end=11,
        effect_size=0.8,
        seed=7,
    ).rename(columns={"subject": "participant"})


def test_statistics_sources_include_prior_studio_outputs():
    data = _model_table()
    event_samples = _cluster_table()
    event_summary = data.copy()
    analyses = {
        "multimodal": {
            "eventlocked": {"summary": event_summary, "samples": event_samples},
            "model_data": data.copy(),
        }
    }
    tables = statistics_source_tables(data, analyses)
    assert {"loaded_data", "multimodal_event_responses", "multimodal_event_samples", "multimodal_model_data"} <= set(tables)
    choices = statistics_source_choices(data, analyses)
    assert choices["multimodal_model_data"].startswith("Multimodal")
    inventory = statistics_source_inventory(data, analyses)
    assert set(inventory["source"]) >= {"loaded_data", "multimodal_event_samples"}


def test_lme_model_preparation_delegates_to_package_contract():
    table = _model_table()
    result = run_lme_preparation(
        table,
        outcome_col="summary_mean",
        fixed_effect_cols=["condition"],
        covariate_cols=["age"],
        participant_col="participant",
        trial_col="trial",
        baseline_col="baseline_mean",
        baseline_correct=True,
        factor_cols=["condition"],
        continuous_cols=["age"],
        scale_continuous=True,
        min_rows=4,
    )
    assert "condition" in result["model_formula"]
    assert "participant" in result["model_formula"]
    assert result["studio_parameters"]["baseline_correct"] is True
    tables = lme_tables(result)
    assert not tables["model_data"].empty
    assert "variable_summary" in tables
    script = lme_reproducibility_script(result)
    assert "prepare_gazepoint_biometrics_lme_data" in script
    assert "baseline_correct=True" in script


def test_cluster_permutation_valid_design_runs_with_diagnostics():
    table = _cluster_table()
    result = run_cluster_analysis(
        table,
        outcome_col="value",
        time_col="time",
        condition_col="condition",
        participant_col="participant",
        condition_a="control",
        condition_b="warning",
        time_bin_width=None,
        aggregation="mean",
        min_subjects=5,
        n_permutations=50,
        cluster_forming_alpha=0.05,
        cluster_alpha=0.05,
        tail="two.sided",
        seed=11,
        run_sensitivity=False,
    )
    assert result["status"] == "completed"
    assert result["diagnostic"]["passed"] is True
    assert result["cluster"]["class"] == "gazepoint_cluster_permutation"
    tables = cluster_tables(result)
    assert not tables["design_checks"].empty
    assert not tables["grid_summary"].empty
    assert not tables["cluster_timewise"].empty
    assert "global null" in cluster_report_text(result)
    script = cluster_reproducibility_script(result)
    assert "diagnose_gazepoint_cluster_design" in script
    assert "run_gazepoint_cluster_permutation" in script


def test_cluster_permutation_incomplete_grid_is_blocked_before_inference():
    table = _cluster_table()
    table = table.drop(index=table.index[0]).reset_index(drop=True)
    result = run_cluster_analysis(
        table,
        outcome_col="value",
        time_col="time",
        condition_col="condition",
        participant_col="participant",
        condition_a="control",
        condition_b="warning",
        min_subjects=5,
        n_permutations=20,
    )
    assert result["status"] == "design_blocked"
    assert result["diagnostic"]["passed"] is False
    assert "cluster" not in result
    checks = cluster_tables(result)["design_checks"]
    assert ((checks["check"] == "complete_grid") & (~checks["passed"])).any()
    assert "not run" in cluster_report_text(result).lower()


def test_cluster_binning_aggregates_repeated_samples_before_grid_diagnostic():
    base = _cluster_table(n_subjects=6, n_time=12)
    repeated = pd.concat(
        [
            base.assign(time=base["time"] + 0.01),
            base.assign(time=base["time"] + 0.04, value=base["value"] + 0.02),
        ],
        ignore_index=True,
    )
    result = run_cluster_analysis(
        repeated,
        outcome_col="value",
        time_col="time",
        condition_col="condition",
        participant_col="participant",
        condition_a="control",
        condition_b="warning",
        time_bin_width=1.0,
        min_subjects=5,
        n_permutations=20,
        seed=3,
    )
    assert result["status"] == "completed"
    prepared = result["prepared_data"]
    assert not prepared.duplicated(["participant", "condition", "time"]).any()


def test_unsupported_cluster_methods_remain_visible_guardrails():
    table = unsupported_cluster_guardrails()
    assert len(table) >= 5
    assert (table["studio_status"] == "not exposed").all()
    assert table["package_guardrail"].str.contains("cluster|tfce|estimate", case=False).all()


def test_statistics_module_and_app_import():
    importlib.import_module("studio.modules.statistics_modelling")
    importlib.import_module("studio.app")
