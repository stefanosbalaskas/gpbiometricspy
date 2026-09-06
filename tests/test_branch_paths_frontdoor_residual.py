from __future__ import annotations

import pandas as pd

import gpbiometricspy as gp


def test_import_retains_nonempty_unnamed_column(tmp_path):
    path = tmp_path / "User 0_all_gaze.csv"
    path.write_text(
        "TIME,GSR_US,Unnamed: 1\n"
        "0.01,2.0,keep\n"
        "0.02,2.1,also_keep\n",
        encoding="utf-8",
    )

    out = gp.import_gazepoint_biometrics(path)

    assert "Unnamed: 1" in out.columns
    assert out["Unnamed: 1"].tolist() == ["keep", "also_keep"]


def test_missingness_accepts_explicit_column_list():
    data = pd.DataFrame({"GSR_US": [2.0, None, 0.0]})

    out = gp.audit_gazepoint_biometric_missingness(
        data,
        columns=["GSR_US"],
    )

    assert out["column"].tolist() == ["GSR_US"]
    assert int(out.iloc[0]["missing_rows"]) == 1
