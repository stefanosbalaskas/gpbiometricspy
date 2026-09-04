from pathlib import Path

import pandas as pd
import pytest

from studio.services import (
    MAX_UPLOAD_BYTES,
    inspect_dataset,
    load_demo_dataset,
    load_uploaded_dataset,
    run_qc,
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


def test_demo_intake_and_qc_use_public_package_contract():
    data, source = load_demo_dataset()
    assert source == "Bundled synthetic kiosk demo"
    assert isinstance(data, pd.DataFrame)
    assert len(data) > 0

    validation = inspect_dataset(data)
    assert set(validation) >= {"overview", "active_channels", "issues"}

    qc = run_qc(data.head(2000).copy())
    assert set(qc) == {"validation", "missingness", "activity"}


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


def test_studio_app_imports():
    from studio.app import app

    assert app is not None
