"""Tests for the COT payload (stored files only, no network)."""

from __future__ import annotations

from src.features.web import cot_view

LEGACY_ROWS = [
    ("GOLD - COMMODITY EXCHANGE INC.", "2026-10-27", 1000, 600, 200, 50, 10, 4,
     400),
    ("GOLD - COMMODITY EXCHANGE INC.", "2026-11-03", 1200, 700, 250, 60, 12, 5,
     450),
]
DISAGG_ROWS = [
    ("GOLD - COMMODITY EXCHANGE INC.", "2026-11-03", 1200, 700, 250, 60, 12,
     5, 12, 450),
]


def test_payload_returns_the_chart_series(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2026, LEGACY_ROWS)
    body = cot_view.payload(str(tmp_path))
    assert body["year"] == 2026
    assert body["years"] == [2026]
    report = body["reports"]["legacy"]
    assert report["dates"] == ["2026-10-27", "2026-11-03"]
    assert report["net"] == [400, 450]
    assert report["open_interest"] == [1000, 1200]
    assert report["long"] == [600, 700]
    assert report["short"] == [200, 250]
    assert report["summary"]["net"] == 450
    assert report["summary"]["weekly_change"] == 50


def test_payload_keeps_both_reports(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2026, LEGACY_ROWS)
    write_cot(tmp_path, "disagg", 2026, DISAGG_ROWS)
    body = cot_view.payload(str(tmp_path))
    assert sorted(body["reports"]) == ["disagg", "legacy"]
    assert body["reports"]["disagg"]["net"] == [450]


def test_payload_handles_a_year_without_files(tmp_path):
    body = cot_view.payload(str(tmp_path), 2020)
    assert body["year"] == 2020
    assert body["reports"] == {}


def test_payload_uses_the_newest_stored_year_by_default(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2025, LEGACY_ROWS)
    write_cot(tmp_path, "legacy", 2026, LEGACY_ROWS)
    assert cot_view.payload(str(tmp_path))["year"] == 2026


def test_summary_leaves_out_the_chart_series(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2026, LEGACY_ROWS)
    body = cot_view.summary(str(tmp_path))
    assert "dates" not in body["reports"]["legacy"]
    assert body["reports"]["legacy"]["net"] == 450
