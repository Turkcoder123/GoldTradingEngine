"""In-process caches: one for whole responses, one for daily bar aggregates.

The dashboard reads only local CSV files, but a full year of 1-minute bars per
series costs a few seconds to aggregate. Both caches keep the read-only results
of this process, so a page load builds each section once (MOD-1).
"""

from __future__ import annotations

import os
import time

from . import price_view

_DEFAULT_TTL_SECONDS = 120.0
_DEFAULT_FILE_CAPACITY = 256


class TtlCache:
    """Remembers built responses for a few seconds, keyed by endpoint."""

    def __init__(self, ttl_seconds: float = _DEFAULT_TTL_SECONDS,
                 clock=time.monotonic):
        self._ttl = float(ttl_seconds)
        self._clock = clock
        self._items = {}

    def get_or_build(self, key, builder):
        """Cached value of `key`, built by `builder` when missing or expired."""
        now = self._clock()
        hit = self._items.get(key)
        if hit is not None and (now - hit[0]) < self._ttl:
            return hit[1]
        value = builder()
        self._items[key] = (now, value)
        return value

    def clear(self) -> None:
        """Forgets every value, used by the refresh button."""
        self._items.clear()


class DailyCache:
    """Daily bars per monthly file, keyed by path, size and modification time.

    A file that gained rows changes its size and mtime, so a cache entry is
    never stale. The dictionary order doubles as the eviction order.
    """

    def __init__(self, capacity: int = _DEFAULT_FILE_CAPACITY):
        self._capacity = int(capacity)
        self._items = {}

    def file_aggregate(self, path: str, interval: str = "1d") -> dict:
        """Bars and gap counts of one monthly CSV, once per file and interval."""
        stat = os.stat(path)
        key = (path, interval, stat.st_size, stat.st_mtime_ns)
        entry = self._items.pop(key, None)
        if entry is None:
            entry = price_view.aggregate_file(path, interval)
            while len(self._items) >= self._capacity:
                self._items.pop(next(iter(self._items)))
        self._items[key] = entry
        return entry

    def clear(self) -> None:
        """Forgets every aggregate, used by the refresh button."""
        self._items.clear()
