import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_biosppy_missing_group_and_explicit_time_preparation_paths():
    base = pd.DataFrame(
        {"time_s": [0.0, 0.1, 0.2], "EDA": [1.0, 1.1, 1.2]}
    )
    with pytest.raises(ValueError, match="Missing group columns"):
        gp.extract_gazepoint_eda_events_biosppy_style(
            base,
            signal_col="EDA",
            time_col="time_s",
            group_cols="missing",
            sampling_rate_hz=10,
        )

    prepared = gp.prepare_gazepoint_biosppy_input(
        base,
        signal_type="eda",
        signal_col="EDA",
        time_col="time_s",
    )
    assert prepared["settings"]["time_col"] == "time_s"
    assert prepared["sampling_rates_hz"].iloc[0] == pytest.approx(10.0)


def test_biosppy_bandpass_invalid_band_public_fallback():
    t = np.arange(0.0, 2.0, 0.1)
    x = np.sin(2 * np.pi * t)
    out = gp.compute_gazepoint_signal_phase_locking(
        x,
        x,
        sampling_rate_hz=10,
        band=(6.0, 8.0),
    )
    assert out.loc[0, "phase_locking_value"] == pytest.approx(1.0)


def test_biosppy_manifest_only_collision_path(tmp_path):
    manifest = tmp_path / "gazepoint_biosppy_eda_manifest.csv"
    manifest.write_text("existing\n", encoding="utf-8")

    base = pd.DataFrame(
        {"time_s": [0.0, 0.1, 0.2], "EDA": [1.0, 1.1, 1.2]}
    )
    with pytest.raises(FileExistsError, match="already exists"):
        gp.prepare_gazepoint_biosppy_input(
            base,
            signal_type="eda",
            output_dir=tmp_path,
        )


def test_biosppy_invalid_inferred_eda_sampling_rate_path():
    one = pd.DataFrame({"time_s": [0.0], "EDA": [1.0]})
    with pytest.raises(ValueError, match="valid sampling rate"):
        gp.extract_gazepoint_eda_events_biosppy_style(
            one,
            signal_col="EDA",
            time_col="time_s",
        )
