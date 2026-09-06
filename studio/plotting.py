from __future__ import annotations

from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure


def as_matplotlib_figure(plot_result: Any) -> Figure:
    """Resolve a package plot result to the Figure required by Shiny ``render.plot``.

    gpbiometricspy deliberately preserves several R-style plotting contracts. Most
    Python plot functions return a bare Matplotlib ``Figure``, while a small number
    return a structured dictionary that carries the figure alongside plot data and
    settings. Studio is a UI boundary, so it should unwrap those structured results
    without changing the public scientific API contract.
    """
    if isinstance(plot_result, Figure):
        return plot_result
    if isinstance(plot_result, Axes):
        return plot_result.figure
    if isinstance(plot_result, dict):
        figure = plot_result.get("figure")
        if isinstance(figure, Figure):
            return figure
        plots = plot_result.get("plots")
        if isinstance(plots, dict):
            for candidate in plots.values():
                if isinstance(candidate, Figure):
                    return candidate
                if isinstance(candidate, Axes):
                    return candidate.figure
    raise TypeError(
        "Studio plot output did not contain a Matplotlib Figure; "
        f"received {type(plot_result).__name__}."
    )
