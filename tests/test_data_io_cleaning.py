from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_import_session_prefixed_csv_files(tmp_path):
    pd.DataFrame({"time_s": [1, 2, 3], "GSR": [1, 2, 3]}).to_csv(tmp_path / "S01_biometrics.csv", index=False)
    pd.DataFrame({"time_s": [1, 2, 3], "FPOGX": [.1, .2, .3], "FPOGY": [.4, .5, .6]}).to_csv(tmp_path / "S01_all_gaze.csv", index=False)
    pd.DataFrame({"time_s": [1, 2, 3], "GSR": [4, 5, 6]}).to_csv(tmp_path / "S02_biometrics.csv", index=False)
    out = gp.import_gazepoint_data(tmp_path, session="S01")
    assert len(out) == 2
    assert all(isinstance(x, pd.DataFrame) for x in out.values())
    assert {"gp_source_file", "gp_source_basename", "gp_source_index"}.issubset(next(iter(out.values())).columns)
    index = out.file_index
    assert isinstance(index, pd.DataFrame) and len(index) == 2
    assert (index["rows"] == 3).all()
    assert set(index["detected_type"]).issubset({"biometrics", "all_gaze"})
    assert out.attrs["class"][0] == "gazepoint_session_data"


def test_import_semicolon_and_missing_folder_errors(tmp_path):
    (tmp_path / "S03_biometrics.csv").write_text("time_s;PPG\n0;1.1\n1;1.2\n", encoding="utf-8")
    out = gp.import_gazepoint_data(tmp_path, session="S03")
    frame = next(iter(out.values()))
    assert {"time_s", "PPG"}.issubset(frame.columns) and len(frame) == 2
    with pytest.raises(FileNotFoundError, match="Folder does not exist"):
        gp.import_gazepoint_data(tmp_path / "absent")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="No files matching"):
        gp.import_gazepoint_data(empty)


def test_impute_linear_vector_and_max_gap():
    np.testing.assert_allclose(gp.impute_gazepoint_missing([1, np.nan, 3, 4]), [1, 2, 3, 4])
    out = gp.impute_gazepoint_missing([1, np.nan, np.nan, 4, np.nan, 6], max_gap=1)
    assert np.isnan(out[1]) and np.isnan(out[2]) and np.isfinite(out[4])


def test_impute_dataframe_summary_and_groups():
    dat = pd.DataFrame({"time_s": range(1, 6), "GSR": [1, np.nan, 3, np.nan, 5], "label": list("abcde")})
    out = gp.impute_gazepoint_missing(dat, cols="GSR", time_col="time_s")
    assert not out["GSR"].isna().any()
    assert int(out["GSR_was_imputed"].sum()) == 2
    summary = out.attrs["imputation_summary"]
    assert int(summary.loc[0, "n_missing_before"]) == 2 and int(summary.loc[0, "n_missing_after"]) == 0

    grouped = pd.DataFrame({
        "participant": ["P01"] * 3 + ["P02"] * 3,
        "time_s": [1, 2, 3, 1, 2, 3],
        "PPG": [1, np.nan, 3, 10, np.nan, 14],
    })
    gout = gp.impute_gazepoint_missing(grouped, cols="PPG", time_col="time_s", group_cols="participant")
    np.testing.assert_allclose(gout["PPG"], [1, 2, 3, 10, 12, 14])
    assert int(gout["PPG_was_imputed"].sum()) == 2


def test_impute_methods_edges_validation_and_all_missing_warning():
    x = [np.nan, 2, np.nan, 4, np.nan]
    np.testing.assert_allclose(gp.impute_gazepoint_missing(x, method="locf"), [2, 2, 2, 4, 4])
    np.testing.assert_allclose(gp.impute_gazepoint_missing(x, method="nocb"), [2, 2, 4, 4, 4])
    np.testing.assert_allclose(gp.impute_gazepoint_missing(x, method="nearest"), [2, 2, 2, 4, 4])
    np.testing.assert_allclose(gp.impute_gazepoint_missing(x, method="constant", constant_value=-1), [-1, 2, -1, 4, -1])
    no_edges = gp.impute_gazepoint_missing([np.nan, 2, 4, np.nan], method="linear", fill_edges=False)
    assert np.isnan(no_edges[0]) and np.isnan(no_edges[-1])
    with pytest.warns(RuntimeWarning, match="no observed values"):
        all_missing = gp.impute_gazepoint_missing([np.nan, np.nan])
    assert np.isnan(all_missing).all()
    with pytest.raises(ValueError, match="non-negative"):
        gp.impute_gazepoint_missing([1, np.nan], max_gap=-1)
    with pytest.raises(ValueError, match="time_col"):
        gp.impute_gazepoint_missing(pd.DataFrame({"x": [1, np.nan]}), time_col="time")
    with pytest.raises(ValueError, match="numeric"):
        gp.impute_gazepoint_missing(pd.DataFrame({"x": ["a", None]}), cols="x")
