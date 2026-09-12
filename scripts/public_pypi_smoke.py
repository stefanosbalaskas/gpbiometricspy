from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys


def _run(command: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _require_console_script(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise SystemExit(f"missing installed console script: {name}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a clean public-PyPI gpbiometricspy installation.")
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()

    expected = args.expected_version

    import gpbiometricspy as gp

    installed = metadata.version("gpbiometricspy")
    if installed != expected or gp.__version__ != expected:
        raise SystemExit(
            f"version mismatch: metadata={installed!r}, runtime={gp.__version__!r}, expected={expected!r}"
        )

    if len(gp.R_EXPORTS) != 406:
        raise SystemExit(f"R export contract mismatch: {len(gp.R_EXPORTS)} != 406")
    if len(gp.IMPLEMENTED_EXPORTS) != 406:
        raise SystemExit(f"implemented export contract mismatch: {len(gp.IMPLEMENTED_EXPORTS)} != 406")
    if len(gp.PENDING_EXPORTS) != 0:
        raise SystemExit(f"pending export contract mismatch: {len(gp.PENDING_EXPORTS)} != 0")

    missing_exports = [name for name in gp.R_EXPORTS if not hasattr(gp, name)]
    if missing_exports:
        raise SystemExit(f"installed package is missing frozen exports: {missing_exports[:10]}")

    demo_files = gp.kiosk_demo_files()
    if len(demo_files) != 36 or not all(Path(path).is_file() for path in demo_files):
        raise SystemExit("packaged kiosk demo data are incomplete")
    overview = gp.kiosk_demo_overview().iloc[0]
    if int(overview["participants"]) != 36 or int(overview["total_rows"]) != 69_120:
        raise SystemExit(f"packaged kiosk demo overview mismatch: {overview.to_dict()}")

    required_scripts = (
        "gpbiometricspy-studio",
        "gpbiometricspy-studio-public",
        "gpbiometricspy-studio-desktop",
        "gpbiometricspy-studio-native",
        "gpbiometricspy-studio-doctor",
    )
    resolved_scripts = {name: _require_console_script(name) for name in required_scripts}

    doctor = _run([resolved_scripts["gpbiometricspy-studio-doctor"], "--json"])
    doctor_payload = json.loads(doctor.stdout)
    if doctor_payload.get("package_version") != expected or doctor_payload.get("ok") is not True:
        raise SystemExit(f"Studio doctor failed: {doctor.stdout}\n{doctor.stderr}")

    for launcher in ("gpbiometricspy-studio", "gpbiometricspy-studio-public"):
        help_run = _run([resolved_scripts[launcher], "--help"], timeout=30)
        help_text = (help_run.stdout + help_run.stderr).lower()
        if "shiny" not in help_text or "run" not in help_text:
            raise SystemExit(f"{launcher} did not reach the installed Shiny CLI: {help_text[:500]}")

    payload = {
        "version": expected,
        "python": sys.version.split()[0],
        "r_exports": len(gp.R_EXPORTS),
        "implemented_exports": len(gp.IMPLEMENTED_EXPORTS),
        "pending_exports": len(gp.PENDING_EXPORTS),
        "demo_files": len(demo_files),
        "demo_rows": int(overview["total_rows"]),
        "studio_doctor": doctor_payload,
        "console_scripts": resolved_scripts,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
