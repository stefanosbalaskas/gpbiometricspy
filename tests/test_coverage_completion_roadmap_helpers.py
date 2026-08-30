from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.roadmap_helpers as m


def test_private_group_pupil_validity_and_event_branches(tmp_path):
    df = pd.DataFrame({"g": ["a"], "LPD": [3.0], "RPD": [3.1], "custom": [2.0]})
    with pytest.raises(ValueError, match="Missing grouping columns"):
        m._groups(df, "missing")
    with pytest.raises(ValueError, match="Missing pupil columns"):
        m._pupil_cols(df, ["LPD", "missing"])
    with pytest.raises(ValueError, match="identify pupil"):
        m._pupil_cols(pd.DataFrame({"x": [1.0]}))

    assert m._validity_for_pupil(df, "LPD") is None
    assert m._validity_for_pupil(df, "RPD") is None
    assert m._validity_for_pupil(df, "custom") is None

    p = tmp_path / "events.csv"
    p.write_text("event_time,event_id,event_label\n1,E1,A\n", encoding="utf-8")
    from_file = m._standardize_events(p)
    assert from_file.event_id.tolist() == ["E1"]

    guessed = m._standardize_events(pd.DataFrame({"time": [1.0], "trial": [9], "condition": ["A"]}))
    assert guessed.event_id.tolist() == [9]
    assert guessed.event_label.tolist() == ["A"]

    with pytest.raises(ValueError, match="event_time_col"):
        m._standardize_events(pd.DataFrame({"x": [1]}), event_time_col="missing")


def test_local_peaks_distance_and_replacement():
    assert m._local_peaks([1, 2]).size == 0
    # The later/higher peak replaces an earlier candidate that is too close.
    x = np.array([0.0, 2.0, 1.0, 3.0, 0.0, 0.0])
    peaks = m._local_peaks(x, min_distance=4)
    assert peaks.tolist() == [3]


def test_habituation_validation_guessing_synthetic_columns_and_nonfinite_trials():
    with pytest.raises(ValueError, match="method"):
        m.compute_gazepoint_scr_habituation([1, 2, 3], method="bad")

    # Guess amplitude; synthesize trial and subject columns.
    out = m.compute_gazepoint_scr_habituation(
        pd.DataFrame({"amplitude": [3.0, 2.0, 1.0]}), min_trials=2
    )
    assert out.subject.tolist() == ["all"]
    assert out.n_trials.tolist() == [3]

    # Existing all-NaN trial column exercises sequential fallback.
    out2 = m.compute_gazepoint_scr_habituation(
        pd.DataFrame({"scr_amplitude": [1.0, 2.0, 3.0], "trial": [np.nan] * 3}),
        amplitude_col="scr_amplitude",
        trial_col="trial",
        min_trials=2,
    )
    assert out2.habituation_direction.iloc[0] == "increasing"


def test_recovery_validation_and_tracking_without_pupil_columns():
    dat = pd.DataFrame({"time_s": [0.0, 1.0], "GSR": [0.0, 1.0]})
    with pytest.raises(ValueError, match="pre"):
        m.summarize_gazepoint_scr_recovery(dat, [0.5], pre=-1)

    # No recognizable pupil columns -> tracking falls back to gaze-only validity.
    track = m.summarize_gazepoint_tracking(
        pd.DataFrame({"x": [0.2, 2.0], "y": [0.2, 0.2]}),
        x_col="x",
        y_col="y",
    )
    assert np.isnan(track.pupil_valid_ratio.iloc[0])
    assert track.gaze_valid_ratio.iloc[0] == 0.5


def test_ppg_explicit_peak_forms_and_empty_quality_window():
    t = np.linspace(0, 1, 21)
    ppg = np.sin(2 * np.pi * t)
    dat = pd.DataFrame({"time_s": t, "PPG": ppg})

    # 1-based integer peak indices.
    a = m.extract_gazepoint_ppg_morphology(dat, peaks=[6])
    assert a.peak_index.iloc[0] == 6

    # Non-integral values are interpreted as timestamps.
    b = m.extract_gazepoint_ppg_morphology(dat, peaks=[0.25])
    assert len(b) == 1

    # All missing values take the finite-empty quality path.
    q = m.flag_gazepoint_ppg_quality(
        pd.DataFrame({"time_s": [0.0, 0.1, 0.2], "PPG": [np.nan] * 3}),
        window_s=1,
    )
    assert len(q) == 1 and not bool(q.quality_ok.iloc[0])


def test_schema_file_paths_manifest_empty_and_output_list(tmp_path):
    with pytest.raises(ValueError, match="existing file"):
        m.audit_gazepoint_export_schema(tmp_path / "missing.csv")

    p = tmp_path / "tab.tsv"
    p.write_text("time_s\tGSR\n0\t1\n", encoding="utf-8")
    out = m.audit_gazepoint_export_schema(p, expected_roles=["time_s", "GSR"])
    assert out.present.all()

    manifest = tmp_path / "manifest.txt"
    result = m.create_gazepoint_analysis_manifest(
        settings={}, outputs=["a.csv", "b.csv"], path=manifest
    )
    text = manifest.read_text(encoding="utf-8")
    assert "[files]\nnone" in text
    assert "a.csv" in text and "b.csv" in text
    assert "session_info" in result


def test_template_similarity_dataframe_without_time_and_timestamp_peak():
    # No time column triggers sampling-rate construction.
    phase = np.linspace(0, 8 * np.pi, 200)
    df = pd.DataFrame({"PPG": np.sin(phase)})
    out = m.compute_gazepoint_ppg_template_similarity(
        df, sampling_rate_hz=50, peaks=[0.5, 1.5, 2.5, 3.5]
    )
    assert out["settings"]["n_grid"] == 101


def test_aoi_dwell_duration_without_time_column():
    out = m.summarize_gazepoint_aoi_dwell(
        pd.DataFrame({"AOI": ["A", "A", "B"], "duration": [0.1, 0.2, 0.3]}),
        duration_col="duration",
    )
    assert out.loc[out.AOI == "A", "dwell_time_s"].iloc[0] == pytest.approx(0.3)
