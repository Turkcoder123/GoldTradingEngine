"""Tests for the timeframes and windows of the price chart."""

import pytest

from src.features.web import intervals, price_view


def test_minutes_rejects_an_unknown_timeframe():
    with pytest.raises(ValueError):
        intervals.minutes("2h")


def test_the_bucket_of_an_intraday_bar_starts_at_its_timeframe():
    key, text, day = intervals.bucket("2026-11-09 08:37:00", "5m")
    assert key == text == "2026-11-09 08:35"
    assert day == "2026-11-09"


def test_the_bucket_of_a_daily_bar_is_the_day():
    assert intervals.bucket("2026-11-09 23:59:00", "1d")[0] == "2026-11-09"


def test_the_daily_cap_is_the_largest_and_every_cap_is_positive():
    for name in intervals.INTERVALS:
        assert intervals.limit(name) > 0
    assert intervals.limit("1d") >= intervals.limit("1h")


def test_a_daily_aggregate_keeps_one_bar_per_day(tmp_path, write_month):
    rows = [["2026-11-09 08:00:00", 10, 11, 9, 10.5, 1],
            ["2026-11-09 08:30:00", 10.5, 12, 10, 11.5, 2],
            ["2026-11-10 08:00:00", 11.5, 12, 11, 11.8, 3]]
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", rows)
    bars = price_view.aggregate_file(path, "1d")["bars"]
    assert [bar["time"] for bar in bars] == ["2026-11-09", "2026-11-10"]
    first = bars[0]
    assert (first["open"], first["high"], first["low"], first["close"],
            first["volume"], first["count"]) == (10, 12, 9, 11.5, 3, 2)


def test_an_hourly_aggregate_keeps_one_bar_per_hour(tmp_path, write_month):
    rows = [["2026-11-09 08:05:00", 10, 10, 10, 10, 1],
            ["2026-11-09 08:59:00", 10, 12, 10, 12, 1],
            ["2026-11-09 09:01:00", 12, 13, 12, 13, 1]]
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", rows)
    bars = price_view.aggregate_file(path, "1h")["bars"]
    assert [bar["time"] for bar in bars] == ["2026-11-09 08:00",
                                            "2026-11-09 09:00"]


def test_the_window_keeps_the_newest_days(tmp_path, write_month):
    rows = [["2026-11-01 08:00:00", 1, 1, 1, 1, 1],
            ["2026-11-05 08:00:00", 2, 2, 2, 2, 1],
            ["2026-11-09 08:00:00", 3, 3, 3, 3, 1]]
    write_month(tmp_path, "xauusd_1m_2026-11.csv", rows)
    body = price_view.payload(price_view.aggregate_file, str(tmp_path),
                              "xauusd", 0, 3, "1d")
    assert [bar["time"] for bar in body["bars"]] == ["2026-11-09"]
    assert body["interval"] == "1d"
    assert body["days_requested"] == 3
    assert body["bars_total"] == 1


def test_an_intraday_window_reads_only_the_months_it_needs(
        tmp_path, write_month, monkeypatch):
    monkeypatch.setitem(intervals.LIMITS, "1m", 60)
    for month in ("2026-09", "2026-10", "2026-11"):
        write_month(tmp_path, "xauusd_1m_%s.csv" % month, [])
    body = price_view.payload(price_view.aggregate_file, str(tmp_path),
                              "xauusd", 0, 0, "1m")
    assert body["months"] == ["2026-11"]


def test_a_long_window_is_cut_to_the_cap_of_its_timeframe(
        tmp_path, write_month, monkeypatch):
    monkeypatch.setitem(intervals.LIMITS, "1h", 2)
    rows = [["2026-11-09 0%d:00:00" % hour, 1, 1, 1, 1, 1]
            for hour in range(5)]
    write_month(tmp_path, "xauusd_1m_2026-11.csv", rows)
    body = price_view.payload(price_view.aggregate_file, str(tmp_path),
                              "xauusd", 0, 0, "1h")
    assert body["truncated"] is True
    assert body["bars_total"] == 5
    assert len(body["bars"]) == 2
    assert body["bars"][-1]["time"] == "2026-11-09 04:00"
