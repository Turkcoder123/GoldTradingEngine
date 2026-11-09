"""Live session: SiftingIO ticks plus the polled dollar index, one rule set.

Two sources feed the same buffers: SiftingIO streams the ticks of the series it
publishes, and the Dukascopy feed is polled once a minute for the dollar index,
whose 1-minute bars no tick provider offers. Before a bar is accepted the
session refreshes the newest minute Dukascopy has stored (a tail read, so it
stays cheap), moves the boundary forward and drops every live bar the stored
history now covers. Live data therefore fills the gap between two keeper
refreshes and can never rewrite the store (`docs/live.md`).
"""

from __future__ import annotations

import datetime as dt
import time

from ..shared import config, timeutil
from . import csvfile, live_bar, live_client, live_params, live_snapshot
from . import feed as feed_module


def stored_through(data_dir: str, series_key: str,
                   side: str = config.DEFAULT_SIDE) -> int:
    """Newest minute Dukascopy stored for one series and side (0 when empty)."""
    series = config.resolve_series(series_key)
    return csvfile.last_stored_ms(data_dir, side, series.prefix)


def _checked(series) -> tuple:
    """Registry keys of the live layer, rejecting anything else."""
    wanted = tuple(series or live_params.DEFAULT_LIVE_SERIES)
    unknown = [key for key in wanted if key not in live_params.DEFAULT_LIVE_SERIES]
    if not wanted or unknown:
        raise ValueError(
            f"unknown live series {', '.join(unknown) or '-'}, expected one of "
            f"{', '.join(live_params.DEFAULT_LIVE_SERIES)}")
    return wanted


class LiveSession:
    """One live run: a buffer per series, its boundary and the two sources."""

    def __init__(self, data_dir: str, series=None,
                 side: str = config.DEFAULT_SIDE,
                 buffer_minutes: int = live_params.BUFFER_MINUTES,
                 on_bar=None, key: str = None, connect=None,
                 clock=time.monotonic, sleeper=time.sleep, report=print,
                 boundary_seconds: float = live_params.BOUNDARY_REFRESH_SECONDS,
                 dxy_seconds: float = live_params.DXY_POLL_SECONDS, fetch=None,
                 now=timeutil.utc_now_minute, publish: bool = True,
                 snapshot_path: str = None):
        self.data_dir = data_dir
        self.series = _checked(series)
        self.side = side
        self.on_bar = on_bar or (lambda series_key, bar: None)
        self.report = report
        self.now = now
        self._clock = clock
        self._sleeper = sleeper
        self._fetch = fetch or feed_module.fetch_range
        self._boundary_seconds = float(boundary_seconds)
        self._boundary_at = {key: 0.0 for key in self.series}
        self._dxy_seconds = max(float(dxy_seconds), 1.0)
        self._dxy_at = 0.0
        self._dxy_cursor = 0
        self._stopped = False
        self._publishing = bool(publish)
        self._snapshot_path = (snapshot_path if snapshot_path is not None
                               else live_snapshot.path(data_dir))
        self.buffers = {
            key: live_bar.LiveBuffer(buffer_minutes,
                                     stored_through(data_dir, key, side))
            for key in self.series}
        self.feed = self._build_feed(key, connect, clock, sleeper, report)

    def _build_feed(self, key, connect, clock, sleeper, report):
        """The WebSocket feed of the streamed series, or None when polled only."""
        streamed = {series: live_params.LIVE_SERIES[series]
                    for series in self.series
                    if series in live_params.LIVE_SERIES}
        if not streamed:
            return None
        return live_client.LiveFeed(
            self._accept_tick, key=self._require_key(key), series=streamed,
            side=self.side, connect=connect, clock=clock, sleeper=sleeper,
            report=report, on_idle=self._poll_dxy)

    @staticmethod
    def _require_key(key: str | None) -> str:
        """The API key, or a readable error when the stream needs one."""
        resolved = (key or live_client.api_key() or "").strip()
        if not resolved:
            raise live_client.LiveFeedError(
                "no SiftingIO API key: set $SIFTING_API_KEY or "
                f"{live_params.API_KEY_ENV} in .env (docs/live.md)")
        return resolved

    def _refresh_boundary(self, series_key: str) -> int:
        """Reads the stored range at most once per interval and prunes.

        When the keeper caught up with the buffer, the bars it now covers are
        dropped and the published document is refreshed immediately, so the
        dashboard never draws a live bar that the stored history already holds.
        """
        moment = self._clock()
        if moment - self._boundary_at[series_key] < self._boundary_seconds:
            return 0
        self._boundary_at[series_key] = moment
        removed = self.buffers[series_key].prune(
            stored_through(self.data_dir, series_key, self.side))
        if removed:
            self._publish()
        return removed

    def _accept_tick(self, tick) -> None:
        """Buffers one tick and reports the bar that a new minute closed."""
        buffer = self.buffers[tick.series]
        self._refresh_boundary(tick.series)
        previous = buffer.newest_minute
        if not buffer.accept(tick.timestamp_ms, tick.price):
            return
        current = buffer.newest_minute
        if previous is not None and current != previous:
            bar = buffer.get(previous)
            if bar is not None:
                self._emit(tick.series, bar)

    def _emit(self, series_key: str, bar: dict) -> None:
        """Hands one closed bar to the caller and refreshes the dashboard copy."""
        self.on_bar(series_key, bar)
        self._publish()

    def _publish(self) -> None:
        """Writes the buffers for the dashboard; a failure disables it once."""
        if not self._publishing:
            return
        try:
            live_snapshot.write(self._snapshot_path, self.snapshot())
        except OSError as exc:
            self._publishing = False
            self.report(f" ! live snapshot disabled: {exc}")

    def _poll_dxy(self, force: bool = False) -> int:
        """Polls the Dukascopy feed for new dollar index bars, throttled."""
        if live_params.DXY_SERIES not in self.series:
            return 0
        moment = self._clock()
        if not force and moment - self._dxy_at < self._dxy_seconds:
            return 0
        self._dxy_at = moment
        self._refresh_boundary(live_params.DXY_SERIES)
        end = self.now()
        start = (timeutil.epoch_to_minute(self._dxy_cursor)
                 if self._dxy_cursor else end - dt.timedelta(minutes=5))
        settings = feed_module.FeedSettings(
            side=self.side,
            instrument=config.SERIES[live_params.DXY_SERIES].instrument)
        try:
            rows = list(self._fetch(start, end, settings))
        except (feed_module.FeedError, OSError) as exc:
            self.report(f" ! dxy poll failed: {exc}")
            return 0
        accepted = 0
        buffer = self.buffers[live_params.DXY_SERIES]
        for row in rows:
            if buffer.add_bar(row[0], row[1], row[2], row[3], row[4], row[5]):
                accepted += 1
                self._dxy_cursor = max(self._dxy_cursor, int(row[0]))
                bar = buffer.get(live_bar.minute_of(row[0]))
                if bar is not None:
                    self._emit(live_params.DXY_SERIES, bar)
        return accepted

    def snapshot(self) -> dict:
        """Every buffered bar per series, oldest first."""
        return {key: buffer.snapshot() for key, buffer in self.buffers.items()}

    def stop(self) -> None:
        """Asks the run to finish after the current frame."""
        self._stopped = True
        if self.feed is not None:
            self.feed.stop()

    def run(self, max_seconds=None) -> dict:
        """Streams and polls until the duration ends or `stop()` is called."""
        if self.feed is not None:
            summary = self.feed.run(max_seconds)
        else:
            summary = self._poll_only(max_seconds)
        summary.update(bars={key: len(buffer.snapshot())
                             for key, buffer in self.buffers.items()},
                       boundary={key: self._boundary_text(key)
                                 for key in self.series})
        return summary

    def _poll_only(self, max_seconds=None) -> dict:
        """A run that only polls the dollar index, used when no series streams."""
        deadline = (None if max_seconds is None
                    else self._clock() + float(max_seconds))
        self._poll_dxy(force=True)
        while not self._stopped and (deadline is None
                                     or self._clock() < deadline):
            self._sleeper(min(self._dxy_seconds, 5.0))
            self._poll_dxy()
        return {"accepted": 0, "ignored": 0, "status_events": 0, "errors": 0,
                "pongs": 0, "reconnects": 0, "stopped": self._stopped}

    def _boundary_text(self, series_key: str):
        """Boundary of one series as UTC text, or None when nothing is stored."""
        boundary = self.buffers[series_key].boundary_ms
        return timeutil.ts_to_text(boundary) if boundary else None

