from __future__ import annotations

import argparse
from typing import Any

from shiny import run_app

from studio.desktop import DEFAULT_HOST, DEFAULT_PORT, choose_port


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpbiometricspy-studio-frozen",
        description=(
            "Launch a frozen gpbiometricspy Studio bundle through Shiny's in-process runner. "
            "This entry point is for standalone packaging and does not replace the normal pip launchers."
        ),
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred local port (default: 8765).")
    parser.add_argument("--public-demo", action="store_true", help="Launch the synthetic-only public boundary.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the default browser automatically.")
    return parser


def _load_studio_app(*, public_demo: bool) -> Any:
    """Load the requested Studio boundary only after runtime mode is known."""
    if public_demo:
        from studio.public_demo import app
    else:
        from studio.app import app
    return app


def main(argv: list[str] | None = None) -> int:
    """Run Studio in-process for standalone/frozen packaging experiments."""
    args = _parser().parse_args(argv)
    port = choose_port(args.host, args.port)
    app = _load_studio_app(public_demo=args.public_demo)
    url = f"http://{args.host}:{port}"

    print(f"Starting frozen gpbiometricspy Studio at {url}")
    if port != args.port:
        print(f"Preferred port {args.port} was unavailable; using {port} instead.")

    run_app(
        app,
        host=args.host,
        port=port,
        reload=False,
        launch_browser=not args.no_browser,
        dev_mode=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
