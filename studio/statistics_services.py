from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import gpbiometricspy as gp


_SOURCE_LABELS = {
    "loaded_data": "Loaded dataset",
    "multimodal_event_responses": "Multimodal · event response summary",
    "multimodal_event_samples": "Multimodal · event-locked samples",
    "multimodal_model_data": "Multimodal · model-ready table",
    "multimodal_windows": "Multimodal · participant/trial windows",
    "multimodal_aoi_summary": "Multimodal · AOI-linked biometrics",
    "eda_decomposition": "EDA / SCR · decomposed samples",
    "eda_scr_events": "EDA / SCR · SCR events",
    "pupil_processed": "Pupil · processed samples",
    "pupil_event_summary": "Pupil · event response summary",
    "gaze_processed": "Gaze · processed samples",
    "gaze_fixation_summary": "Gaze · fixation summary",
    "ppg_hr_windows": "PPG / HR / HRV · HR windows",
    "ppg_ibi_hrv": "PPG / HR / HRV · IBI HRV features",
}


def _put(out: dict[str, pd.DataFrame], key: str, value: Any) -> None:
    if isinstance(value, pd.DataFrame) and not value.empty:
        out[key] = value


def statistics_source_tables(
    data: pd.DataFrame | None,
    analyses: dict[str, Any] | None,
) -> dict[str, pd.DataFrame]:
    """Return curated Studio tables that are reasonable inputs to statistical workflows."""
    out: dict[str, pd.DataFrame] = {}
    if isinstance(data, pd.DataFrame) and not data.empty:
        out["loaded_data"] = data
    analyses = analyses or {}

    multimodal = analyses.get("multimodal")
    if isinstance(multimodal, dict):
        eventlocked = multimodal.get("eventlocked")
        if isinstance(eventlocked, dict):
            _put(out, "multimodal_event_responses", eventlocked.get("summary"))
            _put(out, "multimodal_event_samples", eventlocked.get("samples"))
        _put(out, "multimodal_model_data", multimodal.get("model_data"))
        _put(out, "multimodal_windows", multimodal.get("multimodal_windows"))
        aoi = multimodal.get("aoi_biometrics")
        if isinstance(aoi, dict):
            _put(out, "multimodal_aoi_summary", aoi.get("summary"))

    eda = analyses.get("eda_scr")
    if isinstance(eda, dict):
        _put(out, "eda_decomposition", eda.get("decomposition"))
        _put(out, "eda_scr_events", eda.get("events"))

    pupil = analyses.get("pupil")
    if isinstance(pupil, dict):
        _put(out, "pupil_processed", pupil.get("processed_data"))
        _put(out, "pupil_event_summary", pupil.get("event_summary"))

    gaze = analyses.get("gaze")
    if isinstance(gaze, dict):
        _put(out, "gaze_processed", gaze.get("processed_data"))
        _put(out, "gaze_fixation_summary", gaze.get("fixation_summary"))

    cardiac = analyses.get("ppg_hr_hrv")
    if isinstance(cardiac, dict):
        _put(out, "ppg_hr_windows", cardiac.get("hr_windows"))
        ibi_hrv = cardiac.get("ibi_hrv")
        if isinstance(ibi_hrv, dict):
            for candidate in ["features", "summary", "overview"]:
                if isinstance(ibi_hrv.get(candidate), pd.DataFrame) and not ibi_hrv[candidate].empty:
                    out["ppg_ibi_hrv"] = ibi_hrv[candidate]
                    break

    return out


def statistics_source_choices(
    data: pd.DataFrame | None,
    analyses: dict[str, Any] | None,
) -> dict[str, str]:
    tables = statistics_source_tables(data, analyses)
    return {key: _SOURCE_LABELS.get(key, key.replace("_", " ").title()) for key in tables}


def statistics_source_table(
    data: pd.DataFrame | None,
    analyses: dict[str, Any] | None,
    source_key: str,
) -> pd.DataFrame:
    tables = statistics_source_tables(data, analyses)
    if source_key not in tables:
        raise ValueError("The selected statistical source table is not available in the current Studio session.")
    return tables[source_key]


def statistics_source_inventory(
    data: pd.DataFrame | None,
    analyses: dict[str, Any] | None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, table in statistics_source_tables(data, analyses).items():
        numeric = [c for c in table.columns if pd.api.types.is_numeric_dtype(table[c])]
        nonnumeric = [c for c in table.columns if c not in numeric]
        rows.append(
            {
                "source": key,
                "label": _SOURCE_LABELS.get(key, key),
                "rows": len(table),
                "columns": len(table.columns),
                "numeric_columns": len(numeric),
                "non_numeric_columns": len(nonnumeric),
            }
        )
    return pd.DataFrame(rows)


def numeric_column_choices(table: pd.DataFrame | None) -> list[str]:
    if not isinstance(table, pd.DataFrame):
        return []
    return [c for c in table.columns if pd.api.types.is_numeric_dtype(table[c])]


def categorical_column_choices(table: pd.DataFrame | None) -> list[str]:
    if not isinstance(table, pd.DataFrame):
        return []
    preferred = [
        "condition",
        "event_label",
        "modality",
        "signal",
        "aoi_label",
        "AOI",
        "participant",
        "participant_id",
        "source_participant",
        "subject",
        "subject_id",
        "trial",
        "trial_id",
        "stimulus",
        "stimulus_id",
        "MEDIA_ID",
        "MEDIA_NAME",
    ]
    ordered = [c for c in preferred if c in table.columns]
    ordered.extend(c for c in table.columns if c not in ordered and not pd.api.types.is_numeric_dtype(table[c]))
    return ordered


def participant_column_choices(table: pd.DataFrame | None) -> list[str]:
    if not isinstance(table, pd.DataFrame):
        return []
    preferred = [
        "participant",
        "participant_id",
        "source_participant",
        "subject",
        "subject_id",
        "USER",
        "source_file",
        "session_id",
        "session",
    ]
    return [c for c in preferred if c in table.columns]


def trial_column_choices(table: pd.DataFrame | None) -> list[str]:
    if not isinstance(table, pd.DataFrame):
        return []
    preferred = ["trial", "trial_id", "TRIAL", "stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME"]
    return [c for c in preferred if c in table.columns]


def time_column_choices(table: pd.DataFrame | None) -> list[str]:
    if not isinstance(table, pd.DataFrame):
        return []
    preferred = [
        "relative_time_s",
        "time",
        "time_s",
        "event_time_s",
        "event_time",
        "TIME",
        "MSTIMER",
        "CNT",
        "timestamp",
    ]
    ordered = [c for c in preferred if c in table.columns and pd.api.types.is_numeric_dtype(table[c])]
    ordered.extend(
        c
        for c in table.columns
        if c not in ordered and pd.api.types.is_numeric_dtype(table[c]) and "time" in str(c).lower()
    )
    return ordered


def condition_levels(table: pd.DataFrame | None, condition_col: str | None) -> list[str]:
    if not isinstance(table, pd.DataFrame) or not condition_col or condition_col not in table.columns:
        return []
    return sorted(table[condition_col].dropna().astype(str).unique().tolist())


def run_lme_preparation(
    table: pd.DataFrame,
    *,
    outcome_col: str,
    fixed_effect_cols: list[str] | tuple[str, ...] | None = None,
    covariate_cols: list[str] | tuple[str, ...] | None = None,
    random_effect_cols: list[str] | tuple[str, ...] | None = None,
    participant_col: str | None = None,
    stimulus_col: str | None = None,
    trial_col: str | None = None,
    window_col: str | None = None,
    baseline_col: str | None = None,
    baseline_correct: bool = False,
    factor_cols: list[str] | tuple[str, ...] | None = None,
    continuous_cols: list[str] | tuple[str, ...] | None = None,
    scale_continuous: bool = False,
    include_window: bool = True,
    drop_missing: bool = True,
    min_rows: int = 10,
) -> dict[str, Any]:
    if not isinstance(table, pd.DataFrame) or table.empty:
        raise ValueError("Model preparation requires a non-empty statistical source table.")
    if outcome_col not in table.columns:
        raise ValueError("Selected model outcome was not found in the source table.")
    if not pd.api.types.is_numeric_dtype(table[outcome_col]):
        raise TypeError("Selected model outcome must be numeric.")
    if int(min_rows) < 1:
        raise ValueError("Minimum model rows must be positive.")

    result = gp.prepare_gazepoint_biometrics_lme_data(
        table,
        outcome_col=outcome_col,
        fixed_effect_cols=list(fixed_effect_cols or []),
        covariate_cols=list(covariate_cols or []),
        random_effect_cols=list(random_effect_cols or []),
        participant_col=participant_col,
        stimulus_col=stimulus_col,
        trial_col=trial_col,
        window_col=window_col,
        baseline_col=baseline_col,
        baseline_correct=bool(baseline_correct),
        factor_cols=list(factor_cols or []),
        continuous_cols=list(continuous_cols or []),
        scale_continuous=bool(scale_continuous),
        include_window=bool(include_window),
        drop_missing=bool(drop_missing),
        min_rows=int(min_rows),
    )
    result["studio_parameters"] = {
        "outcome_col": outcome_col,
        "fixed_effect_cols": list(fixed_effect_cols or []),
        "covariate_cols": list(covariate_cols or []),
        "random_effect_cols": list(random_effect_cols or []),
        "participant_col": participant_col,
        "stimulus_col": stimulus_col,
        "trial_col": trial_col,
        "window_col": window_col,
        "baseline_col": baseline_col,
        "baseline_correct": bool(baseline_correct),
        "factor_cols": list(factor_cols or []),
        "continuous_cols": list(continuous_cols or []),
        "scale_continuous": bool(scale_continuous),
        "include_window": bool(include_window),
        "drop_missing": bool(drop_missing),
        "min_rows": int(min_rows),
    }
    return result


def lme_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not isinstance(result, dict):
        return {}
    return {
        key: value.copy()
        for key, value in result.items()
        if key in {"overview", "data", "model_data", "variable_summary"} and isinstance(value, pd.DataFrame)
    }


def lme_reproducibility_script(result: dict[str, Any] | None, *, source_label: str = "source_table") -> str:
    if not isinstance(result, dict):
        return "# Run Model Preparation in gpbiometricspy Studio to generate reproducible code.\n"
    p = result.get("studio_parameters") or {}
    return "\n".join(
        [
            "import gpbiometricspy as gp",
            "",
            "# Replace this with the same table selected in Studio.",
            f"{source_label} = ...",
            "",
            "prepared = gp.prepare_gazepoint_biometrics_lme_data(",
            f"    {source_label},",
            f"    outcome_col={p.get('outcome_col')!r},",
            f"    fixed_effect_cols={p.get('fixed_effect_cols')!r},",
            f"    covariate_cols={p.get('covariate_cols')!r},",
            f"    random_effect_cols={p.get('random_effect_cols')!r},",
            f"    participant_col={p.get('participant_col')!r},",
            f"    stimulus_col={p.get('stimulus_col')!r},",
            f"    trial_col={p.get('trial_col')!r},",
            f"    window_col={p.get('window_col')!r},",
            f"    baseline_col={p.get('baseline_col')!r},",
            f"    baseline_correct={p.get('baseline_correct')!r},",
            f"    factor_cols={p.get('factor_cols')!r},",
            f"    continuous_cols={p.get('continuous_cols')!r},",
            f"    scale_continuous={p.get('scale_continuous')!r},",
            f"    include_window={p.get('include_window')!r},",
            f"    drop_missing={p.get('drop_missing')!r},",
            f"    min_rows={p.get('min_rows')!r},",
            ")",
            "model_data = prepared['model_data']",
            "print(prepared['model_formula'])",
            "",
        ]
    )


def run_cluster_analysis(
    table: pd.DataFrame,
    *,
    outcome_col: str,
    time_col: str,
    condition_col: str,
    participant_col: str,
    condition_a: str | None = None,
    condition_b: str | None = None,
    time_bin_width: float | None = None,
    aggregation: str = "mean",
    min_subjects: int = 10,
    n_permutations: int = 1000,
    cluster_forming_alpha: float = 0.05,
    cluster_alpha: float = 0.05,
    tail: str = "two.sided",
    seed: int | None = 2026,
    run_sensitivity: bool = False,
) -> dict[str, Any]:
    if not isinstance(table, pd.DataFrame) or table.empty:
        raise ValueError("Cluster permutation requires a non-empty statistical source table.")
    for column in [outcome_col, time_col, condition_col, participant_col]:
        if not column or column not in table.columns:
            raise ValueError(f"Required cluster-permutation column `{column}` was not found in the source table.")
    if not pd.api.types.is_numeric_dtype(table[outcome_col]):
        raise TypeError("Cluster-permutation outcome must be numeric.")
    if not pd.api.types.is_numeric_dtype(table[time_col]):
        raise TypeError("Cluster-permutation time must be numeric.")
    if aggregation not in {"mean", "median"}:
        raise ValueError("Cluster aggregation must be mean or median.")
    if int(min_subjects) < 3:
        raise ValueError("Minimum participant diagnostic threshold cannot be below three.")
    if int(n_permutations) < 1:
        raise ValueError("Number of permutations must be positive.")

    prepared = gp.prepare_gazepoint_timecourse_test_data(
        table,
        outcome_col=outcome_col,
        time_col=time_col,
        condition_col=condition_col,
        participant_col=participant_col,
        condition_a=condition_a,
        condition_b=condition_b,
        time_bin_width=time_bin_width,
        aggregation=aggregation,
        require_complete=False,
    )
    settings = prepared.attrs.get("gpbiometrics_settings", {})
    resolved_a = settings.get("condition_a", condition_a)
    resolved_b = settings.get("condition_b", condition_b)
    diagnostic = gp.diagnose_gazepoint_cluster_design(
        prepared,
        subject="participant",
        condition="condition",
        time="time",
        value="value",
        design="within",
        min_subjects=int(min_subjects),
    )
    parameters = {
        "outcome_col": outcome_col,
        "time_col": time_col,
        "condition_col": condition_col,
        "participant_col": participant_col,
        "condition_a": resolved_a,
        "condition_b": resolved_b,
        "time_bin_width": time_bin_width,
        "aggregation": aggregation,
        "min_subjects": int(min_subjects),
        "n_permutations": int(n_permutations),
        "cluster_forming_alpha": float(cluster_forming_alpha),
        "cluster_alpha": float(cluster_alpha),
        "tail": tail,
        "seed": seed,
        "run_sensitivity": bool(run_sensitivity),
    }
    result: dict[str, Any] = {
        "prepared_data": prepared,
        "diagnostic": diagnostic,
        "parameters": parameters,
        "status": "design_ready" if bool(diagnostic.get("passed")) else "design_blocked",
    }
    if not bool(diagnostic.get("passed")):
        return result

    cluster = gp.run_gazepoint_cluster_permutation(
        prepared,
        outcome_col="value",
        time_col="time",
        condition_col="condition",
        participant_col="participant",
        design="within",
        condition_a=resolved_a,
        condition_b=resolved_b,
        n_permutations=int(n_permutations),
        cluster_forming_alpha=float(cluster_forming_alpha),
        cluster_alpha=float(cluster_alpha),
        tail=tail,
        seed=seed,
        time_bin_width=None,
        aggregation="mean",
    )
    result["cluster"] = cluster
    result["cluster_summary"] = gp.summarize_gazepoint_time_clusters(cluster, alpha=float(cluster_alpha))
    result["report"] = gp.report_gazepoint_cluster_permutation(
        cluster,
        cluster_alpha=float(cluster_alpha),
        include_assumptions=True,
    )
    result["status"] = "completed"

    if run_sensitivity:
        result["sensitivity"] = gp.run_gazepoint_cluster_threshold_sensitivity(
            prepared,
            dv="value",
            time="time",
            condition="condition",
            subject="participant",
            thresholds=(0.01, 0.025, 0.05, 0.10),
            cluster_alpha=float(cluster_alpha),
            seed=seed,
            n_permutations=int(n_permutations),
            condition_a=resolved_a,
            condition_b=resolved_b,
            tail=tail,
            aggregation="mean",
        )
    return result


def cluster_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not isinstance(result, dict):
        return {}
    tables: dict[str, pd.DataFrame] = {}
    if isinstance(result.get("prepared_data"), pd.DataFrame):
        tables["prepared_data"] = result["prepared_data"].copy()
    diagnostic = result.get("diagnostic")
    if isinstance(diagnostic, dict):
        if isinstance(diagnostic.get("checks"), pd.DataFrame):
            tables["design_checks"] = diagnostic["checks"].copy()
        audit = diagnostic.get("audit")
        if isinstance(audit, dict):
            for key in ["summary", "missing_cells", "duplicate_cells", "subject_condition_counts"]:
                if isinstance(audit.get(key), pd.DataFrame):
                    tables[f"grid_{key}"] = audit[key].copy()
    cluster = result.get("cluster")
    if isinstance(cluster, dict):
        for key in ["timewise", "clusters", "condition_summary", "prepared_data"]:
            if isinstance(cluster.get(key), pd.DataFrame):
                tables[f"cluster_{key}"] = cluster[key].copy()
    if isinstance(result.get("cluster_summary"), pd.DataFrame):
        tables["cluster_summary"] = result["cluster_summary"].copy()
    sensitivity = result.get("sensitivity")
    if isinstance(sensitivity, pd.DataFrame):
        tables["sensitivity"] = sensitivity.copy()
    elif isinstance(sensitivity, dict):
        for key, value in sensitivity.items():
            if isinstance(value, pd.DataFrame):
                tables[f"sensitivity_{key}"] = value.copy()
    return tables


def cluster_report_text(result: dict[str, Any] | None) -> str:
    if not isinstance(result, dict):
        return "Run Cluster Permutation to generate a package-native result statement."
    if result.get("status") == "design_blocked":
        return (
            "Cluster permutation was not run because the package design diagnostic found one or more "
            "error-level problems. Resolve the design/grid checks before inference."
        )
    report = result.get("report")
    if isinstance(report, dict) and report.get("text"):
        return str(report["text"])
    return "No cluster-permutation report is available."


def cluster_reproducibility_script(result: dict[str, Any] | None, *, source_label: str = "timecourse") -> str:
    if not isinstance(result, dict):
        return "# Run Cluster Permutation in gpbiometricspy Studio to generate reproducible code.\n"
    p = result.get("parameters") or {}
    lines = [
        "import gpbiometricspy as gp",
        "",
        "# Replace this with the same time-course table selected in Studio.",
        f"{source_label} = ...",
        "",
        "prepared = gp.prepare_gazepoint_timecourse_test_data(",
        f"    {source_label},",
        f"    outcome_col={p.get('outcome_col')!r}, time_col={p.get('time_col')!r},",
        f"    condition_col={p.get('condition_col')!r}, participant_col={p.get('participant_col')!r},",
        f"    condition_a={p.get('condition_a')!r}, condition_b={p.get('condition_b')!r},",
        f"    time_bin_width={p.get('time_bin_width')!r}, aggregation={p.get('aggregation')!r},",
        "    require_complete=False,",
        ")",
        "diagnostic = gp.diagnose_gazepoint_cluster_design(",
        "    prepared, subject='participant', condition='condition', time='time', value='value',",
        f"    design='within', min_subjects={p.get('min_subjects')!r},",
        ")",
        "if not diagnostic['passed']:",
        "    raise ValueError('Cluster design diagnostic did not pass.')",
        "",
        "result = gp.run_gazepoint_cluster_permutation(",
        "    prepared, outcome_col='value', time_col='time', condition_col='condition', participant_col='participant',",
        f"    design='within', condition_a={p.get('condition_a')!r}, condition_b={p.get('condition_b')!r},",
        f"    n_permutations={p.get('n_permutations')!r}, cluster_forming_alpha={p.get('cluster_forming_alpha')!r},",
        f"    cluster_alpha={p.get('cluster_alpha')!r}, tail={p.get('tail')!r}, seed={p.get('seed')!r},",
        ")",
        "clusters = gp.summarize_gazepoint_time_clusters(result)",
        "report = gp.report_gazepoint_cluster_permutation(result)",
    ]
    if p.get("run_sensitivity"):
        lines.extend(
            [
                "",
                "sensitivity = gp.run_gazepoint_cluster_threshold_sensitivity(",
                "    prepared, dv='value', time='time', condition='condition', subject='participant',",
                f"    thresholds=(0.01, 0.025, 0.05, 0.10), cluster_alpha={p.get('cluster_alpha')!r},",
                f"    seed={p.get('seed')!r}, n_permutations={p.get('n_permutations')!r},",
                f"    condition_a={p.get('condition_a')!r}, condition_b={p.get('condition_b')!r}, tail={p.get('tail')!r},",
                ")",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def unsupported_cluster_guardrails() -> pd.DataFrame:
    """Document public package guardrails that Studio intentionally does not bypass."""
    return pd.DataFrame(
        [
            {
                "requested_method": "ANOVA / >2-condition cluster permutation",
                "package_guardrail": "run_gazepoint_cluster_permutation_anova()",
                "studio_status": "not exposed",
                "reason": "Package export is an intentional unsupported-method guardrail.",
            },
            {
                "requested_method": "Mixed-model cluster permutation",
                "package_guardrail": "run_gazepoint_cluster_permutation_lmer()",
                "studio_status": "not exposed",
                "reason": "Package export is an intentional unsupported-method guardrail.",
            },
            {
                "requested_method": "TFCE",
                "package_guardrail": "run_gazepoint_tfce()",
                "studio_status": "not exposed",
                "reason": "Package export is an intentional unsupported-method guardrail.",
            },
            {
                "requested_method": "Multidimensional cluster inference",
                "package_guardrail": "run_gazepoint_multidimensional_cluster_permutation()",
                "studio_status": "not exposed",
                "reason": "Package export is an intentional unsupported-method guardrail.",
            },
            {
                "requested_method": "Precise cluster onset / offset estimation",
                "package_guardrail": "estimate_gazepoint_cluster_onset()/offset()",
                "studio_status": "not exposed",
                "reason": "Cluster temporal extent is descriptive rather than a precise change-point estimate.",
            },
        ]
    )
