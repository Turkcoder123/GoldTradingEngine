"""Smart money concept structures detected on one ordered bar window.

Ported from the SMC pattern discovery system v0.1 (`smc/detectors.py`) to the
standard library (OPEN-2): the pandas frame is replaced by the daily bar
dictionaries of `features.web.price_view` and the numpy comparisons by plain
Python. The rules themselves are unchanged:

* a swing needs `left_bars` bars on its left and `right_bars` on its right before
  it counts, which is what keeps every event free of look-ahead;
* a structure break is close-based and only uses already confirmed swings; it is
  a CHoCH when it goes against the current trend and a BOS otherwise;
* a liquidity sweep is a wick through a confirmed level with the close back on
  the other side;
* an order block is the last opposite-colour bar before the break;
* a fair value gap is the classic three-candle gap.

The definitions are a documented starting point, not a proven edge
(`docs/smc.md`).
"""

from __future__ import annotations

from .smc_events import (
    BEARISH, BEARISH_REFERENCE, BOS, BULLISH, BULLISH_REFERENCE, BUY_SIDE_TAKEN,
    CHOCH, LIQUIDITY_SWEEP, SELL_SIDE_TAKEN, SWING_HIGH, SWING_LOW,
    ZONE_PATTERNS, event,
)
from .smc_params import DEFAULT_PARAMS, SmcParams
from .smc_swings import by_confirmation, confirmed_swings
from .smc_zones import fvg_events, mark_mitigation, order_block_event

MINIMUM_EXTRA_BARS = 5


class _Walk:
    """One oldest-first pass over the bars, carrying the detection state."""

    def __init__(self, bars: list, params: SmcParams):
        self.bars = bars
        self.params = params
        self.events = []
        self.active_high = None
        self.active_low = None
        self.broken_highs = set()
        self.broken_lows = set()
        self.trend = 0
        self._highs_at = {}
        self._lows_at = {}

    def run(self) -> list:
        """Every event of the window, oldest detection first."""
        highs, lows = confirmed_swings(self.bars, self.params.left_bars,
                                       self.params.right_bars)
        self._highs_at = by_confirmation(highs)
        self._lows_at = by_confirmation(lows)
        for index, bar in enumerate(self.bars):
            self._swings(index)
            self._sweeps(index, bar)
            self._structure(index, bar)
            self.events.extend(fvg_events(self.bars, index))
        return self._result()

    def _result(self) -> list:
        """Closes the lifetime of every zone and orders the events."""
        for item in self.events:
            if item["pattern"] in ZONE_PATTERNS:
                mark_mitigation(self.bars, item)
        return sorted(self.events, key=lambda item: (item["detected_at"],
                                                     item["bar_index"],
                                                     item["pattern"]))

    def _swings(self, index: int) -> None:
        """Pivots whose right-hand bars just closed become the active levels."""
        for pivot_index, price in self._highs_at.get(index, ()):
            self.active_high = (pivot_index, price)
            self.events.append(event(
                SWING_HIGH, BEARISH_REFERENCE,
                (self.bars[pivot_index]["day"], self.bars[index]["day"]), price,
                bar_index=pivot_index, confirmed_index=index))
        for pivot_index, price in self._lows_at.get(index, ()):
            self.active_low = (pivot_index, price)
            self.events.append(event(
                SWING_LOW, BULLISH_REFERENCE,
                (self.bars[pivot_index]["day"], self.bars[index]["day"]), price,
                bar_index=pivot_index, confirmed_index=index))

    def _sweeps(self, index: int, bar: dict) -> None:
        """Wick through a level with the close back on the other side."""
        tolerance = self.params.sweep_tolerance
        high = self.active_high
        if high and high[0] not in self.broken_highs:
            if bar["high"] > high[1] + tolerance and bar["close"] < high[1]:
                self.events.append(event(
                    LIQUIDITY_SWEEP, BUY_SIDE_TAKEN, (bar["day"], bar["day"]),
                    high[1], bar_index=index, reference_pivot=high[0],
                    wick_extreme=bar["high"]))
        low = self.active_low
        if low and low[0] not in self.broken_lows:
            if bar["low"] < low[1] - tolerance and bar["close"] > low[1]:
                self.events.append(event(
                    LIQUIDITY_SWEEP, SELL_SIDE_TAKEN, (bar["day"], bar["day"]),
                    low[1], bar_index=index, reference_pivot=low[0],
                    wick_extreme=bar["low"]))

    def _breaks_high(self, bar: dict) -> bool:
        """True when this close takes out the active, still unbroken high."""
        high = self.active_high
        return (high is not None and high[0] not in self.broken_highs
                and bar["close"] > high[1])

    def _breaks_low(self, bar: dict) -> bool:
        """True when this close takes out the active, still unbroken low."""
        low = self.active_low
        return (low is not None and low[0] not in self.broken_lows
                and bar["close"] < low[1])

    def _structure(self, index: int, bar: dict) -> None:
        """Close-based structure break plus the order block before it."""
        direction = level = pivot = None
        if self._breaks_high(bar):
            direction = BULLISH
            level, pivot = self.active_high[1], self.active_high[0]
            self.broken_highs.add(pivot)
        elif self._breaks_low(bar):
            direction = BEARISH
            level, pivot = self.active_low[1], self.active_low[0]
            self.broken_lows.add(pivot)
        if direction is None:
            return
        against_trend = self.trend != 0 and self.trend != _trend_sign(direction)
        pattern = CHOCH if against_trend else BOS
        self.events.append(event(pattern, direction, (bar["day"], bar["day"]),
                                 level, bar_index=index, broken_pivot=pivot,
                                 previous_trend=self.trend))
        self.trend = _trend_sign(direction)
        zone = order_block_event(self.bars, index, direction,
                                 self.params.ob_lookback)
        if zone is not None:
            zone["source_break"] = pattern
            zone["source_break_at"] = bar["day"]
            self.events.append(zone)


def _trend_sign(direction: str) -> int:
    """1 for a bullish structure, -1 for a bearish one."""
    return 1 if direction == BULLISH else -1


def detect(bars: list, params: SmcParams = DEFAULT_PARAMS) -> list:
    """Every SMC event of one ordered daily bar window, oldest first.

    `bars` are the daily bars of `features.web.price_view`: dictionaries with
    `day`, `open`, `high`, `low`, `close`, `volume` and `count`, sorted by day.
    Each event carries `pattern_at` (the bar that formed it) and `detected_at`
    (the first bar whose close made it knowable), so a caller never acts on a
    pivot before the bars to its right had closed. A window shorter than the two
    pivot windows plus five bars answers an empty list.
    """
    if len(bars) < params.left_bars + params.right_bars + MINIMUM_EXTRA_BARS:
        return []
    return _Walk(bars, params).run()

