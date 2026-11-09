"""Names and the row builder of one detected SMC structure (LANG-2, CODE-8).

Every detector writes the same row shape, so the API, the tests and the chart
overlay never have to guess which keys an event carries. `pattern_at` is the bar
that formed the structure, `detected_at` is the first bar whose close made it
knowable; a caller must use the second one (no look-ahead).
"""

from __future__ import annotations

SWING_HIGH = "SWING_HIGH"
SWING_LOW = "SWING_LOW"
BOS = "BOS"
CHOCH = "CHOCH"
LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
ORDER_BLOCK = "ORDER_BLOCK"
FVG = "FVG"

PATTERNS = (SWING_HIGH, SWING_LOW, BOS, CHOCH, LIQUIDITY_SWEEP, ORDER_BLOCK, FVG)
ZONE_PATTERNS = (ORDER_BLOCK, FVG)
STRUCTURE_PATTERNS = (BOS, CHOCH)

BULLISH = "bullish"
BEARISH = "bearish"
BULLISH_REFERENCE = "bullish_reference"
BEARISH_REFERENCE = "bearish_reference"
BUY_SIDE_TAKEN = "buy_side_taken"
SELL_SIDE_TAKEN = "sell_side_taken"


def event(pattern: str, direction: str, times: tuple, level: float,
          **extra) -> dict:
    """One structure; `times` is (pattern_at, detected_at) as day strings."""
    row = {
        "pattern": pattern,
        "direction": direction,
        "pattern_at": times[0],
        "detected_at": times[1],
        "level": level,
    }
    row.update(extra)
    return row
