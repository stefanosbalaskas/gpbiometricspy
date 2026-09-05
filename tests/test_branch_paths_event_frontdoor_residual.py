from __future__ import annotations

import pytest

import gpbiometricspy as gp


def test_engagement_scalar_rejects_multiple_groups():
    with pytest.raises(ValueError, match="single group"):
        gp.compute_gazepoint_engagement_index(
            [40.0, 60.0],
            time=[0.0, 1.0],
            group=["a", "b"],
            return_="scalar",
        )
