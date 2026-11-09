"""Confirmed swing pivots of one ordered bar window.

A pivot is only known once the bars to its right have closed, which is what keeps
the caller free of look-ahead: the confirm index travels with every pivot, so an
event can carry the bar at which it became knowable.
"""

from __future__ import annotations


def _unique(window: list, field: str, value: float) -> bool:
    """True when the extreme appears exactly once inside the window."""
    return sum(1 for bar in window if bar[field] == value) == 1


def confirmed_swings(bars: list, left_bars: int = 3, right_bars: int = 3):
    """Swing highs and lows as (pivot index, confirm index, price) tuples.

    The pivot bar must hold the extreme of the whole `left_bars + right_bars + 1`
    window and it must be the only bar holding it; a flat top or bottom is not a
    pivot. Bars are the daily dictionaries of `features.web.price_view`, already
    sorted by day.
    """
    counted = len(bars)
    highs, lows = [], []
    for index in range(left_bars, counted - right_bars):
        window = bars[index - left_bars:index + right_bars + 1]
        high = bars[index]["high"]
        low = bars[index]["low"]
        if _unique(window, "high", high):
            if high == max(bar["high"] for bar in window):
                highs.append((index, index + right_bars, high))
        if _unique(window, "low", low):
            if low == min(bar["low"] for bar in window):
                lows.append((index, index + right_bars, low))
    return highs, lows


def by_confirmation(pivots: list) -> dict:
    """Pivots grouped by the bar index that makes them known."""
    grouped = {}
    for pivot_index, confirm_index, price in pivots:
        grouped.setdefault(confirm_index, []).append((pivot_index, price))
    return grouped
