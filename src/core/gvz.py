"""GVZ storage: keeps the Cboe gold volatility history as one CSV.

Downloading and parsing live in `gvz_feed.py`; this module owns the stored file
and the summary the CLI and the report print.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..shared import config
from . import altstore, gvz_feed
from .altfeed import AltError

_NAME = "GVZ"


@dataclass(frozen=True)
class GvzResult:
    """What one update stored, so the CLI can report it (CODE-3)."""

    file: str = ""
    rows: int = 0
    added: int = 0
    first_date: str | None = None
    last_date: str | None = None
    latest: float | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when the series was written without an error."""
        return self.error is None


def path(data_dir: str) -> str:
    """File of the stored GVZ history."""
    return altstore.series_path(data_dir, config.VOLATILITY_SERIES[_NAME]["file"])


def update_gvz(data_dir: str) -> GvzResult:
    """Downloads the Cboe history and merges it into the stored CSV."""
    target = path(data_dir)
    stored = altstore.read_rows(target)
    try:
        fresh = gvz_feed.fetch()
    except AltError as exc:
        return GvzResult(error=str(exc))
    merged = altstore.merge_series(stored, fresh, config.VOLATILITY_FIELDS)
    try:
        altstore.write_rows(target, merged, config.VOLATILITY_FIELDS)
    except OSError as exc:
        return GvzResult(error=f"cannot write {target}: {exc}")
    described = altstore.describe(merged)
    return GvzResult(
        file=target.rsplit("/", 1)[-1],
        rows=described["rows"],
        added=len(merged) - len(stored),
        first_date=described["first_date"],
        last_date=described["last_date"],
        latest=described["latest"],
    )


def status(data_dir: str) -> dict:
    """Stored history of the series, without touching the network."""
    described = altstore.describe(altstore.read_rows(path(data_dir)))
    described["file"] = path(data_dir)
    return described
