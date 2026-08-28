from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

import gpbiometricspy as gp


def demo(rows=900):
    d = gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"]).copy().iloc[:rows].reset_index(drop=True)
    return d


def pulse_frame(fs=100, seconds=20):
    t = np.arange(0, seconds + 1 / fs / 2, 1 / fs)
    x = np.sin(2 * np.pi * 1.2 * t) ** 8 + 0.02 * np.sin(2 * np.pi * 6 * t)
    return pd.DataFrame({"participant": "P01", "time_s": t, "pulse": x})


def summarize(value):
    if isinstance(value, pd.DataFrame):
        return {"type": "DataFrame", "rows": len(value), "columns": len(value.columns)}
    if isinstance(value, pd.Series):
        return {"type": "Series", "rows": len(value)}
    if isinstance(value, dict):
        return {"type": "dict", "keys": sorted(map(str, value.keys()))[:20]}
    if isinstance(value, np.ndarray):
        return {"type": "ndarray", "shape": list(value.shape)}
    if isinstance(value, Figure):
        return {"type": "Figure", "axes": len(value.axes)}
    return {"type": type(value).__name__}


def _figures(value: Any) -> Iterable[Figure]:
    if isinstance(value, Figure):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _figures(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            yield from _figures(nested)


def _export_figures(name: str, objects: dict[str, Any]) -> list[str]:
    output = os.environ.get("GPBIOMETRICSPY_TUTORIAL_OUTPUT_DIR")
    if not output:
        return []
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    seen: set[int] = set()
    index = 1
    for value in objects.values():
        for fig in _figures(value):
            identity = id(fig)
            if identity in seen:
                continue
            seen.add(identity)
            path = root / f"{name}-{index:02d}.png"
            fig.savefig(path, dpi=160, bbox_inches="tight")
            saved.append(str(path))
            index += 1
    return saved


def finish(name, **objects):
    saved = _export_figures(name, objects)
    summary = {
        "tutorial": name,
        "status": "PASS",
        "objects": {k: summarize(v) for k, v in objects.items()},
    }
    if saved:
        summary["saved_figures"] = saved
    plt.close("all")
    print(json.dumps(summary, sort_keys=True))
