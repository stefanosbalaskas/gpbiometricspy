from pathlib import Path

import pandas as pd
import pytest

from studio.services import (
    MAX_UPLOAD_BYTES,
    analysis_group_column_choices,
    annotation_signal_choices,
    annotations_frame,
    eda_analysis_tables,
    eda_reproducibility_script,
    eda_signal_choices,
    inspect_dataset,
    load_demo_dataset,
    load_uploaded_dataset,
    run_advanced_qc,
    run_eda_scr_analysis,
    run_qc,
    time_column_choices,
)
from studio.state import ProjectState


def test_project_state_records_dataset_and_qc_provenance():
    data = pd.DataFrame({"GSR_US": [1.0, 1.2], "CNT": [1, 2]})
    validation = {"issues": pd.DataFrame()}
    state = ProjectState().with_dataset(
        data,
        source_name="example.csv",
        validation=validation,
        operation="load_upload",
    )
    assert state.loaded
    assert state.n_rows == 2
    assert state.n_columns == 2
    assert state.provenance[-1]["operation"] == "load_upload"

    updated = state.with_qc({"missingness": pd.DataFrame()})
    assert updated.provenance[-1]["operation"] == "run_qc"


def test_project_state_rejects_qc_without_dataset():
    with pytest.raises(ValueError, match="dataset"):
        ProjectState().with_qc({})


def test_project_state_records_analysis_and_resets_it_with_new_dataset():
    data = pd.DataFrame({"CNT": [1, 2], "GSR_US": [1.0, 1.2]})
    state = ProjectState().with_dataset(
        data,
        source_name="example.csv",
        validation={"issues": pd.DataFrame()},
        operation="load_upload",
    )
    result = {"parameters": {"window_size": 31}}
    state = state.with_analysis("eda_scr", result, parameters={"window_size": 31})
    assert "eda_scr" in state.analyses
    assert state.provenance[-1]["operation"] == "run_eda_scr_analysis"
    assert '"window_size": 31' in state.provenance[-1]["parameters_json"]

    replacement = state.with_dataset(
        data.copy(),
        source_name="replacement.csv",
        validation={"issues": pd.DataFrame()},
        operation="load_upload",
    )
    assert replacement.analyses == {}


def test_project_state_rejects_analysis_without_dataset():
    with pytest.raises(ValueError, match="dataset"):
        ProjectState().with_analysis("eda_scr", {})


def test_annotation_state_add_remove_and_clear():
    data = pd.DataFrame({"TIME": [0.0, 0.1], "GSR_US": [1.0, 1.2]})
    state = ProjectState().with_dataset(
        data,
        source_name="example.csv",
        validation={"issues": pd.DataFrame()},
        operation="load_upload",
    )
    state = state.with_annotation(
        {
            "annotation_type": "manual_peak",
            "signal_col": "GSR_US",
            "time_col": "TIME",
            "time": 0.1,
            "start": None,
            "end": None,
            "note": "peak",
        }
    )
    state = state.with_annotation(
        {
            "annotation_type": "artifact_interval",
            "signal_col": "GSR_US",
            "time_col": "TIME",
            "time": None,
            "start": 0.0,
            "end": 0.1,
            "note": "artifact",
        }
    )
    assert len(state.annotations) == 2
    assert state.provenance[-1]["operation"] == "add_annotation"

    state = state.without_annotation(1)
    assert len(state.annotations) == 1
    assert state.annotations[0]["annotation_type"] == "artifact_interval"

    state = state.without_annotations()
    assert state.annotations == ()
    assert state.provenance[-1]["operation"] == "clear_annotations"


def test_demo_intake_and_qc_use_public_package_contract():
    data, source = load_demo_dataset()
    assert source == "Bundled synthetic kiosk demo"
    assert isinstance(data, pd.DataFrame)
    assert len(data) > 0

    validation = inspect_dataset(data)
    assert set(validation) >= {"overview", "active_channels", "issues"}

    qc = run_qc(data.head(2000).copy())
    assert set(qc) == {"validation", "missingness", "activity"}


def test_advanced_qc_uses_time_physiology_and_gaze_contracts():
    n = 12
    data = pd.DataFrame(
        {
            "TIME": [i / 60 for i in range(n)],
            "GSR_US": [1.0 + i * 0.01 for i in range(n)],
            "GSRV": [1] * n,
            "HR": [70 + (i % 3) for i in range(n)],
            "HRV": [1] * n,
            "FPOGX": [0.2 + i * 0.01 for i in range(n)],
            "FPOGY": [0.4 + i * 0.005 for i in range(n)],
            "FPOGV": [1] * n,
        }
    )
    qc = run_advanced_qc(data, time_col="TIME", expected_sampling_rate_hz=60)
    assert set(qc) >= {"time_resets", "gsr_quality", "hr_quality", "gaze_validation"}
    assert qc["time_resets"]["overview"].iloc[0]["status"] == "pass"
    assert qc["gaze_validation"]["summary"].iloc[0]["status"] in {"pass", "warn"}


def test_eda_scr_analysis_uses_public_package_contracts():
    phasic = [0.0] * 5 + [0.2, 0.8, 0.2] + [0.0] * 4 + [0.3, 0.9, 0.2] + [0.0] * 5
    data = pd.DataFrame(
        {
            "participant_id": ["p1"] * len(phasic),
            "CNT": list(range(1, len(phasic) + 1)),
            "GSR_US_TONIC": [1.0] * len(phasic),
            "GSR_US_PHASIC": phasic,
            "GSR_US": [1.0 + value for value in phasic],
        }
    )
    result = run_eda_scr_analysis(
        data,
        signal_col="GSR_US",
        time_col="CNT",
        group_col="participant_id",
        window_size=31,
        threshold=0.5,
        min_peak_distance=3,
    )
    assert set(result) == {"quality", "decomposition", "events", "summary", "parameters"}
    assert {"studio_eda_tonic", "studio_eda_phasic"}.issubset(result["decomposition"].columns)
    assert result["events"]["overview"].iloc[0]["n_events"] == 2
    assert result["events"]["overview"].iloc[0]["status"] == "scr_events_detected"
    tables = eda_analysis_tables(result)
    assert {"quality", "decomposition_overview", "events_overview", "events_events"}.issubset(tables)
    script = eda_reproducibility_script(result)
    assert "decompose_gazepoint_eda" in script
    assert "detect_gazepoint_scr_events" in script
    assert "summarise_gazepoint_gsr_tonic_phasic" in script


def test_eda_scr_analysis_validates_user_configuration():
    data = pd.DataFrame({"CNT": [1, 2, 3], "GSR_US": [1.0, 1.1, 1.0]})
    with pytest.raises(ValueError, match="signal"):
        run_eda_scr_analysis(data, signal_col="missing", time_col="CNT")
    with pytest.raises(ValueError, match="window"):
        run_eda_scr_analysis(data, signal_col="GSR_US", time_col="CNT", window_size=0)
    with pytest.raises(ValueError, match="peak distance"):
        run_eda_scr_analysis(data, signal_col="GSR_US", time_col="CNT", min_peak_distance=0)


def test_studio_choice_and_annotation_helpers():
    data = pd.DataFrame(
        {
            "TIME": [0.0],
            "CNT": [1],
            "participant_id": ["p1"],
            "GSR_US": [1.1],
            "HR": [70],
        }
    )
    assert time_column_choices(data)[:2] == ["TIME", "CNT"]
    assert annotation_signal_choices(data) == ["GSR_US"]
    assert eda_signal_choices(data) == ["GSR_US"]
    assert analysis_group_column_choices(data)[0] == "participant_id"
    table = annotations_frame(
        (
            {
                "annotation_type": "manual_peak",
                "signal_col": "GSR_US",
                "time_col": "TIME",
                "time": 0.0,
                "note": "x",
            },
        )
    )
    assert table.iloc[0]["row"] == 1
    assert table.iloc[0]["annotation_type"] == "manual_peak"


def test_upload_is_imported_through_package(tmp_path: Path):
    path = tmp_path / "example.csv"
    path.write_text("CNT,GSR_US,HR\n1,1.0,70\n2,1.2,71\n", encoding="utf-8")
    data, name = load_uploaded_dataset([
        {"name": "example.csv", "datapath": str(path), "size": path.stat().st_size}
    ])
    assert name == "example.csv"
    assert list(data.columns) == ["CNT", "GSR_US", "HR"]


def test_upload_guardrails_reject_extension_and_size(tmp_path: Path):
    path = tmp_path / "bad.exe"
    path.write_text("not,data\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_uploaded_dataset([{"name": "bad.exe", "datapath": str(path), "size": 10}])

    with pytest.raises(ValueError, match="100 MB"):
        load_uploaded_dataset([
            {"name": "large.csv", "datapath": str(path), "size": MAX_UPLOAD_BYTES + 1}
        ])


def test_studio_app_and_modules_import():
    from studio.app import app
    from studio.modules.annotation import annotation_server, annotation_ui
    from studio.modules.eda_scr import eda_scr_server, eda_scr_ui
    from studio.modules.qc import qc_server, qc_ui

    assert app is not None
    assert annotation_ui is not None and annotation_server is not None
    assert eda_scr_ui is not None and eda_scr_server is not None
    assert qc_ui is not None and qc_server is not None
