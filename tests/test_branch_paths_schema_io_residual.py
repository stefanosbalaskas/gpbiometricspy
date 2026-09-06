import pandas as pd
import pytest

import gpbiometricspy as gp


def test_detect_time_columns_empty_input_returns_empty_schema():
    out = gp.detect_gazepoint_time_columns(pd.DataFrame())

    assert out.empty
    assert list(out.columns) == [
        "column",
        "standard_name",
        "role",
        "unit_hint",
        "confidence",
        "reason",
    ]


def test_detect_biometric_timebase_rejects_missing_explicit_time_column():
    data = pd.DataFrame({"value": [1.0, 2.0]})

    with pytest.raises(ValueError, match="time_col"):
        gp.detect_gazepoint_biometric_timebase(data, time_col="missing")


def test_import_data_summary_section_marker_without_header_is_empty(tmp_path):
    path = tmp_path / "summary.csv"
    path.write_text(
        "Gazepoint Analysis,1.0\n"
        "Processed,2026-09-06\n"
        "AOI Summary\n",
        encoding="utf-8",
    )

    out = gp.import_gazepoint_data_summary(path)

    assert out["aoi_summary"].empty
    assert list(out["aoi_summary"].columns) == ["source_file"]


def test_import_data_summary_rejects_empty_file_path():
    with pytest.raises(ValueError, match="file"):
        gp.import_gazepoint_data_summary("")
