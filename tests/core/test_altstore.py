"""Tests for the CSV store shared by the alternative series."""

from __future__ import annotations

from src.core import altstore
from src.shared import config

FIELDS = ("date", "close")


def test_series_path_lives_under_the_alt_folder(tmp_path):
    path = altstore.series_path(str(tmp_path), "gvz_daily")
    assert path == str(tmp_path / "alt" / "gvz_daily.csv")


def test_read_rows_is_empty_for_a_missing_file(tmp_path):
    assert altstore.read_rows(str(tmp_path / "missing.csv")) == []


def test_write_and_read_keep_the_field_order(tmp_path):
    path = altstore.series_path(str(tmp_path), "gvz_daily")
    rows = [{"date": "2026-11-05", "close": "24.11"},
            {"date": "2026-11-06", "close": "25.97"}]
    assert altstore.write_rows(path, rows, FIELDS) == 2
    assert altstore.read_rows(path) == rows
    header = open(path, encoding=config.ENCODING).readline().strip()
    assert header == "date,close"


def test_write_rows_of_nothing_writes_nothing(tmp_path):
    path = altstore.series_path(str(tmp_path), "gvz_daily")
    assert altstore.write_rows(path, [], FIELDS) == 0
    assert not (tmp_path / "alt" / "gvz_daily.csv").exists()


def test_merge_series_sorts_and_lets_the_fresh_row_win():
    stored = [{"date": "2026-11-05", "close": "24.11"},
              {"date": "2026-11-06", "close": "0.00"}]
    fresh = [{"date": "2026-11-04", "close": "23.00"},
             {"date": "2026-11-06", "close": "25.97"}]
    merged = altstore.merge_series(stored, fresh, FIELDS)
    assert [row["date"] for row in merged] == ["2026-11-04", "2026-11-05",
                                               "2026-11-06"]
    assert merged[-1]["close"] == "25.97"


def test_merge_series_drops_rows_without_a_date():
    merged = altstore.merge_series([{"close": "1"}],
                                   [{"date": "2026-11-06", "close": "2"}],
                                   FIELDS)
    assert merged == [{"date": "2026-11-06", "close": "2"}]


def test_merge_documents_keys_on_the_url_and_sorts_by_date():
    fields = ("date", "kind", "title", "speaker", "url", "chars")
    stored = [{"date": "2026-10-15", "kind": "speech", "title": "A",
               "speaker": "Bowman", "url": "u1", "chars": "100"}]
    fresh = [{"date": "2026-10-07", "kind": "statement", "title": "B",
              "speaker": "", "url": "u2", "chars": "50"},
             {"date": "2026-10-15", "kind": "speech", "title": "A",
              "speaker": "Bowman", "url": "u1", "chars": "120"}]
    merged = altstore.merge_documents(stored, fresh, fields)
    assert [row["url"] for row in merged] == ["u2", "u1"]
    assert merged[-1]["chars"] == "120"


def test_merge_documents_fills_missing_cells():
    fields = ("date", "url", "chars")
    merged = altstore.merge_documents([], [{"date": "2026-11-06",
                                            "url": "u1"}], fields)
    assert merged == [{"date": "2026-11-06", "url": "u1", "chars": ""}]


def test_describe_reports_coverage_and_the_latest_value():
    rows = [{"date": "2026-11-05", "close": "24.11"},
            {"date": "2026-11-06", "close": "25.97"}]
    described = altstore.describe(rows)
    assert described == {"rows": 2, "first_date": "2026-11-05",
                         "last_date": "2026-11-06", "latest": 25.97}


def test_describe_handles_empty_and_unreadable_values():
    assert altstore.describe([])["rows"] == 0
    described = altstore.describe([{"date": "2026-11-06", "close": ""}])
    assert described["latest"] is None
