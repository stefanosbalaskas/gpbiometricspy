from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
import tracemalloc
from typing import Any

import gpbiometricspy as gp

try:
    from studio.services import inspect_dataset, load_demo_dataset, run_qc
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import inspect_dataset, load_demo_dataset, run_qc

# Deliberately generous CI budgets: these are regression tripwires rather than
# microbenchmarks. They catch pathological startup/QC regressions without making
# normal shared-runner variation a release blocker.
MAX_LOAD_SECONDS = 30.0
MAX_INSPECT_SECONDS = 30.0
MAX_QC_SECONDS = 60.0
MAX_TOTAL_SECONDS = 90.0


def _timed(callable_obj, *args, **kwargs):
    started = perf_counter()
    value = callable_obj(*args, **kwargs)
    return value, perf_counter() - started


def run_production_smoke() -> dict[str, Any]:
    """Exercise the public synthetic-data path and return coarse runtime metrics."""
    tracemalloc.start()
    total_started = perf_counter()

    (data, source_name), load_seconds = _timed(load_demo_dataset)
    validation, inspect_seconds = _timed(inspect_dataset, data)
    qc, qc_seconds = _timed(run_qc, data)

    total_seconds = perf_counter() - total_started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    activity = qc.get("activity") if isinstance(qc, dict) else None
    active_rows = len(activity) if hasattr(activity, "__len__") else 0

    return {
        "gpbiometricspy_version": gp.__version__,
        "source_name": source_name,
        "row_count": int(len(data)),
        "column_count": int(len(data.columns)),
        "validation_valid": bool(validation.get("valid", True)) if isinstance(validation, dict) else True,
        "activity_rows": int(active_rows),
        "load_seconds": round(float(load_seconds), 6),
        "inspect_seconds": round(float(inspect_seconds), 6),
        "qc_seconds": round(float(qc_seconds), 6),
        "total_seconds": round(float(total_seconds), 6),
        "python_peak_tracemalloc_mb": round(float(peak_bytes) / (1024 * 1024), 3),
    }


def validate_production_smoke(metrics: dict[str, Any]) -> None:
    """Apply broad production regression budgets to synthetic-demo execution."""
    if int(metrics.get("row_count", 0)) <= 0 or int(metrics.get("column_count", 0)) <= 0:
        raise RuntimeError("Synthetic production smoke did not load a non-empty dataset.")
    budgets = {
        "load_seconds": MAX_LOAD_SECONDS,
        "inspect_seconds": MAX_INSPECT_SECONDS,
        "qc_seconds": MAX_QC_SECONDS,
        "total_seconds": MAX_TOTAL_SECONDS,
    }
    exceeded = [
        f"{name}={float(metrics.get(name, 0.0)):.3f}s > {limit:.1f}s"
        for name, limit in budgets.items()
        if float(metrics.get(name, 0.0)) > limit
    ]
    if exceeded:
        raise RuntimeError("Production smoke runtime budget exceeded: " + "; ".join(exceeded))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gpbiometricspy Studio production smoke diagnostics.")
    parser.add_argument("--json", dest="json_path", type=Path, default=None, help="Optional path for JSON metrics.")
    args = parser.parse_args()

    metrics = run_production_smoke()
    validate_production_smoke(metrics)
    payload = json.dumps(metrics, indent=2, sort_keys=True)
    print(payload)
    if args.json_path is not None:
        args.json_path.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
