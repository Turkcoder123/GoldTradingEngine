"""Write side of the monthly CSVs: the only module that writes data files.

Files are append-only, so a retry can never duplicate a minute. A row that is
not newer than the newest stored minute is refused and reported back to the
caller (late / duplicate counters) instead of being dropped silently (CODE-3).
Only format problems raise StorageError; IO errors propagate as OSError so the
run can report them instead of pretending the data is safe.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass

from ..shared import config, timeutil
from . import csvfile


class StorageError(RuntimeError):
    """Raised when an existing file does not hold the expected CSV layout."""


@dataclass(frozen=True)
class AppendResult:
    """What one append actually did, so nothing is dropped silently."""

    added: int = 0
    duplicates: int = 0
    late: int = 0
    newest: int = 0
    files: tuple = ()

    def merge(self, other: "AppendResult") -> "AppendResult":
        """Combine two results (several monthly files can be touched)."""
        return AppendResult(
            added=self.added + other.added,
            duplicates=self.duplicates + other.duplicates,
            late=self.late + other.late,
            newest=max(self.newest, other.newest),
            files=tuple(sorted(set(self.files) | set(other.files))),
        )


def write_rows(path: str, rows, append: bool = True) -> int:
    """Writes rows as 'timestamp,open,high,low,close,volume' (CRLF)."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    mode = "a" if (append and exists) else "w"
    written = 0
    with open(path, mode, newline="", encoding=config.ENCODING) as handle:
        writer = csv.writer(handle, lineterminator=config.NEWLINE)
        if mode == "w":
            writer.writerow(config.COLUMNS)
        for row in rows:
            stamp = timeutil.ts_to_text(int(row[0]))
            writer.writerow([stamp, *list(row[1:6])])
            written += 1
    return written


def _group_by_month(data_dir: str, side: str, prefix: str, rows) -> dict:
    """Split rows into {monthly path: rows} so one call can cross a month."""
    grouped: dict = {}
    for row in rows:
        when = timeutil.epoch_to_minute(int(row[0]))
        path = config.month_path(data_dir, when, side, prefix)
        grouped.setdefault(path, []).append(row)
    return grouped


def _select_new(month_rows, floor_ms: int) -> tuple:
    """Rows strictly newer than `floor_ms`, sorted, deduplicated per minute."""
    accepted, duplicates, late = [], 0, 0
    seen: set = set()
    for row in sorted(month_rows, key=lambda item: int(item[0])):
        stamp = int(row[0])
        if stamp in seen:
            duplicates += 1
        elif stamp <= floor_ms:
            late += 1
        else:
            seen.add(stamp)
            accepted.append(row)
    return accepted, duplicates, late


def append_rows(data_dir: str, rows, side: str = config.DEFAULT_SIDE,
                prefix: str = config.PREFIX) -> AppendResult:
    """Appends rows to their monthly CSV: format checked, deduplicated."""
    result = AppendResult()
    for path, month_rows in _group_by_month(data_dir, side, prefix,
                                            rows).items():
        exists = os.path.exists(path) and os.path.getsize(path) > 0
        if exists and not csvfile.header_ok(path):
            raise StorageError(
                f"unexpected header in {path} (expected '{config.HEADER}')")
        if exists:
            csvfile.ensure_clean_tail(path)
        floor = csvfile.tail_last_ms(path) if exists else 0
        accepted, duplicates, late = _select_new(month_rows, floor)
        added = write_rows(path, accepted, append=exists) if accepted else 0
        result = result.merge(AppendResult(
            added=added,
            duplicates=duplicates,
            late=late,
            newest=int(accepted[-1][0]) if accepted else 0,
            files=(os.path.basename(path),) if added else (),
        ))
    return result
