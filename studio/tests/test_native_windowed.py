from __future__ import annotations

import io
import sys

import studio.native_windowed as native_windowed


def _close_windowed_handles() -> None:
    for handle in native_windowed._WINDOWED_STREAM_HANDLES:
        if not handle.closed:
            handle.close()
    native_windowed._WINDOWED_STREAM_HANDLES.clear()


def test_stabilize_standard_streams_repairs_noconsole_streams(tmp_path, monkeypatch):
    log_path = tmp_path / "windowed.log"
    _close_windowed_handles()

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdin", None)
        patch.setattr(sys, "stdout", None)
        patch.setattr(sys, "stderr", None)
        patch.setenv(native_windowed.WINDOWED_LOG_ENV, str(log_path))

        native_windowed._stabilize_standard_streams()

        assert sys.stdin is not None
        assert sys.stdout is not None
        assert sys.stderr is not None
        assert sys.stdout is sys.stderr
        print("windowed stdout diagnostic")
        print("windowed stderr diagnostic", file=sys.stderr)
        sys.stdout.flush()

    text = log_path.read_text(encoding="utf-8")
    assert "windowed stdout diagnostic" in text
    assert "windowed stderr diagnostic" in text
    _close_windowed_handles()


def test_stabilize_standard_streams_preserves_existing_streams(monkeypatch):
    stdin = io.StringIO("")
    stdout = io.StringIO()
    stderr = io.StringIO()
    _close_windowed_handles()

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdin", stdin)
        patch.setattr(sys, "stdout", stdout)
        patch.setattr(sys, "stderr", stderr)

        native_windowed._stabilize_standard_streams()

        assert sys.stdin is stdin
        assert sys.stdout is stdout
        assert sys.stderr is stderr
        assert native_windowed._WINDOWED_STREAM_HANDLES == []


def test_windowed_bootstrap_does_not_import_native_frozen_at_module_scope():
    source = __import__("inspect").getsource(native_windowed)
    stabilize_call = source.index("_stabilize_standard_streams()", source.index("def main"))
    frozen_import = source.index("from studio.native_frozen import main as native_main")
    assert stabilize_call < frozen_import
