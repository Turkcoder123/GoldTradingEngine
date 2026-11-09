"""Alternative sources payload: ETF tonnage, GVZ and the newest Fed documents.

The payload stays small on purpose: one year of tonnage, two years of the index
and the ten newest documents, while the summaries describe the whole history.
"""

from __future__ import annotations

import datetime as dt

from ...core import altstatus, altstore, etf, fedtext, gvz

ETF_POINT_DAYS = 365
VOLATILITY_POINT_DAYS = 730
DOCUMENTS = 10


def payload(data_dir: str) -> dict:
    """Everything the alternative sources panel shows."""
    return {
        "etf": _etf(data_dir),
        "volatility": _volatility(data_dir),
        "fed": _fed(data_dir),
    }


def _float(text):
    """Cell to float, or None when it is empty or unreadable."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _window(rows: list, field: str, days: int) -> list:
    """Points of the last `days` days as [date, value], oldest first."""
    points = [[row["date"], _float(row.get(field))] for row in rows
              if _float(row.get(field)) is not None]
    if not points:
        return []
    cutoff = (dt.date.fromisoformat(points[-1][0])
              - dt.timedelta(days=days)).isoformat()
    return [point for point in points if point[0] >= cutoff]


def _change(points: list):
    """Percent change between the first and the last point of a window."""
    if len(points) < 2 or not points[0][1]:
        return None
    return round((points[-1][1] - points[0][1]) / points[0][1] * 100, 2)


def _etf(data_dir: str) -> list:
    """Every stored fund with its tonnage window."""
    result = []
    for row in altstatus.etf_holdings(data_dir):
        points = _window(altstore.read_rows(etf.path(data_dir, row["key"])),
                         "tonnes", ETF_POINT_DAYS)
        result.append(dict(row, points=points, change_pct=_change(points)))
    return result


def _volatility(data_dir: str) -> dict:
    """The stored volatility index with its close window."""
    row = altstatus.volatility(data_dir)[0]
    points = _window(altstore.read_rows(gvz.path(data_dir)), "close",
                     VOLATILITY_POINT_DAYS)
    return dict(row, points=points, change_pct=_change(points))


def _fed(data_dir: str) -> dict:
    """Document counts plus the newest index rows, newest first."""
    described = altstatus.fed_documents(data_dir)
    rows = altstore.read_rows(fedtext.index_path(data_dir))[-DOCUMENTS:]
    documents = [{
        "date": row.get("date"),
        "kind": row.get("kind"),
        "title": row.get("title"),
        "speaker": row.get("speaker"),
        "chars": altstatus.number_of(row.get("chars")),
        "url": row.get("url"),
    } for row in reversed(rows)]
    return dict(described, documents=documents)
