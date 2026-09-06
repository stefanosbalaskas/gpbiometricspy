from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

import gpbiometricspy as gp
from studio.plotting import as_matplotlib_figure


def test_plot_render_adapter_accepts_figure_axes_and_structured_results():
    fig, ax = plt.subplots()
    assert as_matplotlib_figure(fig) is fig
    assert as_matplotlib_figure(ax) is fig
    assert as_matplotlib_figure({"figure": fig, "data": pd.DataFrame({"x": [1]})}) is fig
    assert as_matplotlib_figure({"plots": {"diagnostic": fig}}) is fig
    assert as_matplotlib_figure({"plots": {"diagnostic": ax}}) is fig
    plt.close(fig)


def test_plot_render_adapter_rejects_non_plot_results():
    with pytest.raises(TypeError, match="did not contain a Matplotlib Figure"):
        as_matplotlib_figure({"data": pd.DataFrame({"x": [1]})})


def test_saccade_main_sequence_structured_contract_is_renderable_by_studio():
    saccades = pd.DataFrame(
        {
            "amplitude_deg": [1.0, 2.0, 3.0, 4.0, 5.0],
            "peak_velocity_deg_s": [100.0, 180.0, 250.0, 300.0, 340.0],
        }
    )
    result = gp.plot_gazepoint_saccade_main_sequence(
        saccades,
        amplitude_col="amplitude_deg",
        peak_velocity_col="peak_velocity_deg_s",
        add_smoother=False,
    )
    assert isinstance(result, dict)
    assert isinstance(result.get("figure"), Figure)
    assert as_matplotlib_figure(result) is result["figure"]
    plt.close(result["figure"])
