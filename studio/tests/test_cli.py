from __future__ import annotations

from pathlib import Path
import sys

from studio.cli import STUDIO_DIR, build_shiny_command


def test_full_studio_command_targets_installed_app_and_forwards_shiny_arguments():
    command = build_shiny_command(argv=["--host", "127.0.0.1", "--port", "8765"])

    assert command[:4] == [sys.executable, "-m", "shiny", "run"]
    assert command[4:8] == ["--host", "127.0.0.1", "--port", "8765"]
    assert Path(command[-1]) == STUDIO_DIR / "app.py"


def test_public_studio_command_targets_fail_closed_public_boundary():
    command = build_shiny_command(public_demo=True, argv=[])

    assert Path(command[-1]) == STUDIO_DIR / "public_demo.py"
    assert command[:4] == [sys.executable, "-m", "shiny", "run"]
