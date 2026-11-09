"""Tests for the fair value gaps, the order blocks and their lifetime."""

from __future__ import annotations

import pytest

from src.core import smc_zones
from src.core.smc_events import BEARISH, BULLISH


def bar_of(day, open, high, low, close):
    """One daily bar with the keys the detector reads."""
    return {"day": day, "open": open, "high": high, "low": low,
            "close": close, "volume": 1.0, "count": 1}


def test_a_fair_value_gap_needs_three_candles():
    bars = [bar_of("2026-01-01", 10, 11, 9, 10.5)]
    assert smc_zones.fvg_events(bars, 0) == []
    assert smc_zones.fvg_events(bars + bars, 1) == []


def test_a_bullish_gap_is_measured_from_the_first_high_to_the_third_low():
    bars = [bar_of("2026-01-01", 10, 10.5, 9.9, 10.4),
            bar_of("2026-01-02", 10.4, 11, 10.3, 10.9),
            bar_of("2026-01-03", 12, 12.5, 11.9, 12.4)]
    found = smc_zones.fvg_events(bars, 2)
    assert len(found) == 1
    gap = found[0]
    assert gap["pattern"] == "FVG"
    assert gap["direction"] == BULLISH
    assert (gap["zone_low"], gap["zone_high"]) == (10.5, 11.9)
    assert gap["gap_size"] == pytest.approx(1.4)
    assert gap["bar_index"] == 2
    assert gap["pattern_at"] == gap["detected_at"] == "2026-01-03"


def test_a_bearish_gap_is_measured_from_the_third_high_to_the_first_low():
    bars = [bar_of("2026-01-01", 12, 12.5, 11.9, 12.1),
            bar_of("2026-01-02", 12.1, 12.2, 11.5, 11.6),
            bar_of("2026-01-03", 10, 10.4, 9.8, 10.2)]
    gap = smc_zones.fvg_events(bars, 2)[0]
    assert gap["direction"] == BEARISH
    assert (gap["zone_low"], gap["zone_high"]) == (10.4, 11.9)
    assert gap["gap_size"] == pytest.approx(1.5)


def test_an_order_block_is_the_last_opposite_colour_bar_before_the_break():
    bars = [bar_of("2026-01-01", 10, 11, 9, 10.5),
            bar_of("2026-01-02", 10.5, 11, 10, 10.2),
            bar_of("2026-01-03", 10.2, 11.5, 10.1, 11.4)]
    zone = smc_zones.order_block_event(bars, 2, BULLISH, 5)
    assert zone["pattern"] == "ORDER_BLOCK"
    assert zone["bar_index"] == 1
    assert (zone["zone_low"], zone["zone_high"]) == (10, 11)
    assert zone["level"] == 10
    assert zone["pattern_at"] == "2026-01-02"
    assert zone["detected_at"] == "2026-01-03"


def test_an_order_block_answers_none_when_the_window_has_no_opposite_bar():
    bars = [bar_of("2026-01-01", 10, 11, 9, 10.5),
            bar_of("2026-01-02", 10.5, 11, 10, 10.2),
            bar_of("2026-01-03", 10.2, 11.5, 10.1, 11.4)]
    assert smc_zones.order_block_event(bars, 2, BEARISH, 1) is None


def test_a_zone_is_filled_by_the_bar_that_trades_through_it():
    bars = [bar_of("2026-01-01", 10, 11, 9, 10.5),
            bar_of("2026-01-02", 10.5, 12, 10.5, 11.5),
            bar_of("2026-01-03", 11.5, 12, 11.5, 11.8),
            bar_of("2026-01-04", 11.8, 12, 9.5, 10.0),
            bar_of("2026-01-05", 10.0, 10.5, 9.8, 10.2)]
    zone = {"direction": BULLISH, "bar_index": 1, "zone_low": 10,
            "zone_high": 12}
    marked = smc_zones.mark_mitigation(bars, zone)
    assert marked["touched_at"] == "2026-01-03"
    assert marked["filled_at"] == "2026-01-04"
    assert marked["is_filled"] is True
    assert marked["end_index"] == 3


def test_an_untouched_zone_stays_open_to_the_newest_bar():
    bars = [bar_of("2026-01-01", 10, 11, 9, 10.5),
            bar_of("2026-01-02", 10.5, 12, 10.5, 11.5),
            bar_of("2026-01-03", 12, 13, 12.1, 12.8),
            bar_of("2026-01-04", 12.8, 13, 12.4, 12.6)]
    zone = {"direction": BULLISH, "bar_index": 1, "zone_low": 10,
            "zone_high": 12}
    marked = smc_zones.mark_mitigation(bars, zone)
    assert marked["touched_at"] is None
    assert marked["filled_at"] is None
    assert marked["is_filled"] is False
    assert marked["end_index"] == 3


def test_a_touched_but_unfilled_zone_keeps_its_end_at_the_newest_bar():
    bars = [bar_of("2026-01-01", 10, 11, 9, 10.5),
            bar_of("2026-01-02", 10.5, 12, 10.5, 11.5),
            bar_of("2026-01-03", 11.5, 12, 11.6, 11.8),
            bar_of("2026-01-04", 11.8, 12, 11.7, 11.9)]
    zone = {"direction": BULLISH, "bar_index": 1, "zone_low": 10,
            "zone_high": 12}
    marked = smc_zones.mark_mitigation(bars, zone)
    assert marked["touched_at"] == "2026-01-03"
    assert marked["filled_at"] is None
    assert marked["end_index"] == 3
