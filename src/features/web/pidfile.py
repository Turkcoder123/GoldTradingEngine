"""Single-instance guard for one dashboard address: a PID file plus a lock.

Starting the dashboard twice on the same port would either die on a raw socket
error or leave two servers with two caches, so the start-up path takes a lock
first. The file carries the pid, the address and the start time for the report;
the OS lock decides, which is why a crashed run never blocks the next one
(`core/lock.py`).
"""

from __future__ import annotations

import json
import os

from ...core.lock import Lock
from ...shared import config, timeutil
from .payload import version_text

_PID_SUFFIX = ".pid"


def pid_path(data_dir: str, port: int, value: str | None = None) -> str:
    """--pid-file > <data dir>/dashboard-<port>.pid (one file per address)."""
    if value:
        return os.path.abspath(value)
    return os.path.join(os.path.abspath(data_dir),
                        f"dashboard-{port}{_PID_SUFFIX}")


def read_record(path: str) -> dict:
    """Record of one PID file: the JSON we write, or the bare pid of the lock."""
    try:
        with open(path, "r", encoding=config.ENCODING) as handle:
            text = handle.read().strip()
    except OSError:
        return {}
    if not text:
        return {}
    if text.isdigit():
        return {"pid": int(text)}
    try:
        record = json.loads(text)
    except ValueError:
        return {}
    return record if isinstance(record, dict) else {}


class PidFile:
    """Lock of one dashboard address, with a readable record of the holder."""

    def __init__(self, path: str, host: str, port: int):
        self.path = path
        self.host = host
        self.port = port
        self.reason = ""
        self.record = {}
        self._lock = Lock(path)
        self._owned = False

    @property
    def url(self) -> str:
        """Address this guard stands for, as printed to the user."""
        return f"http://{self.host}:{self.port}/"

    def acquire(self) -> bool:
        """Takes the address; False when another run still holds it."""
        if not self._lock.acquire():
            self.reason = self._lock.reason
            self.record = read_record(self.path)
            return False
        self._owned = True
        self._write()
        return True

    def release(self) -> None:
        """Clears the record and drops the lock; safe to call twice."""
        if not self._owned:
            return
        self._owned = False
        self._clear()
        self._lock.release()

    def _write(self) -> None:
        """Stores who holds the address; a failure is reported, not raised."""
        self.record = {
            "pid": os.getpid(),
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "started_at": timeutil.utc_now().strftime(config.TIMESTAMP_FORMAT),
            "version": version_text(),
        }
        try:
            with open(self.path, "w", encoding=config.ENCODING) as handle:
                json.dump(self.record, handle, ensure_ascii=True)
                handle.write("\n")
        except OSError as exc:
            self.reason = f"could not write {self.path}: {exc}"

    def _clear(self) -> None:
        """Leaves an empty file, so a stale record cannot claim a free address."""
        try:
            with open(self.path, "w", encoding=config.ENCODING):
                pass
        except OSError as exc:
            self.reason = f"could not clear {self.path}: {exc}"
