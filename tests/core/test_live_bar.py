"""Tests for the in-memory live bar buffer (no files, no socket)."""

import builtins

import pytest

from src.core import live_bar
from src.shared import config

BASE = (1_760_000_000_000 // config.MINUTE_MS) * config.MINUTE_MS
MINUTE = config.MINUTE_MS


def _bar(buffer, minute_ms):
    return buffer.get(minute_ms)


def test_a_first_tick_opens_a_bar():
    buffer = live_bar.LiveBuffer(10)
    assert buffer.accept(BASE + 5_000, 4000.0) is True
    bar = _bar(buffer, live_bar.minute_of(BASE))
    assert (bar["open"], bar["high"], bar["low"], bar["close"]) == (
        4000.0, 4000.0, 4000.0, 4000.0)
    assert bar["ticks"] == 1
    assert bar["volume"] is None


def test_high_low_and_close_follow_every_tick():
    buffer = live_bar.LiveBuffer(10)
    for offset, price in ((1_000, 4000.0), (20_000, 4002.5),
                          (40_000, 3999.5), (50_000, 4001.0)):
        buffer.accept(BASE + offset, price)
    bar = _bar(buffer, live_bar.minute_of(BASE))
    assert (bar["open"], bar["high"], bar["low"], bar["close"]) == (
        4000.0, 4002.5, 3999.5, 4001.0)
    assert bar["ticks"] == 4


def test_an_out_of_order_tick_keeps_the_earliest_open_and_the_latest_close():
    buffer = live_bar.LiveBuffer(10)
    buffer.accept(BASE + 30_000, 4001.0)
    buffer.accept(BASE + 10_000, 3999.0)
    bar = _bar(buffer, live_bar.minute_of(BASE))
    assert bar["open"] == 3999.0
    assert bar["close"] == 4001.0
    assert bar["ticks"] == 2


def test_a_tick_at_the_boundary_minute_is_refused():
    buffer = live_bar.LiveBuffer(10, boundary_ms=BASE)
    assert buffer.accept(BASE + 30_000, 4000.0) is False
    assert buffer.snapshot() == []


def test_the_minute_after_the_boundary_is_accepted():
    buffer = live_bar.LiveBuffer(10, boundary_ms=BASE)
    assert buffer.accept(BASE + MINUTE + 1, 4001.0) is True
    assert buffer.covered(BASE + MINUTE + 1) is False


def test_prune_drops_the_bars_the_stored_data_now_covers():
    buffer = live_bar.LiveBuffer(10)
    buffer.accept(BASE, 4000.0)
    buffer.accept(BASE + MINUTE, 4001.0)
    assert buffer.prune(BASE) == 1
    assert [bar["minute_ms"] for bar in buffer.snapshot()] == [BASE + MINUTE]


def test_prune_never_moves_the_boundary_backwards():
    buffer = live_bar.LiveBuffer(10, boundary_ms=BASE + 5 * MINUTE)
    assert buffer.prune(BASE) == 0
    assert buffer.boundary_ms == BASE + 5 * MINUTE


def test_the_buffer_keeps_only_the_newest_minutes():
    buffer = live_bar.LiveBuffer(3)
    for index in range(5):
        buffer.accept(BASE + index * MINUTE, 4000.0 + index)
    assert [bar["minute_ms"] for bar in buffer.snapshot()] == [
        BASE + 2 * MINUTE, BASE + 3 * MINUTE, BASE + 4 * MINUTE]


def test_the_snapshot_is_sorted_and_returns_copies():
    buffer = live_bar.LiveBuffer(10)
    buffer.accept(BASE + MINUTE, 4001.0)
    buffer.accept(BASE, 4000.0)
    snapshot = buffer.snapshot()
    assert [bar["minute_ms"] for bar in snapshot] == [BASE, BASE + MINUTE]
    snapshot[0]["close"] = -1
    assert _bar(buffer, BASE)["close"] == 4000.0
    assert snapshot[0]["minute"] == live_bar.timeutil.ts_to_text(BASE)


def test_the_newest_minute_tracks_the_highest_buffered_minute():
    buffer = live_bar.LiveBuffer(10)
    assert buffer.newest_minute is None
    buffer.accept(BASE + MINUTE, 4001.0)
    assert buffer.newest_minute == BASE + MINUTE


def test_a_non_positive_limit_is_rejected():
    with pytest.raises(ValueError):
        live_bar.LiveBuffer(0)


def test_aggregation_never_touches_the_filesystem(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("the live buffer must not touch files")

    monkeypatch.setattr(builtins, "open", explode)
    buffer = live_bar.LiveBuffer(5)
    buffer.accept(BASE, 4000.0)
    buffer.accept(BASE + MINUTE, 4001.0)
    buffer.prune(BASE)
    assert len(buffer.snapshot()) == 1
