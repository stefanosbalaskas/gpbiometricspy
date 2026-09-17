from __future__ import annotations

import json
import os
from pathlib import Path

import gpbiometricspy as gp


OUTPUT_DIR = Path(
    os.environ.get(
        "GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR",
        "artifacts/tutorials/bring-your-own-export",
    )
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Build a deterministic stand-in for an unfamiliar external CSV. The source
# values are synthetic; only the column labels are changed to demonstrate the
# adaptation workflow without distributing participant data.
source = (
    gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    .iloc[:960]
    .copy()
    .reset_index(drop=True)
)

custom = source[
    ["participant_id", "TIME", "GSR_US", "HR", "IBI", "TTL0", "TTLV"]
].rename(
    columns={
        "participant_id": "subject_id",
        "TIME": "timestamp_s",
        "GSR_US": "eda_us",
        "HR": "heart_rate",
        "IBI": "interbeat_interval",
        "TTL0": "event_marker",
        "TTLV": "ttl_validity",
    }
)
custom.to_csv(OUTPUT_DIR / "source_like_export.csv", index=False)

# Inspect the proposed mapping before changing any names.
name_map = gp.standardise_gazepoint_biometric_names(custom, rename=False)
name_map.to_csv(OUTPUT_DIR / "column_name_map.csv", index=False)

# Apply the package's conservative aliases only after the mapping is visible.
standard = gp.standardise_gazepoint_biometric_names(custom, rename=True)
required = {"USER", "TIME", "GSR_US", "HR", "IBI", "TTL", "TTLV"}
missing = required.difference(standard.columns)
if missing:
    raise RuntimeError(f"Expected standardized columns were not produced: {sorted(missing)}")

standard.head(120).to_csv(OUTPUT_DIR / "standardized_preview.csv", index=False)

schema = gp.detect_gazepoint_biometric_schema(standard)
schema["overview"].to_csv(OUTPUT_DIR / "schema_overview.csv", index=False)
schema["columns"].to_csv(OUTPUT_DIR / "schema_columns.csv", index=False)

timebase = gp.detect_gazepoint_biometric_timebase(standard, time_col="TIME")
timebase["overview"].to_csv(OUTPUT_DIR / "timebase_overview.csv", index=False)
timebase["interval_summary"].to_csv(
    OUTPUT_DIR / "timebase_interval_summary.csv", index=False
)

events = gp.extract_gazepoint_ttl_events(
    standard,
    ttl_columns=["TTL"],
    group_columns=["USER"],
    validity_column="TTLV",
    require_validity=True,
)
events.to_csv(OUTPUT_DIR / "ttl_events.csv", index=False)

manifest = {
    "workflow": "bring-your-own-export",
    "synthetic_demo": True,
    "source_rows": int(len(custom)),
    "mapping": {
        row.original_name: row.standard_name
        for row in name_map.itertuples(index=False)
    },
    "required_standard_columns": sorted(required),
    "timebase_status": str(timebase["overview"].iloc[0]["status"]),
    "ttl_event_count": int(len(events)),
    "evidence_boundary": (
        "Column-name recognition does not prove units, channel activity, event semantics, "
        "clock synchronization, validity, or suitability for a scientific claim."
    ),
    "artifacts": [
        "source_like_export.csv",
        "column_name_map.csv",
        "standardized_preview.csv",
        "schema_overview.csv",
        "schema_columns.csv",
        "timebase_overview.csv",
        "timebase_interval_summary.csv",
        "ttl_events.csv",
        "adaptation_manifest.json",
    ],
}
(OUTPUT_DIR / "adaptation_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
)

print(
    json.dumps(
        {
            "tutorial": "bring-your-own-export",
            "status": "PASS",
            "output_dir": str(OUTPUT_DIR),
            "ttl_events": int(len(events)),
        },
        sort_keys=True,
    )
)
