from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import gpbiometricspy as gp


def test_gaze_validation_singleton_group_skips_interval_gap_branch():
    data = pd.DataFrame({"time_s": [0.0], "gaze_x": [0.5], "gaze_y": [0.5]})

    out = gp.validate_gazepoint_gaze(data)

    assert len(out["groups"]) == 1
    assert np.isnan(out["groups"].iloc[0]["median_interval_s"])
    assert int(out["groups"].iloc[0]["large_gap_count"]) == 0


def test_mne_fif_execute_without_events_skips_annotation_branch(monkeypatch, tmp_path):
    saved = {}

    class FakeRaw:
        def __init__(self, matrix, info, first_samp=0, verbose=None):
            saved["matrix"] = np.asarray(matrix).copy()
            saved["info"] = info
            saved["first_samp"] = first_samp

        def set_annotations(self, annotations):
            raise AssertionError("No annotations should be set when events=None")

        def save(self, path, overwrite=False, fmt="single", verbose=None):
            saved["save"] = (path, overwrite, fmt, verbose)
            Path(path).write_bytes(b"fake-fif")

    fake_mne = SimpleNamespace(
        __version__="test-mne",
        create_info=lambda ch_names, sfreq, ch_types: {
            "ch_names": ch_names,
            "sfreq": sfreq,
            "ch_types": ch_types,
        },
        io=SimpleNamespace(RawArray=FakeRaw),
    )
    monkeypatch.setitem(sys.modules, "mne", fake_mne)

    prepared = {
        "data": np.array([[0.1, 0.2, 0.3]], dtype=float),
        "channel_info": pd.DataFrame(
            {"channel_name": ["gaze_x"], "channel_type": ["eyegaze"]}
        ),
        "info_spec": {"sfreq": 100.0},
        "rawarray_spec": {"first_samp": 0},
    }

    out = gp.write_gazepoint_mne_fif(
        prepared,
        tmp_path / "noevents_raw.fif",
        events=None,
        execute=True,
    )

    assert out["executed"] is True
    assert out["event_count"] == 0
    assert Path(out["output"]).exists()


class _Info:
    def __init__(self, name: str, uid: str):
        self._name = name
        self._uid = uid

    def name(self):
        return self._name

    def type(self):
        return "Gaze"

    def source_id(self):
        return "source"

    def uid(self):
        return self._uid

    def hostname(self):
        return "host"


class _InletWithoutClose:
    def __init__(self, info, max_buflen=1, recover=True):
        self.info = info

    def time_correction(self, timeout=0):
        return 0.001


def test_lsl_multiple_streams_continue_when_inlet_has_no_close_stream(monkeypatch):
    streams = [_Info("GP", "u1"), _Info("GP", "u2")]
    fake_pylsl = SimpleNamespace(
        __version__="test-lsl",
        resolve_streams=lambda wait_time: list(streams),
        StreamInlet=_InletWithoutClose,
        local_clock=lambda: 123.456,
    )
    monkeypatch.setitem(sys.modules, "pylsl", fake_pylsl)

    out = gp.estimate_gazepoint_lsl_clock_offsets(
        timeout_s=1,
        n_estimates=1,
        pause_s=0,
        execute=True,
    )

    assert out["executed"] is True
    assert len(out["estimates"]) == 2
    assert set(out["estimates"]["uid"]) == {"u1", "u2"}
