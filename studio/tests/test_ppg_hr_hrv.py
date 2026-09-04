import numpy as np
import pandas as pd
import pytest

from studio.ppg_services import (
    crosscheck_status_table,
    hr_signal_choices,
    ibi_signal_choices,
    ppg_hr_hrv_reproducibility_script,
    ppg_hr_hrv_tables,
    ppg_signal_choices,
    run_ppg_hr_hrv_analysis,
)
from studio.state import ProjectState


def _cardiac_frame(seconds: int = 20, fs: int = 60) -> pd.DataFrame:
    n = seconds * fs
    t = np.arange(n, dtype=float) / fs
    pulse = 1.0 + 0.65 * np.sin(2 * np.pi * 1.2 * t) + 0.08 * np.sin(2 * np.pi * 2.4 * t)
    ibi = np.full(n, np.nan)
    interval_values = np.array([0.82, 0.84, 0.81, 0.85, 0.83, 0.82, 0.86, 0.81, 0.84, 0.83, 0.82, 0.85])
    ibi[: len(interval_values)] = interval_values
    return pd.DataFrame(
        {
            "participant_id": "P01",
            "TIME": t,
            "HRP": pulse,
            "HR": 72 + 2 * np.sin(2 * np.pi * 0.05 * t),
            "IBI": ibi,
        }
    )


def test_cardiac_column_helpers_prefer_gazepoint_names():
    data = pd.DataFrame({"HRP": [1.0], "PPG": [1.0], "HR": [70.0], "IBI": [0.8], "RR_MS": [800.0]})
    assert ppg_signal_choices(data)[:2] == ["HRP", "PPG"]
    assert hr_signal_choices(data) == ["HR"]
    assert ibi_signal_choices(data)[:2] == ["IBI", "RR_MS"]


def test_ppg_hr_hrv_service_runs_core_signal_families():
    data = _cardiac_frame()
    result = run_ppg_hr_hrv_analysis(
        data,
        ppg_col="HRP",
        hr_col="HR",
        ibi_col="IBI",
        time_col="TIME",
        group_col="participant_id",
        sampling_rate_hz=60,
        high_precision=False,
    )
    assert set(result) >= {
        "waveform_quality",
        "detection",
        "cleaned_peaks",
        "ppg_measures",
        "ppg_hrv",
        "hr_quality",
        "hr_windows",
        "ibi_quality",
        "ibi_windows",
        "ibi_hrv",
        "parameters",
    }
    assert not result["detection"]["diagnostics"].empty
    assert len(result["cleaned_peaks"]) >= 10
    assert result["parameters"]["sampling_rate_hz"] == 60
    assert result["ibi_quality"]["overview"].iloc[0]["n_valid_ibi"] >= 10
    assert result["ibi_hrv"]["overview"].iloc[0]["status"] == "hrv_features_available"


def test_cardiac_analysis_supports_independent_hr_and_ibi_paths():
    data = _cardiac_frame()
    result = run_ppg_hr_hrv_analysis(
        data,
        ppg_col=None,
        hr_col="HR",
        ibi_col="IBI",
        time_col="TIME",
        group_col="participant_id",
        sampling_rate_hz=60,
    )
    assert "detection" not in result
    assert "hr_windows" in result
    assert "ibi_hrv" in result
    assert result["crosschecks"] == {}


def test_cardiac_analysis_validates_required_parameters():
    data = _cardiac_frame()
    with pytest.raises(ValueError, match="at least one"):
        run_ppg_hr_hrv_analysis(
            data,
            ppg_col=None,
            hr_col=None,
            ibi_col=None,
            time_col="TIME",
        )
    with pytest.raises(ValueError, match="Sampling rate"):
        run_ppg_hr_hrv_analysis(
            data,
            ppg_col="HRP",
            hr_col=None,
            ibi_col=None,
            time_col="TIME",
            sampling_rate_hz=0,
        )
    with pytest.raises(ValueError, match="IBI limits"):
        run_ppg_hr_hrv_analysis(
            data,
            ppg_col=None,
            hr_col=None,
            ibi_col="IBI",
            time_col="TIME",
            min_ibi_ms=2000,
            max_ibi_ms=300,
        )


def test_cardiac_tables_script_and_crosscheck_status():
    data = _cardiac_frame()
    result = run_ppg_hr_hrv_analysis(
        data,
        ppg_col=None,
        hr_col="HR",
        ibi_col="IBI",
        time_col="TIME",
        group_col="participant_id",
        sampling_rate_hz=60,
    )
    tables = ppg_hr_hrv_tables(result)
    assert set(tables) >= {"hr_quality", "hr_windows", "ibi_quality_overview", "ibi_hrv_features"}
    script = ppg_hr_hrv_reproducibility_script(result)
    assert "audit_gazepoint_ibi_quality" in script
    assert "summarise_gazepoint_hrv_features" in script
    assert "summarise_gazepoint_hr_windows" in script

    status = crosscheck_status_table(
        {
            "crosschecks": {
                "heartpy": {"heartpy_available": False, "heartpy": None},
                "biosppy": {"overview": pd.DataFrame([{"status": "ok"}])},
            }
        }
    )
    assert set(status["backend"]) == {"heartpy", "biosppy"}
    assert status.loc[status.backend.eq("heartpy"), "status"].iloc[0] == "not_installed_native_only"


def test_project_state_records_cardiac_analysis_parameters():
    data = _cardiac_frame(seconds=2)
    state = ProjectState().with_dataset(
        data,
        source_name="cardiac.csv",
        validation={"issues": pd.DataFrame()},
        operation="load_upload",
    )
    result = {"parameters": {"ppg_col": "HRP", "sampling_rate_hz": 60}}
    state = state.with_analysis("ppg_hr_hrv", result, parameters=result["parameters"])
    assert "ppg_hr_hrv" in state.analyses
    assert state.provenance[-1]["operation"] == "run_ppg_hr_hrv_analysis"
    assert state.provenance[-1]["parameters"]["ppg_col"] == "HRP"


def test_cardiac_module_imports():
    from studio.modules.ppg_hr_hrv import ppg_hr_hrv_server, ppg_hr_hrv_ui

    assert ppg_hr_hrv_ui is not None
    assert ppg_hr_hrv_server is not None
