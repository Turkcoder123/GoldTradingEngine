"""Tests for the CFTC COT client. No test touches the real network."""

import csv
import io
import zipfile

import pytest

from src.core import cot, cot_feed
from src.shared import config

LEGACY_HEADER = [
    "Market and Exchange Names",
    "As of Date in Form YYYY-MM-DD",
    "Open Interest (All)",
    "Noncommercial Positions-Long (All)",
    "Noncommercial Positions-Short (All)",
    "Noncommercial Positions-Spreading (All)",
    "Traders-Noncommercial-Long (All)",
    "Traders-Noncommercial-Short (All)",
]
DISAGG_HEADER = [
    "Market_and_Exchange_Names",
    "Report_Date_as_YYYY-MM-DD",
    "Open_Interest_All",
    "M_Money_Positions_Long_All",
    "M_Money_Positions_Short_All",
    "Prod_Merc_Positions_Long_All",
    "Prod_Merc_Positions_Short_All",
    "Swap_Positions_Long_All",
    "Swap__Positions_Short_All",
]
LEGACY_ROWS = [
    [config.COT_GOLD_MARKET, "2026-11-03", "399169", "220530", "40982",
     "5000", "200", "80"],
    [config.COT_GOLD_MARKET, "2026-10-27", "396810", "223724", "37273",
     "5100", "210", "70"],
    ["MICRO GOLD - COMMODITY EXCHANGE INC.", "2026-11-03", "70000",
     "50000", "10000", "10", "5", "4"],
    ["SILVER - COMMODITY EXCHANGE INC.", "2026-11-03", "1", "2", "3",
     "4", "5", "6"],
]
DISAGG_ROWS = [
    [config.COT_GOLD_MARKET, "2026-11-03", "399169", "122283", "18669",
     "1000", "2000", "3000", "4000"],
    [config.COT_GOLD_MARKET, "2026-10-27", "396810", "122508", "16946",
     "1100", "2100", "3100", "4100"],
]


def make_zip(header, rows, member="deacot2026.txt"):
    """Builds an archive shaped like a CFTC download."""
    buffer = io.BytesIO()
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(header)
    writer.writerows(rows)
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, text.getvalue())
    return buffer.getvalue()


def gold_rows(header=LEGACY_HEADER, rows=LEGACY_ROWS, report="legacy",
              exact=config.COT_GOLD_MARKET):
    """Rows of the archive filtered and reshaped like the client does."""
    parsed = cot.read_rows(make_zip(header, rows))
    columns = (cot_feed.LEGACY_COLUMNS if report == "legacy"
               else cot_feed.DISAGG_COLUMNS)
    return cot.select_gold(parsed, config.COT_MARKET_COLUMNS[report],
                           columns, exact=exact)


def test_read_rows_returns_every_row_as_a_dict():
    rows = cot.read_rows(make_zip(LEGACY_HEADER, LEGACY_ROWS))
    assert len(rows) == 4
    assert rows[0]["Market and Exchange Names"] == config.COT_GOLD_MARKET


def test_read_rows_rejects_a_broken_archive():
    with pytest.raises(cot.CotError):
        cot.read_rows(b"not a zip at all")


def test_read_rows_rejects_an_archive_without_a_text_file():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("payload.bin", b"x")
    with pytest.raises(cot.CotError):
        cot.read_rows(buffer.getvalue())


def test_select_gold_keeps_only_the_exact_market_oldest_first():
    picked = gold_rows()
    assert [row["date"] for row in picked] == ["2026-10-27", "2026-11-03"]
    assert all(row["market"] == config.COT_GOLD_MARKET for row in picked)
    assert picked[-1]["noncomm_long"] == "220530"


def test_select_gold_can_keep_every_gold_market():
    picked = gold_rows(exact=None)
    assert len(picked) == 3
    markets = {row["market"] for row in picked}
    assert "MICRO GOLD - COMMODITY EXCHANGE INC." in markets
    assert "SILVER - COMMODITY EXCHANGE INC." not in markets


def test_add_net_computes_long_minus_short():
    picked = gold_rows()
    cot.add_net(picked, "noncomm_long", "noncomm_short")
    assert picked[-1]["net"] == str(220530 - 40982)


def test_write_csv_creates_the_directory(tmp_path):
    picked = gold_rows()
    path = tmp_path / "cot" / "legacy.csv"
    assert cot.write_csv(str(path), picked) == 2
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("market,date,open_interest,noncomm_long")


def test_update_cot_reports_a_download_failure(tmp_path, monkeypatch):
    def fail(name):
        raise cot.CotError("network down")

    monkeypatch.setattr(cot, "download", fail)
    result = cot.update_cot(str(tmp_path), 2026)
    assert result.ok is False
    assert "network down" in result.error
    assert result.files == ()


def test_update_cot_reports_a_missing_column(tmp_path, monkeypatch):
    broken_header = [name for name in LEGACY_HEADER
                     if name != "Noncommercial Positions-Short (All)"]
    payload = make_zip(broken_header,
                       [row[:-1] for row in LEGACY_ROWS])
    monkeypatch.setattr(cot, "download", lambda name: payload)
    result = cot.update_cot(str(tmp_path), 2026)
    assert result.ok is False
    assert "Noncommercial Positions-Short (All)" in result.error


def test_summarize_reads_the_latest_report_and_its_changes():
    rows = [{"date": "2026-01-06", "open_interest": "100", "a": "10",
             "b": "4"},
            {"date": "2026-01-13", "open_interest": "200", "a": "30",
             "b": "5"},
            {"date": "2026-01-20", "open_interest": "400", "a": "50",
             "b": "10"}]
    summary = cot.summarize(rows, "a", "b", weeks=2)
    assert summary.date == "2026-01-20"
    assert (summary.long_positions, summary.short_positions) == (50, 10)
    assert summary.net == 40
    assert summary.weekly_change == 15
    assert summary.trend_change == 34
    assert summary.trend_weeks == 2
    assert round(summary.net_share, 3) == 0.1


def test_summarize_returns_an_empty_summary_for_no_rows():
    summary = cot.summarize([], "a", "b")
    assert summary.date is None
    assert summary.net_share == 0.0
    assert summary.to_dict()["net_share"] == 0.0


def test_status_reads_the_stored_files(tmp_path):
    target = tmp_path / "cot"
    target.mkdir()
    path = target / "cot_legacy_gold_2026.csv"
    path.write_text(
        "market,date,open_interest,noncomm_long,noncomm_short,net\n"
        "GOLD,2026-11-03,1000,600,200,400\n", encoding="utf-8")
    reports = cot.status(str(tmp_path), 2026)
    assert list(reports) == ["legacy"]
    assert reports["legacy"].net == 400


def test_status_skips_a_missing_year(tmp_path):
    assert cot.status(str(tmp_path), 1999) == {}


def test_update_cot_writes_both_reports(tmp_path, monkeypatch):
    payloads = {
        "deacot2026": make_zip(LEGACY_HEADER, LEGACY_ROWS),
        "fut_disagg_txt_2026": make_zip(DISAGG_HEADER, DISAGG_ROWS,
                                       member="fut_disagg_txt_2026.txt"),
    }
    monkeypatch.setattr(cot, "download", lambda name: payloads[name])
    result = cot.update_cot(str(tmp_path), 2026)
    assert result.ok is True
    assert result.counts == {"cot_legacy_gold_2026.csv": 2,
                             "cot_disagg_gold_2026.csv": 2}
    assert result.latest == "2026-11-03"
    assert sorted(result.files) == ["cot_disagg_gold_2026.csv",
                                    "cot_legacy_gold_2026.csv"]
    assert (tmp_path / "cot" / "cot_legacy_gold_2026.csv").exists()
