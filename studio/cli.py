from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
from typing import Sequence


STUDIO_DIR = Path(__file__).resolve().parent


def build_shiny_command(*, public_demo: bool = False, argv: Sequence[str] | None = None) -> list[str]:
    """Build the Shiny CLI command used by the installed Studio launchers."""
    app_name = "public_demo.py" if public_demo else "app.py"
    forwarded = list(sys.argv[1:] if argv is None else argv)
    return [sys.executable, "-m", "shiny", "run", *forwarded, str(STUDIO_DIR / app_name)]


def _run(*, public_demo: bool) -> int:
    if importlib.util.find_spec("shiny") is None:
        print(
            'gpbiometricspy Studio requires the optional Studio dependencies. '
            'Install them with: python -m pip install "gpbiometricspy[studio]"',
            file=sys.stderr,
        )
        return 2
    return subprocess.call(build_shiny_command(public_demo=public_demo))


def main() -> int:
    """Launch the full local/authenticated gpbiometricspy Studio."""
    return _run(public_demo=False)


def main_public() -> int:
    """Launch the synthetic-only public-demonstration boundary."""
    return _run(public_demo=True)


if __name__ == "__main__":
    raise SystemExit(main())
