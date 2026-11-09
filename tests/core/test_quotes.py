"""Tests for the quote helpers that read the edges of a stored CSV."""

from __future__ import annotations

from src.core import quotes

ROWS = [
    ("2026-11-05 21:58:00", 10, 11, 9, 10.5, 1),
    ("2026-11-05 21:59:00", 10.5, 11, 10, 10.8, 1),
    ("2026-11-06 23:00:00", 11, 12, 10, 11.5, 1),
    ("2026-11-06 23:59:00", 11.5, 12, 11, 11.9, 1),
]


def test_tail_quotes_reads_the_last_two_days(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    result = quotes.tail_quotes(path)
    assert result["last_day"] == "2026-11-06"
    assert result["last_bar"] == "2026-11-06 23:59:00"
    assert result["last_close"] == 11.9
    assert result["previous_day"] == "2026-11-05"
    assert result["previous_close"] == 10.8


def test_tail_quotes_survives_a_cut_first_line(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    result = quotes.tail_quotes(path, max_bytes=120)
    assert result["last_close"] == 11.9
    assert result["previous_close"] == 10.8


def test_tail_quotes_returns_nothing_for_a_missing_file(tmp_path):
    assert quotes.tail_quotes(str(tmp_path / "missing.csv")) == {}


def test_numbers_rejects_a_short_row():
    assert quotes.numbers(["timestamp", "open"]) is None


def test_numbers_rejects_a_broken_cell():
    assert quotes.numbers(["t", "1", "2", "3", "oops", "5"]) is None


def test_first_close_reads_the_oldest_row(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    assert quotes.first_close(path) == 10.5


def test_first_close_is_none_without_a_stored_row(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", [])
    assert quotes.first_close(path) is None
    assert quotes.first_close(str(tmp_path / "missing.csv")) is None


def test_count_rows_ignores_the_header(tmp_path, write_month):
    path = write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    assert quotes.count_rows(path) == len(ROWS)
    empty = write_month(tmp_path, "xauusd_1m_2026-10.csv", [])
    assert quotes.count_rows(empty) == 0
    assert quotes.count_rows(str(tmp_path / "missing.csv")) == 0
