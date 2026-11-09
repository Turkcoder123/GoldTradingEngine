"""CSV storage of the alternative series: read, merge and write one file.

The alternative sources publish their full history (GVZ, the SPDR archive) or a
single snapshot (iShares tonnage), so every update merges instead of appending:
a repeated run rewrites the same rows and can never duplicate a day.
"""

from __future__ import annotations

import csv
import os

from ..shared import config


def series_path(data_dir: str, name: str) -> str:
    """Path of one stored alternative series: <data dir>/alt/<name>.csv."""
    return os.path.join(config.alt_dir(data_dir), f"{name}.csv")


def read_rows(path: str) -> list:
    """Stored rows of one file; a missing file is simply empty."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: str, rows: list, fields) -> int:
    """Writes the rows in the given field order; returns the row count."""
    if not rows:
        return 0
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding=config.ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def merge_series(stored: list, fresh: list, fields) -> list:
    """Daily rows merged on the date, oldest first; the fresh row wins."""
    merged = {row["date"]: row for row in stored if row.get("date")}
    for row in fresh:
        merged[row["date"]] = row
    return [_ordered(row, fields)
            for row in sorted(merged.values(), key=lambda row: row["date"])]


def merge_documents(stored: list, fresh: list, fields) -> list:
    """Documents merged on the url, oldest first; the fresh row wins."""
    merged = {row["url"]: row for row in stored if row.get("url")}
    for row in fresh:
        merged[row["url"]] = row
    ordered = sorted(merged.values(),
                     key=lambda row: (row.get("date", ""), row["url"]))
    return [_ordered(row, fields) for row in ordered]


def describe(rows: list, value_field: str = "close") -> dict:
    """Row count, covered dates and the latest readable value of a series."""
    if not rows:
        return {"rows": 0, "first_date": None, "last_date": None,
                "latest": None}
    latest = None
    for row in reversed(rows):
        latest = _number(row.get(value_field))
        if latest is not None:
            break
    return {
        "rows": len(rows),
        "first_date": rows[0].get("date"),
        "last_date": rows[-1].get("date"),
        "latest": latest,
    }


def _number(text):
    """Cell to float, or None when it is empty or unreadable."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _ordered(row: dict, fields) -> dict:
    """One row in the stored field order, missing cells empty."""
    return {field: row.get(field, "") for field in fields}
