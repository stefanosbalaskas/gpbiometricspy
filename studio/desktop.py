from __future__ import annotations

import argparse
import importlib.util
import socket
import subprocess
import sys
import time
import webbrowser

from studio.cli import build_shiny_command


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def choose_port(host: str = DEFAULT_HOST, preferred: int = DEFAULT_PORT) -> int:
    """Return the preferred local port when available, otherwise an ephemeral free port."""
    if preferred < 0 or preferred > 65535:
        raise ValueError("Port must be between 0 and 65535.")
    if preferred:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, preferred))
            except OSError:
                pass
            else:
                return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_server(host: str, port: int, *, timeout: float = 20.0) -> bool:
    """Wait until the local Shiny socket is accepting connections."""
    deadline = time.monotonic() + max(0.0, float(timeout))
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def build_desktop_command(*, host: str, port: int, public_demo: bool = False) -> list[str]:
    """Build the installed Shiny command used by the desktop-style launcher."""
    return build_shiny_command(
        public_demo=public_demo,
        argv=["--host", host, "--port", str(port)],
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpbiometricspy-studio-desktop",
        description="Launch gpbiometricspy Studio locally and open it in your default browser.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Loopback host to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred local port (default: 8765).")
    parser.add_argument("--public-demo", action="store_true", help="Launch the synthetic-only public boundary.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the default browser automatically.")
    parser.add_argument("--startup-timeout", type=float, default=20.0, help="Seconds to wait for the local server.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Launch Studio as a desktop-style local application experience."""
    args = _parser().parse_args(argv)
    if importlib.util.find_spec("shiny") is None:
        print(
            'gpbiometricspy Studio requires the optional Studio dependencies. '
            'Install them with: python -m pip install "gpbiometricspy[studio]"',
            file=sys.stderr,
        )
        return 2

    port = choose_port(args.host, args.port)
    url = f"http://{args.host}:{port}"
    command = build_desktop_command(host=args.host, port=port, public_demo=args.public_demo)
    print(f"Starting gpbiometricspy Studio at {url}")
    if port != args.port:
        print(f"Preferred port {args.port} was unavailable; using {port} instead.")

    process = subprocess.Popen(command)
    try:
        ready = wait_for_server(args.host, port, timeout=args.startup_timeout)
        if not ready:
            if process.poll() is not None:
                return int(process.returncode or 1)
            print(
                f"Studio did not become reachable within {args.startup_timeout:g} seconds. "
                "The server is still running; check the terminal output for diagnostics.",
                file=sys.stderr,
            )
        elif not args.no_browser:
            webbrowser.open(url, new=2)
        return int(process.wait())
    except KeyboardInterrupt:
        print("\nStopping gpbiometricspy Studio...")
        process.terminate()
        try:
            return int(process.wait(timeout=5))
        except subprocess.TimeoutExpired:
            process.kill()
            return int(process.wait())


if __name__ == "__main__":
    raise SystemExit(main())
