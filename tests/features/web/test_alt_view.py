"""Tests for the alternative sources payload of the dashboard (no network)."""

from __future__ import annotations

import os

from src.features.web import alt_view
from src.shared import config

ETF_HEADER = "date,close,volume,tonnes,ounces,nav"


def write_rows(folder: str, name: str, header: str, rows: list) -> None:
    """Writes one stored CSV of the alternative sources."""
    target = os.path.join(folder, name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding=config.ENCODING, newline="") as handle:
        handle.write(header + "\n")
        for row in rows:
            handle.write(",".join(str(value) for value in row) + "\n")


def test_payload_of_an_empty_directory(tmp_path):
    body = alt_view.payload(str(tmp_path))
    assert [row["key"] for row in body["etf"]] == ["gld", "iau"]
    assert all(row["rows"] == 0 for row in body["etf"])
    assert all(row["points"] == [] for row in body["etf"])
    assert body["volatility"]["key"] == "GVZ"
    assert body["volatility"]["points"] == []
    assert body["fed"]["rows"] == 0
    assert body["fed"]["documents"] == []


def test_etf_payload_windows_the_tonnage(tmp_path):
    write_rows(str(tmp_path / "alt"), "etf_gld_daily.csv", ETF_HEADER, [
        ("2024-01-02", 180.0, 1, "900.00", "1", "1"),
        ("2025-11-05", 370.0, 1, "1000.00", "1", "1"),
        ("2026-11-05", 375.5, 1, "1040.51", "1", "1"),
    ])
    gld = alt_view.payload(str(tmp_path))["etf"][0]
    assert gld["rows"] == 3
    assert gld["tonnes"] == 1040.51
    assert [point[0] for point in gld["points"]] == ["2025-11-05", "2026-11-05"]
    assert gld["change_pct"] == 4.05


def test_etf_payload_skips_rows_without_tonnage(tmp_path):
    write_rows(str(tmp_path / "alt"), "etf_iau_daily.csv", ETF_HEADER, [
        ("2026-11-06", "", "", "460.81", "14815410.05", ""),
        ("2026-11-07", "", "", "", "", ""),
    ])
    iau = alt_view.payload(str(tmp_path))["etf"][1]
    assert iau["tonnes"] == 460.81
    assert [point[0] for point in iau["points"]] == ["2026-11-06"]
    assert iau["change_pct"] is None


def test_volatility_payload_windows_the_close(tmp_path):
    write_rows(str(tmp_path / "alt"), "gvz_daily.csv", "date,close", [
        ("2020-01-02", "14.00"),
        ("2025-11-06", "17.63"),
        ("2026-11-06", "25.97"),
    ])
    volatility = alt_view.payload(str(tmp_path))["volatility"]
    assert volatility["rows"] == 3
    assert volatility["close"] == 25.97
    assert [point[0] for point in volatility["points"]] == ["2025-11-06",
                                                            "2026-11-06"]
    assert volatility["change_pct"] == 47.31


def test_fed_payload_returns_the_newest_documents_first(tmp_path):
    rows = [(f"2026-10-{day:02d}", "speech", f"Title {day}", "Bowman",
             f"https://example/{day}", "100") for day in range(1, 13)]
    write_rows(str(tmp_path / "alt"), "fed_documents.csv",
               "date,kind,title,speaker,url,chars", rows)
    fed = alt_view.payload(str(tmp_path))["fed"]
    assert fed["rows"] == 12
    assert len(fed["documents"]) == alt_view.DOCUMENTS
    assert fed["documents"][0]["date"] == "2026-10-12"
    assert fed["documents"][-1]["date"] == "2026-10-03"
    assert fed["chars"] == 1200
    assert fed["kinds"] == {"speech": 12}


def test_change_of_a_single_point_is_unknown(tmp_path):
    assert alt_view._change([["2026-11-06", 25.97]]) is None
    assert alt_view._change([]) is None
