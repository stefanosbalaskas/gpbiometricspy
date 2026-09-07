from __future__ import annotations

import pandas as pd

import gpbiometricspy as gp
from studio.services import run_qc


def test_foundation_qc_is_concat_safe_for_dataframe_attrs() -> None:
    data = gp.load_kiosk_demo()
    metadata = pd.DataFrame(
        {
            "column": ["POR X", "POR Y"],
            "active": [True, True],
        }
    )
    data.attrs["biometric_columns"] = metadata

    result = run_qc(data)

    assert set(result) == {"validation", "missingness", "activity"}
    assert isinstance(result["missingness"], pd.DataFrame)
    assert isinstance(result["activity"], dict)
    assert data.attrs["biometric_columns"] is metadata
