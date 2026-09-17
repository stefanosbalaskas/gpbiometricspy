from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(
    os.environ.get(
        "GPBIOMETRICSPY_PROJECT_DIR",
        "artifacts/tutorials/research-project-scaffold",
    )
)

DIRECTORIES = [
    "raw",
    "metadata",
    "mappings",
    "qc",
    "events",
    "derived",
    "models",
    "figures",
    "reports",
    "manifests",
    "logs",
]

for name in DIRECTORIES:
    (ROOT / name).mkdir(parents=True, exist_ok=True)

readme = """# gpbiometricspy research project scaffold

This directory separates immutable/source material from mapping decisions,
quality evidence, event/alignment evidence, derived data, model outputs,
figures, reports, manifests, and logs.

- `raw/`: source exports. Keep immutable and private when required.
- `metadata/`: acquisition notes, design tables, dictionaries, and device settings.
- `mappings/`: source-to-analysis column/event/AOI mappings.
- `qc/`: schema, missingness, signal activity, unit, and timebase evidence.
- `events/`: extracted markers, alignment tables, and event-window evidence.
- `derived/`: analysis-ready tables created from documented transformations.
- `models/`: model specifications, certificates, diagnostics, and predictions.
- `figures/`: reviewable visual checkpoints and final figures.
- `reports/`: methods text, summaries, tables, and manuscript-ready outputs.
- `manifests/`: software/configuration/evidence manifests tying outputs together.
- `logs/`: run logs and warnings that help reproduce or diagnose a workflow.

Do not commit private participant exports merely because this scaffold exists.
Use your project or institution's access, encryption, retention, and sharing rules.
"""
(ROOT / "README.md").write_text(readme, encoding="utf-8")

raw_readme = """# Raw source data

Place source exports here only when your data-governance rules permit it.
Treat source files as immutable. Do not overwrite them with cleaned or renamed data.
Record source identity/checksums externally or in a manifest when appropriate.
"""
(ROOT / "raw" / "README.md").write_text(raw_readme, encoding="utf-8")

mapping_template = """original_name,analysis_name,role,unit,source,verified,notes
subject_id,participant_id,identifier,,,false,
timestamp_s,TIME,time,seconds,,false,
eda_us,GSR_US,signal,microsiemens,,false,
event_marker,TTL,event,,,false,
"""
(ROOT / "mappings" / "column-mapping-template.csv").write_text(
    mapping_template, encoding="utf-8"
)

analysis_config = {
    "participant_columns": [],
    "session_columns": [],
    "trial_columns": [],
    "time_column": None,
    "counter_column": None,
    "signal_columns": [],
    "validity_columns": [],
    "event_columns": [],
    "sampling_rate_hz": None,
    "time_unit": None,
    "coordinate_space": None,
    "notes": [
        "Populate only after checking the actual export and acquisition documentation.",
        "Do not infer units, event semantics, or synchronization accuracy from names alone.",
    ],
}
(ROOT / "metadata" / "analysis-config.json").write_text(
    json.dumps(analysis_config, indent=2, sort_keys=True), encoding="utf-8"
)

manifest = {
    "workflow": "research-project-scaffold",
    "synthetic_or_template_only": True,
    "directories": DIRECTORIES,
    "required_review_before_analysis": [
        "source identity and access rules",
        "participant/session/trial identifiers",
        "column mapping",
        "units and validity semantics",
        "timebase and sampling evidence",
        "event semantics and clock ownership",
        "QC outputs and exclusion decisions",
    ],
    "evidence_boundary": (
        "A well-structured project directory improves provenance and reviewability; "
        "it does not establish measurement validity, synchronization accuracy, causal "
        "identification, diagnosis, or psychological interpretation."
    ),
}
(ROOT / "manifests" / "project-scaffold.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
)

print(
    json.dumps(
        {
            "tutorial": "research-project-scaffold",
            "status": "PASS",
            "project_dir": str(ROOT),
            "directory_count": len(DIRECTORIES),
        },
        sort_keys=True,
    )
)
