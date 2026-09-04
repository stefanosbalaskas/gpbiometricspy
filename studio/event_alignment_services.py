from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gpbiometricspy as gp

EVENT_UPLOAD_SUFFIXES = {".csv", ".txt", ".tsv"}
MAX_EVENT_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_TARGET_UPLOAD_BYTES = 100 * 1024 * 1024


def event_time_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["time_s", "time_ms", "TIME", "TIME_TICK", "MSTIMER", "timestamp", "time", "CNT"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def ttl_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["TTL0", "TTL1", "TTL2", "TTL3", "TTL4", "TTL5", "TTL6", "TTL", "ttl_marker", "marker", "event_marker"]
    return [c for c in preferred if c in data.columns]


def ttl_validity_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["TTLV", "ttl_validity_flag", "ttlv", "TTL_VALID", "ttl_valid"]
    return [c for c in preferred if c in data.columns]


def event_group_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = [
        "participant_id",
        "source_participant",
        "participant",
        "subject_id",
        "subject",
        "USER",
        "USERID",
        "session_id",
        "session",
        "trial_id",
        "trial",
        "TRIAL",
        "MEDIA_ID",
        "MEDIA_NAME",
        "condition",
    ]
    return [c for c in preferred if c in data.columns]


def summary_signal_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    excluded = set(event_time_choices(data)) | set(ttl_column_choices(data))
    return [
        c
        for c in data.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(data[c])
    ]


def _upload_descriptor(
    file_info: list[dict[str, Any]] | None,
    *,
    label: str,
    max_bytes: int,
) -> tuple[dict[str, Any], str, str]:
    if not file_info:
        raise ValueError(f"Choose a {label} CSV/TXT/TSV file first.")
    if len(file_info) != 1:
        raise ValueError(f"Upload exactly one {label} file.")
    info = file_info[0]
    name = str(info.get("name") or f"{label.replace(' ', '_')}.csv")
    suffix = Path(name).suffix.lower()
    if suffix not in EVENT_UPLOAD_SUFFIXES:
        raise ValueError(f"{label.capitalize()} must be CSV, TXT, or TSV.")
    size = info.get("size")
    if size is not None and int(size) > max_bytes:
        raise ValueError(f"The {label} file exceeds the Studio size limit.")
    datapath = str(info.get("datapath") or "")
    if not datapath:
        raise ValueError(f"The {label} upload did not provide a readable temporary path.")
    return info, name, datapath


def load_event_log(file_info: list[dict[str, Any]] | None) -> tuple[pd.DataFrame, str]:
    _, name, datapath = _upload_descriptor(
        file_info,
        label="event log",
        max_bytes=MAX_EVENT_UPLOAD_BYTES,
    )
    events = gp.import_gazepoint_event_log(datapath)
    return events, name


def load_target_stream(file_info: list[dict[str, Any]] | None) -> tuple[pd.DataFrame, str]:
    _, name, datapath = _upload_descriptor(
        file_info,
        label="target stream",
        max_bytes=MAX_TARGET_UPLOAD_BYTES,
    )
    data = gp.import_gazepoint_biometrics(datapath)
    return data, name


def _groups(group_col: str | None) -> list[str] | None:
    return [group_col] if group_col else None


def _standard_events_from_ttl_alignment(alignment: dict[str, Any]) -> pd.DataFrame:
    events = alignment.get("events") if isinstance(alignment, dict) else None
    if not isinstance(events, pd.DataFrame) or events.empty:
        return pd.DataFrame(columns=["event_id", "event_time", "event_label"])
    if "event_time_ms" not in events.columns:
        raise ValueError("TTL alignment did not return event_time_ms.")
    out = events.copy()
    out["event_time"] = pd.to_numeric(out["event_time_ms"], errors="coerce") / 1000.0
    if "ttl_event_id" in out.columns:
        out["event_id"] = out["ttl_event_id"].astype(str)
    elif "ttl_event_sequence" in out.columns:
        out["event_id"] = out["ttl_event_sequence"].astype(str)
    else:
        out["event_id"] = [f"E{i}" for i in range(1, len(out) + 1)]
    if "event_ttl_value" in out.columns:
        out["event_label"] = out["event_ttl_value"].astype(str)
    elif "event_ttl_column" in out.columns:
        out["event_label"] = out["event_ttl_column"].astype(str)
    else:
        out["event_label"] = [f"event_{i}" for i in range(1, len(out) + 1)]
    first = ["event_id", "event_time", "event_label"]
    return out[first + [c for c in out.columns if c not in first]].reset_index(drop=True)


def _ttl_workflow(
    data: pd.DataFrame,
    *,
    ttl_col: str,
    time_col: str,
    validity_col: str | None,
    group_col: str | None,
    extraction_mode: str,
    event_edge: str,
    pre_s: float,
    post_s: float,
    collapse_nearby_ms: float,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    if ttl_col not in data.columns:
        raise ValueError(f"Selected TTL/marker column was not found: {ttl_col}.")
    raw_events = gp.extract_gazepoint_ttl_events(
        data,
        ttl_columns=[ttl_col],
        group_columns=_groups(group_col),
        validity_column=validity_col,
        require_validity=bool(validity_col),
        mode=extraction_mode,
        include_initial=False,
    )
    alignment = gp.align_gazepoint_biometrics_to_ttl(
        data,
        ttl_cols=[ttl_col],
        ttl_valid_col=validity_col,
        time_col=time_col,
        group_cols=_groups(group_col),
        event_edge=event_edge,
        pre_window_ms=float(pre_s) * 1000.0,
        post_window_ms=float(post_s) * 1000.0,
        collapse_nearby_ms=float(collapse_nearby_ms),
        require_valid_ttl=bool(validity_col),
    )
    events = _standard_events_from_ttl_alignment(alignment)
    return raw_events, alignment, events


def run_event_alignment(
    data: pd.DataFrame,
    *,
    source_mode: str,
    time_col: str,
    ttl_col: str | None = None,
    validity_col: str | None = None,
    group_col: str | None = None,
    external_events: pd.DataFrame | None = None,
    extraction_mode: str = "changes",
    event_edge: str = "rising",
    pre_s: float = 1.0,
    post_s: float = 5.0,
    collapse_nearby_ms: float = 0.0,
    summary_cols: list[str] | None = None,
    target_stream: pd.DataFrame | None = None,
    target_time_col: str | None = None,
    target_ttl_col: str | None = None,
    target_validity_col: str | None = None,
    target_group_col: str | None = None,
    stream_method: str = "linear",
) -> dict[str, Any]:
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Event alignment requires a non-empty reference dataset.")
    if source_mode not in {"ttl", "event_log"}:
        raise ValueError("Event source must be ttl or event_log.")
    if not time_col or time_col not in data.columns:
        raise ValueError("Select a valid reference time column.")
    if extraction_mode not in {"changes", "nonzero"}:
        raise ValueError("TTL extraction mode must be changes or nonzero.")
    if event_edge not in {"rising", "change", "active"}:
        raise ValueError("TTL alignment edge must be rising, change, or active.")
    if pre_s < 0 or post_s <= 0:
        raise ValueError("Pre-event time must be non-negative and post-event time must be positive.")
    if collapse_nearby_ms < 0:
        raise ValueError("Collapse-nearby interval must be non-negative.")
    if stream_method not in {"linear", "offset"}:
        raise ValueError("Stream-alignment method must be linear or offset.")
    if validity_col and validity_col not in data.columns:
        raise ValueError("Selected reference TTL validity column was not found.")
    if group_col and group_col not in data.columns:
        raise ValueError("Selected reference grouping column was not found.")

    result: dict[str, Any] = {}
    ttl_alignment = None
    raw_ttl_events = pd.DataFrame()

    if source_mode == "ttl":
        if not ttl_col:
            raise ValueError("Choose a TTL/marker column for TTL event extraction.")
        raw_ttl_events, ttl_alignment, events = _ttl_workflow(
            data,
            ttl_col=ttl_col,
            time_col=time_col,
            validity_col=validity_col,
            group_col=group_col,
            extraction_mode=extraction_mode,
            event_edge=event_edge,
            pre_s=pre_s,
            post_s=post_s,
            collapse_nearby_ms=collapse_nearby_ms,
        )
        result["ttl_events"] = raw_ttl_events
        result["ttl_alignment"] = ttl_alignment
    else:
        if not isinstance(external_events, pd.DataFrame) or external_events.empty:
            raise ValueError("Upload a non-empty external event log for event-log mode.")
        events = gp.import_gazepoint_event_log(external_events)

    if events.empty:
        raise ValueError("No usable events were available after event extraction/import.")
    result["events"] = events

    summary_cols = [c for c in (summary_cols or []) if c in data.columns]
    windows = gp.match_gazepoint_events_to_biometrics(
        data,
        events,
        pre=float(pre_s),
        post=float(post_s),
        time_col=time_col,
        event_time_col="event_time",
        event_id_col="event_id",
        summary_cols=summary_cols or None,
        return_="windows",
    )
    summary = gp.match_gazepoint_events_to_biometrics(
        data,
        events,
        pre=float(pre_s),
        post=float(post_s),
        time_col=time_col,
        event_time_col="event_time",
        event_id_col="event_id",
        summary_cols=summary_cols or None,
        return_="summary",
    )
    result["event_windows"] = windows
    result["event_summary"] = summary

    if target_stream is not None:
        if not isinstance(target_stream, pd.DataFrame) or target_stream.empty:
            raise ValueError("Target stream must be a non-empty data frame.")
        if not target_time_col or target_time_col not in target_stream.columns:
            raise ValueError("Select a valid target-stream time column.")
        if not target_ttl_col:
            raise ValueError("Choose a target-stream TTL/marker column for event-anchor alignment.")
        if target_validity_col and target_validity_col not in target_stream.columns:
            raise ValueError("Selected target TTL validity column was not found.")
        if target_group_col and target_group_col not in target_stream.columns:
            raise ValueError("Selected target grouping column was not found.")

        target_raw_events, target_ttl_alignment, target_events = _ttl_workflow(
            target_stream,
            ttl_col=target_ttl_col,
            time_col=target_time_col,
            validity_col=target_validity_col,
            group_col=target_group_col,
            extraction_mode=extraction_mode,
            event_edge=event_edge,
            pre_s=pre_s,
            post_s=post_s,
            collapse_nearby_ms=collapse_nearby_ms,
        )
        if target_events.empty:
            raise ValueError("No usable target-stream event anchors were detected.")
        result["target_ttl_events"] = target_raw_events
        result["target_ttl_alignment"] = target_ttl_alignment
        result["target_events"] = target_events

        stream_alignment = gp.align_gazepoint_streams_by_events(
            data,
            target_stream,
            events,
            target_events,
            reference_time_col=time_col,
            target_time_col=target_time_col,
            reference_event_time_col="event_time",
            target_event_time_col="event_time",
            method=stream_method,
            include_streams=True,
        )
        result["stream_alignment"] = stream_alignment

        n_pairs = min(len(events), len(target_events))
        if n_pairs >= 2:
            drift = gp.diagnose_gazepoint_sync_drift(
                events["event_time"].iloc[:n_pairs].to_numpy(float),
                target_events["event_time"].iloc[:n_pairs].to_numpy(float),
            )
            result["drift"] = drift

    result["parameters"] = {
        "source_mode": source_mode,
        "time_col": time_col,
        "ttl_col": ttl_col,
        "validity_col": validity_col,
        "group_col": group_col,
        "extraction_mode": extraction_mode,
        "event_edge": event_edge,
        "pre_s": float(pre_s),
        "post_s": float(post_s),
        "collapse_nearby_ms": float(collapse_nearby_ms),
        "summary_cols": summary_cols,
        "target_stream_used": target_stream is not None,
        "target_time_col": target_time_col,
        "target_ttl_col": target_ttl_col,
        "target_validity_col": target_validity_col,
        "target_group_col": target_group_col,
        "stream_method": stream_method,
    }
    return result


def event_alignment_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not result:
        return {}
    tables: dict[str, pd.DataFrame] = {}
    for key in [
        "events",
        "ttl_events",
        "event_windows",
        "event_summary",
        "target_events",
        "target_ttl_events",
    ]:
        value = result.get(key)
        if isinstance(value, pd.DataFrame):
            tables[key] = value
    ttl_alignment = result.get("ttl_alignment")
    if isinstance(ttl_alignment, dict):
        for name in ["overview", "events", "aligned_data"]:
            value = ttl_alignment.get(name)
            if isinstance(value, pd.DataFrame):
                tables[f"ttl_alignment_{name}"] = value
    stream_alignment = result.get("stream_alignment")
    if isinstance(stream_alignment, dict):
        for name in ["diagnostics", "alignment_table", "target_aligned"]:
            value = stream_alignment.get(name)
            if isinstance(value, pd.DataFrame):
                tables[f"stream_{name}"] = value
    drift = result.get("drift")
    if isinstance(drift, dict):
        for name in ["summary", "lag_table"]:
            value = drift.get(name)
            if isinstance(value, pd.DataFrame):
                tables[f"drift_{name}"] = value
    return tables


def event_alignment_reproducibility_script(result: dict[str, Any]) -> str:
    p = result.get("parameters", {})
    source_mode = p.get("source_mode", "ttl")
    lines = [
        "import gpbiometricspy as gp",
        "",
        "# Replace with your own Gazepoint export path.",
        "data = gp.import_gazepoint_biometrics('reference.csv')",
        "",
    ]
    if source_mode == "event_log":
        lines.extend(
            [
                "events = gp.import_gazepoint_event_log('events.csv')",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "ttl_alignment = gp.align_gazepoint_biometrics_to_ttl(",
                f"    data, ttl_cols={[p.get('ttl_col')]!r}, ttl_valid_col={p.get('validity_col')!r},",
                f"    time_col={p.get('time_col')!r}, group_cols={([p.get('group_col')] if p.get('group_col') else None)!r},",
                f"    event_edge={p.get('event_edge')!r}, pre_window_ms={p.get('pre_s', 1.0) * 1000!r},",
                f"    post_window_ms={p.get('post_s', 5.0) * 1000!r}, collapse_nearby_ms={p.get('collapse_nearby_ms', 0.0)!r},",
                f"    require_valid_ttl={bool(p.get('validity_col'))!r},",
                ")",
                "events = ttl_alignment['events'].copy()",
                "events['event_time'] = events['event_time_ms'] / 1000.0",
                "events['event_id'] = events['ttl_event_id'].astype(str)",
                "",
            ]
        )
    lines.extend(
        [
            "windows = gp.match_gazepoint_events_to_biometrics(",
            f"    data, events, pre={p.get('pre_s')!r}, post={p.get('post_s')!r}, time_col={p.get('time_col')!r},",
            "    event_time_col='event_time', event_id_col='event_id', return_='windows',",
            ")",
            "summary = gp.match_gazepoint_events_to_biometrics(",
            f"    data, events, pre={p.get('pre_s')!r}, post={p.get('post_s')!r}, time_col={p.get('time_col')!r},",
            f"    event_time_col='event_time', event_id_col='event_id', summary_cols={p.get('summary_cols')!r}, return_='summary',",
            ")",
        ]
    )
    if p.get("target_stream_used"):
        lines.extend(
            [
                "",
                "target = gp.import_gazepoint_biometrics('target.csv')",
                "target_alignment = gp.align_gazepoint_biometrics_to_ttl(",
                f"    target, ttl_cols={[p.get('target_ttl_col')]!r}, ttl_valid_col={p.get('target_validity_col')!r},",
                f"    time_col={p.get('target_time_col')!r}, group_cols={([p.get('target_group_col')] if p.get('target_group_col') else None)!r},",
                f"    event_edge={p.get('event_edge')!r}, pre_window_ms={p.get('pre_s', 1.0) * 1000!r}, post_window_ms={p.get('post_s', 5.0) * 1000!r},",
                ")",
                "target_events = target_alignment['events'].copy()",
                "target_events['event_time'] = target_events['event_time_ms'] / 1000.0",
                "target_events['event_id'] = target_events['ttl_event_id'].astype(str)",
                "stream_alignment = gp.align_gazepoint_streams_by_events(",
                f"    data, target, events, target_events, reference_time_col={p.get('time_col')!r}, target_time_col={p.get('target_time_col')!r},",
                f"    reference_event_time_col='event_time', target_event_time_col='event_time', method={p.get('stream_method')!r},",
                ")",
            ]
        )
    return "\n".join(lines) + "\n"
