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


def _write_frame(root: Path, name: str, value: Any) -> str | None:
    """Write a dataframe-like object when the workflow actually produced one."""
    to_csv = getattr(value, "to_csv", None)
    if not callable(to_csv):
        return None
    path = root / name
    to_csv(path, index=False)
    return path.name


def main() -> None:
    """Build a deterministic, reviewable research-evidence bundle."""
    data = demo(1800)
    groups = ["participant_id"]

    # 1. Retain the study design independently from sample-level data.
    design = gp.kiosk_demo_trial_design()
    design = design.loc[
        design["participant_id"].astype(str).eq("synthetic_kiosk_p001")
    ].reset_index(drop=True)

    # 2. Establish basic quality and timing evidence before deriving measures.
    activity = gp.audit_gazepoint_signal_activity(
        data,
        signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
        group_cols=groups,
    )
    time_resets = gp.audit_gazepoint_time_resets(
        data,
        time_col="TIME",
        group_cols=groups,
    )

    # 3. Extract event identity and construct explicit event-relative windows.
    ttl_events = gp.extract_gazepoint_ttl_events(
        data,
        ttl_columns=["TTL0"],
        group_columns=groups,
    )
    alignment = gp.align_gazepoint_biometrics_to_ttl(
        data,
        ttl_cols=["TTL0"],
        time_col="TIME",
        group_cols=groups,
        pre_window_ms=250,
        post_window_ms=500,
    )

    # 4. Produce event-relative descriptive summaries from recorded channels.
    eventlocked = gp.summarize_gazepoint_eventlocked_multimodal(
        data,
        events=ttl_events,
        time_col="TIME",
        event_time_col="TIME",
        signal_cols=["GSR_US", "HR", "LPMM"],
        group_cols=groups,
        pre_s=0.25,
        post_s=0.50,
        baseline_window_s=(-0.25, 0.0),
        summary_window_s=(0.0, 0.50),
    )

    # 5. Keep a visual checkpoint on the same recorded timeline.
    timeline = gp.plot_gazepoint_multimodal_timeline(
        data,
        time_col="TIME",
        signal_cols=["GSR_US", "HR", "LPMM"],
        group_cols=groups,
        title="Research evidence bundle: recorded multimodal timeline",
    )

    # 6. Finish with report/replay evidence and explicit software identity.
    checklist = gp.create_gazepoint_biometrics_checklist(data)
    methods_text = gp.create_gazepoint_biometrics_methods_text(checklist=checklist)
    software = {
        "gpbiometricspy": gp.__version__,
        "python": platform.python_version(),
    }

    output = os.environ.get("GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR")
    if output:
        root = Path(output)
        root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []

        for filename, value in (
            ("study_design.csv", design),
            ("signal_activity_overview.csv", activity.get("overview")),
            ("signal_activity_by_group.csv", activity.get("signal_by_group")),
            ("time_reset_overview.csv", time_resets.get("overview")),
            ("time_reset_segments.csv", time_resets.get("segment_summary")),
            ("time_reset_flags.csv", time_resets.get("row_flags")),
            ("ttl_events.csv", ttl_events),
            ("alignment_overview.csv", alignment.get("overview")),
            ("alignment_events.csv", alignment.get("events")),
            ("aligned_data.csv", alignment.get("aligned_data")),
            ("eventlocked_summary.csv", eventlocked.get("summary")),
            ("eventlocked_samples.csv", eventlocked.get("samples")),
            ("analysis_checklist_overview.csv", checklist.get("overview")),
        ):
            saved = _write_frame(root, filename, value)
            if saved is not None:
                written.append(saved)

        (root / "software.json").write_text(
            json.dumps(software, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (root / "methods_text.txt").write_text(methods_text + "\n", encoding="utf-8")
        written.extend(
            [
                "software.json",
                "methods_text.txt",
                "research-evidence-bundle-01.png",
            ]
        )

        manifest = {
            "workflow": "research-evidence-bundle",
            "synthetic_demo": True,
            "participant": "synthetic_kiosk_p001",
            "artifacts": sorted(written),
            "interpretation_boundary": (
                "Artifacts document recorded/derived quantities and workflow provenance; "
                "they do not establish latent psychological states, diagnosis, causality, "
                "or hardware-level synchronization."
            ),
        }
        (root / "evidence_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    finish(
        "research-evidence-bundle",
        design=design,
        activity=activity,
        time_resets=time_resets,
        ttl_events=ttl_events,
        alignment=alignment,
        eventlocked=eventlocked,
        checklist=checklist,
        methods_text=methods_text,
        software=software,
        timeline=timeline,
    )


if __name__ == "__main__":
    main()
