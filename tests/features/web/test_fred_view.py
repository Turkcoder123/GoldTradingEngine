"""Tests for the macro payload (stored files only, no network)."""

from __future__ import annotations

from src.features.web import fred_view

POINTS = [("2019-01-02", 1.0), ("2025-01-02", 2.0), ("2026-11-05", 2.6)]


def test_payload_slices_the_display_window(tmp_path, write_fred):
    write_fred(tmp_path, "DFII10", POINTS)
    body = fred_view.payload(str(tmp_path), years=2)
    serie = body["series"][0]
    assert serie["id"] == "DFII10"
    assert serie["label"] == "10-year TIPS real yield"
    assert [point[0] for point in serie["points"]] == ["2025-01-02",
                                                       "2026-11-05"]
    assert serie["summary"]["value"] == 2.6
    assert serie["summary"]["observations"] == 3


def test_payload_keeps_the_whole_history_when_years_is_zero(tmp_path,
                                                            write_fred):
    write_fred(tmp_path, "DFII10", POINTS)
    body = fred_view.payload(str(tmp_path), years=0)
    assert len(body["series"][0]["points"]) == 3


def test_payload_skips_a_series_that_is_not_stored(tmp_path, write_fred):
    write_fred(tmp_path, "DGS10", [("2026-11-05", 4.05)])
    body = fred_view.payload(str(tmp_path))
    assert [serie["id"] for serie in body["series"]] == ["DGS10"]


def test_payload_reports_no_series_for_an_empty_folder(tmp_path):
    body = fred_view.payload(str(tmp_path))
    assert body["series"] == []
    assert body["years"] == fred_view.DEFAULT_YEARS


def test_summary_has_no_chart_points(tmp_path, write_fred):
    write_fred(tmp_path, "DGS10", [("2026-11-05", 4.05)])
    entries = fred_view.summary(str(tmp_path))
    assert entries[0]["label"] == "10-year Treasury yield"
    assert "points" not in entries[0]
    assert entries[0]["value"] == 4.05


def test_window_skips_missing_observations(tmp_path, write_fred):
    write_fred(tmp_path, "DGS10", [("2026-11-03", 4.1), ("2026-11-04", ""),
                                   ("2026-11-05", 4.05)])
    body = fred_view.payload(str(tmp_path))
    assert [point[0] for point in body["series"][0]["points"]] == [
        "2026-11-03", "2026-11-05"]
