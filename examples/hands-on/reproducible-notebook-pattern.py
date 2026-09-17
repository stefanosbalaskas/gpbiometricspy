from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

TUTORIAL_DIR = Path(__file__).resolve().parents[1] / "tutorials"
sys.path.insert(0, str(TUTORIAL_DIR))

from _shared import demo, finish, gp  # noqa: E402


# %% 1. Declare analysis choices in one place.
PARAMETERS = {
    "participant": "synthetic_kiosk_p001",
    "rows": 900,
    "signal_cols": ["GSR_US", "HR", "IBI", "LPMM"],
    "group_cols": ["participant_id"],
    "time_col": "TIME",
}


def _write_frame(root: Path, name: str, value: Any) -> str | None:
    to_csv = getattr(value, "to_csv", None)
    if not callable(to_csv):
        return None
    path = root / name
    to_csv(path, index=False)
    return path.name


# %% 2. Keep the scientific work in a reusable function.
def run_analysis(parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a deterministic synthetic workflow without relying on notebook state."""
    settings = dict(PARAMETERS if parameters is None else parameters)

    # Input loading is explicit and bounded. Replace only after validating a real export.
    data = demo(int(settings["rows"]))

    # QC precedes substantive feature derivation.
    activity = gp.audit_gazepoint_signal_activity(
        data,
        signal_cols=list(settings["signal_cols"]),
        group_cols=list(settings["group_cols"]),
    )
    timing = gp.audit_gazepoint_time_resets(
        data,
        time_col=str(settings["time_col"]),
        group_cols=list(settings["group_cols"]),
    )

    return {
        "parameters": settings,
        "data": data,
        "activity": activity,
        "timing": timing,
    }


# %% 3. Export reviewable evidence from explicit return values.
def write_evidence(bundle: dict[str, Any], root: Path) -> dict[str, Any]:
    """Write deterministic evidence artifacts and return the manifest payload."""
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    activity = bundle["activity"]
    timing = bundle["timing"]
    for filename, value in (
        ("signal_activity_overview.csv", activity.get("overview")),
        ("signal_activity_by_group.csv", activity.get("signal_by_group")),
        ("time_reset_overview.csv", timing.get("overview")),
        ("time_reset_segments.csv", timing.get("segment_summary")),
    ):
        saved = _write_frame(root, filename, value)
        if saved is not None:
            written.append(saved)

    parameters_path = root / "analysis_parameters.json"
    parameters_path.write_text(
        json.dumps(bundle["parameters"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    written.append(parameters_path.name)

    software = {
        "gpbiometricspy": gp.__version__,
        "python": platform.python_version(),
    }
    software_path = root / "software.json"
    software_path.write_text(
        json.dumps(software, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    written.append(software_path.name)

    manifest = {
        "workflow": "reproducible-notebook-pattern",
        "synthetic_demo": True,
        "participant": bundle["parameters"]["participant"],
        "rows_requested": int(bundle["parameters"]["rows"]),
        "rows_loaded": int(len(bundle["data"])),
        "artifacts": sorted(written),
        "execution_contract": (
            "All analysis results are produced from declared parameters by run_analysis(); "
            "write_evidence() receives those explicit return values and does not depend on "
            "hidden notebook state."
        ),
        "interpretation_boundary": (
            "The artifacts document recorded/derived quantities, QC and execution provenance; "
            "they do not establish latent psychological states, causality, diagnosis, or "
            "hardware-level synchronization."
        ),
    }
    manifest_path = root / "notebook_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


# %% 4. A notebook cell can call the same function; CI can run the whole file.
def main() -> None:
    bundle = run_analysis()
    output = os.environ.get("GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR")
    manifest = None
    if output:
        manifest = write_evidence(bundle, Path(output))

    finish(
        "reproducible-notebook-pattern",
        parameters=bundle["parameters"],
        activity=bundle["activity"],
        timing=bundle["timing"],
        manifest=manifest,
    )


if __name__ == "__main__":
    main()
