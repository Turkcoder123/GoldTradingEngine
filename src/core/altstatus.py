"""Stored facts of the alternative sources, shared by the report and the page.

Both surfaces describe the same three sources, so the numbers are gathered here
once (MOD-1): the text report and the dashboard payload read this module instead
of duplicating the file layout.
"""

from __future__ import annotations

from ..shared import config
from . import altstore, etf, fedtext, gvz


def etf_holdings(data_dir: str) -> list:
    """One row per stored fund: coverage, stored rows and the latest tonnage."""
    stored = etf.status(data_dir)
    return [{
        "key": key,
        "label": config.ETF_SERIES[key]["label"],
        "source": config.ETF_SERIES[key]["source"],
        "rows": described["rows"],
        "first_date": described["first_date"],
        "last_date": described["last_date"],
        "tonnes": described["latest"],
    } for key, described in stored.items()]


def volatility(data_dir: str) -> list:
    """One row per stored volatility index."""
    described = gvz.status(data_dir)
    key = next(iter(config.VOLATILITY_SERIES))
    return [{
        "key": key,
        "label": config.VOLATILITY_SERIES[key]["label"],
        "rows": described["rows"],
        "first_date": described["first_date"],
        "last_date": described["last_date"],
        "close": described["latest"],
    }]


def fed_documents(data_dir: str) -> dict:
    """Stored Federal Reserve documents, counted per kind."""
    rows = altstore.read_rows(fedtext.index_path(data_dir))
    kinds = {}
    for row in rows:
        kind = row.get("kind", "-")
        kinds[kind] = kinds.get(kind, 0) + 1
    described = fedtext.status(data_dir)
    return {
        "rows": described["rows"],
        "texts": described["texts"],
        "first_date": described["first_date"],
        "last_date": described["last_date"],
        "chars": sum(number_of(row.get("chars")) for row in rows),
        "kinds": kinds,
    }


def number_of(text) -> int:
    """Cell to int, or 0 when it is empty or unreadable."""
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0
