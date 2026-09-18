from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path

import numpy as np
import pandas as pd

import gpbiometricspy as gp


TUTORIAL = "qc-exclusion-decision-ledger"
OUTPUT_ENV = "GPBIOMETRICSPY_EXCLUSION_DIR"


def _output_dir() -> Path:
    target = os.environ.get(OUTPUT_ENV)
    path = Path(target).expanduser().resolve() if target else Path.cwd() / "outputs" / "qc-exclusion-ledger"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    out = _output_dir()

    dat = (
        gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
        .copy()
        .iloc[:600]
        .reset_index(drop=True)
    )

    required = {"participant_id", "TIME", "GSR_US", "HR"}
    missing = required.difference(dat.columns)
    if missing:
        raise RuntimeError(f"Bundled demonstration is missing expected columns: {sorted(missing)}")

    # Deliberately inject two bounded, known issues into the synthetic copy so the
    # tutorial always has review candidates. The source demonstration is untouched.
    dat.loc[100:119, "GSR_US"] = np.nan
    dat.loc[300:325, "HR"] = 60.0

    activity = gp.audit_gazepoint_signal_activity(
        dat,
        signal_cols=["GSR_US", "HR"],
        group_cols=["participant_id"],
    )
    time_qc = gp.audit_gazepoint_time_resets(
        dat,
        time_col="TIME",
        group_cols=["participant_id"],
    )

    # Preserve source-row acquisition order for the deliberately injected runs.
    # TIME is audited separately above; sorting across participant-level time resets
    # could otherwise interleave samples from different acquisition segments.
    dropout = gp.flag_gazepoint_biometric_dropouts(
        dat,
        signal_cols=["GSR_US", "HR"],
        group_cols=["participant_id"],
        min_missing_run=5,
        min_flatline_run=10,
    )

    activity_path = out / "qc-signal-activity.csv"
    time_path = out / "qc-time-reset-overview.csv"
    dropout_path = out / "qc-dropout-summary.csv"
    activity["signal_by_group"].to_csv(activity_path, index=False)
    time_qc["overview"].to_csv(time_path, index=False)
    dropout_summary = dropout.attrs["dropout_summary"].copy()
    dropout_summary.to_csv(dropout_path, index=False)

    candidates: list[dict[str, object]] = []
    for _, row in dropout_summary.iterrows():
        if int(row["n_any_dropout"]) <= 0:
            continue
        signal = str(row["column"])
        candidates.append(
            {
                "decision_id": f"QC-{len(candidates) + 1:03d}",
                "analysis_stage": "quality_control",
                "unit_type": "signal_x_participant",
                "unit_id": "synthetic_kiosk_p001",
                "signal": signal,
                "issue": "dropout_or_flatline_candidate",
                "evidence_artifact": "qc-dropout-summary.csv",
                "evidence_value": (
                    f"n_any_dropout={int(row['n_any_dropout'])};"
                    f" missing={int(row['n_missing_dropout'])};"
                    f" flatline={int(row['n_flatline_dropout'])}"
                ),
                "criterion": "demonstration QC flag only; researcher review required",
                "decision": "REVIEW",
                "reason": "",
                "downstream_effect": "not_applied",
                "reviewer": "",
                "notes": "Synthetic tutorial candidate; a QC flag is not an automatic exclusion.",
            }
        )

    if not candidates:
        raise RuntimeError("Expected the synthetic QC perturbations to produce review candidates.")

    ledger = pd.DataFrame(candidates)
    ledger_path = out / "exclusion-decision-ledger.csv"
    ledger.to_csv(ledger_path, index=False)

    rows_before = int(len(dat))
    participants_before = int(dat["participant_id"].nunique(dropna=True))
    denominator = pd.DataFrame(
        [
            {
                "unit_type": "row",
                "before": rows_before,
                "excluded": 0,
                "after": rows_before,
                "retained_fraction": 1.0,
                "status": "NO_AUTOMATIC_EXCLUSIONS_APPLIED",
            },
            {
                "unit_type": "participant",
                "before": participants_before,
                "excluded": 0,
                "after": participants_before,
                "retained_fraction": 1.0,
                "status": "NO_AUTOMATIC_EXCLUSIONS_APPLIED",
            },
        ]
    )
    denominator_path = out / "denominator-audit.csv"
    denominator.to_csv(denominator_path, index=False)

    artifacts = [activity_path, time_path, dropout_path, ledger_path, denominator_path]
    manifest = {
        "workflow": TUTORIAL,
        "status": "REVIEW",
        "synthetic_or_template_only": True,
        "gpbiometricspy": gp.__version__,
        "python": platform.python_version(),
        "input_rows": rows_before,
        "review_candidate_count": int(len(ledger)),
        "automatic_exclusions_applied": False,
        "excluded_rows": 0,
        "excluded_participants": 0,
        "dropout_ordering": "preserved_source_row_order_after_separate_time_reset_audit",
        "decision_states": sorted(ledger["decision"].unique().tolist()),
        "artifacts": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in artifacts
        },
    }
    manifest_path = out / "exclusion-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "tutorial": TUTORIAL,
                "status": "PASS",
                "output_dir": str(out),
                "review_candidate_count": int(len(ledger)),
                "automatic_exclusions_applied": False,
                "artifact_count": 6,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
