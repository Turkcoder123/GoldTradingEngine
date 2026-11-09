"""Tests for the dashboard command line: parser, PID guard and failure paths."""

from __future__ import annotations

import argparse
import socket

import pytest

from src.features.web import cli, pidfile


def namespace(**overrides):
    """Arguments like the parser would produce, with the tested ones changed."""
    values = {"host": "127.0.0.1", "port": 8765, "data_dir": None,
              "ttl": 120.0, "pid_file": None, "no_pid": False}
    values.update(overrides)
    return argparse.Namespace(**values)


def test_parser_provides_the_documented_defaults(tmp_path):
    args = cli.build_parser().parse_args(["--data-dir", str(tmp_path)])
    assert args.host == cli.DEFAULT_HOST
    assert args.port == cli.DEFAULT_PORT
    assert args.ttl > 0
    assert args.pid_file is None
    assert args.no_pid is False


def test_parser_accepts_a_pid_file_and_no_pid(tmp_path):
    target = str(tmp_path / "custom.pid")
    args = cli.build_parser().parse_args(
        ["--pid-file", target, "--no-pid"])
    assert args.no_pid is True
    assert args.pid_file == target


def test_take_pid_refuses_a_second_run_on_the_same_address(tmp_path, capsys):
    args = namespace(port=8765)
    first = cli.take_pid(args, str(tmp_path))
    assert first is not False
    try:
        assert cli.take_pid(args, str(tmp_path)) is False
    finally:
        first.release()
    printed = capsys.readouterr().err
    assert "already running" in printed
    assert "http://127.0.0.1:8765/" in printed
    assert "--no-pid" in printed


def test_take_pid_is_skipped_with_no_pid(tmp_path):
    assert cli.take_pid(namespace(no_pid=True), str(tmp_path)) is None


def test_take_pid_uses_the_requested_file(tmp_path):
    target = str(tmp_path / "custom.pid")
    guard = cli.take_pid(namespace(pid_file=target), str(tmp_path))
    try:
        assert guard.path == target
        assert pidfile.read_record(target)["port"] == 8765
    finally:
        guard.release()


def test_main_reports_a_busy_port(tmp_path, capsys):
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        code = cli.main(["--data-dir", str(tmp_path), "--port", str(port),
                         "--no-pid"])
    assert code == 1
    assert "cannot listen" in capsys.readouterr().err


def test_main_refuses_a_second_run(tmp_path, capsys):
    guard = pidfile.PidFile(pidfile.pid_path(str(tmp_path), 8765),
                            "127.0.0.1", 8765)
    assert guard.acquire() is True
    try:
        code = cli.main(["--data-dir", str(tmp_path), "--port", "8765"])
    finally:
        guard.release()
    assert code == 1
    assert "already running" in capsys.readouterr().err


def test_main_clears_the_pid_file_when_the_server_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_serve", lambda args, data_dir: 0)
    assert cli.main(["--data-dir", str(tmp_path), "--port", "8765"]) == 0
    assert pidfile.read_record(
        pidfile.pid_path(str(tmp_path), 8765)) == {}


def test_main_clears_the_pid_file_after_a_ctrl_c(tmp_path, monkeypatch):
    def interrupt(args, data_dir):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_serve", interrupt)
    code = cli.main(["--data-dir", str(tmp_path), "--port", "8765"])
    assert code == cli.INTERRUPTED
    assert pidfile.read_record(
        pidfile.pid_path(str(tmp_path), 8765)) == {}


def test_install_stop_handler_reports_when_it_is_not_allowed(monkeypatch):
    def refuse(signum, handler):
        raise ValueError("not the main thread")

    monkeypatch.setattr(cli.signal, "signal", refuse)
    assert cli.install_stop_handler() is False


def test_install_stop_handler_replaces_the_sigterm_handler(monkeypatch):
    installed = {}

    def record(signum, handler):
        installed[signum] = handler

    monkeypatch.setattr(cli.signal, "signal", record)
    assert cli.install_stop_handler() is True
    assert installed[cli.signal.SIGTERM] is cli._on_stop_signal


def test_the_stop_handler_raises_a_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        cli._on_stop_signal(cli.signal.SIGTERM, None)


def test_serve_closes_the_socket_and_reports_an_interrupt(tmp_path, monkeypatch,
                                                          capsys):
    closed = []

    class FakeServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            closed.append(True)

    monkeypatch.setattr(cli, "ThreadingHTTPServer",
                        lambda address, handler: FakeServer())
    code = cli._serve(namespace(), str(tmp_path))
    assert code == cli.INTERRUPTED
    assert closed == [True]
    assert "dashboard : http://127.0.0.1:8765/" in capsys.readouterr().out


def test_main_can_skip_the_pid_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_serve", lambda args, data_dir: 0)
    assert cli.main(["--data-dir", str(tmp_path), "--port", "8765",
                     "--no-pid"]) == 0
    assert not (tmp_path / "dashboard-8765.pid").exists()
