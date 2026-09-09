from __future__ import annotations

import socket
import sys

import pytest

from studio.desktop import DEFAULT_HOST, build_desktop_command, choose_port, wait_for_server


def test_choose_port_prefers_requested_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((DEFAULT_HOST, 0))
        port = int(probe.getsockname()[1])
    assert choose_port(DEFAULT_HOST, port) == port


def test_choose_port_falls_back_when_preferred_port_is_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind((DEFAULT_HOST, 0))
        occupied.listen(1)
        busy = int(occupied.getsockname()[1])
        selected = choose_port(DEFAULT_HOST, busy)
    assert selected != busy
    assert 0 < selected <= 65535


def test_choose_port_validates_range():
    with pytest.raises(ValueError, match="between 0 and 65535"):
        choose_port(DEFAULT_HOST, 70000)


def test_desktop_command_targets_installed_full_studio():
    command = build_desktop_command(host=DEFAULT_HOST, port=8765)
    assert command[:3] == [sys.executable, "-m", "shiny"]
    assert command[3:6] == ["run", "--host", DEFAULT_HOST]
    assert command[6:8] == ["--port", "8765"]
    assert command[-1].endswith("studio/app.py") or command[-1].endswith("studio\\app.py")


def test_desktop_command_can_target_public_boundary():
    command = build_desktop_command(host=DEFAULT_HOST, port=8765, public_demo=True)
    assert command[-1].endswith("studio/public_demo.py") or command[-1].endswith("studio\\public_demo.py")


def test_wait_for_server_detects_listening_socket():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((DEFAULT_HOST, 0))
        listener.listen(1)
        port = int(listener.getsockname()[1])
        assert wait_for_server(DEFAULT_HOST, port, timeout=0.5)


def test_wait_for_server_times_out_when_socket_is_closed():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((DEFAULT_HOST, 0))
        port = int(probe.getsockname()[1])
    assert wait_for_server(DEFAULT_HOST, port, timeout=0.05) is False
