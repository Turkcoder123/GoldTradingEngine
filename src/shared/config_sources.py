"""Registries of the market context sources (alternative data and rates).

Split out of `config.py` to keep every module small (MOD-2): these tables grow
with each source, while the layout of the data files stays in `config.py`,
which re-exports everything here so callers keep writing `config.ETF_SERIES`.
"""

from __future__ import annotations

import os

# Alternative market context sources (docs/alternative.md). Each one is a small
# daily or document series stored as CSV under <data dir>/alt: ETF gold holdings,
# the Cboe gold volatility index and Federal Reserve documents.
_ALT_SUBDIR = "alt"
ALT_TIMEOUT_SECONDS = 60.0
ALT_LIMIT_DOCUMENTS = 10          # newest Fed documents fetched per run
ETF_SERIES = {
    "gld": {
        "label": "SPDR Gold Shares",
        "source": "SPDR Gold Shares historical archive (XLSX)",
        "file": "etf_gld_daily",
    },
    "iau": {
        "label": "iShares Gold Trust",
        "source": "iShares product page (tonnes in trust)",
        "file": "etf_iau_daily",
    },
}
ETF_FIELDS = ("date", "close", "volume", "tonnes", "ounces", "nav")
VOLATILITY_SERIES = {
    "GVZ": {
        "label": "Cboe Gold ETF Volatility Index",
        "url": ("https://cdn.cboe.com/api/global/us_indices/daily_prices/"
                "GVZ_History.csv"),
        "file": "gvz_daily",
    },
}
VOLATILITY_FIELDS = ("date", "close")
FED_FEEDS = {
    "speeches": "https://www.federalreserve.gov/feeds/speeches.xml",
    "press_monetary": "https://www.federalreserve.gov/feeds/press_monetary.xml",
}
FED_FIELDS = ("date", "kind", "title", "speaker", "url", "chars")
SPDR_ARCHIVE_URL = ("https://api.spdrgoldshares.com/api/v1/historical-archive"
                    "?product=gld&exchange=NYSE&lang=en")
ISHARES_IAU_URL = "https://www.ishares.com/us/products/239561/ishares-gold-trust-fund"


def alt_dir(data_dir: str) -> str:
    """Where the alternative series live: <data dir>/alt."""
    return os.path.join(data_dir, _ALT_SUBDIR)


# Real interest rates derived from FRED (docs/rates.md): the long-term
# government yield of a country minus its consumer price inflation, both in
# percent, joined on the month (Fisher approximation). Series ids follow the
# OECD naming that FRED republishes; an id that does not resolve fails loudly.
_RATES_SUBDIR = "rates"
RATES_COUNTRIES = {
    # cpi_index: a CPI level series, the inflation rate is computed as the year
    # over year change. The OECD growth series (CPALTT01...M659N) are no longer
    # updated for most countries, so only the index based path stays current.
    "US": {"label": "United States", "yield": "IRLTLT01USM156N",
           "cpi_index": "CPIAUCSL"},
    "DE": {"label": "Germany", "yield": "IRLTLT01DEM156N",
           "cpi_index": "CP0000DEM086NEST"},
    "FR": {"label": "France", "yield": "IRLTLT01FRM156N",
           "cpi_index": "CP0000FRM086NEST"},
    "IT": {"label": "Italy", "yield": "IRLTLT01ITM156N",
           "cpi_index": "CP0000ITM086NEST"},
    "GB": {"label": "United Kingdom", "yield": "IRLTLT01GBM156N",
           "cpi_index": "GBRCPIALLMINMEI"},
}
# Not registered, with the reason a test run showed:
# * JP: every Japan CPI series on FRED stops in 2021, far too old to be useful.
# * TR: FRED has no OECD long term rate (IRLTLT01TRM156N answers HTTP 400).
RATES_STALE_MONTHS = 6
RATES_FIELDS = ("date", "real")
RATES_YEAR_DAYS = 365


def rates_dir(data_dir: str) -> str:
    """Where the derived real rate series live: <data dir>/rates."""
    return os.path.join(data_dir, _RATES_SUBDIR)


# FRED (St. Louis Fed). The keyless CSV endpoint needs no API key; when
# $FRED_API_KEY or secrets/fred_api_key exists, the official API is used.
# Neither the key nor the secrets folder is ever committed (GIT-6).
FRED_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY_ENV = "FRED_API_KEY"
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
# Unit and publication frequency as FRED documents them (see docs/macro.md);
# the ids must match FRED_SERIES, which a test checks.
FRED_SERIES_DETAIL = {
    "DFII10": ("percent", "daily"),
    "DGS10": ("percent", "daily"),
    "DGS2": ("percent", "daily"),
    "T10Y2Y": ("percentage points", "daily"),
    "T10YIE": ("percent", "daily"),
    "DTWEXBGS": ("index points", "daily"),
    "WALCL": ("million USD", "weekly"),
    "CPIAUCSL": ("index 1982-84=100", "monthly"),
    "FEDFUNDS": ("percent", "monthly"),
    "VIXCLS": ("index points", "daily"),
}


def fred_dir(data_dir: str) -> str:
    """Where the FRED series live: <data dir>/fred."""
    return os.path.join(data_dir, _FRED_SUBDIR)
