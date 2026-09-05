from __future__ import annotations

import pandas as pd

import gpbiometricspy as gp


def test_single_sample_auto_time_through_public_fixation_detector():
    out = gp.detect_gazepoint_fixations(
        pd.DataFrame({"time": [0.0], "x": [0.1], "y": [0.2]}),
        time_col="time",
        x_col="x",
        y_col="y",
        time_unit="auto",
        velocity_threshold=10.0,
    )
    assert out["summary"].loc[0, "n_samples"] == 1
