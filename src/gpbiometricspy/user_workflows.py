from __future__ import annotations

import platform
import re
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from .deterministic_extensions import (
    create_gazepoint_biometrics_checklist,
    create_gazepoint_biometrics_methods_text,
    standardise_gazepoint_plot_contract,
)
from .frontdoor import (
    audit_gazepoint_biometric_missingness,
    detect_active_biometric_channels,
    import_gazepoint_biometric_folder,
    validate_gazepoint_biometrics,
)
from .intake_alignment import extract_gazepoint_ttl_events
from .qc_dropouts import audit_gazepoint_signal_activity, audit_gazepoint_time_resets
from .qc_windows_standardization import (
    audit_gazepoint_engagement_dial,
    audit_gazepoint_gsr_quality,
    audit_gazepoint_hr_quality,
    summarise_gazepoint_engagement_windows,
    summarise_gazepoint_multimodal_windows,
)
from .remaining_core import extract_gazepoint_hrv_features


def _df(x, name="data"):
    if not isinstance(x, pd.DataFrame):
        raise TypeError(f"`{name}` must be a data frame.")
    return x


def _as_list(x):
    if x is None:
        return []
    return [x] if isinstance(x, str) else list(x)


def _plot_contract(fig, data, plot_type, settings=None, notes=None, **extra):
    settings = {"plot_type": plot_type, **(settings or {})}
    standardise_gazepoint_plot_contract(
        fig,
        data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(),
        settings,
        notes or ["Descriptive plot; interpretation should follow the study design."],
        plot_type,
    )
    for key, value in extra.items():
        setattr(fig, f"_gazepoint_{key}", value)
    return fig


def _signals(data, requested=None):
    if requested is not None:
        cols = _as_list(requested)
        missing = [c for c in cols if c not in data]
        if missing:
            raise ValueError("Signal columns were not found in `data`: " + ", ".join(missing))
        non_numeric = [c for c in cols if not pd.api.types.is_numeric_dtype(data[c])]
        if non_numeric:
            raise TypeError("Biometric signal columns must be numeric: " + ", ".join(non_numeric))
        return cols
    candidates = [
        "GSR_US", "GSR", "EDA", "HR", "HRP", "PPG", "IBI", "DIAL",
        "GSR_US_TONIC", "GSR_US_PHASIC", "eda_tonic", "eda_phasic",
    ]
    return [c for c in candidates if c in data and pd.api.types.is_numeric_dtype(data[c])]


def _downsample_indices(n, max_points):
    if not isinstance(max_points, (int, float, np.number)) or not np.isfinite(max_points) or max_points < 1:
        raise ValueError("`max_points` must be a positive finite number.")
    max_points = int(max_points)
    if n <= max_points:
        return np.arange(n, dtype=int)
    return np.unique(np.rint(np.linspace(0, n - 1, max_points)).astype(int))


def plot_gazepoint_biometric_signals(
    data, signal_cols=None, time_col=None, group_col=None, max_points=5000,
    standardize=False, type="line", main=None, xlab=None, ylab=None,
    legend=True, plot=True, **kwargs,
):
    data = _df(data)
    if not isinstance(standardize, (bool, np.bool_)):
        raise TypeError("`standardize` must be TRUE or FALSE.")
    if not isinstance(plot, (bool, np.bool_)):
        raise TypeError("`plot` must be TRUE or FALSE.")
    if type not in {"line", "points", "both"}:
        raise ValueError("`type` must be 'line', 'points', or 'both'.")
    if time_col is not None and time_col not in data:
        raise ValueError("`time_col` was not found in `data`.")
    if group_col is not None and group_col not in data:
        raise ValueError("`group_col` was not found in `data`.")
    sig = _signals(data, signal_cols)
    if not sig:
        raise ValueError("No biometric signal columns were available to plot.")
    idx = _downsample_indices(len(data), max_points)
    d = data.iloc[idx].copy()
    if standardize:
        for c in sig:
            x = pd.to_numeric(d[c], errors="coerce")
            sd = x.std(ddof=1)
            d[c] = (x - x.mean()) / sd if np.isfinite(sd) and sd > 0 else np.nan
    x = pd.to_numeric(d[time_col], errors="coerce") if time_col else np.arange(len(d))
    fig, ax = plt.subplots()
    for c in sig:
        y = pd.to_numeric(d[c], errors="coerce")
        if type in {"line", "both"}:
            ax.plot(x, y, label=c)
        if type in {"points", "both"}:
            ax.scatter(x, y, s=10, label=c if type == "points" else None)
    if legend:
        ax.legend()
    ax.set_title(main or "Gazepoint biometric signals")
    ax.set_xlabel(xlab or (time_col or "sample"))
    ax.set_ylabel(ylab or ("standardized signal" if standardize else "signal"))
    summary = pd.DataFrame([
        {
            "signal": c,
            "n_finite": int(pd.to_numeric(d[c], errors="coerce").notna().sum()),
            "mean": float(pd.to_numeric(d[c], errors="coerce").mean()),
            "sd": float(pd.to_numeric(d[c], errors="coerce").std(ddof=1)),
        }
        for c in sig
    ])
    overview = pd.DataFrame([{
        "n_rows": len(data), "plotted_rows": len(d), "signal_column_count": len(sig),
        "group_count": int(data[group_col].nunique(dropna=False)) if group_col else 1,
        "status": "signals_prepared",
    }])
    if not plot:
        plt.close(fig)
    return _plot_contract(
        fig, d, "biometric_signals",
        {"signal_cols": sig, "time_col": time_col, "group_col": group_col,
         "standardize": bool(standardize), "type": type, "max_points": int(max_points)},
        overview=overview, signal_summary=summary,
    )


def _as_quality_flag(series, name):
    s = pd.Series(series)
    if pd.api.types.is_bool_dtype(s.dtype):
        return s.fillna(False).to_numpy(bool)
    x = pd.to_numeric(s, errors="coerce")
    # Gazepoint validity columns: 1 means valid, so a flag is value <= 0.
    upper = str(name).upper()
    if upper.endswith("V") or "VALID" in upper:
        return (x.isna() | x.le(0)).to_numpy(bool)
    return (x.fillna(0) != 0).to_numpy(bool)


def plot_gazepoint_biometric_quality(
    data, quality_cols=None, signal_cols=None, time_col=None, group_col=None,
    dropout_prefix="biometric_dropout", max_points=5000, main=None, plot=True, **kwargs,
):
    data = _df(data)
    if not isinstance(plot, (bool, np.bool_)):
        raise TypeError("`plot` must be TRUE or FALSE.")
    if not isinstance(dropout_prefix, str) or not dropout_prefix:
        raise ValueError("`dropout_prefix` must be a non-empty string.")
    if group_col is not None and group_col not in data:
        raise ValueError("`group_col` was not found in `data`.")
    if time_col is not None and time_col not in data:
        raise ValueError("`time_col` was not found in `data`.")
    idx = _downsample_indices(len(data), max_points)
    d = data.iloc[idx].copy()
    derived = quality_cols is None
    if quality_cols is not None:
        qcols = _as_list(quality_cols)
        missing = [c for c in qcols if c not in data]
        if missing:
            raise ValueError("Quality columns were not found in `data`: " + ", ".join(missing))
        plot_data = d[qcols].copy()
        source = "quality_column"
    else:
        qcols = [c for c in data if dropout_prefix in str(c)]
        if not qcols:
            sig = _signals(data, signal_cols)
            if not sig:
                raise ValueError("No quality columns or signal columns were available.")
            plot_data = pd.DataFrame(index=d.index)
            qcols = []
            for c in sig:
                name = f"{c}_missing"
                plot_data[name] = pd.to_numeric(d[c], errors="coerce").isna()
                qcols.append(name)
            source = "derived_signal_missingness"
        else:
            plot_data = d[qcols].copy()
            source = "quality_column"
    rows = []
    for c in qcols:
        flag = _as_quality_flag(plot_data[c], c)
        rows.append({"column": c, "n_rows": len(flag), "n_flagged": int(flag.sum()),
                     "flagged_pct": 100 * float(flag.mean()) if len(flag) else np.nan,
                     "source": source})
    quality_summary = pd.DataFrame(rows)
    group_summary = pd.DataFrame()
    if group_col:
        grows = []
        for g, pos in data.groupby(group_col, sort=False, dropna=False).groups.items():
            sub = data.loc[pos]
            flags = []
            if quality_cols is not None:
                for c in _as_list(quality_cols):
                    flags.extend(_as_quality_flag(sub[c], c).tolist())
            else:
                sig = _signals(sub, signal_cols)
                for c in sig:
                    flags.extend(pd.to_numeric(sub[c], errors="coerce").isna().tolist())
            grows.append({"group": g, "n_rows": len(sub), "n_flagged": int(np.sum(flags)),
                          "flagged_pct": 100 * float(np.mean(flags)) if flags else 0.0})
        group_summary = pd.DataFrame(grows)
    overview = pd.DataFrame([{
        "n_rows": len(data), "quality_column_count": len(qcols),
        "group_count": int(data[group_col].nunique(dropna=False)) if group_col else 1,
        "derived_from_signals": bool(source == "derived_signal_missingness"),
        "status": "quality_flags_present" if len(qcols) else "no_quality_flags",
    }])
    fig, ax = plt.subplots()
    if len(quality_summary):
        ax.bar(quality_summary["column"], quality_summary["flagged_pct"])
        ax.tick_params(axis="x", rotation=45)
    ax.set_ylabel("Flagged (%)")
    ax.set_title(main or "Gazepoint biometric quality")
    if not plot:
        plt.close(fig)
    return _plot_contract(fig, plot_data.reset_index(drop=True), "biometric_quality",
                          {"quality_cols": qcols, "group_col": group_col, "max_points": int(max_points)},
                          overview=overview, quality_summary=quality_summary, group_summary=group_summary)


def _group_label_from_audit(data):
    if "group_id" in data:
        out = data["group_id"].astype("string").fillna("all").replace("", "all")
        return out.astype(str)
    candidates = [c for c in ["source_file", "source_participant", "participant", "subject", "subject_id", "USER", "USER_FILE", "MEDIA_ID", "MEDIA_NAME", "stimulus", "stimulus_id", "trial", "trial_id", "trial_global", "reset_segment_index"] if c in data]
    if not candidates:
        return pd.Series(["all"] * len(data), index=data.index)
    return data[candidates].astype("string").fillna("<NA>").agg("||".join, axis=1)


def plot_gazepoint_signal_activity(data, signal_cols=None, group_cols=None, metric="active_signal", max_groups=30, title=None):
    if metric not in {"active_signal", "nonzero_prop", "missing_prop", "n_unique_finite"}:
        raise ValueError("Unsupported signal-activity metric.")
    if not isinstance(max_groups, (int, float, np.number)) or not np.isfinite(max_groups) or max_groups < 1:
        raise ValueError("`max_groups` must be a single positive number.")
    if isinstance(data, dict) and isinstance(data.get("signal_by_group"), pd.DataFrame):
        audit = data
    else:
        audit = audit_gazepoint_signal_activity(_df(data), signal_cols=signal_cols, group_cols=group_cols)
    plot_data = audit["signal_by_group"].copy()
    if plot_data.empty:
        raise ValueError("No signal-activity rows were available for plotting.")
    plot_data["active_signal"] = plot_data.get("status", pd.Series(index=plot_data.index, dtype=object)).eq("active")
    plot_data["n_unique_finite"] = plot_data.get("unique_finite", np.nan)
    plot_data[".plot_group"] = _group_label_from_audit(plot_data)
    values = plot_data[metric]
    if pd.api.types.is_bool_dtype(values.dtype):
        values = values.fillna(False).astype(float)
    else:
        values = pd.to_numeric(values, errors="coerce")
    plot_data[".plot_value"] = values
    plot_data[".plot_metric"] = metric
    selected = list(dict.fromkeys(plot_data[".plot_group"].tolist()))[: int(max_groups)]
    plot_data = plot_data[plot_data[".plot_group"].isin(selected)].reset_index(drop=True)
    fig, ax = plt.subplots()
    if len(plot_data):
        labels = plot_data[".plot_group"] + "||" + plot_data["signal"].astype(str)
        ax.bar(np.arange(len(plot_data)), plot_data[".plot_value"].fillna(0))
        ax.set_xticks(np.arange(len(plot_data)), labels, rotation=45, ha="right")
    ax.set_title(title or "Gazepoint biometric signal activity")
    ax.set_xlabel("Signal / group")
    ax.set_ylabel(metric)
    notes = ["Signal activity plots summarize availability and basic variation.", "They do not infer emotion, valence, cognition, trust, preference, or physiological diagnosis."]
    return _plot_contract(fig, plot_data, "signal_activity", {"metric": metric, "signal_cols": signal_cols, "group_cols": _as_list(group_cols), "max_groups": int(max_groups)}, notes)


def plot_gazepoint_time_resets(data, time_col=None, group_cols=None, max_groups=30, title=None):
    if not isinstance(max_groups, (int, float, np.number)) or not np.isfinite(max_groups) or max_groups < 1:
        raise ValueError("`max_groups` must be a single positive number.")
    if isinstance(data, dict) and isinstance(data.get("row_flags"), pd.DataFrame):
        audit = data
    else:
        audit = audit_gazepoint_time_resets(_df(data), time_col=time_col, group_cols=group_cols)
    plot_data = audit["row_flags"].copy()
    if plot_data.empty:
        raise ValueError("No time-reset rows were available for plotting.")
    if "time_value" not in plot_data:
        raise ValueError("The time-reset audit must contain a `time_value` column.")
    plot_data[".plot_index"] = plot_data["group_row_index"] if "group_row_index" in plot_data else np.arange(1, len(plot_data) + 1)
    plot_data[".plot_group"] = _group_label_from_audit(plot_data)
    issue_cols = [c for c in ["flag_nonfinite_time", "flag_negative_step", "flag_duplicate_time", "flag_nonmonotonic", "flag_short_segment"] if c in plot_data]
    plot_data[".any_time_issue"] = plot_data[issue_cols].fillna(False).astype(bool).any(axis=1) if issue_cols else False
    selected = list(dict.fromkeys(plot_data[".plot_group"].tolist()))[: int(max_groups)]
    plot_data = plot_data[plot_data[".plot_group"].isin(selected)].reset_index(drop=True)
    fig, ax = plt.subplots()
    for group, g in plot_data.groupby(".plot_group", sort=False, dropna=False):
        ax.plot(g[".plot_index"], g["time_value"], marker="o", label=str(group))
        bad = g[".any_time_issue"].to_numpy(bool)
        if bad.any():
            ax.scatter(g.loc[bad, ".plot_index"], g.loc[bad, "time_value"], marker="x")
    if plot_data[".plot_group"].nunique() > 1:
        ax.legend()
    ax.set_title(title or "Gazepoint time/counter reset diagnostics")
    ax.set_xlabel("Row index within group")
    ax.set_ylabel("Time/counter value")
    notes = ["Time-reset plots summarize time/counter ordering and reset flags.", "They support synchronization QC only and do not establish causal timing or true physiological latency."]
    return _plot_contract(fig, plot_data, "time_resets", {"time_col": time_col, "group_cols": _as_list(group_cols), "max_groups": int(max_groups)}, notes)


def plot_gazepoint_biometric_report_dashboard(
    data=None, signal_activity=None, time_resets=None, signal_cols=None, group_cols=None,
    time_col=None, include_signal_activity=True, include_time_resets=True, max_groups=30,
    continue_on_error=True, title_prefix="Gazepoint biometric QC",
):
    for name, value in [("include_signal_activity", include_signal_activity), ("include_time_resets", include_time_resets), ("continue_on_error", continue_on_error)]:
        if not isinstance(value, (bool, np.bool_)):
            raise TypeError(f"`{name}` must be TRUE or FALSE.")
    if data is None and signal_activity is None and time_resets is None:
        raise ValueError("Supply `data`, `signal_activity`, `time_resets`, or a combination of these.")
    plots = {}
    errors = []
    if include_signal_activity:
        try:
            inp = signal_activity if signal_activity is not None else data
            plots["signal_activity"] = plot_gazepoint_signal_activity(inp, signal_cols, group_cols, max_groups=max_groups, title=f"{title_prefix} - signal activity")
        except Exception as exc:
            if not continue_on_error:
                raise
            errors.append({"plot": "signal_activity", "message": str(exc)})
    if include_time_resets:
        try:
            inp = time_resets if time_resets is not None else data
            plots["time_resets"] = plot_gazepoint_time_resets(inp, time_col, group_cols, max_groups=max_groups, title=f"{title_prefix} - time resets")
        except Exception as exc:
            if not continue_on_error:
                raise
            errors.append({"plot": "time_resets", "message": str(exc)})
    error_df = pd.DataFrame(errors, columns=["plot", "message"])
    contract_ok = [bool(getattr(x, "_gazepoint_plot_contract", False)) for x in plots.values()]
    status = "no_plots_created" if not plots else ("partial_dashboard_created" if len(error_df) else "dashboard_created")
    overview = pd.DataFrame([{"plot_count": len(plots), "error_count": len(error_df), "all_plot_contracts_ok": all(contract_ok) if contract_ok else np.nan, "status": status, "interpretation": "Dashboard plots are lightweight QC aids for manual review and reporting. They do not infer emotion, valence, cognition, trust, preference, or physiological diagnosis."}])
    return {"overview": overview, "plots": plots, "errors": error_df, "inputs": {"data_supplied": data is not None, "signal_activity_supplied": signal_activity is not None, "time_resets_supplied": time_resets is not None}, "settings": {"signal_cols": signal_cols, "group_cols": _as_list(group_cols), "time_col": time_col, "include_signal_activity": bool(include_signal_activity), "include_time_resets": bool(include_time_resets), "max_groups": int(max_groups), "continue_on_error": bool(continue_on_error), "title_prefix": title_prefix}, "_class": "gazepoint_biometric_plot_dashboard"}


def _retag(fig, plot_type):
    fig._gazepoint_plot_type = plot_type
    settings = dict(getattr(fig, "_gazepoint_settings", {}))
    settings["plot_type"] = plot_type
    fig._gazepoint_settings = settings
    return fig


def plot_gazepoint_eda_decomposition(data, time_col=None, signal_cols=None, group_cols=None, standardise=False, max_points=5000, title=None):
    data = _df(data)
    sig = signal_cols or [c for c in ["GSR_US", "GSR_US_TONIC", "GSR_US_PHASIC", "eda_tonic", "eda_phasic"] if c in data]
    fig = plot_gazepoint_biometric_signals(data, sig, time_col, max_points=max_points, standardize=standardise, main=title or "EDA decomposition")
    return _retag(fig, "eda_decomposition")


def plot_gazepoint_scr_events(data, scr_peaks, event_windows=None, events=None, time_col=None, signal_col=None, phasic_col=None, group_cols=None, show_events=True, max_points=5000, title=None):
    data = _df(data)
    signal_col = signal_col or phasic_col or next((c for c in ["GSR_US_PHASIC", "GSR_US", "GSR"] if c in data), None)
    if signal_col is None:
        raise ValueError("No EDA/SCR signal column was available.")
    fig = plot_gazepoint_biometric_signals(data, [signal_col], time_col, max_points=max_points, main=title or "SCR events")
    ax = fig.axes[0]
    peaks = scr_peaks.copy() if isinstance(scr_peaks, pd.DataFrame) else pd.DataFrame()
    if len(peaks):
        tx = pd.to_numeric(peaks["peak_time"], errors="coerce") if "peak_time" in peaks else np.arange(len(peaks))
        if "peak_value" in peaks:
            yy = pd.to_numeric(peaks["peak_value"], errors="coerce")
        elif "peak_amplitude" in peaks:
            yy = pd.to_numeric(peaks["peak_amplitude"], errors="coerce")
        else:
            yy = np.zeros(len(peaks))
        ax.scatter(tx, yy, marker="x", label="SCR peak")
    fig = _retag(fig, "scr_events")
    fig._gazepoint_peak_data = peaks
    fig._gazepoint_event_data = events.copy() if isinstance(events, pd.DataFrame) else pd.DataFrame()
    fig._gazepoint_event_windows = event_windows.copy() if isinstance(event_windows, pd.DataFrame) else pd.DataFrame()
    return fig


def plot_gazepoint_multimodal_timeline(data, time_col=None, signal_cols=None, group_cols=None, participant_col=None, stimulus_col=None, trial_col=None, event_time_col=None, event_col=None, standardise=True, show_event_markers=True, title=None):
    data = _df(data)
    if not isinstance(standardise, (bool, np.bool_)):
        raise TypeError("`standardise` must be TRUE or FALSE.")
    names = list(data.columns)
    if time_col is None:
        time_col = next((c for c in ["event_relative_time_ms", "time_ms", "TIME", "time", "CNT"] if c in data), None)
    if time_col is None:
        raise ValueError("No time column was detected.")
    if time_col not in data:
        raise ValueError("`time_col` was not found in `data`.")
    sig = _signals(data, signal_cols)
    if not sig:
        raise ValueError("No biometric signal columns were available to plot.")
    groups = list(dict.fromkeys([c for c in _as_list(group_cols) + _as_list(participant_col) + _as_list(stimulus_col) + _as_list(trial_col) if c is not None]))
    if not groups:
        for candidates in [["participant", "subject", "subject_id", "USER", "USER_FILE", "user_file"], ["stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name"], ["trial", "trial_id", "TRIAL", "trial_global"]]:
            c = next((x for x in candidates if x in data), None)
            if c is not None:
                groups.append(c)
    missing = [c for c in groups if c not in data]
    if missing:
        raise ValueError("Grouping columns were not found in `data`: " + ", ".join(missing))
    base = data[[time_col] + groups + sig].copy()
    long = base.melt(id_vars=[time_col] + groups, value_vars=sig, var_name=".data_signal", value_name=".data_value")
    long[".data_time"] = pd.to_numeric(long[time_col], errors="coerce")
    if groups:
        long[".data_group"] = long[groups].astype("string").fillna("<NA>").agg("||".join, axis=1)
    else:
        long[".data_group"] = "all"
    if standardise:
        values = pd.to_numeric(long[".data_value"], errors="coerce")
        grouped = values.groupby([long[".data_group"], long[".data_signal"]], sort=False, dropna=False)
        means = grouped.transform("mean")
        sds = grouped.transform("std")
        long[".data_value"] = np.where(np.isfinite(sds) & (sds > 0), (values - means) / sds, np.nan)
    event_times = []
    event_data = pd.DataFrame()
    if event_col is not None:
        if event_col not in data:
            raise ValueError("`event_col` was not found in `data`.")
        active = pd.to_numeric(data[event_col], errors="coerce").fillna(0).ne(0)
        event_data = data.loc[active].copy()
        xcol = event_time_col if event_time_col is not None else time_col
        if xcol not in data:
            raise ValueError("`event_time_col` was not found in `data`.")
        event_times = pd.to_numeric(event_data[xcol], errors="coerce").dropna().tolist()
    elif time_col == "event_relative_time_ms":
        event_times = [0]
    fig, ax = plt.subplots()
    for (grp, signal), g in long.groupby([".data_group", ".data_signal"], sort=False, dropna=False):
        ax.plot(g[".data_time"], g[".data_value"], label=f"{grp}||{signal}")
    if show_event_markers:
        for x in event_times:
            ax.axvline(x, alpha=0.25)
    if long[".data_signal"].nunique() > 1 or long[".data_group"].nunique() > 1:
        ax.legend()
    ax.set_title(title or "Gazepoint multimodal timeline")
    ax.set_xlabel(time_col)
    ax.set_ylabel("standardized signal" if standardise else "signal")
    settings = {"plot_type": "multimodal_timeline", "time_col": time_col, "signal_cols": sig, "group_cols": groups, "standardise": bool(standardise), "event_col": event_col, "event_times": event_times}
    fig = _plot_contract(fig, long, "multimodal_timeline", settings, ["Multimodal timelines are descriptive and do not establish causal timing or psychological states."])
    fig._gazepoint_event_data = event_data
    return fig


def plot_gazepoint_scr_specification_curve(x, estimate_col=None, specification_col="specification_id", add_zero_line=True, main="SCR specification curve"):
    x = _df(x, "x")
    if specification_col not in x:
        raise ValueError("`specification_col` was not found in `x`.")
    estimate_col = estimate_col or next((c for c in x if c != specification_col and pd.api.types.is_numeric_dtype(x[c])), None)
    if estimate_col is None or estimate_col not in x:
        raise ValueError("A numeric estimate column could not be determined.")
    fig, ax = plt.subplots()
    ax.plot(np.arange(len(x)), pd.to_numeric(x[estimate_col], errors="coerce"), marker="o")
    if add_zero_line:
        ax.axhline(0)
    ax.set_title(main)
    return _plot_contract(fig, x.copy(), "scr_specification_curve", {"estimate_col": estimate_col, "specification_col": specification_col})


# Feature inventory -----------------------------------------------------------
_FEATURE_DOMAINS = {
    "import_and_schema": ["import_gazepoint_biometrics", "import_gazepoint_biometric_folder", "import_gazepoint_data_summary", "check_gazepoint_biometric_columns", "import_gazepoint_lsl_xdf", "standardise_gazepoint_biometric_names", "detect_gazepoint_biometric_schema", "detect_gazepoint_time_columns", "simulate_gazepoint_biometrics", "detect_active_biometric_channels"],
    "quality_and_readiness": ["validate_gazepoint_biometrics", "summarise_gazepoint_biometric_validity", "audit_gazepoint_biometric_missingness", "flag_gazepoint_biometric_dropouts", "audit_gazepoint_biometric_sampling", "audit_gazepoint_signal_activity", "audit_gazepoint_time_resets", "recommend_gazepoint_biometric_exclusions", "run_gazepoint_biometrics_real_data_readiness", "audit_gazepoint_distributional_drift", "audit_gazepoint_gsr_units", "prepare_gazepoint_artifact_svm_features", "flag_gazepoint_mad_artifacts", "flag_gazepoint_artifacts_svm"],
    "preprocessing": ["standardise_gazepoint_zscore", "standardize_gazepoint_zscore", "standardise_gazepoint_range_correction", "standardize_gazepoint_range_correction", "baseline_correct_gazepoint_pupil", "standardise_gazepoint_adaptive_ema", "standardize_gazepoint_adaptive_ema", "baseline_correct_gazepoint_gsr", "baseline_correct_gazepoint_hr", "smooth_gazepoint_biometrics", "convert_gazepoint_gsr_to_conductance", "decompose_gazepoint_eda", "denoise_gazepoint_eda_wavelet", "denoise_gazepoint_eda_autoencoder", "denoise_gazepoint_ppg_autoencoder", "denoise_gazepoint_quantization_noise", "correct_gazepoint_eda_temperature", "audit_gazepoint_stabilization_period", "regress_gazepoint_pupil_luminance", "standardize_gazepoint_biometrics_within_unit", "standardise_gazepoint_biometrics_within_unit"],
    "eda_scr": ["classify_gazepoint_eda_response_pattern", "classify_gazepoint_scr_intervals", "flag_kleckner_eda_artifacts", "audit_gazepoint_gsr_quality", "audit_gazepoint_eda_artifacts", "detect_gazepoint_scr_events", "detect_gazepoint_scr_peaks", "summarise_gazepoint_scr_event_windows", "prepare_gazepoint_scr_hurdle_model_data", "run_gazepoint_scr_threshold_sensitivity", "run_gazepoint_scr_multiverse", "screen_gazepoint_eda_nonresponders", "summarise_gazepoint_gsr_windows", "summarise_gazepoint_gsr_tonic_phasic", "extract_gazepoint_eda_spectral_power", "extract_gazepoint_eda_complexity", "extract_gazepoint_eda_tvsymp", "plot_gazepoint_eda_decomposition", "optimize_gazepoint_cvxeda_tau", "model_gazepoint_eda_point_process", "extract_gazepoint_bilateral_eda_asymmetry", "analyze_gazepoint_skin_potential", "analyze_gazepoint_ac_susceptance", "detect_gazepoint_doubly_stochastic_changepoints", "extract_gazepoint_scr_recovery_times", "plot_gazepoint_scr_events"],
    "ibi_hr_hrv": ["audit_gazepoint_hr_quality", "assess_gazepoint_hrp_waveform_quality", "audit_gazepoint_ibi_quality", "filter_gazepoint_ibi_implausible", "compare_gazepoint_hr_ibi_consistency", "summarise_gazepoint_hr_windows", "summarise_gazepoint_ibi_windows", "summarise_gazepoint_ibi_hrv_windows", "extract_gazepoint_hrv_features", "extract_gazepoint_pdr_signals", "calculate_gazepoint_rsa", "test_gazepoint_hrv_nonlinearity", "extract_gazepoint_hrv_rqa", "extract_gazepoint_hrv_geometric", "extract_gazepoint_hrv_fragmentation", "extract_gazepoint_hrv_asymmetry", "model_gazepoint_hr_point_process", "analyze_gazepoint_cardiorespiratory_causality", "extract_gazepoint_edr_pca", "extract_gazepoint_hrv_rcmse", "extract_gazepoint_respiration_ceemdan", "fuse_gazepoint_respiration_kalman", "extract_gazepoint_hrv_fuzzy_csi", "extract_gazepoint_beats_kmeans", "model_gazepoint_hrv_ipfm", "extract_gazepoint_hrv_nonlinear"],
    "ttl_alignment": ["extract_gazepoint_ttl_events", "align_gazepoint_biometrics_to_ttl", "estimate_gazepoint_signal_lag", "audit_gazepoint_biometric_sync_drift", "plot_gazepoint_multimodal_timeline"],
    "aoi_biometrics": ["summarise_gazepoint_aoi_biometrics", "prepare_gazepoint_aoi_biometrics_model_data", "plot_gazepoint_aoi_biometrics"],
    "modelling_and_windows": ["summarise_gazepoint_engagement_windows", "summarise_gazepoint_dial_windows", "summarise_gazepoint_multimodal_windows", "summarise_gazepoint_full_biometric_windows", "sync_gazepoint_biometrics_with_gaze", "join_gazepoint_biometrics_to_master", "chunk_gazepoint_biometrics", "run_gazepoint_online_design_optimization", "prepare_gazepoint_multimodal_model_data", "prepare_gazepoint_biometrics_lme_data"],
    "reporting": ["create_gazepoint_preregistration_template", "run_gpbiometrics_shiny", "run_gpbiometrics_shiny_annotator", "run_gazepoint_biometrics_workflow", "summarise_gazepoint_biometrics_workflow", "diagnose_gazepoint_biometrics_workflow", "create_gazepoint_biometrics_checklist", "create_gazepoint_biometrics_methods_text", "create_gazepoint_eda_analysis_pipeline", "run_gazepoint_eda_analysis_pipeline", "create_gazepoint_biometrics_report_tables", "write_gazepoint_biometrics_report_tables", "create_gazepoint_biometrics_report", "run_gazepoint_automated_statistics", "export_gazepoint_biometrics_report_bundle"],
    "interoperability": ["export_gazepoint_rhrv_input", "prepare_gazepoint_rhrv_input", "prepare_gazepoint_pyppg_input", "prepare_gazepoint_neurokit_eda_input", "run_gazepoint_neurokit_eda_crosscheck", "prepare_gazepoint_ledalab_input", "prepare_gazepoint_pspm_input", "prepare_gazepoint_pspm_dcm_input", "prepare_gazepoint_ctsi_input", "prepare_gazepoint_cvxeda_input"],
    "plotting": ["plot_gazepoint_biometric_signals", "plot_gazepoint_biometric_quality", "plot_gazepoint_eda_decomposition", "plot_gazepoint_scr_events", "plot_gazepoint_multimodal_timeline", "plot_gazepoint_signal_activity", "plot_gazepoint_time_resets", "plot_gazepoint_biometric_report_dashboard", "plot_gazepoint_saccade_main_sequence", "standardise_gazepoint_plot_contract", "standardize_gazepoint_plot_contracts", "check_gazepoint_plot_contract", "plot_gazepoint_scr_specification_curve", "plot_gazepoint_eda_gram", "get_gazepoint_plot_data"],
}


def create_gazepoint_biometrics_feature_inventory(include_internal=False):
    if not isinstance(include_internal, (bool, np.bool_)):
        raise TypeError("`include_internal` must be TRUE or FALSE.")
    import gpbiometricspy as gp
    rows = []
    for domain, names in _FEATURE_DOMAINS.items():
        for name in names:
            available = name in getattr(gp, "IMPLEMENTED_EXPORTS", [])
            rows.append({"domain": domain, "function_name": name, "expected": True,
                         "user_facing": True, "available": available,
                         "status": "available" if available else "missing"})
    inventory = pd.DataFrame(rows)
    domain_summary = inventory.groupby("domain", sort=False).agg(
        feature_count=("function_name", "size"), available_features=("available", "sum")
    ).reset_index()
    domain_summary["missing_features"] = domain_summary["feature_count"] - domain_summary["available_features"]
    domain_summary["completion_rate"] = domain_summary["available_features"] / domain_summary["feature_count"]
    domain_summary["status"] = np.where(domain_summary["missing_features"].eq(0), "complete",
                                         np.where(domain_summary["available_features"].gt(0), "partial", "missing"))
    missing_expected = inventory.loc[~inventory["available"] & inventory["expected"]].copy()
    overview = pd.DataFrame([{
        "feature_rows": len(inventory), "domain_count": inventory["domain"].nunique(),
        "available_features": int(inventory["available"].sum()),
        "missing_expected_features": len(missing_expected), "include_internal": bool(include_internal),
        "status": "feature_inventory_complete" if len(missing_expected) == 0 else "warn_expected_features_missing",
    }])
    return {"overview": overview, "inventory": inventory, "domain_summary": domain_summary,
            "missing_expected": missing_expected,
            "settings": {"include_internal": bool(include_internal),
                         "interpretation_notes": ["The inventory audits major user-facing gpbiometrics helpers and does not analyse biometric data." ]},
            "_class": "gazepoint_biometrics_feature_inventory"}


_DOMAIN_LABELS = {
    "import_and_schema": "Import and schema", "quality_and_readiness": "Quality and readiness",
    "preprocessing": "Preprocessing", "eda_scr": "EDA / GSR / SCR", "ibi_hr_hrv": "IBI / HR / HRV",
    "ttl_alignment": "TTL and alignment", "aoi_biometrics": "AOI biometrics",
    "modelling_and_windows": "Modelling and windows", "reporting": "Reporting",
    "interoperability": "Interoperability", "plotting": "Plotting",
}


def format_gazepoint_biometrics_feature_inventory(inventory=None, include_internal=False, sort=True):
    inv = create_gazepoint_biometrics_feature_inventory(include_internal) if inventory is None else inventory
    d = inv["inventory"].copy() if isinstance(inv, dict) else _df(inv, "inventory").copy()
    d["domain_label"] = d["domain"].map(_DOMAIN_LABELS).fillna(d["domain"].str.replace("_", " ").str.title())
    d["workflow_stage"] = np.select([
        d["function_name"].str.startswith(("import_", "detect_gazepoint_biometric_schema", "check_")),
        d["function_name"].str.startswith(("prepare_", "baseline_", "smooth_", "filter_", "standard")),
        d["function_name"].str.startswith("plot_"),
        d["function_name"].str.startswith(("report_", "create_gazepoint_biometrics_report", "export_gazepoint_biometrics_report")),
    ], ["import", "preprocessing", "visualisation", "reporting"], default="analysis")
    d["method_family"] = d["domain_label"]
    d["user_level"] = np.where(d["domain"].isin(["interoperability", "modelling_and_windows"]), "advanced", "general")
    d["interpretation_caution"] = "Interpret outputs in the context of the study design; biometric signals do not directly identify psychological or clinical states."
    d["availability_label"] = np.where(d["available"], "Available", "Unavailable")
    cols = ["domain", "domain_label", "workflow_stage", "method_family", "user_level", "function_name",
            "interpretation_caution", "available", "availability_label", "status"]
    d = d[cols]
    return d.sort_values(["domain", "function_name"]).reset_index(drop=True) if sort else d.reset_index(drop=True)


def summarise_gazepoint_biometrics_feature_inventory(formatted_inventory=None):
    d = format_gazepoint_biometrics_feature_inventory() if formatted_inventory is None else _df(formatted_inventory, "formatted_inventory")
    overview = pd.DataFrame([{
        "feature_rows": len(d), "available_features": int(d["available"].sum()),
        "missing_features": int((~d["available"]).sum()),
        "status": "formatted_inventory_complete" if d["available"].all() else "formatted_inventory_partial",
    }])
    def _summary(col):
        out = d.groupby(col, dropna=False, sort=False).agg(feature_rows=("function_name", "size"), available=("available", "sum")).reset_index()
        out["missing"] = out["feature_rows"] - out["available"]
        out["status"] = np.where(out["missing"].eq(0), "complete", "partial")
        return out
    return {"overview": overview, "domain_summary": _summary("domain"),
            "method_summary": _summary("method_family"), "user_level_summary": _summary("user_level")}


# Windows/model data -----------------------------------------------------------
def summarise_gazepoint_full_biometric_windows(data, group_columns, include_ibi_hrv=True):
    data = _df(data)
    groups = _as_list(group_columns)
    missing = [c for c in groups if c not in data]
    if missing:
        raise ValueError("`group_columns` were not found in `data`: " + ", ".join(missing))
    out = summarise_gazepoint_multimodal_windows(data, groups)
    if include_ibi_hrv and "IBI" in data:
        hres = extract_gazepoint_hrv_features(data, ibi_col="IBI", group_cols=groups, unit="auto", min_intervals=2, min_duration_s=0)
        h = hres["features"].copy()
        if "mean_ibi_ms" in h and "mean_ibi_sec" not in h:
            h["mean_ibi_sec"] = pd.to_numeric(h["mean_ibi_ms"], errors="coerce") / 1000.0
        h = h.rename(columns={"mean_ibi_sec": "ibi_mean_ibi_sec", "mean_ibi_ms": "ibi_mean_ibi_ms", "rmssd_ms": "ibi_rmssd_ms"})
        keep = groups + [c for c in ["ibi_mean_ibi_sec", "ibi_mean_ibi_ms", "ibi_rmssd_ms", "sdnn_ms", "mean_hr_bpm"] if c in h]
        out = out.merge(h[keep], on=groups, how="left")
    return out


def prepare_gazepoint_multimodal_model_data(biometrics, eye_tracking=None, group_columns=None, biometric_is_summarised=False, by=None, all=False):
    biometrics = _df(biometrics, "biometrics")
    groups = group_columns or by or [c for c in ["USER", "MEDIA_ID", "participant", "source_participant"] if c in biometrics][:2]
    groups = _as_list(groups)
    missing = [c for c in groups if c not in biometrics]
    if missing:
        raise ValueError("`group_columns` were not found in biometrics: " + ", ".join(missing))
    result = biometrics.copy() if biometric_is_summarised else summarise_gazepoint_multimodal_windows(biometrics, groups)
    source = "biometrics_only"
    if eye_tracking is not None:
        eye_tracking = _df(eye_tracking, "eye_tracking")
        missing_eye = [c for c in groups if c not in eye_tracking]
        if missing_eye:
            raise ValueError("`eye_tracking` is missing merge keys: " + ", ".join(missing_eye))
        result = result.merge(eye_tracking, on=groups, how="outer" if all else "left")
        source = "eye_tracking_plus_biometrics"
    result.attrs["model_data_summary"] = {
        "source": source, "rows": len(result), "has_eye_tracking": eye_tracking is not None,
    }
    result.attrs["class"] = ["gazepoint_multimodal_model_data", "data.frame"]
    return result


def _first_existing(names, candidates):
    lower = {str(c).lower(): c for c in names}
    for c in candidates:
        if c in names:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def prepare_gazepoint_biometrics_lme_data(
    data, outcome_col, fixed_effect_cols=None, condition_cols=None, covariate_cols=None,
    random_effect_cols=None, participant_col=None, stimulus_col=None, trial_col=None,
    window_col=None, baseline_col=None, baseline_correct=False, factor_cols=None,
    continuous_cols=None, scale_continuous=False, include_window=True, drop_missing=True, min_rows=10,
):
    data = _df(data).copy()
    if not isinstance(outcome_col, str) or not outcome_col:
        raise ValueError("`outcome_col` must be a single column name.")
    if outcome_col not in data:
        raise ValueError("`outcome_col` was not found in `data`.")
    if not isinstance(min_rows, (int, float, np.number)) or min_rows < 1:
        raise ValueError("`min_rows` must be a positive number.")
    for name, value in [("baseline_correct", baseline_correct), ("scale_continuous", scale_continuous),
                        ("include_window", include_window), ("drop_missing", drop_missing)]:
        if not isinstance(value, (bool, np.bool_)):
            raise TypeError(f"`{name}` must be TRUE or FALSE.")
    requested = list(dict.fromkeys(c for c in sum([_as_list(fixed_effect_cols), _as_list(condition_cols), _as_list(covariate_cols),
                                                   _as_list(random_effect_cols), _as_list(participant_col), _as_list(stimulus_col),
                                                   _as_list(trial_col), _as_list(window_col), _as_list(baseline_col),
                                                   _as_list(factor_cols), _as_list(continuous_cols)], []) if c is not None))
    missing = [c for c in requested if c not in data]
    if missing:
        raise ValueError("The following requested columns were not found in `data`: " + ", ".join(missing))
    data[".gpbiometrics_original_row_id"] = np.arange(1, len(data) + 1)
    data[outcome_col] = pd.to_numeric(data[outcome_col], errors="coerce")
    if data[outcome_col].isna().all():
        raise ValueError("`outcome_col` must contain numeric values.")
    analysis_outcome = outcome_col
    if baseline_correct:
        if baseline_col is None:
            raise ValueError("`baseline_col` must be supplied when `baseline_correct = TRUE`.")
        data[baseline_col] = pd.to_numeric(data[baseline_col], errors="coerce")
        if data[baseline_col].isna().all():
            raise ValueError("`baseline_col` must contain numeric values.")
        analysis_outcome = f"{outcome_col}_baseline_corrected"
        data[analysis_outcome] = data[outcome_col] - data[baseline_col]
    explicit_random = list(dict.fromkeys(_as_list(random_effect_cols) + _as_list(participant_col) + _as_list(stimulus_col) + _as_list(trial_col)))
    if explicit_random:
        random_cols = explicit_random
    else:
        random_cols = [c for c in [
            _first_existing(data.columns, ["participant", "subject", "subject_id", "USER", "USER_FILE", "user_file"]),
            _first_existing(data.columns, ["stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name"]),
            _first_existing(data.columns, ["trial", "trial_id", "TRIAL", "trial_global"]),
        ] if c is not None]
    fixed_terms = list(dict.fromkeys(_as_list(fixed_effect_cols) + _as_list(condition_cols) + _as_list(covariate_cols) + (_as_list(window_col) if include_window else [])))
    inferred_factor = [c for c in fixed_terms if c in data and not pd.api.types.is_numeric_dtype(data[c])]
    factor_cols_final = list(dict.fromkeys(_as_list(factor_cols) + inferred_factor + random_cols))
    for c in factor_cols_final:
        if c in data:
            data[c] = data[c].astype("category")
    continuous = _as_list(continuous_cols) if continuous_cols is not None else [c for c in fixed_terms if c in data and pd.api.types.is_numeric_dtype(data[c])]
    formula_fixed = fixed_terms.copy()
    scaled_rows = []
    if scale_continuous:
        for c in continuous:
            x = pd.to_numeric(data[c], errors="coerce")
            sd = x.std(ddof=1)
            scaled = f"z_{re.sub(r'[^A-Za-z0-9_.]+', '.', c)}"
            data[scaled] = (x - x.mean()) / sd if np.isfinite(sd) and sd != 0 else np.nan
            formula_fixed = [scaled if z == c else z for z in formula_fixed]
            scaled_rows.append({"original_col": c, "scaled_col": scaled})
    required = list(dict.fromkeys([analysis_outcome] + formula_fixed + random_cols))
    complete = data[required].notna().all(axis=1) if required else pd.Series(True, index=data.index)
    data["lme_complete_case"] = complete.to_numpy(bool)
    model_data = data.loc[complete].copy() if drop_missing else data.copy()
    n_complete = int(complete.sum())
    status = "empty_input" if len(data) == 0 else ("no_complete_model_rows" if n_complete == 0 else ("limited_complete_rows" if n_complete < min_rows else "ready"))
    rhs = " + ".join(formula_fixed) if formula_fixed else "1"
    if random_cols:
        rhs = " + ".join([rhs] + [f"(1 | {c})" for c in random_cols])
    formula_text = f"{analysis_outcome} ~ {rhs}"
    vars_to_summarise = list(dict.fromkeys([analysis_outcome, outcome_col] + _as_list(baseline_col) + formula_fixed + fixed_terms + random_cols))
    variable_rows = []
    for c in vars_to_summarise:
        if c not in data:
            continue
        role = "analysis_outcome" if c == analysis_outcome else ("fixed_effect" if c in formula_fixed else ("random_effect" if c in random_cols else ("baseline" if c == baseline_col else "other")))
        variable_rows.append({"variable": c, "role": role, "class": str(data[c].dtype),
                              "missing_count": int(data[c].isna().sum()), "unique_count": int(data[c].nunique(dropna=True))})
    return {
        "overview": pd.DataFrame([{"input_rows": len(data), "complete_model_rows": n_complete, "model_rows": len(model_data),
                                   "outcome_col": outcome_col, "analysis_outcome_col": analysis_outcome,
                                   "fixed_effect_count": len(formula_fixed), "random_effect_count": len(random_cols), "status": status}]),
        "data": data, "model_data": model_data, "model_formula": formula_text,
        "variable_summary": pd.DataFrame(variable_rows),
        "settings": {"outcome_col": outcome_col, "analysis_outcome_col": analysis_outcome,
                     "formula_fixed_terms": formula_fixed, "random_effect_cols": random_cols,
                     "factor_cols": factor_cols_final, "continuous_cols": continuous,
                     "scaled_map": pd.DataFrame(scaled_rows), "scale_continuous": bool(scale_continuous),
                     "include_window": bool(include_window), "drop_missing": bool(drop_missing),
                     "min_rows": min_rows, "formula_text": formula_text},
        "_class": "gazepoint_biometrics_lme_data",
    }


def summarise_gazepoint_dial_windows(data, *args, dial_col=None, **kwargs):
    return summarise_gazepoint_engagement_windows(data, *args, value_column=dial_col or "DIAL", **kwargs)


def join_gazepoint_biometrics_to_gp3tools(biometrics, gp3tools_master, *args, **kwargs):
    biometrics = _df(biometrics, "biometrics")
    gp3tools_master = _df(gp3tools_master, "gp3tools_master")
    by = kwargs.get("by") or [c for c in ["USER", "MEDIA_ID", "participant", "trial", "CNT", "time"] if c in biometrics and c in gp3tools_master]
    by = _as_list(by)
    if not by:
        raise ValueError("No shared join columns were detected; supply `by`.")
    missing = [c for c in by if c not in biometrics or c not in gp3tools_master]
    if missing:
        raise ValueError("Join columns were not found in both inputs: " + ", ".join(missing))
    return gp3tools_master.merge(biometrics, on=by, how=kwargs.get("how", "left"), suffixes=("", "_biometric"))


# Workflow/readiness/reporting -------------------------------------------------
def _signal_is_active(active_channels, signal):
    if not isinstance(active_channels, pd.DataFrame) or "signal" not in active_channels or "active" not in active_channels:
        return False
    sel = active_channels.loc[active_channels["signal"].eq(signal), "active"]
    return bool(sel.fillna(False).astype(bool).any())


def _sampling_audit(data, group_columns=None, time_column=None, time_unit="samples", expected_rate_hz=60):
    groups = _as_list(group_columns)
    tc = time_column or next((c for c in ["CNT", "TIME", "TIME_TICK", "time_ms", "time"] if c in data), None)
    if tc is None:
        return pd.DataFrame([{"time_column": None, "n_rows": len(data), "status": "time_column_missing"}])
    if tc not in data:
        raise ValueError("`sampling_time_column` was not found in imported data.")
    missing = [c for c in groups if c not in data]
    if missing:
        raise ValueError("Sampling group columns were not found in imported data: " + ", ".join(missing))
    iterator = data.groupby(groups[0] if len(groups) == 1 else groups, dropna=False, sort=False) if groups else [("all", data)]
    rows = []
    for key, g in iterator:
        t = pd.to_numeric(g[tc], errors="coerce").to_numpy(float)
        diff = np.diff(t)
        pos = diff[np.isfinite(diff) & (diff > 0)]
        median_step = float(np.median(pos)) if len(pos) else np.nan
        if time_unit == "seconds":
            rate = 1 / median_step if np.isfinite(median_step) and median_step > 0 else np.nan
        elif time_unit == "milliseconds":
            rate = 1000 / median_step if np.isfinite(median_step) and median_step > 0 else np.nan
        elif time_unit == "microseconds":
            rate = 1_000_000 / median_step if np.isfinite(median_step) and median_step > 0 else np.nan
        else:
            rate = float(expected_rate_hz) if expected_rate_hz else np.nan
        row = {"time_column": tc, "time_unit": time_unit, "n_rows": len(g), "median_step": median_step,
               "observed_rate_hz": rate, "expected_rate_hz": expected_rate_hz,
               "negative_steps": int((diff[np.isfinite(diff)] < 0).sum()),
               "status": "review_nonmonotonic_time" if np.any(diff[np.isfinite(diff)] < 0) else "sampling_audited"}
        if groups:
            values = key if isinstance(key, tuple) else (key,)
            row.update(dict(zip(groups, values)))
        rows.append(row)
    return pd.DataFrame(rows)


def _exclusion_recommendations(windows, gsr_min=50, hr_min=50, dial_min=50):
    d = windows.copy()
    criteria = []
    for col, threshold in [("gsr_usable_pct", gsr_min), ("hr_usable_pct", hr_min), ("dial_usable_pct", dial_min)]:
        if col in d:
            criteria.append(pd.to_numeric(d[col], errors="coerce").lt(threshold))
    flag = np.logical_or.reduce(criteria) if criteria else np.zeros(len(d), dtype=bool)
    window = d.copy()
    window["recommendation"] = np.where(flag, "review", "keep")
    group_cols = [c for c in ["source_participant", "USER", "participant"] if c in d]
    if group_cols:
        pcol = group_cols[0]
        participant = window.groupby(pcol, dropna=False, sort=False)["recommendation"].apply(
            lambda x: "review" if (x == "review").any() else "keep"
        ).reset_index(name="participant_recommendation")
    else:
        participant = pd.DataFrame([{"participant_recommendation": "review" if flag.any() else "keep"}])
    return {"windows": window, "participants": participant, "_class": "gazepoint_biometric_exclusion_recommendations"}


def run_gazepoint_biometrics_real_data_readiness(data=None, workflow_result=None, min_rows=100, min_active_signal_count=1, max_missing_prop=.50, required_signal_cols=None, require_gsr_us_preferred=True, require_ibi_for_hrv=False, time_col=None, ttl_cols=None):
    if data is None:
        if not isinstance(workflow_result, dict):
            raise ValueError("Supply `data` or a workflow result containing biometric data.")
        data = workflow_result.get("biometrics", workflow_result.get("data"))
        if data is None:
            raise ValueError("Supply `data` or a workflow result containing biometric data.")
    data = _df(data)
    active = _signals(data)
    checks = [
        {"check": "row_count", "status": "pass" if len(data) >= min_rows else "fail"},
        {"check": "active_signals", "status": "pass" if len(active) >= min_active_signal_count else "fail"},
    ]
    missing_prop = max((float(data[c].isna().mean()) for c in active), default=1.0)
    checks.append({"check": "missingness", "status": "pass" if missing_prop <= max_missing_prop else "warn"})
    if required_signal_cols:
        missing = [c for c in required_signal_cols if c not in data]
        checks.append({"check": "required_signals", "status": "fail" if missing else "pass"})
    if "GSR" in data and "GSR_US" not in data and require_gsr_us_preferred:
        checks.append({"check": "gsr_conductance_channel", "status": "warn"})
    if "HRV" in data and "IBI" not in data:
        checks.append({"check": "hrv_ibi_caution", "status": "fail" if require_ibi_for_hrv else "warn"})
    tc = time_col or next((c for c in ["time_ms", "CNT", "TIME", "time"] if c in data), None)
    if tc:
        bad = False
        iterator = data.groupby("source_file", sort=False, dropna=False) if "source_file" in data else [(None, data)]
        for _, g in iterator:
            t = pd.to_numeric(g[tc], errors="coerce").to_numpy(float)
            finite = t[np.isfinite(t)]
            bad |= bool(len(finite) > 1 and np.any(np.diff(finite) < 0))
        checks.append({"check": "time_column", "status": "warn" if bad else "pass"})
    ttl = _as_list(ttl_cols) if ttl_cols is not None else [c for c in data if str(c).upper().startswith("TTL") and not str(c).upper().endswith("V")]
    ttl_pass = bool(ttl and any(pd.to_numeric(data[c], errors="coerce").fillna(0).ne(0).any() for c in ttl if c in data))
    checks.append({"check": "ttl_markers", "status": "pass" if ttl_pass else "warn"})
    c = pd.DataFrame(checks)
    final = "fail" if c["status"].eq("fail").any() else ("warn" if c["status"].eq("warn").any() else "pass")
    decision = "ready_for_analysis_with_standard_cautions" if final == "pass" else ("review_before_analysis" if final == "warn" else "not_ready_for_analysis")
    return {"overview": pd.DataFrame([{"final_status": final, "decision": decision, "row_count": len(data), "active_signal_count": len(active)}]),
            "checks": c, "settings": {"min_rows": min_rows, "min_active_signal_count": min_active_signal_count, "max_missing_prop": max_missing_prop},
            "_class": "gazepoint_biometrics_real_data_readiness"}


def run_gazepoint_biometrics_workflow(
    path, group_columns=None, recursive=False, include_fixations=False, include_all_gaze=True,
    include_other_csv=False, require_active_signal=True, create_exclusion_recommendations=True,
    gsr_min_usable_pct=50, hr_min_usable_pct=50, dial_min_usable_pct=50,
    extract_ttl_events=True, ttl_event_mode="changes", audit_sampling=True,
    sampling_group_columns=None, sampling_time_column=None, sampling_time_unit="samples",
    expected_sampling_rate_hz=60,
):
    data = import_gazepoint_biometric_folder(path, recursive=recursive, include_fixations=include_fixations,
                                             include_all_gaze=include_all_gaze, include_other_csv=include_other_csv)
    validation = validate_gazepoint_biometrics(data, require_active_signal=require_active_signal)
    missingness = audit_gazepoint_biometric_missingness(data)
    quality = pd.concat([audit_gazepoint_gsr_quality(data), audit_gazepoint_hr_quality(data), audit_gazepoint_engagement_dial(data)], ignore_index=True)
    if audit_sampling:
        groups = sampling_group_columns
        if groups is None:
            groups = [c for c in ["source_file", "source_participant", "MEDIA_ID", "MEDIA_NAME"] if c in data]
        sampling = _sampling_audit(data, groups, sampling_time_column, sampling_time_unit, expected_sampling_rate_hz)
    else:
        sampling = None
    windows = None
    exclusions = None
    if group_columns is not None:
        windows = summarise_gazepoint_multimodal_windows(data, group_columns)
        if create_exclusion_recommendations:
            exclusions = _exclusion_recommendations(windows, gsr_min_usable_pct, hr_min_usable_pct, dial_min_usable_pct)
    ttl = None
    if extract_ttl_events:
        ttl_groups = [c for c in ["source_participant", "USER", "USERID", "MEDIA_ID", "MEDIA_NAME"] if c in data]
        ttl = extract_gazepoint_ttl_events(data, group_columns=ttl_groups, mode=ttl_event_mode)
    checklist = create_gazepoint_biometrics_checklist(data, require_active_signal=require_active_signal)
    methods_text = create_gazepoint_biometrics_methods_text(checklist=checklist)
    overview = pd.DataFrame([{
        "n_rows": len(data), "n_columns": data.shape[1],
        "source_file_count": int(data["source_file"].nunique()) if "source_file" in data else 1,
        "has_sampling_audit": sampling is not None,
        "sampling_group_count": len(sampling) if isinstance(sampling, pd.DataFrame) else np.nan,
        "has_window_summaries": windows is not None,
        "has_exclusion_recommendations": exclusions is not None,
        "has_ttl_events": ttl is not None,
        "ttl_event_count": len(ttl) if isinstance(ttl, pd.DataFrame) else np.nan,
        "validation_issue_count": len(validation.get("issues", [])),
        "active_signal_count": int(validation["overview"].iloc[0]["active_signal_count"]),
    }])
    out = {"overview": overview, "data": data, "biometrics": data, "validation": validation,
           "missingness": missingness, "quality": quality, "sampling": sampling, "windows": windows,
           "exclusion_recommendations": exclusions, "ttl_events": ttl, "checklist": checklist,
           "methods_text": methods_text, "settings": {"group_columns": _as_list(group_columns),
           "expected_sampling_rate_hz": expected_sampling_rate_hz}, "_class": "gazepoint_biometrics_workflow"}
    out["diagnostics"] = diagnose_gazepoint_biometrics_workflow(out, require_gsr=False, require_hr=False)
    return out


def diagnose_gazepoint_biometrics_workflow(workflow, require_gsr=True, require_hr=True, require_dial=False, max_exclude_window_pct=25, max_review_window_pct=25):
    if not isinstance(workflow, dict) or workflow.get("_class") != "gazepoint_biometrics_workflow":
        raise ValueError("`workflow` must be produced by run_gazepoint_biometrics_workflow().")
    data = workflow.get("data", workflow.get("biometrics"))
    active = workflow.get("validation", {}).get("active_channels", detect_active_biometric_channels(data))
    reasons = []
    if require_gsr and not _signal_is_active(active, "gsr_eda"):
        reasons.append("GSR/EDA required but unavailable")
    if require_hr and not _signal_is_active(active, "heart_rate"):
        reasons.append("heart rate required but unavailable")
    if require_dial and not _signal_is_active(active, "engagement_dial"):
        reasons.append("engagement dial required but unavailable")
    exclusions = workflow.get("exclusion_recommendations")
    window_table = exclusions.get("windows") if isinstance(exclusions, dict) else pd.DataFrame()
    n_windows = len(window_table) if isinstance(window_table, pd.DataFrame) else 0
    review_windows = int(window_table.get("recommendation", pd.Series(dtype=object)).eq("review").sum()) if n_windows else 0
    exclude_windows = int(window_table.get("recommendation", pd.Series(dtype=object)).eq("exclude").sum()) if n_windows else 0
    review_pct = 100 * review_windows / n_windows if n_windows else 0.0
    exclude_pct = 100 * exclude_windows / n_windows if n_windows else 0.0
    if review_pct > max_review_window_pct:
        reasons.append("review-window percentage exceeds threshold")
    if exclude_pct > max_exclude_window_pct:
        reasons.append("exclude-window percentage exceeds threshold")
    status = "fail" if reasons else "pass"
    return pd.DataFrame([{
        "final_status": status, "diagnostic_reasons": "; ".join(reasons) if reasons else "workflow diagnostics passed",
        "validation_issue_count": len(workflow.get("validation", {}).get("issues", [])),
        "active_gsr_eda": _signal_is_active(active, "gsr_eda"), "active_heart_rate": _signal_is_active(active, "heart_rate"),
        "active_engagement_dial": _signal_is_active(active, "engagement_dial"), "active_ttl_marker": _signal_is_active(active, "ttl_marker"),
        "n_windows": n_windows, "review_windows": review_windows, "exclude_windows": exclude_windows,
        "review_window_pct": review_pct, "exclude_window_pct": exclude_pct,
        "ttl_event_count": len(workflow.get("ttl_events")) if isinstance(workflow.get("ttl_events"), pd.DataFrame) else 0,
    }])


def summarise_gazepoint_biometrics_workflow(workflow):
    if not isinstance(workflow, dict) or workflow.get("_class") != "gazepoint_biometrics_workflow":
        raise ValueError("`workflow` must be produced by run_gazepoint_biometrics_workflow().")
    ov = workflow["overview"].iloc[0]
    active = workflow["validation"]["active_channels"]
    return pd.DataFrame([{
        "n_rows": int(ov.n_rows), "n_columns": int(ov.n_columns), "source_file_count": int(ov.source_file_count),
        "validation_issue_count": int(ov.validation_issue_count),
        "active_gsr_eda": _signal_is_active(active, "gsr_eda"), "active_heart_rate": _signal_is_active(active, "heart_rate"),
        "active_engagement_dial": _signal_is_active(active, "engagement_dial"), "active_ttl_marker": _signal_is_active(active, "ttl_marker"),
        "has_sampling_audit": bool(ov.has_sampling_audit), "sampling_group_count": ov.sampling_group_count,
        "has_window_summaries": bool(ov.has_window_summaries), "has_exclusion_recommendations": bool(ov.has_exclusion_recommendations),
        "has_ttl_events": bool(ov.has_ttl_events), "ttl_event_count": ov.ttl_event_count,
    }])


def _message_table(message, required_col=None):
    row = {"message": message}
    if required_col is not None:
        row[required_col] = np.nan
    return pd.DataFrame([row])


def create_gazepoint_biometrics_report_tables(workflow=None, validation=None, quality=None, sampling=None, diagnostics=None, exclusion_recommendations=None, ttl_events=None, max_ttl_events=20):
    overview = None
    if workflow is not None:
        if not isinstance(workflow, dict) or workflow.get("_class") != "gazepoint_biometrics_workflow":
            raise ValueError("`workflow` must be produced by run_gazepoint_biometrics_workflow().")
        validation = workflow.get("validation")
        quality = workflow.get("quality")
        sampling = workflow.get("sampling")
        diagnostics = diagnose_gazepoint_biometrics_workflow(workflow, require_gsr=False, require_hr=False)
        exclusion_recommendations = workflow.get("exclusion_recommendations")
        ttl_events = workflow.get("ttl_events")
        overview = workflow.get("overview")
    if overview is None:
        overview = validation.get("overview") if isinstance(validation, dict) and isinstance(validation.get("overview"), pd.DataFrame) else _message_table("No overview information supplied.")
    diagnostics_table = diagnostics.copy() if isinstance(diagnostics, pd.DataFrame) else _message_table("No workflow diagnostics table supplied.")
    channels = validation.get("active_channels").copy() if isinstance(validation, dict) and isinstance(validation.get("active_channels"), pd.DataFrame) else _message_table("No active-channel table supplied.", "signal")
    quality_table = quality.copy() if isinstance(quality, pd.DataFrame) else _message_table("No quality-audit table supplied.", "usable_pct")
    sampling_table = sampling.copy() if isinstance(sampling, pd.DataFrame) else _message_table("No sampling table supplied.", "time_column")
    if isinstance(exclusion_recommendations, dict):
        win = exclusion_recommendations.get("windows")
        part = exclusion_recommendations.get("participants")
        window_table = win.copy() if isinstance(win, pd.DataFrame) else _message_table("No window recommendations supplied.", "recommendation")
        participant_table = part.copy() if isinstance(part, pd.DataFrame) else _message_table("No participant recommendations supplied.", "participant_recommendation")
    elif isinstance(exclusion_recommendations, pd.DataFrame):
        window_table = exclusion_recommendations.copy()
        if "recommendation" not in window_table:
            window_table["recommendation"] = np.nan
        participant_table = _message_table("No participant recommendations supplied.", "participant_recommendation")
    else:
        window_table = _message_table("No window recommendations supplied.", "recommendation")
        participant_table = _message_table("No participant recommendations supplied.", "participant_recommendation")
    ttl_table = ttl_events.head(int(max_ttl_events)).copy() if isinstance(ttl_events, pd.DataFrame) else _message_table("No TTL events supplied.", "ttl_value")
    return {"overview": overview.copy(), "diagnostics": diagnostics_table, "channels": channels,
            "quality": quality_table, "sampling": sampling_table, "window_recommendations": window_table,
            "participant_recommendations": participant_table, "ttl_events": ttl_table,
            "_class": "gazepoint_biometrics_report_tables"}


def _safe_filename(x):
    x = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(x))
    x = re.sub(r"_+", "_", x).strip("_")
    return x or "table"


def write_gazepoint_biometrics_report_tables(tables, output_dir, prefix="gazepoint_biometrics", overwrite=True, include_empty_message_tables=False):
    if isinstance(tables, dict) and tables.get("_class") == "gazepoint_biometrics_workflow":
        tables = create_gazepoint_biometrics_report_tables(workflow=tables)
    if not isinstance(tables, dict):
        raise TypeError("`tables` must be a workflow object, report-table object, or named mapping of data frames.")
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, obj in tables.items():
        file_path = outdir / f"{_safe_filename(prefix)}_{_safe_filename(name)}.csv"
        if not isinstance(obj, pd.DataFrame):
            rows.append({"table": name, "file": str(file_path), "n_rows": np.nan, "n_columns": np.nan,
                         "written": False, "skipped_reason": "not_a_data_frame"})
            continue
        message_only = list(obj.columns) == ["message"]
        if message_only and not include_empty_message_tables:
            rows.append({"table": name, "file": str(file_path), "n_rows": len(obj), "n_columns": obj.shape[1],
                         "written": False, "skipped_reason": "message_only_table"})
            continue
        if file_path.exists() and not overwrite:
            rows.append({"table": name, "file": str(file_path), "n_rows": len(obj), "n_columns": obj.shape[1],
                         "written": False, "skipped_reason": "file_exists"})
            continue
        obj.to_csv(file_path, index=False)
        rows.append({"table": name, "file": str(file_path), "n_rows": len(obj), "n_columns": obj.shape[1],
                     "written": True, "skipped_reason": None})
    return pd.DataFrame(rows)


def export_gazepoint_biometrics_report_bundle(bundle=None, output_dir=None, prefix="gpbiometrics_report", tables=None, text=None, plots=None, include_readme=True, include_session_info=True, overwrite=False):
    if output_dir is None:
        raise ValueError("`output_dir` must be supplied.")
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    if bundle is not None and isinstance(bundle, dict):
        tables = tables or bundle.get("tables")
        text = text or bundle.get("text")
        plots = plots or bundle.get("plots")
    tables = tables or {}
    text = text or {}
    plots = plots or {}
    manifest = []
    def _guard(p):
        if p.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {p}")
    for name, obj in tables.items():
        if not isinstance(obj, pd.DataFrame):
            continue
        p = outdir / f"{prefix}_tables_{_safe_filename(name)}.csv"
        _guard(p); obj.to_csv(p, index=False); manifest.append({"item": f"table:{name}", "path": str(p)})
    for name, lines in text.items():
        p = outdir / f"{prefix}_text_{_safe_filename(name)}.txt"
        _guard(p); p.write_text("\n".join(str(x) for x in (lines if isinstance(lines, (list, tuple)) else [lines]))); manifest.append({"item": f"text:{name}", "path": str(p)})
    for name, fig in plots.items():
        if isinstance(fig, Figure):
            p = outdir / f"{prefix}_plot_{_safe_filename(name)}.png"
            _guard(p); fig.savefig(p, dpi=150, bbox_inches="tight"); manifest.append({"item": f"plot:{name}", "path": str(p)})
    if include_readme:
        p = outdir / f"{prefix}_README.txt"; _guard(p)
        p.write_text("gpbiometrics report bundle\nBiometric outputs require conservative interpretation.\n")
        manifest.append({"item": "README", "path": str(p)})
    if include_session_info:
        p = outdir / f"{prefix}_session_info.txt"; _guard(p)
        p.write_text(f"Python {platform.python_version()}\nPlatform {platform.platform()}\n")
        manifest.append({"item": "session_info", "path": str(p)})
    manifest_path = outdir / f"{prefix}_manifest.csv"
    _guard(manifest_path)
    pd.DataFrame(manifest).to_csv(manifest_path, index=False)
    manifest.append({"item": "manifest", "path": str(manifest_path)})
    return {"overview": pd.DataFrame([{"status": "bundle_exported", "files_written": len(manifest)}]),
            "manifest": pd.DataFrame(manifest), "output_dir": str(outdir),
            "_class": "gazepoint_biometrics_report_bundle"}


def create_gazepoint_biometrics_report(data=None, workflow=None, validation=None, quality=None, sampling=None, missingness=None, exclusions=None, report_tables=None, methods_text=None, checklist=None, title="Gazepoint Biometrics report", subtitle=None, output_file=None, format="markdown", include_timestamp=False, overwrite=False, max_table_rows=20):
    if report_tables is None:
        report_tables = create_gazepoint_biometrics_report_tables(
            workflow=workflow, validation=validation, quality=quality, sampling=sampling,
            diagnostics=workflow.get("diagnostics") if isinstance(workflow, dict) else None,
            exclusion_recommendations=exclusions,
            ttl_events=workflow.get("ttl_events") if isinstance(workflow, dict) else None,
            max_ttl_events=max_table_rows,
        )
    if data is None and isinstance(workflow, dict):
        data = workflow.get("data", workflow.get("biometrics"))
    if checklist is None and isinstance(data, pd.DataFrame):
        checklist = create_gazepoint_biometrics_checklist(data)
    if methods_text is None and checklist is not None:
        methods_text = create_gazepoint_biometrics_methods_text(checklist=checklist)
    lines = [f"# {title}"] + ([subtitle] if subtitle else []) + ["", methods_text or ""]
    for name, table in report_tables.items():
        if isinstance(table, pd.DataFrame):
            lines.extend([f"\n## {name.replace('_', ' ').title()}", table.head(int(max_table_rows)).to_string(index=False)])
    content = "\n".join(lines)
    if output_file:
        p = Path(output_file)
        if p.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return {"content": content, "tables": report_tables,
            "overview": pd.DataFrame([{"status": "report_created", "format": format,
                                       "output_file": str(output_file) if output_file else None}]),
            "_class": "gazepoint_biometrics_report"}
