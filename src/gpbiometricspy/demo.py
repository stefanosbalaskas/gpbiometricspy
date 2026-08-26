"""Packaged synthetic demonstration data for :mod:`gpbiometricspy`.

The kiosk dataset is copied unchanged from the frozen ``gpbiometrics 2.0.0``
source distribution.  It is fully synthetic and is intended only for examples,
tests, documentation, and reproducible workflow demonstrations.
"""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pandas as pd


def kiosk_demo_path() -> Path:
    """Return the installed path of the synthetic kiosk demo export folder."""
    return Path(str(files("gpbiometricspy").joinpath("data", "gazepoint_biometrics_kiosk_demo_exports")))


def kiosk_demo_files() -> list[Path]:
    """Return the 36 participant ``all_gaze`` CSV files in canonical order."""
    return sorted(kiosk_demo_path().glob("synthetic_kiosk_p*_all_gaze.csv"))


def load_kiosk_demo(*, participants: list[str] | tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load the packaged synthetic kiosk demonstration data.

    Parameters
    ----------
    participants:
        Optional participant identifiers such as ``["synthetic_kiosk_p001"]``.
        When omitted, all 36 participants are loaded.

    Returns
    -------
    pandas.DataFrame
        Concatenated Gazepoint-like samples.  The complete dataset contains
        69,120 rows.
    """
    wanted = None if participants is None else {str(x) for x in participants}
    frames: list[pd.DataFrame] = []
    for path in kiosk_demo_files():
        frame = pd.read_csv(path)
        if wanted is not None:
            if "participant_id" not in frame.columns:
                continue
            frame = frame[frame["participant_id"].astype(str).isin(wanted)]
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out.attrs["source"] = "gpbiometrics 2.0.0 synthetic kiosk demo"
    out.attrs["synthetic"] = True
    return out


def kiosk_demo_overview() -> pd.DataFrame:
    """Load the one-row overview distributed with the synthetic kiosk demo."""
    return pd.read_csv(kiosk_demo_path() / "synthetic_kiosk_overview.csv")


def kiosk_demo_trial_design() -> pd.DataFrame:
    """Load the synthetic kiosk trial-design table."""
    return pd.read_csv(kiosk_demo_path() / "synthetic_kiosk_trial_design.csv")
