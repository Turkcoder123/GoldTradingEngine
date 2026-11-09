"""Quotes read from the edges of a stored file: the newest and the oldest row.

An overview card must not aggregate a month of minute bars, so the last close
and the close of the day before it are read from the end of the newest file, and
the first close from the start of the oldest one (CODE-8 keeps the window
explicit instead of guessing a row count).
"""

from __future__ import annotations

import os

from ..shared import config

PRICE_DIGITS = 6


def numbers(parts: list):
    """open, high, low, close, volume of one CSV row; None when unreadable."""
    try:
        return (float(parts[1]), float(parts[2]), float(parts[3]),
                float(parts[4]), float(parts[5]))
    except (IndexError, ValueError):
        return None


def tail_quotes(path: str, max_bytes: int = config.TAIL_BYTES * 64) -> dict:
    """Last close of one file and the close of the day before it.

    Only the tail of the file is read, so a card costs a few milliseconds
    instead of a full aggregation. The window is large enough for a weekend,
    the daily session break and a holiday closure.
    """
    if not os.path.exists(path):
        return {}
    size = os.path.getsize(path)
    with open(path, "rb") as handle:
        start = max(0, size - max_bytes)
        handle.seek(start)
        chunk = handle.read()
    lines = chunk.decode("ascii", "replace").splitlines()
    if start and lines:
        lines = lines[1:]                     # the first line may be cut
    latest = None
    previous = None
    for line in reversed(lines):
        parts = line.split(",")
        if len(parts) < len(config.COLUMNS):
            continue
        values = numbers(parts)
        if values is None:
            continue
        day = parts[0][:10]
        if latest is None:
            latest = {"last_day": day, "last_bar": parts[0],
                      "last_close": round(values[3], PRICE_DIGITS)}
            continue
        if day == latest["last_day"]:
            continue
        if previous is None:
            previous = {"previous_day": day,
                        "previous_close": round(values[3], PRICE_DIGITS)}
        elif day != previous["previous_day"]:
            break
        # Rows of the previous day come later in reverse order; the first one
        # seen is its last minute, so it already holds the close of that day.
    quotes = latest or {}
    if previous:
        quotes.update(previous)
    return quotes


def first_close(path: str):
    """Close of the first stored row of one file; None when it is unusable."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        handle.readline()                                # header line
        for line in handle:
            values = numbers(line.split(","))
            if values is not None:
                return round(values[3], PRICE_DIGITS)
    return None


def count_rows(path: str) -> int:
    """Number of stored data rows of one CSV (the header line is not counted).

    Counted as raw bytes, which is much cheaper than parsing every row: the
    dashboard needs the count, not the values.
    """
    if not os.path.exists(path):
        return 0
    rows = 0
    with open(path, "rb") as handle:
        for _line in handle:
            rows += 1
    return max(0, rows - 1)
