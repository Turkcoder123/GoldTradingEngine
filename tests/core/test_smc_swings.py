"""Tests for the confirmed swing pivots of one bar window."""

from __future__ import annotations

from src.core import smc_swings


def bars_of(highs, lows):
    """Daily bars carrying the given highs and lows, one day apart."""
    return [{"day": f"2026-01-{index + 1:02d}", "open": low, "high": high,
             "low": low, "close": low, "volume": 1.0, "count": 1}
            for index, (high, low) in enumerate(zip(highs, lows))]


FLAT_LOWS = [5.0] * 10


def test_a_pivot_is_confirmed_only_after_the_right_bars_close():
    bars = bars_of([10, 11, 12, 13, 20, 13, 12, 11, 10, 9], FLAT_LOWS)
    highs, _lows = smc_swings.confirmed_swings(bars, 2, 2)
    assert highs == [(4, 6, 20)]


def test_a_flat_top_is_not_a_pivot():
    bars = bars_of([10, 12, 12, 10, 9, 8], FLAT_LOWS)
    highs, _lows = smc_swings.confirmed_swings(bars, 1, 1)
    assert highs == []


def test_a_bar_closer_to_the_edge_than_the_right_window_is_not_a_pivot():
    bars = bars_of([10, 11, 19, 20, 18], FLAT_LOWS)
    highs, _lows = smc_swings.confirmed_swings(bars, 2, 2)
    assert highs == []


def test_grouping_keeps_the_pivot_and_the_price_per_confirmation():
    pivots = [(4, 6, 20.0), (5, 7, 8.0)]
    grouped = smc_swings.by_confirmation(pivots)
    assert grouped == {6: [(4, 20.0)], 7: [(5, 8.0)]}


def test_grouping_keeps_two_pivots_confirmed_by_the_same_bar():
    pivots = [(4, 6, 20.0), (3, 6, 8.0)]
    assert smc_swings.by_confirmation(pivots) == {6: [(4, 20.0), (3, 8.0)]}
