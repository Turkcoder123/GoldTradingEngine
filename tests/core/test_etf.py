"""Tests for the ETF sources: SPDR XLSX, iShares page and the CSV store."""

from __future__ import annotations

import io
import zipfile

import pytest

from src.core import etf, etf_feed
from src.core.altfeed import AltError

SHARED = ["Disclaimer text", "Date", "Closing Price", "Daily Share Volume",
          "Tonnes of Gold", "Total Ounces of Gold in the Trust",
          "Total Net Asset Value in the Trust", "02-Jan-2026", "05-Jan-2026"]
HEADER_ROW = ('<row r="1">'
              '<c r="A1" t="s"><v>1</v></c><c r="B1" t="s"><v>2</v></c>'
              '<c r="C1" t="s"><v>3</v></c><c r="D1" t="s"><v>4</v></c>'
              '<c r="E1" t="s"><v>5</v></c><c r="F1" t="s"><v>6</v></c></row>')
FIRST_ROW = ('<row r="2"><c r="A2" t="s"><v>7</v></c><c r="B2"><v>44.38</v></c>'
             '<c r="C2"><v>5992000</v></c><c r="D2"><v>8.09</v></c>'
             '<c r="E2"><v>260000.0</v></c><c r="F2"><v>114920000.0</v></c></row>')
SECOND_ROW = ('<row r="3"><c r="A3" t="s"><v>8</v></c><c r="B3"><v>375.49</v></c>'
              '<c r="C3"><v>12421693</v></c><c r="D3"><v>1040.50999999</v></c>'
              '<c r="E3"><v>33453518.23</v></c><c r="F3"><v>137534762708.8</v></c>'
              '</row>')
IAU_PAGE = ('<html><body><script type="application/json">'
            '{"tonnes":{"visible":true,"label":"Tonnes in Trust",'
            '"formattedValue":"460.81","formattedAsOfDate":"Nov 06, 2026"},'
            '"ounces":{"visible":true,"label":"Ounces in Trust",'
            '"formattedValue":"14,815,410.05",'
            '"formattedAsOfDate":"Nov 06, 2026"}}'
            '</script></body></html>')


def workbook(rows_xml: str) -> bytes:
    """Minimal XLSX shaped like the SPDR archive (disclaimer + data sheet)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook><sheets><sheet name="Disclaimer"/>'
            '<sheet name="US GLD Historical Archive"/></sheets></workbook>')
        archive.writestr(
            "xl/sharedStrings.xml",
            "<sst>" + "".join(f"<si><t>{text}</t></si>"
                              for text in SHARED) + "</sst>")
        archive.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
        archive.writestr("xl/worksheets/sheet2.xml",
                         f"<worksheet>{rows_xml}</worksheet>")
    return buffer.getvalue()


def test_parse_spdr_reads_the_named_columns():
    rows = etf_feed.parse_spdr(workbook(HEADER_ROW + FIRST_ROW + SECOND_ROW))
    assert [row["date"] for row in rows] == ["2026-01-02", "2026-01-05"]
    assert rows[0] == {"date": "2026-01-02", "close": "44.38",
                       "volume": "5992000", "tonnes": "8.09",
                       "ounces": "260000.00", "nav": "114920000.00"}
    assert rows[-1]["tonnes"] == "1040.51"


def test_parse_spdr_rejects_a_workbook_without_a_header():
    with pytest.raises(AltError):
        etf_feed.parse_spdr(workbook('<row r="1"><c r="A1"><v>1</v></c></row>'))


def test_parse_spdr_rejects_something_that_is_not_a_zip():
    with pytest.raises(AltError):
        etf_feed.parse_spdr(b"not a workbook")


def test_parse_ishares_reads_the_tonnage_snapshot():
    snapshot = etf_feed.parse_ishares(IAU_PAGE.encode("utf-8"))
    assert snapshot == {"date": "2026-11-06", "tonnes": "460.81",
                        "ounces": "14815410.05"}


def test_parse_ishares_reports_a_page_without_tonnage():
    with pytest.raises(AltError):
        etf_feed.parse_ishares(b"<html><body>nothing</body></html>")


def test_update_stores_both_funds(tmp_path, monkeypatch):
    monkeypatch.setattr(etf_feed, "fetch_gld", lambda: [
        {"date": "2026-11-05", "close": "375.49", "volume": "1",
         "tonnes": "1040.51", "ounces": "33453518.23", "nav": "1"}])
    monkeypatch.setattr(etf_feed, "fetch_iau_tonnes", lambda: {
        "date": "2026-11-06", "tonnes": "460.81", "ounces": "14815410.05"})
    result = etf.update_etf(str(tmp_path))
    assert result.ok is True
    assert result.series["gld"]["rows"] == 1
    assert result.series["gld"]["latest"] == 1040.51
    assert result.series["iau"]["latest"] == 460.81
    assert etf.status(str(tmp_path))["iau"]["rows"] == 1


def test_update_can_be_limited_to_one_fund(tmp_path, monkeypatch):
    monkeypatch.setattr(etf_feed, "fetch_gld", lambda: [])
    monkeypatch.setattr(etf_feed, "fetch_iau_tonnes", lambda: {
        "date": "2026-11-06", "tonnes": "460.81", "ounces": ""})
    result = etf.update_etf(str(tmp_path), ["iau"])
    assert list(result.series) == ["iau"]
    assert not (tmp_path / "alt" / "etf_gld_daily.csv").exists()


def test_a_download_failure_is_reported(tmp_path, monkeypatch):
    def explode():
        raise AltError("blocked")

    monkeypatch.setattr(etf_feed, "fetch_gld", explode)
    result = etf.update_etf(str(tmp_path), ["gld"])
    assert result.ok is False
    assert "gld: blocked" in result.error


def test_status_of_an_empty_directory(tmp_path):
    described = etf.status(str(tmp_path))
    assert sorted(described) == ["gld", "iau"]
    assert described["gld"]["rows"] == 0
    assert described["gld"]["latest"] is None
