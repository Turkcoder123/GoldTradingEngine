"""Tests for the two in-process caches of the dashboard."""

from __future__ import annotations

from src.features.web import cache

ROWS = [("2026-11-06 23:00:00", 10, 11, 9, 10.5, 1)]


def test_ttl_cache_reuses_a_value_until_it_expires():
    clock = [0.0]
    builds = []

    def build():
        builds.append(1)
        return len(builds)

    subject = cache.TtlCache(ttl_seconds=10, clock=lambda: clock[0])
    assert subject.get_or_build("overview", build) == 1
    clock[0] = 5
    assert subject.get_or_build("overview", build) == 1
    clock[0] = 11
    assert subject.get_or_build("overview", build) == 2
    assert len(builds) == 2


def test_ttl_cache_clear_forgets_every_value():
    subject = cache.TtlCache(ttl_seconds=10, clock=lambda: 0.0)
    subject.get_or_build("overview", lambda: {"files": 1})
    subject.clear()
    assert subject.get_or_build("overview", lambda: {"files": 2}) == {"files": 2}


def test_daily_cache_aggregates_once_per_file_version(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    subject = cache.DailyCache()
    first = subject.file_aggregate(path)
    assert first["bars"][0]["close"] == 10.5
    assert subject.file_aggregate(path) is first


def test_daily_cache_notices_a_file_that_grew(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    subject = cache.DailyCache()
    assert len(subject.file_aggregate(path)["bars"]) == 1
    write_month(tmp_path, "xauusd_1m_2026-11.csv",
                ROWS + [("2026-11-07 00:00:00", 11, 12, 10, 11.5, 1)])
    assert len(subject.file_aggregate(path)["bars"]) == 2
