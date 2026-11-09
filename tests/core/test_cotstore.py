"""Tests for the stored COT file layout (paths and years, no network)."""

from __future__ import annotations

import os

from src.core import cotstore


def test_report_path_follows_the_export_names(tmp_path):
    path = cotstore.report_path(str(tmp_path), "legacy", 2026)
    assert os.path.basename(path) == "cot_legacy_gold_2026.csv"
    assert os.path.dirname(path) == os.path.join(str(tmp_path), "cot")


def test_stored_years_lists_the_stored_reports(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2025, [])
    write_cot(tmp_path, "disagg", 2026, [])
    assert cotstore.stored_years(str(tmp_path)) == [2026, 2025]


def test_stored_years_is_empty_without_a_cot_folder(tmp_path):
    assert cotstore.stored_years(str(tmp_path)) == []
    assert cotstore.newest_year(str(tmp_path)) is None


def test_stored_years_ignores_files_that_carry_no_year(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2026, [])
    target = tmp_path / "cot"
    (target / "notes.csv").write_text("x\n", encoding="ascii")
    assert cotstore.stored_years(str(tmp_path)) == [2026]


def test_newest_year_reports_the_latest_stored_year(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2025, [])
    write_cot(tmp_path, "legacy", 2026, [])
    assert cotstore.newest_year(str(tmp_path)) == 2026
