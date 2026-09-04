from pathlib import Path

import pandas as pd
import pytest

from studio.services import (
    MAX_UPLOAD_BYTES,
    annotation_signal_choices,
    annotations_frame,
    inspect_dataset,
    load_demo_dataset,
    load_uploaded_dataset,
    run_advanced_qc,
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


def test_studio_choice_and_annotation_helpers():
    data = pd.DataFrame({"TIME": [0.0], "CNT": [1], "GSR_US": [1.1], "HR": [70]})
    assert time_column_choices(data)[:2] == ["TIME", "CNT"]
    assert annotation_signal_choices(data) == ["GSR_US"]
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
    from studio.modules.qc import qc_server, qc_ui

    assert app is not None
    assert annotation_ui is not None and annotation_server is not None
    assert qc_ui is not None and qc_server is not None
