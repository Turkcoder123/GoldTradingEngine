"""CFTC archive access: download, unzip, and the report schema.

The only COT module that uses the network. The column mappings live here as
well, because a mapping only means something together with the archive it
targets: the CFTC header differs between the legacy and the disaggregated
report.
"""

from __future__ import annotations

import csv
import io
import urllib.request
import zipfile

from ..shared import config

LEGACY_COLUMNS = {
    "date": "As of Date in Form YYYY-MM-DD",
    "open_interest": "Open Interest (All)",
    "noncomm_long": "Noncommercial Positions-Long (All)",
    "noncomm_short": "Noncommercial Positions-Short (All)",
    "noncomm_spread": "Noncommercial Positions-Spreading (All)",
    "traders_long": "Traders-Noncommercial-Long (All)",
    "traders_short": "Traders-Noncommercial-Short (All)",
}
DISAGG_COLUMNS = {
    "date": "Report_Date_as_YYYY-MM-DD",
    "open_interest": "Open_Interest_All",
    "managed_money_long": "M_Money_Positions_Long_All",
    "managed_money_short": "M_Money_Positions_Short_All",
    "producer_long": "Prod_Merc_Positions_Long_All",
    "producer_short": "Prod_Merc_Positions_Short_All",
    # The CFTC header really is inconsistent here: one underscore for the
    # long side, two for the short side.
    "swap_long": "Swap_Positions_Long_All",
    "swap_short": "Swap__Positions_Short_All",
}
NET_KEYS = {
    "legacy": ("noncomm_long", "noncomm_short"),
    "disagg": ("managed_money_long", "managed_money_short"),
}
REPORTS = {
    "legacy": (LEGACY_COLUMNS, "cot_legacy_gold_{year}.csv"),
    "disagg": (DISAGG_COLUMNS, "cot_disagg_gold_{year}.csv"),
}


class CotError(RuntimeError):
    """Raised when an archive cannot be downloaded or does not parse."""


def download(name: str) -> bytes:
    """Fetches one archive; the site blocks the default python user agent."""
    url = config.COT_BASE_URL.format(name=name)
    request = urllib.request.Request(
        url, headers={"User-Agent": config.REQUEST_HEADERS["User-Agent"]})
    try:
        with urllib.request.urlopen(
                request, timeout=config.COT_TIMEOUT_SECONDS) as response:
            return response.read()
    except OSError as exc:
        raise CotError(f"cannot download {url}: {exc}") from exc


def read_rows(payload: bytes) -> list:
    """Every row of one archive, keyed by the raw CFTC column names."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [name for name in archive.namelist()
                       if name.lower().endswith((".txt", ".csv"))]
            if not members:
                raise CotError("archive holds no text file")
            with archive.open(members[0]) as raw:
                text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                return list(csv.DictReader(text))
    except (zipfile.BadZipFile, EOFError) as exc:
        raise CotError(f"unreadable archive: {exc}") from exc


def check_columns(rows: list, columns: dict) -> None:
    """Raises CotError when the archive lacks a column the mapping needs.

    Without this a renamed CFTC header would silently produce empty columns.
    """
    if not rows:
        raise CotError("archive holds no rows")
    present = set(rows[0])
    missing = sorted(source for source in columns.values()
                     if source not in present)
    if missing:
        raise CotError("archive lacks column(s): " + ", ".join(missing))
