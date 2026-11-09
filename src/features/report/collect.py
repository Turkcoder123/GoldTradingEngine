"""Read-only facts of the stored data: what is there, how much, until when.

Every number comes from the CSV files the updaters wrote; this module never
downloads and never aggregates minute bars into days (the report only needs the
row count, which `core/quotes.py` counts as bytes).
"""

from __future__ import annotations

import os

from ...core import (altstatus, cot, cot_feed, cotstore, csvfile, fred,
                     fred_feed, quotes, rates)
from ...shared import config, timeutil, version

_MB = 1024 * 1024
_DAY_MS = config.MINUTE_MS * config.MINUTES_PER_DAY
_PRICE_FREQUENCY = "1 min"
_COT_FREQUENCY = "weekly"
_COT_REPORTS = ("legacy", "disagg")
_UNKNOWN = "unknown"


def _version() -> str:
    """The project version, or a readable placeholder when VERSION is broken."""
    try:
        return version.read_version()
    except version.VersionError:
        return _UNKNOWN


def _change(last, previous):
    """Percent change between two values, or None when either is missing."""
    if last is None or not previous:
        return None
    return round((last - previous) / previous * 100, 2)


def _age_minutes(last_ms: int) -> int:
    """Age of the newest stored bar in minutes (0 when nothing is stored)."""
    if not last_ms:
        return 0
    delta = timeutil.utc_now() - timeutil.epoch_to_minute(last_ms)
    return max(0, int(delta.total_seconds() // 60))


def prices(data_dir: str) -> list:
    """One row per registered price series: coverage, size, rows and quotes."""
    rows = []
    for series in config.SERIES.values():
        paths = csvfile.month_files(data_dir, config.DEFAULT_SIDE,
                                    series.prefix)
        first_ms = csvfile.oldest_ms(paths)
        last_ms = csvfile.newest_ms(paths)
        latest = quotes.tail_quotes(paths[-1]) if paths else {}
        first_close = quotes.first_close(paths[0]) if paths else None
        last_close = latest.get("last_close")
        rows.append({
            "key": series.key,
            "instrument": series.instrument,
            "frequency": _PRICE_FREQUENCY,
            "files": len(paths),
            "size_mb": round(sum(os.path.getsize(path) for path in paths)
                             / _MB, 2),
            "bars": sum(quotes.count_rows(path) for path in paths),
            "first_bar": timeutil.ts_to_text(first_ms) if first_ms else None,
            "last_bar": timeutil.ts_to_text(last_ms) if last_ms else None,
            "days": ((last_ms - first_ms) // _DAY_MS + 1
                     if first_ms and last_ms else 0),
            "first_close": first_close,
            "last_close": last_close,
            "day_change_pct": _change(last_close, latest.get("previous_close")),
            "range_change_pct": _change(last_close, first_close),
            "age_minutes": _age_minutes(last_ms),
        })
    return rows


def cot_reports(data_dir: str, year: int | None = None) -> dict:
    """The stored COT reports of one year (the newest stored year by default)."""
    years = cotstore.stored_years(data_dir)
    chosen = year if year is not None else (years[0] if years else None)
    rows = []
    if chosen is not None:
        for report in _COT_REPORTS:
            path = cotstore.report_path(data_dir, report, chosen)
            if not os.path.exists(path):
                continue
            stored = cot.read_stored(path)
            summary = cot.summarize(stored, *cot_feed.NET_KEYS[report])
            rows.append({
                "report": report,
                "frequency": _COT_FREQUENCY,
                "first_date": stored[0]["date"] if stored else None,
                "last_date": stored[-1]["date"] if stored else None,
                "reports": len(stored),
                "open_interest": summary.open_interest,
                "net": summary.net,
                "net_share": summary.net_share,
                "weekly_change": summary.weekly_change,
                "trend_change": summary.trend_change,
                "trend_weeks": summary.trend_weeks,
            })
    return {"year": chosen, "years": years, "rows": rows}


def macro(data_dir: str) -> list:
    """One row per stored FRED series: coverage, unit, frequency, last value."""
    rows = []
    for series_id, description in config.FRED_SERIES.items():
        path = fred.series_path(data_dir, series_id)
        if not os.path.exists(path):
            continue
        stored = fred.read_stored(path)
        summary = fred.summarize(series_id, stored)
        points = fred_feed.numeric_points(stored)
        unit, frequency = config.FRED_SERIES_DETAIL[series_id]
        rows.append({
            "id": series_id,
            "label": description,
            "unit": unit,
            "frequency": frequency,
            "first_date": points[0][0] if points else None,
            "last_date": points[-1][0] if points else None,
            "observations": len(points),
            "value": summary.value,
            "date": summary.date,
            "change": summary.change,
            "year_change": summary.year_change,
        })
    return rows


def totals(price_rows: list) -> dict:
    """Aggregate figures of the stored price files."""
    first_bars = [row["first_bar"] for row in price_rows if row["first_bar"]]
    last_bars = [row["last_bar"] for row in price_rows if row["last_bar"]]
    return {
        "series": len([row for row in price_rows if row["files"]]),
        "files": sum(row["files"] for row in price_rows),
        "bars": sum(row["bars"] for row in price_rows),
        "size_mb": round(sum(row["size_mb"] for row in price_rows), 2),
        "first_bar": min(first_bars) if first_bars else None,
        "last_bar": max(last_bars) if last_bars else None,
    }


def build(data_dir: str, year: int | None = None) -> dict:
    """Everything the report prints, gathered in one pass over the files."""
    price_rows = prices(data_dir)
    return {
        "version": _version(),
        "generated_at": timeutil.utc_now().strftime(config.TIMESTAMP_FORMAT),
        "data_dir": os.path.abspath(data_dir),
        "totals": totals(price_rows),
        "prices": price_rows,
        "cot": cot_reports(data_dir, year),
        "macro": macro(data_dir),
        "etf": altstatus.etf_holdings(data_dir),
        "volatility": altstatus.volatility(data_dir),
        "fed": altstatus.fed_documents(data_dir),
        "rates": rates.status(data_dir),
    }
