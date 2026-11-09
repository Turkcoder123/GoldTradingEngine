"""Tests for the dashboard PID guard (one instance per address)."""

from __future__ import annotations

import json
import os

from src.features.web import pidfile


def test_acquire_writes_the_record(tmp_path):
    guard = pidfile.PidFile(str(tmp_path / "dashboard-8765.pid"),
                            "127.0.0.1", 8765)
    assert guard.acquire() is True
    try:
        record = json.loads(
            (tmp_path / "dashboard-8765.pid").read_text(encoding="utf-8"))
        assert record["pid"] == os.getpid()
        assert record["host"] == "127.0.0.1"
        assert record["port"] == 8765
        assert record["url"] == "http://127.0.0.1:8765/"
        assert record["version"]
        assert record["started_at"]
        assert guard.reason == ""
        assert guard.url == "http://127.0.0.1:8765/"
    finally:
        guard.release()


def test_second_start_is_refused_and_reports_the_holder(tmp_path):
    path = str(tmp_path / "dashboard-8765.pid")
    first = pidfile.PidFile(path, "127.0.0.1", 8765)
    second = pidfile.PidFile(path, "127.0.0.1", 8765)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
        assert "another run holds" in second.reason
        assert second.record["pid"] == os.getpid()
        assert second.record["url"] == "http://127.0.0.1:8765/"
    finally:
        first.release()


def test_release_clears_the_record_and_frees_the_address(tmp_path):
    path = str(tmp_path / "dashboard-8765.pid")
    first = pidfile.PidFile(path, "127.0.0.1", 8765)
    assert first.acquire() is True
    first.release()
    assert pidfile.read_record(path) == {}
    second = pidfile.PidFile(path, "127.0.0.1", 8765)
    assert second.acquire() is True
    second.release()


def test_a_stale_record_does_not_block_a_new_start(tmp_path):
    path = tmp_path / "dashboard-8765.pid"
    path.write_text('{"pid": 999999, "url": "http://127.0.0.1:8765/"}',
                    encoding="utf-8")
    guard = pidfile.PidFile(str(path), "127.0.0.1", 8765)
    assert guard.acquire() is True
    assert guard.record["pid"] == os.getpid()
    guard.release()


def test_a_stale_record_is_not_reported_as_a_running_instance(tmp_path):
    path = tmp_path / "dashboard-8765.pid"
    path.write_text('{"pid": 999999}', encoding="utf-8")
    guard = pidfile.PidFile(str(path), "127.0.0.1", 8765)
    assert guard.acquire() is True
    assert guard.record["pid"] == os.getpid()
    guard.release()


def test_read_record_accepts_the_bare_pid_of_the_lock(tmp_path):
    path = tmp_path / "raw.pid"
    path.write_text(str(os.getpid()), encoding="ascii")
    assert pidfile.read_record(str(path)) == {"pid": os.getpid()}


def test_read_record_handles_missing_empty_and_broken_files(tmp_path):
    assert pidfile.read_record(str(tmp_path / "missing.pid")) == {}
    for name, content in (("empty.pid", ""), ("broken.pid", "not json"),
                          ("list.pid", "[1, 2]")):
        target = tmp_path / name
        target.write_text(content, encoding="ascii")
        assert pidfile.read_record(str(target)) == {}, name


def test_pid_path_defaults_to_the_data_directory(tmp_path):
    assert pidfile.pid_path(str(tmp_path), 8765) == str(
        tmp_path / "dashboard-8765.pid")


def test_pid_path_can_be_overridden(tmp_path):
    target = str(tmp_path / "custom.pid")
    assert pidfile.pid_path(str(tmp_path), 8765, target) == target


def test_two_ports_do_not_share_a_pid_file(tmp_path):
    assert (pidfile.pid_path(str(tmp_path), 8765)
            != pidfile.pid_path(str(tmp_path), 9000))


def test_release_without_acquire_is_safe(tmp_path):
    guard = pidfile.PidFile(str(tmp_path / "dashboard-8765.pid"),
                            "127.0.0.1", 8765)
    guard.release()
    assert guard.reason == ""
    assert not (tmp_path / "dashboard-8765.pid").exists()
