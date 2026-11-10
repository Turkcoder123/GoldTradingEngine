"""Timeframes of the price chart: how a stored minute becomes one bar.

One table, so the API, the aggregation and the chart agree on the same set:
intraday resolutions aggregate whole minutes, `1d` aggregates the UTC day. The
bar caps keep a response small enough for a phone whatever the window asks for
(MOD-7 keeps the table out of the view module).
"""

from __future__ import annotations

import datetime as dt

# Minutes per bar; 0 means one UTC calendar day (the aggregation differs).
INTERVALS = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 0,
}
DEFAULT = "1d"
# Bars a single response may carry; the newest ones win.
LIMITS = {
    "1m": 1500,
    "5m": 1500,
    "15m": 1500,
    "30m": 1500,
    "1h": 2000,
    "4h": 2000,
    "1d": 3000,
}
MAX_DAYS = 3650


def minutes(interval: str) -> int:
    """Minutes per bar of one interval; raises ValueError when unknown."""
    if interval not in INTERVALS:
        raise ValueError(
            f"unknown interval {interval!r}, expected one of "
            f"{', '.join(INTERVALS)}")
    return INTERVALS[interval]


def limit(interval: str) -> int:
    """Bar cap of one interval, so a response always stays small."""
    return LIMITS[minutes_key(interval)]


def minutes_key(interval: str) -> str:
    """The canonical name of a known interval."""
    minutes(interval)
    return interval


def bucket(time_text: str, interval: str) -> tuple:
    """Bucket start of one stored minute: (key, text, day) of its bar.

    `key` is comparable across bars and files, `text` is what the page prints
    and `day` keeps the date part for the daily view and the tooltip.
    """
    size = minutes(interval)
    day = time_text[:10]
    if not size:
        return day, day, day
    hour = int(time_text[11:13])
    minute = int(time_text[14:16])
    start = (hour * 60 + minute) - (hour * 60 + minute) % size
    text = f"{day} {start // 60:02d}:{start % 60:02d}"
    return text, text, day


def _moment(text: str) -> dt.datetime:
    """Bar time as a datetime; a daily bar carries a date only."""
    for shape in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, shape)
        except ValueError:
            continue
    raise ValueError(f"unreadable bar time {text!r}")


def cutoff(bars: list, days: int) -> list:
    """The newest `days` worth of bars; 0 keeps every bar."""
    if days <= 0 or not bars:
        return bars
    first = _moment(bars[-1]["time"]) - dt.timedelta(days=int(days))
    return [bar for bar in bars if _moment(bar["time"]) >= first]
