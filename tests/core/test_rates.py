"""Tests for the derived real interest rates (no network)."""

from __future__ import annotations


from src.core import fred, rates
from src.shared import config


def write_pair(data_dir, country, yields, cpis):
    """Writes the two FRED series (yield and inflation) of one country."""
    yield_id, cpi_id = rates.series_ids(country)
    fred.write_csv(fred.series_path(data_dir, yield_id),
                   [{"date": date, "value": value} for date, value in yields])
    fred.write_csv(fred.series_path(data_dir, cpi_id),
                   [{"date": date, "value": value} for date, value in cpis])


def test_series_ids_come_from_the_registry():
    assert rates.series_ids("US") == ("IRLTLT01USM156N", "CPIAUCSL")
    assert rates.series_ids("DE") == ("IRLTLT01DEM156N", "CP0000DEM086NEST")


def test_build_series_computes_inflation_from_the_index(tmp_path):
    write_pair(tmp_path, "US",
               [("2026-08-01", "4.20"), ("2026-09-01", "4.10")],
               [("2025-08-01", "100"), ("2025-09-01", "100"),
                ("2026-08-01", "103"), ("2026-09-01", "103")])
    rows = rates.build_series(str(tmp_path), "US")
    assert rows == [{"date": "2026-08-01", "real": "1.200"},
                    {"date": "2026-09-01", "real": "1.100"}]


def test_build_series_keeps_only_the_months_it_can_join(tmp_path):
    write_pair(tmp_path, "DE",
               [("2026-08-01", "2.50"), ("2026-09-01", "2.70")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    rows = rates.build_series(str(tmp_path), "DE")
    assert rows == [{"date": "2026-09-01", "real": "0.700"}]


def test_build_series_collapses_a_daily_yield_to_the_month(tmp_path):
    write_pair(tmp_path, "GB",
               [("2026-09-01", "4.00"), ("2026-09-15", "4.30"),
                ("2026-09-30", "4.20")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    rows = rates.build_series(str(tmp_path), "GB")
    assert rows == [{"date": "2026-09-01", "real": "2.200"}]


def test_build_series_is_empty_when_a_series_is_missing(tmp_path):
    assert rates.build_series(str(tmp_path), "FR") == []


def test_offline_update_writes_one_file_per_country(tmp_path):
    write_pair(tmp_path, "US", [("2026-09-01", "4.00")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    result = rates.update_rates(str(tmp_path), ["US"], refresh=False)
    assert result.ok is True
    assert result.countries["US"]["rows"] == 1
    assert result.countries["US"]["latest"] == 2.0
    assert result.countries["US"]["change_1y"] is None
    assert rates.real_path(str(tmp_path), "US").endswith("real_us.csv")
    stored = rates.status(str(tmp_path))["countries"]["US"]
    assert stored["label"] == "United States"
    assert stored["last_date"] == "2026-09-01"


def test_a_country_without_series_is_a_warning_not_an_error(tmp_path):
    result = rates.update_rates(str(tmp_path), ["US", "DE"], refresh=False)
    assert result.ok is True
    assert result.countries == {}
    assert len(result.warnings) == 2


def test_update_downloads_the_needed_series(tmp_path, monkeypatch):
    calls = {}

    def fake_update(data_dir, series_ids=None):
        calls["ids"] = list(series_ids or [])
        return fred.FredResult(files=(), counts={}, summaries={})

    monkeypatch.setattr(rates.fred, "update_fred", fake_update)
    result = rates.update_rates(str(tmp_path), ["US"])
    assert result.ok is True
    assert calls["ids"] == ["IRLTLT01USM156N", "CPIAUCSL"]


def test_a_download_failure_becomes_a_warning(tmp_path, monkeypatch):
    """One unavailable series must not block the other countries."""
    monkeypatch.setattr(rates.fred, "update_fred",
                        lambda data_dir, series_ids=None: fred.FredResult(
                            error="FRED is down"))
    result = rates.update_rates(str(tmp_path), ["US", "DE"])
    assert result.countries == {}
    assert len(result.warnings) == 2
    assert "FRED is down" in result.warnings[0]


def test_status_builds_the_equal_weighted_median(tmp_path):
    for country, rate in (("US", 2.0), ("DE", 1.0), ("FR", -1.0)):
        write_pair(tmp_path, country, [("2026-09-01", f"{rate + 2:.2f}")],
                   [("2025-09-01", "100"), ("2026-09-01", "102")])
    rates.update_rates(str(tmp_path), ["US", "DE", "FR"], refresh=False)
    body = rates.status(str(tmp_path))
    assert body["world"]["count"] == 3
    assert body["world"]["median"] == 1.0          # median of 2.0, 1.0, -1.0
    assert body["world"]["min"] == -1.0
    assert body["world"]["max"] == 2.0
    assert body["world"]["points"] == [["2026-09-01", 1.0]]


def test_change_against_a_year_earlier():
    rows = [{"date": "2025-09-01", "real": "0.500"},
            {"date": "2026-09-01", "real": "1.250"}]
    assert rates._change_1y(rows) == 0.75
    assert rates._change_1y([]) is None
    assert rates._change_1y([{"date": "2026-09-01", "real": "1.0"}]) is None


def test_a_series_older_than_the_allowance_is_marked_stale():
    assert rates._is_stale(None) is False
    assert rates._is_stale("2026-10-01") is False
    assert rates._is_stale("2025-03-01") is True


def test_an_unwritable_folder_is_reported(tmp_path, monkeypatch):
    blocked = tmp_path / "blocked"
    blocked.write_text("not a folder", encoding="ascii")
    write_pair(str(tmp_path), "US", [("2026-09-01", "4.00")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    monkeypatch.setattr(rates.config, "rates_dir",
                        lambda data_dir: str(blocked / "rates"))
    result = rates.update_rates(str(tmp_path), ["US"], refresh=False)
    assert result.ok is False
    assert "cannot write" in result.error


def test_every_country_has_a_yield_and_an_inflation_series():
    for country, entry in config.RATES_COUNTRIES.items():
        assert entry["yield"], country
        assert entry.get("cpi") or entry.get("cpi_index"), country
        assert entry["label"], country
