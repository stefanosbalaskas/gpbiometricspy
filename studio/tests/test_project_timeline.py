from __future__ import annotations

import pandas as pd

from studio.project_timeline import project_timeline
from studio.state import ProjectState


def _state_with_history() -> ProjectState:
    data = pd.DataFrame(
        {
            "TIME": [0.0, 0.1, 0.2],
            "GSR_US": [2.0, 2.1, 2.2],
            "HR": [70.0, 71.0, 72.0],
        }
    )
    state = ProjectState().with_project_name("Timeline pilot")
    state = state.with_dataset(
        data,
        source_name="private_participant_001.csv",
        validation={"valid": True},
        operation="load_upload",
    )
    state = state.with_qc({"validation": {"valid": True}})
    state = state.with_analysis(
        "eda_scr",
        {"status": "ok"},
        parameters={"signal_col": "GSR_US", "private_note": "not a timeline field"},
    )
    state = state.with_analysis("event_alignment", {"status": "ok"})
    state = state.with_analysis("statistics_modelling", {"status": "ok"})
    return state.with_operation("build_reporting_artifacts", raw_data_embedded=False)


def test_project_timeline_is_empty_for_a_new_session():
    timeline = project_timeline(ProjectState())
    assert timeline.empty
    assert list(timeline.columns) == [
        "step",
        "time_utc",
        "stage",
        "stage_order",
        "action",
        "detail",
        "status",
    ]


def test_project_timeline_classifies_the_research_journey_in_recorded_order():
    timeline = project_timeline(_state_with_history())

    assert timeline["step"].tolist() == list(range(1, len(timeline) + 1))
    assert timeline["stage"].tolist() == [
        "Project",
        "Project",
        "Quality",
        "Analyze",
        "Integrate",
        "Model",
        "Report",
    ]
    assert "Research dataset loaded" in timeline["action"].tolist()
    assert "EDA / SCR completed" in timeline["action"].tolist()
    assert "Events & Alignment completed" in timeline["action"].tolist()
    assert "Statistics & modelling completed" in timeline["action"].tolist()
    assert timeline.iloc[-1]["action"] == "Reporting artifacts built"
    assert timeline["time_utc"].str.endswith(" UTC").all()


def test_project_timeline_omits_source_filenames_raw_values_and_parameter_payloads():
    timeline = project_timeline(_state_with_history())
    rendered = timeline.to_string()

    assert "private_participant_001.csv" not in rendered
    assert "private_note" not in rendered
    assert "parameters_json" not in timeline.columns
    assert "GSR_US" not in rendered
    assert "source" not in timeline.columns
