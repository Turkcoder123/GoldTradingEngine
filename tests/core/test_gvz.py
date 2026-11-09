"""Tests for the Cboe GVZ source (parsing, storage, no network)."""

from __future__ import annotations

import pytest

from src.core import gvz, gvz_feed
from src.core.altfeed import AltError

CSV_TEXT = b"DATE,GVZ\n11/05/2026,24.110000\n11/06/2026,25.970000\n"


def test_parse_reads_us_dates_and_keeps_the_close():
    rows = gvz_feed.parse(CSV_TEXT)
    assert rows == [{"date": "2026-11-05", "close": "24.110000"},
                    {"date": "2026-11-06", "close": "25.970000"}]


def test_parse_skips_rows_with_a_broken_date_or_value():
    rows = gvz_feed.parse(b"DATE,GVZ\nnot a date,1.0\n11/06/2026,\n")
    assert rows == []


def test_fetch_uses_a_given_payload_without_network(monkeypatch):
    def explode(url, timeout=None):
        raise AssertionError("download must not be called")

    monkeypatch.setattr(gvz_feed, "download", explode)
    assert len(gvz_feed.fetch(CSV_TEXT)) == 2


def test_update_stores_the_merged_series(tmp_path, monkeypatch):
    monkeypatch.setattr(gvz_feed, "fetch", lambda payload=None: [
        {"date": "2026-11-05", "close": "24.11"},
        {"date": "2026-11-06", "close": "25.97"}])
    result = gvz.update_gvz(str(tmp_path))
    assert result.ok is True
    assert result.rows == 2
    assert result.added == 2
    assert result.first_date == "2026-11-05"
    assert result.last_date == "2026-11-06"
    assert result.latest == 25.97
    stored = gvz.status(str(tmp_path))
    assert stored["rows"] == 2
    assert stored["latest"] == 25.97


def test_a_second_run_adds_nothing_new(tmp_path, monkeypatch):
    monkeypatch.setattr(gvz_feed, "fetch", lambda payload=None: [
        {"date": "2026-11-06", "close": "25.97"}])
    gvz.update_gvz(str(tmp_path))
    second = gvz.update_gvz(str(tmp_path))
    assert second.added == 0
    assert second.rows == 1


def test_a_download_failure_is_reported(tmp_path, monkeypatch):
    def explode(payload=None):
        raise AltError("boom")

    monkeypatch.setattr(gvz_feed, "fetch", explode)
    result = gvz.update_gvz(str(tmp_path))
    assert result.ok is False
    assert "boom" in result.error


def test_an_unwritable_folder_is_reported(tmp_path, monkeypatch):
    blocked = tmp_path / "blocked"
    blocked.write_text("not a folder", encoding="ascii")
    monkeypatch.setattr(gvz_feed, "fetch", lambda payload=None: [
        {"date": "2026-11-06", "close": "25.97"}])
    result = gvz.update_gvz(str(blocked))
    assert result.ok is False
    assert "cannot write" in result.error


def test_status_of_an_empty_directory(tmp_path):
    described = gvz.status(str(tmp_path))
    assert described["rows"] == 0
    assert described["latest"] is None
    assert described["file"].endswith("gvz_daily.csv")


@pytest.mark.parametrize("payload", [b"", b"DATE,GVZ\n"])
def test_parse_of_an_empty_payload_returns_no_rows(payload):
    assert gvz_feed.parse(payload) == []
