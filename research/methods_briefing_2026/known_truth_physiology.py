"""Reproducible *phenomenological* known-truth cardiovascular/EDA test signals.

For methodological error recovery only. NOT a biophysically validated generator
of ECG, PPG, heart-rate variability, respiration or electrodermal physiology.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def simulate_known_truth_physiology(
    *,
    duration_s: float = 20.0,
    sampling_rate_hz: float = 100.0,
    heart_rate_bpm: float = 75.0,
    scr_onsets_s: Sequence[float] = (3.0, 9.0),
    scr_amplitudes: Sequence[float] = (0.5, 0.8),
    noise_sd: float = 0.03,
    dropout_fraction: float = 0.02,
    seed: int = 2026,
) -> dict:
    """Return separate latent, corrupted, artifact and event-truth tables.

    Nominally sampled ECG-like spikes, delayed PPG-like pulses, and a toy
    tonic+phasic EDA convolution; these are *not validated physiological
    forward models*. SCR responses can overlap. Beat times are exact truth.
    """
    numeric = [duration_s, sampling_rate_hz, heart_rate_bpm, noise_sd, dropout_fraction]
    if not all(np.isfinite(numeric)):
        raise ValueError("parameters must be finite")
    if duration_s <= 0 or sampling_rate_hz < 20 or heart_rate_bpm <= 0:
        raise ValueError("positive duration/rate/HR required; sample rate >=20 Hz")
    if noise_sd < 0 or not 0 <= dropout_fraction <= 1:
        raise ValueError("noise and dropout parameters must be valid")
    n = int(np.floor(duration_s * sampling_rate_hz))
    if n < 40 or n > 1_000_000:
        raise ValueError("sample count must be from 40 to 1,000,000")
    onsets = np.asarray(scr_onsets_s, dtype=float)
    amplitudes = np.asarray(scr_amplitudes, dtype=float)
    if (onsets.ndim != 1 or amplitudes.shape != onsets.shape
            or not np.isfinite(onsets).all() or not np.isfinite(amplitudes).all()
            or np.any(onsets < 0) or np.any(onsets >= duration_s)
            or np.any(amplitudes < 0) or np.any(np.diff(onsets) <= 0)):
        raise ValueError("SCR onset/amplitude pairs must be finite, ordered and in range")
    t = np.arange(n, dtype=float) / sampling_rate_hz
    beat_t = np.arange(.5 * 60. / heart_rate_bpm, duration_s, 60. / heart_rate_bpm)
    ecg = np.zeros(n)
    ppg = np.zeros(n)
    for beat in beat_t:
        ecg += np.exp(-.5 * ((t - beat) / .025) ** 2)
        ppg += np.exp(-.5 * ((t - beat - .18) / .09) ** 2)
    eda_tonic = np.full(n, 1.0)
    eda_phasic = np.zeros(n)
    for onset, amplitude in zip(onsets, amplitudes):
        dt = np.maximum(t - onset, 0.0)
        response = np.exp(-dt / 3.0) - np.exp(-dt / .35)
        eda_phasic += amplitude * response * (t >= onset)
    rng = np.random.default_rng(seed)
    missing = rng.random(n) < dropout_fraction
    noise = rng.normal(0, noise_sd, (n, 3))
    truth = pd.DataFrame({
        "time_s": t, "ecg_like": ecg, "ppg_like": ppg,
        "eda_tonic": eda_tonic, "eda_phasic": eda_phasic,
        "eda_total": eda_tonic + eda_phasic,
    })
    observed = pd.DataFrame({
        "time_s": t,
        "ecg_like": ecg + noise[:, 0],
        "ppg_like": ppg + noise[:, 1],
        "eda_total": eda_tonic + eda_phasic + noise[:, 2],
    })
    observed.loc[missing, ["ecg_like", "ppg_like", "eda_total"]] = np.nan
    artifacts = pd.DataFrame({
        "time_s": t, "dropout_mask": missing,
        "ecg_noise": noise[:, 0], "ppg_noise": noise[:, 1],
        "eda_noise": noise[:, 2],
    })
    events = pd.DataFrame(
        [{"event_type": "beat", "time_s": float(v), "amplitude": 1.0} for v in beat_t]
        + [{"event_type": "scr_onset", "time_s": float(v), "amplitude": float(a)}
           for v, a in zip(onsets, amplitudes)]
    ).sort_values("time_s", kind="stable").reset_index(drop=True)
    return {
        "truth": truth, "observed_signal": observed, "artifacts": artifacts,
        "event_truth": events,
        "metadata": {
            "seed": int(seed), "sampling_rate_hz": float(sampling_rate_hz),
            "duration_s": float(duration_s), "heart_rate_bpm": float(heart_rate_bpm),
            "n_dropout_samples": int(missing.sum()),
            "validation_status": "synthetic_phenomenological_truth_only",
            "claim_boundary": (
                "Test pipeline recovery under this declared toy generator only; "
                "no device accuracy, population validity, or physiological equivalence."
            ),
        },
    }
