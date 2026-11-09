"""Tests for the real rates payload of the dashboard (no network)."""

from __future__ import annotations

import os

from src.core import fred, rates
from src.features.web import rates_view
from src.shared import config


def write_pair(data_dir, country, yields, cpis):
    """Writes the yield series and the CPI index series of one country."""
    for series_id, rows in zip(rates.series_ids(country), (yields, cpis)):
        fred.write_csv(fred.series_path(data_dir, series_id),
                       [{"date": date, "value": value} for date, value in rows])


def test_payload_of_an_empty_directory(tmp_path):
    body = rates_view.payload(str(tmp_path))
    assert body["countries"] == []
    assert body["world"]["median"] is None
    assert body["world"]["points"] == []


def test_payload_lists_only_stored_countries(tmp_path):
    write_pair(str(tmp_path), "US", [("2026-09-01", "4.00")],
               [("2025-09-01", "100"), ("2026-09-01", "102")])
    rates.update_rates(str(tmp_path), ["US"], refresh=False)
    body = rates_view.payload(str(tmp_path))
    assert [entry["code"] for entry in body["countries"]] == ["US"]
    assert body["countries"][0]["latest"] == 2.0
    assert body["countries"][0]["date"] == "2026-09-01"
    assert body["world"]["median"] == 2.0
    assert body["world"]["count"] == 1


def test_payload_windows_the_median_history(tmp_path):
    write_pair(str(tmp_path), "US",
               [("2023-09-01", "5.00"), ("2024-09-01", "5.00"),
                ("2025-09-01", "5.00"), ("2026-09-01", "4.00")],
               [("2022-09-01", "100"), ("2023-09-01", "100"),
                ("2024-09-01", "100"), ("2025-09-01", "100"),
                ("2026-09-01", "102")])
    rates.update_rates(str(tmp_path), ["US"], refresh=False)
    world = rates_view.payload(str(tmp_path))["world"]
    dates = [point[0] for point in world["points"]]
    assert dates[-1] == "2026-09-01"
    assert "2023-09-01" not in dates       # older than the two year window
    assert len(dates) == 3
    assert world["points"][-1][1] == 2.0


def test_window_of_no_points_is_empty():
    assert rates_view._window([]) == []


def test_every_registered_country_reports_a_label():
    for country, entry in config.RATES_COUNTRIES.items():
        assert entry["label"] and entry["yield"], country
        assert entry.get("cpi") or entry.get("cpi_index"), country
    assert os.path.basename(rates.real_path("data", "us")) == "real_us.csv"
