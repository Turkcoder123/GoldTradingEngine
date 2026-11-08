"""Tests for the offline freshness report."""

import datetime as dt

from src.core import status, storage
from src.shared import config

START = dt.datetime(2026, 11, 6, 21, 55, tzinfo=dt.timezone.utc)


def bar(offset_minutes):
    moment = START + dt.timedelta(minutes=offset_minutes)
    return [int(moment.timestamp() * 1000), 1, 1, 1, 1, 1]


def test_empty_directory_reports_no_files(tmp_path):
    snapshot = status.status_snapshot(str(tmp_path))
    assert snapshot["files"] == 0
    assert snapshot["first_bar"] is None
    assert snapshot["last_bar"] is None
    assert snapshot["newest_file"] is None
    assert snapshot["error"] is None
    assert snapshot["format"] == config.HEADER


def test_snapshot_reports_the_stored_range(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0), bar(1), bar(2)])
    snapshot = status.status_snapshot(str(tmp_path))
    assert snapshot["files"] == 1
    assert snapshot["newest_file"] == "xauusd_1m_2026-11.csv"
    assert snapshot["first_bar"] == "2026-11-06 21:55:00"
    assert snapshot["last_bar"] == "2026-11-06 21:57:00"
    assert snapshot["gaps"] == 0
    assert snapshot["size_mb"] >= 0.0


def test_snapshot_counts_the_gaps_of_the_newest_file(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0), bar(30)])
    snapshot = status.status_snapshot(str(tmp_path))
    assert snapshot["gaps"] == 1
    assert snapshot["missing_minutes"] == 29


def test_snapshot_reports_the_offer_side_it_reads(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0)], config.SIDE_ASK)
    snapshot = status.status_snapshot(str(tmp_path), config.SIDE_ASK)
    assert snapshot["side"] == config.SIDE_ASK
    assert snapshot["newest_file"] == "xauusd_1m_ask_2026-11.csv"
