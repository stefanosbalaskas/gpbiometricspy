from __future__ import annotations

import pandas as pd
import pytest

import gpbiometricspy as gp


def test_validity_rejects_nonpositive_active_min_unique():
    with pytest.raises(ValueError, match="active_min_unique"):
        gp.summarise_gazepoint_biometric_validity(
            pd.DataFrame({"GSR": [1.0, 2.0]}),
            active_min_unique=0,
        )


def test_validity_rejects_requested_missing_columns():
    with pytest.raises(ValueError, match="signal_cols"):
        gp.summarise_gazepoint_biometric_validity(
            pd.DataFrame({"GSR": [1.0, 2.0]}),
            signal_cols=["missing_signal"],
        )
