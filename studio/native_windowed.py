from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import IO


# PyInstaller's Windows GUI/noconsole bootloader sets the standard streams to
# None. Keep any replacement handles alive for the lifetime of the process.
_WINDOWED_STREAM_HANDLES: list[IO[str]] = []
WINDOWED_LOG_ENV = "GPBIOMETRICSPY_WINDOWED_LOG_PATH"


def _open_text_sink(path: str | None = None) -> IO[str]:
    if path:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = target.open("a", encoding="utf-8", buffering=1)
    else:
        handle = open(os.devnull, "a", encoding="utf-8", buffering=1)
    _WINDOWED_STREAM_HANDLES.append(handle)
    return handle


def _open_text_source() -> IO[str]:
    handle = open(os.devnull, "r", encoding="utf-8")
    _WINDOWED_STREAM_HANDLES.append(handle)
    return handle


def _stabilize_standard_streams() -> None:
    """Restore safe text streams before importing Shiny/uvicorn in noconsole builds."""
    if sys.stdin is None:
        sys.stdin = _open_text_source()

    if sys.stdout is None or sys.stderr is None:
        sink = _open_text_sink(os.environ.get(WINDOWED_LOG_ENV))
        if sys.stdout is None:
            sys.stdout = sink
        if sys.stderr is None:
            sys.stderr = sink


def _console_attached() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        return bool(ctypes.windll.kernel32.GetConsoleWindow())
    except (AttributeError, OSError):
        return False


def main(argv: list[str] | None = None) -> int:
    """Bootstrap the unchanged frozen native app safely from a GUI-subsystem executable."""
    _stabilize_standard_streams()
    print(f"Windowed release bootstrap: console_attached={str(_console_attached()).lower()}")

    # Import only after the noconsole stream contract has been repaired. Shiny,
    # uvicorn and application modules are intentionally absent from module scope.
    from studio.native_frozen import main as native_main

    return native_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
