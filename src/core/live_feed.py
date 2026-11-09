"""Live session: Twelve Data ticks joined with the authoritative stored range.

The session owns the buffer and the precedence rule: before a tick is accepted
it refreshes the newest minute Dukascopy has stored (a tail read, so it stays
cheap), moves the boundary forward and drops every live bar that is now
covered. A tick at or before that boundary is refused instead of overwriting
history, and a tick that starts a new minute hands the previous bar to the
caller as closed (`docs/live.md`).
"""

from __future__ import annotations

import time

from ..shared import config, timeutil
from . import csvfile, live_bar, live_client, live_params


def stored_through(data_dir: str, series_key: str = config.DEFAULT_SERIES,
                   side: str = config.DEFAULT_SIDE) -> int:
    """Newest minute Dukascopy stored for one series and side (0 when empty)."""
    series = config.resolve_series(series_key)
    return csvfile.last_stored_ms(data_dir, side, series.prefix)


class LiveSession:
    """One live run over a stored series: buffer, precedence and callbacks."""

    def __init__(self, data_dir: str, series_key: str = config.DEFAULT_SERIES,
                 side: str = config.DEFAULT_SIDE,
                 buffer_minutes: int = live_params.BUFFER_MINUTES,
                 on_bar=None, key: str = None, symbol: str = live_params.SYMBOL,
                 connect=None, clock=time.monotonic, sleeper=time.sleep,
                 report=print,
                 boundary_seconds: float = live_params.BOUNDARY_REFRESH_SECONDS):
        self.data_dir = data_dir
        self.series_key = series_key
        self.side = side
        self.on_bar = on_bar or (lambda bar: None)
        self.report = report
        self._clock = clock
        self._boundary_seconds = float(boundary_seconds)
        self._boundary_at = 0.0
        self.buffer = live_bar.LiveBuffer(
            buffer_minutes,
            stored_through(data_dir, series_key, side))
        self.feed = live_client.LiveFeed(
            self.accept_tick, key=self._require_key(key), symbol=symbol,
            side=side, connect=connect, clock=clock, sleeper=sleeper,
            report=report)

    @staticmethod
    def _require_key(key: str | None) -> str:
        """The API key of this session; a missing key is a readable error."""
        resolved = (key or live_client.api_key() or "").strip()
        if not resolved:
            raise live_client.LiveFeedError(
                "no Twelve Data API key: set $TWELVE_DATA_API_KEY or "
                f"{live_params.API_KEY_ENV} in .env (docs/live.md)")
        return resolved

    def _refresh_boundary(self, force: bool = False) -> int:
        """Reads the stored range at most once per interval and prunes."""
        now = self._clock()
        if not force and now - self._boundary_at < self._boundary_seconds:
            return self.buffer.boundary_ms
        self._boundary_at = now
        return self.buffer.prune(
            stored_through(self.data_dir, self.series_key, self.side))

    def accept_tick(self, tick) -> None:
        """Buffers one tick and reports the bar that a new minute closed."""
        self._refresh_boundary()
        previous = self.buffer.newest_minute
        if not self.buffer.accept(tick.timestamp_ms, tick.price):
            return
        current = self.buffer.newest_minute
        if previous is not None and current != previous:
            bar = self.buffer.get(previous)
            if bar is not None:
                self.on_bar(bar)

    def snapshot(self) -> list:
        """Every buffered live bar, oldest first."""
        return self.buffer.snapshot()

    def stop(self) -> None:
        """Asks the stream to finish after the current frame."""
        self.feed.stop()

    def run(self, max_seconds=None) -> dict:
        """Streams until the duration ends, then answers the run counters."""
        summary = self.feed.run(max_seconds)
        summary.update(bars=len(self.snapshot()), boundary=self._boundary_text())
        return summary

    def _boundary_text(self):
        """Boundary as UTC text, or None when nothing is stored yet."""
        boundary = self.buffer.boundary_ms
        return timeutil.ts_to_text(boundary) if boundary else None
