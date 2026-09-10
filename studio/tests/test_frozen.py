from __future__ import annotations

from types import SimpleNamespace

import studio.frozen as frozen


def test_frozen_main_runs_shiny_in_process(monkeypatch):
    app = object()
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(frozen, "choose_port", lambda host, port: port)
    monkeypatch.setattr(frozen, "_load_studio_app", lambda *, public_demo: app)

    def fake_run_app(app_arg, **kwargs):
        calls.append({"app": app_arg, **kwargs})

    monkeypatch.setattr(frozen, "run_app", fake_run_app)

    result = frozen.main(["--host", "127.0.0.1", "--port", "8765", "--no-browser"])

    assert result == 0
    assert calls == [
        {
            "app": app,
            "host": "127.0.0.1",
            "port": 8765,
            "reload": False,
            "launch_browser": False,
            "dev_mode": False,
        }
    ]


def test_frozen_main_selects_public_boundary_and_fallback_port(monkeypatch, capsys):
    app = SimpleNamespace(name="public")
    selected: list[bool] = []
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(frozen, "choose_port", lambda host, port: 9123)

    def fake_load(*, public_demo: bool):
        selected.append(public_demo)
        return app

    def fake_run_app(app_arg, **kwargs):
        calls.append({"app": app_arg, **kwargs})

    monkeypatch.setattr(frozen, "_load_studio_app", fake_load)
    monkeypatch.setattr(frozen, "run_app", fake_run_app)

    result = frozen.main(["--public-demo", "--no-browser"])

    assert result == 0
    assert selected == [True]
    assert calls[0]["app"] is app
    assert calls[0]["port"] == 9123
    assert calls[0]["launch_browser"] is False
    output = capsys.readouterr().out
    assert "Starting frozen gpbiometricspy Studio at http://127.0.0.1:9123" in output
    assert "Preferred port 8765 was unavailable; using 9123 instead." in output


def test_frozen_parser_defaults_to_local_browser_launch(monkeypatch):
    app = object()
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(frozen, "choose_port", lambda host, port: port)
    monkeypatch.setattr(frozen, "_load_studio_app", lambda *, public_demo: app)
    monkeypatch.setattr(
        frozen,
        "run_app",
        lambda app_arg, **kwargs: calls.append({"app": app_arg, **kwargs}),
    )

    assert frozen.main([]) == 0
    assert calls[0]["host"] == frozen.DEFAULT_HOST
    assert calls[0]["port"] == frozen.DEFAULT_PORT
    assert calls[0]["launch_browser"] is True
