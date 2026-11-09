"""Gold ETF sources: the SPDR archive (XLSX), Yahoo prices and iShares tonnage.

Everything is parsed from bytes with the standard library, so the repository
keeps its "no third-party dependency" promise (OPEN-2): the XLSX reader walks
`xl/sharedStrings.xml` and the sheet XML, nothing more.
"""

from __future__ import annotations

import datetime as dt
import html
import io
import re
import zipfile

from ..shared import config
from .altfeed import AltError, download

_CELL = re.compile(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<v>([^<]*)</v>)?')
_TAG = re.compile(r"<[^>]+>")
_SHEET_FILE = re.compile(r"xl/worksheets/sheet\d+\.xml$")
_TONNES = re.compile(r'"tonnes":\{[^}]*?"formattedValue":"([\d.,]+)"'
                     r'[^}]*?"formattedAsOfDate":"([^"]+)"')
_OUNCES = re.compile(r'"ounces":\{[^}]*?"formattedValue":"([\d.,]+)"'
                     r'[^}]*?"formattedAsOfDate":"([^"]+)"')

# Column titles of the SPDR archive as they are written in the sheet.
_SPDR_COLUMNS = {
    "close": ("Closing Price", 2),
    "volume": ("Daily Share Volume", 0),
    "tonnes": ("Tonnes of Gold", 2),
    "ounces": ("Total Ounces of Gold in the Trust", 2),
    "nav": ("Total Net Asset Value in the Trust", 2),
}


def fetch_gld() -> list:
    """Daily GLD rows of the official SPDR archive (full history)."""
    return parse_spdr(download(config.SPDR_ARCHIVE_URL))


def fetch_iau_tonnes() -> dict:
    """Latest IAU tonnage snapshot of the iShares product page."""
    return parse_ishares(download(config.ISHARES_IAU_URL))


def parse_spdr(payload: bytes) -> list:
    """Daily rows of the SPDR XLSX archive, oldest first."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            shared = _shared_strings(archive)
            rows = _sheet_rows(archive, _archive_sheet(archive), shared)
    except (zipfile.BadZipFile, KeyError, EOFError) as exc:
        raise AltError(f"unreadable SPDR archive: {exc}") from exc
    header_index = next((index for index, row in enumerate(rows)
                         if "Date" in row.values()), None)
    if header_index is None:
        raise AltError("SPDR archive has no header row")
    columns = {name: column for column, name in rows[header_index].items()}
    parsed = []
    for row in rows[header_index + 1:]:
        date = _date(row.get(columns.get("Date", ""), ""), "%d-%b-%Y")
        if not date:
            continue
        record = {"date": date}
        for field, (title, digits) in _SPDR_COLUMNS.items():
            record[field] = _number(row.get(columns.get(title, ""), ""), digits)
        parsed.append(record)
    if not parsed:
        raise AltError("SPDR archive holds no data rows")
    return parsed


def parse_ishares(payload: bytes) -> dict:
    """Latest IAU tonnage snapshot read from the product page JSON."""
    text = html.unescape(payload.decode("utf-8", "replace"))
    tonnes = _TONNES.search(text)
    if tonnes is None:
        raise AltError("iShares page holds no tonnage figure")
    ounces = _OUNCES.search(text)
    return {
        "date": _date(tonnes.group(2), "%b %d, %Y"),
        "tonnes": tonnes.group(1).replace(",", ""),
        "ounces": ounces.group(1).replace(",", "") if ounces else "",
    }


def _shared_strings(archive) -> list:
    """The workbook's text table, one entry per <si> element."""
    raw = archive.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    return [html.unescape(_TAG.sub("", item))
            for item in re.findall(r"<si>(.*?)</si>", raw, re.S)]


def _archive_sheet(archive) -> str:
    """Worksheet file that holds the data; the last sheet when unnamed."""
    workbook = archive.read("xl/workbook.xml").decode("utf-8", "replace")
    names = re.findall(r'<sheet name="([^"]+)"', workbook)
    sheets = sorted(name for name in archive.namelist()
                    if _SHEET_FILE.match(name))
    for index, name in enumerate(names):
        if "archive" in name.lower() and index < len(sheets):
            return sheets[index]
    if not sheets:
        raise AltError("archive holds no worksheet")
    return sheets[-1]


def _sheet_rows(archive, sheet: str, shared: list) -> list:
    """Cells of one worksheet as {column letter: text}, empty cells dropped."""
    xml = archive.read(sheet).decode("utf-8", "replace")
    rows = []
    for raw in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
        cells = {}
        for column, attributes, value in _CELL.findall(raw):
            if value is None:
                continue
            cells[column] = (shared[int(value)]
                             if 't="s"' in attributes else html.unescape(value))
        if cells:
            rows.append(cells)
    return rows


def _date(text: str, pattern: str) -> str:
    """Date cell in ISO form; empty when the cell is unreadable."""
    try:
        return dt.datetime.strptime(text.strip(), pattern).date().isoformat()
    except ValueError:
        return ""


def _number(text: str, digits: int) -> str:
    """Numeric cell rounded to `digits`; empty when the cell is not a number."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return ""
    if digits == 0:
        return str(int(round(value)))
    return f"{round(value, digits):.{digits}f}"
