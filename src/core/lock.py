"""Single-instance advisory lock: two writers would interleave one CSV."""

from __future__ import annotations

import errno
import os

try:                      # POSIX only; the lock is advisory by design (GIT-6)
    import fcntl
except ImportError:       # pragma: no cover - Windows has no fcntl
    fcntl = None

_BUSY_ERRNOS = (errno.EAGAIN, errno.EACCES)


class Lock:
    """flock() based lock, released by the OS when the process dies."""

    def __init__(self, path: str):
        self.path = path
        self.reason = ""                  # why acquire() failed, for the CLI
        self.enforced = fcntl is not None
        self._handle = None

    def acquire(self) -> bool:
        """Takes the lock; False when it is held or cannot be made."""
        if fcntl is None:
            self.reason = "file locks are not available on this platform"
            return True
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._handle = open(self.path, "a+")
            fcntl.flock(self._handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.reason = self._describe(exc)
            self._close()
            return False
        self._write_pid()
        return True

    def _describe(self, exc: OSError) -> str:
        """Turns a flock/open failure into a message a user can act on."""
        if exc.errno in _BUSY_ERRNOS:
            return f"another run holds {self.path}"
        return f"cannot lock {self.path}: {exc}"

    def release(self) -> None:
        """Drops the lock; safe to call when it was never taken."""
        if self._handle is None:
            return
        try:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
        except OSError as exc:
            self.reason = f"could not release {self.path}: {exc}"
        self._close()

    def _write_pid(self) -> None:
        """Records the pid inside the lock file; a failure is only recorded."""
        try:
            self._handle.seek(0)
            self._handle.truncate()
            self._handle.write(str(os.getpid()))
            self._handle.flush()
        except OSError as exc:
            self.reason = f"could not write the pid into {self.path}: {exc}"

    def _close(self) -> None:
        """Closes the handle once, recording any failure reason."""
        if self._handle is None:
            return
        handle, self._handle = self._handle, None
        try:
            handle.close()
        except OSError as exc:
            self.reason = f"could not close {self.path}: {exc}"

    def __enter__(self) -> "Lock":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()
