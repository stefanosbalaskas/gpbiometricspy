from __future__ import annotations

import argparse
import sys
import threading
import time
from typing import Any

from shiny import run_app

from studio.desktop import DEFAULT_HOST, DEFAULT_PORT, choose_port, wait_for_server
from studio.frozen import _load_studio_app
from studio.native import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    WINDOW_TITLE,
    WINDOWS_RENDERER,
    _validate_window_size,
    is_loopback_host,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpbiometricspy-studio-native-frozen",
        description=(
            "Run frozen gpbiometricspy Studio in-process and present it in a Windows WebView2 window. "
            "This adapter is for packaging evaluation and does not replace normal pip launchers."
        ),
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Loopback host to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred local port (default: 8765).")
    parser.add_argument("--public-demo", action="store_true", help="Launch the synthetic-only public boundary.")
    parser.add_argument("--startup-timeout", type=float, default=60.0, help="Seconds to wait for the local server.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Initial native window width.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Initial native window height.")
    parser.add_argument("--debug", action="store_true", help="Enable pywebview debug mode.")
    parser.add_argument(
        "--automation-close-seconds",
        type=float,
        default=0.0,
        help=argparse.SUPPRESS,
    )
    return parser


def _run_server(app: Any, *, host: str, port: int, errors: list[BaseException]) -> None:
    try:
        run_app(
            app,
            host=host,
            port=port,
            reload=False,
            launch_browser=False,
            dev_mode=False,
        )
    except BaseException as exc:  # pragma: no cover - surfaced by the outer startup guard
        errors.append(exc)


def _close_after(window: Any, seconds: float) -> None:
    time.sleep(max(0.0, float(seconds)))
    window.destroy()


def main(argv: list[str] | None = None) -> int:
    """Run frozen Studio and host the unchanged local app in a WebView2 window."""
    args = _parser().parse_args(argv)

    if not is_loopback_host(args.host):
        print(
            "Frozen native Studio is intentionally loopback-only; use 127.0.0.1, localhost, or ::1.",
            file=sys.stderr,
        )
        return 2

    try:
        _validate_window_size(args.width, args.height)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        import webview
    except ImportError as exc:
        print(f"Frozen native Studio is missing its pywebview runtime: {exc}", file=sys.stderr)
        return 2

    port = choose_port(args.host, args.port)
    app = _load_studio_app(public_demo=args.public_demo)
    url = f"http://{args.host}:{port}"
    errors: list[BaseException] = []

    print(f"Starting frozen native gpbiometricspy Studio at {url}")
    if port != args.port:
        print(f"Preferred port {args.port} was unavailable; using {port} instead.")

    server_thread = threading.Thread(
        target=_run_server,
        kwargs={"app": app, "host": args.host, "port": port, "errors": errors},
        name="gpbiometricspy-studio-server",
        daemon=True,
    )
    server_thread.start()

    if not wait_for_server(args.host, port, timeout=args.startup_timeout):
        if errors:
            print(f"Frozen native Studio server failed: {errors[0]}", file=sys.stderr)
        else:
            print(
                f"Frozen native Studio did not become reachable within {args.startup_timeout:g} seconds.",
                file=sys.stderr,
            )
        return 1

    window = webview.create_window(
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
        print(f"Native renderer requested: {WINDOWS_RENDERER}")

    try:
        if args.automation_close_seconds > 0:
            webview.start(
                _close_after,
                (window, float(args.automation_close_seconds)),
                **start_kwargs,
            )
        else:
            webview.start(**start_kwargs)
    except Exception as exc:
        print(f"Frozen native Studio window failed to initialize: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"Frozen native Studio server failed: {errors[0]}", file=sys.stderr)
        return 1

    print("Frozen native Studio window closed cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
