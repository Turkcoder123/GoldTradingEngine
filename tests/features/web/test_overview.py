"""Tests for the overview cards and the totals of the dashboard."""

from __future__ import annotations

import pytest

from src.features.web import overview
from src.shared import config

ROWS = [
    ("2026-11-05 21:58:00", 10, 11, 9, 10.5, 1),
    ("2026-11-05 21:59:00", 10.5, 11, 10, 10.8, 1),
    ("2026-11-06 23:00:00", 11, 12, 10, 11.5, 1),
    ("2026-11-06 23:59:00", 11.5, 12, 11, 11.9, 1),
]
COT_ROWS = [
    ("GOLD - COMMODITY EXCHANGE INC.", "2026-11-03", 1200, 700, 250, 60, 12, 5,
     450),
]


def bulk_rows(count=600):
    """Enough rows for a stored size that is not rounded down to zero."""
    rows = []
    for index in range(count):
        rows.append(("2026-11-06 %02d:%02d:00" % (10 + index // 60, index % 60),
                     10, 11, 9, 10.5, 1))
    return rows


def test_cards_cover_every_registered_series(tmp_path):
    body = overview.payload(str(tmp_path))
    assert [card["key"] for card in body["series"]] == list(config.SERIES)
    assert all(card["files"] == 0 for card in body["series"])
    assert body["totals"]["series"] == 0
    assert body["totals"]["files"] == 0
    assert body["totals"]["size_mb"] == 0.0
    assert body["totals"]["first_bar"] is None
    assert body["data_dir"] == str(tmp_path)


def test_card_reports_the_stored_range_and_the_last_quotes(tmp_path,
                                                           write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", bulk_rows())
    card = overview.payload(str(tmp_path))["series"][0]
    assert card["instrument"] == "XAU/USD"
    assert card["files"] == 1
    assert card["size_mb"] > 0
    assert card["newest_file"] == "xauusd_1m_2026-11.csv"
    assert card["first_bar"] == "2026-11-06 10:00:00"
    assert card["last_bar"] == "2026-11-06 19:59:00"
    assert card["last_day"] == "2026-11-06"
    assert card["last_close"] == 10.5
    assert card["stale_minutes"] >= 0
    assert card["error"] is None


def test_card_reports_the_day_change(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    card = overview.payload(str(tmp_path))["series"][0]
    assert card["last_close"] == 11.9
    assert card["day_change_pct"] == pytest.approx(10.19, abs=0.01)


def test_totals_add_up_the_stored_files(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-10.csv", bulk_rows())
    write_month(tmp_path, "xauusd_1m_2026-11.csv", bulk_rows())
    write_month(tmp_path, "dxy_1m_2026-11.csv", bulk_rows())
    totals = overview.payload(str(tmp_path))["totals"]
    assert totals["series"] == 2
    assert totals["files"] == 3
    assert totals["size_mb"] > 0


def test_payload_includes_the_macro_and_cot_snapshots(tmp_path, write_cot,
                                                      write_fred):
    write_cot(tmp_path, "legacy", 2026, COT_ROWS)
    write_fred(tmp_path, "DGS10", [("2026-11-05", 4.05)])
    body = overview.payload(str(tmp_path))
    assert body["cot"]["year"] == 2026
    assert body["cot"]["reports"]["legacy"]["net"] == 450
    assert body["macro"][0]["id"] == "DGS10"


def test_payload_includes_the_alternative_sources(tmp_path):
    """`FLOW-10`: the dashboard shows a new data type without code changes."""
    body = overview.payload(str(tmp_path))
    assert [row["key"] for row in body["alt"]["etf"]] == ["gld", "iau"]
    assert body["alt"]["volatility"]["key"] == "GVZ"
    assert body["alt"]["fed"]["rows"] == 0


def test_payload_includes_the_real_rates(tmp_path):
    body = overview.payload(str(tmp_path))
    assert body["rates"]["countries"] == []
    assert body["rates"]["world"]["median"] is None


def test_a_card_reports_an_io_error_instead_of_failing(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise OSError("disk away")

    monkeypatch.setattr(overview.price_view, "month_paths", explode)
    body = overview.payload(str(tmp_path))
    assert body["series"][0]["error"] == "disk away"
    assert body["totals"]["files"] == 0
