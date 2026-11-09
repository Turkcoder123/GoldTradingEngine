"""Tests for the SMC payload behind the overlay (no network)."""

from __future__ import annotations

import pytest

from src.features.web import price_view, smc_view

CLOSES = [10, 11, 12, 13, 12, 11, 10, 9, 8, 9, 10, 11]


def month_rows(closes):
    """One minute per day, so the aggregation produces one daily bar each."""
    rows = []
    for index, close in enumerate(closes):
        day = f"2026-11-{index + 1:02d}"
        rows.append((f"{day} 12:00:00", close - 0.5, close + 0.5, close - 1,
                     close, 1))
    return rows


def test_the_payload_reports_the_window_the_parameters_and_the_events(
        tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", month_rows(CLOSES))
    body = smc_view.payload(price_view.aggregate_file, str(tmp_path), "xauusd",
                            1)
    assert body["key"] == "xauusd"
    assert body["instrument"] == "XAU/USD"
    assert body["timeframe"] == "1d"
    assert body["months"] == ["2026-11"]
    assert body["bars"] == {"count": 12, "first_day": "2026-11-01",
                            "last_day": "2026-11-12"}
    assert body["parameters"]["right_bars"] == 3
    assert body["events"]


def test_the_summary_counts_every_event_once(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", month_rows(CLOSES))
    body = smc_view.payload(price_view.aggregate_file, str(tmp_path), "xauusd",
                            1)
    counted = sum(sum(bucket.values()) for bucket in body["summary"].values())
    assert counted == len(body["events"])
    assert "SWING_HIGH" in body["summary"]


def test_every_event_points_at_a_bar_inside_the_window(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", month_rows(CLOSES))
    body = smc_view.payload(price_view.aggregate_file, str(tmp_path), "xauusd",
                            1)
    for item in body["events"]:
        assert 0 <= item["bar_index"] < body["bars"]["count"]
        assert body["bars"]["first_day"] <= item["detected_at"]
        assert item["detected_at"] <= body["bars"]["last_day"]


def test_an_empty_data_directory_answers_an_empty_window(tmp_path):
    body = smc_view.payload(price_view.aggregate_file, str(tmp_path), "dxy", 1)
    assert body["bars"] == {"count": 0, "first_day": None, "last_day": None}
    assert body["events"] == []
    assert body["summary"] == {}


def test_an_unknown_series_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        smc_view.payload(price_view.aggregate_file, str(tmp_path), "nope", 1)
