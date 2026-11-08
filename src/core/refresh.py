"""One catch-up run: walks from the newest stored minute towards now.

The walk never writes bars beyond an unproven empty stretch: a segment that
returns nothing is treated as a market closure only while it stays shorter than
`empty_allowance_hours` (a weekend plus a holiday). Beyond that the run stops
before storing later bars, so the missing minutes stay at the end of the file
and the next run retries them - a feed problem can therefore never punch an
unfillable hole into the stored history (B-1).
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass

from ..shared import config, timeutil
from . import csvfile
from . import feed as feed_module
from . import storage

_MINUTE = dt.timedelta(minutes=1)


@dataclass(frozen=True)
class RefreshSettings:
    """Everything one run needs; built once by the CLI."""

    segment_hours: int = config.DEFAULT_SEGMENT_HOURS
    max_segments: int = config.DEFAULT_SEGMENTS
    empty_allowance_hours: int = config.DEFAULT_EMPTY_ALLOWANCE_HOURS
    since: dt.datetime | None = None
    prefix: str = config.PREFIX
    feed: feed_module.FeedSettings = feed_module.FeedSettings()


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of one run, reported by the CLI (never by the core itself)."""

    ok: bool = True
    added: int = 0
    segments: int = 0
    start: str | None = None
    end: str | None = None
    last_bar: str | None = None
    pending_minutes: int = 0
    done: bool = False
    closure_hours: float = 0.0
    late: int = 0
    files: tuple = ()
    error: str | None = None


def initial_cursor(data_dir: str, settings: RefreshSettings, now) -> tuple:
    """First minute to fetch, plus the newest stored minute (0 when empty)."""
    last_ms = csvfile.last_stored_ms(data_dir, settings.feed.side,
                                     settings.prefix)
    if last_ms:
        return timeutil.epoch_to_minute(last_ms) + _MINUTE, last_ms
    if settings.since is not None:
        return timeutil.minute_floor(settings.since), 0
    bootstrap = now - dt.timedelta(days=config.BOOTSTRAP_DAYS)
    return timeutil.minute_floor(bootstrap), 0


class _Walk:
    """Mutable state of one run; keeps refresh_once() short and readable."""

    def __init__(self, data_dir: str, settings: RefreshSettings, now):
        self.data_dir = data_dir
        self.settings = settings
        self.now = now
        self.side = settings.feed.side
        self.cursor = None
        self.start = None
        self.last_ms = 0
        self.added = 0
        self.late = 0
        self.segments = 0
        self.closure = 0.0
        self.files: set = set()

    def run(self) -> RefreshResult:
        """Walks the gap and returns a result; failures become `error`."""
        try:
            self.cursor, self.last_ms = initial_cursor(
                self.data_dir, self.settings, self.now)
            self.start = self.cursor
            return self._walk()
        except (feed_module.FeedError, storage.StorageError, OSError) as exc:
            return self._result(error=str(exc))

    def _walk(self) -> RefreshResult:
        step = dt.timedelta(hours=max(int(self.settings.segment_hours), 1))
        allowance = dt.timedelta(
            hours=max(int(self.settings.empty_allowance_hours), 1))
        empty_since = None
        limit = max(int(self.settings.max_segments), 1)
        while self.cursor < self.now and self.segments < limit:
            segment_end = min(self.cursor + step, self.now)
            rows = list(feed_module.fetch_range(
                self.cursor, segment_end, self.settings.feed))
            self.segments += 1
            if rows:
                if empty_since is not None:
                    self.closure += (
                        (self.cursor - empty_since).total_seconds() / 3600)
                    empty_since = None
                self._store(rows)
            else:
                if empty_since is None:
                    empty_since = self.cursor
                if segment_end - empty_since > allowance:
                    break            # the gap is too long to be a closure
            self.cursor = segment_end
        return self._result()

    def _store(self, rows) -> None:
        """Appends one segment and keeps the counters of the run in sync."""
        result = storage.append_rows(self.data_dir, rows, self.side,
                                    self.settings.prefix)
        self.added += result.added
        self.late += result.late
        self.files.update(result.files)
        self.last_ms = max(self.last_ms, result.newest)

    def _result(self, error: str | None = None) -> RefreshResult:
        """Snapshot of the run; `last_bar` is what is stored on disk."""
        cursor = self.cursor if self.cursor is not None else self.now
        done = error is None and cursor >= self.now
        return RefreshResult(
            ok=error is None,
            added=self.added,
            segments=self.segments,
            start=(self.start.strftime(config.TIMESTAMP_FORMAT)[:16]
                   if self.start else None),
            end=cursor.strftime(config.TIMESTAMP_FORMAT)[:16],
            last_bar=(timeutil.ts_to_text(self.last_ms)
                      if self.last_ms else None),
            pending_minutes=(0 if done else
                             int((self.now - cursor).total_seconds() // 60)),
            done=done,
            closure_hours=round(self.closure, 2),
            late=self.late,
            files=tuple(sorted(self.files)),
            error=error,
        )


def refresh_once(data_dir: str,
                 settings: RefreshSettings | None = None) -> RefreshResult:
    """Fills the gap between the newest stored bar and now. Never raises."""
    run_settings = settings or RefreshSettings()
    now = timeutil.utc_now_minute()
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError as exc:
        message = f"cannot create {data_dir}: {exc}"
        return RefreshResult(ok=False, error=message)
    return _Walk(data_dir, run_settings, now).run()
