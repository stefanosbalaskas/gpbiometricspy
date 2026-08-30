from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp
import gpbiometricspy.roadmap_final_gaps as rfg


def _prepared(matrix=None):
    if matrix is None:
        matrix = np.array([[0.1, 0.2, 0.3], [3.0, 3.1, 3.2]], float)
    return {
        "data": matrix,
        "channel_info": pd.DataFrame(
            {"channel_name": ["gaze_x", "pupil"], "channel_type": ["eyegaze", "pupil"]}
        ),
        "info_spec": {"sfreq": 100.0},
        "rawarray_spec": {"first_samp": 4},
    }


def test_final_gap_private_resolvers_and_validation_edges():
    df = pd.DataFrame({"time": [0.0, 0.1], "x": [0.1, 0.2], "y": [0.2, 0.3]})
    with pytest.raises(ValueError, match="non-empty"):
        rfg._resolve_col(df, "", ["time"], "time")
    with pytest.raises(ValueError, match="not found"):
        rfg._resolve_col(df, "missing", ["time"], "time")
    with pytest.raises(ValueError, match="Could not identify"):
        rfg._resolve_col(df, None, ["missing"], "time")

    with pytest.raises(ValueError, match="time_unit"):
        rfg._resolve_time_unit([0, 1], "time", "minutes")
    assert rfg._resolve_time_unit([0, 1], "time", "seconds") == "seconds"
    with pytest.raises(ValueError, match="Could not infer"):
        rfg._resolve_time_unit([1, 1, np.nan], "time", "auto")
    assert rfg._resolve_time_unit([0, 0.1, 0.2], "time", "auto") == "seconds"
    assert rfg._resolve_time_unit([0, 10, 20], "time", "auto") == "milliseconds"
    with pytest.raises(ValueError, match="ambiguous"):
        rfg._resolve_time_unit([0, 2, 4], "time", "auto")

    with pytest.raises(ValueError, match="duration_unit"):
        rfg._resolve_duration_unit([1], "duration", "minutes")
    assert rfg._resolve_duration_unit([1], "duration", "seconds") == "seconds"
    assert rfg._resolve_duration_unit([1], "sample_count") == "samples"
    assert rfg._resolve_duration_unit([1], "duration_sec") == "seconds"
    with pytest.raises(ValueError, match="Could not infer"):
        rfg._resolve_duration_unit([np.nan], "duration")
    assert rfg._resolve_duration_unit([100, 200], "duration") == "milliseconds"
    assert rfg._resolve_duration_unit([0.1, 0.2], "duration") == "seconds"

    with pytest.raises(ValueError, match="Unsupported unit"):
        rfg._to_seconds([1], "minutes")
    numeric_valid = rfg._valid_values(pd.Series([1, 0, -1, np.nan], dtype=float))
    assert numeric_valid.tolist() == [True, False, False, False]

    with pytest.raises(ValueError, match="coordinate_system"):
        rfg._coordinate_system(np.array([0.1]), np.array([0.2]), "cm")
    assert rfg._coordinate_system(np.array([np.nan]), np.array([np.nan]), "auto") == "normalized"
    assert rfg._coordinate_system(np.array([1.7]), np.array([1.8]), "auto") == "degrees"

    base = pd.DataFrame({"time_s": [0, 0.1], "gaze_x": [0.1, 0.2], "gaze_y": [0.2, 0.3]})
    with pytest.raises(ValueError, match="missing_threshold"):
        gp.validate_gazepoint_gaze(base, missing_threshold=2)
    with pytest.raises(ValueError, match="gap_multiplier"):
        gp.validate_gazepoint_gaze(base, gap_multiplier=0)
    with pytest.raises(ValueError, match="no finite"):
        gp.validate_gazepoint_gaze(base.assign(time_s=np.nan))
    with pytest.raises(ValueError, match="expected_sampling_rate_hz"):
        gp.validate_gazepoint_gaze(base, expected_sampling_rate_hz=0)
    with pytest.raises(ValueError, match="screen_width_px"):
        gp.validate_gazepoint_gaze(base, screen_width_px=0)


def test_fixation_summary_remaining_argument_and_empty_edges():
    fix = pd.DataFrame({"aoi": [None, ""], "start_ms": [0, 10], "duration_ms": [2, 2]})
    with pytest.raises(TypeError, match="include_unassigned"):
        gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="start_ms", duration_col="duration_ms", include_unassigned=1)
    with pytest.raises(ValueError, match="unassigned_label"):
        gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="start_ms", duration_col="duration_ms", include_unassigned=True, unassigned_label="")
    with pytest.raises(ValueError, match="No valid assigned"):
        gp.summarise_gazepoint_fixations_by_aoi(fix, start_col="start_ms", duration_col="duration_ms")


def test_mne_writer_execute_and_defensive_paths(monkeypatch, tmp_path):
    with pytest.raises(TypeError, match="overwrite"):
        gp.write_gazepoint_mne_fif(_prepared(), tmp_path / "x_raw.fif", overwrite="yes", execute=False)
    with pytest.raises(ValueError, match="fname"):
        gp.write_gazepoint_mne_fif(_prepared(), "", execute=False)
    with pytest.raises(ValueError, match="empty"):
        gp.write_gazepoint_mne_fif(_prepared(np.empty((0, 0))), tmp_path / "x_raw.fif", execute=False)

    non_df_info = _prepared()
    non_df_info["channel_info"] = {"channel_name": ["gaze_x", "pupil"], "channel_type": ["eyegaze", "pupil"]}
    converted = gp.write_gazepoint_mne_fif(non_df_info, tmp_path / "converted_raw.fif", execute=False)
    assert isinstance(converted["channel_info"], pd.DataFrame)

    # DataFrame coercion path delegates to the public MNE-input preparation helper.
    monkeypatch.setattr(gp, "prepare_gazepoint_mne_input", lambda x: _prepared())
    dry = gp.write_gazepoint_mne_fif(pd.DataFrame({"x": [1]}), tmp_path / "df_raw.fif", execute=False)
    assert dry["n_channels"] == 2
    with pytest.raises(TypeError, match="must be"):
        gp.write_gazepoint_mne_fif(object(), tmp_path / "x_raw.fif", execute=False)

    # Import failure is a documented optional-dependency path.
    monkeypatch.setitem(sys.modules, "mne", None)
    with pytest.raises(ImportError, match="MNE is required"):
        gp.write_gazepoint_mne_fif(_prepared(), tmp_path / "missing_raw.fif", execute=True)
    monkeypatch.delitem(sys.modules, "mne", raising=False)

    saved = {}

    class FakeRaw:
        def __init__(self, matrix, info, first_samp=0, verbose=None):
            saved["raw_init"] = (matrix.copy(), info, first_samp, verbose)
            self.annotations = None

        def set_annotations(self, ann):
            self.annotations = ann
            saved["annotations"] = ann

        def save(self, path, overwrite=False, fmt="single", verbose=None):
            saved["save"] = (path, overwrite, fmt, verbose)
            Path(path).write_bytes(b"fake-fif")

    fake_mne = SimpleNamespace(
        __version__="test-mne",
        create_info=lambda ch_names, sfreq, ch_types: {"ch_names": ch_names, "sfreq": sfreq, "ch_types": ch_types},
        io=SimpleNamespace(RawArray=FakeRaw),
        annotations_from_events=lambda events, sfreq, event_desc, first_samp: {
            "events": events.copy(), "sfreq": sfreq, "event_desc": dict(event_desc), "first_samp": first_samp
        },
    )
    monkeypatch.setitem(sys.modules, "mne", fake_mne)

    event_dict = {"events": np.array([[4, 0, 1], [10, 0, 2]]), "event_dictionary": {"event_code": [1, 2], "event_label": ["A", "B"]}}
    out = gp.write_gazepoint_mne_fif(_prepared(), tmp_path / "exec_raw.fif", events=event_dict, overwrite=True, fmt="double", execute=True, verbose=True)
    assert out["executed"] is True and out["mne_version"] == "test-mne"
    assert saved["annotations"]["event_desc"] == {1: "A", 2: "B"}
    assert Path(out["output"]).exists()

    # Event descriptions are generated when no dictionary is supplied.
    out2 = gp.write_gazepoint_mne_fif(_prepared(), tmp_path / "exec2_raw.fif", events=np.array([[4, 0, 7]]), execute=True)
    assert out2["event_count"] == 1
    assert saved["annotations"]["event_desc"] == {7: "event_7"}

    bad_rate = _prepared()
    bad_rate["info_spec"]["sfreq"] = np.nan
    with pytest.raises(ValueError, match="positive sampling"):
        gp.write_gazepoint_mne_fif(bad_rate, tmp_path / "rate_raw.fif", execute=True)


class _FakeInfo:
    def __init__(self, name, typ, source, uid="uid", host="host"):
        self._name, self._typ, self._source, self._uid, self._host = name, typ, source, uid, host

    def name(self): return self._name
    def type(self): return self._typ
    def source_id(self): return self._source
    def uid(self): return self._uid
    def hostname(self): return self._host


class _FakeInlet:
    closed = 0

    def __init__(self, info, max_buflen=1, recover=True):
        self.info = info
        self.k = 0

    def time_correction(self, timeout=0):
        self.k += 1
        return 0.001 * self.k

    def close_stream(self):
        type(self).closed += 1


def _fake_pylsl(streams):
    return SimpleNamespace(
        __version__="test-lsl",
        resolve_streams=lambda wait_time: list(streams),
        StreamInlet=_FakeInlet,
        local_clock=lambda: 123.456,
    )


def test_lsl_execute_filtering_summary_and_errors(monkeypatch):
    with pytest.raises(ValueError, match="stream_name"):
        gp.estimate_gazepoint_lsl_clock_offsets(stream_name="", execute=False)
    with pytest.raises(TypeError, match="execute"):
        gp.estimate_gazepoint_lsl_clock_offsets(execute="yes")

    monkeypatch.setitem(sys.modules, "pylsl", None)
    with pytest.raises(ImportError, match="pylsl"):
        gp.estimate_gazepoint_lsl_clock_offsets(execute=True)
    monkeypatch.delitem(sys.modules, "pylsl", raising=False)

    streams = [
        _FakeInfo("wrong", "Gaze", "src"),      # name filter continue
        _FakeInfo("GP", "wrong", "src"),        # type filter continue
        _FakeInfo("GP", "Gaze", "wrong"),       # source filter continue
        _FakeInfo("GP", "Gaze", "src", "u1"),
        _FakeInfo("GP", "Gaze", "src", "u2"),  # duplicate name -> make.unique suffix
    ]
    monkeypatch.setitem(sys.modules, "pylsl", _fake_pylsl(streams))
    monkeypatch.setattr(rfg.time, "sleep", lambda _: None)
    _FakeInlet.closed = 0
    out = gp.estimate_gazepoint_lsl_clock_offsets(
        stream_name="GP", stream_type="Gaze", source_id="src", timeout_s=1,
        n_estimates=2, pause_s=0.01, execute=True
    )
    assert out["executed"] is True
    assert len(out["estimates"]) == 4
    assert set(out["clock_offsets_s"]) == {"GP"}
    assert _FakeInlet.closed == 2

    # Two summary groups can share a stream name when type/source differ; keys are made unique.
    monkeypatch.setitem(sys.modules, "pylsl", _fake_pylsl([
        _FakeInfo("GP", "Gaze", "src1", "u1"),
        _FakeInfo("GP", "Markers", "src2", "u2"),
    ]))
    dup = gp.estimate_gazepoint_lsl_clock_offsets(n_estimates=1, pause_s=0, execute=True, timeout_s=0.01)
    assert set(dup["clock_offsets_s"]) == {"GP", "GP.1"}

    monkeypatch.setitem(sys.modules, "pylsl", _fake_pylsl([_FakeInfo("no", "Gaze", "src")]))
    with pytest.raises(RuntimeError, match="No active LSL streams"):
        gp.estimate_gazepoint_lsl_clock_offsets(stream_name="GP", execute=True, timeout_s=0.01)

    class WeirdInt(int):
        def __new__(cls): return int.__new__(cls, 1)
        def __int__(self): return 0

    monkeypatch.setitem(sys.modules, "pylsl", _fake_pylsl([_FakeInfo("GP", "Gaze", "src")]))
    with pytest.raises(RuntimeError, match="No LSL clock-offset estimates"):
        gp.estimate_gazepoint_lsl_clock_offsets(n_estimates=WeirdInt(), execute=True, timeout_s=0.01)
