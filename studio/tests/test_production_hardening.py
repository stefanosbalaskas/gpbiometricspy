from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from studio.config import (
    LOCAL_MODE,
    PUBLIC_DEMO_MODE,
    PUBLIC_UPLOAD_BLOCK_MESSAGE,
    STUDIO_MODE_ENV,
    reject_external_upload,
    studio_runtime_config,
)
from studio.production import run_production_smoke, validate_production_smoke


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_config_defaults_local_and_public_demo_fails_closed():
    local = studio_runtime_config({})
    public = studio_runtime_config({STUDIO_MODE_ENV: PUBLIC_DEMO_MODE})

    assert local.mode == LOCAL_MODE
    assert local.allow_external_uploads is True
    assert local.sanitize_errors is False

    assert public.mode == PUBLIC_DEMO_MODE
    assert public.is_public_demo is True
    assert public.allow_external_uploads is False
    assert public.sanitize_errors is True


def test_runtime_config_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported"):
        studio_runtime_config({STUDIO_MODE_ENV: "internet-anything-goes"})


def test_public_upload_guard_is_explicit():
    with pytest.raises(PermissionError, match="External file uploads are disabled"):
        reject_external_upload("Test upload")
    assert "local or authenticated" in PUBLIC_UPLOAD_BLOCK_MESSAGE


def test_connect_cloud_contract_files_are_minimal_and_public_entrypoint_is_sanitized():
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "." in requirements
    assert any(line.startswith("shiny>=1.7") for line in requirements)

    env = os.environ.copy()
    env.pop(STUDIO_MODE_ENV, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import app; "
                "from studio.config import studio_runtime_config; "
                "cfg=studio_runtime_config(); "
                "assert cfg.is_public_demo; "
                "assert app.app.sanitize_errors is True"
            ),
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr


def test_synthetic_production_smoke_stays_inside_regression_budgets():
    metrics = run_production_smoke()
    validate_production_smoke(metrics)
    assert metrics["row_count"] > 0
    assert metrics["column_count"] > 0
    assert metrics["total_seconds"] >= 0
    assert metrics["python_peak_tracemalloc_mb"] >= 0
