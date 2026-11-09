"""Where the exported COT rows live: one CSV per report and year (read side).

`core/cot.py` downloads and writes the exports, `core/cot_feed.py` knows the
archives; this module only answers where the stored files are, which both the
dashboard and the text report need (MOD-1).
"""

from __future__ import annotations

import os

from ..shared import config
from .cot_feed import REPORTS


def report_path(data_dir: str, report: str, year: int) -> str:
    """Path of one stored report for one year."""
    pattern = REPORTS[report][1]
    return os.path.join(config.cot_dir(data_dir), pattern.format(year=year))


def stored_years(data_dir: str) -> list:
    """Years with a stored COT file, newest first (empty when none)."""
    folder = config.cot_dir(data_dir)
    if not os.path.isdir(folder):
        return []
    years = set()
    for name in os.listdir(folder):
        if not name.endswith(".csv"):
            continue
        year = name[:-len(".csv")].rsplit("_", 1)[-1]
        if len(year) == 4 and year.isdigit():
            years.add(int(year))
    return sorted(years, reverse=True)


def newest_year(data_dir: str):
    """Newest stored year, or None when nothing is stored."""
    years = stored_years(data_dir)
    return years[0] if years else None
