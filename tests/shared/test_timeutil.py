"""Tests for the UTC time helpers."""

import datetime as dt

import pytest

from src.shared import timeutil

SAMPLE = dt.datetime(2026, 11, 6, 21, 59, tzinfo=dt.timezone.utc)


def test_minute_floor_drops_seconds_and_microseconds():
    when = dt.datetime(2026, 11, 6, 21, 59, 42, 123456, tzinfo=dt.timezone.utc)
    assert timeutil.minute_floor(when) == SAMPLE


def test_minute_floor_assumes_utc_for_naive_input():
    naive = dt.datetime(2026, 11, 6, 21, 59, 30)
    assert timeutil.minute_floor(naive).tzinfo is dt.timezone.utc


def test_timestamp_text_round_trip():
    milliseconds = int(SAMPLE.timestamp() * 1000)
    assert timeutil.ts_to_text(milliseconds) == "2026-11-06 21:59:00"
    assert timeutil.text_to_ms("2026-11-06 21:59:00") == milliseconds


def test_text_to_ms_returns_zero_for_unparsable_text():
    assert timeutil.text_to_ms("") == 0
    assert timeutil.text_to_ms("not-a-timestamp") == 0
    assert timeutil.text_to_ms("2026-13-45 99:99:99") == 0


def test_parse_cli_date_accepts_both_documented_forms():
    assert timeutil.parse_cli_date("2026-11-06") == dt.datetime(
        2026, 11, 6, tzinfo=dt.timezone.utc)
    assert timeutil.parse_cli_date("2026-11-06 15:30") == dt.datetime(
        2026, 11, 6, 15, 30, tzinfo=dt.timezone.utc)


def test_parse_cli_date_rejects_other_formats():
    with pytest.raises(ValueError):
        timeutil.parse_cli_date("06/11/2026")


def test_utc_now_minute_is_utc_and_on_a_minute_boundary():
    now = timeutil.utc_now_minute()
    assert now.tzinfo is dt.timezone.utc
    assert now.second == 0
    assert now.microsecond == 0
