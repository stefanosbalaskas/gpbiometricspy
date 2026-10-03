from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy import signal
from scipy.special import expit
from scipy.optimize import minimize

from .deterministic_extensions import assess_gazepoint_hrp_waveform_quality

_SCHEMA_VERSION = "gpbiometricspy-ppg-pigmentation-equity-v1"
_OBJECTIVE_METRICS = {"ita", "cielab", "melanin_index"}
_SUBJECTIVE_METRICS = {"monk", "fitzpatrick", "pantone", "von_luschan"}
_PROXY_METRICS = {"race", "ethnicity"}
_METRIC_ALIASES = {
    "individual_typology_angle": "ita",
    "individual_typology_angle_degrees": "ita",
    "cie_lab": "cielab",
    "cielab": "cielab",
    "melanin": "melanin_index",
    "melanin_index": "melanin_index",
    "monk_skin_tone": "monk",
    "fitzpatrick_skin_type": "fitzpatrick",
    "von_luschan_scale": "von_luschan",
}


def _frame(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("`data` must be a pandas DataFrame.")
    if data.empty:
        raise ValueError("`data` must contain at least one row.")
    return data


def _metric_name(metric: str) -> str:
    if not isinstance(metric, str) or not metric.strip():
        raise ValueError("`metric` must be a non-empty string.")
    key = metric.strip().lower().replace("-", "_").replace(" ", "_")
    key = _METRIC_ALIASES.get(key, key)
    allowed = _OBJECTIVE_METRICS | _SUBJECTIVE_METRICS | _PROXY_METRICS
    if key not in allowed:
        raise ValueError(f"Unsupported pigmentation metric {metric!r}; choose one of {sorted(allowed)}.")
    return key


def _require_columns(data: pd.DataFrame, columns: Iterable[str | None]) -> None:
    missing = [c for c in columns if c is not None and c not in data.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))


def _metadata_series(data: pd.DataFrame, value, name: str) -> pd.Series:
    if value is None:
        return pd.Series([pd.NA] * len(data), index=data.index, dtype="object")
    if isinstance(value, str) and value in data.columns:
        return data[value].astype("object")
    if isinstance(value, (pd.Series, np.ndarray, list, tuple)) and not isinstance(value, str):
        if len(value) != len(data):
            raise ValueError(f"`{name}` must have the same length as `data`.")
        return pd.Series(value, index=data.index, dtype="object")
    return pd.Series([value] * len(data), index=data.index, dtype="object")


def _ita_category(values: np.ndarray) -> np.ndarray:
    out = np.full(values.shape, None, dtype=object)
    finite = np.isfinite(values)
    v = values[finite]
    labels = np.where(
        v > 55,
        "very_light",
        np.where(v > 41, "light", np.where(v > 28, "intermediate", np.where(v > 10, "tan", np.where(v > -30, "brown", "dark")))),
    )
    out[finite] = labels
    return out


def compute_skin_ita(l_star, b_star, *, classify: bool = False) -> pd.DataFrame:
    """Compute Individual Typology Angle (ITA) from CIELAB L* and b* values.

    The continuous ITA is primary. Conventional presentation categories are
    optional and should not be treated as interchangeable with Monk,
    Fitzpatrick, race, ethnicity, or melanin-index measurements.
    """
    l_raw, b_raw = np.broadcast_arrays(np.asarray(l_star), np.asarray(b_star))
    l = pd.to_numeric(pd.Series(l_raw.ravel()), errors="coerce").to_numpy(float)
    b = pd.to_numeric(pd.Series(b_raw.ravel()), errors="coerce").to_numpy(float)
    valid = np.isfinite(l) & np.isfinite(b) & (l >= 0) & (l <= 100)
    ratio = np.full(l.shape, np.nan, dtype=float)
    nonzero = valid & (b != 0)
    ratio[nonzero] = (l[nonzero] - 50.0) / b[nonzero]
    zero_b = valid & (b == 0)
    ratio[zero_b & (l > 50)] = np.inf
    ratio[zero_b & (l < 50)] = -np.inf
    ita = np.degrees(np.arctan(ratio))
    status = np.full(l.shape, "ok", dtype=object)
    status[~np.isfinite(l) | ~np.isfinite(b)] = "missing_or_nonfinite"
    status[np.isfinite(l) & ((l < 0) | (l > 100))] = "invalid_l_star"
    status[zero_b & (l != 50)] = "b_star_zero_limit"
    status[zero_b & (l == 50)] = "undefined_zero_over_zero"
    result = pd.DataFrame({"l_star": l, "b_star": b, "ita_degrees": ita, "status": status})
    if classify:
        result["ita_category"] = _ita_category(ita)
    return result


def validate_skin_pigmentation_metadata(
    data: pd.DataFrame,
    *,
    metric: str,
    pigmentation_col: str | None = None,
    l_star_col: str | None = None,
    a_star_col: str | None = None,
    b_star_col: str | None = None,
    method=None,
    measurement_site=None,
    sensor_site=None,
    instrument_manufacturer=None,
    instrument_model=None,
    assessor=None,
    missing_reason_col: str | None = None,
) -> dict:
    """Validate pigmentation metadata without converting demographic proxies into optical measurements."""
    data = _frame(data)
    metric = _metric_name(metric)
    _require_columns(data, [pigmentation_col, l_star_col, a_star_col, b_star_col, missing_reason_col])
    warnings: list[str] = []

    if metric == "cielab":
        if l_star_col is None or b_star_col is None:
            raise ValueError("`cielab` requires both `l_star_col` and `b_star_col`.")
        calc = compute_skin_ita(data[l_star_col], data[b_star_col], classify=True)
        values = calc["ita_degrees"].to_numpy(float)
        categories = calc["ita_category"].to_numpy(object)
        value_status = calc["status"].to_numpy(object)
        analysis_metric = "ita"
    else:
        if pigmentation_col is None:
            raise ValueError(f"`pigmentation_col` is required for metric {metric!r}.")
        raw = data[pigmentation_col]
        if metric in _OBJECTIVE_METRICS:
            values = pd.to_numeric(raw, errors="coerce").to_numpy(float)
        else:
            values = raw.astype("object").to_numpy()
        if metric == "ita":
            numeric = pd.to_numeric(raw, errors="coerce").to_numpy(float)
            categories = _ita_category(numeric)
            value_status = np.where(np.isfinite(numeric), "ok", "missing_or_nonfinite").astype(object)
            values = numeric
        else:
            categories = raw.astype("object").where(raw.notna(), pd.NA).to_numpy()
            value_status = np.where(raw.notna(), "ok", "missing_or_nonfinite").astype(object)
        analysis_metric = metric

    evidence_class = "objective" if metric in _OBJECTIVE_METRICS else ("subjective" if metric in _SUBJECTIVE_METRICS else "proxy")
    if evidence_class == "proxy":
        warnings.append("race_or_ethnicity_is_not_an_optical_pigmentation_measurement")

    measure_site = _metadata_series(data, measurement_site, "measurement_site")
    sensor_site_s = _metadata_series(data, sensor_site, "sensor_site")
    method_s = _metadata_series(data, method, "method")
    manufacturer_s = _metadata_series(data, instrument_manufacturer, "instrument_manufacturer")
    model_s = _metadata_series(data, instrument_model, "instrument_model")
    assessor_s = _metadata_series(data, assessor, "assessor")

    site_match = pd.Series([pd.NA] * len(data), index=data.index, dtype="object")
    have_sites = measure_site.notna() & sensor_site_s.notna()
    if have_sites.any():
        site_match.loc[have_sites] = (
            measure_site.loc[have_sites].astype(str).str.strip().str.lower().to_numpy()
            == sensor_site_s.loc[have_sites].astype(str).str.strip().str.lower().to_numpy()
        )
    if not have_sites.all():
        warnings.append("measurement_site_or_sensor_site_missing_for_some_rows")

    if missing_reason_col is None:
        missing_reason = pd.Series([pd.NA] * len(data), index=data.index, dtype="object")
    else:
        missing_reason = data[missing_reason_col].astype("object")

    if metric in _OBJECTIVE_METRICS:
        missing_value = ~np.isfinite(pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float))
    else:
        missing_value = pd.isna(values)
    missing_reason.loc[missing_value & missing_reason.isna()] = "unknown"

    row_status = np.asarray(value_status, dtype=object).copy()
    measured = ~missing_value
    row_status[measured] = f"{evidence_class}_measured"
    if evidence_class == "proxy":
        row_status[measured] = "proxy_not_pigmentation"

    normalized = pd.DataFrame(
        {
            "source_index": data.index,
            "pigmentation_value": values,
            "pigmentation_metric": analysis_metric,
            "evidence_class": evidence_class,
            "objective": evidence_class == "objective",
            "ita_category": categories if analysis_metric == "ita" else pd.Series(categories, dtype="object"),
            "measurement_method": method_s.to_numpy(),
            "measurement_site": measure_site.to_numpy(),
            "sensor_site": sensor_site_s.to_numpy(),
            "site_match": site_match.to_numpy(),
            "instrument_manufacturer": manufacturer_s.to_numpy(),
            "instrument_model": model_s.to_numpy(),
            "assessor": assessor_s.to_numpy(),
            "missing_reason": missing_reason.to_numpy(),
            "status": row_status,
        }
    )
    if l_star_col is not None:
        normalized["l_star"] = pd.to_numeric(data[l_star_col], errors="coerce").to_numpy(float)
    if a_star_col is not None:
        normalized["a_star"] = pd.to_numeric(data[a_star_col], errors="coerce").to_numpy(float)
    if b_star_col is not None:
        normalized["b_star"] = pd.to_numeric(data[b_star_col], errors="coerce").to_numpy(float)

    n_measured = int((~missing_value).sum())
    evidence = "not_measured_proxy_only" if evidence_class == "proxy" else (evidence_class if n_measured else "not_measured")
    overview = pd.DataFrame(
        [
            {
                "rows": len(data),
                "measured_rows": n_measured,
                "missing_rows": int(missing_value.sum()),
                "metric": analysis_metric,
                "evidence_class": evidence_class,
                "pigmentation_evidence": evidence,
                "site_match_known_rows": int(have_sites.sum()),
                "site_match_rows": int((site_match == True).sum()),
                "status": "proxy_only" if evidence_class == "proxy" else ("complete" if n_measured == len(data) else "partial"),
            }
        ]
    )
    missingness = (
        normalized.loc[missing_value, "missing_reason"].astype("object").fillna("unknown").value_counts(dropna=False).rename_axis("missing_reason").reset_index(name="n")
    )
    return {
        "overview": overview,
        "normalized": normalized,
        "missingness": missingness,
        "warnings": tuple(dict.fromkeys(warnings)),
        "settings": {
            "metric": metric,
            "analysis_metric": analysis_metric,
            "pigmentation_col": pigmentation_col,
            "l_star_col": l_star_col,
            "a_star_col": a_star_col,
            "b_star_col": b_star_col,
            "missing_reason_col": missing_reason_col,
        },
    }


def _sampling_rate(group: pd.DataFrame, time_col: str | None, sampling_rate_hz: float | None) -> float | None:
    if sampling_rate_hz is not None:
        fs = float(sampling_rate_hz)
        if not np.isfinite(fs) or fs <= 0:
            raise ValueError("`sampling_rate_hz` must be a finite positive number.")
        return fs
    if time_col is None or time_col not in group.columns:
        return None
    t = pd.to_numeric(group[time_col], errors="coerce").to_numpy(float)
    d = np.diff(t[np.isfinite(t)])
    d = d[d > 0]
    if not len(d):
        return None
    dt = float(np.median(d))
    if dt > 5:
        dt /= 1000.0
    return 1.0 / dt if dt > 0 else None


def _template_correlation(x: np.ndarray, fs: float | None) -> float:
    finite = np.isfinite(x)
    if fs is None or finite.sum() < max(20, int(fs * 2)):
        return np.nan
    y = pd.Series(x).interpolate(limit_direction="both").to_numpy(float)
    y = signal.detrend(y)
    peaks, _ = signal.find_peaks(y, distance=max(1, int(fs * 0.3)), prominence=max(np.std(y) * 0.1, 1e-12))
    before, after = int(round(0.25 * fs)), int(round(0.45 * fs))
    beats = []
    for p in peaks:
        if p - before < 0 or p + after >= len(y):
            continue
        beat = y[p - before : p + after + 1]
        grid = np.linspace(0, 1, 101)
        beats.append(np.interp(grid, np.linspace(0, 1, len(beat)), beat))
    if len(beats) < 2:
        return np.nan
    beat_matrix = np.vstack(beats)
    template = np.median(beat_matrix, axis=0)
    corrs = []
    for beat in beat_matrix:
        if np.std(beat) == 0 or np.std(template) == 0:
            continue
        corrs.append(float(np.corrcoef(beat, template)[0, 1]))
    return float(np.mean(corrs)) if corrs else np.nan


def _ppg_sqi(x: np.ndarray, fs: float | None, flat_tolerance: float) -> dict:
    x = np.asarray(x, dtype=float)
    finite = np.isfinite(x)
    vals = x[finite]
    finite_prop = float(finite.mean()) if len(x) else np.nan
    missing_prop = 1.0 - finite_prop if np.isfinite(finite_prop) else np.nan
    if len(vals):
        q05, q95 = np.quantile(vals, [0.05, 0.95])
        ac = float((q95 - q05) / 2.0)
        dc = float(np.median(vals))
        ac_dc = ac / abs(dc) if dc != 0 else np.nan
    else:
        ac = dc = ac_dc = np.nan
    flat_prop = float(np.mean(np.abs(np.diff(vals)) <= flat_tolerance)) if len(vals) > 1 else np.nan
    snr_db = np.nan
    if fs is not None and len(vals) >= 16:
        y = pd.Series(x).interpolate(limit_direction="both").to_numpy(float)
        y = signal.detrend(y)
        freq, power = signal.welch(y, fs=fs, nperseg=min(256, len(y)))
        band = (freq >= 0.5) & (freq <= min(5.0, fs / 2.0 * 0.95))
        if band.any() and np.any(power[band] > 0):
            peak_frequency = float(freq[band][np.argmax(power[band])])
            pulse = band & (np.abs(freq - peak_frequency) <= 0.15)
            noise = band & ~pulse
            signal_power = float(np.sum(power[pulse]))
            noise_power = float(np.sum(power[noise]))
            if signal_power > 0 and noise_power > 0:
                snr_db = 10.0 * np.log10(signal_power / noise_power)
    return {
        "finite_prop": finite_prop,
        "missing_prop": missing_prop,
        "ac_amplitude": ac,
        "dc_level": dc,
        "ac_dc_ratio": ac_dc,
        "flat_prop_sqi": flat_prop,
        "ppg_snr_db": snr_db,
        "template_correlation": _template_correlation(x, fs),
    }


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.var(x) == 0:
        return np.nan
    return float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1))


def _cluster_bootstrap_slope(frame: pd.DataFrame, x_col: str, y_col: str, cluster_col: str, n_boot: int, rng: np.random.Generator) -> dict:
    x = pd.to_numeric(frame[x_col], errors="coerce")
    y = pd.to_numeric(frame[y_col], errors="coerce")
    keep = x.notna() & y.notna() & frame[cluster_col].notna()
    d = frame.loc[keep, [x_col, y_col, cluster_col]].copy()
    d[x_col] = pd.to_numeric(d[x_col], errors="coerce")
    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    clusters = pd.unique(d[cluster_col])
    estimate = _slope(d[x_col].to_numpy(float), d[y_col].to_numpy(float))
    boots = []
    if len(clusters) >= 2 and n_boot > 0:
        groups = {c: d[d[cluster_col] == c] for c in clusters}
        for _ in range(int(n_boot)):
            sampled = rng.choice(clusters, size=len(clusters), replace=True)
            b = pd.concat([groups[c] for c in sampled], ignore_index=True)
            val = _slope(b[x_col].to_numpy(float), b[y_col].to_numpy(float))
            if np.isfinite(val):
                boots.append(val)
    lo, hi = (np.quantile(boots, [0.025, 0.975]) if boots else (np.nan, np.nan))
    return {
        "outcome": y_col,
        "estimate": estimate,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_rows": len(d),
        "n_clusters": len(clusters),
        "method": "participant_cluster_bootstrap_linear_slope",
    }


def _strata_summary(frame: pd.DataFrame, participant_col: str, category_col: str) -> pd.DataFrame:
    rows = []
    for category, g in frame.groupby(category_col, dropna=False, sort=False):
        rows.append(
            {
                "pigmentation_category": category,
                "n_participants": int(g[participant_col].nunique(dropna=True)),
                "n_groups": len(g),
                "finite_prop_mean": float(g["finite_prop"].mean()),
                "missing_prop_mean": float(g["missing_prop"].mean()),
                "retention_rate": float(g["quality_retained"].mean()),
                "ppg_snr_db_mean": float(g["ppg_snr_db"].mean()) if g["ppg_snr_db"].notna().any() else np.nan,
                "ac_dc_ratio_mean": float(g["ac_dc_ratio"].mean()) if g["ac_dc_ratio"].notna().any() else np.nan,
                "template_correlation_mean": float(g["template_correlation"].mean()) if g["template_correlation"].notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_ppg_quality_by_pigmentation(
    data: pd.DataFrame,
    *,
    participant_col: str,
    ppg_col: str,
    pigmentation_col: str,
    pigmentation_metric: str = "ita",
    time_col: str | None = None,
    group_cols: Iterable[str] | None = None,
    sampling_rate_hz: float | None = None,
    min_rows: int = 20,
    min_finite_prop: float = 0.80,
    max_flat_prop: float = 0.95,
    flat_tolerance: float = 1e-8,
    max_gap_multiplier: float = 3.0,
    n_boot: int = 1000,
    random_state: int | None = 0,
) -> dict:
    """Audit PPG quality, missingness, and QC retention against measured pigmentation."""
    data = _frame(data)
    pigmentation_metric = _metric_name(pigmentation_metric)
    if pigmentation_metric == "cielab":
        raise ValueError("Use `validate_skin_pigmentation_metadata()` or `ppg_pigmentation_audit()` to derive ITA from CIELAB before quality stratification.")
    _require_columns(data, [participant_col, ppg_col, pigmentation_col, time_col])
    extra = [] if group_cols is None else list(group_cols)
    _require_columns(data, extra)
    grouping = list(dict.fromkeys([participant_col, *extra]))
    work = data.copy()
    if pigmentation_metric in _OBJECTIVE_METRICS:
        work[pigmentation_col] = pd.to_numeric(work[pigmentation_col], errors="coerce")
    if pigmentation_metric == "ita":
        work["_pigmentation_category"] = _ita_category(pd.to_numeric(work[pigmentation_col], errors="coerce").to_numpy(float))
    else:
        work["_pigmentation_category"] = work[pigmentation_col].astype("object")

    rows = []
    grouped = work.groupby(grouping, dropna=False, sort=False) if grouping else [("all", work)]
    for key, g in grouped:
        base = assess_gazepoint_hrp_waveform_quality(
            g,
            hrp_col=ppg_col,
            time_col=time_col,
            group_cols=None,
            sampling_rate=sampling_rate_hz,
            min_rows=min_rows,
            min_finite_prop=min_finite_prop,
            max_flat_prop=max_flat_prop,
            flat_tolerance=flat_tolerance,
            max_gap_multiplier=max_gap_multiplier,
        )
        quality = base["group_quality"].iloc[0]
        fs = _sampling_rate(g, time_col, sampling_rate_hz)
        sqi = _ppg_sqi(pd.to_numeric(g[ppg_col], errors="coerce").to_numpy(float), fs, flat_tolerance)
        values = g[pigmentation_col].dropna()
        categories = g["_pigmentation_category"].dropna()
        row = {}
        key_tuple = key if isinstance(key, tuple) else (key,)
        for col, val in zip(grouping, key_tuple):
            row[col] = val
        row.update(
            {
                "n_rows": len(g),
                "pigmentation_value": values.iloc[0] if len(values) else np.nan,
                "pigmentation_category": categories.iloc[0] if len(categories) else pd.NA,
                "pigmentation_consistent_within_group": values.nunique(dropna=True) <= 1,
                "quality_status": quality["status"],
                "quality_retained": not str(quality["status"]).startswith("fail"),
                "sampling_rate_hz": fs,
                **sqi,
            }
        )
        rows.append(row)
    group_quality = pd.DataFrame(rows)
    warnings = []
    if not group_quality["pigmentation_consistent_within_group"].all():
        warnings.append("pigmentation_varies_within_one_or_more_analysis_groups")
    n_participants = int(group_quality[participant_col].nunique(dropna=True))
    if n_participants < 5:
        warnings.append("fewer_than_five_participants_limits_stratified_inference")

    strata = _strata_summary(group_quality, participant_col, "pigmentation_category")
    associations = pd.DataFrame()
    continuous = pigmentation_metric in _OBJECTIVE_METRICS
    if continuous:
        rng = np.random.default_rng(random_state)
        assoc_rows = []
        for outcome in ["finite_prop", "missing_prop", "quality_retained", "ppg_snr_db", "ac_dc_ratio", "template_correlation"]:
            assoc_rows.append(_cluster_bootstrap_slope(group_quality, "pigmentation_value", outcome, participant_col, n_boot, rng))
        associations = pd.DataFrame(assoc_rows)
    overview = pd.DataFrame(
        [
            {
                "n_participants": n_participants,
                "n_groups": len(group_quality),
                "retained_groups": int(group_quality["quality_retained"].sum()),
                "retention_rate": float(group_quality["quality_retained"].mean()),
                "pigmentation_metric": pigmentation_metric,
                "continuous_associations_run": continuous,
                "status": "qualified" if warnings else "complete",
            }
        ]
    )
    reporting_text = (
        "PPG acquisition quality, missingness, and QC retention were audited against the supplied pigmentation measurement. "
        "Continuous association estimates use participant-cluster bootstrap uncertainty when an objective metric is available. "
        "These associations are observational and do not establish melanin or pigmentation as the causal source of a measurement difference."
    )
    return {
        "overview": overview,
        "group_quality": group_quality,
        "strata_summary": strata,
        "associations": associations,
        "warnings": tuple(warnings),
        "reporting_text": reporting_text,
        "settings": {
            "participant_col": participant_col,
            "ppg_col": ppg_col,
            "pigmentation_col": pigmentation_col,
            "pigmentation_metric": pigmentation_metric,
            "time_col": time_col,
            "group_cols": extra,
            "sampling_rate_hz": sampling_rate_hz,
            "n_boot": int(n_boot),
        },
    }


def _ccc(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return np.nan
    vx, vy = np.var(x, ddof=1), np.var(y, ddof=1)
    den = vx + vy + (np.mean(x) - np.mean(y)) ** 2
    return float(2 * np.cov(x, y, ddof=1)[0, 1] / den) if den > 0 else np.nan


def _agreement_metrics(d: pd.DataFrame, reference_col: str, candidate_col: str, participant_col: str) -> dict:
    ref = pd.to_numeric(d[reference_col], errors="coerce").to_numpy(float)
    cand = pd.to_numeric(d[candidate_col], errors="coerce").to_numpy(float)
    valid_ref = np.isfinite(ref)
    paired = valid_ref & np.isfinite(cand)
    diff = cand[paired] - ref[paired]
    bias = float(np.mean(diff)) if len(diff) else np.nan
    sd = float(np.std(diff, ddof=1)) if len(diff) > 1 else np.nan
    return {
        "n_rows": len(d),
        "n_participants": int(d[participant_col].nunique(dropna=True)),
        "reference_available": int(valid_ref.sum()),
        "n_pairs": int(paired.sum()),
        "retention_rate": float(paired.sum() / valid_ref.sum()) if valid_ref.sum() else np.nan,
        "bias": bias,
        "mae": float(np.mean(np.abs(diff))) if len(diff) else np.nan,
        "rmse": float(np.sqrt(np.mean(diff**2))) if len(diff) else np.nan,
        "loa_lower": bias - 1.96 * sd if np.isfinite(sd) else np.nan,
        "loa_upper": bias + 1.96 * sd if np.isfinite(sd) else np.nan,
        "lin_ccc": _ccc(ref[paired], cand[paired]) if paired.sum() >= 2 else np.nan,
    }


def _cluster_bootstrap_agreement(d: pd.DataFrame, reference_col: str, candidate_col: str, participant_col: str, n_boot: int, rng: np.random.Generator) -> pd.DataFrame:
    clusters = pd.unique(d[participant_col].dropna())
    targets = ["retention_rate", "bias", "mae", "rmse", "lin_ccc"]
    draws = {name: [] for name in targets}
    if len(clusters) >= 2 and n_boot > 0:
        groups = {c: d[d[participant_col] == c] for c in clusters}
        for _ in range(int(n_boot)):
            sampled = rng.choice(clusters, size=len(clusters), replace=True)
            b = pd.concat([groups[c] for c in sampled], ignore_index=True)
            m = _agreement_metrics(b, reference_col, candidate_col, participant_col)
            for name in targets:
                if np.isfinite(m[name]):
                    draws[name].append(m[name])
    rows = []
    point = _agreement_metrics(d, reference_col, candidate_col, participant_col)
    for name in targets:
        lo, hi = (np.quantile(draws[name], [0.025, 0.975]) if draws[name] else (np.nan, np.nan))
        rows.append({"metric": name, "estimate": point[name], "ci_low": float(lo), "ci_high": float(hi), "method": "participant_cluster_bootstrap"})
    return pd.DataFrame(rows)


def _logit_slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) == 0 or len(np.unique(y)) < 2:
        return np.nan
    mean_x, sd_x = float(np.mean(x)), float(np.std(x, ddof=0))
    z = (x - mean_x) / sd_x
    design = np.column_stack([np.ones(len(z)), z])

    def objective(beta):
        p = np.clip(expit(design @ beta), 1e-12, 1 - 1e-12)
        return float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)) + 1e-8 * np.sum(beta**2))

    fit = minimize(objective, np.zeros(2), method="BFGS")
    return float(fit.x[1] / sd_x) if fit.success else np.nan


def _cluster_bootstrap_retention_logit(frame: pd.DataFrame, x_col: str, retained_col: str, cluster_col: str, n_boot: int, rng: np.random.Generator) -> dict:
    x = pd.to_numeric(frame[x_col], errors="coerce")
    y = pd.to_numeric(frame[retained_col], errors="coerce")
    keep = x.notna() & y.notna() & frame[cluster_col].notna()
    d = frame.loc[keep, [x_col, retained_col, cluster_col]].copy()
    d[x_col] = pd.to_numeric(d[x_col], errors="coerce")
    d[retained_col] = pd.to_numeric(d[retained_col], errors="coerce")
    beta = _logit_slope(d[x_col].to_numpy(float), d[retained_col].to_numpy(float))
    clusters = pd.unique(d[cluster_col])
    boots = []
    if len(clusters) >= 2 and n_boot > 0:
        groups = {c: d[d[cluster_col] == c] for c in clusters}
        for _ in range(int(n_boot)):
            sampled = rng.choice(clusters, size=len(clusters), replace=True)
            b = pd.concat([groups[c] for c in sampled], ignore_index=True)
            val = _logit_slope(b[x_col].to_numpy(float), b[retained_col].to_numpy(float))
            if np.isfinite(val):
                boots.append(val)
    if boots:
        odds = np.exp(np.asarray(boots) * 10.0)
        lo, hi = np.quantile(odds, [0.025, 0.975])
    else:
        lo = hi = np.nan
    return {
        "outcome": "retained_measurement",
        "estimate_log_odds_per_unit": beta,
        "odds_ratio_per_10_units": float(np.exp(beta * 10.0)) if np.isfinite(beta) else np.nan,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_rows": len(d),
        "n_clusters": len(clusters),
        "method": "participant_cluster_bootstrap_logistic",
    }


def compare_ppg_reference_by_pigmentation(
    data: pd.DataFrame,
    *,
    participant_col: str,
    reference_col: str,
    candidate_col: str,
    pigmentation_col: str,
    pigmentation_metric: str = "ita",
    metric_name: str = "heart_rate",
    device_col: str | None = None,
    condition_col: str | None = None,
    n_boot: int = 1000,
    random_state: int | None = 0,
) -> dict:
    """Compare a PPG-derived measure with a reference while auditing pigmentation-linked retention and error."""
    data = _frame(data)
    pigmentation_metric = _metric_name(pigmentation_metric)
    if pigmentation_metric == "cielab":
        raise ValueError("Use `validate_skin_pigmentation_metadata()` or `ppg_pigmentation_audit()` to derive ITA from CIELAB before reference comparison.")
    _require_columns(data, [participant_col, reference_col, candidate_col, pigmentation_col, device_col, condition_col])
    work = data.copy()
    work["_pigmentation_numeric"] = pd.to_numeric(work[pigmentation_col], errors="coerce")
    work["_pigmentation_category"] = (
        _ita_category(work["_pigmentation_numeric"].to_numpy(float)) if pigmentation_metric == "ita" else work[pigmentation_col].astype("object").to_numpy()
    )
    ref = pd.to_numeric(work[reference_col], errors="coerce").to_numpy(float)
    cand = pd.to_numeric(work[candidate_col], errors="coerce").to_numpy(float)
    work["_reference_available"] = np.isfinite(ref)
    work["_retained"] = np.isfinite(ref) & np.isfinite(cand)
    work["_signed_error"] = np.where(work["_retained"], cand - ref, np.nan)
    work["_abs_error"] = np.abs(work["_signed_error"])

    strata_cols = [c for c in [device_col, condition_col] if c is not None]
    grouping = strata_cols
    summary_rows = []
    ci_parts = []
    rng = np.random.default_rng(random_state)
    if grouping:
        iterator = work.groupby(grouping, dropna=False, sort=False)
    else:
        iterator = [("all", work)]
    for key, g in iterator:
        key_tuple = key if isinstance(key, tuple) else (key,)
        labels = {col: val for col, val in zip(grouping, key_tuple)}
        summary_rows.append({**labels, **_agreement_metrics(g, reference_col, candidate_col, participant_col)})
        ci = _cluster_bootstrap_agreement(g, reference_col, candidate_col, participant_col, n_boot, rng)
        for col, val in labels.items():
            ci[col] = val
        ci_parts.append(ci)
    agreement = pd.DataFrame(summary_rows)
    agreement_ci = pd.concat(ci_parts, ignore_index=True) if ci_parts else pd.DataFrame()

    category_rows = []
    category_grouping = [*strata_cols, "_pigmentation_category"]
    for key, g in work.groupby(category_grouping, dropna=False, sort=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        labels = {col: val for col, val in zip(category_grouping, key_tuple)}
        labels["pigmentation_category"] = labels.pop("_pigmentation_category")
        category_rows.append({**labels, **_agreement_metrics(g, reference_col, candidate_col, participant_col)})
    category_summary = pd.DataFrame(category_rows)

    association_rows = []
    retention_association = pd.DataFrame()
    continuous = pigmentation_metric in _OBJECTIVE_METRICS
    if continuous:
        for outcome in ["_signed_error", "_abs_error"]:
            row = _cluster_bootstrap_slope(work, "_pigmentation_numeric", outcome, participant_col, n_boot, rng)
            row["outcome"] = "signed_error" if outcome == "_signed_error" else "absolute_error"
            association_rows.append(row)
        denominator = work[work["_reference_available"]].copy()
        retention_association = pd.DataFrame([
            _cluster_bootstrap_retention_logit(denominator, "_pigmentation_numeric", "_retained", participant_col, n_boot, rng)
        ])
    associations = pd.DataFrame(association_rows)
    warnings = []
    n_participants = int(work[participant_col].nunique(dropna=True))
    if n_participants < 5:
        warnings.append("fewer_than_five_participants_limits_reference_validation")
    if not continuous:
        warnings.append("continuous_association_models_not_run_for_nonobjective_pigmentation_metric")
    reporting_text = (
        f"{metric_name} reference agreement was evaluated separately from measurement retention. Bias, MAE, RMSE, Lin's CCC, and Bland-Altman limits describe paired measurements, while retention uses all rows with an available reference. "
        "Participant-cluster bootstrap intervals account for repeated observations. Pigmentation associations are observational and do not establish a causal optical mechanism."
    )
    return {
        "overview": pd.DataFrame([
            {
                "metric_name": metric_name,
                "n_rows": len(work),
                "n_participants": n_participants,
                "reference_available": int(work["_reference_available"].sum()),
                "paired_measurements": int(work["_retained"].sum()),
                "pigmentation_metric": pigmentation_metric,
                "status": "qualified" if warnings else "complete",
            }
        ]),
        "agreement": agreement,
        "agreement_ci": agreement_ci,
        "category_summary": category_summary,
        "associations": associations,
        "retention_association": retention_association,
        "row_level": work,
        "warnings": tuple(warnings),
        "reporting_text": reporting_text,
        "settings": {
            "participant_col": participant_col,
            "reference_col": reference_col,
            "candidate_col": candidate_col,
            "pigmentation_col": pigmentation_col,
            "pigmentation_metric": pigmentation_metric,
            "device_col": device_col,
            "condition_col": condition_col,
            "n_boot": int(n_boot),
        },
    }


def ppg_pigmentation_audit(
    data: pd.DataFrame,
    *,
    participant_col: str,
    ppg_col: str,
    pigmentation_metric: str,
    pigmentation_col: str | None = None,
    l_star_col: str | None = None,
    a_star_col: str | None = None,
    b_star_col: str | None = None,
    pigmentation_method=None,
    pigmentation_site=None,
    sensor_site=None,
    instrument_manufacturer=None,
    instrument_model=None,
    assessor=None,
    missing_reason_col: str | None = None,
    time_col: str | None = None,
    group_cols: Iterable[str] | None = None,
    sampling_rate_hz: float | None = None,
    reference_col: str | None = None,
    candidate_col: str | None = None,
    metric_name: str = "heart_rate",
    device_col: str | None = None,
    condition_col: str | None = None,
    n_boot: int = 1000,
    random_state: int | None = 0,
) -> dict:
    """Run the integrated PPG Pigmentation & Measurement-Equity Audit."""
    data = _frame(data)
    _require_columns(data, [participant_col, ppg_col, time_col, reference_col, candidate_col, device_col, condition_col])
    metadata = validate_skin_pigmentation_metadata(
        data,
        metric=pigmentation_metric,
        pigmentation_col=pigmentation_col,
        l_star_col=l_star_col,
        a_star_col=a_star_col,
        b_star_col=b_star_col,
        method=pigmentation_method,
        measurement_site=pigmentation_site,
        sensor_site=sensor_site,
        instrument_manufacturer=instrument_manufacturer,
        instrument_model=instrument_model,
        assessor=assessor,
        missing_reason_col=missing_reason_col,
    )
    evidence_class = metadata["overview"].loc[0, "evidence_class"]
    warnings = list(metadata["warnings"])
    working = data.copy()
    working["_gp_pigmentation"] = metadata["normalized"]["pigmentation_value"].to_numpy()
    analysis_metric = metadata["settings"]["analysis_metric"]

    if evidence_class == "proxy":
        acquisition_quality = {
            "overview": pd.DataFrame([{"status": "not_assessed_proxy_is_not_pigmentation"}]),
            "group_quality": pd.DataFrame(),
            "strata_summary": pd.DataFrame(),
            "associations": pd.DataFrame(),
            "warnings": ("pigmentation_not_measured",),
            "reporting_text": "Pigmentation-stratified PPG analysis was not performed because only a demographic proxy was supplied.",
        }
        warnings.append("pigmentation_not_measured")
    else:
        acquisition_quality = summarize_ppg_quality_by_pigmentation(
            working,
            participant_col=participant_col,
            ppg_col=ppg_col,
            pigmentation_col="_gp_pigmentation",
            pigmentation_metric=analysis_metric,
            time_col=time_col,
            group_cols=group_cols,
            sampling_rate_hz=sampling_rate_hz,
            n_boot=n_boot,
            random_state=random_state,
        )
        warnings.extend(acquisition_quality["warnings"])

    if reference_col is None and candidate_col is None:
        reference_agreement = {"status": "not_assessed", "reason": "reference_and_candidate_not_supplied"}
    elif reference_col is None or candidate_col is None:
        raise ValueError("Supply both `reference_col` and `candidate_col`, or neither.")
    elif evidence_class == "proxy":
        reference_agreement = {"status": "not_assessed", "reason": "pigmentation_not_measured"}
    else:
        reference_agreement = compare_ppg_reference_by_pigmentation(
            working,
            participant_col=participant_col,
            reference_col=reference_col,
            candidate_col=candidate_col,
            pigmentation_col="_gp_pigmentation",
            pigmentation_metric=analysis_metric,
            metric_name=metric_name,
            device_col=device_col,
            condition_col=condition_col,
            n_boot=n_boot,
            random_state=random_state,
        )
        warnings.extend(reference_agreement["warnings"])

    reporting_parts = [
        "Pigmentation was treated as a measured acquisition characteristic with explicit provenance rather than inferred from race or ethnicity.",
        acquisition_quality["reporting_text"],
    ]
    if isinstance(reference_agreement, dict) and "reporting_text" in reference_agreement:
        reporting_parts.append(reference_agreement["reporting_text"])
    reporting_parts.append(
        "The audit does not label a device fair or unfair, does not automatically exclude observations based on pigmentation, and does not perform a pigmentation-based signal correction."
    )
    provenance = pd.DataFrame(
        [
            {
                "schema_version": _SCHEMA_VERSION,
                "pigmentation_metric_supplied": pigmentation_metric,
                "analysis_metric": analysis_metric,
                "evidence_class": evidence_class,
                "sensor_site_supplied": sensor_site is not None,
                "pigmentation_site_supplied": pigmentation_site is not None,
                "reference_validation_requested": reference_col is not None,
            }
        ]
    )
    return {
        "metadata": metadata,
        "acquisition_quality": acquisition_quality,
        "reference_agreement": reference_agreement,
        "warnings": tuple(dict.fromkeys(warnings)),
        "reporting_text": " ".join(reporting_parts),
        "provenance": provenance,
        "settings": {
            "participant_col": participant_col,
            "ppg_col": ppg_col,
            "pigmentation_metric": pigmentation_metric,
            "time_col": time_col,
            "group_cols": [] if group_cols is None else list(group_cols),
            "sampling_rate_hz": sampling_rate_hz,
            "reference_col": reference_col,
            "candidate_col": candidate_col,
            "device_col": device_col,
            "condition_col": condition_col,
            "n_boot": int(n_boot),
        },
    }


__all__ = [
    "compute_skin_ita",
    "validate_skin_pigmentation_metadata",
    "summarize_ppg_quality_by_pigmentation",
    "compare_ppg_reference_by_pigmentation",
    "ppg_pigmentation_audit",
]
