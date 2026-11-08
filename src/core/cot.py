"""CFTC Commitments of Traders: keeps the gold positioning as CSV files.

Selecting, summarizing and storing only; the archive access lives in
`core/cot_feed.py` (the single network module of the COT feature). Nothing here
prints: the CLI in `features/cli/cot_app.py` reports the result.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

from ..shared import config
from .cot_feed import (CotError, NET_KEYS, REPORTS, check_columns, download,
                       read_rows)

_TREND_WEEKS = 6


@dataclass(frozen=True)
class CotResult:
    """What one update stored, so the CLI can report it (CODE-3)."""

    year: int
    files: tuple = ()
    counts: dict = field(default_factory=dict)
    latest: str | None = None
    summaries: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when every report was written without an error."""
        return self.error is None


@dataclass(frozen=True)
class CotSummary:
    """The three numbers that make a COT report readable at a glance."""

    date: str | None = None
    open_interest: int = 0
    long_positions: int = 0
    short_positions: int = 0
    net: int = 0
    weekly_change: int = 0
    trend_change: int = 0
    trend_weeks: int = 0

    @property
    def net_share(self) -> float:
        """Net position as a share of open interest (0.0 when unknown)."""
        if not self.open_interest:
            return 0.0
        return self.net / self.open_interest

    def to_dict(self) -> dict:
        """Plain dict for --json, including the derived share."""
        payload = dict(self.__dict__)
        payload["net_share"] = round(self.net_share, 4)
        return payload


def select_gold(rows: list, market_column: str, columns: dict,
                exact: str | None = config.COT_GOLD_MARKET) -> list:
    """Picks the wanted columns of the gold rows, oldest report first."""
    picked = []
    for row in rows:
        market = (row.get(market_column) or "").strip()
        if exact is not None:
            if market != exact:
                continue
        elif "GOLD" not in market.upper():
            continue
        record = {"market": market}
        record.update({key: (row.get(source) or "").strip()
                       for key, source in columns.items()})
        picked.append(record)
    picked.sort(key=lambda item: (item["date"], item["market"]))
    return picked


def add_net(rows: list, long_key: str, short_key: str) -> None:
    """Adds a net position column in place (long minus short)."""
    for row in rows:
        try:
            row["net"] = str(int(row[long_key]) - int(row[short_key]))
        except (KeyError, ValueError):
            row["net"] = ""


def _net_of(row: dict, long_key: str, short_key: str) -> int | None:
    """Long minus short of one row; None when the row is unusable."""
    try:
        return int(row[long_key]) - int(row[short_key])
    except (KeyError, ValueError):
        return None



def summarize(rows: list, long_key: str, short_key: str,
              weeks: int = _TREND_WEEKS) -> CotSummary:
    """Latest positioning plus its weekly and multi-week change."""
    if not rows:
        return CotSummary()
    latest = rows[-1]
    net = _net_of(latest, long_key, short_key)
    if net is None:
        return CotSummary(date=latest.get("date"))
    previous = None
    if len(rows) > 1:
        previous = _net_of(rows[-2], long_key, short_key)
    base = _net_of(rows[max(0, len(rows) - 1 - weeks)], long_key, short_key)
    try:
        open_interest = int(latest.get("open_interest") or 0)
    except ValueError:
        open_interest = 0
    return CotSummary(
        date=latest.get("date"),
        open_interest=open_interest,
        long_positions=int(latest[long_key]),
        short_positions=int(latest[short_key]),
        net=net,
        weekly_change=(net - previous) if previous is not None else 0,
        trend_change=(net - base) if base is not None else 0,
        trend_weeks=min(weeks, len(rows) - 1),
    )


def read_stored(path: str) -> list:
    """Rows of an already stored COT CSV (no network, no reformatting)."""
    with open(path, "r", encoding=config.ENCODING, newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: str, rows: list) -> int:
    """Writes dicts to CSV with a fixed column order; returns the row count."""
    if not rows:
        return 0
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding=config.ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _report_path(data_dir: str, report: str, year: int) -> str:
    """Path of one stored report for one year."""
    pattern = REPORTS[report][1]
    return os.path.join(config.cot_dir(data_dir), pattern.format(year=year))


def status(data_dir: str, year: int) -> dict:
    """Summarizes the stored COT files; missing files are simply absent."""
    reports = {}
    for report in REPORTS:
        path = _report_path(data_dir, report, year)
        if not os.path.exists(path):
            continue
        reports[report] = summarize(read_stored(path), *NET_KEYS[report])
    return reports


def update_cot(data_dir: str, year: int,
               all_gold: bool = False) -> CotResult:
    """Downloads both reports of one year and stores them under <data>/cot."""
    exact = None if all_gold else config.COT_GOLD_MARKET
    files, counts, summaries = [], {}, {}
    latest = None
    for report, (columns, _pattern) in REPORTS.items():
        try:
            payload = download(config.COT_ARCHIVES[report].format(year=year))
            rows = read_rows(payload)
            check_columns(rows, columns)
        except CotError as exc:
            return CotResult(year=year, files=tuple(files), counts=counts,
                             latest=latest, summaries=summaries,
                             error=str(exc))
        gold = select_gold(rows, config.COT_MARKET_COLUMNS[report], columns,
                           exact=exact)
        add_net(gold, *NET_KEYS[report])
        path = _report_path(data_dir, report, year)
        name = os.path.basename(path)
        counts[name] = write_csv(path, gold)
        summaries[report] = summarize(gold, *NET_KEYS[report])
        if gold:
            files.append(name)
            latest = max(filter(None, [latest, gold[-1]["date"]]))
    return CotResult(year=year, files=tuple(files), counts=counts,
                     latest=latest, summaries=summaries)
