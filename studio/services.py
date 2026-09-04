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
    """Run the foundation Studio QC tranche using public gpbiometricspy APIs."""
    validation = gp.validate_gazepoint_biometrics(data, require_active_signal=True)
    missingness = gp.audit_gazepoint_biometric_missingness(data)
    activity = gp.audit_gazepoint_signal_activity(data)
    return {
        "validation": validation,
        "missingness": missingness,
        "activity": activity,
    }


def time_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["TIME", "CNT", "TIME_TICK", "time", "time_ms", "timestamp", "MSTIMER"]
    return [c for c in preferred if c in data.columns]


def annotation_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["GSR_US", "GSR", "GSR_US_PHASIC", "GSR_US_TONIC", "EDA", "eda", "gsr_us"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def eda_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["GSR_US", "EDA_US", "GSR", "EDA", "GSR_OHMS", "SKIN_CONDUCTANCE"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def analysis_group_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = [
        "participant_id",
        "source_participant",
        "participant",
        "subject_id",
        "subject",
        "USER",
        "source_file",
        "session_id",
        "session",
        "trial_id",
        "trial",
        "condition",
    ]
    return [c for c in preferred if c in data.columns]


def gaze_available(data: pd.DataFrame) -> bool:
    x = {"FPOGX", "BPOGX", "LPOGX", "RPOGX", "POGX", "gaze_x", "x"}
    y = {"FPOGY", "BPOGY", "LPOGY", "RPOGY", "POGY", "gaze_y", "y"}
    return bool(x.intersection(data.columns) and y.intersection(data.columns))


def run_advanced_qc(
    data: pd.DataFrame,
    *,
    time_col: str | None,
    expected_sampling_rate_hz: float,
    gsr_min: float = 0.0,
    gsr_max: float = 100.0,
    hr_min: float = 30.0,
    hr_max: float = 220.0,
) -> dict[str, Any]:
    """Run structured time, physiology, and gaze QC through public package APIs."""
    if expected_sampling_rate_hz <= 0:
        raise ValueError("Expected sampling rate must be positive.")
    if gsr_min >= gsr_max:
        raise ValueError("GSR minimum must be lower than the GSR maximum.")
    if hr_min >= hr_max:
        raise ValueError("HR minimum must be lower than the HR maximum.")

    result: dict[str, Any] = {}

    if time_col:
        result["time_resets"] = gp.audit_gazepoint_time_resets(data, time_col=time_col)
    else:
        result["time_resets_error"] = "No supported time column was detected."

    if "GSR_US" in data.columns or "GSR" in data.columns:
        result["gsr_quality"] = gp.audit_gazepoint_gsr_quality(
            data,
            min_value=gsr_min,
            max_value=gsr_max,
        )
    if "HR" in data.columns:
        result["hr_quality"] = gp.audit_gazepoint_hr_quality(
            data,
            min_value=hr_min,
            max_value=hr_max,
        )

    if gaze_available(data) and time_col:
        kwargs: dict[str, Any] = {
            "time_col": time_col,
            "expected_sampling_rate_hz": expected_sampling_rate_hz,
        }
        if str(time_col).lower() in {"cnt", "sample", "sample_index", "index"}:
            kwargs["sampling_rate_hz"] = expected_sampling_rate_hz
        try:
            result["gaze_validation"] = gp.validate_gazepoint_gaze(data, **kwargs)
        except (TypeError, ValueError) as exc:
            result["gaze_validation_error"] = str(exc)
    else:
        result["gaze_validation_error"] = "Gaze coordinates or a supported time column were not detected."

    return result


def run_eda_scr_analysis(
    data: pd.DataFrame,
    *,
    signal_col: str,
    time_col: str | None,
    group_col: str | None = None,
    window_size: int = 31,
    threshold: float | None = None,
    min_peak_distance: int = 10,
    standardise_plot: bool = False,
) -> dict[str, Any]:
    """Run the Studio EDA/SCR workflow entirely through public gpbiometricspy APIs."""
    if signal_col not in data.columns:
        raise ValueError("Selected EDA signal column was not found in the dataset.")
    if not pd.api.types.is_numeric_dtype(data[signal_col]):
        raise TypeError("Selected EDA signal column must be numeric.")
    if time_col is not None and time_col not in data.columns:
        raise ValueError("Selected time column was not found in the dataset.")
    if group_col is not None and group_col not in data.columns:
        raise ValueError("Selected grouping column was not found in the dataset.")
    if int(window_size) < 1:
        raise ValueError("EDA decomposition window must be positive.")
    if int(min_peak_distance) < 1:
        raise ValueError("Minimum SCR peak distance must be positive.")

    groups = [group_col] if group_col else None
    quality = gp.audit_gazepoint_gsr_quality(data, value_column=signal_col)
    decomposition = gp.decompose_gazepoint_eda(
        data,
        signal_col=signal_col,
        time_col=time_col,
        group_cols=groups,
        window_size=int(window_size),
        output_prefix="studio_eda",
        overwrite=True,
    )
    events = gp.detect_gazepoint_scr_events(
        decomposition,
        phasic_col="studio_eda_phasic",
        time_col=time_col,
        group_cols=groups,
        threshold=threshold,
        min_peak_distance=int(min_peak_distance),
        window_size=int(window_size),
    )
    summary = gp.summarise_gazepoint_gsr_tonic_phasic(
        decomposition,
        gsr_col=signal_col,
        group_cols=groups,
        time_col=time_col,
        window_n=int(window_size),
        peak_threshold=threshold,
        output_prefix="studio_gsr",
    )
    parameters = {
        "signal_col": signal_col,
        "time_col": time_col,
        "group_col": group_col,
        "window_size": int(window_size),
        "threshold": threshold,
        "min_peak_distance": int(min_peak_distance),
        "standardise_plot": bool(standardise_plot),
    }
    return {
        "quality": quality,
        "decomposition": decomposition,
        "events": events,
        "summary": summary,
        "parameters": parameters,
    }


def eda_analysis_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not result:
        return {}
    decomposition = result.get("decomposition")
    events = result.get("events")
    summary = result.get("summary")
    tables: dict[str, pd.DataFrame] = {}
    quality = result.get("quality")
    if isinstance(quality, pd.DataFrame):
        tables["quality"] = quality.copy()
    if isinstance(decomposition, pd.DataFrame):
        overview = decomposition.attrs.get("overview")
        if isinstance(overview, pd.DataFrame):
            tables["decomposition_overview"] = overview.copy()
    if isinstance(events, dict):
        for key in ["overview", "events", "group_summary"]:
            table = events.get(key)
            if isinstance(table, pd.DataFrame):
                tables[f"events_{key}"] = table.copy()
    if isinstance(summary, dict):
        for key in ["overview", "summary", "group_summary", "events"]:
            table = summary.get(key)
            if isinstance(table, pd.DataFrame):
                tables[f"summary_{key}"] = table.copy()
    return tables


def eda_reproducibility_script(result: dict[str, Any] | None) -> str:
    if not result:
        return "# Run an EDA/SCR analysis in gpbiometricspy Studio to generate reproducible code.\n"
    p = result.get("parameters") or {}
    groups = [p.get("group_col")] if p.get("group_col") else None
    return (
        "import gpbiometricspy as gp\n\n"
        "data = gp.import_gazepoint_biometrics(\"your_gazepoint_export.csv\")\n\n"
        "decomposition = gp.decompose_gazepoint_eda(\n"
        f"    data, signal_col={p.get('signal_col')!r}, time_col={p.get('time_col')!r},\n"
        f"    group_cols={groups!r}, window_size={p.get('window_size', 31)!r},\n"
        "    output_prefix=\"studio_eda\", overwrite=True,\n"
        ")\n\n"
        "events = gp.detect_gazepoint_scr_events(\n"
        "    decomposition, phasic_col=\"studio_eda_phasic\",\n"
        f"    time_col={p.get('time_col')!r}, group_cols={groups!r},\n"
        f"    threshold={p.get('threshold')!r}, min_peak_distance={p.get('min_peak_distance', 10)!r},\n"
        f"    window_size={p.get('window_size', 31)!r},\n"
        ")\n\n"
        "summary = gp.summarise_gazepoint_gsr_tonic_phasic(\n"
        f"    decomposition, gsr_col={p.get('signal_col')!r}, group_cols={groups!r},\n"
        f"    time_col={p.get('time_col')!r}, window_n={p.get('window_size', 31)!r},\n"
        f"    peak_threshold={p.get('threshold')!r}, output_prefix=\"studio_gsr\",\n"
        ")\n"
    )


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


def physiology_quality_table(qc: dict[str, Any] | None) -> pd.DataFrame:
    if not qc:
        return pd.DataFrame()
    frames = [qc.get("gsr_quality"), qc.get("hr_quality")]
    frames = [x for x in frames if isinstance(x, pd.DataFrame)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def annotations_frame(annotations: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> pd.DataFrame:
    if not annotations:
        return pd.DataFrame(
            columns=["row", "annotation_type", "signal_col", "time_col", "time", "start", "end", "note"]
        )
    table = pd.DataFrame(list(annotations)).copy()
    table.insert(0, "row", range(1, len(table) + 1))
    order = ["row", "annotation_type", "signal_col", "time_col", "time", "start", "end", "note"]
    for column in order:
        if column not in table:
            table[column] = pd.NA
    return table.loc[:, order]
