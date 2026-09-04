from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

import gpbiometricspy as gp

ALLOWED_UPLOAD_SUFFIXES = {".csv", ".txt"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def load_demo_dataset() -> tuple[pd.DataFrame, str]:
    """Load the complete packaged synthetic kiosk demonstration dataset."""
    return gp.load_kiosk_demo(), "Bundled synthetic kiosk demo"


def load_uploaded_dataset(file_info: list[dict[str, Any]] | None) -> tuple[pd.DataFrame, str]:
    """Validate a Shiny upload descriptor and import it through gpbiometricspy."""
    if not file_info:
        raise ValueError("Choose a Gazepoint CSV or TXT file first.")
    if len(file_info) != 1:
        raise ValueError("Upload exactly one file for the Studio MVP.")

    info = file_info[0]
    name = str(info.get("name") or "uploaded_file")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_SUFFIXES))
        raise ValueError(f"Unsupported file type. Allowed extensions: {allowed}.")

    size = info.get("size")
    if size is not None and int(size) > MAX_UPLOAD_BYTES:
        raise ValueError("The uploaded file exceeds the 100 MB Studio MVP limit.")

    datapath = info.get("datapath")
    if not datapath:
        raise ValueError("The upload did not provide a readable temporary file path.")

    data = gp.import_gazepoint_biometrics(datapath)
    return data, name


def inspect_dataset(data: pd.DataFrame) -> dict[str, Any]:
    """Run lightweight package-native validation immediately after intake."""
    return gp.validate_gazepoint_biometrics(data, require_active_signal=False)


def run_qc(data: pd.DataFrame) -> dict[str, Any]:
    """Run the first Studio QC tranche using public gpbiometricspy APIs."""
    validation = gp.validate_gazepoint_biometrics(data, require_active_signal=True)
    missingness = gp.audit_gazepoint_biometric_missingness(data)
    activity = gp.audit_gazepoint_signal_activity(data)
    return {
        "validation": validation,
        "missingness": missingness,
        "activity": activity,
    }


def active_channels_table(validation: dict[str, Any] | None) -> pd.DataFrame:
    if not validation:
        return pd.DataFrame(columns=["signal", "present", "active", "summary_column", "valid_rows"])
    table = validation.get("active_channels")
    if not isinstance(table, pd.DataFrame):
        return pd.DataFrame()
    keep = [c for c in ["signal", "present", "active", "summary_column", "valid_rows", "nonzero_rows"] if c in table]
    return table.loc[:, keep].copy()


def issues_table(validation: dict[str, Any] | None) -> pd.DataFrame:
    if not validation:
        return pd.DataFrame(columns=["issue", "severity", "details"])
    table = validation.get("issues")
    return table.copy() if isinstance(table, pd.DataFrame) else pd.DataFrame()


def missingness_table(qc: dict[str, Any] | None) -> pd.DataFrame:
    if not qc:
        return pd.DataFrame(columns=["column", "signal", "missing_pct", "zero_pct"])
    table = qc.get("missingness")
    if not isinstance(table, pd.DataFrame):
        return pd.DataFrame()
    keep = [c for c in ["column", "signal", "role", "missing_rows", "missing_pct", "zero_rows", "zero_pct"] if c in table]
    return table.loc[:, keep].copy()
