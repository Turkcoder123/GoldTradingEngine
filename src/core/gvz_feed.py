"""Cboe gold volatility index (GVZ): download and parse the daily CSV.

The official endpoint returns the whole history as `DATE,GVZ` with US style
dates; nothing else is needed, so this module stays free of dependencies.
"""

from __future__ import annotations

import csv
import datetime as dt
import io

from ..shared import config
from .altfeed import download


def parse(payload: bytes) -> list:
    """Stored rows of the Cboe history, oldest first, dates in ISO form."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8", "replace")))
    rows = []
    for row in reader:
        date = _iso_date(row.get("DATE") or "")
        close = (row.get("GVZ") or "").strip()
        if date and close:
            rows.append({"date": date, "close": close})
    return rows


def fetch(payload: bytes | None = None) -> list:
    """Rows of the configured series; downloads unless a payload is given."""
    if payload is None:
        payload = download(config.VOLATILITY_SERIES["GVZ"]["url"])
    return parse(payload)


def _iso_date(text: str) -> str:
    """'11/06/2026' -> '2026-11-06'; empty when the cell is unreadable."""
    try:
        return dt.datetime.strptime(text.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return ""
