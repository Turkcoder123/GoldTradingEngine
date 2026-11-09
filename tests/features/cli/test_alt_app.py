"""Tests for the alternative sources command line (no network)."""

from __future__ import annotations

import argparse
import json

import pytest

from src.core import etf, fedtext, gvz
from src.features.cli import alt_app


def test_parser_accepts_the_documented_options():
    args = alt_app.build_parser().parse_args(
        ["--source", "gvz", "--source", "fed", "--limit", "3", "--quiet"])
    assert args.source == ["gvz", "fed"]
    assert args.limit == 3
    assert args.quiet is True
    assert args.etf is None


def test_the_etf_argument_parses_fund_keys():
    assert alt_app._etf_argument("gld, IAU") == ["gld", "iau"]


def test_the_etf_argument_rejects_unknown_funds():
    with pytest.raises(argparse.ArgumentTypeError):
        alt_app._etf_argument("spy")


def test_format_gvz_reports_coverage_and_the_latest_close():
    result = gvz.GvzResult(file="gvz_daily.csv", rows=4309, added=1,
                           first_date="2009-09-18", last_date="2026-11-06",
                           latest=25.97)
    text = alt_app.format_gvz(result)
    assert "gvz_daily.csv" in text
    assert "4,309 rows" in text
    assert "25.97" in text


def test_format_etf_lists_every_fund():
    result = etf.EtfResult(series={
        "gld": {"file": "etf_gld_daily.csv", "rows": 5730, "latest": 1040.51,
                "first_date": "2004-11-18", "last_date": "2026-11-05"},
        "iau": {"file": "etf_iau_daily.csv", "rows": 1, "latest": 460.81,
                "first_date": "2026-11-06", "last_date": "2026-11-06"},
    })
    text = alt_app.format_etf(result)
    assert "+2 ETF series" in text
    assert "1,040.51" in text
    assert "460.81" in text


def test_format_fed_reports_the_added_documents():
    result = fedtext.FedResult(file="fed_documents.csv", added=2, total=6,
                               latest="2026-10-28")
    text = alt_app.format_fed(result)
    assert "+2 documents" in text
    assert "6 stored" in text


def test_a_failure_formats_as_an_error_line():
    failed = gvz.GvzResult(error="boom")
    assert alt_app.format_gvz(failed).startswith(" ! GVZ update failed")


def test_status_is_read_from_the_data_directory(tmp_path, capsys):
    code = alt_app.main(["--data-dir", str(tmp_path), "--status"])
    assert code == 1
    printed = capsys.readouterr().out
    assert "alternative sources" in printed


def test_main_runs_the_requested_source(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gvz, "update_gvz", lambda data_dir: gvz.GvzResult(
        file="gvz_daily.csv", rows=2, added=2, first_date="2026-11-05",
        last_date="2026-11-06", latest=25.97))
    code = alt_app.main(["--data-dir", str(tmp_path), "--source", "gvz"])
    assert code == 0
    assert "GVZ" not in capsys.readouterr().out  # the line names the index


def test_main_json_output_is_machine_readable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fedtext, "update_fed",
                        lambda data_dir, limit: fedtext.FedResult(
                            file="fed_documents.csv", added=1, total=1,
                            latest="2026-10-28"))
    code = alt_app.main(["--data-dir", str(tmp_path), "--source", "fed",
                         "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fed"]["ok"] is True
    assert payload["fed"]["added"] == 1


def test_main_returns_one_when_a_source_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(etf, "update_etf",
                        lambda data_dir, keys=None: etf.EtfResult(error="boom"))
    assert alt_app.main(["--data-dir", str(tmp_path),
                         "--source", "etf"]) == 1


def test_quiet_silences_a_successful_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gvz, "update_gvz", lambda data_dir: gvz.GvzResult(
        file="gvz_daily.csv", rows=1))
    assert alt_app.main(["--data-dir", str(tmp_path), "--source", "gvz",
                         "--quiet"]) == 0
    assert capsys.readouterr().out == ""
