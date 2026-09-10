from __future__ import annotations

from studio.config import STUDIO_MODE_ENV
from studio.error_guidance import classify_failure, format_failure, recovery_guidance


def test_error_taxonomy_classifies_common_researcher_failures():
    assert classify_failure("Dataset fingerprint mismatch").category == "identity"
    assert classify_failure("External event log could not be loaded").category == "resource"
    assert classify_failure("Load a dataset before running EDA/SCR analysis").category == "prerequisite"
    assert classify_failure("Selected signal column must be numeric").category == "input"
    assert classify_failure("EDA/SCR analysis failed", context="eda_scr").category == "analysis"


def test_primary_gazepoint_import_is_input_not_secondary_resource():
    guidance = classify_failure("Import failed: Choose a Gazepoint CSV or TXT file first.")
    assert guidance.code == "GP-STUDIO-INPUT"
    assert guidance.category == "input"


def test_secondary_resources_have_resource_specific_recovery():
    event = recovery_guidance("Choose an event log CSV/TXT/TSV file first.")
    target = recovery_guidance("Target stream could not be read.")
    assert "GP-STUDIO-RESOURCE" in event
    assert "event log" in event.lower()
    assert "GP-STUDIO-RESOURCE" in target
    assert "target stream" in target.lower()


def test_identity_guidance_never_recommends_bypassing_fingerprint_guards():
    text = recovery_guidance("External event log fingerprint mismatch: expected abc, got def")
    assert "GP-STUDIO-IDENTITY" in text
    assert "exact dataset or secondary resource" in text
    assert "do not bypass fingerprint validation" in text


def test_public_safe_failure_does_not_echo_private_exception_detail():
    private_detail = (
        "/home/research/private_participant_001.csv failed with GSR_US=0.123456; "
        "parameters={'threshold': 0.05, 'participant': 'P001'}"
    )
    rendered = format_failure(
        "EDA/SCR analysis failed",
        ValueError(private_detail),
        public_safe=True,
        context="eda_scr",
    )
    assert rendered.startswith("EDA/SCR analysis failed.")
    assert "GP-STUDIO-ANALYSIS" in rendered
    assert "private_participant_001.csv" not in rendered
    assert "/home/research" not in rendered
    assert "GSR_US" not in rendered
    assert "0.123456" not in rendered
    assert "threshold" not in rendered
    assert "P001" not in rendered


def test_runtime_public_demo_policy_sanitizes_without_explicit_override(monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "public-demo")
    rendered = format_failure(
        "Project restore blocked",
        ValueError("fingerprint mismatch for /private/P007.json"),
        context="project recipe source fingerprint",
    )
    assert "GP-STUDIO-IDENTITY" in rendered
    assert "/private/P007.json" not in rendered
    assert "fingerprint mismatch for" not in rendered


def test_runtime_local_policy_retains_bounded_detail_without_explicit_override(monkeypatch):
    monkeypatch.setenv(STUDIO_MODE_ENV, "local")
    rendered = format_failure(
        "Import failed",
        ValueError("Selected Gazepoint CSV is unreadable."),
        context="Gazepoint import",
    )
    assert "Selected Gazepoint CSV is unreadable." in rendered
    assert "GP-STUDIO-INPUT" in rendered


def test_local_failure_preserves_concise_detail_and_adds_recovery_code():
    rendered = format_failure(
        "PPG/HR/HRV analysis failed",
        ValueError("Selected HR column must be numeric."),
        public_safe=False,
        context="ppg_hr_hrv",
    )
    assert rendered.startswith(
        "PPG/HR/HRV analysis failed: Selected HR column must be numeric."
    )
    assert "GP-STUDIO-INPUT" in rendered
    assert "Next:" in rendered


def test_local_failure_detail_is_bounded():
    rendered = format_failure(
        "Analysis failed",
        RuntimeError("x" * 500),
        public_safe=False,
        context="analysis",
    )
    detail_section = rendered.split("[GP-STUDIO-", maxsplit=1)[0]
    assert "..." in detail_section
    assert len(detail_section) < 260


def test_unknown_failure_points_to_privacy_safe_doctor():
    rendered = format_failure(
        "Operation failed",
        RuntimeError("unexpected internal condition"),
        public_safe=True,
    )
    assert "GP-STUDIO-UNKNOWN" in rendered
    assert "gpbiometricspy-studio-doctor" in rendered
    assert "unexpected internal condition" not in rendered
