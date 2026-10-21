import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.october_2026.synchronization_validation import (  # noqa: E402
    audit_clock_and_event_alignment,
)


def _data():
    anchors = pd.DataFrame({
        "participant_id": ["p"] * 4,
        "session_id": ["s"] * 4,
        "device_time_s": [1., 2., 3., 4.],
        "reference_time_s": [1.1, 2.1, 3.1, 4.1],
    })
    events = pd.DataFrame({
        "participant_id": ["p"] * 2,
        "session_id": ["s"] * 2,
        "device_event_time_s": [1.5, 3.5],
        "reference_event_time_s": [1.6, 3.6],
    })
    return anchors, events


def test_offset_and_affine_recovery_from_independent_anchor_events():
    anchors, events = _data()
    for method in ["offset", "affine"]:
        a = audit_clock_and_event_alignment(anchors, events, fit=method)
        assert a["clock_fits"].iloc[0].clock_offset_s == pytest.approx(.1)
        assert a["clock_fits"].iloc[0].clock_slope == pytest.approx(1)
        assert a["independent_event_errors"].absolute_event_alignment_error_ms.max() < 1e-8


def test_refuses_unmatched_sessions():
    anchors, events = _data()
    events["session_id"] = "other"
    with pytest.raises(ValueError, match="independent event"):
        audit_clock_and_event_alignment(anchors, events)
