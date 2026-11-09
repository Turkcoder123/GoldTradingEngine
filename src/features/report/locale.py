"""English labels of the stored-data report (LANG-2, LANG-4, ASCII only)."""

from __future__ import annotations

DEFAULT_LOCALE = "en"

_EN = {
    "title": "GOLD MARKET DATA - STORED DATA REPORT",
    "generated": "generated",
    "version": "project",
    "data_dir": "data directory",
    "totals": "totals",
    "totals.value": "{series} series | {files} files | {bars} rows | {size} MB | "
                    "{first} -> {last} UTC",
    "nothing": "nothing stored yet",

    "prices.coverage.title": "PRICE SERIES - COVERAGE (1-minute bars, bid side)",
    "prices.latest.title": "PRICE SERIES - LATEST VALUES",
    "prices.series": "SERIES",
    "prices.instrument": "INSTRUMENT",
    "prices.frequency": "FREQ",
    "prices.first_bar": "FIRST BAR (UTC)",
    "prices.last_bar": "LAST BAR (UTC)",
    "prices.days": "DAYS",
    "prices.bars": "BARS",
    "prices.files": "FILES",
    "prices.size": "SIZE MB",
    "prices.last_close": "LAST CLOSE",
    "prices.day_change": "DAY %",
    "prices.range_change": "RANGE %",
    "prices.age": "AGE",

    "cot.title": "COT - CFTC COMMITMENTS OF TRADERS (weekly, COMEX gold)",
    "cot.report": "REPORT",
    "cot.frequency": "FREQ",
    "cot.first": "FIRST REPORT",
    "cot.last": "LAST REPORT",
    "cot.reports": "REPORTS",
    "cot.open_interest": "OPEN INTEREST",
    "cot.net": "NET",
    "cot.share": "NET % OI",
    "cot.week_change": "WEEK CHG",
    "cot.trend_change": "TREND CHG",
    "cot.legacy": "legacy",
    "cot.disagg": "disagg",

    "macro.title": "MACRO SERIES (FRED)",
    "macro.id": "ID",
    "macro.what": "WHAT",
    "macro.unit": "UNIT",
    "macro.frequency": "FREQ",
    "macro.first": "FIRST",
    "macro.last": "LAST",
    "macro.observations": "OBS",
    "macro.latest": "LATEST",
    "macro.change": "CHG",
    "macro.year_change": "1Y CHG",

    "common.rows": "ROWS",
    "common.first": "FIRST",
    "common.last": "LAST",

    "etf.title": "GOLD ETF HOLDINGS (tonnes in trust)",
    "etf.fund": "FUND",
    "etf.source": "SOURCE",
    "etf.tonnes": "TONNES",

    "volatility.title": "GOLD VOLATILITY INDEX",
    "volatility.index": "INDEX",
    "volatility.close": "CLOSE",

    "fed.title": "FEDERAL RESERVE DOCUMENTS",
    "fed.kind": "KIND",
    "fed.count": "COUNT",
    "fed.summary": "{rows} documents ({texts} texts, {chars} characters) "
                   "{first} -> {last}",

    "rates.title": "REAL INTEREST RATES (long term yield minus CPI inflation)",
    "rates.country": "CC",
    "rates.name": "COUNTRY",
    "rates.last": "LAST",
    "rates.latest": "LATEST",
    "rates.change": "1Y CHG",
    "rates.rows": "ROWS",
    "rates.world": "world median {median} over {count} countries "
                   "(equal weighted)",
    "rates.stale": "stale series (older than six months): {countries}",

    "notes": "NOTES",

    "empty": "-",
}

# Explanation lines printed under the tables, one per row of the report legend.
_NOTES = (
    "FREQ is the resolution of the stored rows: 1 min = one CSV row per minute.",
    "COVERAGE is the first and the last stored row; DAYS counts calendar days.",
    "BARS counts stored rows only: market closures hold no bars, so a month has "
    "about 25,000-31,000 rows, not 44,000.",
    "DAY % compares the last two stored trading days; RANGE % compares the last "
    "close with the first stored close.",
    "AGE is how old the newest stored bar is at report time (min, h, d).",
    "COT is measured on Tuesday and published on Friday: align it with prices by "
    "the publication day.",
    "NET is long minus short of the report's main group; NET % OI divides it by "
    "open interest.",
    "FRED keeps the full published history; a missing observation stays empty and "
    "is not counted as an observation.",
    "SOURCES: Dukascopy (1-minute prices), CFTC (COT), FRED / St. Louis Fed "
    "(macro series).",
    "REFRESH: python update_1m.py | python update_cot.py | python update_fred.py",
    "ALTERNATIVE: python update_alt.py (ETF gold, GVZ, Fed documents).",
    "ETF tonnage comes from the SPDR archive (GLD) and the iShares product page "
    "(IAU); the IAU row is one snapshot per run, GLD carries the full history.",
    "GVZ is the Cboe Gold ETF Volatility Index, read from the official Cboe CSV.",
    "Fed documents are listed from the Board RSS feeds; the text of every "
    "document is stored next to the index.",
    "REAL RATES: real = long term government yield - consumer price inflation, "
    "joined on the month (Fisher approximation, ex-post).",
    "The world figure is the equal weighted median of the stored countries: it "
    "is not GDP weighted.",
    "REFRESH RATES: python update_rates.py (or --offline to rebuild only).",
    "This file is generated from the stored CSVs: run python data_report.py.",
)

_RESOURCES = {DEFAULT_LOCALE: _EN}
_NOTES_BY_LOCALE = {DEFAULT_LOCALE: _NOTES}


def labels(locale: str = DEFAULT_LOCALE) -> dict:
    """Label dictionary of one locale; an unknown locale falls back to English."""
    return dict(_RESOURCES.get(locale, _EN))


def notes(locale: str = DEFAULT_LOCALE) -> tuple:
    """Explanation lines of the report legend."""
    return _NOTES_BY_LOCALE.get(locale, _NOTES)


def text(key: str, locale: str = DEFAULT_LOCALE) -> str:
    """One label; an unknown key reports the key instead of failing."""
    return labels(locale).get(key, key)
