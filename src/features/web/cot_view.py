"""COT payload: the stored weekly positioning as chart series.

The stored CSV files are the single source (no network, no recomputation of the
CFTC columns here); the report meaning and column dictionary live in
`docs/cot.md`, the download in `core/cot.py`.
"""

from __future__ import annotations

import os

from ...core import cot, cot_feed, cotstore

DEFAULT_REPORT_ORDER = ("legacy", "disagg")


def _column(rows: list, name: str) -> list:
    """One numeric column as a list; an unreadable cell becomes null."""
    values = []
    for row in rows:
        try:
            values.append(int(row.get(name, "")))
        except (TypeError, ValueError):
            values.append(None)
    return values


def _report_payload(rows: list, report: str) -> dict:
    """Chart series and the stored summary of one report."""
    long_key, short_key = cot_feed.NET_KEYS[report]
    summary = cot.summarize(rows, long_key, short_key)
    return {
        "dates": [row.get("date") for row in rows],
        "net": _column(rows, "net"),
        "open_interest": _column(rows, "open_interest"),
        "long": _column(rows, long_key),
        "short": _column(rows, short_key),
        "summary": summary.to_dict(),
    }


def payload(data_dir: str, year: int | None = None) -> dict:
    """Every stored report of one year, plus which years exist."""
    years = cotstore.stored_years(data_dir)
    chosen = year if year is not None else (years[0] if years else None)
    reports = {}
    if chosen is not None:
        for report in DEFAULT_REPORT_ORDER:
            path = cotstore.report_path(data_dir, report, chosen)
            if not os.path.exists(path):
                continue
            reports[report] = _report_payload(cot.read_stored(path), report)
    return {"year": chosen, "years": years, "reports": reports}


def summary(data_dir: str) -> dict:
    """Year, stored years and the latest summary per report (no chart series)."""
    body = payload(data_dir)
    return {
        "year": body["year"],
        "years": body["years"],
        "reports": {report: data["summary"]
                    for report, data in body["reports"].items()},
    }
