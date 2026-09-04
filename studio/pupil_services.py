from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import gpbiometricspy as gp

try:
    from studio.services import analysis_group_column_choices, time_column_choices
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import analysis_group_column_choices, time_column_choices


def pupil_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = [
        "LPD", "RPD", "LPMM", "RPMM", "Pupil", "PUPIL", "pupil",
        "pupil_size", "pupil_diameter", "left_pupil", "right_pupil",
        "pupil_left", "pupil_right",
    ]
    found = [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]
    for column in data.columns:
        text = str(column)
        lower = text.lower()
        pupil_like = "pupil" in lower or "diameter" in lower or text.upper() in {"LPD", "RPD", "LPMM", "RPMM"}
        derived = any(token in lower for token in ["valid", "flag", "blink", "clean", "interp", "smooth", "baseline", "imputed", "spike", "was_"])
        if pupil_like and not derived and pd.api.types.is_numeric_dtype(data[column]) and column not in found:
            found.append(column)
    return found


def pupil_validity_choices(data: pd.DataFrame | None, pupil_col: str | None = None) -> list[str]:
    if data is None:
        return []
    preferred: list[str] = []
    if pupil_col:
        upper = pupil_col.upper()
        if upper in {"LPD", "LPMM"}:
            preferred.extend(["LPV", "LVALID", "left_pupil_valid", "left_validity"])
        elif upper in {"RPD", "RPMM"}:
            preferred.extend(["RPV", "RVALID", "right_pupil_valid", "right_validity"])
        preferred.extend([f"{pupil_col}_valid", f"{pupil_col}_validity"])
    preferred.extend(["LPV", "RPV", "validity_left", "validity_right"])
    return [c for c in dict.fromkeys(preferred) if c in data.columns]


def trial_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["trial_id", "trial", "TRIAL", "stimulus_id", "stimulus", "MEDIA_ID", "MEDIA_NAME", "screen"]
    return [c for c in preferred if c in data.columns]


def onset_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = [
        "stimulus_onset", "stimulus_onset_s", "trial_onset", "trial_onset_s",
        "event_time", "event_onset", "onset", "TTL_EVENT_TIME", "TTL_TIME",
    ]
    found = [c for c in preferred if c in data.columns]
    for column in data.columns:
        lower = str(column).lower()
        if ("onset" in lower or "event_time" in lower) and column not in found:
            found.append(column)
    return found


def marker_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["TTL", "TTL0", "TTL1", "TTL2", "TTL3", "USER", "USER_DATA", "marker", "event_marker"]
    found = [c for c in preferred if c in data.columns]
    for column in data.columns:
        if str(column).upper().startswith("TTL") and column not in found:
            found.append(column)
    return found


def _events_from_onset_column(data: pd.DataFrame, onset_col: str, trial_col: str | None) -> pd.DataFrame:
    if onset_col not in data.columns:
        raise ValueError("Selected event-onset column was not found in the dataset.")
    work = pd.DataFrame({"event_time": pd.to_numeric(data[onset_col], errors="coerce")})
    if trial_col:
        if trial_col not in data.columns:
            raise ValueError("Selected trial column was not found in the dataset.")
        work["event_id"] = data[trial_col]
        work = work.loc[work.event_time.notna()].drop_duplicates(["event_id", "event_time"])
    else:
        work = work.loc[work.event_time.notna()].drop_duplicates(["event_time"])
        work["event_id"] = np.arange(1, len(work) + 1)
    work["event_label"] = work["event_id"].astype(str)
    return work.reset_index(drop=True)


def _events_from_marker(data: pd.DataFrame, marker_col: str, time_col: str, group_col: str | None) -> pd.DataFrame:
    groups = [group_col] if group_col else None
    extracted = gp.extract_gazepoint_ttl_events(
        data,
        ttl_columns=[marker_col],
        group_columns=groups,
        require_validity=False,
        mode="changes",
        include_initial=False,
    )
    if isinstance(extracted, pd.DataFrame) and not extracted.empty:
        event_time_col = next(
            (c for c in ["event_time", "time", "TIME", "timestamp", "onset_time", time_col] if c in extracted.columns),
            None,
        )
        if event_time_col is not None:
            out = pd.DataFrame({"event_time": pd.to_numeric(extracted[event_time_col], errors="coerce")})
            label_col = next((c for c in ["value", "event_value", "ttl_value", marker_col, "event"] if c in extracted.columns), None)
            out["event_label"] = extracted[label_col].astype(str).to_numpy() if label_col else "TTL event"
            out["event_id"] = np.arange(1, len(out) + 1)
            return out.loc[out.event_time.notna(), ["event_id", "event_time", "event_label"]].reset_index(drop=True)

    # Fallback only resolves event rows for the UI when the package-native event table does not retain time.
    marker = data[marker_col]
    changed = marker.ne(marker.shift()).fillna(False)
    numeric = pd.to_numeric(marker, errors="coerce")
    active = numeric.ne(0) & numeric.notna() if numeric.notna().any() else marker.notna()
    rows = changed & active
    out = pd.DataFrame(
        {
            "event_time": pd.to_numeric(data.loc[rows, time_col], errors="coerce"),
            "event_label": marker.loc[rows].astype(str),
        }
    ).dropna(subset=["event_time"])
    out.insert(0, "event_id", np.arange(1, len(out) + 1))
    return out.reset_index(drop=True)


def _event_baseline_seconds(window: tuple[float, float], time_values: pd.Series) -> tuple[float, float]:
    values = pd.to_numeric(time_values, errors="coerce").dropna().drop_duplicates().sort_values().to_numpy(float)
    diffs = np.diff(values)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) and np.median(diffs) > 5:
        return (float(window[0]) / 1000.0, float(window[1]) / 1000.0)
    return (float(window[0]), float(window[1]))


def run_pupil_analysis(
    data: pd.DataFrame,
    *,
    pupil_col: str,
    time_col: str,
    validity_col: str | None = None,
    group_col: str | None = None,
    trial_col: str | None = None,
    min_blink_samples: int = 2,
    interpolate: bool = False,
    interpolation_max_gap_s: float | None = 0.25,
    interpolation_method: str = "linear",
    smooth: bool = False,
    smooth_window: int = 5,
    baseline_correct: bool = False,
    stimulus_onset_col: str | None = None,
    baseline_window: tuple[float, float] = (-0.5, -0.1),
    baseline_function: str = "median",
    correction: str = "subtract",
    summarize_events: bool = False,
    event_onset_col: str | None = None,
    marker_col: str | None = None,
    pre_s: float = 1.0,
    post_s: float = 3.0,
    response_window: tuple[float, float] = (0.0, 3.0),
) -> dict[str, Any]:
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Pupil analysis requires a non-empty data frame.")
    for column, label in [(pupil_col, "pupil"), (time_col, "time")]:
        if not column or column not in data.columns:
            raise ValueError(f"Selected {label} column was not found in the dataset.")
    if not pd.api.types.is_numeric_dtype(data[pupil_col]):
        raise TypeError("Selected pupil column must be numeric.")
    for column, label in [(validity_col, "validity"), (group_col, "group"), (trial_col, "trial")]:
        if column is not None and column not in data.columns:
            raise ValueError(f"Selected {label} column was not found in the dataset.")
    if int(min_blink_samples) < 1:
        raise ValueError("Minimum blink samples must be at least one.")
    if interpolation_method not in {"linear", "constant"}:
        raise ValueError("Interpolation method must be 'linear' or 'constant'.")
    if interpolation_max_gap_s is not None and interpolation_max_gap_s <= 0:
        raise ValueError("Maximum interpolation gap must be positive when supplied.")
    if int(smooth_window) < 1 or int(smooth_window) % 2 == 0:
        raise ValueError("Smoothing window must be a positive odd integer.")
    if baseline_window[0] >= baseline_window[1]:
        raise ValueError("Baseline window start must be earlier than its end.")
    if response_window[0] >= response_window[1]:
        raise ValueError("Response window start must be earlier than its end.")
    if pre_s < 0 or post_s <= 0:
        raise ValueError("Event pre-window must be non-negative and post-window must be positive.")

    groups = [group_col] if group_col else None
    validity = [validity_col] if validity_col else None
    result: dict[str, Any] = {}

    result["blink_intervals"] = gp.detect_gazepoint_pupil_blinks(
        data,
        pupil_cols=[pupil_col],
        time_col=time_col,
        group_cols=groups,
        validity_cols=validity,
        combine="all",
        min_blink_samples=int(min_blink_samples),
        return_="intervals",
    )
    blink_flags = gp.detect_gazepoint_pupil_blinks(
        data,
        pupil_cols=[pupil_col],
        time_col=time_col,
        group_cols=groups,
        validity_cols=validity,
        combine="all",
        min_blink_samples=int(min_blink_samples),
        return_="flags",
    )
    result["blink_flags"] = np.asarray(blink_flags, dtype=bool)
    result["blink_audit"] = gp.detect_gazepoint_blinks(
        data,
        pupil_cols=[pupil_col],
        id_cols=groups,
        min_pupil=0,
        extend_samples=0,
        mask=True,
    )

    working = data.copy()
    current_col = pupil_col
    temporary_blink_col = "__studio_pupil_blink"
    working[temporary_blink_col] = result["blink_flags"]

    if interpolate:
        working = gp.interpolate_gazepoint_pupil_blinks(
            working,
            pupil_cols=[current_col],
            time_col=time_col,
            blink_col=temporary_blink_col,
            max_gap_s=interpolation_max_gap_s,
            method=interpolation_method,
            suffix="_studio_interp",
        )
        current_col = f"{current_col}_studio_interp"
        result["interpolated_data"] = working.copy()

    if smooth:
        smoothed = gp.smooth_gazepoint_pupil(
            working,
            pupil_cols=[current_col],
            id_cols=groups,
            window=int(smooth_window),
            suffix="_studio_smooth",
            min_nonmissing=1,
        )
        result["smoothing"] = smoothed
        working = smoothed["data"]
        current_col = f"{current_col}_studio_smooth"

    if baseline_correct:
        if not stimulus_onset_col:
            raise ValueError("Choose a stimulus-onset column before baseline correction.")
        if stimulus_onset_col not in working.columns:
            raise ValueError("Selected stimulus-onset column was not found in the dataset.")
        trial_cols = [c for c in [group_col, trial_col] if c]
        working = gp.baseline_correct_gazepoint_pupil(
            working,
            pupil_col=current_col,
            time_col=time_col,
            stimulus_onset_col=stimulus_onset_col,
            trial_cols=trial_cols or None,
            baseline_window=baseline_window,
            baseline_function=baseline_function,
            correction=correction,
            suffix="_studio_baseline",
            min_baseline_rows=2,
            overwrite=True,
        )
        current_col = f"{current_col}_studio_baseline"
        result["baseline_data"] = working.copy()

    if summarize_events:
        if event_onset_col:
            events = _events_from_onset_column(data, event_onset_col, trial_col)
        elif marker_col:
            events = _events_from_marker(data, marker_col, time_col, group_col)
        else:
            raise ValueError("Choose an event-onset or TTL/marker column before event-locked summarization.")
        if events.empty:
            raise ValueError("No usable pupil events were detected from the selected event source.")
        result["events"] = events
        result["event_summary"] = gp.summarize_gazepoint_pupil_events(
            working,
            events,
            pre=float(pre_s),
            post=float(post_s),
            time_col=time_col,
            pupil_col=current_col,
            event_time_col="event_time",
            event_id_col="event_id",
            baseline_window=_event_baseline_seconds(baseline_window, data[time_col]),
            response_window=response_window,
        )

    if temporary_blink_col in working.columns:
        working = working.drop(columns=[temporary_blink_col])
    result["processed_data"] = working
    result["analysis_pupil_col"] = current_col
    result["parameters"] = {
        "pupil_col": pupil_col,
        "time_col": time_col,
        "validity_col": validity_col,
        "group_col": group_col,
        "trial_col": trial_col,
        "min_blink_samples": int(min_blink_samples),
        "interpolate": bool(interpolate),
        "interpolation_max_gap_s": interpolation_max_gap_s,
        "interpolation_method": interpolation_method,
        "smooth": bool(smooth),
        "smooth_window": int(smooth_window),
        "baseline_correct": bool(baseline_correct),
        "stimulus_onset_col": stimulus_onset_col,
        "baseline_window": tuple(float(x) for x in baseline_window),
        "baseline_function": baseline_function,
        "correction": correction,
        "summarize_events": bool(summarize_events),
        "event_onset_col": event_onset_col,
        "marker_col": marker_col,
        "pre_s": float(pre_s),
        "post_s": float(post_s),
        "response_window": tuple(float(x) for x in response_window),
        "analysis_pupil_col": current_col,
    }
    return result


def pupil_analysis_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not result:
        return {}
    tables: dict[str, pd.DataFrame] = {}
    intervals = result.get("blink_intervals")
    if isinstance(intervals, pd.DataFrame):
        tables["blink_intervals"] = intervals.copy()
    audit = result.get("blink_audit")
    if isinstance(audit, dict) and isinstance(audit.get("summary"), pd.DataFrame):
        tables["blink_summary"] = audit["summary"].copy()
    smoothing = result.get("smoothing")
    if isinstance(smoothing, dict) and isinstance(smoothing.get("summary"), pd.DataFrame):
        tables["smoothing_summary"] = smoothing["summary"].copy()
    for key in ["events", "event_summary"]:
        table = result.get(key)
        if isinstance(table, pd.DataFrame):
            tables[key] = table.copy()
    processed = result.get("processed_data")
    if isinstance(processed, pd.DataFrame):
        flags = [c for c in processed.columns if c.endswith("_was_interpolated") or c.endswith("_blink_flag")]
        if flags:
            tables["repair_flags"] = processed[flags].copy()
    return tables


def pupil_reproducibility_script(result: dict[str, Any] | None) -> str:
    if not result:
        return "# Run a Pupil Analysis workflow in gpbiometricspy Studio to generate reproducible code.\n"
    p = result.get("parameters") or {}
    groups = [p.get("group_col")] if p.get("group_col") else None
    validity = [p.get("validity_col")] if p.get("validity_col") else None
    current = p.get("pupil_col")
    lines = [
        "import gpbiometricspy as gp",
        "",
        'data = gp.import_gazepoint_biometrics("your_gazepoint_export.csv")',
        "",
        "blinks = gp.detect_gazepoint_pupil_blinks(",
        f"    data, pupil_cols={[current]!r}, time_col={p.get('time_col')!r},",
        f"    group_cols={groups!r}, validity_cols={validity!r}, min_blink_samples={p.get('min_blink_samples', 2)!r},",
        '    combine="all", return_="intervals",',
        ")",
        "blink_flags = gp.detect_gazepoint_pupil_blinks(",
        f"    data, pupil_cols={[current]!r}, time_col={p.get('time_col')!r}, group_cols={groups!r},",
        f"    validity_cols={validity!r}, min_blink_samples={p.get('min_blink_samples', 2)!r}, return_=\"flags\",",
        ")",
        "working = data.copy()",
        'working["__studio_pupil_blink"] = blink_flags',
    ]
    if p.get("interpolate"):
        lines.extend([
            "working = gp.interpolate_gazepoint_pupil_blinks(",
            f"    working, pupil_cols={[current]!r}, time_col={p.get('time_col')!r}, blink_col=\"__studio_pupil_blink\",",
            f"    max_gap_s={p.get('interpolation_max_gap_s')!r}, method={p.get('interpolation_method', 'linear')!r}, suffix=\"_studio_interp\",",
            ")",
        ])
        current = f"{current}_studio_interp"
    if p.get("smooth"):
        lines.extend([
            "smooth_result = gp.smooth_gazepoint_pupil(",
            f"    working, pupil_cols={[current]!r}, id_cols={groups!r}, window={p.get('smooth_window', 5)!r}, suffix=\"_studio_smooth\", min_nonmissing=1,",
            ")",
            'working = smooth_result["data"]',
        ])
        current = f"{current}_studio_smooth"
    if p.get("baseline_correct"):
        trial_cols = [c for c in [p.get("group_col"), p.get("trial_col")] if c]
        lines.extend([
            "working = gp.baseline_correct_gazepoint_pupil(",
            f"    working, pupil_col={current!r}, time_col={p.get('time_col')!r}, stimulus_onset_col={p.get('stimulus_onset_col')!r},",
            f"    trial_cols={trial_cols or None!r}, baseline_window={tuple(p.get('baseline_window', (-0.5, -0.1)))!r},",
            f"    baseline_function={p.get('baseline_function', 'median')!r}, correction={p.get('correction', 'subtract')!r},",
            '    suffix="_studio_baseline", min_baseline_rows=2, overwrite=True,',
            ")",
        ])
        current = f"{current}_studio_baseline"
    if p.get("summarize_events"):
        lines.extend([
            "# Recreate `events` from the onset/TTL source used in Studio, then:",
            "event_summary = gp.summarize_gazepoint_pupil_events(",
            f"    working, events, pre={p.get('pre_s', 1.0)!r}, post={p.get('post_s', 3.0)!r},",
            f"    time_col={p.get('time_col')!r}, pupil_col={current!r}, response_window={tuple(p.get('response_window', (0.0, 3.0)))!r},",
            ")",
        ])
    return "\n".join(lines) + "\n"


__all__ = [
    "analysis_group_column_choices",
    "marker_column_choices",
    "onset_column_choices",
    "pupil_analysis_tables",
    "pupil_reproducibility_script",
    "pupil_signal_choices",
    "pupil_validity_choices",
    "run_pupil_analysis",
    "time_column_choices",
    "trial_column_choices",
]
