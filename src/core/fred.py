"""FRED macro series: downloads, stores and summarizes them as CSV.

Storage and summarising only; the download lives in `core/fred_feed.py` and the
reporting in `features/cli/fred_app.py`. Files keep the full FRED history as
`date,value` (empty value = FRED reported a missing observation).
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import time
from dataclasses import dataclass, field

from ..shared import config
from .fred_feed import FredError, download, numeric_points, parse_rows

_YEAR_LOOKBACK_DAYS = 365


@dataclass(frozen=True)
class FredResult:
    """What one update stored, so the CLI can report it (CODE-3)."""

    files: tuple = ()
    counts: dict = field(default_factory=dict)
    summaries: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when every series was written without an error."""
        return self.error is None


@dataclass(frozen=True)
class FredSummary:
    """Latest observation of one series plus its short and yearly change."""

    series_id: str = ""
    date: str | None = None
    value: float | None = None
    change: float | None = None
    year_change: float | None = None
    observations: int = 0

    def to_dict(self) -> dict:
        """Plain dict for --json."""
        return dict(self.__dict__)


def _series_path(data_dir: str, series_id: str) -> str:
    """Path of one stored series."""
    return os.path.join(config.fred_dir(data_dir), f"{series_id}.csv")


def write_csv(path: str, rows: list) -> int:
    """Writes 'date,value' rows; returns the observation count."""
    if not rows:
        return 0
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding=config.ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "value"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def read_stored(path: str) -> list:
    """Rows of an already stored series (no network)."""
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        return list(csv.DictReader(handle))


def _year_ago(points: list, date: str, days: int) -> float | None:
    """Value of the last observation at or before `date - days`."""
    cutoff = dt.date.fromisoformat(date) - dt.timedelta(days=days)
    cutoff_text = cutoff.isoformat()
    found = None
    for when, value in points:
        if when <= cutoff_text:
            found = value
        else:
            break
    return found


def summarize(series_id: str, rows: list,
              days: int = _YEAR_LOOKBACK_DAYS) -> FredSummary:
    """Latest value, the change since the previous point and a year earlier."""
    points = numeric_points(rows)
    if not points:
        return FredSummary(series_id=series_id, observations=len(rows))
    date, value = points[-1]
    previous = points[-2][1] if len(points) > 1 else None
    year_ago = _year_ago(points, date, days)
    return FredSummary(
        series_id=series_id,
        date=date,
        value=value,
        change=(value - previous) if previous is not None else None,
        year_change=(value - year_ago) if year_ago is not None else None,
        observations=len(rows),
    )


def status(data_dir: str, series_ids=None) -> dict:
    """Summarizes the stored series; missing files are simply absent."""
    wanted = series_ids or config.FRED_SERIES
    summaries = {}
    for series_id in wanted:
        path = _series_path(data_dir, series_id)
        if not os.path.exists(path):
            continue
        summaries[series_id] = summarize(series_id, read_stored(path))
    return summaries


def update_fred(data_dir: str, series_ids=None) -> FredResult:
    """Downloads the requested series and stores them under <data>/fred."""
    wanted = list(series_ids or config.FRED_SERIES)
    files, counts, summaries = [], {}, {}
    for position, series_id in enumerate(wanted):
        if position:
            time.sleep(config.FRED_PAUSE_SECONDS)   # be gentle with the host
        try:
            rows = parse_rows(download(series_id))
        except FredError as exc:
            return FredResult(files=tuple(files), counts=counts,
                              summaries=summaries, error=str(exc))
        name = f"{series_id}.csv"
        counts[name] = write_csv(_series_path(data_dir, series_id), rows)
        summaries[series_id] = summarize(series_id, rows)
        files.append(name)
    return FredResult(files=tuple(files), counts=counts, summaries=summaries)
