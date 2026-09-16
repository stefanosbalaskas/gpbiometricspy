from __future__ import annotations

import os
import sys
from pathlib import Path

TUTORIAL_DIR = Path(__file__).resolve().parents[1] / "tutorials"
sys.path.insert(0, str(TUTORIAL_DIR))

from _shared import demo, finish, gp  # noqa: E402


def main() -> None:
    """Run a complete, deterministic EDA/SCR teaching workflow."""
    data = demo(1800)
    groups = ["participant_id"]

    # 1. Establish measurement and timing evidence before deriving features.
    units = gp.audit_gazepoint_gsr_units(data, gsr_col="GSR_US")
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
    quality = gp.audit_gazepoint_gsr_quality(data, value_column="GSR_US")
    artifacts = gp.audit_gazepoint_eda_artifacts(
        data,
        signal_col="GSR_US",
        time_col="TIME",
        group_cols=groups,
    )

    # 2. Create explicit tonic/phasic components.
    decomposition = gp.decompose_gazepoint_eda(
        data,
        signal_col="GSR_US",
        time_col="TIME",
        group_cols=groups,
        window_size=31,
        output_prefix="eda",
    )

    # 3. Detect descriptive SCR-like local peaks from the derived phasic signal.
    scr = gp.detect_gazepoint_scr_events(
        decomposition,
        phasic_col="eda_phasic",
        signal_col="GSR_US",
        time_col="TIME",
        group_cols=groups,
        threshold=None,
        min_peak_distance=10,
    )

    # 4. Retain visual evidence for review.
    decomposition_plot = gp.plot_gazepoint_eda_decomposition(
        decomposition,
        time_col="TIME",
        signal_cols=["GSR_US", "eda_tonic", "eda_phasic"],
        group_cols=groups,
        title="Observed, tonic and phasic EDA",
    )
    scr_plot = gp.plot_gazepoint_scr_events(
        decomposition,
        scr["events"],
        time_col="TIME",
        signal_col="GSR_US",
        phasic_col="eda_phasic",
        group_cols=groups,
        title="Candidate SCR events",
    )

    # 5. Generate reporting evidence rather than leaving methods implicit.
    checklist = gp.create_gazepoint_biometrics_checklist(data)
    methods_text = gp.create_gazepoint_biometrics_methods_text(checklist=checklist)

    # Optional export: set GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR to keep artifacts.
    output = os.environ.get("GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR")
    if output:
        root = Path(output)
        root.mkdir(parents=True, exist_ok=True)
        keep = ["participant_id", "TIME", "GSR_US", "eda_tonic", "eda_phasic"]
        decomposition.loc[:, keep].to_csv(root / "eda_decomposition.csv", index=False)
        scr["events"].to_csv(root / "scr_events.csv", index=False)
        scr["group_summary"].to_csv(root / "scr_group_summary.csv", index=False)
        checklist["overview"].to_csv(root / "analysis_checklist_overview.csv", index=False)
        (root / "methods_text.txt").write_text(methods_text + "\n", encoding="utf-8")

    finish(
        "end-to-end-eda-research",
        units=units,
        activity=activity,
        time_resets=time_resets,
        quality=quality,
        artifacts=artifacts,
        decomposition=decomposition,
        scr=scr,
        checklist=checklist,
        methods_text=methods_text,
        decomposition_plot=decomposition_plot,
        scr_plot=scr_plot,
    )


if __name__ == "__main__":
    main()
