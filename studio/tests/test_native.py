from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import studio.native as native


def test_native_command_reuses_full_studio_target():
    command = native.build_native_command(host="127.0.0.1", port=8765)
    assert command[:3] == [sys.executable, "-m", "shiny"]
    assert command[-1].endswith("studio/app.py") or command[-1].endswith("studio\\app.py")


def test_native_command_reuses_public_demo_target():
    command = native.build_native_command(host="127.0.0.1", port=8765, public_demo=True)
    assert command[-1].endswith("studio/public_demo.py") or command[-1].endswith("studio\\public_demo.py")


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "LOCALHOST", "::1"])
def test_native_accepts_explicit_loopback_hosts(host):
    assert native.is_loopback_host(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.org", ""])
def test_native_rejects_non_loopback_hosts(host):
    assert not native.is_loopback_host(host)


def test_native_window_size_is_fail_closed():
    with pytest.raises(ValueError, match="at least 640x480"):
        native._validate_window_size(639, 960)
    with pytest.raises(ValueError, match="at least 640x480"):
        native._validate_window_size(1440, 479)


def test_native_main_rejects_network_binding_before_launch(monkeypatch, capsys):
    monkeypatch.setattr(native.subprocess, "Popen", lambda *_a, **_k: pytest.fail("must not launch"))
    assert native.main(["--host", "0.0.0.0"]) == 2
    assert "loopback-only" in capsys.readouterr().err


def test_native_main_explains_missing_pywebview(monkeypatch, capsys):
    def fake_find_spec(name):
        return object() if name == "shiny" else None

    monkeypatch.setattr(native.importlib.util, "find_spec", fake_find_spec)
    assert native.main([]) == 2
    stderr = capsys.readouterr().err
    assert "requires pywebview" in stderr
    assert "gpbiometricspy[studio-native]" in stderr


def test_native_main_uses_window_and_cleans_up_server(monkeypatch):
    events: list[tuple] = []

    class FakeProcess:
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            events.append(("terminate",))
            self.returncode = 0

        def wait(self, timeout=None):
            events.append(("wait", timeout))
            return int(self.returncode or 0)

        def kill(self):
            events.append(("kill",))
            self.returncode = 0

    fake_process = FakeProcess()
    fake_webview = SimpleNamespace()

    def create_window(title, **kwargs):
        events.append(("create_window", title, kwargs))
        return object()

    def start(**kwargs):
        events.append(("start", kwargs))

    fake_webview.create_window = create_window
    fake_webview.start = start

    monkeypatch.setattr(native.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(native, "choose_port", lambda _host, port: port)
    monkeypatch.setattr(native, "wait_for_server", lambda *_a, **_k: True)
    monkeypatch.setattr(native.subprocess, "Popen", lambda _command: fake_process)
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(native.sys, "platform", "win32")

    assert native.main([]) == 0
    create = next(event for event in events if event[0] == "create_window")
    assert create[1] == native.WINDOW_TITLE
    assert create[2]["url"] == "http://127.0.0.1:8765"
    assert create[2]["min_size"] == (640, 480)
    start_event = next(event for event in events if event[0] == "start")
    assert start_event[1]["gui"] == "edgechromium"
    assert ("terminate",) in events


def test_native_browser_fallback_is_explicit(monkeypatch):
    events: list[tuple] = []

    class FakeProcess:
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = 0

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

        def kill(self):
            self.returncode = 0

    fake_webview = SimpleNamespace(
        create_window=lambda *_a, **_k: object(),
        start=lambda **_k: (_ for _ in ()).throw(RuntimeError("no webview runtime")),
    )

    monkeypatch.setattr(native.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(native, "choose_port", lambda _host, port: port)
    monkeypatch.setattr(native, "wait_for_server", lambda *_a, **_k: True)
    monkeypatch.setattr(native.subprocess, "Popen", lambda _command: FakeProcess())
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(native.webbrowser, "open", lambda url, new=0: events.append(("browser", url, new)) or True)

    assert native.main(["--browser-fallback"]) == 0
    assert events == [("browser", "http://127.0.0.1:8765", 2)]
