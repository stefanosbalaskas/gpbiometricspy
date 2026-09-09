
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import importlib.util
import json
from pathlib import Path
import platform
import socket
from typing import Any

import gpbiometricspy as gp

try:
    from studio.config import studio_runtime_config
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from config import studio_runtime_config


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    passed: bool
    detail: str
    required: bool = True


def _localhost_bind_check() -> DoctorCheck:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = int(probe.getsockname()[1])
        return DoctorCheck("localhost_bind", True, f"loopback bind available on test port {port}")
    except OSError as exc:
        return DoctorCheck("localhost_bind", False, f"loopback bind failed: {exc}")


def run_doctor() -> tuple[DoctorCheck, ...]:
    """Run local, privacy-safe preflight checks for Studio startup and support."""
    studio_dir = Path(__file__).resolve().parent
    runtime = studio_runtime_config()
    shiny_available = importlib.util.find_spec("shiny") is not None
    return (
        DoctorCheck(
            "shiny_dependency",
            shiny_available,
            "Shiny for Python is importable" if shiny_available else 'install with: python -m pip install "gpbiometricspy[studio]"',
        ),
        DoctorCheck("studio_app", (studio_dir / "app.py").is_file(), str(studio_dir / "app.py")),
        DoctorCheck("studio_css", (studio_dir / "www" / "studio.css").is_file(), str(studio_dir / "www" / "studio.css")),
        DoctorCheck("runtime_mode", True, runtime.mode),
        _localhost_bind_check(),
    )


def doctor_payload() -> dict[str, Any]:
    checks = run_doctor()
    return {
        "product": "gpbiometricspy Studio",
        "package_version": gp.__version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "ok": all(check.passed for check in checks if check.required),
        "checks": [asdict(check) for check in checks],
    }


def format_doctor(payload: dict[str, Any] | None = None) -> str:
    data = doctor_payload() if payload is None else payload
    lines = [
        f"gpbiometricspy Studio doctor — package {data['package_version']}",
        f"Python {data['python_version']} · {data['platform']}",
    ]
    for check in data["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"[{marker}] {check['name']}: {check['detail']}")
    lines.append("Overall: READY" if data["ok"] else "Overall: ACTION REQUIRED")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpbiometricspy-studio-doctor",
        description="Run privacy-safe gpbiometricspy Studio installation and launch diagnostics.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON diagnostics.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = doctor_payload()
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else format_doctor(payload))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
