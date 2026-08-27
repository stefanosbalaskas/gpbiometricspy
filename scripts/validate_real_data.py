#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import argparse
import json
import tempfile
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import gpbiometricspy as gp


def path_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def compact(value: Any) -> dict[str, Any]:
    if isinstance(value, pd.DataFrame):
        return {"status": "pass", "type": "DataFrame", "rows": len(value), "columns": len(value.columns)}
    if isinstance(value, dict):
        return {"status": "pass", "type": "dict", "keys": sorted(map(str, value.keys()))[:30]}
    return {"status": "pass", "type": type(value).__name__}


def guarded(steps: dict[str, dict[str, Any]], name: str, fn: Callable[[], Any]) -> Any | None:
    try:
        value = fn()
        steps[name] = compact(value)
        return value
    except Exception as exc:  # real exports can legitimately lack a modality or required metadata
        steps[name] = {"status": "review", "error_type": type(exc).__name__, "message": str(exc)[:500]}
        return None


def first_present(columns: pd.Index, names: list[str]) -> str | None:
    lookup = {str(c).lower(): str(c) for c in columns}
    for name in names:
        if name in columns:
            return name
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def validate_single_file(inp: Path, out: Path, expected_sampling_rate_hz: float) -> dict[str, Any]:
    dat = gp.import_gazepoint_biometrics(inp)
    steps: dict[str, dict[str, Any]] = {}
    tables: dict[str, pd.DataFrame] = {}
    plots: dict[str, Any] = {}

    audit = guarded(steps, "import_schema_audit", lambda: gp.audit_gazepoint_biometrics_file(data=dat, include_data=False))
    active = guarded(steps, "active_channels", lambda: gp.detect_active_biometric_channels(dat))
    readiness = guarded(steps, "real_data_readiness", lambda: gp.run_gazepoint_biometrics_real_data_readiness(dat, min_rows=100))
    validity = guarded(steps, "biometric_validity", lambda: gp.summarise_gazepoint_biometric_validity(dat))
    missing = guarded(steps, "missingness", lambda: gp.summarize_gazepoint_missingness(dat))

    if isinstance(active, pd.DataFrame):
        tables["active_channels"] = active
    if isinstance(missing, pd.DataFrame):
        tables["missingness"] = missing
    if isinstance(validity, dict) and isinstance(validity.get("signals"), pd.DataFrame):
        tables["validity_signals"] = validity["signals"]

    group_col = first_present(dat.columns, ["participant_id", "source_participant", "participant", "USER"])
    group_cols = [group_col] if group_col else None
    time_col = first_present(dat.columns, ["TIME", "time_s", "CNT", "TIME_MS", "MSTIMER"])

    eda_col = first_present(dat.columns, ["GSR_US", "EDA_US", "EDA", "GSR"])
    if eda_col:
        eda_quality = guarded(steps, "eda_quality", lambda: gp.audit_gazepoint_gsr_quality(dat, value_column=eda_col))
        if isinstance(eda_quality, pd.DataFrame):
            tables["eda_quality"] = eda_quality
        eda_decomp = guarded(
            steps,
            "eda_decomposition",
            lambda: gp.decompose_gazepoint_eda(dat, signal_col=eda_col, time_col=time_col, group_cols=group_cols, window_size=31),
        )
        if isinstance(eda_decomp, pd.DataFrame):
            guarded(
                steps,
                "scr_event_detection",
                lambda: gp.detect_gazepoint_scr_events(
                    eda_decomp,
                    phasic_col="eda_phasic",
                    time_col=time_col,
                    group_cols=group_cols,
                    min_peak_distance=10,
                ),
            )

    ppg_col = first_present(dat.columns, ["HRP", "PPG", "pulse", "ppg"])
    if ppg_col:
        ppg_dat = dat.iloc[: min(len(dat), 6000)].copy()
        ppg_detection = guarded(
            steps,
            "ppg_peak_detection",
            lambda: gp.detect_gazepoint_ppg_peaks(
                ppg_dat,
                signal_col=ppg_col,
                time_col=time_col,
                group_cols=group_cols,
                sampling_rate_hz=expected_sampling_rate_hz,
                high_precision=False,
            ),
        )
        if isinstance(ppg_detection, dict) and "peaks" in ppg_detection:
            rejected = guarded(steps, "ppg_peak_qc", lambda: gp.reject_gazepoint_ppg_peaks(ppg_detection["peaks"]))
            if isinstance(rejected, pd.DataFrame):
                measures = guarded(steps, "ppg_measures", lambda: gp.compute_gazepoint_ppg_measures(rejected))
                if isinstance(measures, pd.DataFrame):
                    tables["ppg_measures"] = measures

    ibi_col = first_present(dat.columns, ["IBI_clean_ms", "RR_ms", "IBI"])
    if ibi_col:
        hrv_dat = dat.copy()
        values = pd.to_numeric(hrv_dat[ibi_col], errors="coerce")
        resolved_col = ibi_col
        unit = "ms"
        finite = values[np.isfinite(values)]
        if ibi_col.upper() == "IBI" and len(finite) and float(np.nanmedian(finite)) < 10:
            resolved_col = "IBI_clean_ms"
            hrv_dat[resolved_col] = values * 1000.0
        hrv = guarded(
            steps,
            "hrv_features",
            lambda: gp.extract_gazepoint_hrv_features(
                hrv_dat,
                ibi_col=resolved_col,
                group_cols=group_cols,
                unit=unit,
                min_intervals=3,
                min_duration_s=1,
            ),
        )
        if isinstance(hrv, pd.DataFrame):
            tables["hrv_features"] = hrv
        elif isinstance(hrv, dict) and isinstance(hrv.get("features"), pd.DataFrame):
            tables["hrv_features"] = hrv["features"]

    pupil_cols = [c for c in [first_present(dat.columns, ["LPMM", "pupil_left"]), first_present(dat.columns, ["RPMM", "pupil_right"])] if c]
    if pupil_cols:
        guarded(
            steps,
            "pupil_cleaning",
            lambda: gp.clean_gazepoint_pupil_signal(dat, pupil_cols=pupil_cols, time_col=time_col, group_cols=group_cols),
        )

    x_col = first_present(dat.columns, ["FPOGX", "gaze_x"])
    y_col = first_present(dat.columns, ["FPOGY", "gaze_y"])
    if x_col and y_col:
        guarded(
            steps,
            "gaze_validation",
            lambda: gp.validate_gazepoint_gaze(
                dat,
                time_col=time_col,
                x_col=x_col,
                y_col=y_col,
                group_cols=group_cols,
                expected_sampling_rate_hz=expected_sampling_rate_hz,
            ),
        )

    ttl_cols = [c for c in [f"TTL{i}" for i in range(7)] if c in dat.columns]
    if ttl_cols:
        ttl = guarded(
            steps,
            "ttl_event_extraction",
            lambda: gp.extract_gazepoint_ttl_events(dat, ttl_columns=ttl_cols, group_columns=group_cols),
        )
        if isinstance(ttl, pd.DataFrame):
            tables["ttl_events"] = ttl.head(500)

    signal_cols = [c for c in [eda_col, ppg_col, first_present(dat.columns, ["HR"]), *(pupil_cols[:1])] if c]
    if signal_cols:
        fig = guarded(
            steps,
            "multimodal_plot",
            lambda: gp.plot_gazepoint_biometric_signals(
                dat,
                signal_cols=signal_cols,
                time_col=time_col,
                group_col=group_col,
                max_points=3000,
                standardize=True,
            ),
        )
        if fig is not None and hasattr(fig, "savefig"):
            plots["multimodal_signals"] = fig

    report = guarded(
        steps,
        "aggregate_report_bundle",
        lambda: gp.export_gazepoint_biometrics_report_bundle(
            output_dir=out / "report_bundle",
            prefix="real_data_validation",
            tables=tables or {"dimensions": pd.DataFrame([{"rows": len(dat), "columns": len(dat.columns)}])},
            plots=plots or None,
            text={"privacy": "Aggregate validation outputs only. Source participant exports were not copied into the repository."},
            overwrite=True,
        ),
    )
    plt.close("all")

    warning_count = len(audit.get("warnings", [])) if isinstance(audit, dict) else None
    readiness_overview = readiness.get("overview") if isinstance(readiness, dict) else None
    readiness_records = readiness_overview.to_dict(orient="records") if isinstance(readiness_overview, pd.DataFrame) else []
    return {
        "mode": "single_file",
        "input_name": inp.name,
        "rows": len(dat),
        "columns": len(dat.columns),
        "audit_warning_count": warning_count,
        "readiness": readiness_records,
        "steps": steps,
        "report_bundle_written": bool(report is not None),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate private Gazepoint exports without committing participant data.")
    ap.add_argument("input", help="CSV file or directory of Gazepoint exports kept outside the repository")
    ap.add_argument("--output", required=True, help="Output directory, preferably outside the repository")
    ap.add_argument("--allow-repository-output", action="store_true")
    ap.add_argument("--expected-sampling-rate-hz", type=float, default=60)
    ns = ap.parse_args()
    inp = Path(ns.input).expanduser().resolve()
    out = Path(ns.output).expanduser().resolve()
    repo = ROOT

    if not inp.exists():
        raise SystemExit(f"input does not exist: {inp}")
    if path_inside(inp, repo):
        raise SystemExit("private real-data input must remain outside the repository")
    if path_inside(out, repo) and not ns.allow_repository_output:
        raise SystemExit("output is inside the repository; choose an external directory or pass --allow-repository-output explicitly")
    out.mkdir(parents=True, exist_ok=True)

    if inp.is_file():
        summary = validate_single_file(inp, out, ns.expected_sampling_rate_hz)
    else:
        smoke = gp.run_gazepoint_real_data_smoke(
            str(inp),
            output_dir=str(out),
            workflow_args={"expected_sampling_rate_hz": ns.expected_sampling_rate_hz},
            write_results=True,
            overwrite=True,
            protect_repository=True,
        )
        privacy = gp.audit_gazepoint_smoke_privacy(smoke)
        summary = {
            "mode": "directory",
            "input_name": inp.name,
            "privacy": privacy.to_dict(orient="records") if hasattr(privacy, "to_dict") else str(privacy),
            "workflow_keys": sorted(smoke),
        }

    summary_path = out / "gpbiometricspy_real_data_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
