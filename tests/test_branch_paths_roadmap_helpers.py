from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_roadmap_recovery_and_pupil_empty_response_paths():
    no_peak = gp.summarize_gazepoint_scr_recovery(
        pd.DataFrame({"time_s": [0.0, 0.1], "GSR": [1.0, 1.1]}),
        [0.0],
        pre=0,
        post=0.1,
    )
    assert np.isnan(no_peak.loc[0, "peak_amplitude"])

    short_after = gp.summarize_gazepoint_scr_recovery(
        pd.DataFrame({"time_s": [-0.2, 0.0, 0.5, 1.0], "GSR": [1.0, 1.0, 2.0, 1.5]}),
        [0.0],
        pre=0.2,
        post=1.0,
        peak_window=(0.5, 0.6),
    )
    assert short_after.loc[0, "peak_latency_s"] == pytest.approx(0.5)
    assert np.isnan(short_after.loc[0, "recovery_slope"])

    pupil = gp.summarize_gazepoint_pupil_events(
        pd.DataFrame({"time_s": [-0.2, 0.0, 0.2], "pupil": [3.0, 3.0, 3.1]}),
        [0.0],
        pre=0.2,
        post=0.2,
        response_window=(1.0, 2.0),
    )
    assert np.isnan(pupil.loc[0, "pupil_peak_dilation"])


def test_roadmap_tracking_public_modality_combinations():
    pupil_only = gp.summarize_gazepoint_tracking(
        pd.DataFrame({"pupil_left": [3.0, 0.0, 3.2]}),
        pupil_cols="pupil_left",
    )
    assert pupil_only.loc[0, "pupil_valid_ratio"] == pytest.approx(2 / 3)
    assert np.isnan(pupil_only.loc[0, "gaze_valid_ratio"])
    assert pupil_only.loc[0, "tracking_ratio"] == pytest.approx(2 / 3)

    combined = gp.summarize_gazepoint_tracking(
        pd.DataFrame({
            "pupil_left": [3.0, 3.1],
            "gaze_x": [0.2, 2.0],
            "gaze_y": [0.2, 0.2],
        }),
        pupil_cols="pupil_left",
        x_col="gaze_x",
        y_col="gaze_y",
    )
    assert combined.loc[0, "tracking_ratio"] == pytest.approx(0.5)


def test_roadmap_luminance_and_local_peak_public_paths():
    with pytest.raises(ValueError, match="method"):
        gp.audit_gazepoint_pupil_luminance(
            pd.DataFrame({"pupil": [3.0], "luminance": [1.0]}), method="kendall"
        )

    sparse = gp.audit_gazepoint_pupil_luminance(
        pd.DataFrame({"pupil": [3.0, np.nan], "luminance": [1.0, 2.0]})
    )
    assert sparse.loc[0, "n_complete"] == 1
    assert np.isnan(sparse.loc[0, "correlation"])

    # Automatic peak detection reaches the close/lower-candidate suppression path.
    morph = gp.extract_gazepoint_ppg_morphology(
        pd.DataFrame({
            "time_s": np.arange(5, dtype=float) * 0.1,
            "PPG": [0.0, 3.0, 0.0, 2.0, 0.0],
        }),
        min_peak_distance_s=0.4,
    )
    assert isinstance(morph, pd.DataFrame)


def test_roadmap_ppg_quality_empty_windows():
    q = gp.flag_gazepoint_ppg_quality(
        pd.DataFrame({"time_s": [0.0, 1.0], "PPG": [0.0, 1.0]}),
        window_s=0.1,
        step_s=0.2,
    )
    assert q.start_time.tolist() == pytest.approx([0.0, 1.0])


def test_roadmap_event_log_public_import_paths(tmp_path):
    frame = gp.import_gazepoint_event_log(pd.DataFrame({"time": [1.0, 2.0]}))
    assert frame.event_id.tolist() == [1, 2]
    assert frame.event_label.tolist() == ["event_1", "event_2"]

    with pytest.raises(ValueError, match="existing event-log path"):
        gp.import_gazepoint_event_log(tmp_path / "missing.csv")

    explicit = tmp_path / "events.csv"
    explicit.write_text("time,label\n1,A\n2,B\n", encoding="utf-8")
    imported = gp.import_gazepoint_event_log(explicit, sep=",")
    assert imported.event_label.tolist() == ["A", "B"]


def test_roadmap_event_matching_public_residual_paths():
    data = pd.DataFrame({"time_s": [0.0, 1.0], "signal": [1.0, 2.0]})

    with pytest.raises(ValueError, match="return"):
        gp.match_gazepoint_events_to_biometrics(data, [0.0], return_="bad")

    empty = gp.match_gazepoint_events_to_biometrics(
        data, [100.0], pre=0, post=0.1, return_="windows"
    )
    assert empty.empty


def test_roadmap_assert_columns_invalid_mode():
    with pytest.raises(ValueError, match="Invalid `mode`"):
        gp.assert_gazepoint_columns(pd.DataFrame({"x": [1]}), ["x"], mode="bad")


def test_roadmap_sync_drift_public_input_variants():
    with pytest.raises(ValueError, match="Supply `target`"):
        gp.diagnose_gazepoint_sync_drift([0.0, 1.0], target=None)

    mixed = gp.diagnose_gazepoint_sync_drift(
        pd.DataFrame({"time_s": [0.0, 1.0, 2.0]}),
        [0.1, 1.1, 2.1],
    )
    assert mixed["summary"].loc[0, "n_pairs"] == 3

    dataframe_target = gp.diagnose_gazepoint_sync_drift(
        [0.0, 1.0, 2.0],
        pd.DataFrame({"time_s": [0.2, 1.2, 2.2]}),
    )
    assert dataframe_target["summary"].loc[0, "median_lag_s"] == pytest.approx(0.2)

    with pytest.raises(ValueError, match="finite matched"):
        gp.diagnose_gazepoint_sync_drift([0.0, np.nan], [0.1, np.nan])


def test_roadmap_scanpath_optional_aoi_paths():
    no_aoi = gp.summarize_gazepoint_scanpath_metrics(
        pd.DataFrame({"x": [0.0, 0.1], "y": [0.0, 0.1]})
    )
    assert np.isnan(no_aoi.loc[0, "aoi_transition_count"])

    empty_aoi = gp.summarize_gazepoint_scanpath_metrics(
        pd.DataFrame({"x": [0.0, 0.1], "y": [0.0, 0.1], "AOI": [np.nan, ""]})
    )
    assert np.isnan(empty_aoi.loc[0, "transition_entropy"])

    one_aoi = gp.summarize_gazepoint_scanpath_metrics(
        pd.DataFrame({"x": [0.0, 0.1], "y": [0.0, 0.1], "AOI": ["A", "A"]})
    )
    assert one_aoi.loc[0, "aoi_transition_count"] == 0
    assert np.isnan(one_aoi.loc[0, "transition_entropy"])


def test_roadmap_manifest_validation_no_path_and_none_outputs(tmp_path):
    with pytest.raises(TypeError, match="settings"):
        gp.create_gazepoint_analysis_manifest(settings=[])

    no_path = gp.create_gazepoint_analysis_manifest(include_session=False)
    assert "manifest_path" not in no_path
    assert "session_info" not in no_path

    p = tmp_path / "manifest.txt"
    written = gp.create_gazepoint_analysis_manifest(path=p, outputs=None)
    assert p.exists()
    assert "[outputs]\nnone" in p.read_text(encoding="utf-8")
    assert written["manifest_path"] == str(p.resolve())


def test_roadmap_template_similarity_index_and_short_window_paths():
    t = np.arange(100, dtype=float) / 50.0
    ppg = np.sin(2 * np.pi * 2 * t)

    indexed = gp.compute_gazepoint_ppg_template_similarity(
        pd.DataFrame({"time_s": t, "PPG": ppg}),
        peaks=[26, 51, 76],
    )
    assert indexed["summary"].loc[0, "n_beats"] >= 1

    short = gp.compute_gazepoint_ppg_template_similarity(
        pd.DataFrame({"time_s": t, "PPG": ppg}),
        peaks=[1],
        window_s=(-0.001, 0.001),
    )
    assert short["summary"].loc[0, "n_beats"] == 0
