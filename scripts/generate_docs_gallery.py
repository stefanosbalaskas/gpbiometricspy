from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "gpbiometricspy-docs-gallery"
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

import gpbiometricspy as gp

DEFAULT_OUTPUT = ROOT / "docs" / "assets" / "generated"


def _figure(obj: Any) -> Figure:
    if isinstance(obj, Figure):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("figure"), Figure):
            return obj["figure"]
        plots = obj.get("plots")
        if isinstance(plots, dict):
            for value in plots.values():
                if isinstance(value, Figure):
                    return value
    raise TypeError(f"Could not extract matplotlib Figure from {type(obj).__name__}")


def _save(obj: Any, path: Path) -> None:
    fig = _figure(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        format="png",
        dpi=160,
        bbox_inches="tight",
        metadata={
            "Date": "2026-08-28",
            "Creator": f"gpbiometricspy {gp.__version__}",
            "Description": "Generated from bundled synthetic/public demonstration data.",
        },
    )
    plt.close(fig)


def generate(output_dir: Path) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)

    demo = (
        gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
        .copy()
        .iloc[:1800]
        .reset_index(drop=True)
    )

    entries: list[tuple[str, str, str, Any]] = []

    entries.append(
        (
            "missingness",
            "Missingness overview",
            "Missingness across EDA, heart-rate and IBI channels.",
            gp.plot_gazepoint_missingness(
                demo,
                cols=["GSR_US", "HR", "IBI", "LPMM"],
                time_col="TIME",
            ),
        )
    )

    entries.append(
        (
            "biometric-signals",
            "Biometric signal overview",
            "EDA and heart-rate traces from the bundled kiosk demonstration.",
            gp.plot_gazepoint_biometric_signals(
                demo,
                signal_cols=["GSR_US", "HR"],
                time_col="TIME",
                standardize=True,
                main="Standardised EDA and heart-rate signals",
            ),
        )
    )

    entries.append(
        (
            "pupil-gaze-overview",
            "Pupil and gaze overview",
            "Standardised pupil diameter and gaze coordinates for one synthetic participant.",
            gp.plot_gazepoint_biometric_signals(
                demo,
                signal_cols=["LPMM", "FPOGX", "FPOGY"],
                time_col="TIME",
                standardize=True,
                main="Pupil diameter and gaze-position overview",
            ),
        )
    )

    entries.append(
        (
            "multimodal-timeline",
            "Multimodal timeline",
            "Synchronous EDA, heart-rate and pupil channels with event markers.",
            gp.plot_gazepoint_multimodal_timeline(
                demo,
                time_col="TIME",
                signal_cols=["GSR_US", "HR", "LPMM"],
                group_cols=["participant_id"],
                title="Multimodal Gazepoint timeline",
            ),
        )
    )

    entries.append(
        (
            "eda-decomposition",
            "EDA decomposition",
            "Observed, tonic and phasic electrodermal components.",
            gp.plot_gazepoint_eda_decomposition(
                demo,
                time_col="TIME",
                signal_cols=["GSR_US"],
                group_cols=["participant_id"],
                title="EDA decomposition",
            ),
        )
    )

    scr = gp.detect_gazepoint_scr_events(
        demo,
        phasic_col="GSR_US_PHASIC",
        signal_col="GSR_US",
        time_col="TIME",
        group_cols=["participant_id"],
        threshold=0.02,
        min_peak_distance=30,
    )
    entries.append(
        (
            "scr-events",
            "SCR event detection",
            "Detected skin-conductance responses over the EDA trace.",
            gp.plot_gazepoint_scr_events(
                demo,
                scr["events"],
                time_col="TIME",
                signal_col="GSR_US",
                phasic_col="GSR_US_PHASIC",
                group_cols=["participant_id"],
                title="Detected SCR events",
            ),
        )
    )

    simulated = gp.simulate_gazepoint_biometrics(
        n_seconds=30,
        sampling_rate=60,
        seed=42,
    )["data"]
    detection = gp.detect_gazepoint_ppg_peaks(
        simulated,
        signal_col="HRP",
        time_col="CNT",
        group_cols=["participant_id"],
        sampling_rate_hz=60,
    )
    entries.append(
        (
            "ppg-peak-detection",
            "PPG peak detection",
            "Pulse waveform with detected peaks from the deterministic synthetic generator.",
            gp.plot_gazepoint_ppg_peak_detection(detection),
        )
    )

    rr_ms = (demo["IBI"].dropna().iloc[::60] * 1000.0).to_numpy()
    entries.append(
        (
            "ppg-poincare",
            "Poincaré plot",
            "Successive RR-interval geometry for HRV quality inspection.",
            gp.plot_gazepoint_ppg_poincare(rr_ms=rr_ms),
        )
    )
    entries.append(
        (
            "hrv-tachogram",
            "HRV tachogram",
            "Beat-to-beat interval trajectory using the pyHRV-style visual interface.",
            gp.plot_gazepoint_pyhrv_tachogram(rr_ms),
        )
    )

    aoi = gp.summarise_gazepoint_aoi_biometrics(
        demo,
        aoi_col="AOI",
        signal_cols=["GSR_US", "HR", "LPMM"],
        group_cols=["participant_id"],
    )
    entries.append(
        (
            "aoi-biometrics",
            "AOI-linked biometrics",
            "AOI summaries for EDA, heart-rate and pupil channels.",
            gp.plot_gazepoint_aoi_biometrics(
                aoi["summary"],
                value_col="mean_value",
                aoi_col="aoi_label",
                signal_col="signal",
                title="AOI-linked biometric summaries",
            ),
        )
    )

    quality = gp.audit_gazepoint_gsr_quality(demo, value_column="GSR_US")
    entries.append(
        (
            "signal-quality",
            "Signal-quality summary",
            "Missingness-based EDA quality diagnostic from the core QC family.",
            gp.plot_gazepoint_signal_quality(
                quality,
                metric="missing_pct",
                x="signal",
            ),
        )
    )

    edagram = gp.plot_gazepoint_eda_gram(
        demo,
        eda_col="GSR_US",
        time_col="CNT",
        group_cols=["participant_id"],
        group_id_to_plot="synthetic_kiosk_p001",
        sampling_rate=60,
        window_seconds=5,
        step_seconds=1,
        main="EDA time-frequency diagnostic",
    )
    entries.append(
        (
            "eda-gram",
            "EDA-gram",
            "Time-frequency representation of the electrodermal signal.",
            edagram,
        )
    )

    amplitude = np.linspace(0.2, 12.0, 120)
    saccades = pd.DataFrame(
        {
            "amplitude_deg": amplitude,
            "peak_velocity_dps": 80.0
            + 180.0 * np.sqrt(amplitude)
            + 25.0 * np.sin(np.linspace(0.0, 10.0, amplitude.size)),
        }
    )
    entries.append(
        (
            "saccade-main-sequence",
            "Saccade main sequence",
            "Deterministic amplitude/peak-velocity diagnostic for gaze QC.",
            gp.plot_gazepoint_saccade_main_sequence(
                saccades,
                amplitude_col="amplitude_deg",
                peak_velocity_col="peak_velocity_dps",
                main="Saccade main-sequence diagnostic",
            ),
        )
    )

    manifest: list[dict[str, str]] = []
    for slug, title, description, obj in entries:
        path = output_dir / f"{slug}.png"
        _save(obj, path)
        manifest.append(
            {
                "slug": slug,
                "title": title,
                "description": description,
                "file": f"{slug}.png",
            }
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "package_version": gp.__version__,
                "source": "bundled synthetic/public demonstration data",
                "figures": manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic PNG figures for the gpbiometricspy documentation gallery."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory receiving PNG figures and manifest.json.",
    )
    args = parser.parse_args()
    manifest = generate(args.output_dir)
    print(f"generated {len(manifest)} documentation figures in {args.output_dir}")


if __name__ == "__main__":
    main()
