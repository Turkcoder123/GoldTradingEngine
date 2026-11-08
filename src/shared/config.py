"""Constants, paths and environment lookups shared by every module (CODE-7)."""

from __future__ import annotations

import os
from dataclasses import dataclass

_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_DIR = os.path.dirname(_PACKAGE_DIR)

# Data file layout: one CSV per calendar month, one header line, CRLF endings.
COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
HEADER = ",".join(COLUMNS)
ENCODING = "utf-8"
NEWLINE = "\r\n"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_WIDTH = 19
_MONTH_FORMAT = "%Y-%m"
_MONTH_GLOB = "[0-9][0-9][0-9][0-9]-[0-9][0-9]"
MINUTE_MS = 60_000


@dataclass(frozen=True)
class Series:
    """One price series: the Dukascopy instrument and its file prefix."""

    key: str
    instrument: str

    @property
    def prefix(self) -> str:
        """File prefix; keeps every series in its own files."""
        return f"{self.key}_1m"


SERIES = {
    "xauusd": Series("xauusd", "XAU/USD"),
    "xagusd": Series("xagusd", "XAG/USD"),
    "xaueur": Series("xaueur", "XAU/EUR"),
    "xaugbp": Series("xaugbp", "XAU/GBP"),
    "xauchf": Series("xauchf", "XAU/CHF"),
    "xauaud": Series("xauaud", "XAU/AUD"),
    "xaujpy": Series("xaujpy", "XAU/JPY"),
    "dxy": Series("dxy", "DOLLAR.IDX/USD"),
}
DEFAULT_SERIES = "xauusd"
PREFIX = SERIES[DEFAULT_SERIES].prefix

# Offer side; the default side keeps the plain file name, the ask side gets a
# suffix so two different price series can never be mixed in one file.
SIDE_BID = "B"
SIDE_ASK = "A"
SIDES = (SIDE_BID, SIDE_ASK)
DEFAULT_SIDE = SIDE_BID
_SIDE_SUFFIX = {SIDE_BID: "", SIDE_ASK: "ask_"}

DATA_DIR_ENV = "XAUUSD_DATA_DIR"
LOCK_DIR_ENV = "XAUUSD_LOCK_DIR"
LOCK_NAME = "xauusd-fetch.lock"
DEFAULT_DATA_DIR = os.path.join(_PROJECT_DIR, "xauusd_data")
VERSION_FILE = os.path.join(_PROJECT_DIR, "VERSION")

# Dukascopy free web service (no key, no signup).
BASE_URL = "https://freeserv.dukascopy.com/2.0/index.php"
INSTRUMENT = SERIES[DEFAULT_SERIES].instrument
INTERVAL = "1MIN"
PAGE_LIMIT = 30_000
PAGE_PAUSE_SECONDS = 0.25
JSONP_PREFIX = "_callbacks____"
JSONP_LENGTH = 9
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Host": "freeserv.dukascopy.com",
    "Referer": "https://freeserv.dukascopy.com/2.0/?path=chart/index",
}

# CFTC Commitments of Traders (weekly positioning report, published on Friday
# for the preceding Tuesday). The archives are yearly and keep every market.
COT_BASE_URL = "https://www.cftc.gov/files/dea/history/{name}.zip"
COT_ARCHIVES = {
    "legacy": "deacot{year}",
    "disagg": "fut_disagg_txt_{year}",
}
COT_MARKET_COLUMNS = {
    "legacy": "Market and Exchange Names",
    "disagg": "Market_and_Exchange_Names",
}
COT_GOLD_MARKET = "GOLD - COMMODITY EXCHANGE INC."
_COT_SUBDIR = "cot"
COT_TIMEOUT_SECONDS = 120.0

# FRED (St. Louis Fed). The keyless CSV endpoint needs no API key; when
# $FRED_API_KEY or secrets/fred_api_key exists, the official API is used.
# Neither the key nor the secrets folder is ever committed (GIT-6).
FRED_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY_ENV = "FRED_API_KEY"
FRED_API_KEY_FILE = os.path.join(_PROJECT_DIR, "secrets", "fred_api_key")
_FRED_SUBDIR = "fred"
FRED_TIMEOUT_SECONDS = 60.0
FRED_RETRIES = 3
FRED_RETRY_BACKOFF_SECONDS = 4
FRED_PAUSE_SECONDS = 1.0
FRED_SERIES = {
    "DFII10": "10-year TIPS real yield",
    "DGS10": "10-year Treasury yield",
    "DGS2": "2-year Treasury yield",
    "T10Y2Y": "10-year minus 2-year spread",
    "T10YIE": "10-year breakeven inflation",
    "DTWEXBGS": "broad trade-weighted dollar index",
    "WALCL": "Fed total assets",
    "CPIAUCSL": "consumer price index",
    "FEDFUNDS": "effective federal funds rate",
    "VIXCLS": "CBOE volatility index",
}

# Run defaults, all overridable from the command line.
DEFAULT_SEGMENT_HOURS = 24
DEFAULT_SEGMENTS = 8
DEFAULT_INTERVAL_MINUTES = 15.0
MIN_INTERVAL_MINUTES = 0.5
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2
RETRY_BACKOFF_CAP_SECONDS = 30
DEFAULT_EMPTY_ALLOWANCE_HOURS = 72
BOOTSTRAP_DAYS = 365
TAIL_BYTES = 8192


def resolve_data_dir(value: str | None = None) -> str:
    """--data-dir > $XAUUSD_DATA_DIR > <project>/xauusd_data."""
    return os.path.abspath(
        value or os.environ.get(DATA_DIR_ENV) or DEFAULT_DATA_DIR)


def lock_path(data_dir: str, value: str | None = None) -> str:
    """--lock-dir > $XAUUSD_LOCK_DIR > the data directory itself."""
    base = value or os.environ.get(LOCK_DIR_ENV) or data_dir
    return os.path.join(os.path.abspath(base), LOCK_NAME)


def normalize_side(value: str) -> str:
    """'b', 'BID' -> 'B'; 'a', 'ASK' -> 'A'. Raises ValueError otherwise."""
    aliases = {"B": SIDE_BID, "BID": SIDE_BID, "A": SIDE_ASK, "ASK": SIDE_ASK}
    text = str(value).strip().upper()
    if text not in aliases:
        raise ValueError(f"unknown offer side {value!r}, expected B or A")
    return aliases[text]


def resolve_series(value: str | None = None) -> Series:
    """Series by key; the default series when nothing is given."""
    key = (value or DEFAULT_SERIES).strip().lower()
    if key not in SERIES:
        raise ValueError(f"unknown series {value!r}, expected one of "
                         f"{', '.join(sorted(SERIES))}")
    return SERIES[key]


def month_path(data_dir: str, when, side: str = DEFAULT_SIDE,
               prefix: str = PREFIX) -> str:
    """Path of the monthly CSV a bar of `when` belongs to."""
    suffix = _SIDE_SUFFIX[side]
    return os.path.join(
        data_dir, f"{prefix}_{suffix}{when.strftime(_MONTH_FORMAT)}.csv")


def data_file_pattern(data_dir: str, side: str = DEFAULT_SIDE,
                      prefix: str = PREFIX) -> str:
    """Glob that matches the monthly files of exactly one offer side."""
    suffix = _SIDE_SUFFIX[side]
    return os.path.join(data_dir, f"{prefix}_{suffix}{_MONTH_GLOB}.csv")


def cot_dir(data_dir: str) -> str:
    """Where the COT exports live: <data dir>/cot."""
    return os.path.join(data_dir, _COT_SUBDIR)


def fred_dir(data_dir: str) -> str:
    """Where the FRED series live: <data dir>/fred."""
    return os.path.join(data_dir, _FRED_SUBDIR)
