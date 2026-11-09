"""Tests for the one-pass structure walk: breaks, sweeps and look-ahead."""

from __future__ import annotations

from src.core import smc
from src.core.smc_events import PATTERNS
from src.core.smc_params import SmcParams

PARAMS = SmcParams(left_bars=1, right_bars=1, ob_lookback=5)


def bars_of(rows):
    """Daily bars from (open, high, low, close) rows, one day apart."""
    return [{"day": f"2026-01-{index + 1:02d}", "open": row[0], "high": row[1],
             "low": row[2], "close": row[3], "volume": 1.0, "count": 1}
            for index, row in enumerate(rows)]


STAIR_ROWS = [
    (100, 101, 99.5, 100.5),
    (100.5, 102, 100, 101.5),
    (101.5, 103, 101, 102.5),
    (102.5, 104, 102, 103.5),
    (103.5, 103.8, 101, 101.5),
    (101.5, 102, 99.5, 100),
    (100, 100.5, 98, 98.5),
    (98.5, 99.5, 98.2, 99),
    (99, 101, 98.8, 100.5),
    (100.5, 102.5, 100, 102),
    (102, 104.5, 101.5, 104),
    (104, 106, 103.5, 105.5),
    (105.5, 106.5, 104, 104.5),
    (104.5, 105, 102, 102.5),
    (102.5, 103, 99.5, 100),
    (100, 101, 97, 97.5),
    (97.5, 99, 97, 98.5),
    (98.5, 100, 98, 99.5),
    (99.5, 101, 99, 100.5),
    (100.5, 102, 100, 101.5),
]


def stair_bars():
    """Twenty bars with two confirmed pivots, a break and two gaps."""
    return bars_of(STAIR_ROWS)


BREAK_ROWS = [
    (10, 11, 9, 10),
    (10, 12, 10, 11.5),
    (11.5, 11, 10, 10.2),
    (10.2, 10.8, 10, 10.6),
    (10.6, 12.5, 10.5, 12.4),
    (12.4, 12.6, 11.5, 11.8),
    (11.8, 12.0, 11.0, 11.2),
    (11.2, 11.5, 11.4, 11.0),
    (11.0, 11.1, 10.0, 10.2),
]

SWEEP_ROWS = [
    (10, 11, 9, 10),
    (10, 12, 10, 11.5),
    (11.5, 11, 10, 10.2),
    (10.2, 10.6, 10, 10.4),
    (10.4, 10.8, 10.1, 10.6),
    (10.6, 12.5, 10.5, 11.0),
    (11.0, 11.2, 10.8, 11.0),
    (11.0, 11.1, 10.9, 11.0),
    (11.0, 11.2, 10.9, 11.1),
]


def test_a_window_shorter_than_the_rules_is_empty():
    assert smc.detect(stair_bars()[:10]) == []


def test_a_close_above_the_swing_high_is_a_break_of_structure():
    events = smc.detect(bars_of(BREAK_ROWS), PARAMS)
    breaks = [item for item in events if item["pattern"] == "BOS"]
    assert len(breaks) == 1
    broken = breaks[0]
    assert broken["direction"] == "bullish"
    assert broken["level"] == 12
    assert broken["bar_index"] == 4
    assert broken["pattern_at"] == broken["detected_at"] == "2026-01-05"


def test_the_break_carries_the_last_opposite_bar_as_an_order_block():
    events = smc.detect(bars_of(BREAK_ROWS), PARAMS)
    zones = [item for item in events if item["pattern"] == "ORDER_BLOCK"
             and item["source_break"] == "BOS"]
    assert len(zones) == 1
    zone = zones[0]
    assert zone["bar_index"] == 2
    assert (zone["zone_low"], zone["zone_high"]) == (10, 11)
    assert zone["source_break_at"] == "2026-01-05"


def test_a_break_against_the_trend_is_a_change_of_character():
    events = smc.detect(bars_of(BREAK_ROWS), PARAMS)
    changes = [item for item in events if item["pattern"] == "CHOCH"]
    assert len(changes) == 1
    changed = changes[0]
    assert changed["direction"] == "bearish"
    assert changed["level"] == 11
    assert changed["previous_trend"] == 1


def test_a_wick_through_a_level_with_the_close_back_is_a_sweep():
    events = smc.detect(bars_of(SWEEP_ROWS), PARAMS)
    sweeps = [item for item in events if item["pattern"] == "LIQUIDITY_SWEEP"]
    assert len(sweeps) == 1
    sweep = sweeps[0]
    assert sweep["direction"] == "buy_side_taken"
    assert sweep["level"] == 12
    assert sweep["wick_extreme"] == 12.5
    assert sweep["bar_index"] == 5


def test_a_wick_that_closes_through_the_level_is_not_a_sweep():
    rows = list(SWEEP_ROWS)
    rows[5] = (10.6, 12.5, 10.5, 12.4)
    events = smc.detect(bars_of(rows), PARAMS)
    assert not [item for item in events
                if item["pattern"] == "LIQUIDITY_SWEEP"]


def test_no_event_is_knowable_before_the_bar_that_formed_it():
    bars = stair_bars()
    events = smc.detect(bars)
    assert events
    days = [bar["day"] for bar in bars]
    for item in events:
        assert item["pattern"] in PATTERNS
        assert item["detected_at"] >= item["pattern_at"]
        assert item["detected_at"] in days
        assert 0 <= item["bar_index"] < len(bars)


def test_a_swing_is_known_only_at_the_confirming_bar():
    bars = stair_bars()
    swings = [item for item in smc.detect(bars)
              if item["pattern"] in ("SWING_HIGH", "SWING_LOW")]
    assert swings
    for item in swings:
        assert bars[item["bar_index"]]["day"] == item["pattern_at"]
        assert bars[item["confirmed_index"]]["day"] == item["detected_at"]
        assert item["confirmed_index"] == item["bar_index"] + 3


def test_every_zone_reports_its_lifetime():
    zones = [item for item in smc.detect(stair_bars())
             if item["pattern"] in ("FVG", "ORDER_BLOCK")]
    assert zones
    for zone in zones:
        assert zone["zone_low"] < zone["zone_high"]
        assert zone["end_index"] >= zone["bar_index"]
        assert isinstance(zone["is_filled"], bool)


def test_events_come_back_oldest_detection_first():
    events = smc.detect(stair_bars())
    detected = [item["detected_at"] for item in events]
    assert detected == sorted(detected)


def test_the_parameters_are_reportable():
    assert SmcParams().as_dict() == {"left_bars": 3, "right_bars": 3,
                                     "ob_lookback": 12,
                                     "sweep_tolerance": 0.0}
