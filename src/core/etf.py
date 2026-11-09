"""ETF storage: keeps the GLD and IAU daily files and their summaries.

One file per fund under <data dir>/alt; the GLD archive is a full history and the
IAU tonnage is a single snapshot per day, so both are merged by date instead of
appended (a repeated run cannot duplicate a day).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..shared import config
from . import altstore, etf_feed
from .altfeed import AltError


@dataclass(frozen=True)
class EtfResult:
    """What one update stored, so the CLI can report it (CODE-3)."""

    series: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when every requested fund was written without an error."""
        return self.error is None


def path(data_dir: str, key: str) -> str:
    """File of one stored fund."""
    return altstore.series_path(data_dir, config.ETF_SERIES[key]["file"])


def _merge(target: str, fresh: list) -> dict:
    """Merges rows into one file and describes what is stored now."""
    stored = altstore.read_rows(target)
    merged = altstore.merge_series(stored, fresh, config.ETF_FIELDS)
    altstore.write_rows(target, merged, config.ETF_FIELDS)
    described = altstore.describe(merged, "tonnes")
    described["added"] = len(merged) - len(stored)
    described["file"] = target.rsplit("/", 1)[-1]
    return described


def _fresh_rows(key: str) -> list:
    """Rows of one fund: the GLD archive or the IAU tonnage snapshot."""
    if key == "gld":
        return etf_feed.fetch_gld()
    snapshot = etf_feed.fetch_iau_tonnes()
    return [{"date": snapshot["date"], "close": "", "volume": "",
             "tonnes": snapshot["tonnes"], "ounces": snapshot["ounces"],
             "nav": ""}]


def update_etf(data_dir: str, keys=None) -> EtfResult:
    """Downloads the requested funds and merges them into the stored CSVs."""
    series = {}
    for key in list(keys or config.ETF_SERIES):
        target = path(data_dir, key)
        try:
            series[key] = _merge(target, _fresh_rows(key))
        except AltError as exc:
            return EtfResult(series=series, error=f"{key}: {exc}")
        except OSError as exc:
            return EtfResult(series=series,
                             error=f"{key}: cannot write {target}: {exc}")
    return EtfResult(series=series)


def status(data_dir: str) -> dict:
    """Stored funds with their coverage and latest tonnage, offline."""
    report = {}
    for key in config.ETF_SERIES:
        described = altstore.describe(altstore.read_rows(path(data_dir, key)),
                                      "tonnes")
        described["file"] = path(data_dir, key)
        report[key] = described
    return report
