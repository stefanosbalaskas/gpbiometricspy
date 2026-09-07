"""Measurement-accountability tools for gpbiometricspy.

Agreement is metric-specific, low SCR responsivity remains analyzable, and
PPG topology is explicitly treated as a structural descriptor rather than a
direct physiological surrogate.
"""
from __future__ import annotations

from typing import Mapping, Sequence
import math


def _finite_pairs(a, b):
    out = []
    for x, y in zip(a, b):
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            out.append((x, y))
    return out


def _mean(x):
    return sum(x) / len(x)


def _var(x, m=None):
    if len(x) < 2:
        return math.nan
    m = _mean(x) if m is None else m
    return sum((v - m) ** 2 for v in x) / (len(x) - 1)


def _quantile(x, q):
    xs = sorted(x)
    if not xs:
        return math.nan
    p = (len(xs) - 1) * q
    lo, hi = int(math.floor(p)), int(math.ceil(p))
    return xs[lo] if lo == hi else xs[lo] + (p - lo) * (xs[hi] - xs[lo])


def compare_hrv_prv_devices(
    reference: Sequence[float],
    candidate: Sequence[float],
    *,
    metric: str,
    reference_source: str = "ECG-HRV",
    candidate_source: str = "PPG-PRV",
    reference_site: str | None = None,
    candidate_site: str | None = None,
) -> dict:
    """Audit agreement for one HR/HRV/PRV metric and acquisition configuration.

    Reports ICC(A,1), Lin's concordance correlation coefficient, and Bland-Altman
    bias/95% limits. The output deliberately forbids interpreting one metric's
    agreement as global ECG/PPG interchangeability.
    """
    pairs = _finite_pairs(reference, candidate)
    if len(pairs) < 3:
        raise ValueError("at least 3 paired finite observations are required")
    x, y = [p[0] for p in pairs], [p[1] for p in pairs]
    n = len(x)
    mx, my = _mean(x), _mean(y)
    vx, vy = _var(x, mx), _var(y, my)
    cov = sum((a - mx) * (b - my) for a, b in pairs) / (n - 1)
    ccc_denom = vx + vy + (mx - my) ** 2
    ccc = 2 * cov / ccc_denom if ccc_denom > 0 else math.nan

    differences = [a - b for a, b in pairs]
    bias = _mean(differences)
    sd_diff = math.sqrt(_var(differences, bias))
    loa = (bias - 1.96 * sd_diff, bias + 1.96 * sd_diff)

    # ICC(A,1): two-way random-effects, absolute agreement, single measurement.
    grand = (sum(x) + sum(y)) / (2 * n)
    row_means = [(a + b) / 2 for a, b in pairs]
    msr = 2 * sum((r - grand) ** 2 for r in row_means) / (n - 1)
    msc = n * ((mx - grand) ** 2 + (my - grand) ** 2)
    sse = sum(
        (a - r - mx + grand) ** 2 + (b - r - my + grand) ** 2
        for (a, b), r in zip(pairs, row_means)
    )
    mse = sse / (n - 1)
    denom = msr + mse + 2 * (msc - mse) / n
    icc = (msr - mse) / denom if denom else math.nan

    return {
        "metric": metric,
        "n": n,
        "icc_a1": icc,
        "lin_ccc": ccc,
        "bland_altman_bias": bias,
        "bland_altman_loa95": loa,
        "mean_paired_difference": bias,
        "reference": {"source": reference_source, "site": reference_site},
        "candidate": {"source": candidate_source, "site": candidate_site},
        "interpretation": (
            "Agreement applies to this derived metric and acquisition configuration; "
            "it does not establish global ECG/PPG interchangeability."
        ),
    }


def scr_responsivity_sensitivity(
    participant: Sequence[object],
    amplitude: Sequence[float],
    *,
    threshold: float = 0.02,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> list[dict]:
    """Estimate participant SCR responsivity without automatic non-responder deletion.

    A transparent Beta-Binomial update shrinks trial-level response rates while
    retaining the conventional median-amplitude flag as provenance. All finite
    participants are returned with ``retain_for_modeling=True`` so exclusion can
    be treated as a sensitivity specification rather than an irreversible rule.
    """
    if len(participant) != len(amplitude):
        raise ValueError("participant and amplitude must have equal length")
    if threshold < 0 or prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("invalid threshold or prior")
    groups = {}
    for pid, amp in zip(participant, amplitude):
        try:
            a = float(amp)
        except (TypeError, ValueError):
            continue
        if math.isfinite(a):
            groups.setdefault(pid, []).append(max(0.0, a))

    out = []
    for pid, vals in groups.items():
        n = len(vals)
        responses = sum(v >= threshold for v in vals)
        alpha = prior_alpha + responses
        beta = prior_beta + n - responses
        ordered = sorted(vals)
        median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        out.append(
            {
                "participant": pid,
                "n_trials": n,
                "responses": responses,
                "response_rate": responses / n,
                "posterior_response_probability": alpha / (alpha + beta),
                "posterior_alpha": alpha,
                "posterior_beta": beta,
                "conventional_nonresponder": median < threshold,
                "retain_for_modeling": True,
            }
        )
    return out


def validation_ladder(stages: Mapping[str, str | bool | None], *, claim: str = "descriptive") -> dict:
    """Separate acquisition, analytical, construct, within-person, and generalization evidence."""
    required = ["acquisition_qc", "analytical_qc", "construct_check", "within_person", "held_out_person"]

    def norm(value):
        if value is True:
            return "pass"
        if value is False:
            return "fail"
        if value is None:
            return "not_assessed"
        value = str(value).lower().replace("-", "_")
        return {"ok": "pass", "passed": "pass", "warn": "warning", "na": "not_assessed"}.get(value, value)

    values = {key: norm(stages.get(key)) for key in required}
    if any(v not in {"pass", "warning", "fail", "not_assessed"} for v in values.values()):
        raise ValueError("invalid stage status")
    held_out = values["held_out_person"] == "pass"
    general_claim = claim.lower().replace("-", "_") in {"generalizable", "generalization", "population", "out_of_person"}
    if any(v == "fail" for v in values.values()) or (general_claim and not held_out):
        state = "not_supported"
    elif any(v in {"warning", "not_assessed"} for v in values.values()):
        state = "qualified"
    else:
        state = "supported"
    return {
        "stages": values,
        "claim": claim,
        "claim_status": state,
        "held_out_person_generalization": held_out,
        "interpretation": (
            "Within-person prediction is personalized/calibrated evidence unless "
            "held-out-participant validation passes."
        ),
    }


def _distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _mst_edges(points):
    n = len(points)
    if n < 2:
        return []
    used, edges = {0}, []
    while len(used) < n:
        best = None
        for i in used:
            for j in range(n):
                if j in used:
                    continue
                d = _distance(points[i], points[j])
                if best is None or d < best[0]:
                    best = (d, j)
        edges.append(best[0])
        used.add(best[1])
    return edges


def ppg_topology_features(
    signal: Sequence[float],
    *,
    delay: int = 2,
    dimension: int = 3,
    max_points: int = 300,
) -> dict:
    """Compute an experimental topology-aware PPG morphology descriptor.

    H0 persistence lifetimes are represented by Euclidean MST edge weights from
    a delay embedding. This is a structural waveform descriptor, not a direct
    physiological surrogate. Participant-grouped validation is required before
    using these features for out-of-person ML claims.
    """
    xs = []
    for value in signal:
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            xs.append(value)
    if delay < 1 or dimension < 2 or max_points < 2:
        raise ValueError("delay >= 1, dimension >= 2, and max_points >= 2 are required")
    if len(xs) < (dimension - 1) * delay + 2:
        raise ValueError("signal is too short for requested embedding")

    points = [
        [xs[i - j * delay] for j in range(dimension)]
        for i in range((dimension - 1) * delay, len(xs))
    ]
    if len(points) > max_points:
        step = (len(points) - 1) / (max_points - 1)
        points = [points[round(i * step)] for i in range(max_points)]
    edges = _mst_edges(points)
    mean = _mean(edges)
    sd = math.sqrt(_var(edges, mean)) if len(edges) > 1 else 0.0
    total = sum(edges)
    probabilities = [e / total for e in edges if e > 0] if total > 0 else []
    entropy = -sum(p * math.log(p) for p in probabilities) if probabilities else 0.0
    return {
        "n_embedding_points": len(points),
        "delay": delay,
        "dimension": dimension,
        "h0_lifetime_mean": mean,
        "h0_lifetime_sd": sd,
        "h0_lifetime_median": _quantile(edges, 0.50),
        "h0_lifetime_q25": _quantile(edges, 0.25),
        "h0_lifetime_q75": _quantile(edges, 0.75),
        "h0_lifetime_max": max(edges),
        "h0_entropy": entropy,
        "h0_energy": sum(e * e for e in edges),
        "descriptor_status": "experimental_structural_descriptor",
        "ml_guardrail": "Use participant-grouped validation for any out-of-person prediction claim.",
    }


__all__ = [
    "compare_hrv_prv_devices",
    "scr_responsivity_sensitivity",
    "validation_ladder",
    "ppg_topology_features",
]
