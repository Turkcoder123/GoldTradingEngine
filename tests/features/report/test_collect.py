"""Tests for the facts behind the text report (no network, no real data)."""

from __future__ import annotations

import pytest

from src.features.report import collect
from src.shared import config

ROWS = [
    ("2026-11-05 21:58:00", 10, 11, 9, 10.5, 1),
    ("2026-11-05 21:59:00", 10.5, 11, 10, 10.8, 1),
    ("2026-11-06 23:00:00", 11, 12, 10, 11.5, 1),
    ("2026-11-06 23:59:00", 11.5, 12, 11, 11.9, 1),
]
COT_ROWS = [
    ("GOLD - COMMODITY EXCHANGE INC.", "2026-10-27", 1000, 600, 200, 50, 10, 4,
     400),
    ("GOLD - COMMODITY EXCHANGE INC.", "2026-11-03", 1200, 700, 250, 60, 12, 5,
     450),
]


def bulk_rows(count=600):
    """Enough rows for a stored size that is not rounded down to zero."""
    return [("2026-11-06 %02d:%02d:00" % (10 + index // 60, index % 60),
             10, 11, 9, 10.5, 1) for index in range(count)]


def test_prices_cover_every_registered_series(tmp_path):
    rows = collect.prices(str(tmp_path))
    assert [row["key"] for row in rows] == list(config.SERIES)
    assert all(row["files"] == 0 for row in rows)
    assert all(row["bars"] == 0 for row in rows)
    assert all(row["first_bar"] is None for row in rows)
    assert all(row["last_close"] is None for row in rows)


def test_price_row_reports_coverage_and_values(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    row = collect.prices(str(tmp_path))[0]
    assert row["instrument"] == "XAU/USD"
    assert row["frequency"] == "1 min"
    assert row["files"] == 1
    assert row["bars"] == len(ROWS)
    assert row["days"] == 2
    assert row["first_bar"] == "2026-11-05 21:58:00"
    assert row["last_bar"] == "2026-11-06 23:59:00"
    assert row["first_close"] == 10.5
    assert row["last_close"] == 11.9
    assert row["day_change_pct"] == pytest.approx(10.19, abs=0.01)
    assert row["range_change_pct"] == pytest.approx(13.33, abs=0.01)
    assert row["age_minutes"] >= 0
    assert row["size_mb"] >= 0


def test_a_new_registered_series_reaches_the_report(tmp_path, write_month,
                                                    monkeypatch):
    """FLOW-10: the report reads the registry, so it needs no code change."""
    extra = config.Series("xaunok", "XAU/NOK")
    monkeypatch.setitem(config.SERIES, extra.key, extra)
    write_month(tmp_path, "xaunok_1m_2026-11.csv", ROWS)
    rows = collect.prices(str(tmp_path))
    assert rows[-1]["key"] == "xaunok"
    assert rows[-1]["instrument"] == "XAU/NOK"
    assert rows[-1]["bars"] == len(ROWS)


def test_cot_rows_come_from_the_newest_stored_year(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2026, COT_ROWS)
    body = collect.cot_reports(str(tmp_path))
    assert body["year"] == 2026
    assert body["years"] == [2026]
    row = body["rows"][0]
    assert row["report"] == "legacy"
    assert row["frequency"] == "weekly"
    assert row["first_date"] == "2026-10-27"
    assert row["last_date"] == "2026-11-03"
    assert row["reports"] == 2
    assert row["open_interest"] == 1200
    assert row["net"] == 450
    assert row["net_share"] == pytest.approx(0.375, abs=0.001)
    assert row["weekly_change"] == 50


def test_cot_rows_can_be_asked_for_one_year(tmp_path, write_cot):
    write_cot(tmp_path, "legacy", 2025, COT_ROWS)
    write_cot(tmp_path, "legacy", 2026, COT_ROWS)
    assert collect.cot_reports(str(tmp_path), 2025)["year"] == 2025
    assert collect.cot_reports(str(tmp_path), 2020)["rows"] == []
    assert collect.cot_reports(str(tmp_path))["year"] == 2026


def test_macro_rows_carry_unit_frequency_and_coverage(tmp_path, write_fred):
    write_fred(tmp_path, "DGS10", [("2019-01-02", 1.0), ("2026-11-05", 4.84)])
    row = collect.macro(str(tmp_path))[0]
    assert row["id"] == "DGS10"
    assert row["label"] == "10-year Treasury yield"
    assert row["unit"] == "percent"
    assert row["frequency"] == "daily"
    assert row["first_date"] == "2019-01-02"
    assert row["last_date"] == "2026-11-05"
    assert row["observations"] == 2
    assert row["value"] == 4.84
    assert row["change"] == pytest.approx(3.84, abs=0.001)


def test_macro_does_not_count_missing_observations(tmp_path, write_fred):
    write_fred(tmp_path, "DGS10", [("2026-11-03", 4.1), ("2026-11-04", ""),
                                   ("2026-11-05", 4.05)])
    row = collect.macro(str(tmp_path))[0]
    assert row["observations"] == 2
    assert row["last_date"] == "2026-11-05"


def test_macro_skips_a_series_that_is_not_stored(tmp_path, write_fred):
    write_fred(tmp_path, "DGS10", [("2026-11-05", 4.05)])
    assert [row["id"] for row in collect.macro(str(tmp_path))] == ["DGS10"]


def test_totals_add_up_the_price_files(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-10.csv", bulk_rows())
    write_month(tmp_path, "xauusd_1m_2026-11.csv", bulk_rows())
    write_month(tmp_path, "dxy_1m_2026-11.csv", bulk_rows())
    totals = collect.totals(collect.prices(str(tmp_path)))
    assert totals["series"] == 2
    assert totals["files"] == 3
    assert totals["bars"] == 3 * 600
    assert totals["size_mb"] > 0
    assert totals["first_bar"] == "2026-11-06 10:00:00"
    assert totals["last_bar"] == "2026-11-06 19:59:00"


def test_build_gathers_the_three_sections(tmp_path, write_month, write_cot,
                                          write_fred):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    write_cot(tmp_path, "legacy", 2026, COT_ROWS)
    write_fred(tmp_path, "DGS10", [("2026-11-05", 4.84)])
    document = collect.build(str(tmp_path))
    assert document["version"]
    assert document["generated_at"]
    assert document["data_dir"] == str(tmp_path)
    assert document["prices"][0]["key"] == "xauusd"
    assert document["cot"]["year"] == 2026
    assert document["macro"][0]["id"] == "DGS10"
