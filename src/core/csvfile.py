"""Read side of the monthly CSVs: locate, inspect and repair stored files.

Appending lives in storage.py; keeping the byte level helpers here keeps both
modules small and single purpose (MOD-1, MOD-2).
"""

from __future__ import annotations

import glob
import os

from ..shared import config, timeutil


def month_files(data_dir: str, side: str = config.DEFAULT_SIDE,
                prefix: str = config.PREFIX) -> list:
    """Monthly CSV paths of one series and side, oldest file first."""
    return sorted(glob.glob(config.data_file_pattern(data_dir, side, prefix)))


def tail_last_ms(path: str) -> int:
    """Newest timestamp stored in one CSV, read from the file tail only."""
    if not os.path.exists(path):
        return 0
    size = os.path.getsize(path)
    if size <= 0:
        return 0
    with open(path, "rb") as handle:
        handle.seek(max(0, size - config.TAIL_BYTES))
        chunk = handle.read()
    for line in reversed([row for row in chunk.split(b"\n") if row.strip()]):
        raw = line.split(b",", 1)[0].decode("ascii", "replace")
        stamp = timeutil.text_to_ms(raw)
        if stamp:
            return stamp
    return 0


def head_first_ms(path: str) -> int:
    """Oldest timestamp stored in one CSV (header plus the first rows only)."""
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        handle.readline()                                # header line
        for line in handle:
            stamp = timeutil.text_to_ms(line.split(",", 1)[0])
            if stamp:
                return stamp
    return 0


def newest_ms(paths) -> int:
    """Newest timestamp across files; only the last file can hold it."""
    for path in reversed(list(paths)):
        stamp = tail_last_ms(path)
        if stamp:
            return stamp
    return 0


def oldest_ms(paths) -> int:
    """Oldest timestamp across files; only the first file can hold it."""
    for path in paths:
        stamp = head_first_ms(path)
        if stamp:
            return stamp
    return 0


def last_stored_ms(data_dir: str, side: str = config.DEFAULT_SIDE,
                   prefix: str = config.PREFIX) -> int:
    """Newest stored minute of one series and side (0 when there is none)."""
    return newest_ms(month_files(data_dir, side, prefix))


def header_ok(path: str) -> bool:
    """True when a file starts with the expected header (or is empty)."""
    if not os.path.exists(path):
        return True
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        return handle.readline().strip() == config.HEADER


def _last_newline_offset(handle, size: int) -> int:
    """Byte offset just after the last newline, scanning the file backwards."""
    position = size
    while position > 0:
        step = min(config.TAIL_BYTES, position)
        position -= step
        handle.seek(position)
        block = handle.read(step)
        found = block.rfind(b"\n")
        if found != -1:
            return position + found + 1
    return 0


def ensure_clean_tail(path: str) -> int:
    """Drops an unterminated last line so the next row cannot be glued to it.

    Returns the number of bytes removed (0 when the file already ends cleanly).
    """
    size = os.path.getsize(path)
    if size <= 0:
        return 0
    with open(path, "r+b") as handle:
        handle.seek(size - 1)
        if handle.read(1) == b"\n":
            return 0
        keep = _last_newline_offset(handle, size)
        handle.truncate(keep)
        return size - keep


def gap_report(path: str) -> dict:
    """Minutes without bars inside one month: count, size and largest stretch.

    Market closures (weekends and the daily 21:00-22:00 UTC break) hold no
    bars, so they are counted here as well: a non-zero result is expected on
    real gold data and does not by itself mean minutes were lost.
    """
    gaps = missing = largest = 0
    previous = 0
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        handle.readline()                                # header line
        for line in handle:
            stamp = timeutil.text_to_ms(line.split(",", 1)[0])
            if not stamp:
                continue
            if previous:
                step = int((stamp - previous) // config.MINUTE_MS)
                if step > 1:
                    gaps += 1
                    missing += step - 1
                    largest = max(largest, step - 1)
            previous = stamp
    return {"gaps": gaps, "missing_minutes": missing,
            "largest_gap_minutes": largest}
