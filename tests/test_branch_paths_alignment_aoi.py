from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def _streams():
    reference = pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "value": [1.0, 2.0, 3.0]})
    target = pd.DataFrame({"time_s": [0.2, 1.2, 2.2], "value": [4.0, 5.0, 6.0]})
    return reference, target


def test_alignment_event_vector_and_guardrail_paths():
    reference, target = _streams()

    with pytest.raises(TypeError, match="events.*data frame"):
        gp.align_gazepoint_streams_by_events(
            reference,
            target,
            ["not-numeric"],
            [0.0],
        )

    with pytest.raises(ValueError, match="method"):
        gp.align_gazepoint_streams_by_events(
            reference,
            target,
            [0.0],
            [0.2],
            method="unsupported",
        )

    with pytest.raises(ValueError, match="No event pairs"):
        gp.align_gazepoint_streams_by_events(
            reference,
            target,
            np.array([], dtype=float),
            np.array([], dtype=float),
        )

    with pytest.raises(ValueError, match="No finite event pairs"):
        gp.align_gazepoint_streams_by_events(
            reference,
            target,
            [np.nan],
            [np.nan],
        )


def test_aoi_timecourse_validation_paths():
    gaze = pd.DataFrame(
        {
            "time_s": [0.0, 0.1, 0.2],
            "gaze_x": [0.1, 0.2, 0.3],
            "gaze_y": [0.1, 0.2, 0.3],
            "AOI": ["A", "A", "B"],
        }
    )

    with pytest.raises(ValueError, match="aoi_definitions"):
        gp.build_gazepoint_aoi_timecourse(
            gaze,
            aoi_definitions=pd.DataFrame({"AOI": ["A"], "xmin": [0.0]}),
        )

    with pytest.raises(ValueError, match="Missing grouping columns"):
        gp.build_gazepoint_aoi_timecourse(gaze, group_cols="participant")

    with pytest.raises(ValueError, match="bin_width_s"):
        gp.build_gazepoint_aoi_timecourse(gaze, bin_width_s=0)

    with pytest.raises(ValueError, match="aoi_col"):
        gp.build_gazepoint_aoi_timecourse(gaze, aoi_col="missing")


def test_aoi_timecourse_nonfinite_time_and_nonempty_only_paths():
    no_time = gp.build_gazepoint_aoi_timecourse(
        pd.DataFrame({"time_s": [np.nan, np.nan], "AOI": ["A", "B"]})
    )
    assert no_time.empty

    sparse = gp.build_gazepoint_aoi_timecourse(
        pd.DataFrame({"time_s": [0.0, 1.0], "AOI": ["A", "B"]}),
        bin_width_s=1.0,
        include_empty=False,
    )
    assert len(sparse) == 2
    assert (sparse.aoi_samples == 1).all()


def test_eventlocked_group_mismatch_and_no_window_paths():
    stream = pd.DataFrame(
        {
            "participant": ["P1", "P1", "P1"],
            "time_s": [0.0, 1.0, 2.0],
            "signal": [1.0, 2.0, 3.0],
        }
    )

    mismatch_events = pd.DataFrame(
        {"event_time_s": [1.0], "event_id": ["E1"], "participant": ["P2"]}
    )
    mismatch = gp.summarize_gazepoint_eventlocked_multimodal(
        stream,
        mismatch_events,
        group_cols="participant",
        signal_cols="signal",
    )
    assert mismatch["samples"].empty
    assert mismatch["summary"].empty

    far_events = pd.DataFrame(
        {"event_time_s": [100.0], "event_id": ["E2"], "participant": ["P1"]}
    )
    outside = gp.summarize_gazepoint_eventlocked_multimodal(
        stream,
        far_events,
        group_cols="participant",
        signal_cols="signal",
        pre_s=1,
        post_s=1,
    )
    assert outside["samples"].empty
    assert outside["summary"].empty


def test_quality_dashboard_title_guard():
    with pytest.raises(ValueError, match="title"):
        gp.create_gazepoint_quality_dashboard(title="")
