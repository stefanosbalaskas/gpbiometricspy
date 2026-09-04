from __future__ import annotations

from typing import Any

import pandas as pd

import gpbiometricspy as gp


def ppg_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["HRP", "PPG", "PULSE", "BVP", "pulse", "ppg", "heart_signal", "biometric_pulse"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def hr_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["HR", "HEART_RATE", "heart_rate", "bpm", "BPM"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def ibi_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["IBI", "IBI_MS", "IBI_clean_ms", "RR", "RRI", "RR_MS", "RR_INTERVAL"]
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


def time_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["TIME", "time_s", "time", "time_ms", "CNT", "MSTIMER", "TIME_TICK", "timestamp"]
    return [c for c in preferred if c in data.columns]


def _require_selected_column(data: pd.DataFrame, column: str | None, label: str) -> None:
    if column is None:
        return
    if column not in data.columns:
        raise ValueError(f"Selected {label} column was not found in the dataset.")
    if not pd.api.types.is_numeric_dtype(data[column]):
        raise TypeError(f"Selected {label} column must be numeric.")


def _rr_from_cleaned_peaks(peaks: pd.DataFrame | None) -> pd.DataFrame:
    if not isinstance(peaks, pd.DataFrame) or peaks.empty or "rr_ms" not in peaks:
        return pd.DataFrame(columns=["group", "peak_time_s", "rr_ms"])
    accepted = peaks["accepted"].fillna(False).astype(bool) if "accepted" in peaks else pd.Series(True, index=peaks.index)
    rr = peaks.loc[accepted & peaks["rr_ms"].notna(), [c for c in ["group", "peak_time_s", "rr_ms"] if c in peaks]].copy()
    if "group" not in rr:
        rr["group"] = "all"
    return rr


def run_ppg_hr_hrv_analysis(
    data: pd.DataFrame,
    *,
    ppg_col: str | None,
    hr_col: str | None,
    ibi_col: str | None,
    time_col: str | None,
    group_col: str | None = None,
    sampling_rate_hz: float = 60.0,
    bpm_min: float = 40.0,
    bpm_max: float = 180.0,
    rr_tolerance: float = 0.30,
    min_ibi_ms: float = 300.0,
    max_ibi_ms: float = 2000.0,
    max_jump_ms: float = 500.0,
    min_valid_ibi: int = 3,
    high_precision: bool = False,
    run_crosschecks: bool = False,
) -> dict[str, Any]:
    """Run the Studio PPG/HR/HRV workflow through public gpbiometricspy APIs."""
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("A non-empty data frame is required for PPG/HR/HRV analysis.")
    if not any([ppg_col, hr_col, ibi_col]):
        raise ValueError("Select at least one PPG waveform, HR, or IBI/RR column.")
    _require_selected_column(data, ppg_col, "PPG")
    _require_selected_column(data, hr_col, "HR")
    _require_selected_column(data, ibi_col, "IBI/RR")
    if time_col is not None and time_col not in data.columns:
        raise ValueError("Selected time column was not found in the dataset.")
    if group_col is not None and group_col not in data.columns:
        raise ValueError("Selected grouping column was not found in the dataset.")
    if sampling_rate_hz <= 0:
        raise ValueError("Sampling rate must be positive.")
    if bpm_min <= 0 or bpm_max <= bpm_min:
        raise ValueError("BPM limits must be positive and ordered from minimum to maximum.")
    if rr_tolerance <= 0:
        raise ValueError("RR tolerance must be positive.")
    if min_ibi_ms <= 0 or max_ibi_ms <= min_ibi_ms:
        raise ValueError("IBI limits must be positive and ordered from minimum to maximum.")
    if max_jump_ms <= 0:
        raise ValueError("Maximum IBI jump must be positive.")
    if int(min_valid_ibi) < 2:
        raise ValueError("At least two valid IBI values are required for HRV summaries.")

    groups = [group_col] if group_col else None
    result: dict[str, Any] = {}

    if ppg_col:
        waveform_quality = gp.assess_gazepoint_hrp_waveform_quality(
            data,
            hrp_col=ppg_col,
            time_col=time_col,
            group_cols=groups,
            sampling_rate=sampling_rate_hz,
        )
        detection = gp.detect_gazepoint_ppg_peaks(
            data,
            signal_col=ppg_col,
            time_col=time_col,
            group_cols=groups,
            sampling_rate_hz=sampling_rate_hz,
            bpm_min=bpm_min,
            bpm_max=bpm_max,
            high_precision=bool(high_precision),
        )
        cleaned_peaks = gp.reject_gazepoint_ppg_peaks(
            detection["peaks"],
            rr_tolerance=rr_tolerance,
            min_rr_ms=min_ibi_ms,
        )
        ppg_measures = gp.compute_gazepoint_ppg_measures(cleaned_peaks)
        rr_table = _rr_from_cleaned_peaks(cleaned_peaks)
        ppg_hrv = None
        if not rr_table.empty:
            ppg_hrv = gp.summarise_gazepoint_hrv_features(
                rr_table,
                ibi_col="rr_ms",
                group_cols=["group"],
                time_col="peak_time_s" if "peak_time_s" in rr_table else None,
                ibi_unit="milliseconds",
                min_ibi_ms=min_ibi_ms,
                max_ibi_ms=max_ibi_ms,
                min_valid_ibi=int(min_valid_ibi),
            )
        result.update(
            {
                "waveform_quality": waveform_quality,
                "detection": detection,
                "cleaned_peaks": cleaned_peaks,
                "ppg_measures": ppg_measures,
                "ppg_rr": rr_table,
                "ppg_hrv": ppg_hrv,
            }
        )

    if hr_col:
        result["hr_quality"] = gp.audit_gazepoint_hr_quality(
            data,
            value_column=hr_col,
            min_value=bpm_min,
            max_value=bpm_max,
        )
        result["hr_windows"] = gp.summarise_gazepoint_hr_windows(
            data,
            group_columns=groups,
            value_column=hr_col,
            validity_column="HRV" if "HRV" in data.columns else None,
            exclude_zero=True,
        )

    if ibi_col:
        ibi_quality = gp.audit_gazepoint_ibi_quality(
            data,
            ibi_col=ibi_col,
            group_cols=groups,
            time_col=time_col,
            unit="auto",
            min_ibi_ms=min_ibi_ms,
            max_ibi_ms=max_ibi_ms,
            max_jump_ms=max_jump_ms,
        )
        result["ibi_quality"] = ibi_quality
        result["ibi_windows"] = gp.summarise_gazepoint_ibi_windows(
            data,
            ibi_col=ibi_col,
            group_cols=groups,
            time_col=time_col,
            unit="auto",
            min_ibi_ms=min_ibi_ms,
            max_ibi_ms=max_ibi_ms,
            max_jump_ms=max_jump_ms,
            min_valid_ibi=int(min_valid_ibi),
        )
        result["ibi_hrv"] = gp.summarise_gazepoint_hrv_features(
            data,
            ibi_col=ibi_col,
            group_cols=groups,
            time_col=time_col,
            ibi_unit="auto",
            min_ibi_ms=min_ibi_ms,
            max_ibi_ms=max_ibi_ms,
            min_valid_ibi=int(min_valid_ibi),
        )

    crosschecks: dict[str, Any] = {}
    if run_crosschecks and ppg_col:
        crosschecks["heartpy"] = gp.run_gazepoint_heartpy_crosscheck(
            data,
            signal_col=ppg_col,
            time_col=time_col,
            group_cols=groups,
            sampling_rate_hz=sampling_rate_hz,
            bpm_min=bpm_min,
            bpm_max=bpm_max,
            high_precision=bool(high_precision),
        )
        crosschecks["biosppy"] = gp.run_gazepoint_biosppy_ppg(
            data,
            signal_col=ppg_col,
            time_col=time_col,
            group_cols=groups,
            sampling_rate_hz=sampling_rate_hz,
        )
    if run_crosschecks and ibi_col and isinstance(result.get("ibi_quality"), dict):
        samples = result["ibi_quality"].get("samples")
        if isinstance(samples, pd.DataFrame) and {"ibi_ms", "valid_ibi"}.issubset(samples.columns):
            nni = samples.loc[samples["valid_ibi"].fillna(False).astype(bool), "ibi_ms"].dropna().to_numpy()
            if len(nni) >= int(min_valid_ibi):
                crosschecks["pyhrv"] = gp.run_gazepoint_pyhrv_style(nni_ms=nni)
    result["crosschecks"] = crosschecks

    result["parameters"] = {
        "ppg_col": ppg_col,
        "hr_col": hr_col,
        "ibi_col": ibi_col,
        "time_col": time_col,
        "group_col": group_col,
        "sampling_rate_hz": float(sampling_rate_hz),
        "bpm_min": float(bpm_min),
        "bpm_max": float(bpm_max),
        "rr_tolerance": float(rr_tolerance),
        "min_ibi_ms": float(min_ibi_ms),
        "max_ibi_ms": float(max_ibi_ms),
        "max_jump_ms": float(max_jump_ms),
        "min_valid_ibi": int(min_valid_ibi),
        "high_precision": bool(high_precision),
        "run_crosschecks": bool(run_crosschecks),
    }
    return result


def ppg_hr_hrv_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not result:
        return {}
    tables: dict[str, pd.DataFrame] = {}
    for key in ["cleaned_peaks", "ppg_measures", "ppg_rr", "hr_quality", "hr_windows"]:
        table = result.get(key)
        if isinstance(table, pd.DataFrame):
            tables[key] = table.copy()
    for prefix in ["waveform_quality", "ppg_hrv", "ibi_quality", "ibi_windows", "ibi_hrv"]:
        obj = result.get(prefix)
        if isinstance(obj, dict):
            for key, table in obj.items():
                if isinstance(table, pd.DataFrame):
                    tables[f"{prefix}_{key}"] = table.copy()
    detection = result.get("detection")
    if isinstance(detection, dict):
        for key in ["peaks", "processed_signal", "diagnostics"]:
            table = detection.get(key)
            if isinstance(table, pd.DataFrame):
                tables[f"detection_{key}"] = table.copy()
    return tables


def crosscheck_status_table(result: dict[str, Any] | None) -> pd.DataFrame:
    crosschecks = result.get("crosschecks") if isinstance(result, dict) else None
    if not isinstance(crosschecks, dict) or not crosschecks:
        return pd.DataFrame(columns=["backend", "status", "details"])
    rows: list[dict[str, Any]] = []
    for backend, value in crosschecks.items():
        if backend == "heartpy" and isinstance(value, dict):
            available = bool(value.get("heartpy_available"))
            ext = value.get("heartpy")
            status = "available_and_executed" if available and isinstance(ext, dict) and "error" not in ext else ("available_with_error" if available else "not_installed_native_only")
            details = ext.get("error") if isinstance(ext, dict) and "error" in ext else "Native gpbiometricspy comparison retained."
        else:
            status = "completed"
            details = "Package bridge completed."
        rows.append({"backend": backend, "status": status, "details": details})
    return pd.DataFrame(rows)


def ppg_hr_hrv_reproducibility_script(result: dict[str, Any] | None) -> str:
    if not result:
        return "# Run a PPG/HR/HRV analysis in gpbiometricspy Studio to generate reproducible code.\n"
    p = result.get("parameters") or {}
    groups = [p.get("group_col")] if p.get("group_col") else None
    lines = [
        "import gpbiometricspy as gp",
        "",
        'data = gp.import_gazepoint_biometrics("your_gazepoint_export.csv")',
        "",
    ]
    if p.get("ppg_col"):
        lines.extend(
            [
                "detection = gp.detect_gazepoint_ppg_peaks(",
                f"    data, signal_col={p.get('ppg_col')!r}, time_col={p.get('time_col')!r},",
                f"    group_cols={groups!r}, sampling_rate_hz={p.get('sampling_rate_hz')!r},",
                f"    bpm_min={p.get('bpm_min')!r}, bpm_max={p.get('bpm_max')!r},",
                f"    high_precision={p.get('high_precision')!r},",
                ")",
                "cleaned_peaks = gp.reject_gazepoint_ppg_peaks(",
                f"    detection['peaks'], rr_tolerance={p.get('rr_tolerance')!r}, min_rr_ms={p.get('min_ibi_ms')!r}",
                ")",
                "ppg_measures = gp.compute_gazepoint_ppg_measures(cleaned_peaks)",
                "",
            ]
        )
    if p.get("hr_col"):
        lines.extend(
            [
                "hr_windows = gp.summarise_gazepoint_hr_windows(",
                f"    data, group_columns={groups!r}, value_column={p.get('hr_col')!r},",
                "    validity_column='HRV' if 'HRV' in data.columns else None, exclude_zero=True,",
                ")",
                "",
            ]
        )
    if p.get("ibi_col"):
        lines.extend(
            [
                "ibi_quality = gp.audit_gazepoint_ibi_quality(",
                f"    data, ibi_col={p.get('ibi_col')!r}, group_cols={groups!r}, time_col={p.get('time_col')!r},",
                f"    min_ibi_ms={p.get('min_ibi_ms')!r}, max_ibi_ms={p.get('max_ibi_ms')!r}, max_jump_ms={p.get('max_jump_ms')!r},",
                ")",
                "hrv = gp.summarise_gazepoint_hrv_features(",
                f"    data, ibi_col={p.get('ibi_col')!r}, group_cols={groups!r}, time_col={p.get('time_col')!r},",
                f"    min_ibi_ms={p.get('min_ibi_ms')!r}, max_ibi_ms={p.get('max_ibi_ms')!r}, min_valid_ibi={p.get('min_valid_ibi')!r},",
                ")",
            ]
        )
    return "\n".join(lines) + "\n"
