from __future__ import annotations

import math
from pathlib import Path

import matplotlib.figure
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def _cluster_frame(n_subjects: int = 6, n_time: int = 8) -> pd.DataFrame:
    rows = []
    for subject in range(n_subjects):
        for condition in ("A", "B"):
            for time in range(n_time):
                value = subject * 0.01 + time * 0.02
                if condition == "B" and 2 <= time <= 5:
                    value += 1.0
                rows.append(
                    {
                        "participant": f"P{subject + 1:02d}",
                        "condition": condition,
                        "time": float(time),
                        "value": value,
                    }
                )
    return pd.DataFrame(rows)


def _report_audit(overview: dict[str, object], warnings=None) -> dict[str, object]:
    return {
        "overview": pd.DataFrame([overview]),
        "warnings": [] if warnings is None else warnings,
    }


def _report_log(include_stage: bool = True) -> dict[str, object]:
    data = {"decision": ["retain", "review"]}
    if include_stage:
        data["stage"] = ["quality_control", "reporting"]
    return {"decisions": pd.DataFrame(data)}


def test_cluster_preparation_alternative_paths_and_guardrails():
    raw = _cluster_frame()
    duplicated = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
    prep = gp.prepare_gazepoint_timecourse_test_data(
        duplicated,
        "value",
        "time",
        "condition",
        "participant",
        time_bin_width=2,
        aggregation="median",
    )
    assert prep.attrs["gpbiometrics_settings"]["aggregation"] == "median"
    assert prep["time"].nunique() == 4

    incomplete = raw.drop(index=0)
    loose = gp.prepare_gazepoint_timecourse_test_data(
        incomplete,
        "value",
        "time",
        "condition",
        "participant",
        require_complete=False,
    )
    assert len(loose) == len(incomplete)
    with pytest.raises(ValueError, match="complete participant"):
        gp.prepare_gazepoint_timecourse_test_data(
            incomplete,
            "value",
            "time",
            "condition",
            "participant",
            require_complete=True,
        )

    with pytest.raises(ValueError, match="aggregation"):
        gp.prepare_gazepoint_timecourse_test_data(raw, "value", "time", "condition", "participant", aggregation="sum")
    with pytest.raises(TypeError, match="outcome_col"):
        gp.prepare_gazepoint_timecourse_test_data(raw.assign(value="x"), "value", "time", "condition", "participant")
    with pytest.raises(TypeError, match="time_col"):
        gp.prepare_gazepoint_timecourse_test_data(raw.assign(time="x"), "value", "time", "condition", "participant")
    with pytest.raises(ValueError, match="time_bin_width"):
        gp.prepare_gazepoint_timecourse_test_data(raw, "value", "time", "condition", "participant", time_bin_width=0)
    with pytest.raises(ValueError, match="No complete finite rows"):
        gp.prepare_gazepoint_timecourse_test_data(raw.assign(value=np.nan), "value", "time", "condition", "participant")

    three = pd.concat([raw, raw.assign(condition="C")], ignore_index=True)
    with pytest.raises(ValueError, match="Exactly two condition"):
        gp.prepare_gazepoint_timecourse_test_data(three, "value", "time", "condition", "participant")
    with pytest.raises(ValueError, match="must be different"):
        gp.prepare_gazepoint_timecourse_test_data(raw, "value", "time", "condition", "participant", "A", "A")
    with pytest.raises(ValueError, match="not found"):
        gp.prepare_gazepoint_timecourse_test_data(raw, "value", "time", "condition", "participant", "A", "C")


def test_cluster_runner_negative_tail_null_case_and_reporting_paths():
    data = _cluster_frame()
    result = gp.run_gazepoint_cluster_permutation(
        data,
        n_permutations=31,
        tail="negative",
        seed=404,
    )
    assert result["settings"]["tail"] == "negative"
    assert len(result["clusters"]) >= 1
    assert set(result["clusters"]["direction"]) == {"negative"}

    summarized = gp.summarize_gazepoint_time_clusters(result, alpha=1.0)
    assert summarized["significant"].all()
    assert isinstance(
        gp.plot_gazepoint_cluster_permutation(result, show_all_clusters=True),
        matplotlib.figure.Figure,
    )
    assert isinstance(
        gp.plot_gazepoint_cluster_null_distribution(result, cluster_id=999),
        matplotlib.figure.Figure,
    )

    report = gp.report_gazepoint_cluster_permutation(
        {"clusters": pd.DataFrame()},
        include_assumptions=False,
    )
    assert "did not indicate" in report["text"]
    assert "Assumptions checked" not in report["text"]

    identical = data.copy()
    identical.loc[identical["condition"] == "B", "value"] = identical.loc[
        identical["condition"] == "A", "value"
    ].to_numpy()
    no_cluster = gp.run_gazepoint_cluster_permutation(identical, n_permutations=7, seed=2)
    assert no_cluster["clusters"].empty
    assert np.all(no_cluster["null_distribution"] == 0)

    with pytest.raises(TypeError, match="run_gazepoint_cluster_permutation"):
        gp.summarize_gazepoint_time_clusters({})
    with pytest.raises(ValueError, match="finite null distribution"):
        gp.plot_gazepoint_cluster_null_distribution({"null_distribution": [np.nan]})
    with pytest.raises(ValueError, match="within"):
        gp.run_gazepoint_cluster_permutation(data, design="between", n_permutations=3)
    with pytest.raises(ValueError, match="tail"):
        gp.run_gazepoint_cluster_permutation(data, tail="bad", n_permutations=3)
    with pytest.raises(ValueError, match="n_permutations"):
        gp.run_gazepoint_cluster_permutation(data, n_permutations=0)
    with pytest.raises(ValueError, match="Alpha"):
        gp.run_gazepoint_cluster_permutation(data, cluster_alpha=1.0, n_permutations=3)
    with pytest.raises(ValueError, match="At least three"):
        gp.run_gazepoint_cluster_permutation(_cluster_frame(n_subjects=2), n_permutations=3)


def test_cluster_simulation_grid_and_design_diagnostic_paths():
    with pytest.raises(ValueError, match="exactly two"):
        gp.simulate_gazepoint_cluster_timecourse_data(conditions=("A", "B", "C"))
    with pytest.raises(ValueError, match="effect_condition"):
        gp.simulate_gazepoint_cluster_timecourse_data(effect_condition="C")
    with pytest.raises(ValueError, match="at least two"):
        gp.simulate_gazepoint_cluster_timecourse_data(n_subjects=1)

    data = _cluster_frame(n_subjects=4, n_time=5)
    duplicated = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    audit = gp.audit_gazepoint_timecourse_grid(
        duplicated,
        "participant",
        "condition",
        "time",
        max_report_cells=1,
    )
    assert audit["summary"].iloc[0].duplicate_cells == 1
    assert math.isnan(audit["summary"].iloc[0].missing_values)
    assert len(audit["duplicate_cells"]) == 1

    between = pd.concat(
        [
            data.query("condition == 'A' and participant in ['P01', 'P02']"),
            data.query("condition == 'B' and participant in ['P03', 'P04']"),
        ],
        ignore_index=True,
    )
    diagnosis = gp.diagnose_gazepoint_cluster_design(
        between,
        "participant",
        "condition",
        "time",
        "value",
        design="between",
        min_subjects=10,
    )
    assert "between_subject_condition_presence" in set(diagnosis["checks"]["check"])
    assert not bool(diagnosis["checks"].query("check == 'supported_by_current_runner'")["passed"].iloc[0])
    with pytest.raises(ValueError, match="Invalid design"):
        gp.diagnose_gazepoint_cluster_design(data, "participant", "condition", "time", design="crossover")


def test_governance_decision_log_validation_and_serialization_paths(tmp_path):
    log = gp.create_gazepoint_analysis_decision_log()
    empty_summary = gp.summarise_gazepoint_decision_log(log)
    assert empty_summary["by_stage"].empty

    log = gp.add_gazepoint_decision(log, "qc", "signal", "retain", value=[-1, 0])
    log = gp.add_gazepoint_decision(log, "model", "parameter", "set", value=[1, 2, 3])
    log = gp.add_gazepoint_decision(log, "report", "note", "record", value=None)
    assert log["value"].tolist() == ["start=-1; end=0", "0=1; 1=2; 2=3", ""]

    with pytest.raises(TypeError, match="create_gazepoint_analysis_decision_log"):
        gp.summarise_gazepoint_decision_log(pd.DataFrame())
    with pytest.raises(ValueError, match="stage"):
        gp.add_gazepoint_decision(log, "", "signal", "retain")
    with pytest.raises(ValueError, match="object_type"):
        gp.add_gazepoint_decision(log, "qc", "", "retain")
    with pytest.raises(ValueError, match="decision"):
        gp.add_gazepoint_decision(log, "qc", "signal", "")
    with pytest.raises(ValueError, match="path"):
        gp.write_gazepoint_decision_log(log, "")

    path = tmp_path / "decision.csv"
    gp.write_gazepoint_decision_log(log, path)
    assert path.exists()
    with pytest.raises(FileExistsError):
        gp.write_gazepoint_decision_log(log, path)


def test_governance_pipeline_customization_and_audit_guardrails():
    with pytest.raises(ValueError, match="include_default"):
        gp.create_gazepoint_pipeline_map(include_default="yes")
    with pytest.raises(ValueError, match="pipeline_id"):
        gp.create_gazepoint_pipeline_map(pipeline_id="")
    with pytest.raises(ValueError, match="steps"):
        gp.create_gazepoint_pipeline_map(include_default=False)
    with pytest.raises(ValueError, match="step_id"):
        gp.create_gazepoint_pipeline_map(pd.DataFrame({"label": ["x"]}), include_default=False)
    with pytest.raises(ValueError, match="non-empty"):
        gp.create_gazepoint_pipeline_map(pd.DataFrame({"step_id": [""]}), include_default=False)
    with pytest.raises(ValueError, match="unique"):
        gp.create_gazepoint_pipeline_map(pd.DataFrame({"step_id": ["a", "a"]}), include_default=False)

    steps = pd.DataFrame({"step_id": ["import", "model", "report"]})
    pipeline = gp.create_gazepoint_pipeline_map(steps, include_default=False)
    assert len(pipeline["edges"]) == 2
    assert set(["label", "domain", "description", "required", "status", "notes"]).issubset(pipeline["nodes"])

    one = gp.create_gazepoint_pipeline_map(pd.DataFrame({"step_id": ["only"]}), include_default=False)
    assert one["edges"].empty

    edges = pd.DataFrame({"from": ["import"], "to": ["report"]})
    custom = gp.create_gazepoint_pipeline_map(steps, edges=edges, include_default=False)
    assert custom["edges"].iloc[0].edge_type == "required"
    with pytest.raises(ValueError, match="missing required columns"):
        gp.create_gazepoint_pipeline_map(steps, edges=pd.DataFrame({"from": ["import"]}), include_default=False)
    with pytest.raises(ValueError, match="unknown step"):
        gp.create_gazepoint_pipeline_map(
            steps,
            edges=pd.DataFrame({"from": ["import"], "to": ["missing"]}),
            include_default=False,
        )

    direct = gp.audit_gazepoint_pipeline_steps(steps, expected_steps=["import", "report"], allow_extra=False)
    assert direct["summary"].iloc[0].n_warn >= 1
    with pytest.raises(ValueError, match="allow_extra"):
        gp.audit_gazepoint_pipeline_steps(pipeline, allow_extra="yes")
    with pytest.raises(ValueError, match="character"):
        gp.audit_gazepoint_pipeline_steps(pipeline, expected_steps=[1])
    with pytest.raises(TypeError, match="pipeline"):
        gp.audit_gazepoint_pipeline_steps({})

    with pytest.raises(ValueError, match="graph_name"):
        gp.export_gazepoint_pipeline_dot(pipeline, graph_name="")
    with pytest.raises(ValueError, match="rankdir"):
        gp.export_gazepoint_pipeline_dot(pipeline, rankdir="")
    with pytest.raises(ValueError, match="include_descriptions"):
        gp.export_gazepoint_pipeline_dot(pipeline, include_descriptions="yes")
    assert "\\n" not in gp.export_gazepoint_pipeline_dot(pipeline, include_descriptions=False)


def test_governance_audit_index_summary_and_markdown_paths():
    empty = gp.create_gazepoint_audit_index()
    assert empty.empty
    empty_summary = gp.summarize_gazepoint_audit_trail(empty)
    assert empty_summary.empty

    manual = pd.DataFrame(
        {
            "check": ["schema", "timing"],
            "status": ["complete", "mystery"],
            "message": ["ok", "review"],
        }
    )
    recorded = {"metadata": "kept"}
    index = gp.create_gazepoint_audit_index(
        [manual, recorded],
        audit_ids=["manual", "recorded"],
        include_summary_rows=True,
    )
    assert set(index["audit_id"]) == {"manual", "recorded"}
    assert {"pass", "other", "recorded"}.issubset(set(index["status"]))

    grouped = gp.summarize_gazepoint_audit_trail(index, by="audit_id")
    assert len(grouped) == 2
    assert grouped["needs_review"].any()
    markdown = gp.export_gazepoint_audit_trail_markdown(
        index,
        summary=grouped,
        include_details=False,
    )
    assert "## Summary" in markdown and "## Details" not in markdown

    with pytest.raises(ValueError, match="include_summary_rows"):
        gp.create_gazepoint_audit_index(manual, include_summary_rows="yes")
    with pytest.raises(ValueError, match="audit_ids"):
        gp.create_gazepoint_audit_index([manual, manual], audit_ids=["one"])
    with pytest.raises(TypeError, match="audits"):
        gp.create_gazepoint_audit_index(1)
    with pytest.raises(TypeError, match="data frame"):
        gp.summarize_gazepoint_audit_trail([])
    with pytest.raises(ValueError, match="known column"):
        gp.summarize_gazepoint_audit_trail(index, by="missing")
    with pytest.raises(TypeError, match="summary"):
        gp.export_gazepoint_audit_trail_markdown(index, summary={})
    with pytest.raises(ValueError, match="title"):
        gp.export_gazepoint_audit_trail_markdown(index, title="")
    with pytest.raises(ValueError, match="include_details"):
        gp.export_gazepoint_audit_trail_markdown(index, include_details="yes")
    with pytest.raises(ValueError, match="max_details"):
        gp.export_gazepoint_audit_trail_markdown(index, max_details=-1)


def test_reporting_optional_content_warning_and_validation_paths():
    export = _report_audit(
        {"n_files": 3, "n_readable_files": 2, "n_read_errors": 1},
        warnings=pd.DataFrame([{"code": "read", "message": "one unreadable file"}]),
    )
    design = _report_audit(
        {"n_participants": 4, "n_trials": 8, "n_conditions": 2},
        warnings=["small sample"],
    )
    event = _report_audit(
        {"n_units": 8, "n_expected_events": 2, "n_complete_units": 6, "complete_unit_prop": 0.75},
        warnings="event mismatch",
    )
    condition = _report_audit(
        {
            "n_participants": 4,
            "n_conditions": 2,
            "n_trials": 7,
            "trial_imbalance_ratio": np.nan,
            "complete_participant_condition_grid": False,
        }
    )

    methods = gp.create_gazepoint_methods_section(
        export_profile=export,
        design_audit=design,
        event_audit=event,
        condition_audit=condition,
        decision_log=_report_log(include_stage=False),
        package_version="0.1.4.dev0",
        validation={"schema": "pass"},
        include_guardrails=False,
    )
    assert "incomplete" in str(methods)
    assert "Package validation" in str(methods)
    assert "not interpreted as direct measures" not in str(methods)

    supplement = gp.create_gazepoint_qc_supplement(
        export_profile=export,
        design_audit=design,
        event_audit=event,
        condition_audit=condition,
        decision_log=_report_log(),
        title="QC",
    )
    assert "one unreadable file" in str(supplement)
    assert "Decision counts by stage" in str(supplement)

    reproducibility = gp.create_gazepoint_reproducibility_statement(
        decision_log=_report_log(),
        repository_url="https://example.test/repo",
        validation={"parity": "pass"},
        data_statement="Synthetic demonstration data only.",
        include_guardrails=False,
    )
    assert "https://example.test/repo" in str(reproducibility)
    assert "Synthetic demonstration data only" in str(reproducibility)
    assert "workflow is conservative" not in str(reproducibility)

    sparse = gp.create_gazepoint_reproducibility_statement(
        repository_url=np.nan,
        data_statement=np.nan,
    )
    assert "nan" not in str(sparse).lower()

    audit_report = gp.create_gazepoint_audit_report_section(
        export_profile=export,
        design_audit=design,
        event_audit=event,
        condition_audit=condition,
        decision_log=_report_log(),
        include_warnings=True,
    )
    assert "3 warning records" in str(audit_report)
    no_warnings = gp.create_gazepoint_audit_report_section(include_warnings=False)
    assert "Audit warnings" not in str(no_warnings)

    with pytest.raises(ValueError, match="named list"):
        gp.create_gazepoint_methods_section(validation={})
    with pytest.raises(ValueError, match="include_guardrails"):
        gp.create_gazepoint_methods_section(include_guardrails=None)
    with pytest.raises(ValueError, match="overview"):
        gp.create_gazepoint_methods_section(export_profile={"overview": []})
    with pytest.raises(ValueError, match="decision_log"):
        gp.create_gazepoint_methods_section(decision_log={})
    with pytest.raises(ValueError, match="data frame"):
        gp.create_gazepoint_methods_section(decision_log={"decisions": []})
