"""Tests for the real rates command line (no network)."""

from __future__ import annotations

import argparse
import json

import pytest

from src.core import rates
from src.features.cli import rates_app


def test_the_country_argument_parses_codes():
    assert rates_app._country_argument("us, DE") == ["US", "DE"]


def test_the_country_argument_rejects_unknown_codes():
    with pytest.raises(argparse.ArgumentTypeError):
        rates_app._country_argument("XX")


def test_format_country_reports_value_date_and_change():
    text = rates_app.format_country("US", {
        "label": "United States", "last_date": "2026-09-01", "latest": 1.25,
        "change_1y": -0.75})
    assert "US" in text
    assert "2026-09-01" in text
    assert "+1.250" in text
    assert "-0.750" in text


def test_format_country_handles_missing_values():
    text = rates_app.format_country("DE", {"label": "Germany"})
    assert text.count("-") >= 2


def test_format_result_lists_the_countries_and_the_median():
    result = rates.RatesResult(countries={
        "US": {"label": "United States", "last_date": "2026-09-01",
               "latest": 1.25, "change_1y": None},
    }, warnings=("DE: no overlapping months stored",))
    text = rates_app.format_result(result, {"median": 1.25, "count": 1})
    assert "+1 real rate series" in text
    assert "world median +1.250 over 1 countries" in text
    assert "DE: no overlapping months stored" in text


def test_a_failure_formats_as_an_error_line():
    failed = rates.RatesResult(error="FRED is down")
    assert rates_app.format_result(failed, {}).startswith(" ! rates update failed")


def test_format_status_warns_when_nothing_is_stored():
    body = {"countries": {"US": {"rows": 0}}, "world": {"median": None,
                                                        "count": 0}}
    assert "no stored real rates" in rates_app.format_status(body)[0]


def test_main_status_exit_code_follows_the_stored_files(tmp_path, capsys):
    code = rates_app.main(["--data-dir", str(tmp_path), "--status"])
    assert code == 1
    assert "no stored real rates" in capsys.readouterr().out


def test_main_builds_from_a_stored_pair(tmp_path, monkeypatch, capsys):
    from tests.core.test_rates import write_pair

    write_pair(str(tmp_path), "US", [("2026-09-01", "4.00")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    code = rates_app.main(["--data-dir", str(tmp_path), "--country", "US",
                           "--offline"])
    assert code == 0
    printed = capsys.readouterr().out
    assert "US" in printed
    assert "+2.000" in printed


def test_main_json_answer_keeps_the_world_summary(tmp_path, capsys):
    from tests.core.test_rates import write_pair

    write_pair(str(tmp_path), "US", [("2026-09-01", "4.00")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    code = rates_app.main(["--data-dir", str(tmp_path), "--country", "US",
                           "--offline", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["world"]["median"] == 2.0
    assert "points" not in payload["world"]


def test_main_returns_one_when_nothing_was_stored(tmp_path, capsys):
    code = rates_app.main(["--data-dir", str(tmp_path), "--offline",
                           "--quiet"])
    assert code == 1
    assert capsys.readouterr().out == ""


def test_main_reports_a_download_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rates, "update_rates",
                        lambda data_dir, countries=None, refresh=True:
                        rates.RatesResult(error="FRED is down"))
    code = rates_app.main(["--data-dir", str(tmp_path), "--country", "US"])
    assert code == 1
    assert "FRED is down" in capsys.readouterr().out
