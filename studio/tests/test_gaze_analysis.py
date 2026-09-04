from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest

from studio.gaze_services import (
    aoi_column_choices,
    gaze_analysis_tables,
    gaze_reproducibility_script,
    gaze_time_choices,
    gaze_validity_choices,
    gaze_x_choices,
    gaze_y_choices,
    load_aoi_definitions,
    recommended_velocity_threshold,
    run_gaze_analysis,
    validate_aoi_definitions,
)


def _gaze_frame() -> pd.DataFrame:
    time = np.arange(0.0, 1.0, 0.02)
    left = np.linspace(0.20, 0.22, 20)
    jump = np.array([0.80, 0.81])
    right = np.linspace(0.81, 0.84, len(time) - len(left) - len(jump))
    x = np.r_[left, jump, right]
    y = np.r_[np.linspace(0.30, 0.31, 20), [0.31, 0.31], np.linspace(0.31, 0.33, len(right))]
    valid = np.ones(len(time), dtype=int)
    return pd.DataFrame(
        {
            "participant_id": "P01",
            "trial": "T1",
            "time_s": time,
            "FPOGX": x,
            "FPOGY": y,
            "FPOGV": valid,
        }
    )


def _aois() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "aoi": ["left", "right"],
            "xmin": [0.0, 0.5],
            "xmax": [0.5, 1.0],
            "ymin": [0.0, 0.0],
            "ymax": [1.0, 1.0],
            "priority": [1, 2],
        }
    )


def test_gaze_column_helpers_detect_gazepoint_schema():
    data = _gaze_frame().assign(AOI="screen")
    assert gaze_x_choices(data)[0] == "FPOGX"
    assert gaze_y_choices(data)[0] == "FPOGY"
    assert gaze_time_choices(data)[0] == "time_s"
    assert gaze_validity_choices(data)[0] == "FPOGV"
    assert aoi_column_choices(data)[0] == "AOI"
    assert recommended_velocity_threshold("normalized") == 2.0
    assert recommended_velocity_threshold("pixels") == 1000.0


def test_validate_aoi_definitions_normalizes_label_and_rejects_bad_geometry():
    definitions = _aois().rename(columns={"aoi": "label"})
    out = validate_aoi_definitions(definitions)
    assert out.aoi.tolist() == ["left", "right"]
    assert "priority" in out
    bad = _aois()
    bad.loc[0, "xmin"] = 0.7
    with pytest.raises(ValueError, match="xmin < xmax"):
        validate_aoi_definitions(bad)


def test_load_aoi_definitions_from_shiny_upload_descriptor(tmp_path):
    path = tmp_path / "aois.csv"
    _aois().to_csv(path, index=False)
    table, name = load_aoi_definitions([{"name": "aois.csv", "size": path.stat().st_size, "datapath": str(path)}])
    assert name == "aois.csv"
    assert table.aoi.tolist() == ["left", "right"]
    with pytest.raises(ValueError, match="CSV or TXT"):
        load_aoi_definitions([{"name": "aois.json", "size": 1, "datapath": str(path)}])


def test_run_gaze_analysis_detects_events_assigns_aois_and_scanpath_metrics():
    result = run_gaze_analysis(
        _gaze_frame(),
        x_col="FPOGX",
        y_col="FPOGY",
        time_col="time_s",
        validity_col="FPOGV",
        group_col="participant_id",
        trial_col="trial",
        coordinate_system="normalized",
        screen_width_px=1920,
        screen_height_px=1080,
        expected_sampling_rate_hz=50,
        filter_to_screen=True,
        detect_events=True,
        velocity_threshold=2.0,
        min_fixation_duration_ms=100,
        min_saccade_duration_ms=10,
        max_gap_ms=100,
        aoi_definitions=_aois(),
        min_saccade_distance=0.02,
    )
    assert result["coordinate_mode"] == "normalized"
    assert result["analysis_x_col"].endswith("_studio_filtered")
    assert result["analysis_aoi_col"] == "Studio_AOI"
    assert "Studio_AOI" in result["processed_data"]
    assert not result["scanpath"].empty
    assert result["scanpath"]["aoi_transition_count"].iloc[0] >= 1
    assert not result["aoi_dwell"].empty
    events = result["gaze_events"]
    assert len(events["fixations"]) >= 1
    assert len(events["saccades"]) >= 1
    assert not result["fixations_by_aoi"].empty
    tables = gaze_analysis_tables(result)
    for key in ["validation_summary", "event_summary", "fixations", "saccades", "aoi_dwell", "scanpath"]:
        assert key in tables


def test_existing_aoi_column_supports_dwell_and_transition_summaries_without_event_detection():
    data = _gaze_frame()
    data["AOI"] = np.where(data["FPOGX"] < 0.5, "left", "right")
    result = run_gaze_analysis(
        data,
        x_col="FPOGX",
        y_col="FPOGY",
        time_col="time_s",
        validity_col="FPOGV",
        group_col="participant_id",
        trial_col="trial",
        coordinate_system="normalized",
        expected_sampling_rate_hz=50,
        filter_to_screen=False,
        detect_events=False,
        existing_aoi_col="AOI",
    )
    assert result["analysis_aoi_col"] == "AOI"
    assert not result["aoi_dwell"].empty
    assert result["scanpath"]["aoi_transition_count"].iloc[0] == 1


def test_reproducibility_script_uses_public_gaze_apis():
    result = run_gaze_analysis(
        _gaze_frame(),
        x_col="FPOGX",
        y_col="FPOGY",
        time_col="time_s",
        coordinate_system="normalized",
        expected_sampling_rate_hz=50,
        filter_to_screen=False,
        detect_events=False,
        aoi_definitions=_aois(),
    )
    script = gaze_reproducibility_script(result)
    assert "gp.validate_gazepoint_gaze" in script
    assert "gp.assign_gazepoint_aoi" in script
    assert "gp.summarize_gazepoint_scanpath_metrics" in script


def test_gaze_service_validation_errors_are_explicit():
    data = _gaze_frame()
    with pytest.raises(ValueError, match="Selected gaze x"):
        run_gaze_analysis(data, x_col="missing", y_col="FPOGY", time_col="time_s")
    with pytest.raises(ValueError, match="sampling rate"):
        run_gaze_analysis(data, x_col="FPOGX", y_col="FPOGY", time_col="time_s", expected_sampling_rate_hz=0)


def test_gaze_module_and_app_import():
    module = importlib.import_module("studio.modules.gaze")
    assert callable(module.gaze_ui)
    assert callable(module.gaze_server)
    app_module = importlib.import_module("studio.app")
    assert app_module.app is not None
