"""Tests for one catch-up run: gap safety, closures and reporting."""

import datetime as dt
import pathlib

from src.core import csvfile, feed, refresh, storage
from src.shared import config

START = dt.datetime(2026, 11, 5, tzinfo=dt.timezone.utc)


def minute_rows(start, count):
    base = int(start.timestamp() * 1000)
    return [[base + step * config.MINUTE_MS, 1, 1, 1, 1, 1]
            for step in range(count)]


def settings(**overrides):
    options = {"segment_hours": 24, "max_segments": 2, "since": START,
               "feed": feed.FeedSettings(retries=1)}
    options.update(overrides)
    return refresh.RefreshSettings(**options)


def test_initial_cursor_uses_since_when_there_is_no_data(tmp_path):
    cursor, last_ms = refresh.initial_cursor(
        str(tmp_path), settings(since=START), START + dt.timedelta(days=1))
    assert cursor == START
    assert last_ms == 0


def test_initial_cursor_starts_after_the_newest_stored_minute(tmp_path):
    stored = minute_rows(START, 10)
    storage.append_rows(str(tmp_path), stored)
    cursor, last_ms = refresh.initial_cursor(
        str(tmp_path), settings(since=None), START + dt.timedelta(days=1))
    assert cursor == START + dt.timedelta(minutes=10)
    assert last_ms == stored[-1][0]


def test_feed_error_is_reported_instead_of_raised(tmp_path, monkeypatch):
    def explode(begin, end, run_settings):
        raise feed.FeedError("boom")

    monkeypatch.setattr(refresh.feed_module, "fetch_range", explode)
    result = refresh.refresh_once(str(tmp_path), settings())
    assert result.ok is False
    assert result.error == "boom"
    assert result.pending_minutes > 0


def test_storage_error_is_reported_instead_of_raised(tmp_path, monkeypatch):
    path = config.month_path(str(tmp_path), START)
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text("wrong,header\r\n", encoding=config.ENCODING)
    monkeypatch.setattr(
        refresh.feed_module, "fetch_range",
        lambda begin, end, run_settings: iter(minute_rows(START, 5)))
    result = refresh.refresh_once(str(tmp_path), settings())
    assert result.ok is False
    assert "header" in result.error


def test_run_stops_before_writing_beyond_a_gap(tmp_path, monkeypatch):
    def empty(begin, end, run_settings):
        return iter([])

    monkeypatch.setattr(refresh.feed_module, "fetch_range", empty)
    result = refresh.refresh_once(
        str(tmp_path), settings(max_segments=8, empty_allowance_hours=12))
    assert result.ok is True
    assert result.added == 0
    assert result.done is False
    assert result.segments == 1
    assert csvfile.month_files(str(tmp_path)) == []


def test_run_writes_nothing_after_a_long_gap(tmp_path, monkeypatch):
    def glitchy(begin, end, run_settings):
        if begin < START + dt.timedelta(hours=48):
            return iter([])
        return iter(minute_rows(begin, 30))

    monkeypatch.setattr(refresh.feed_module, "fetch_range", glitchy)
    result = refresh.refresh_once(
        str(tmp_path), settings(max_segments=8, empty_allowance_hours=12))
    assert result.added == 0
    assert csvfile.month_files(str(tmp_path)) == []
    assert result.start == "2026-11-05 00:00"


def test_short_closure_is_walked_through(tmp_path, monkeypatch):
    def weekend(begin, end, run_settings):
        if begin < START + dt.timedelta(hours=24):
            return iter([])
        return iter(minute_rows(begin, 60))

    monkeypatch.setattr(refresh.feed_module, "fetch_range", weekend)
    result = refresh.refresh_once(
        str(tmp_path), settings(max_segments=2, empty_allowance_hours=72))
    assert result.ok is True
    assert result.added == 60
    assert result.closure_hours == 24.0
    assert result.files == ("xauusd_1m_2026-11.csv",)


def test_run_reports_the_stored_last_bar_not_the_cursor(tmp_path, monkeypatch):
    stored = minute_rows(START, 10)
    storage.append_rows(str(tmp_path), stored)
    monkeypatch.setattr(
        refresh.feed_module, "fetch_range",
        lambda begin, end, run_settings: iter(stored))
    result = refresh.refresh_once(str(tmp_path), settings(max_segments=1))
    assert result.added == 0
    assert result.late == 10
    assert result.last_bar == "2026-11-05 00:09:00"
    assert result.done is False


def test_run_stores_new_bars_and_marks_itself_done(tmp_path, monkeypatch):
    stored = minute_rows(START, 10)
    fresh = minute_rows(START + dt.timedelta(minutes=10), 5)
    storage.append_rows(str(tmp_path), stored)
    monkeypatch.setattr(
        refresh.feed_module, "fetch_range",
        lambda begin, end, run_settings: iter(fresh))
    result = refresh.refresh_once(str(tmp_path), settings(segment_hours=1))
    assert result.added == 5
    assert result.last_bar == "2026-11-05 00:14:00"
    assert result.files == ("xauusd_1m_2026-11.csv",)


def test_unwritable_data_dir_is_reported(tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding=config.ENCODING)
    result = refresh.refresh_once(str(blocked / "data"), settings())
    assert result.ok is False
    assert result.error is not None
