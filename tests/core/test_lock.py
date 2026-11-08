"""Tests for the single-instance lock."""

import os

from src.core import lock


def test_acquire_writes_the_pid_and_releases_cleanly(tmp_path):
    guard = lock.Lock(str(tmp_path / "test.lock"))
    assert guard.acquire() is True
    try:
        with open(guard.path, "r", encoding="ascii") as handle:
            assert handle.read() == str(os.getpid())
    finally:
        guard.release()
    assert guard.reason == ""


def test_second_lock_is_refused_while_the_first_is_held(tmp_path):
    path = str(tmp_path / "test.lock")
    first = lock.Lock(path)
    second = lock.Lock(path)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
        assert "another run holds" in second.reason
    finally:
        first.release()


def test_lock_can_be_taken_again_after_release(tmp_path):
    path = str(tmp_path / "test.lock")
    first = lock.Lock(path)
    assert first.acquire() is True
    first.release()
    second = lock.Lock(path)
    assert second.acquire() is True
    second.release()


def test_release_without_acquire_is_safe(tmp_path):
    guard = lock.Lock(str(tmp_path / "test.lock"))
    guard.release()
    assert guard.reason == ""


def test_acquire_creates_the_lock_directory(tmp_path):
    guard = lock.Lock(str(tmp_path / "locks" / "test.lock"))
    assert guard.acquire() is True
    try:
        assert os.path.exists(guard.path)
    finally:
        guard.release()


def test_lock_is_enforced_on_posix():
    assert lock.Lock("unused.lock").enforced is True


def test_context_manager_releases_the_lock(tmp_path):
    path = str(tmp_path / "test.lock")
    guard = lock.Lock(path)
    with guard:
        assert guard.acquire() is True
        assert os.path.exists(path)
    assert guard._handle is None
    assert lock.Lock(path).acquire() is True
