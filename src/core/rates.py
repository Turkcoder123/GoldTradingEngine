"""Real interest rates derived from the stored FRED series.

`real = long term government yield - consumer price inflation`, both in percent
and joined on the month, which is the Fisher approximation of an ex-post real
rate. The yields and the inflation rates come from FRED through the existing
macro downloader (`core/fred.py`), so this module only joins, stores and
summarises: nothing here touches the network.
"""

from __future__ import annotations

import datetime as dt
import os
import statistics
from dataclasses import dataclass, field

from ..shared import config, timeutil
from . import altstore, fred, fred_feed


@dataclass(frozen=True)
class RatesResult:
    """What one update stored, so the CLI can report it (CODE-3)."""

    countries: dict = field(default_factory=dict)
    warnings: tuple = ()
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when every requested country was written without an error."""
        return self.error is None


def series_ids(country: str) -> tuple:
    """(yield id, inflation id) of one country."""
    entry = config.RATES_COUNTRIES[country]
    return entry["yield"], entry.get("cpi") or entry["cpi_index"]


def real_path(data_dir: str, country: str) -> str:
    """File of one derived real rate series."""
    return os.path.join(config.rates_dir(data_dir), f"real_{country.lower()}.csv")


def _monthly(points: list) -> dict:
    """Last value of every month, keyed by 'YYYY-MM'."""
    months = {}
    for date, value in points:
        months[date[:7]] = value
    return months


def _year_over_year(months: dict) -> dict:
    """Inflation in percent per month from a CPI level series."""
    rates_by_month = {}
    for month, value in months.items():
        year, number = month.split("-")
        before = months.get(f"{int(year) - 1:04d}-{number}")
        if before:
            rates_by_month[month] = (value / before - 1) * 100
    return rates_by_month


def build_series(data_dir: str, country: str) -> list:
    """Monthly real rate rows of one country, oldest first.

    A country whose yield or inflation series is not stored yet yields nothing,
    which the caller reports as a warning instead of failing the whole run.
    """
    entry = config.RATES_COUNTRIES[country]
    yield_path, inflation_path = [fred.series_path(data_dir, series_id)
                                  for series_id in series_ids(country)]
    if not (os.path.exists(yield_path) and os.path.exists(inflation_path)):
        return []
    yields = _monthly(fred_feed.numeric_points(fred.read_stored(yield_path)))
    inflation = _monthly(fred_feed.numeric_points(
        fred.read_stored(inflation_path)))
    if "cpi_index" in entry:
        inflation = _year_over_year(inflation)
    rows = []
    for month in sorted(set(yields) & set(inflation)):
        rows.append({"date": f"{month}-01",
                     "real": f"{yields[month] - inflation[month]:.3f}"})
    return rows


def _change_1y(rows: list):
    """Change against the value about a year before the last row."""
    if len(rows) < 2:
        return None
    last = dt.date.fromisoformat(rows[-1]["date"])
    cutoff = (last - dt.timedelta(days=config.RATES_YEAR_DAYS)).isoformat()
    base = None
    for row in rows:
        if row["date"] <= cutoff:
            base = row["real"]
    if base is None:
        return None
    try:
        return round(float(rows[-1]["real"]) - float(base), 3)
    except (TypeError, ValueError):
        return None


def _is_stale(last_date) -> bool:
    """True when the newest month is older than the configured allowance."""
    if not last_date:
        return False
    last = dt.date.fromisoformat(last_date)
    age_days = (timeutil.utc_now().date() - last).days
    return age_days > config.RATES_STALE_MONTHS * 30


def _median_points(data_dir: str) -> list:
    """Monthly median real rate across the countries that share a month."""
    months = {}
    for country in config.RATES_COUNTRIES:
        for row in altstore.read_rows(real_path(data_dir, country)):
            try:
                months.setdefault(row["date"], []).append(float(row["real"]))
            except (TypeError, ValueError):
                continue
    return [[date, round(statistics.median(values), 3)]
            for date, values in sorted(months.items())]


def status(data_dir: str) -> dict:
    """Per country summary plus the equal weighted median across countries.

    The median is a plain "what is the typical real rate" figure: it is not
    GDP weighted, which the report says out loud (CODE-8).
    """
    countries = {}
    for country, entry in config.RATES_COUNTRIES.items():
        rows = altstore.read_rows(real_path(data_dir, country))
        described = altstore.describe(rows, "real")
        described["label"] = entry["label"]
        described["change_1y"] = _change_1y(rows)
        described["stale"] = _is_stale(described["last_date"])
        countries[country] = described
    points = _median_points(data_dir)
    values = [item["latest"] for item in countries.values()
              if item["latest"] is not None]
    world = {
        "median": points[-1][1] if points else None,
        "date": points[-1][0] if points else None,
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "points": points,
    }
    return {"countries": countries, "world": world}

def update_rates(data_dir: str, countries=None,
                 refresh: bool = True) -> RatesResult:
    """Downloads the needed FRED series, then rebuilds the derived files.

    The download runs per country, so one unavailable series id is reported as
    a warning and never blocks the other countries (the warning names the id).
    """
    wanted = list(countries or config.RATES_COUNTRIES)
    stored = {}
    warnings = []
    for country in wanted:
        if refresh:
            downloaded = fred.update_fred(data_dir, list(series_ids(country)))
            if not downloaded.ok:
                warnings.append(f"{country}: {downloaded.error}")
                continue
        rows = build_series(data_dir, country)
        if not rows:
            warnings.append(f"{country}: no overlapping months stored")
            continue
        try:
            altstore.write_rows(real_path(data_dir, country), rows,
                                config.RATES_FIELDS)
        except OSError as exc:
            return RatesResult(countries=stored, warnings=tuple(warnings),
                               error=f"{country}: cannot write: {exc}")
        stored[country] = dict(altstore.describe(rows, "real"),
                               label=config.RATES_COUNTRIES[country]["label"],
                               change_1y=_change_1y(rows),
                               stale=_is_stale(rows[-1]["date"]))
    return RatesResult(countries=stored, warnings=tuple(warnings))
