from __future__ import annotations

import sys
from types import SimpleNamespace

import studio.native_frozen as native_frozen


def test_frozen_native_rejects_non_loopback_before_webview(monkeypatch, capsys):
    monkeypatch.delitem(sys.modules, "webview", raising=False)
    assert native_frozen.main(["--host", "0.0.0.0"]) == 2
    assert "loopback-only" in capsys.readouterr().err


def test_run_server_surfaces_shiny_failure(monkeypatch):
    errors = []
    monkeypatch.setattr(native_frozen, "run_app", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    native_frozen._run_server(object(), host="127.0.0.1", port=8765, errors=errors)
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)


def test_frozen_native_uses_edgechromium_and_same_app(monkeypatch):
    events: list[tuple] = []

    class FakeThread:
        def __init__(self, *, target, kwargs, name, daemon):
            events.append(("thread", name, daemon, target, kwargs))

        def start(self):
            events.append(("thread-start",))

    def create_window(title, **kwargs):
        events.append(("create-window", title, kwargs))
        return object()

    def start(*args, **kwargs):
        events.append(("webview-start", args, kwargs))

    fake_webview = SimpleNamespace(create_window=create_window, start=start)
    app = object()

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(native_frozen, "choose_port", lambda _host, port: port)
    monkeypatch.setattr(native_frozen, "_load_studio_app", lambda *, public_demo: app)
    monkeypatch.setattr(native_frozen, "wait_for_server", lambda *_a, **_k: True)
    monkeypatch.setattr(native_frozen.threading, "Thread", FakeThread)
    monkeypatch.setattr(native_frozen.sys, "platform", "win32")

    assert native_frozen.main(["--automation-close-seconds", "2"]) == 0
    thread_event = next(event for event in events if event[0] == "thread")
    assert thread_event[2] is True
    assert thread_event[4]["app"] is app
    create_event = next(event for event in events if event[0] == "create-window")
    assert create_event[1] == "gpbiometricspy Studio"
    assert create_event[2]["url"] == "http://127.0.0.1:8765"
    start_event = next(event for event in events if event[0] == "webview-start")
    assert start_event[2]["gui"] == "edgechromium"
    assert start_event[2]["private_mode"] is True
    assert len(start_event[1]) == 2


def test_frozen_native_can_select_public_boundary(monkeypatch):
    selected: list[bool] = []

    class FakeThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    fake_webview = SimpleNamespace(
        create_window=lambda *_a, **_k: object(),
        start=lambda *_a, **_k: None,
    )

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(native_frozen, "choose_port", lambda _host, port: port)
    monkeypatch.setattr(
        native_frozen,
        "_load_studio_app",
        lambda *, public_demo: selected.append(public_demo) or object(),
    )
    monkeypatch.setattr(native_frozen, "wait_for_server", lambda *_a, **_k: True)
    monkeypatch.setattr(native_frozen.threading, "Thread", FakeThread)

    assert native_frozen.main(["--public-demo"]) == 0
    assert selected == [True]
