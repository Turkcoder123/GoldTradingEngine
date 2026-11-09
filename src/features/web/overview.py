"""Overview payload: one card per stored price series plus the totals.

A card answers the questions the CLI `--status` report answers, plus the latest
close, so the page can show every instrument without reading a whole month of
minute bars per series: only the file list and the tails are touched. The gap
counts live in the price panel, where the aggregation runs anyway.
"""

from __future__ import annotations

import os

from ...core import csvfile, quotes
from ...shared import config, timeutil
from . import alt_view, cot_view, fred_view, price_view, rates_view

_MB = 1024 * 1024


def _card(data_dir: str, series) -> dict:
    """One price series as the page shows it in the overview grid."""
    card = {
        "key": series.key,
        "instrument": series.instrument,
        "files": 0,
        "size_mb": 0.0,
        "newest_file": None,
        "first_bar": None,
        "last_bar": None,
        "stale_minutes": 0,
        "last_day": None,
        "last_close": None,
        "day_change_pct": None,
        "error": None,
    }
    try:
        paths = price_view.month_paths(data_dir, series.prefix)
        if not paths:
            return card
        first_ms = csvfile.oldest_ms(paths)
        last_ms = csvfile.newest_ms(paths)
        latest = quotes.tail_quotes(paths[-1])
        card.update({
            "files": len(paths),
            "size_mb": round(sum(os.path.getsize(path) for path in paths)
                             / _MB, 2),
            "newest_file": os.path.basename(paths[-1]),
            "first_bar": timeutil.ts_to_text(first_ms) if first_ms else None,
            "last_bar": timeutil.ts_to_text(last_ms) if last_ms else None,
            "stale_minutes": _stale_minutes(last_ms),
            "last_day": latest.get("last_day"),
            "last_close": latest.get("last_close"),
            "day_change_pct": _change(latest),
        })
    except OSError as exc:
        card["error"] = str(exc)
    return card


def _stale_minutes(last_ms: int) -> int:
    """Age of the newest stored bar in minutes (0 when nothing is stored)."""
    if not last_ms:
        return 0
    age = timeutil.utc_now() - timeutil.epoch_to_minute(last_ms)
    return max(0, int(age.total_seconds() // 60))


def _change(quotes_by_day: dict):
    """Percent change between the last two stored closes, or None."""
    previous = quotes_by_day.get("previous_close")
    if not previous:
        return None
    return round((quotes_by_day["last_close"] - previous) / previous * 100, 2)


def _totals(cards: list) -> dict:
    """Aggregate figures of the stored price files."""
    first_bars = [card["first_bar"] for card in cards if card["first_bar"]]
    last_bars = [card["last_bar"] for card in cards if card["last_bar"]]
    return {
        "series": len([card for card in cards if card["files"]]),
        "files": sum(card["files"] for card in cards),
        "size_mb": round(sum(card["size_mb"] for card in cards), 2),
        "first_bar": min(first_bars) if first_bars else None,
        "last_bar": max(last_bars) if last_bars else None,
    }


def payload(data_dir: str) -> dict:
    """Every price series as a card, plus the totals and the macro snapshots."""
    cards = [_card(data_dir, series) for series in config.SERIES.values()]
    return {
        "data_dir": data_dir,
        "series": cards,
        "totals": _totals(cards),
        "cot": cot_view.summary(data_dir),
        "macro": fred_view.summary(data_dir),
        "alt": alt_view.payload(data_dir),
        "rates": rates_view.payload(data_dir),
    }
