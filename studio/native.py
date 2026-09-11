from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import webbrowser

from studio.desktop import DEFAULT_HOST, DEFAULT_PORT, build_desktop_command, choose_port, wait_for_server


WINDOW_TITLE = "gpbiometricspy Studio"
DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 960
WINDOWS_RENDERER = "edgechromium"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def is_loopback_host(host: str) -> bool:
    """Return whether the native wrapper is bound to an explicit loopback host."""
    return str(host).strip().lower() in _LOOPBACK_HOSTS


def build_native_command(*, host: str, port: int, public_demo: bool = False) -> list[str]:
    """Build the unchanged Shiny command hosted behind the native window."""
    return build_desktop_command(host=host, port=port, public_demo=public_demo)


def native_dependencies_available() -> bool:
    """Return whether the optional pywebview dependency is importable."""
    return importlib.util.find_spec("webview") is not None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpbiometricspy-studio-native",
        description=(
            "Launch gpbiometricspy Studio on loopback and present the unchanged Shiny application "
            "inside a lightweight native webview window."
        ),
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Loopback host to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred local port (default: 8765).")
    parser.add_argument("--public-demo", action="store_true", help="Launch the synthetic-only public boundary.")
    parser.add_argument("--startup-timeout", type=float, default=30.0, help="Seconds to wait for the local server.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Initial native window width.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Initial native window height.")
    parser.add_argument("--debug", action="store_true", help="Enable pywebview debug mode.")
    parser.add_argument(
        "--browser-fallback",
        action="store_true",
        help="If native window initialization fails, open the already-running local Studio in the default browser.",
    )
    return parser


def _validate_window_size(width: int, height: int) -> None:
    if width < 640 or height < 480:
        raise ValueError("Native Studio window must be at least 640x480 pixels.")


def _stop_process(process: subprocess.Popen[object]) -> int:
    if process.poll() is not None:
        return int(process.returncode or 0)
    process.terminate()
    try:
        return int(process.wait(timeout=5))
    except subprocess.TimeoutExpired:
        process.kill()
        return int(process.wait())


def main(argv: list[str] | None = None) -> int:
    """Run the optional Windows-native presentation wrapper for Studio."""
    args = _parser().parse_args(argv)

    if not is_loopback_host(args.host):
        print(
            "Native Studio is intentionally loopback-only; use 127.0.0.1, localhost, or ::1.",
            file=sys.stderr,
        )
        return 2

    try:
        _validate_window_size(args.width, args.height)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if importlib.util.find_spec("shiny") is None:
        print(
            'gpbiometricspy Studio requires the optional Studio dependencies. '
            'Install them with: python -m pip install "gpbiometricspy[studio-native]"',
            file=sys.stderr,
        )
        return 2

    if not native_dependencies_available():
        print(
            'Native Studio requires pywebview. Install it with: '
            'python -m pip install "gpbiometricspy[studio-native]"',
            file=sys.stderr,
        )
        return 2

    port = choose_port(args.host, args.port)
    url = f"http://{args.host}:{port}"
    command = build_native_command(host=args.host, port=port, public_demo=args.public_demo)
    print(f"Starting gpbiometricspy Studio native window at {url}")
    if port != args.port:
        print(f"Preferred port {args.port} was unavailable; using {port} instead.")

    process = subprocess.Popen(command)
    try:
        if not wait_for_server(args.host, port, timeout=args.startup_timeout):
            if process.poll() is not None:
                return int(process.returncode or 1)
            print(
                f"Studio did not become reachable within {args.startup_timeout:g} seconds.",
                file=sys.stderr,
            )
            return 1

        import webview

        webview.create_window(
            WINDOW_TITLE,
            url=url,
            width=args.width,
            height=args.height,
            min_size=(640, 480),
            resizable=True,
            text_select=True,
        )
        start_kwargs: dict[str, object] = {
            "debug": bool(args.debug),
            "private_mode": True,
        }
        if sys.platform == "win32":
            start_kwargs["gui"] = WINDOWS_RENDERER

        try:
            webview.start(**start_kwargs)
        except Exception as exc:
            if not args.browser_fallback:
                print(f"Native Studio window failed to initialize: {exc}", file=sys.stderr)
                return 1
            print(
                f"Native window unavailable ({exc}); opening the existing local Studio in the default browser.",
                file=sys.stderr,
            )
            webbrowser.open(url, new=2)
            return int(process.wait())

        return 0
    except KeyboardInterrupt:
        print("\nStopping gpbiometricspy Studio...")
        return 130
    finally:
        _stop_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
