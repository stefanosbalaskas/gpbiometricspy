from __future__ import annotations

import pandas as pd

import gpbiometricspy as gp


def test_ttl_alignment_falls_back_to_row_order_when_sample_values_are_nonnumeric():
    data = pd.DataFrame(
        {
            "TTL0": [0, 1, 0],
            "time": ["x", "x", "x"],
            "CNT": ["a", "b", "c"],
        }
    )

    out = gp.align_gazepoint_biometrics_to_ttl(
        data,
        time_col="time",
        sample_col="CNT",
        pre_window_samples=0,
        post_window_samples=0,
    )

    assert len(out["events"]) == 1
    assert out["overview"].iloc[0]["status"] == "ttl_events_aligned"


def test_ttl_alignment_skips_nearby_collapse_when_event_times_are_missing():
    data = pd.DataFrame(
        {
            "TTL0": [1, 1, 0],
            "time": ["x", "x", "x"],
            "CNT": [1, 2, 3],
        }
    )

    out = gp.align_gazepoint_biometrics_to_ttl(
        data,
        time_col="time",
        sample_col="CNT",
        event_edge="active",
        collapse_nearby_ms=10,
        pre_window_samples=0,
        post_window_samples=0,
    )

    assert len(out["events"]) == 2
    assert out["events"]["event_time_ms"].isna().all()
