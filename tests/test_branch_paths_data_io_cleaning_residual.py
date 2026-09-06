from __future__ import annotations

import numpy as np

import gpbiometricspy as gp


def test_locf_without_edge_fill_leaves_leading_gap():
    out = gp.impute_gazepoint_missing(
        [np.nan, 2.0, np.nan, 4.0, np.nan],
        method="locf",
        fill_edges=False,
    )
    assert np.isnan(out[0])
    np.testing.assert_allclose(out[1:], [2.0, 2.0, 4.0, 4.0])


def test_nocb_without_edge_fill_leaves_trailing_gap():
    out = gp.impute_gazepoint_missing(
        [np.nan, 2.0, np.nan, 4.0, np.nan],
        method="nocb",
        fill_edges=False,
    )
    np.testing.assert_allclose(out[:-1], [2.0, 2.0, 4.0, 4.0])
    assert np.isnan(out[-1])
