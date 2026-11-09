"""Price zones of the detector: fair value gaps, order blocks and their life.

A zone is not only a rectangle: it is born at one bar, it is touched when price
comes back into it, and it is spent when price trades through it. Recording that
lifetime keeps the chart honest and keeps the overlay from filling up with zones
that the market already traded away.
"""

from __future__ import annotations

from .smc_events import BEARISH, BULLISH, FVG, ORDER_BLOCK, event


def fvg_events(bars: list, index: int) -> list:
    """Classic three-candle fair value gap, known at the close of `index`."""
    if index < 2:
        return []
    first, third = bars[index - 2], bars[index]
    times = (third["day"], third["day"])
    if third["low"] > first["high"]:
        return [event(FVG, BULLISH, times, first["high"], bar_index=index,
                      zone_low=first["high"], zone_high=third["low"],
                      gap_size=third["low"] - first["high"])]
    if third["high"] < first["low"]:
        return [event(FVG, BEARISH, times, third["high"], bar_index=index,
                      zone_low=third["high"], zone_high=first["low"],
                      gap_size=first["low"] - third["high"])]
    return []


def order_block_event(bars: list, index: int, direction: str, lookback: int):
    """Last opposite-colour bar before a structure break, as a zone (or None)."""
    start = max(0, index - lookback)
    for candidate in range(index - 1, start - 1, -1):
        bar = bars[candidate]
        bearish_bar = bar["close"] < bar["open"]
        bullish_bar = bar["close"] > bar["open"]
        found = ((direction == BULLISH and bearish_bar)
                 or (direction == BEARISH and bullish_bar))
        if not found:
            continue
        return event(ORDER_BLOCK, direction, (bar["day"], bars[index]["day"]),
                     bar["low"] if direction == BULLISH else bar["high"],
                     bar_index=candidate, zone_low=bar["low"],
                     zone_high=bar["high"])
    return None


def _day(bars: list, index):
    """Day of one bar index, or None when there is no such bar."""
    return None if index is None else bars[index]["day"]


def mark_mitigation(bars: list, zone: dict) -> dict:
    """Adds the lifetime of one zone: first touch, full fill and last drawn bar.

    A bullish zone sits below the price, so a later low trading into it counts as
    a touch and trading through it counts as a fill; a bearish zone is mirrored.
    The overlay draws a zone up to its fill, and up to the newest bar while the
    zone is still open.
    """
    bullish = zone["direction"] == BULLISH
    low, high = zone["zone_low"], zone["zone_high"]
    touched_index = filled_index = None
    for index in range(zone["bar_index"] + 1, len(bars)):
        bar = bars[index]
        if bullish:
            enters, through = bar["low"] <= high, bar["low"] <= low
        else:
            enters, through = bar["high"] >= low, bar["high"] >= high
        if enters and touched_index is None:
            touched_index = index
        if through:
            filled_index = index
            break
    zone.update({
        "touched_at": _day(bars, touched_index),
        "filled_at": _day(bars, filled_index),
        "is_filled": filled_index is not None,
        "end_index": filled_index if filled_index is not None else len(bars) - 1,
    })
    return zone
