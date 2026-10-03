import numpy as np
import pandas as pd

import gpbiometricspy.ppg_equity as pe


def test_remaining_ppg_equity_branch_arcs(monkeypatch):
    assert pe._sampling_rate(pd.DataFrame({"t": [0.0, 0.1, 0.2]}), "t", None) == 10.0

    low_fs = pe._ppg_sqi(np.sin(np.linspace(0, 4 * np.pi, 32)), 0.5, 1e-8)
    assert np.isnan(low_fs["ppg_snr_db"])

    original_welch = pe.signal.welch

    def zero_noise_welch(y, fs, nperseg):
        return np.array([0.0, 1.0]), np.array([0.0, 1.0])

    monkeypatch.setattr(pe.signal, "welch", zero_noise_welch)
    no_noise = pe._ppg_sqi(np.sin(np.linspace(0, 4 * np.pi, 32)), 10.0, 1e-8)
    assert np.isnan(no_noise["ppg_snr_db"])
    monkeypatch.setattr(pe.signal, "welch", original_welch)

    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, 4.0],
            "y": [1.0, 2.0, 3.0, 4.0],
            "p": ["a", "a", "b", "b"],
        }
    )
    original_slope = pe._slope
    monkeypatch.setattr(pe, "_slope", lambda x, y: np.nan)
    boot = pe._cluster_bootstrap_slope(frame, "x", "y", "p", 2, np.random.default_rng(1))
    assert np.isnan(boot["ci_low"])
    monkeypatch.setattr(pe, "_slope", original_slope)

    original_metrics = pe._agreement_metrics

    def partly_nan_metrics(d, reference_col, candidate_col, participant_col):
        return {
            "n_rows": len(d),
            "n_participants": 2,
            "reference_available": len(d),
            "n_pairs": len(d),
            "retention_rate": 1.0,
            "bias": 0.0,
            "mae": 0.0,
            "rmse": 0.0,
            "loa_lower": 0.0,
            "loa_upper": 0.0,
            "lin_ccc": np.nan,
        }

    monkeypatch.setattr(pe, "_agreement_metrics", partly_nan_metrics)
    agreement = pe._cluster_bootstrap_agreement(
        pd.DataFrame(
            {
                "p": ["a", "a", "b", "b"],
                "r": [1.0, 2.0, 3.0, 4.0],
                "c": [1.0, 2.0, 3.0, 4.0],
            }
        ),
        "r",
        "c",
        "p",
        2,
        np.random.default_rng(2),
    )
    assert np.isnan(agreement.loc[agreement["metric"] == "lin_ccc", "ci_low"].iloc[0])
    monkeypatch.setattr(pe, "_agreement_metrics", original_metrics)
