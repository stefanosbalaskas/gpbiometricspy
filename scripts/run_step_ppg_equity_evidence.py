from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


STEP_DEVICE_COLUMNS = (
    "Apple Watch",
    "Empatica",
    "Garmin",
    "Fitbit",
    "Miband",
    "Biovotion",
)
STEP_REQUIRED_COLUMNS = ("ECG", *STEP_DEVICE_COLUMNS, "ID", "Skin Tone", "Activity")
STEP_ACTIVITY_LABELS = {"Rest", "Activity", "Breathe", "Type"}


def load_step_csv(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    missing = [column for column in STEP_REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("STEP schema mismatch; missing required columns: " + ", ".join(missing))
    return data


def reshape_step(data: pd.DataFrame) -> pd.DataFrame:
    long = data.melt(
        id_vars=["ECG", "ID", "Skin Tone", "Activity"],
        value_vars=list(STEP_DEVICE_COLUMNS),
        var_name="device",
        value_name="wearable_hr",
    )
    long = long.rename(
        columns={
            "ECG": "ecg_hr",
            "ID": "participant",
            "Skin Tone": "fitzpatrick",
            "Activity": "activity",
        }
    )
    long["fitzpatrick"] = pd.to_numeric(long["fitzpatrick"], errors="coerce")
    return long


def schema_report(data: pd.DataFrame) -> dict:
    skin = pd.to_numeric(data["Skin Tone"], errors="coerce")
    activities = sorted(str(value) for value in data["Activity"].dropna().unique())
    return {
        "source": "BigIdeasLab_STEP",
        "source_version": "1.0",
        "restricted_source_data": True,
        "rows": int(len(data)),
        "participants": int(data["ID"].nunique(dropna=True)),
        "fitzpatrick_min": float(skin.min()) if skin.notna().any() else None,
        "fitzpatrick_max": float(skin.max()) if skin.notna().any() else None,
        "activities": activities,
        "official_activity_labels_observed": sorted(STEP_ACTIVITY_LABELS.intersection(activities)),
        "devices": list(STEP_DEVICE_COLUMNS),
        "schema_status": "qualified",
    }


def write_derived_outputs(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result["overview"].to_csv(output_dir / "step-overview.csv", index=False)
    result["agreement"].to_csv(output_dir / "step-agreement-by-device-activity.csv", index=False)
    result["agreement_ci"].to_csv(output_dir / "step-agreement-ci.csv", index=False)
    result["category_summary"].to_csv(output_dir / "step-fitzpatrick-device-activity-summary.csv", index=False)
    result["associations"].to_csv(output_dir / "step-continuous-associations.csv", index=False)
    result["retention_association"].to_csv(output_dir / "step-retention-association.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the gpbiometricspy PPG reference-agreement audit on an authorized local copy of "
            "BigIdeasLab_STEP. Source rows are never copied into repository outputs."
        )
    )
    parser.add_argument("--csv", type=Path, required=True, help="Authorized local STEP CSV obtained under the PhysioNet DUA.")
    parser.add_argument("--output-dir", type=Path, default=Path("external-evidence/step"))
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args()

    data = load_step_csv(args.csv)
    report = schema_report(data)
    long = reshape_step(data)

    from gpbiometricspy.ppg_equity import compare_ppg_reference_by_pigmentation

    result = compare_ppg_reference_by_pigmentation(
        long,
        participant_col="participant",
        reference_col="ecg_hr",
        candidate_col="wearable_hr",
        pigmentation_col="fitzpatrick",
        pigmentation_metric="fitzpatrick",
        metric_name="heart_rate",
        device_col="device",
        condition_col="activity",
        n_boot=args.n_boot,
        random_state=args.seed,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_derived_outputs(result, args.output_dir)
    report.update(
        {
            "analysis_status": "executed_on_authorized_local_copy",
            "analysis_warning": (
                "Fitzpatrick is a subjective phototype scale, not an objective optical pigmentation measure; "
                "gpbiometricspy therefore reports descriptive strata and does not fit continuous pigmentation models."
            ),
            "reporting_text": result["reporting_text"],
            "warnings": list(result["warnings"]),
            "source_rows_redistributed": False,
        }
    )
    (args.output_dir / "step-evidence-report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
