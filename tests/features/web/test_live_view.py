"""Tests for the dashboard live overlay (`GET /api/live`)."""

import datetime as dt

from src.core import live_snapshot
from src.features.web import live_view

NOW = dt.datetime(2026, 11, 9, 8, 20, tzinfo=dt.timezone.utc)


def _publish(tmp_path, series, written_at="2026-11-09 08:19:30"):
    live_snapshot.write(live_snapshot.path(str(tmp_path)), series, written_at)


def test_a_missing_snapshot_answers_an_empty_overlay(tmp_path):
    body = live_view.payload(str(tmp_path), NOW)
    assert body["series"] == {}
    assert body["stale"] is True
    assert body["age_seconds"] is None


def test_the_published_bars_are_returned_per_series(tmp_path):
    bars = [{"minute": "2026-11-09 08:19:00", "close": 4090.0}]
    _publish(tmp_path, {"xauusd": bars})
    body = live_view.payload(str(tmp_path), NOW)
    assert body["series"] == {"xauusd": bars}
    assert body["age_seconds"] == 30
    assert body["stale"] is False
    assert body["source"] == "siftingio+dukascopy"


def test_the_window_is_capped(tmp_path):
    bars = [{"minute": str(index)} for index in range(live_view.MAX_MINUTES + 10)]
    _publish(tmp_path, {"xauusd": bars})
    body = live_view.payload(str(tmp_path), NOW)
    assert len(body["series"]["xauusd"]) == live_view.MAX_MINUTES
    assert body["series"]["xauusd"][-1]["minute"] == str(len(bars) - 1)


def test_an_old_document_is_marked_stale(tmp_path):
    _publish(tmp_path, {"xauusd": []}, written_at="2026-11-09 07:00:00")
    body = live_view.payload(str(tmp_path), NOW)
    assert body["stale"] is True


def test_an_empty_series_is_omitted(tmp_path):
    _publish(tmp_path, {"xauusd": [], "dxy": [{"minute": "x"}]})
    body = live_view.payload(str(tmp_path), NOW)
    assert list(body["series"]) == ["dxy"]
