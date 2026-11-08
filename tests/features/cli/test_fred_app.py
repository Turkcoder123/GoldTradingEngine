"""Tests for the FRED command line (no network)."""

import argparse
import json

import pytest

from src.core import fred
from src.features.cli import fred_app


def test_series_argument_parses_a_comma_separated_list():
    assert fred_app._series_argument(" dgs10 , DFII10 ") == ["DGS10", "DFII10"]


def test_series_argument_rejects_unknown_ids():
    with pytest.raises(argparse.ArgumentTypeError):
        fred_app._series_argument("NOPE")


def test_format_summary_reports_value_and_changes():
    summary = fred.FredSummary(series_id="DGS10", date="2026-11-05",
                               value=4.05, change=-0.15, year_change=-0.45,
                               observations=10)
    text = fred_app.format_summary("DGS10", summary)
    assert "4.050" in text
    assert "change -0.150" in text
    assert "1y -0.450" in text
    assert "10-year Treasury yield" in text


def test_format_summary_handles_a_series_without_numbers():
    summary = fred.FredSummary(series_id="DGS10")
    assert "no observations" in fred_app.format_summary("DGS10", summary)


def test_format_status_warns_when_nothing_is_stored():
    assert "no stored FRED series" in fred_app.format_status({})[0]


def test_main_status_json_is_machine_readable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        fred_app.fred, "status",
        lambda data_dir, series_ids: {
            "DGS10": fred.FredSummary(series_id="DGS10", date="2026-11-05",
                                      value=4.05)})
    code = fred_app.main(["--data-dir", str(tmp_path), "--status", "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["DGS10"]["value"] == 4.05


def test_main_updates_and_reports(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        fred_app.fred, "update_fred",
        lambda data_dir, series_ids=None: fred.FredResult(
            files=("DGS10.csv",), counts={"DGS10.csv": 3},
            summaries={"DGS10": fred.FredSummary(series_id="DGS10",
                                                 date="2026-11-05",
                                                 value=4.05)}))
    code = fred_app.main(["--data-dir", str(tmp_path)])
    assert code == 0
    assert "+1 FRED series (3 observations)" in capsys.readouterr().out


def test_main_returns_one_on_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        fred_app.fred, "update_fred",
        lambda data_dir, series_ids=None: fred.FredResult(error="boom"))
    code = fred_app.main(["--data-dir", str(tmp_path), "--quiet"])
    assert code == 1
    assert "boom" in capsys.readouterr().out
