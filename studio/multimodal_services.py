from __future__ import annotations

from typing import Any

import pandas as pd

import gpbiometricspy as gp


EDA_CANDIDATES = [
    "studio_eda_phasic",
    "studio_eda_tonic",
    "GSR_US",
    "EDA_US",
    "GSR",
    "EDA",
    "SKIN_CONDUCTANCE",
]
CARDIAC_CANDIDATES = [
    "HR",
    "HEART_RATE",
    "heart_rate",
    "HRP",
    "PPG",
    "PULSE",
    "BVP",
    "IBI",
    "RR",
    "RRI",
]
PUPIL_CANDIDATES = [
    "LPD",
    "RPD",
    "LPMM",
    "RPMM",
    "pupil_left",
    "pupil_right",
    "left_pupil",
    "right_pupil",
    "pupil",
]
GAZE_X_CANDIDATES = ["FPOGX", "BPOGX", "GPOGX", "LPOGX", "RPOGX", "gaze_x", "x"]
GAZE_Y_CANDIDATES = ["FPOGY", "BPOGY", "GPOGY", "LPOGY", "RPOGY", "gaze_y", "y"]
AOI_CANDIDATES = ["Studio_AOI", "AOI", "aoi", "AOI_NAME", "aoi_name", "area_of_interest"]
TIME_CANDIDATES = ["time_s", "TIME", "time", "time_ms", "MSTIMER", "TIME_TICK", "timestamp", "CNT"]
GROUP_CANDIDATES = [
    "participant_id",
    "source_participant",
    "participant",
    "subject_id",
    "subject",
    "USER",
    "USERID",
    "session_id",
    "session",
]
TRIAL_CANDIDATES = [
    "trial_id",
    "trial",
    "TRIAL",
    "stimulus_id",
    "stimulus",
    "MEDIA_ID",
    "MEDIA_NAME",
    "condition",
]


def _numeric_choices(data: pd.DataFrame | None, preferred: list[str]) -> list[str]:
    if data is None:
        return []
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def multimodal_time_choices(data: pd.DataFrame | None) -> list[str]:
    return _numeric_choices(data, TIME_CANDIDATES)


def multimodal_group_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    return [c for c in GROUP_CANDIDATES if c in data.columns]


def multimodal_trial_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    return [c for c in TRIAL_CANDIDATES if c in data.columns]


def _analysis_result(analyses: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    value = analyses.get(name) if isinstance(analyses, dict) else None
    return value if isinstance(value, dict) else None


def _eda_source(
    data: pd.DataFrame,
    analyses: dict[str, Any] | None,
    prefer_processed: bool,
) -> tuple[pd.DataFrame, str]:
    result = _analysis_result(analyses, "eda_scr")
    decomposition = result.get("decomposition") if result else None
    if prefer_processed and isinstance(decomposition, pd.DataFrame) and not decomposition.empty:
        return decomposition, "EDA / SCR processed decomposition"
    return data, "Loaded dataset"


def _pupil_source(
    data: pd.DataFrame,
    analyses: dict[str, Any] | None,
    prefer_processed: bool,
) -> tuple[pd.DataFrame, str]:
    result = _analysis_result(analyses, "pupil")
    processed = result.get("processed_data") if result else None
    if prefer_processed and isinstance(processed, pd.DataFrame) and not processed.empty:
        return processed, "Pupil processed dataset"
    return data, "Loaded dataset"


def _gaze_source(
    data: pd.DataFrame,
    analyses: dict[str, Any] | None,
    prefer_processed: bool,
) -> tuple[pd.DataFrame, str]:
    result = _analysis_result(analyses, "gaze")
    processed = result.get("processed_data") if result else None
    if prefer_processed and isinstance(processed, pd.DataFrame) and not processed.empty:
        return processed, "Gaze processed dataset"
    return data, "Loaded dataset"


def multimodal_signal_choices(
    data: pd.DataFrame | None,
    analyses: dict[str, Any] | None = None,
    *,
    prefer_processed: bool = True,
) -> dict[str, list[str]]:
    if data is None:
        return {"eda": [], "cardiac": [], "pupil": [], "gaze_x": [], "gaze_y": [], "aoi": []}

    eda, _ = _eda_source(data, analyses, prefer_processed)
    pupil, _ = _pupil_source(data, analyses, prefer_processed)
    gaze, _ = _gaze_source(data, analyses, prefer_processed)
    pupil_result = _analysis_result(analyses, "pupil")
    gaze_result = _analysis_result(analyses, "gaze")

    eda_choices = _numeric_choices(eda, EDA_CANDIDATES)
    cardiac_choices = _numeric_choices(data, CARDIAC_CANDIDATES)
    pupil_choices = _numeric_choices(pupil, PUPIL_CANDIDATES)
    if pupil_result:
        derived = pupil_result.get("analysis_pupil_col")
        if derived in pupil.columns and pd.api.types.is_numeric_dtype(pupil[derived]) and derived not in pupil_choices:
            pupil_choices.insert(0, derived)

    gaze_x_choices = _numeric_choices(gaze, GAZE_X_CANDIDATES)
    gaze_y_choices = _numeric_choices(gaze, GAZE_Y_CANDIDATES)
    if gaze_result:
        derived_x = gaze_result.get("analysis_x_col")
        derived_y = gaze_result.get("analysis_y_col")
        if derived_x in gaze.columns and derived_x not in gaze_x_choices:
            gaze_x_choices.insert(0, derived_x)
        if derived_y in gaze.columns and derived_y not in gaze_y_choices:
            gaze_y_choices.insert(0, derived_y)

    aoi_choices = [c for c in AOI_CANDIDATES if c in gaze.columns]
    if gaze_result:
        derived_aoi = gaze_result.get("analysis_aoi_col")
        if derived_aoi in gaze.columns and derived_aoi not in aoi_choices:
            aoi_choices.insert(0, derived_aoi)

    return {
        "eda": eda_choices,
        "cardiac": cardiac_choices,
        "pupil": pupil_choices,
        "gaze_x": gaze_x_choices,
        "gaze_y": gaze_y_choices,
        "aoi": aoi_choices,
    }


def event_alignment_available(analyses: dict[str, Any] | None) -> bool:
    result = _analysis_result(analyses, "event_alignment")
    events = result.get("events") if result else None
    return isinstance(events, pd.DataFrame) and not events.empty


def _events_from_alignment(analyses: dict[str, Any] | None) -> pd.DataFrame:
    result = _analysis_result(analyses, "event_alignment")
    events = result.get("events") if result else None
    if not isinstance(events, pd.DataFrame) or events.empty:
        raise ValueError("Run Events & Alignment first so Multimodal Analysis has a validated event table.")
    if not {"event_id", "event_time"}.issubset(events.columns):
        raise ValueError("Events & Alignment did not retain standardized event_id/event_time columns.")
    return events.copy()


def _validate_group_event_scope(data: pd.DataFrame, events: pd.DataFrame, groups: list[str]) -> None:
    for group in groups:
        if group not in data.columns:
            raise ValueError(f"Selected grouping column was not found in the dataset: {group}.")
        n_groups = int(data[group].nunique(dropna=True))
        if n_groups > 1 and group not in events.columns:
            raise ValueError(
                f"Events do not contain `{group}`, but the dataset has {n_groups} values. "
                "Re-run Events & Alignment with the same grouping column before multimodal analysis."
            )


def _copy_selected_processed_columns(
    base: pd.DataFrame,
    source: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    out = base.copy()
    if len(source) != len(out):
        return out
    for column in columns:
        if column in source.columns and column not in out.columns:
            out[column] = source[column].to_numpy()
    return out


def _group_safe_event_windows(
    data: pd.DataFrame,
    events: pd.DataFrame,
    *,
    time_col: str,
    group_cols: list[str],
    pre_s: float,
    post_s: float,
) -> pd.DataFrame:
    if not group_cols:
        return gp.match_gazepoint_events_to_biometrics(
            data,
            events,
            pre=pre_s,
            post=post_s,
            time_col=time_col,
            event_time_col="event_time",
            event_id_col="event_id",
            return_="windows",
        )

    blocks: list[pd.DataFrame] = []
    grouped = data.groupby(group_cols, dropna=False, sort=False)
    for key, frame in grouped:
        values = key if isinstance(key, tuple) else (key,)
        event_subset = events.copy()
        for column, value in zip(group_cols, values):
            if column in events.columns:
                event_subset = event_subset.loc[event_subset[column].astype(str) == str(value)]
        if event_subset.empty:
            continue
        matched = gp.match_gazepoint_events_to_biometrics(
            frame,
            event_subset,
            pre=pre_s,
            post=post_s,
            time_col=time_col,
            event_time_col="event_time",
            event_id_col="event_id",
            return_="windows",
        )
        if not matched.empty:
            blocks.append(matched)
    return pd.concat(blocks, ignore_index=True) if blocks else pd.DataFrame()


def _classic_window_support(data: pd.DataFrame) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not ({"GSR_US", "GSR"} & set(data.columns)):
        missing.append("GSR_US/GSR")
    if "HR" not in data.columns:
        missing.append("HR")
    if "DIAL" not in data.columns:
        missing.append("DIAL")
    return not missing, missing


def run_multimodal_analysis(
    data: pd.DataFrame,
    analyses: dict[str, Any] | None,
    *,
    time_col: str,
    group_col: str | None = None,
    trial_col: str | None = None,
    eda_col: str | None = None,
    cardiac_col: str | None = None,
    pupil_col: str | None = None,
    gaze_x_col: str | None = None,
    gaze_y_col: str | None = None,
    aoi_col: str | None = None,
    pre_s: float = 1.0,
    post_s: float = 3.0,
    baseline_window_s: tuple[float, float] = (-1.0, 0.0),
    summary_window_s: tuple[float, float] = (0.0, 3.0),
    prefer_processed: bool = True,
    standardise_timeline: bool = True,
) -> dict[str, Any]:
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Multimodal analysis requires a non-empty dataset.")
    if not time_col or time_col not in data.columns:
        raise ValueError("Select a valid reference time column.")
    if pre_s < 0 or post_s <= 0:
        raise ValueError("Pre-event time must be non-negative and post-event time must be positive.")
    if baseline_window_s[0] >= baseline_window_s[1]:
        raise ValueError("Baseline window start must be earlier than baseline window end.")
    if summary_window_s[0] >= summary_window_s[1]:
        raise ValueError("Summary window start must be earlier than summary window end.")
    if baseline_window_s[0] < -pre_s or baseline_window_s[1] > post_s:
        raise ValueError("Baseline window must fall inside the event-locked extraction window.")
    if summary_window_s[0] < -pre_s or summary_window_s[1] > post_s:
        raise ValueError("Summary window must fall inside the event-locked extraction window.")

    events = _events_from_alignment(analyses)
    groups = list(dict.fromkeys(c for c in [group_col, trial_col] if c))
    _validate_group_event_scope(data, events, groups)

    eda_source, eda_source_name = _eda_source(data, analyses, prefer_processed)
    pupil_source, pupil_source_name = _pupil_source(data, analyses, prefer_processed)
    gaze_source, gaze_source_name = _gaze_source(data, analyses, prefer_processed)

    streams: dict[str, pd.DataFrame] = {}
    signal_map: dict[str, list[str]] = {}
    source_rows: list[dict[str, Any]] = []

    def add_stream(name: str, source: pd.DataFrame, source_name: str, columns: list[str]) -> None:
        chosen = [c for c in columns if c]
        if not chosen:
            return
        missing = [c for c in chosen if c not in source.columns]
        if missing:
            raise ValueError(
                f"Selected {name} signal(s) are unavailable in the resolved source: {', '.join(missing)}."
            )
        non_numeric = [c for c in chosen if not pd.api.types.is_numeric_dtype(source[c])]
        if non_numeric:
            raise TypeError(f"Selected {name} signal(s) must be numeric: {', '.join(non_numeric)}.")
        streams[name] = source
        signal_map[name] = chosen
        source_rows.append(
            {
                "modality": name,
                "source": source_name,
                "signals": ", ".join(chosen),
                "rows": len(source),
            }
        )

    add_stream("eda", eda_source, eda_source_name, [eda_col] if eda_col else [])
    add_stream("cardiac", data, "Loaded dataset", [cardiac_col] if cardiac_col else [])
    add_stream("pupil", pupil_source, pupil_source_name, [pupil_col] if pupil_col else [])
    add_stream("gaze", gaze_source, gaze_source_name, [c for c in [gaze_x_col, gaze_y_col] if c])
    if not streams:
        raise ValueError("Select at least one EDA, cardiac, pupil, or gaze signal.")

    eventlocked = gp.summarize_gazepoint_eventlocked_multimodal(
        streams,
        events,
        time_col=time_col,
        event_time_col="event_time",
        event_id_col="event_id",
        group_cols=groups or None,
        signal_cols=signal_map,
        pre_s=float(pre_s),
        post_s=float(post_s),
        baseline_window_s=tuple(float(x) for x in baseline_window_s),
        summary_window_s=tuple(float(x) for x in summary_window_s),
    )

    result: dict[str, Any] = {
        "events": events,
        "eventlocked": eventlocked,
        "stream_sources": pd.DataFrame(source_rows),
    }

    classic_ready, classic_missing = _classic_window_support(data)
    if groups and classic_ready:
        result["multimodal_windows"] = gp.summarise_gazepoint_multimodal_windows(
            data,
            group_columns=groups,
        )
        result["model_data"] = gp.prepare_gazepoint_multimodal_model_data(
            data,
            group_columns=groups,
        )
        result["grouped_window_status"] = pd.DataFrame(
            [{"status": "complete", "missing_native_channels": ""}]
        )
    elif groups:
        result["grouped_window_status"] = pd.DataFrame(
            [
                {
                    "status": "not_applicable_partial_channels",
                    "missing_native_channels": ", ".join(classic_missing),
                }
            ]
        )

    if aoi_col:
        if aoi_col not in gaze_source.columns:
            raise ValueError("Selected AOI column is unavailable in the resolved gaze source.")
        gaze_time_col = time_col if time_col in gaze_source.columns else next(
            (c for c in TIME_CANDIDATES if c in gaze_source.columns),
            None,
        )
        if gaze_time_col is None:
            raise ValueError("The resolved gaze source has no supported time column for AOI event matching.")
        gaze_windows = _group_safe_event_windows(
            gaze_source,
            events,
            time_col=gaze_time_col,
            group_cols=groups,
            pre_s=float(pre_s),
            post_s=float(post_s),
        )
        result["aoi_event_windows"] = gaze_windows
        if not gaze_windows.empty:
            aoi_groups = [c for c in [*groups, "event_id"] if c in gaze_windows.columns]
            aoi_signal_cols = [
                c for c in [eda_col, cardiac_col, pupil_col] if c and c in gaze_windows.columns
            ]
            if aoi_signal_cols:
                result["aoi_biometrics"] = gp.summarise_gazepoint_aoi_biometrics(
                    gaze_windows,
                    aoi_col=aoi_col,
                    signal_cols=aoi_signal_cols,
                    group_cols=aoi_groups or None,
                    time_col="relative_time_s" if "relative_time_s" in gaze_windows.columns else None,
                    min_rows=1,
                )
            else:
                result["aoi_biometrics_status"] = pd.DataFrame(
                    [
                        {
                            "status": "no_selected_biometric_signal_present_in_gaze_stream",
                            "aoi_col": aoi_col,
                        }
                    ]
                )

    timeline = data.copy()
    timeline = _copy_selected_processed_columns(timeline, eda_source, [c for c in [eda_col] if c])
    timeline = _copy_selected_processed_columns(timeline, pupil_source, [c for c in [pupil_col] if c])
    timeline = _copy_selected_processed_columns(
        timeline,
        gaze_source,
        [c for c in [gaze_x_col, gaze_y_col] if c],
    )
    timeline_signals = [
        c
        for c in [eda_col, cardiac_col, pupil_col, gaze_x_col, gaze_y_col]
        if c and c in timeline.columns
    ]
    result["timeline_data"] = timeline
    result["timeline_signal_cols"] = timeline_signals

    result["parameters"] = {
        "time_col": time_col,
        "group_col": group_col,
        "trial_col": trial_col,
        "eda_col": eda_col,
        "cardiac_col": cardiac_col,
        "pupil_col": pupil_col,
        "gaze_x_col": gaze_x_col,
        "gaze_y_col": gaze_y_col,
        "aoi_col": aoi_col,
        "pre_s": float(pre_s),
        "post_s": float(post_s),
        "baseline_window_s": tuple(float(x) for x in baseline_window_s),
        "summary_window_s": tuple(float(x) for x in summary_window_s),
        "prefer_processed": bool(prefer_processed),
        "standardise_timeline": bool(standardise_timeline),
        "modalities": list(streams),
        "signal_map": signal_map,
        "classic_grouped_windows_available": bool(classic_ready),
        "classic_grouped_windows_missing": classic_missing,
    }
    return result


def multimodal_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not result:
        return {}
    tables: dict[str, pd.DataFrame] = {}
    for key in [
        "events",
        "stream_sources",
        "multimodal_windows",
        "model_data",
        "grouped_window_status",
        "aoi_event_windows",
        "aoi_biometrics_status",
    ]:
        value = result.get(key)
        if isinstance(value, pd.DataFrame):
            tables[key] = value.copy()

    eventlocked = result.get("eventlocked")
    if isinstance(eventlocked, dict):
        for key in ["samples", "summary", "events"]:
            value = eventlocked.get(key)
            if isinstance(value, pd.DataFrame):
                tables[f"eventlocked_{key}"] = value.copy()

    aoi = result.get("aoi_biometrics")
    if isinstance(aoi, dict):
        for key in ["overview", "summary", "signal_summary", "aoi_summary", "data"]:
            value = aoi.get(key)
            if isinstance(value, pd.DataFrame):
                tables[f"aoi_{key}"] = value.copy()

    summary = tables.get("eventlocked_summary")
    required = {"event_id", "modality", "signal", "summary_mean"}
    if isinstance(summary, pd.DataFrame) and not summary.empty and required.issubset(summary.columns):
        matrix = summary.copy()
        matrix["modality_signal"] = matrix["modality"].astype(str) + ":" + matrix["signal"].astype(str)
        tables["response_matrix"] = matrix.pivot_table(
            index="event_id",
            columns="modality_signal",
            values="summary_mean",
            aggfunc="first",
        ).reset_index()
    return tables


def multimodal_reproducibility_script(result: dict[str, Any] | None) -> str:
    if not result:
        return "# Run Multimodal Analysis in gpbiometricspy Studio to generate reproducible code.\n"
    p = result.get("parameters") or {}
    groups = [c for c in [p.get("group_col"), p.get("trial_col")] if c]
    signal_map = p.get("signal_map") or {}
    selected_signals = sum((list(v) for v in signal_map.values()), [])
    lines = [
        "import gpbiometricspy as gp",
        "",
        'data = gp.import_gazepoint_biometrics("your_gazepoint_export.csv")',
        "",
        "# Recreate or import the standardized event table used by Studio.",
        "# It must retain grouping columns when the dataset contains multiple groups.",
        'events = gp.import_gazepoint_event_log("your_event_log.csv")',
        "",
        "eventlocked = gp.summarize_gazepoint_eventlocked_multimodal(",
        "    data,",
        "    events=events,",
        f"    time_col={p.get('time_col')!r},",
        "    event_time_col='event_time', event_id_col='event_id',",
        f"    group_cols={(groups or None)!r},",
        f"    signal_cols={selected_signals!r},",
        f"    pre_s={p.get('pre_s')!r}, post_s={p.get('post_s')!r},",
        f"    baseline_window_s={tuple(p.get('baseline_window_s', (-1.0, 0.0)))!r},",
        f"    summary_window_s={tuple(p.get('summary_window_s', (0.0, 3.0)))!r},",
        ")",
    ]
    if groups and p.get("classic_grouped_windows_available"):
        lines.extend(
            [
                "",
                "windows = gp.summarise_gazepoint_multimodal_windows(",
                f"    data, group_columns={groups!r}",
                ")",
                "model_data = gp.prepare_gazepoint_multimodal_model_data(",
                f"    data, group_columns={groups!r}",
                ")",
            ]
        )
    if p.get("aoi_col"):
        lines.extend(
            [
                "",
                "# AOI-linked biometric summaries require group-safe event-window samples carrying the AOI column.",
                "# Studio performs that matching before calling gp.summarise_gazepoint_aoi_biometrics(...).",
            ]
        )
    return "\n".join(lines) + "\n"
