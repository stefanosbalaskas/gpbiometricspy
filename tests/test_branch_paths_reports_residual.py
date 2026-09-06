import pandas as pd

import gpbiometricspy as gp


def test_methods_section_renders_na_audit_value():
    profile = {
        "overview": pd.DataFrame(
            [{"n_files": float("nan"), "n_readable_files": 1.0}]
        )
    }

    text = gp.create_gazepoint_methods_section(export_profile=profile)

    assert "NA file(s)" in str(text)


def test_qc_supplement_renders_empty_overview_table():
    profile = {"overview": pd.DataFrame()}

    text = gp.create_gazepoint_qc_supplement(export_profile=profile)

    assert "<no rows>" in text


def test_qc_supplement_accepts_empty_warning_table():
    profile = {
        "overview": pd.DataFrame([{"n_files": 1}]),
        "warnings": pd.DataFrame(),
    }

    text = gp.create_gazepoint_qc_supplement(export_profile=profile)

    assert "Export-folder profile" in text


def test_audit_report_collects_empty_warning_table_without_records():
    profile = {
        "overview": pd.DataFrame(
            [{"n_files": 1, "n_readable_files": 1, "n_read_errors": 0}]
        ),
        "warnings": pd.DataFrame(),
    }

    text = gp.create_gazepoint_audit_report_section(export_profile=profile)

    assert "No audit warnings were recorded in the supplied objects." in text
