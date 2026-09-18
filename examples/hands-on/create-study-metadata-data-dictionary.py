from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path

import pandas as pd

import gpbiometricspy as gp


TUTORIAL = "study-metadata-data-dictionary"
OUTPUT_ENV = "GPBIOMETRICSPY_DICTIONARY_DIR"


def _output_dir() -> Path:
    target = os.environ.get(OUTPUT_ENV)
    if target:
        path = Path(target).expanduser().resolve()
    else:
        path = Path.cwd() / "outputs" / "study-dictionary"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _example_value(series: pd.Series) -> str:
    values = series.dropna()
    if values.empty:
        return ""
    value = values.iloc[0]
    text = str(value)
    return text if len(text) <= 80 else f"{text[:77]}..."


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

    metadata = {
        "tutorial": TUTORIAL,
        "data_kind": "bundled synthetic/public demonstration",
        "source_family": "gpbiometricspy kiosk demo",
        "participant_identifier": "participant_id" if "participant_id" in dat.columns else None,
        "session_identifier": None,
        "run_identifier": None,
        "trial_identifier": "MEDIA_ID" if "MEDIA_ID" in dat.columns else None,
        "primary_time_field": "TIME" if "TIME" in dat.columns else None,
        "declared_time_unit": None,
        "clock_owner": None,
        "acquisition_device": None,
        "configured_sampling_rate_hz": None,
        "event_source": "TTL0" if "TTL0" in dat.columns else None,
        "analysis_target": None,
        "privacy_boundary": "synthetic demonstration only; do not place direct participant identifiers in public metadata",
        "review_status": "REVIEW",
        "note": "Blank scientific declarations are intentional. Verify them from acquisition/protocol evidence before analysis.",
    }
    metadata_path = out / "study-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    rows: list[dict[str, object]] = []
    for column in dat.columns:
        series = dat[column]
        rows.append(
            {
                "source_column": column,
                "dtype": str(series.dtype),
                "missing_fraction": float(series.isna().mean()),
                "n_unique": int(series.nunique(dropna=True)),
                "example_value": _example_value(series),
                "declared_role": "",
                "declared_unit": "",
                "clock_owner": "",
                "derivation": "",
                "validity_semantics": "",
                "review_status": "REVIEW",
                "notes": "",
            }
        )

    variable_dictionary = pd.DataFrame(rows)
    variable_path = out / "variable-dictionary.csv"
    variable_dictionary.to_csv(variable_path, index=False)

    event_rows: list[dict[str, object]] = []
    for field in [name for name in dat.columns if str(name).upper().startswith("TTL")]:
        event_rows.append(
            {
                "source_event_field": field,
                "event_code": "",
                "event_label": "",
                "edge_or_state": "",
                "clock_owner": "",
                "grouping_unit": "",
                "expected_count_per_unit": "",
                "tolerance_or_window": "",
                "review_status": "REVIEW",
                "notes": "Do not infer event meaning from code order or field name.",
            }
        )
    if not event_rows:
        event_rows.append(
            {
                "source_event_field": "",
                "event_code": "",
                "event_label": "",
                "edge_or_state": "",
                "clock_owner": "",
                "grouping_unit": "",
                "expected_count_per_unit": "",
                "tolerance_or_window": "",
                "review_status": "REVIEW",
                "notes": "No TTL-prefixed field detected in the bounded demonstration slice.",
            }
        )

    event_dictionary = pd.DataFrame(event_rows)
    event_path = out / "event-dictionary.csv"
    event_dictionary.to_csv(event_path, index=False)

    artifacts = [metadata_path, variable_path, event_path]
    manifest = {
        "workflow": TUTORIAL,
        "status": "REVIEW",
        "synthetic_or_template_only": True,
        "gpbiometricspy": gp.__version__,
        "python": platform.python_version(),
        "source_rows": int(len(dat)),
        "source_columns": int(dat.shape[1]),
        "scientific_declarations_autofilled": False,
        "artifacts": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in artifacts
        },
    }
    manifest_path = out / "dictionary-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "tutorial": TUTORIAL,
                "status": "PASS",
                "output_dir": str(out),
                "variable_rows": int(len(variable_dictionary)),
                "event_rows": int(len(event_dictionary)),
                "artifact_count": 4,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
