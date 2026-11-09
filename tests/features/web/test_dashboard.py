"""Tests for the section builder and its two caches."""

from __future__ import annotations

from src.features.web import dashboard

ROWS = [("2026-11-06 23:00:00", 11, 12, 10, 11.5, 1)]


def test_a_section_is_built_once_per_window(tmp_path):
    subject = dashboard.Dashboard(str(tmp_path), ttl_seconds=60)
    first = subject.series("xauusd", 3)
    assert subject.series("xauusd", 3) is first
    assert subject.series("xauusd", 1) is not first


def test_refresh_rebuilds_the_sections(tmp_path):
    subject = dashboard.Dashboard(str(tmp_path), ttl_seconds=60)
    first = subject.overview()
    assert subject.overview() is first
    subject.refresh()
    assert subject.overview() is not first


def test_the_daily_cache_survives_a_new_window(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    subject = dashboard.Dashboard(str(tmp_path), ttl_seconds=60)
    three = subject.series("xauusd", 3)
    one = subject.series("xauusd", 1)
    assert one["bars"] == three["bars"]
    assert one["summary"]["bars"] == 1


def test_the_smc_section_is_built_once_per_window(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    subject = dashboard.Dashboard(str(tmp_path), ttl_seconds=60)
    first = subject.smc("xauusd", 1)
    assert first["key"] == "xauusd"
    assert subject.smc("xauusd", 1) is first
    assert subject.smc("xauusd", 3) is not first
