from __future__ import annotations

import numpy as np
import pandas as pd

import gpbiometricspy as gp
from gpbiometricspy import qc_dropouts as qd


def test_pending_registration_helper_is_exercisable_without_pending_exports():
    name = "__coverage_future_export__"
    try:
        gp._register_pending_exports([name])
        fn = getattr(gp, name)
        assert fn.__name__ == name
    finally:
        gp.__dict__.pop(name, None)


def test_signal_activity_distinguishes_missing_from_nonnumeric():
    missing = qd.audit_gazepoint_signal_activity(pd.DataFrame({"x": [np.nan, np.nan]}), signal_cols="x")
    text = qd.audit_gazepoint_signal_activity(pd.DataFrame({"x": ["bad", "worse"]}), signal_cols="x")
    empty = qd.audit_gazepoint_signal_activity(pd.DataFrame({"x": pd.Series(dtype=float)}), signal_cols="x")
    assert missing["signal_by_group"].iloc[0].status == "insufficient_data"
    assert text["signal_by_group"].iloc[0].status == "nonnumeric"
    assert empty["signal_by_group"].iloc[0].status == "insufficient_data"
