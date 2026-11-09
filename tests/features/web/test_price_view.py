"""Tests for the daily aggregation behind the price panel (no network)."""

from __future__ import annotations

import os

import pytest

from src.features.web import price_view

ROWS = [
    ("2026-11-02 23:58:00", 10, 12, 9, 11, 1.5),
    ("2026-11-02 23:59:00", 11, 13, 10, 12, 2.5),
    ("2026-11-03 00:00:00", 12, 12.5, 11, 12.2, 0.5),
]


def test_aggregate_file_builds_daily_bars(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    result = price_view.aggregate_file(path)
    bars = result["bars"]
    assert [bar["day"] for bar in bars] == ["2026-11-02", "2026-11-03"]
    first = bars[0]
    assert (first["open"], first["high"], first["low"], first["close"]) == (
        10, 13, 9, 12)
    assert first["count"] == 2
    assert first["volume"] == pytest.approx(4.0)
    assert result["gaps"] == 0


def test_aggregate_file_counts_minutes_without_bars(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", [
        ("2026-11-02 23:00:00", 10, 12, 9, 11, 1),
        ("2026-11-02 23:10:00", 11, 13, 10, 12, 2),
    ])
    result = price_view.aggregate_file(path)
    assert result["gaps"] == 1
    assert result["missing_minutes"] == 9
    assert result["largest_gap_minutes"] == 9


def test_aggregate_file_skips_unreadable_rows(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", [
        ("2026-11-02 23:00:00", 10, 12, 9, 11, 1),
        ("broken row", "x", "y", "z", "w", "v"),
        ("2026-11-02 23:01:00", 11, 12, 10, 11.5, 1),
    ])
    result = price_view.aggregate_file(path)
    assert result["bars"][0]["count"] == 2
    assert result["gaps"] == 0


def test_month_paths_keeps_the_newest_months(tmp_path, write_month):
    for month in ("2026-09", "2026-10", "2026-11"):
        write_month(tmp_path, f"xauusd_1m_{month}.csv", ROWS)
    newest = price_view.month_paths(str(tmp_path), "xauusd_1m", 2)
    assert [os.path.basename(path) for path in newest] == [
        "xauusd_1m_2026-10.csv", "xauusd_1m_2026-11.csv"]
    assert len(price_view.month_paths(str(tmp_path), "xauusd_1m", 0)) == 3


def test_month_keys_reads_the_file_names(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    assert price_view.month_keys([path]) == ["2026-11"]


def test_combine_adds_the_windows_and_the_gap_counts(write_month, tmp_path):
    first = price_view.aggregate_file(
        write_month(tmp_path, "xauusd_1m_2026-10.csv", [
            ("2026-10-30 10:00:00", 10, 11, 9, 10.5, 1),
            ("2026-10-30 10:05:00", 10.5, 11, 10, 10.8, 1),
        ]))
    second = price_view.aggregate_file(
        write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS))
    bars, quality = price_view.combine([first, second])
    assert len(bars) == 3
    assert quality["gaps"] == 1
    assert quality["missing_minutes"] == 4
    assert quality["largest_gap_minutes"] == 4


def test_summarize_reports_the_window_change(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    bars = price_view.aggregate_file(path)["bars"]
    summary = price_view.summarize(bars)
    assert summary["days"] == 2
    assert summary["bars"] == 3
    assert summary["first_day"] == "2026-11-02"
    assert summary["last_day"] == "2026-11-03"
    assert summary["high"] == 13
    assert summary["low"] == 9
    assert summary["first_close"] == 12
    assert summary["last_close"] == 12.2
    assert summary["change_pct"] == pytest.approx(1.67, abs=0.01)


def test_summarize_handles_an_empty_window():
    summary = price_view.summarize([])
    assert summary["days"] == 0
    assert summary["change_pct"] is None


def test_payload_reports_one_series_for_the_window(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-10.csv", ROWS)
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    body = price_view.payload(price_view.aggregate_file, str(tmp_path),
                              "xauusd", 1)
    assert body["key"] == "xauusd"
    assert body["instrument"] == "XAU/USD"
    assert body["months"] == ["2026-11"]
    assert body["summary"]["days"] == 2
    assert body["quality"]["gaps"] == 0


def test_payload_rejects_an_unknown_series(tmp_path):
    with pytest.raises(ValueError):
        price_view.payload(price_view.aggregate_file, str(tmp_path), "nope", 1)
