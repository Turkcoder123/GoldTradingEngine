"""Tests for the live session: routing, precedence and the DXY poll."""

import datetime as dt

import pytest

from src.core import live_client, live_feed, live_ticks
from src.shared import config, timeutil

BASE = timeutil.text_to_ms("2026-11-09 12:00:00")
MINUTE = config.MINUTE_MS
NOW = dt.datetime(2026, 11, 9, 12, 5, tzinfo=dt.timezone.utc)


def _stored(write_month, folder, key, *minutes):
    """Stores one bar per given minute index in the month file of a series."""
    rows = [[timeutil.ts_to_text(BASE + index * MINUTE),
             4000, 4000, 4000, 4000, 0.1] for index in minutes]
    return write_month(folder, f"{key}_1m_2026-11.csv", rows)


def _session(folder, **kwargs):
    kwargs.setdefault("key", "test-key")
    kwargs.setdefault("boundary_seconds", 0)
    kwargs.setdefault("report", lambda text: None)
    return live_feed.LiveSession(str(folder), **kwargs)


def _tick(series="xauusd", offset_seconds=90, price=4001.0):
    return live_ticks.Tick(series, "XAUUSD", BASE + offset_seconds * 1000,
                           price)


def _rows(*minutes):
    """Dukascopy shaped rows: [timestamp, open, high, low, close, volume]."""
    return [[BASE + index * MINUTE, 101.0, 101.5, 100.5, 101.2, 0.1]
            for index in minutes]


def test_the_stored_boundary_is_the_newest_csv_minute(write_month, tmp_path):
    _stored(write_month, tmp_path, "xauusd", 0, 1, 2)
    assert live_feed.stored_through(str(tmp_path), "xauusd") == BASE + 2 * MINUTE


def test_every_requested_series_starts_from_its_own_boundary(
        write_month, tmp_path):
    _stored(write_month, tmp_path, "xauusd", 0)
    _stored(write_month, tmp_path, "eurusd", 0, 1)
    session = _session(tmp_path, series=["xauusd", "eurusd"])
    assert session.buffers["xauusd"].boundary_ms == BASE
    assert session.buffers["eurusd"].boundary_ms == BASE + MINUTE


def test_a_tick_inside_the_stored_minute_is_refused(write_month, tmp_path):
    _stored(write_month, tmp_path, "xauusd", 0)
    emitted = []
    session = _session(tmp_path, series=["xauusd"],
                       on_bar=lambda key, bar: emitted.append((key, bar)))
    session._accept_tick(_tick(offset_seconds=30))
    assert emitted == []
    assert session.snapshot()["xauusd"] == []


def test_a_new_minute_closes_the_previous_live_bar(write_month, tmp_path):
    _stored(write_month, tmp_path, "xauusd", 0)
    emitted = []
    session = _session(tmp_path, series=["xauusd"],
                       on_bar=lambda key, bar: emitted.append((key, bar)))
    session._accept_tick(_tick(offset_seconds=90, price=4001.0))
    session._accept_tick(_tick(offset_seconds=150, price=4002.0))
    assert [key for key, _bar in emitted] == ["xauusd"]
    bar = emitted[0][1]
    assert bar["minute"] == timeutil.ts_to_text(BASE + MINUTE)
    assert bar["volume"] is None


def test_ticks_are_routed_to_the_buffer_of_their_series(write_month, tmp_path):
    session = _session(tmp_path, series=["xauusd", "eurusd"])
    session._accept_tick(_tick(series="xauusd", offset_seconds=90))
    session._accept_tick(_tick(series="eurusd", offset_seconds=90))
    assert len(session.snapshot()["xauusd"]) == 1
    assert len(session.snapshot()["eurusd"]) == 1


def test_a_boundary_that_advances_prunes_the_covered_bars(
        write_month, tmp_path):
    _stored(write_month, tmp_path, "xauusd", 0)
    session = _session(tmp_path, series=["xauusd"])
    session._accept_tick(_tick(offset_seconds=90))
    _stored(write_month, tmp_path, "xauusd", 0, 1)
    session._accept_tick(_tick(offset_seconds=150))
    assert [bar["minute_ms"] for bar in session.snapshot()["xauusd"]] == [
        BASE + 2 * MINUTE]


class _Fetch:
    """Records every poll and answers the rows it was built with."""

    def __init__(self, rows=(), error=None):
        self.rows = list(rows)
        self.error = error
        self.calls = []

    def __call__(self, start, end, settings):
        self.calls.append((start, end, settings.instrument))
        if self.error is not None:
            raise self.error
        return iter(self.rows)


def test_a_dxy_poll_buffers_and_emits_the_polled_bars(write_month, tmp_path):
    emitted = []
    fetch = _Fetch(_rows(0, 1))
    session = _session(tmp_path, series=["dxy"], fetch=fetch, now=lambda: NOW,
                       on_bar=lambda key, bar: emitted.append((key, bar)))
    assert session._poll_dxy(force=True) == 2
    bars = session.snapshot()["dxy"]
    assert [bar["minute"] for bar in bars] == [
        timeutil.ts_to_text(BASE), timeutil.ts_to_text(BASE + MINUTE)]
    assert bars[0]["volume"] == 0.1
    assert [key for key, _bar in emitted] == ["dxy", "dxy"]
    assert fetch.calls[0][2] == config.SERIES["dxy"].instrument


def test_the_dxy_poll_waits_for_its_interval(write_month, tmp_path):
    fetch = _Fetch(_rows(0))
    session = _session(tmp_path, series=["dxy"], fetch=fetch,
                       dxy_seconds=60, now=lambda: NOW)
    session._poll_dxy(force=True)
    session._poll_dxy()
    assert len(fetch.calls) == 1


def test_a_polled_row_the_store_already_covers_is_refused(
        write_month, tmp_path):
    _stored(write_month, tmp_path, "dxy", 0)
    session = _session(tmp_path, series=["dxy"], fetch=_Fetch(_rows(0, 1)),
                       now=lambda: NOW)
    assert session._poll_dxy(force=True) == 1
    assert [bar["minute_ms"] for bar in session.snapshot()["dxy"]] == [
        BASE + MINUTE]


def test_a_failing_poll_is_reported_not_raised(write_month, tmp_path):
    reports = []
    session = _session(tmp_path, series=["dxy"], now=lambda: NOW,
                       fetch=_Fetch(error=OSError("feed down")),
                       report=reports.append)
    assert session._poll_dxy(force=True) == 0
    assert any("dxy poll failed" in text for text in reports)


def test_a_dxy_only_session_needs_no_api_key(write_month, tmp_path):
    session = _session(tmp_path, series=["dxy"], key=None, fetch=_Fetch(),
                       now=lambda: NOW)
    assert session.feed is None


def test_a_streamed_series_without_a_key_is_a_readable_error(monkeypatch,
                                                             tmp_path):
    from src.core import live_client as client
    monkeypatch.delenv("SIFTING_API_KEY", raising=False)
    monkeypatch.setattr(client.envfile, "read", lambda path: {})
    with pytest.raises(client.LiveFeedError) as error:
        live_feed.LiveSession(str(tmp_path), ["xauusd"])
    assert "SIFTING_API_KEY" in str(error.value)


def test_an_unknown_live_series_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        live_feed.LiveSession(str(tmp_path), ["xagusd"])


class _Clock:
    """Fake monotonic clock: every call advances one second."""

    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


def test_a_dxy_only_run_polls_until_the_duration_ends(write_month, tmp_path):
    fetch = _Fetch(_rows(0))
    session = _session(tmp_path, series=["dxy"], fetch=fetch, now=lambda: NOW,
                       clock=_Clock(), sleeper=lambda _p: None)
    summary = session.run(max_seconds=3)
    assert fetch.calls
    assert summary["bars"] == {"dxy": 1}
    assert summary["boundary"]["dxy"] is None


def test_stop_finishes_the_session(write_month, tmp_path):
    session = _session(tmp_path, series=["dxy"], fetch=_Fetch(),
                       now=lambda: NOW)
    session.stop()
    assert session.run(max_seconds=0)["stopped"] is True

