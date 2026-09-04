from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest

from studio.multimodal_services import (
    event_alignment_available,
    multimodal_reproducibility_script,
    multimodal_signal_choices,
    multimodal_tables,
    run_multimodal_analysis,
)


def _data() -> pd.DataFrame:
    t = np.linspace(0.0, 10.0, 101)
    return pd.DataFrame(
        {
            "time_s": t,
            "participant": "P01",
            "trial": np.where(t < 5, "T1", "T2"),
            "GSR": 2.0 + 0.1 * np.sin(t),
            "HR": 70.0 + 3.0 * np.cos(t / 2),
            "DIAL": 0.5 + 0.1 * np.sin(t / 3),
            "LPD": 3.0 + 0.05 * np.sin(t * 1.5),
            "gaze_x": np.clip(0.5 + 0.25 * np.sin(t), 0, 1),
            "gaze_y": np.clip(0.5 + 0.20 * np.cos(t), 0, 1),
            "AOI": np.where(np.sin(t) >= 0, "right", "left"),
        }
    )


def _analyses() -> dict:
    events = pd.DataFrame(
        {
            "event_id": ["E1", "E2"],
            "event_time": [2.0, 7.0],
            "event_label": ["stimulus", "stimulus"],
            "participant": ["P01", "P01"],
            "trial": ["T1", "T2"],
        }
    )
    return {"event_alignment": {"events": events}}


def test_multimodal_requires_event_alignment():
    assert not event_alignment_available({})
    with pytest.raises(ValueError, match="Events & Alignment"):
        run_multimodal_analysis(
            _data(),
            {},
            time_col="time_s",
            eda_col="GSR",
        )


def test_multimodal_eventlocked_aoi_and_model_tables():
    result = run_multimodal_analysis(
        _data(),
        _analyses(),
        time_col="time_s",
        group_col="participant",
        trial_col="trial",
        eda_col="GSR",
        cardiac_col="HR",
        pupil_col="LPD",
        gaze_x_col="gaze_x",
        gaze_y_col="gaze_y",
        aoi_col="AOI",
        pre_s=1.0,
        post_s=2.0,
        baseline_window_s=(-1.0, 0.0),
        summary_window_s=(0.0, 2.0),
    )
    assert event_alignment_available(_analyses())
    assert set(result["parameters"]["modalities"]) == {"eda", "cardiac", "pupil", "gaze"}
    assert result["parameters"]["classic_grouped_windows_available"]
    assert not result["eventlocked"]["samples"].empty
    summary = result["eventlocked"]["summary"]
    assert set(summary["modality"]) == {"eda", "cardiac", "pupil", "gaze"}
    assert set(summary["event_id"]) == {"E1", "E2"}
    assert not result["multimodal_windows"].empty
    assert not result["model_data"].empty
    assert "aoi_biometrics" in result
    tables = multimodal_tables(result)
    assert not tables["response_matrix"].empty
    assert not tables["aoi_summary"].empty


def test_multimodal_partial_channels_keep_eventlocked_analysis():
    data = _data().drop(columns="DIAL")
    result = run_multimodal_analysis(
        data,
        _analyses(),
        time_col="time_s",
        group_col="participant",
        trial_col="trial",
        eda_col="GSR",
        cardiac_col="HR",
    )
    assert not result["eventlocked"]["summary"].empty
    assert "multimodal_windows" not in result
    status = result["grouped_window_status"].iloc[0]
    assert status["status"] == "not_applicable_partial_channels"
    assert "DIAL" in status["missing_native_channels"]


def test_multimodal_blocks_cross_participant_event_leakage():
    one = _data()
    two = one.copy()
    two["participant"] = "P02"
    two["GSR"] += 1
    data = pd.concat([one, two], ignore_index=True)
    events = _analyses()["event_alignment"]["events"].drop(columns="participant")
    analyses = {"event_alignment": {"events": events}}
    with pytest.raises(ValueError, match="Events do not contain `participant`"):
        run_multimodal_analysis(
            data,
            analyses,
            time_col="time_s",
            group_col="participant",
            eda_col="GSR",
        )


def test_multimodal_prefers_processed_studio_outputs():
    data = _data()
    analyses = _analyses()

    eda = data.copy()
    eda["studio_eda_phasic"] = data["GSR"] - data["GSR"].rolling(5, center=True, min_periods=1).median()
    pupil = data.copy()
    pupil["LPD_studio_interp"] = pupil["LPD"]
    gaze = data.copy()
    gaze["gaze_x_studio_filtered"] = gaze["gaze_x"]
    gaze["gaze_y_studio_filtered"] = gaze["gaze_y"]
    gaze["Studio_AOI"] = gaze["AOI"]

    analyses.update(
        {
            "eda_scr": {"decomposition": eda},
            "pupil": {"processed_data": pupil, "analysis_pupil_col": "LPD_studio_interp"},
            "gaze": {
                "processed_data": gaze,
                "analysis_x_col": "gaze_x_studio_filtered",
                "analysis_y_col": "gaze_y_studio_filtered",
                "analysis_aoi_col": "Studio_AOI",
            },
        }
    )
    choices = multimodal_signal_choices(data, analyses, prefer_processed=True)
    assert choices["eda"][0] == "studio_eda_phasic"
    assert choices["pupil"][0] == "LPD_studio_interp"
    assert choices["gaze_x"][0] == "gaze_x_studio_filtered"
    assert choices["aoi"][0] == "Studio_AOI"

    result = run_multimodal_analysis(
        data,
        analyses,
        time_col="time_s",
        group_col="participant",
        trial_col="trial",
        eda_col="studio_eda_phasic",
        cardiac_col="HR",
        pupil_col="LPD_studio_interp",
        gaze_x_col="gaze_x_studio_filtered",
        gaze_y_col="gaze_y_studio_filtered",
        aoi_col="Studio_AOI",
        prefer_processed=True,
    )
    sources = result["stream_sources"].set_index("modality")["source"].to_dict()
    assert sources["eda"] == "EDA / SCR processed decomposition"
    assert sources["pupil"] == "Pupil processed dataset"
    assert sources["gaze"] == "Gaze processed dataset"


def test_multimodal_reproducibility_script_and_imports():
    result = run_multimodal_analysis(
        _data(),
        _analyses(),
        time_col="time_s",
        group_col="participant",
        trial_col="trial",
        eda_col="GSR",
        cardiac_col="HR",
        pupil_col="LPD",
    )
    script = multimodal_reproducibility_script(result)
    assert "summarize_gazepoint_eventlocked_multimodal" in script
    assert "summarise_gazepoint_multimodal_windows" in script
    assert "prepare_gazepoint_multimodal_model_data" in script
    importlib.import_module("studio.modules.multimodal")
    importlib.import_module("studio.app")
