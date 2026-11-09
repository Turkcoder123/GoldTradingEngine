"""Tests for the live session and its Dukascopy precedence rule."""

import json
import os

import pytest

from src.core import live_client, live_feed, live_ticks
from src.shared import config, timeutil

TEXT = "2026-11-09 12:00:00"
BASE = timeutil.text_to_ms(TEXT)
MINUTE = config.MINUTE_MS


def _stored(write_month, folder, *minutes):
    """Stores one bar per given minute index in the newest month file."""
    rows = [[timeutil.ts_to_text(BASE + index * MINUTE),
             4000, 4000, 4000, 4000, 0] for index in minutes]
    return write_month(folder, "xauusd_1m_2026-11.csv", rows)


def _session(folder, **kwargs):
    kwargs.setdefault("key", "test-key")
    kwargs.setdefault("boundary_seconds", 0)
    kwargs.setdefault("report", lambda text: None)
    return live_feed.LiveSession(str(folder), "xauusd", config.SIDE_BID, 10,
                                 **kwargs)


def _tick(offset_seconds, price):
    return live_ticks.Tick("XAU/USD", BASE + offset_seconds * 1000, price)


def test_the_stored_boundary_is_the_newest_csv_minute(write_month, tmp_path):
    _stored(write_month, tmp_path, 0, 1, 2)
    assert live_feed.stored_through(str(tmp_path), "xauusd") == BASE + 2 * MINUTE


def test_the_session_starts_from_the_stored_boundary(write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    assert _session(tmp_path).buffer.boundary_ms == BASE


def test_a_tick_inside_the_stored_minute_is_refused(write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    emitted = []
    _session(tmp_path, on_bar=emitted.append).accept_tick(_tick(30, 4001.0))
    assert emitted == []
    assert _session(tmp_path).buffer.snapshot() == []


def test_the_first_live_minute_is_buffered_without_being_closed(
        write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    emitted = []
    session = _session(tmp_path, on_bar=emitted.append)
    session.accept_tick(_tick(90, 4001.5))
    assert emitted == []
    assert session.snapshot()[0]["minute"] == timeutil.ts_to_text(BASE + MINUTE)


def test_a_new_minute_closes_the_previous_live_bar(write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    emitted = []
    session = _session(tmp_path, on_bar=emitted.append)
    session.accept_tick(_tick(90, 4001.5))
    session.accept_tick(_tick(150, 4002.5))
    assert len(emitted) == 1
    bar = emitted[0]
    assert bar["minute"] == timeutil.ts_to_text(BASE + MINUTE)
    assert (bar["open"], bar["high"], bar["low"], bar["close"]) == (
        4001.5, 4001.5, 4001.5, 4001.5)
    assert bar["volume"] is None


def test_an_out_of_order_tick_inside_a_live_minute_updates_the_bar(
        write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    session = _session(tmp_path)
    session.accept_tick(_tick(140, 4002.0))
    session.accept_tick(_tick(120, 4000.0))
    bar = session.snapshot()[0]
    assert (bar["open"], bar["close"], bar["ticks"]) == (4000.0, 4002.0, 2)


def test_a_boundary_that_advances_prunes_the_covered_bars(
        write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    session = _session(tmp_path)
    session.accept_tick(_tick(90, 4001.0))
    _stored(write_month, tmp_path, 0, 1)
    session.accept_tick(_tick(150, 4002.0))
    minutes = [bar["minute_ms"] for bar in session.snapshot()]
    assert minutes == [BASE + 2 * MINUTE]


def test_the_snapshot_is_sorted_by_minute(write_month, tmp_path):
    _stored(write_month, tmp_path, 0)
    session = _session(tmp_path)
    session.accept_tick(_tick(150, 4002.0))
    session.accept_tick(_tick(90, 4001.0))
    assert [bar["minute_ms"] for bar in session.snapshot()] == [
        BASE + MINUTE, BASE + 2 * MINUTE]


def test_a_missing_api_key_is_a_readable_error(monkeypatch, tmp_path):
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.setattr(live_client.envfile, "read", lambda path: {})
    with pytest.raises(live_client.LiveFeedError) as error:
        live_feed.LiveSession(str(tmp_path), "xauusd", config.SIDE_BID)
    assert "TWELVE_DATA_API_KEY" in str(error.value)


class _Timeout(Exception):
    """Stands in for the websocket timeout exception."""


class _Socket:
    """Fake socket that answers one price frame and then stays idle."""

    def __init__(self, frame):
        self.sent = []
        self.closed = False
        self._frame = frame

    def send(self, payload):
        self.sent.append(payload)

    def recv(self):
        if self._frame:
            frame, self._frame = self._frame, ""
            return frame
        raise _Timeout()

    def close(self):
        self.closed = True


class _Clock:
    """Fake monotonic clock: every call advances one second."""

    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


def test_a_run_delegates_to_the_stream_and_reports_the_boundary(
        write_month, tmp_path):
    path = _stored(write_month, tmp_path, 0)
    size = os.path.getsize(path)
    frame = json.dumps({"event": "price", "symbol": "XAU/USD",
                        "timestamp": (BASE // 1000) + 90, "bid": 4001.0})
    socket = _Socket(frame)
    session = _session(tmp_path, connect=lambda key: live_client.Connection(
        socket, (_Timeout,)), clock=_Clock(), sleeper=lambda _p: None)
    summary = session.run(max_seconds=10)
    assert summary["accepted"] == 1
    assert summary["bars"] == 1
    assert summary["boundary"] == timeutil.ts_to_text(BASE)
    assert os.path.getsize(path) == size


def test_stop_asks_the_stream_to_finish(write_month, tmp_path):
    session = _session(tmp_path)
    session.stop()
    assert session.feed.summary()["stopped"] is True
