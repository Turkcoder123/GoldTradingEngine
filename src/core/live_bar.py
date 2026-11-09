"""In-memory 1-minute aggregation of live ticks; nothing here touches a file.

Bars are keyed by the UTC minute of the tick. An out-of-order tick is accepted
as long as its minute is not covered by the authoritative Dukascopy range: open
is the earliest tick of the minute, close the latest, high and low come from
every accepted tick. The provider publishes no volume, so a live bar carries
`volume: None` instead of a fabricated number (`docs/live.md`).
"""

from __future__ import annotations

import threading

from ..shared import config, timeutil


def minute_of(timestamp_ms: int) -> int:
    """Start of the UTC minute that holds the tick, in epoch milliseconds."""
    stamp = int(timestamp_ms)
    return stamp - stamp % config.MINUTE_MS


class LiveBuffer:
    """Thread-safe window of live bars, oldest first, bounded by minutes."""

    def __init__(self, max_minutes: int = 180, boundary_ms: int = 0):
        if max_minutes < 1:
            raise ValueError("max_minutes must be positive")
        self._max_minutes = int(max_minutes)
        self._boundary_ms = int(boundary_ms)
        self._bars: dict = {}
        self._lock = threading.Lock()

    @property
    def boundary_ms(self) -> int:
        """Newest minute already covered by the authoritative stored data."""
        with self._lock:
            return self._boundary_ms

    @property
    def newest_minute(self):
        """Minute of the newest buffered bar, or None when the buffer is empty."""
        with self._lock:
            return max(self._bars) if self._bars else None

    def covered(self, timestamp_ms: int) -> bool:
        """True when the minute of the tick is already stored by Dukascopy."""
        with self._lock:
            return minute_of(timestamp_ms) <= self._boundary_ms

    def accept(self, timestamp_ms: int, price: float) -> bool:
        """Adds one tick; False when its minute is already authoritative."""
        minute = minute_of(timestamp_ms)
        stamp = int(timestamp_ms)
        with self._lock:
            if minute <= self._boundary_ms:
                return False
            bar = self._bars.get(minute)
            if bar is None:
                self._bars[minute] = {
                    "minute_ms": minute, "open": price, "high": price,
                    "low": price, "close": price, "ticks": 1, "volume": None,
                    "_open_ts": stamp, "_close_ts": stamp,
                }
                self._trim()
                return True
            bar["ticks"] += 1
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            if stamp < bar["_open_ts"]:
                bar["_open_ts"] = stamp
                bar["open"] = price
            if stamp >= bar["_close_ts"]:
                bar["_close_ts"] = stamp
                bar["close"] = price
            return True

    def add_bar(self, minute_ms: int, open_price: float, high: float,
                low: float, close: float, volume=None) -> bool:
        """Stores one complete bar from a polled source, replacing any ticks.

        A polled bar is authoritative for its minute: it replaces a bar that
        was built from ticks, and it is refused when the stored history already
        covers the minute.
        """
        minute = minute_of(minute_ms)
        with self._lock:
            if minute <= self._boundary_ms:
                return False
            self._bars[minute] = {
                "minute_ms": minute,
                "open": float(open_price),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "ticks": 0,
                "volume": None if volume is None else float(volume),
                "_open_ts": minute,
                "_close_ts": minute,
            }
            self._trim()
            return True

    def _trim(self) -> None:
        """Drops the oldest minutes so the window cannot grow without bound."""
        while len(self._bars) > self._max_minutes:
            del self._bars[min(self._bars)]

    def prune(self, boundary_ms: int) -> int:
        """Moves the boundary forward and drops every bar it now covers."""
        with self._lock:
            self._boundary_ms = max(self._boundary_ms, int(boundary_ms))
            covered = [minute for minute in self._bars
                       if minute <= self._boundary_ms]
            for minute in covered:
                del self._bars[minute]
            return len(covered)

    def get(self, minute_ms: int):
        """Copy of one bar, or None when it is no longer buffered."""
        with self._lock:
            bar = self._bars.get(int(minute_ms))
            return _public(bar) if bar else None

    def snapshot(self) -> list:
        """Every buffered bar, oldest first, as copies the caller may keep."""
        with self._lock:
            return [_public(self._bars[minute]) for minute in sorted(self._bars)]


def _public(bar: dict) -> dict:
    """Bar as reported to callers: UTC minute text, OHLC and the tick count."""
    return {
        "minute": timeutil.ts_to_text(bar["minute_ms"]),
        "minute_ms": bar["minute_ms"],
        "open": bar["open"],
        "high": bar["high"],
        "low": bar["low"],
        "close": bar["close"],
        "ticks": bar["ticks"],
        "volume": bar.get("volume"),
    }
