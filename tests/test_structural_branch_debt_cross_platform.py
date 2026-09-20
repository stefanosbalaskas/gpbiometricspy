from __future__ import annotations

import runpy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = runpy.run_path(
    str(ROOT / "scripts" / "audit_structural_branch_debt.py")
)

coverage_arcs = AUDITOR["_coverage_arcs"]
contract_arcs = AUDITOR["_contract_arcs"]
normalize_path = AUDITOR["_normalize_path"]


def test_structural_branch_audit_normalizes_windows_and_posix_paths() -> None:
    coverage = {
        "files": {
            r"src\gpbiometricspy\advanced_physiology.py": {
                "missing_branches": [[60, 65]]
            },
            r"src\gpbiometricspy\heartpy_style.py": {
                "missing_branches": [[154, 156]]
            },
        }
    }

    contract = {
        "structural_missing_count": 2,
        "entries": [
            {
                "file": "src/gpbiometricspy/advanced_physiology.py",
                "from": 60,
                "to": 65,
                "rationale": "synthetic regression rationale",
            },
            {
                "file": "src/gpbiometricspy/heartpy_style.py",
                "from": 154,
                "to": 156,
                "rationale": "synthetic regression rationale",
            },
        ],
    }

    expected = {
        ("src/gpbiometricspy/advanced_physiology.py", 60, 65),
        ("src/gpbiometricspy/heartpy_style.py", 154, 156),
    }

    assert coverage_arcs(coverage) == expected
    assert contract_arcs(contract) == expected


def test_structural_branch_audit_normalizes_contract_backslashes_too() -> None:
    coverage = {
        "files": {
            "src/gpbiometricspy/user_workflows.py": {
                "missing_branches": [[582, 584]]
            }
        }
    }

    contract = {
        "structural_missing_count": 1,
        "entries": [
            {
                "file": r"src\gpbiometricspy\user_workflows.py",
                "from": 582,
                "to": 584,
                "rationale": "synthetic regression rationale",
            }
        ],
    }

    assert coverage_arcs(coverage) == contract_arcs(contract)


def test_normalized_duplicate_contract_entries_still_fail_closed() -> None:
    contract = {
        "structural_missing_count": 2,
        "entries": [
            {
                "file": "src/gpbiometricspy/remaining_core.py",
                "from": 126,
                "to": 128,
                "rationale": "first representation",
            },
            {
                "file": r"src\gpbiometricspy\remaining_core.py",
                "from": 126,
                "to": 128,
                "rationale": "same arc using Windows separators",
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="Duplicate structural-debt entry",
    ):
        contract_arcs(contract)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            r"src\gpbiometricspy\biosppy_style.py",
            "src/gpbiometricspy/biosppy_style.py",
        ),
        (
            "src/gpbiometricspy/biosppy_style.py",
            "src/gpbiometricspy/biosppy_style.py",
        ),
    ],
)
def test_normalize_path_is_platform_independent(
    raw: str,
    expected: str,
) -> None:
    assert normalize_path(raw) == expected
