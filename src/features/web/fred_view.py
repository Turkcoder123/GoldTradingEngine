"""FRED payload: the stored macro series, sliced for the dashboard charts.

The stored file keeps the full history (DGS10 reaches back to 1962), which is
not useful in a browser; the payload carries a display window plus the same
summary the CLI reports (`features/cli/fred_app.py`).
"""

from __future__ import annotations

import datetime as dt
import os

from ...core import fred, fred_feed
from ...shared import config

DEFAULT_YEARS = 2


def _path(data_dir: str, series_id: str) -> str:
    """Path of one stored series."""
    return fred.series_path(data_dir, series_id)


def _window(points: list, years: int) -> list:
    """Observations of the last `years` years; 0 keeps the whole history."""
    if years <= 0 or not points:
        return [[when, value] for when, value in points]
    last = dt.date.fromisoformat(points[-1][0])
    cutoff = (last - dt.timedelta(days=int(years * 365.25))).isoformat()
    return [[when, value] for when, value in points if when >= cutoff]


def _describe(data_dir: str, series_id: str) -> tuple:
    """Stored rows and summary of one series; (None, None) when unreadable."""
    rows = fred.read_stored(_path(data_dir, series_id))
    return rows, fred.summarize(series_id, rows)


def payload(data_dir: str, years: int = DEFAULT_YEARS) -> dict:
    """Every stored series with its summary and the chart window."""
    series = []
    for series_id in config.FRED_SERIES:
        if not os.path.exists(_path(data_dir, series_id)):
            continue
        rows, summary = _describe(data_dir, series_id)
        series.append({
            "id": series_id,
            "label": config.FRED_SERIES[series_id],
            "points": _window(fred_feed.numeric_points(rows), years),
            "summary": summary.to_dict(),
        })
    return {"years": years, "series": series}


def summary(data_dir: str) -> list:
    """Latest observation per stored series, without the chart points."""
    result = []
    for series_id in config.FRED_SERIES:
        if not os.path.exists(_path(data_dir, series_id)):
            continue
        _rows, summary = _describe(data_dir, series_id)
        entry = summary.to_dict()
        entry["id"] = entry.pop("series_id")
        entry["label"] = config.FRED_SERIES[series_id]
        result.append(entry)
    return result
