"""SMC structures of one price window, in the shape the chart overlay expects.

The detection lives in `core/smc.py`; this module only picks the window, reuses
the daily bars the price panel already builds (same loader, same cache) and
counts the patterns for the panel. Events therefore carry the index of the bar
they belong to, which is what aligns an overlay with the candle it marks.
"""

from __future__ import annotations

from ...core import smc
from ...shared import config
from . import price_view

TIMEFRAME = "1d"


def _summary(events: list) -> dict:
    """Pattern name -> direction -> count, so the panel needs no second pass."""
    counts = {}
    for item in events:
        bucket = counts.setdefault(item["pattern"], {})
        bucket[item["direction"]] = bucket.get(item["direction"], 0) + 1
    return counts


def _window(bars: list) -> dict:
    """First and last day of the detected window plus its bar count."""
    return {
        "count": len(bars),
        "first_day": bars[0]["day"] if bars else None,
        "last_day": bars[-1]["day"] if bars else None,
    }


def payload(loader, data_dir: str, key: str, months: int) -> dict:
    """Detected structures of one series window, with their counts.

    `loader` turns one monthly file into its daily aggregate (the cache in
    `cache.py`), exactly as `price_view.payload` does, so both endpoints always
    describe the same bars.
    """
    series = config.resolve_series(key)
    paths = price_view.month_paths(data_dir, series.prefix, months)
    bars, _quality = price_view.combine([loader(path) for path in paths])
    events = smc.detect(bars)
    return {
        "key": series.key,
        "instrument": series.instrument,
        "timeframe": TIMEFRAME,
        "months_requested": months,
        "months": price_view.month_keys(paths),
        "parameters": smc.DEFAULT_PARAMS.as_dict(),
        "bars": _window(bars),
        "summary": _summary(events),
        "events": events,
    }
