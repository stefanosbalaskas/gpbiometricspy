import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_mne_event_validation_sample_units_and_embedded_codes():
    with pytest.raises(ValueError, match="sampling_rate_hz"):
        gp.prepare_gazepoint_mne_events([0.0, 1.0])
    with pytest.raises(ValueError, match="Invalid option"):
        gp.prepare_gazepoint_mne_events([0.0], sampling_rate_hz=10, marker_onset="bad")
    with pytest.raises(ValueError, match="at least one row"):
        gp.prepare_gazepoint_mne_events(pd.DataFrame(), sampling_rate_hz=10)

    with pytest.raises(ValueError, match="event time column"):
        gp.prepare_gazepoint_mne_events(
            pd.DataFrame({"TTL": [0, 1]}), marker_cols="TTL", sampling_rate_hz=10
        )
    with pytest.raises(ValueError, match="Marker column not found"):
        gp.prepare_gazepoint_mne_events(
            pd.DataFrame({"time_s": [0.0, 1.0]}), marker_cols="TTL", sampling_rate_hz=10
        )
    with pytest.raises(ValueError, match="No active marker events"):
        gp.prepare_gazepoint_mne_events(
            pd.DataFrame({"time_s": [0.0, 1.0], "TTL": [0, 0]}),
            marker_cols="TTL",
            sampling_rate_hz=10,
        )
    with pytest.raises(ValueError, match="event time column"):
        gp.prepare_gazepoint_mne_events(
            pd.DataFrame({"event_label": ["a"]}), sampling_rate_hz=10
        )

    sample_units = gp.prepare_gazepoint_mne_events(
        [10, 20], sampling_rate_hz=100, time_unit="samples", first_samp=5
    )
    assert sample_units["events"][:, 0].tolist() == [15, 25]
    np.testing.assert_allclose(sample_units["table"]["event_time_s"], [0.1, 0.2])

    coded = gp.prepare_gazepoint_mne_events(
        pd.DataFrame(
            {
                "event_time_s": [0.1, 0.2],
                "event_label": ["left", "right"],
                "code": [41, 42],
            }
        ),
        sampling_rate_hz=100,
        event_code_col="code",
    )
    assert coded["events"][:, 2].tolist() == [41, 42]
    assert coded["event_id"] == {"left": 41, "right": 42}

    with pytest.raises(ValueError, match="Missing event codes"):
        gp.prepare_gazepoint_mne_events(
            pd.DataFrame(
                {"event_time_s": [0.0, 1.0], "event_label": ["a", "b"]}
            ),
            sampling_rate_hz=10,
            event_id={"a": 1},
        )


def test_mne_input_validation_and_eeg_ecg_channel_inference():
    with pytest.raises(TypeError, match="non-empty data frame"):
        gp.prepare_gazepoint_mne_input([1, 2, 3])
    with pytest.raises(TypeError, match="non-empty data frame"):
        gp.prepare_gazepoint_mne_input(pd.DataFrame())
    with pytest.raises(ValueError, match="Invalid option"):
        gp.prepare_gazepoint_mne_input(
            pd.DataFrame({"time_s": [0.0, 1.0], "EEG1": [1.0, 2.0]}), missing="bad"
        )
    with pytest.raises(ValueError, match="time column or sampling rate"):
        gp.prepare_gazepoint_mne_input(pd.DataFrame({"EEG1": [1.0, 2.0]}))
    with pytest.raises(ValueError, match="valid sampling rate"):
        gp.prepare_gazepoint_mne_input(
            pd.DataFrame({"time_s": [0.0], "EEG1": [1.0]})
        )
    with pytest.raises(ValueError, match="No channel columns"):
        gp.prepare_gazepoint_mne_input(pd.DataFrame({"time_s": [0.0, 0.1, 0.2]}))
    with pytest.raises(ValueError, match="Channel not found"):
        gp.prepare_gazepoint_mne_input(
            pd.DataFrame({"time_s": [0.0, 0.1], "EEG1": [1.0, 2.0]}),
            channel_cols="missing",
        )
    with pytest.raises(ValueError, match="metadata lengths"):
        gp.prepare_gazepoint_mne_input(
            pd.DataFrame(
                {"time_s": [0.0, 0.1], "EEG1": [1.0, 2.0], "ECG": [0.2, 0.3]}
            ),
            channel_cols=["EEG1", "ECG"],
            channel_names=["only_one"],
        )

    inferred = gp.prepare_gazepoint_mne_input(
        pd.DataFrame(
            {
                "time_s": [0.0, 0.1, 0.2],
                "EEG1": [1.0, 2.0, 3.0],
                "ECG": [0.1, 0.2, 0.3],
            }
        ),
        channel_cols=["EEG1", "ECG"],
    )
    assert inferred["channel_info"]["channel_type"].tolist() == ["eeg", "ecg"]


def test_eeg_alignment_public_guardrails_and_residual_policy():
    gaze = pd.DataFrame({"time_s": [0.0, 1.0, 2.0], "pupil": [3.0, 3.1, 3.2]})
    gp_events = pd.DataFrame(
        {"event_id": ["a", "b", "c"], "event_time_s": [0.0, 1.0, 2.0]}
    )
    eeg_events = pd.DataFrame(
        {"event_id": ["a", "b", "c"], "event_time_s": [0.0, 1.0, 3.0]}
    )

    with pytest.raises(ValueError, match="Invalid option"):
        gp.align_gazepoint_to_eeg(gaze, gp_events, eeg_events, method="bad")
    with pytest.raises(TypeError, match="data frames"):
        gp.align_gazepoint_to_eeg(gaze, gp_events, [1, 2, 3])
    with pytest.raises(ValueError, match="Sampling rate is required for sample time"):
        gp.align_gazepoint_to_eeg(
            gaze,
            gp_events,
            eeg_events,
            gazepoint_time_unit="samples",
        )

    sample_events = pd.DataFrame({"event_id": ["a"], "sample": [10]})
    with pytest.raises(ValueError, match="eeg_sampling_rate_hz"):
        gp.align_gazepoint_to_eeg(
            gaze,
            gp_events.iloc[:1],
            sample_events,
            eeg_event_sample_col="sample",
        )

    with pytest.raises(ValueError, match="No matched finite events"):
        gp.align_gazepoint_to_eeg(
            gaze,
            pd.DataFrame({"event_id": ["a"], "event_time_s": [0.0]}),
            pd.DataFrame({"event_id": ["z"], "event_time_s": [0.1]}),
            match_by="id",
        )

    with pytest.raises(ValueError, match="At least two events"):
        gp.align_gazepoint_to_eeg(
            gaze,
            gp_events.iloc[:1],
            eeg_events.iloc[:1],
            method="linear",
            match_by="row",
        )

    with pytest.raises(ValueError, match="Alignment residual exceeds"):
        gp.align_gazepoint_to_eeg(
            gaze,
            gp_events,
            eeg_events,
            method="offset",
            match_by="row",
            maximum_residual_s=0.1,
        )

    allowed = gp.align_gazepoint_to_eeg(
        gaze,
        gp_events,
        eeg_events,
        method="offset",
        match_by="row",
        robust=False,
        maximum_residual_s=0.1,
        residual_action="allow",
    )
    assert allowed["audit"]["maximum_abs_residual_s"] > 0.1


def test_lsl_public_validation_and_linear_dejitter_guardrails():
    with pytest.raises(ValueError, match="non-empty named mapping"):
        gp.sync_gazepoint_signals_via_lsl({})
    with pytest.raises(ValueError, match="Invalid option"):
        gp.sync_gazepoint_signals_via_lsl(
            {"gaze": pd.DataFrame({"time_s": [0.0], "x": [0.5]})}, merge="bad"
        )
    with pytest.raises(ValueError, match="time column for stream"):
        gp.sync_gazepoint_signals_via_lsl(
            {"gaze": pd.DataFrame({"x": [0.2, 0.3]})}
        )
    with pytest.raises(ValueError, match="Nominal rate required"):
        gp.sync_gazepoint_signals_via_lsl(
            {"gaze": pd.DataFrame({"time_s": [0.0, 0.1], "x": [0.2, 0.3]})},
            dejitter="linear",
        )

    one_dimensional = gp.sync_gazepoint_signals_via_lsl(
        {
            "marker": {
                "time_stamps": [1.0, 2.0],
                "time_series": [10.0, 20.0],
            }
        },
        relative_zero="none",
    )
    assert "value_1" in one_dimensional["streams"]["marker"].columns
