"""Tests for the COT command line (no network)."""

import json

import pytest

from src.core import cot
from src.features.cli import cot_app
from src.shared import version


def test_format_summary_reports_net_share_and_changes():
    summary = cot.CotSummary(date="2026-11-03", open_interest=400000,
                             long_positions=220000, short_positions=40000,
                             net=180000, weekly_change=-7000,
                             trend_change=-39000, trend_weeks=6)
    text = cot_app.format_summary("legacy", summary)
    assert "net +180,000 (45.0% of OI)" in text
    assert "week -7,000" in text
    assert "6w -39,000" in text


def test_format_summary_handles_a_report_without_rows():
    assert "no data" in cot_app.format_summary(
        "disagg", cot.CotSummary())


def test_format_result_lists_the_files_and_one_line_per_report():
    result = cot.CotResult(
        year=2026, files=("a.csv",), counts={"a.csv": 44},
        summaries={"legacy": cot.CotSummary(date="2026-11-03", net=179548,
                                            open_interest=399169)})
    lines = cot_app.format_result(result).splitlines()
    assert lines[0].startswith(" +2026 COT gold: a.csv (44 rows)")
    assert len(lines) == 2
    assert "2026-11-03" in lines[1]


def test_format_status_warns_when_nothing_is_stored():
    assert "no stored COT files for 2026" in \
        cot_app.format_status({}, 2026)[0]


def test_format_status_lists_the_stored_reports():
    lines = cot_app.format_status(
        {"legacy": cot.CotSummary(date="2026-11-03", net=1)}, 2026)
    assert lines[0].strip() == "COT 2026 (as stored)"
    assert "2026-11-03" in lines[1]


def test_format_result_reports_a_failure():
    text = cot_app.format_result(cot.CotResult(year=2026, error="boom"))
    assert "COT update failed: boom" in text


def test_version_prints_the_version_file(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cot_app.build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert version.read_version() in capsys.readouterr().out


def test_main_returns_zero_and_prints_the_summary(tmp_path, monkeypatch,
                                                  capsys):
    monkeypatch.setattr(
        cot_app.cot, "update_cot",
        lambda data_dir, year, all_gold=False: cot.CotResult(
            year=year, files=("a.csv",), counts={"a.csv": 2},
            latest="2026-11-03"))
    code = cot_app.main(["--data-dir", str(tmp_path), "--year", "2026"])
    assert code == 0
    assert "a.csv (2 rows)" in capsys.readouterr().out


def test_main_returns_one_on_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        cot_app.cot, "update_cot",
        lambda data_dir, year, all_gold=False: cot.CotResult(
            year=year, error="boom"))
    code = cot_app.main(["--data-dir", str(tmp_path), "--quiet"])
    assert code == 1
    assert "boom" in capsys.readouterr().out


def test_main_can_print_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        cot_app.cot, "update_cot",
        lambda data_dir, year, all_gold=False: cot.CotResult(
            year=year, counts={"a.csv": 2}))
    assert cot_app.main(["--data-dir", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"] == {"a.csv": 2}
    assert payload["ok"] is True
