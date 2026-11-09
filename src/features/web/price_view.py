"""Daily bars aggregated from the stored 1-minute CSVs (read only).

A year of minute bars is far too much to send to a browser, so the dashboard
aggregates one monthly file into daily OHLC bars. That aggregation is expensive
(roughly a third of a second per month on a phone), which is why `cache.py`
keeps the result per file and this module never caches anything itself (MOD-1).
"""

from __future__ import annotations

import datetime as dt
import os

from ...core import csvfile
from ...core.quotes import PRICE_DIGITS, numbers
from ...shared import config


def _minute_index(text: str) -> int:
    """'YYYY-MM-DD HH:MM:SS' as a serial minute number; 0 when unreadable.

    Built from slices instead of `strptime` because it runs once per stored
    minute; the result only has to be comparable, not meaningful.
    """
    try:
        day = dt.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))
        return (day.toordinal() * config.MINUTES_PER_DAY
                + int(text[11:13]) * 60 + int(text[14:16]))
    except (ValueError, IndexError):
        return 0


def aggregate_file(path: str) -> dict:
    """Daily OHLC bars plus the minute-gap statistics of one monthly CSV.

    A bar holds the first open and the last close of the day, the highest high,
    the lowest low, the summed volume and the number of stored minutes. The gap
    numbers use the same rules as `update_1m.py --status`, including market
    closures, so they stay comparable with the CLI report.
    """
    days = {}
    gaps = missing = largest = 0
    previous = 0
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        handle.readline()                                # header line
        for line in handle:
            parts = line.split(",")
            if len(parts) < len(config.COLUMNS):
                continue
            values = numbers(parts)
            if values is None:
                continue
            day = parts[0][:10]
            bar = days.get(day)
            if bar is None:
                days[day] = {
                    "day": day,
                    "open": round(values[0], PRICE_DIGITS),
                    "high": round(values[1], PRICE_DIGITS),
                    "low": round(values[2], PRICE_DIGITS),
                    "close": round(values[3], PRICE_DIGITS),
                    "volume": values[4],
                    "count": 1,
                }
            else:
                if values[1] > bar["high"]:
                    bar["high"] = round(values[1], PRICE_DIGITS)
                if values[2] < bar["low"]:
                    bar["low"] = round(values[2], PRICE_DIGITS)
                bar["close"] = round(values[3], PRICE_DIGITS)
                bar["volume"] += values[4]
                bar["count"] += 1
            minute = _minute_index(parts[0])
            if previous and minute:
                step = minute - previous
                if step > 1:
                    gaps += 1
                    missing += step - 1
                    largest = max(largest, step - 1)
            if minute:
                previous = minute
    return {
        "bars": [days[day] for day in sorted(days)],
        "gaps": gaps,
        "missing_minutes": missing,
        "largest_gap_minutes": largest,
    }


def month_paths(data_dir: str, prefix: str, months: int = 0) -> list:
    """Newest `months` stored files of a series; 0 means every stored month."""
    paths = csvfile.month_files(data_dir, config.DEFAULT_SIDE, prefix)
    if months > 0:
        return paths[-months:]
    return paths


def month_keys(paths: list) -> list:
    """Month labels ('2026-11') of the given files, oldest first."""
    return [os.path.basename(path).split("_")[-1][:-len(".csv")]
            for path in paths]


def combine(entries: list) -> tuple:
    """Bars of several aggregated files plus their summed gap statistics."""
    bars = []
    quality = {"gaps": 0, "missing_minutes": 0, "largest_gap_minutes": 0}
    for entry in entries:
        bars.extend(entry["bars"])
        quality["gaps"] += entry["gaps"]
        quality["missing_minutes"] += entry["missing_minutes"]
        quality["largest_gap_minutes"] = max(quality["largest_gap_minutes"],
                                             entry["largest_gap_minutes"])
    return bars, quality


def summarize(bars: list) -> dict:
    """First and last close, extremes, bar count and change of one window."""
    if not bars:
        return {
            "days": 0, "bars": 0, "first_day": None, "last_day": None,
            "high": None, "low": None, "first_close": None,
            "last_close": None, "change_pct": None, "volume": 0.0,
        }
    first_close = bars[0]["close"]
    last_close = bars[-1]["close"]
    change = None
    if first_close:
        change = round((last_close - first_close) / first_close * 100, 2)
    return {
        "days": len(bars),
        "bars": sum(bar["count"] for bar in bars),
        "first_day": bars[0]["day"],
        "last_day": bars[-1]["day"],
        "high": round(max(bar["high"] for bar in bars), PRICE_DIGITS),
        "low": round(min(bar["low"] for bar in bars), PRICE_DIGITS),
        "first_close": first_close,
        "last_close": last_close,
        "change_pct": change,
        "volume": round(sum(bar["volume"] for bar in bars), PRICE_DIGITS),
    }


def payload(loader, data_dir: str, key: str, months: int) -> dict:
    """One price series as daily bars plus the summary of the window.

    `loader` turns one file path into its aggregate (the cache in `cache.py`).
    """
    series = config.resolve_series(key)
    paths = month_paths(data_dir, series.prefix, months)
    bars, quality = combine([loader(path) for path in paths])
    return {
        "key": series.key,
        "instrument": series.instrument,
        "side": config.DEFAULT_SIDE,
        "months_requested": months,
        "months": month_keys(paths),
        "bars": bars,
        "quality": quality,
        "summary": summarize(bars),
    }
