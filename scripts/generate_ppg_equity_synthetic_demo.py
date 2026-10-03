from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ACTIVITY_EFFECT = {"Rest": 0.0, "Typing": 8.0, "Walk": 34.0}
ACTIVITY_NOISE = {"Rest": 1.4, "Typing": 2.4, "Walk": 5.0}
ACTIVITY_DROPOUT = {"Rest": 0.0, "Typing": 0.35, "Walk": 1.05}


def expit(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-np.asarray(x)))


def generate_synthetic_ppg_equity(
    *,
    seed: int = 20261003,
    n_participants: int = 36,
    sampling_rate_hz: int = 60,
    seconds_per_activity: int = 6,
) -> pd.DataFrame:
    """Create an educational stress-test dataset with known synthetic mechanisms.

    The data-generating process deliberately makes signal retention depend on ITA
    while candidate heart-rate error depends on activity, not ITA. This is a
    didactic construction for testing measurement-accountability logic; it is not
    a model of human biology and should never be interpreted as one.
    """
    rng = np.random.default_rng(seed)
    activities = tuple(ACTIVITY_EFFECT)
    n_samples = sampling_rate_hz * seconds_per_activity
    rows: list[pd.DataFrame] = []

    ita_values = np.linspace(-20.0, 70.0, n_participants) + rng.normal(0, 1.25, n_participants)
    base_hr_values = rng.normal(64.0, 6.0, n_participants)

    for p_idx, (ita, base_hr) in enumerate(zip(ita_values, base_hr_values), start=1):
        participant = f"P{p_idx:03d}"
        b_star = float(rng.normal(18.0, 0.7))
        l_star = float(50.0 + b_star * np.tan(np.deg2rad(ita)))
        l_star = float(np.clip(l_star, 3.0, 97.0))
        phase0 = float(rng.uniform(0, 2 * np.pi))

        for activity in activities:
            t = np.arange(n_samples, dtype=float) / sampling_rate_hz
            ref_hr = base_hr + ACTIVITY_EFFECT[activity] + 1.8 * np.sin(
                2 * np.pi * t / max(seconds_per_activity, 1)
            )
            pulse_hz = ref_hr / 60.0
            phase = phase0 + 2 * np.pi * np.cumsum(pulse_hz) / sampling_rate_hz

            # Synthetic acquisition mechanism: lower ITA and motion increase dropout.
            dropout_logit = -3.05 - 0.030 * ita + ACTIVITY_DROPOUT[activity]
            dropout_prob = float(expit(dropout_logit))

            # Synthetic amplitude mechanism used only to stress SQIs.
            amplitude = 0.045 + 0.00035 * (ita + 20.0)
            noise_sd = 0.010 + {"Rest": 0.0, "Typing": 0.006, "Walk": 0.020}[activity]
            waveform = (
                1.0
                + amplitude * np.sin(phase)
                + 0.30 * amplitude * np.sin(2.0 * phase + 0.4)
                + rng.normal(0.0, noise_sd, n_samples)
            )
            dropout = rng.random(n_samples) < dropout_prob
            if activity == "Walk":
                burst_start = int(1.8 * sampling_rate_hz)
                burst_stop = min(n_samples, burst_start + int(0.35 * sampling_rate_hz))
                dropout[burst_start:burst_stop] = True
            waveform[dropout] = np.nan

            # Error depends on activity only; pigmentation does not enter the error SD.
            candidate_hr = ref_hr + rng.normal(0.0, ACTIVITY_NOISE[activity], n_samples)
            candidate_dropout_prob = float(expit(-3.45 - 0.025 * ita + ACTIVITY_DROPOUT[activity]))
            candidate_missing = rng.random(n_samples) < candidate_dropout_prob
            candidate_hr[candidate_missing] = np.nan

            rows.append(
                pd.DataFrame(
                    {
                        "participant": participant,
                        "activity": activity,
                        "time_s": t,
                        "HRP": waveform,
                        "ecg_hr": ref_hr,
                        "ppg_hr": candidate_hr,
                        "ita_degrees": ita,
                        "skin_L_star": l_star,
                        "skin_a_star": 7.5 + rng.normal(0, 0.15, n_samples),
                        "skin_b_star": b_star,
                        "pigmentation_site": "finger",
                        "sensor_site": "finger",
                        "instrument_vendor": "SyntheticColorimetry",
                        "instrument_model": "SIM-2026",
                        "device": "SyntheticPPG-1",
                    }
                )
            )

    return pd.concat(rows, ignore_index=True)


def _participant_activity_summary(data: pd.DataFrame) -> pd.DataFrame:
    d = data.copy()
    d["retained_hr"] = d["ecg_hr"].notna() & d["ppg_hr"].notna()
    d["abs_error"] = (d["ppg_hr"] - d["ecg_hr"]).abs()
    return d.groupby(["participant", "activity", "ita_degrees"], as_index=False).agg(
        waveform_available=("HRP", lambda x: float(x.notna().mean())),
        hr_retention=("retained_hr", "mean"),
        mae_bpm=("abs_error", "mean"),
    )


def _bin_summary(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    out["ita_bin"] = pd.cut(
        out["ita_degrees"],
        bins=[-100, -5, 20, 45, 100],
        labels=["lower ITA", "low-mid ITA", "mid-high ITA", "higher ITA"],
        include_lowest=True,
    )
    return out.groupby(["activity", "ita_bin"], observed=True, as_index=False).agg(
        hr_retention=("hr_retention", "mean"),
        mae_bpm=("mae_bpm", "mean"),
        waveform_available=("waveform_available", "mean"),
    )


def _svg_line_chart(
    series: list[tuple[str, np.ndarray, np.ndarray]],
    *,
    title: str,
    x_label: str,
    y_label: str,
    width: int = 900,
    height: int = 520,
    y_limits: tuple[float, float] | None = None,
    show_points: bool = True,
) -> str:
    left, right, top, bottom = 88, 28, 58, 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    all_x = np.concatenate([x for _, x, _ in series])
    all_y = np.concatenate([y[np.isfinite(y)] for _, _, y in series if np.isfinite(y).any()])
    xmin, xmax = float(np.nanmin(all_x)), float(np.nanmax(all_x))
    if y_limits is None:
        ymin, ymax = float(np.nanmin(all_y)), float(np.nanmax(all_y))
        pad = 0.08 * max(ymax - ymin, 1e-9)
        ymin, ymax = ymin - pad, ymax + pad
    else:
        ymin, ymax = y_limits

    def sx(x):
        return left + (np.asarray(x) - xmin) / max(xmax - xmin, 1e-12) * plot_w

    def sy(y):
        return top + (ymax - np.asarray(y)) / max(ymax - ymin, 1e-12) * plot_h

    palette = ["#2563eb", "#059669", "#d97706", "#7c3aed"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        '<style>text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;fill:#111827}'
        '.grid{stroke:#e5e7eb;stroke-width:1}.axis{stroke:#374151;stroke-width:1.2}'
        '.series{fill:none;stroke-width:2}.pt{stroke-width:0}.legend{font-size:14px}.tick{font-size:12px}</style>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-size="20" font-weight="600">{title}</text>',
    ]
    for frac in np.linspace(0, 1, 6):
        x = left + frac * plot_w
        xv = xmin + frac * (xmax - xmin)
        parts.append(f'<line class="grid" x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top+plot_h}"/>')
        parts.append(f'<text class="tick" x="{x:.2f}" y="{top+plot_h+22}" text-anchor="middle">{xv:.0f}</text>')
    for frac in np.linspace(0, 1, 6):
        y = top + (1 - frac) * plot_h
        yv = ymin + frac * (ymax - ymin)
        parts.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}"/>')
        parts.append(f'<text class="tick" x="{left-10}" y="{y+4:.2f}" text-anchor="end">{yv:.2f}</text>')
    parts += [
        f'<line class="axis" x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}"/>',
        f'<text x="{left+plot_w/2:.1f}" y="{height-18}" text-anchor="middle" font-size="14">{x_label}</text>',
        f'<text transform="translate(20 {top+plot_h/2:.1f}) rotate(-90)" text-anchor="middle" font-size="14">'
        f'{y_label}</text>',
    ]
    for idx, (label, x, y) in enumerate(series):
        color = palette[idx % len(palette)]
        keep = np.isfinite(x) & np.isfinite(y)
        xp, yp = sx(x[keep]), sy(y[keep])
        points = " ".join(f"{a:.2f},{b:.2f}" for a, b in zip(xp, yp))
        parts.append(f'<polyline class="series" stroke="{color}" points="{points}"/>')
        if show_points:
            for a, b in zip(xp, yp):
                parts.append(f'<circle class="pt" fill="{color}" cx="{a:.2f}" cy="{b:.2f}" r="2.5"/>')
        lx = left + plot_w - 155
        ly = top + 18 + idx * 22
        parts.append(
            f'<line x1="{lx}" y1="{ly-4}" x2="{lx+20}" y2="{ly-4}" stroke="{color}" stroke-width="2"/>'
        )
        parts.append(f'<text class="legend" x="{lx+27}" y="{ly}">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_figures(data: pd.DataFrame, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = _participant_activity_summary(data)
    bins = _bin_summary(summary)

    retention_series = []
    error_series = []
    for activity, g in summary.groupby("activity", sort=False):
        g = g.sort_values("ita_degrees")
        retention_series.append((activity, g["ita_degrees"].to_numpy(float), g["hr_retention"].to_numpy(float)))
        error_series.append((activity, g["ita_degrees"].to_numpy(float), g["mae_bpm"].to_numpy(float)))

    retention_path = output_dir / "ppg-equity-synthetic-retention.svg"
    retention_path.write_text(
        _svg_line_chart(
            retention_series,
            title="Synthetic retention varies while accuracy mechanism is ITA-neutral",
            x_label="Synthetic ITA (degrees)",
            y_label="Candidate-HR retention",
            y_limits=(0.0, 1.0),
            show_points=False,
        ),
        encoding="utf-8",
    )

    error_path = output_dir / "ppg-equity-synthetic-reference-error.svg"
    error_path.write_text(
        _svg_line_chart(
            error_series,
            title="Synthetic reference error is driven by activity, not ITA",
            x_label="Synthetic ITA (degrees)",
            y_label="Mean absolute HR error (bpm)",
            show_points=False,
        ),
        encoding="utf-8",
    )

    rest = data[data["activity"] == "Rest"]
    participant_ita = rest.groupby("participant")["ita_degrees"].first().sort_values()
    chosen = [participant_ita.index[1], participant_ita.index[len(participant_ita) // 2], participant_ita.index[-2]]
    waveform_series = []
    for participant in chosen:
        g = rest[rest["participant"] == participant].head(180).iloc[::2]
        ita = float(g["ita_degrees"].iloc[0])
        waveform_series.append(
            (f"{participant}: ITA={ita:.1f} deg", g["time_s"].to_numpy(float), g["HRP"].to_numpy(float))
        )
    waveform_path = output_dir / "ppg-equity-synthetic-waveforms.svg"
    waveform_path.write_text(
        _svg_line_chart(
            waveform_series,
            title="Synthetic raw-waveform examples used to exercise SQIs",
            x_label="Time (s)",
            y_label="Synthetic PPG amplitude (a.u.)",
            show_points=False,
        ),
        encoding="utf-8",
    )

    bins_path = output_dir / "ppg-equity-synthetic-bin-summary.csv"
    bins.to_csv(bins_path, index=False)
    summary_path = output_dir / "ppg-equity-synthetic-participant-summary.csv"
    summary.to_csv(summary_path, index=False)

    return {
        "retention_figure": retention_path.name,
        "reference_error_figure": error_path.name,
        "waveform_figure": waveform_path.name,
        "bin_summary": bins_path.name,
        "participant_summary": summary_path.name,
    }


def run_gpbiometricspy_audit(data: pd.DataFrame, output_dir: Path, *, n_boot: int, seed: int) -> dict:
    from gpbiometricspy.ppg_equity import ppg_pigmentation_audit

    result = ppg_pigmentation_audit(
        data,
        participant_col="participant",
        ppg_col="HRP",
        pigmentation_metric="cielab",
        l_star_col="skin_L_star",
        a_star_col="skin_a_star",
        b_star_col="skin_b_star",
        pigmentation_method="synthetic_colorimetry",
        pigmentation_site="pigmentation_site",
        sensor_site="sensor_site",
        instrument_manufacturer="instrument_vendor",
        instrument_model="instrument_model",
        time_col="time_s",
        group_cols=["activity"],
        sampling_rate_hz=60,
        reference_col="ecg_hr",
        candidate_col="ppg_hr",
        metric_name="heart_rate",
        device_col="device",
        condition_col="activity",
        n_boot=n_boot,
        random_state=seed,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    result["metadata"]["overview"].to_csv(output_dir / "audit-metadata-overview.csv", index=False)
    result["metadata"]["missingness"].to_csv(output_dir / "audit-metadata-missingness.csv", index=False)
    result["acquisition_quality"]["overview"].to_csv(output_dir / "audit-quality-overview.csv", index=False)
    result["acquisition_quality"]["group_quality"].to_csv(output_dir / "audit-group-quality.csv", index=False)
    result["acquisition_quality"]["associations"].to_csv(
        output_dir / "audit-quality-associations.csv", index=False
    )
    reference = result["reference_agreement"]
    if isinstance(reference, dict) and "agreement" in reference:
        reference["agreement"].to_csv(output_dir / "audit-reference-agreement.csv", index=False)
        reference["agreement_ci"].to_csv(output_dir / "audit-reference-agreement-ci.csv", index=False)
        reference["category_summary"].to_csv(output_dir / "audit-reference-by-pigmentation.csv", index=False)
        reference["associations"].to_csv(output_dir / "audit-reference-associations.csv", index=False)
        reference["retention_association"].to_csv(output_dir / "audit-retention-association.csv", index=False)
    report = {
        "synthetic_only": True,
        "reporting_text": result["reporting_text"],
        "warnings": list(result["warnings"]),
        "provenance": result["provenance"],
    }
    (output_dir / "audit-report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic gpbiometricspy PPG-equity synthetic worked example."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/assets/ppg-equity"))
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--participants", type=int, default=36)
    parser.add_argument("--n-boot", type=int, default=400)
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Generate synthetic data/figures without importing gpbiometricspy audit functions.",
    )
    parser.add_argument(
        "--write-data",
        action="store_true",
        help="Also write the synthetic row-level CSV; disabled by default to keep the repository compact.",
    )
    args = parser.parse_args()

    data = generate_synthetic_ppg_equity(seed=args.seed, n_participants=args.participants)
    artifacts = render_figures(data, args.output_dir)
    if args.write_data:
        data.to_csv(args.output_dir / "ppg-equity-synthetic-data.csv", index=False)
    if not args.render_only:
        artifacts["audit"] = run_gpbiometricspy_audit(data, args.output_dir, n_boot=args.n_boot, seed=args.seed)
    (args.output_dir / "ppg-equity-synthetic-manifest.json").write_text(
        json.dumps(artifacts, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
