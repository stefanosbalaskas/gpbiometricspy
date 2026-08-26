from pathlib import Path
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_gaze_validation_normalized_fixture():
    data = pd.DataFrame({
        "participant": ["P01"] * 5,
        "trial": ["T01"] * 5,
        "time_s": np.arange(5) * 0.01,
        "gaze_x": [0.2, 0.4, 1.2, np.nan, 0.5],
        "gaze_y": [0.3, 0.5, 0.6, np.nan, 0.5],
        "valid": [True, True, True, True, False],
    })
    out = gp.validate_gazepoint_gaze(data, group_cols=["participant", "trial"], expected_sampling_rate_hz=100)
    s = out["summary"].iloc[0]
    assert s.n_samples == 5
    assert s.out_of_range_rate == pytest.approx(1 / 5)
    assert s.missing_gaze_rate == pytest.approx(2 / 5)
    assert bool(out["data"].loc[2, ".gaze_out_of_range"])
    assert bool(out["data"].loc[3, ".gaze_invalid"])
    assert bool(out["data"].loc[4, ".gaze_invalid"])
    assert out["settings"]["coordinate_system"] == "normalized"


def test_gaze_validation_time_and_pixel_fixtures():
    data = pd.DataFrame({"time_ms": [0, 10, 10, 5, 30], "gaze_x": [0.5] * 5, "gaze_y": [0.5] * 5})
    out = gp.validate_gazepoint_gaze(data)
    s = out["summary"].iloc[0]
    assert s.duplicate_time_count == 1
    assert s.nonmonotonic_time_count == 1
    assert out["checks"].set_index("check").loc["monotonic_time", "status"] == "fail"

    px = pd.DataFrame({"time_ms": [0, 10, 20], "gaze_x": [100, 2000, 300], "gaze_y": [100, 500, 1200]})
    no_screen = gp.validate_gazepoint_gaze(px)
    assert no_screen["settings"]["coordinate_system"] == "pixels"
    assert no_screen["settings"]["range_assessed"] is False
    with_screen = gp.validate_gazepoint_gaze(px, coordinate_system="pixels", screen_width_px=1920, screen_height_px=1080)
    assert with_screen["summary"].iloc[0].out_of_range_rate == pytest.approx(2 / 3)


def test_gaze_validation_edge_paths():
    with pytest.raises(TypeError, match="data frame"):
        gp.validate_gazepoint_gaze([1, 2])
    with pytest.raises(ValueError, match="no rows"):
        gp.validate_gazepoint_gaze(pd.DataFrame())
    with pytest.raises(ValueError, match="sampling_tolerance"):
        gp.validate_gazepoint_gaze(pd.DataFrame({"time_s": [0, 1], "gaze_x": [0, 0], "gaze_y": [0, 0]}), sampling_tolerance=-1)
    with pytest.raises(ValueError, match="sampling_rate_hz"):
        gp.validate_gazepoint_gaze(pd.DataFrame({"CNT": [0, 1], "gaze_x": [0, 0], "gaze_y": [0, 0]}))
    out = gp.validate_gazepoint_gaze(pd.DataFrame({"time_s": [0, 0.01, 0.10], "gaze_x": [0, 0, 0], "gaze_y": [0, 0, 0]}), expected_sampling_rate_hz=100)
    assert out["summary"].iloc[0].large_gap_count == 1


def test_fixations_by_aoi_original_fixtures():
    fix = pd.DataFrame({
        "participant": ["P01"] * 4, "trial": ["T01"] * 4,
        "aoi": ["claim", "claim", "evidence", "evidence"],
        "start_ms": [100, 300, 500, 800], "end_ms": [200, 450, 650, 900],
        "duration_ms": [100, 150, 150, 100], "event_onset_ms": [50] * 4,
    })
    out = gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="start_ms", end_col="end_ms", duration_col="duration_ms", event_onset_col="event_onset_ms")
    assert len(out) == 2
    assert out.fixation_count.tolist() == [2, 2]
    assert out.total_fixation_duration_ms.tolist() == [250.0, 250.0]
    assert out.dwell_proportion.tolist() == [0.5, 0.5]
    assert out.first_fixation_latency_ms.tolist() == [50.0, 450.0]
    assert out.attrs["audit"]["retained_rows"] == 4

    seconds = pd.DataFrame({"aoi": ["A", "A"], "start_s": [0.1, 0.4], "end_s": [0.2, 0.6]})
    sec = gp.summarise_gazepoint_fixations_by_aoi(seconds, start_col="start_s", end_col="end_s", time_unit="seconds")
    assert sec.total_fixation_duration_ms.iloc[0] == pytest.approx(300)
    assert sec.mean_fixation_duration_ms.iloc[0] == pytest.approx(150)


def test_fixation_unassigned_alias_and_errors():
    fix = pd.DataFrame({"aoi": ["A", None, ""], "start_ms": [0, 100, 200], "duration_ms": [50, 50, 50]})
    excluded = gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="start_ms", duration_col="duration_ms")
    assert excluded.aoi.tolist() == ["A"]
    included = gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="start_ms", duration_col="duration_ms", include_unassigned=True)
    assert sorted(included.aoi.tolist()) == ["A", "UNASSIGNED"]
    american = gp.summarize_gazepoint_fixations_by_aoi(fix, start_col="start_ms", duration_col="duration_ms", include_unassigned=True)
    pd.testing.assert_frame_equal(included, american)
    with pytest.raises(ValueError, match="end_col.*duration_col"):
        gp.summarise_gazepoint_fixations_by_aoi(pd.DataFrame({"aoi": ["A"], "start_ms": [0]}), start_col="start_ms")


def test_bids_wrappers_dry_run_and_execute(tmp_path):
    eye = pd.DataFrame({"time_s": [0, 0.01, 0.02], "gaze_x": [0.1] * 3, "gaze_y": [0.2] * 3})
    out = gp.prepare_gazepoint_bids_eye(eye, output_dir="x", execute=False)
    assert out["modality"] == "eye" and out["executed"] is False
    phys = gp.prepare_gazepoint_bids_physio(pd.DataFrame({"time_s": [0, 1, 2], "GSR": [1, 2, 3]}), output_dir="x", execute=False)
    assert phys["modality"] == "physio"

    root = tmp_path / "bids"
    executed = gp.prepare_gazepoint_bids_eye(
        eye, bids_root=root, subject="01", task="t", dataset_name="Test", execute=True
    )
    assert executed["class"][0] == "gazepoint_bids_export"
    assert executed["gpbiometrics_bids_modality"] == "eye"
    assert executed["audit"]["ready_to_write"] is True
    assert all(Path(path).exists() for path in executed["files"]["path"])


def _prepared_mne(finite=True):
    vals = np.array([[0.1, 0.2, 0.3], [3.0, 3.1, 3.2]], float)
    if not finite:
        vals[1, 1] = np.nan
    return {
        "data": vals,
        "channel_info": pd.DataFrame({"channel_name": ["gaze_x", "pupil"], "channel_type": ["eyegaze", "pupil"]}),
        "info_spec": {"sfreq": 100.0}, "rawarray_spec": {"first_samp": 0},
    }


def test_mne_fif_writer_dry_run_and_validation(tmp_path):
    out = gp.write_gazepoint_mne_fif(_prepared_mne(), tmp_path / "gazepoint_raw.fif", execute=False)
    assert out["executed"] is False
    assert out["n_channels"] == 2 and out["n_samples"] == 3
    assert "mne.io.RawArray" in out["python_script"] and "raw.save" in out["python_script"]
    with pytest.raises(ValueError, match="finite"):
        gp.write_gazepoint_mne_fif(_prepared_mne(False), tmp_path / "gazepoint_raw.fif", execute=False)
    with pytest.raises(ValueError, match="MNE-compatible"):
        gp.write_gazepoint_mne_fif(_prepared_mne(), tmp_path / "bad.fif", execute=False)
    with pytest.raises(ValueError, match="three columns"):
        gp.write_gazepoint_mne_fif(_prepared_mne(), tmp_path / "gazepoint_raw.fif", events=np.ones((2, 2)), execute=False)


def test_lsl_clock_offsets_dry_run_and_validation():
    out = gp.estimate_gazepoint_lsl_clock_offsets(stream_name="Gazepoint", n_estimates=3, execute=False)
    assert out["executed"] is False and out["n_estimates"] == 3
    assert "time_correction" in out["python_script"]
    with pytest.raises(ValueError, match="n_estimates"):
        gp.estimate_gazepoint_lsl_clock_offsets(n_estimates=0, execute=False)
    with pytest.raises(ValueError, match="pause_s"):
        gp.estimate_gazepoint_lsl_clock_offsets(pause_s=-1, execute=False)

def test_more_final_gap_edge_paths(monkeypatch, tmp_path):
    # Character validity values and sample-index time.
    dat = pd.DataFrame({"CNT": [0, 1, 2], "gaze_x": [0.1, 0.2, 0.3], "gaze_y": [0.2, 0.3, 0.4], "validity": ["valid", "yes", "off"]})
    out = gp.validate_gazepoint_gaze(dat, sampling_rate_hz=100, validity_cols="validity")
    assert out["settings"]["time_unit"] == "samples"
    assert out["summary"].iloc[0].missing_gaze_rate == pytest.approx(1 / 3)

    # Explicit degree coordinates are deliberately not range-assessed.
    deg = gp.validate_gazepoint_gaze(pd.DataFrame({"time_s": [0, .01], "x": [2.0, 3.0], "y": [1.0, 1.5]}), x_col="x", y_col="y", coordinate_system="degrees")
    assert deg["checks"].set_index("check").loc["coordinate_range", "status"] == "not_assessed"

    # Sample-based fixation timing/duration.
    fix = pd.DataFrame({"aoi": ["A", "A"], "sample_index": [10, 20], "duration_count": [5, 10]})
    fx = gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="sample_index", duration_col="duration_count", time_unit="samples", duration_unit="samples", sampling_rate_hz=100)
    assert fx.total_fixation_duration_ms.iloc[0] == pytest.approx(150)

    # Prepared MNE events and event dictionary enter the dry-run manifest.
    events = {"events": np.array([[0, 0, 1], [10, 0, 2]]), "event_dictionary": pd.DataFrame({"event_code": [1, 2], "event_label": ["A", "B"]})}
    mne = gp.write_gazepoint_mne_fif(_prepared_mne(), tmp_path / "x_raw.fif", events=events, execute=False)
    assert mne["event_count"] == 2

    with pytest.raises(TypeError, match="execute"):
        gp.prepare_gazepoint_bids_eye(pd.DataFrame({"x": [1]}), execute="no")

def test_final_gap_validation_extras(tmp_path):
    with pytest.raises(ValueError, match="fmt"):
        gp.write_gazepoint_mne_fif(_prepared_mne(), tmp_path / "x_raw.fif", fmt="bad", execute=False)
    with pytest.raises(TypeError, match="data frame"):
        gp.summarise_gazepoint_fixations_by_aoi([1, 2])
