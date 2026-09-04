import numpy as np
import pandas as pd
import pytest

from studio.pupil_services import (
    onset_column_choices,
    pupil_analysis_tables,
    pupil_reproducibility_script,
    pupil_signal_choices,
    pupil_validity_choices,
    run_pupil_analysis,
    trial_column_choices,
)
from studio.state import ProjectState


def _pupil_frame(seconds: int = 12, fs: int = 60) -> pd.DataFrame:
    n = seconds * fs
    t = np.arange(n, dtype=float) / fs
    pupil = 3.2 + 0.12 * np.sin(2 * np.pi * 0.25 * t) + 0.03 * np.sin(2 * np.pi * 1.1 * t)
    validity = np.ones(n, dtype=int)

    pupil[100:106] = 2.9
    validity[100:106] = 0
    pupil[300:304] = np.nan

    trial = np.where(t < 6, 1, 2)
    event_onset = np.full(n, np.nan)
    event_onset[np.argmin(np.abs(t - 3.0))] = 3.0
    event_onset[np.argmin(np.abs(t - 8.0))] = 8.0

    return pd.DataFrame(
        {
            "participant_id": "P01",
            "trial_id": trial,
            "TIME": t,
            "LPD": pupil,
            "LPV": validity,
            "event_onset": event_onset,
        }
    )


def test_pupil_column_helpers_recognize_gazepoint_contract():
    data = _pupil_frame(seconds=2)
    data["RPD"] = data["LPD"] + 0.02
    data["RPV"] = 1
    assert pupil_signal_choices(data)[:2] == ["LPD", "RPD"]
    assert pupil_validity_choices(data, "LPD")[0] == "LPV"
    assert trial_column_choices(data)[0] == "trial_id"
    assert onset_column_choices(data)[0] == "event_onset"


def test_guided_pupil_analysis_detects_validity_and_missing_blinks():
    data = _pupil_frame()
    result = run_pupil_analysis(
        data,
        pupil_col="LPD",
        time_col="TIME",
        validity_col="LPV",
        group_col="participant_id",
        trial_col="trial_id",
        min_blink_samples=2,
    )
    assert len(result["blink_intervals"]) >= 2
    assert int(result["blink_flags"].sum()) >= 10
    assert result["analysis_pupil_col"] == "LPD"
    assert "_studio_pupil_blink" not in result["processed_data"].columns
    assert result["parameters"]["interpolate"] is False


def test_pupil_analysis_interpolates_flagged_samples_and_smooths():
    data = _pupil_frame()
    result = run_pupil_analysis(
        data,
        pupil_col="LPD",
        time_col="TIME",
        validity_col="LPV",
        group_col="participant_id",
        trial_col="trial_id",
        min_blink_samples=2,
        interpolate=True,
        interpolation_max_gap_s=0.25,
        interpolation_method="linear",
        smooth=True,
        smooth_window=5,
    )
    processed = result["processed_data"]
    assert "LPD_studio_interp" in processed.columns
    assert "LPD_was_interpolated" in processed.columns
    assert processed.loc[100:105, "LPD_was_interpolated"].all()
    assert processed.loc[100:105, "LPD_studio_interp"].notna().all()
    assert "LPD_studio_interp_studio_smooth" in processed.columns
    assert result["analysis_pupil_col"] == "LPD_studio_interp_studio_smooth"


def test_pupil_event_summary_uses_explicit_event_onsets():
    data = _pupil_frame()
    result = run_pupil_analysis(
        data,
        pupil_col="LPD",
        time_col="TIME",
        validity_col="LPV",
        group_col="participant_id",
        trial_col="trial_id",
        summarize_events=True,
        event_onset_col="event_onset",
        pre_s=1.0,
        post_s=2.0,
        response_window=(0.0, 1.5),
    )
    assert len(result["events"]) == 2
    assert len(result["event_summary"]) == 2
    assert {"event_id", "event_time"}.issubset(result["event_summary"].columns)


def test_pupil_analysis_validates_processing_parameters():
    data = _pupil_frame()
    with pytest.raises(ValueError, match="odd"):
        run_pupil_analysis(data, pupil_col="LPD", time_col="TIME", smooth=True, smooth_window=4)
    with pytest.raises(ValueError, match="Baseline window"):
        run_pupil_analysis(data, pupil_col="LPD", time_col="TIME", baseline_window=(0.0, -0.1))
    with pytest.raises(ValueError, match="stimulus-onset"):
        run_pupil_analysis(
            data,
            pupil_col="LPD",
            time_col="TIME",
            baseline_correct=True,
            stimulus_onset_col=None,
        )
    with pytest.raises(ValueError, match="event-onset or TTL"):
        run_pupil_analysis(data, pupil_col="LPD", time_col="TIME", summarize_events=True)


def test_pupil_tables_and_reproducibility_script():
    data = _pupil_frame()
    result = run_pupil_analysis(
        data,
        pupil_col="LPD",
        time_col="TIME",
        validity_col="LPV",
        group_col="participant_id",
        interpolate=True,
        smooth=True,
        summarize_events=True,
        event_onset_col="event_onset",
        trial_col="trial_id",
    )
    tables = pupil_analysis_tables(result)
    assert set(tables) >= {"blink_intervals", "blink_summary", "smoothing_summary", "events", "event_summary", "repair_flags"}
    script = pupil_reproducibility_script(result)
    assert "detect_gazepoint_pupil_blinks" in script
    assert "interpolate_gazepoint_pupil_blinks" in script
    assert "smooth_gazepoint_pupil" in script
    assert "summarize_gazepoint_pupil_events" in script


def test_project_state_records_pupil_analysis():
    data = _pupil_frame(seconds=2)
    state = ProjectState().with_dataset(
        data,
        source_name="pupil.csv",
        validation={"issues": pd.DataFrame()},
        operation="load_upload",
    )
    result = {"parameters": {"pupil_col": "LPD", "time_col": "TIME"}}
    state = state.with_analysis("pupil", result, parameters=result["parameters"])
    assert "pupil" in state.analyses
    assert state.provenance[-1]["operation"] == "run_pupil_analysis"


def test_pupil_module_imports():
    from studio.modules.pupil import pupil_server, pupil_ui

    assert pupil_ui is not None
    assert pupil_server is not None
