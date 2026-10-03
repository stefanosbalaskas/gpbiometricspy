from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


MEASUREMENT_REQUIRED = {"person_id", "measurement_concept_id"}
CONCEPT_REQUIRED = {"concept_id", "concept_name"}
SKIN_TERMS = re.compile(
    r"skin|monk|fitzpatrick|von\s*luschan|colorim|spectro|melanin|ita|typology|L\*|b\*",
    flags=re.IGNORECASE,
)
OBJECTIVE_TERMS = re.compile(r"colorim|spectro|melanin|ita|typology|L\*|b\*", flags=re.IGNORECASE)
SUBJECTIVE_TERMS = re.compile(r"monk|fitzpatrick|von\s*luschan", flags=re.IGNORECASE)
SITE_TERMS = re.compile(
    r"finger|palm|forehead|earlobe|sternum|toe|dorsal|ventral|left|right",
    flags=re.IGNORECASE,
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _require_columns(data: pd.DataFrame, required: set[str], table: str) -> None:
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"{table} schema mismatch; missing columns: {', '.join(missing)}")


def _classify_concept(name: str) -> str:
    if OBJECTIVE_TERMS.search(name):
        return "objective_or_instrumental"
    if SUBJECTIVE_TERMS.search(name):
        return "subjective_scale"
    return "skin_related_unspecified"


def inventory_encode(measurement: pd.DataFrame, concept: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Inventory ENCoDE skin-measurement concepts without redistributing source rows."""
    _require_columns(measurement, MEASUREMENT_REQUIRED, "MEASUREMENT")
    _require_columns(concept, CONCEPT_REQUIRED, "CONCEPT")

    concepts = concept[["concept_id", "concept_name"]].copy()
    concepts["concept_name"] = concepts["concept_name"].astype("string")
    skin_concepts = concepts[concepts["concept_name"].str.contains(SKIN_TERMS, na=False)].copy()
    if skin_concepts.empty:
        raise RuntimeError(
            "No skin-tone concepts were detected; inspect ENCoDE concept naming before claiming metadata qualification."
        )

    skin_concepts["evidence_class"] = skin_concepts["concept_name"].map(_classify_concept)
    skin_concepts["mentions_anatomical_site"] = skin_concepts["concept_name"].str.contains(SITE_TERMS, na=False)

    joined = measurement.merge(
        skin_concepts,
        left_on="measurement_concept_id",
        right_on="concept_id",
        how="inner",
        validate="many_to_one",
    )
    value_column = next(
        (column for column in ("value_as_number", "value_as_concept_id", "value_source_value") if column in joined.columns),
        None,
    )
    if value_column is None:
        joined["_has_value"] = False
    else:
        joined["_has_value"] = joined[value_column].notna()

    inventory = (
        joined.groupby(
            ["measurement_concept_id", "concept_name", "evidence_class", "mentions_anatomical_site"],
            dropna=False,
            as_index=False,
        )
        .agg(
            n_measurements=("person_id", "size"),
            n_participants=("person_id", "nunique"),
            n_values=("_has_value", "sum"),
        )
        .sort_values(["evidence_class", "concept_name"], kind="stable")
        .reset_index(drop=True)
    )

    report = {
        "source": "ENCoDE",
        "source_version": "1.0.0",
        "restricted_source_data": True,
        "measurement_rows": int(len(measurement)),
        "skin_measurement_rows": int(len(joined)),
        "participants_with_skin_measurements": int(joined["person_id"].nunique(dropna=True)),
        "skin_concepts": int(len(inventory)),
        "objective_or_instrumental_concepts": int(
            (skin_concepts["evidence_class"] == "objective_or_instrumental").sum()
        ),
        "subjective_scale_concepts": int((skin_concepts["evidence_class"] == "subjective_scale").sum()),
        "concepts_with_site_language": int(skin_concepts["mentions_anatomical_site"].sum()),
        "schema_status": "qualified",
        "source_rows_redistributed": False,
    }
    return inventory, report


def optional_table_inventory(data_dir: Path) -> pd.DataFrame:
    rows = []
    names = [
        "OBSERVATION.csv",
        "DEVICE_EXPOSURE.csv",
        "PROCEDURE_OCCURRENCE.csv",
        "OBSERVATION_PERIOD.csv",
        "PERSON.csv",
        "VISIT_OCCURRENCE.csv",
    ]
    for name in names:
        path = data_dir / name
        rows.append({"table": name, "present": path.exists()})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stress-test gpbiometricspy pigmentation metadata assumptions against an authorized local ENCoDE OMOP export. "
            "Only concept-level derived summaries are written."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory containing authorized ENCoDE CSV tables.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("external-evidence/encode"))
    args = parser.parse_args()

    measurement = _read_csv(args.data_dir / "MEASUREMENT.csv")
    concept = _read_csv(args.data_dir / "CONCEPT.csv")
    inventory, report = inventory_encode(measurement, concept)
    table_inventory = optional_table_inventory(args.data_dir)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(args.output_dir / "encode-skin-concept-inventory.csv", index=False)
    table_inventory.to_csv(args.output_dir / "encode-table-inventory.csv", index=False)
    report["analysis_status"] = "executed_on_authorized_local_copy"
    report["table_inventory"] = table_inventory.to_dict(orient="records")
    (args.output_dir / "encode-schema-report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
