"""Tests for the FRED module. No test touches the real network."""

import pytest

from src.core import fred, fred_feed
from src.shared import config

SAMPLE = """observation_date,DGS10
2026-11-03,4.10
2026-11-04,.
2026-11-05,4.05
"""


def test_parse_rows_normalises_missing_values():
    rows = fred_feed.parse_rows(SAMPLE)
    assert rows[1] == {"date": "2026-11-04", "value": ""}
    assert rows[-1] == {"date": "2026-11-05", "value": "4.05"}


def test_parse_rows_rejects_a_payload_without_observation_header():
    with pytest.raises(fred_feed.FredError):
        fred_feed.parse_rows("<html>error</html>")


def test_parse_rows_rejects_an_empty_series():
    with pytest.raises(fred_feed.FredError):
        fred_feed.parse_rows("observation_date,DGS10\n")


def test_numeric_points_skips_missing_values():
    points = fred_feed.numeric_points(fred_feed.parse_rows(SAMPLE))
    assert points == [("2026-11-03", 4.10), ("2026-11-05", 4.05)]


def test_summarize_reports_the_latest_value_and_changes():
    rows = [{"date": "2025-11-05", "value": "4.50"},
            {"date": "2026-11-03", "value": "4.20"},
            {"date": "2026-11-05", "value": "4.05"}]
    summary = fred.summarize("DGS10", rows)
    assert summary.date == "2026-11-05"
    assert summary.value == 4.05
    assert round(summary.change, 2) == -0.15
    assert round(summary.year_change, 2) == -0.45
    assert summary.observations == 3


def test_summarize_returns_an_empty_summary_without_numbers():
    summary = fred.summarize("DGS10", [{"date": "2026-11-05", "value": ""}])
    assert summary.value is None
    assert summary.observations == 1
    assert summary.to_dict()["series_id"] == "DGS10"


def test_write_and_read_round_trip(tmp_path):
    path = tmp_path / "fred" / "DGS10.csv"
    rows = fred_feed.parse_rows(SAMPLE)
    assert fred.write_csv(str(path), rows) == 3
    assert fred.read_stored(str(path)) == rows


def test_update_fred_reports_a_download_failure(tmp_path, monkeypatch):
    def fail(series_id):
        raise fred_feed.FredError("network down")

    monkeypatch.setattr(fred, "download", fail)
    result = fred.update_fred(str(tmp_path), ["DGS10"])
    assert result.ok is False
    assert "network down" in result.error


def test_update_fred_stores_every_requested_series(tmp_path, monkeypatch):
    monkeypatch.setattr(fred, "download", lambda series_id: SAMPLE)
    result = fred.update_fred(str(tmp_path), ["DGS10", "DFII10"])
    assert result.ok is True
    assert sorted(result.files) == ["DFII10.csv", "DGS10.csv"]
    assert result.counts["DGS10.csv"] == 3
    assert result.summaries["DGS10"].value == 4.05
    assert (tmp_path / "fred" / "DFII10.csv").exists()


def test_status_reads_the_stored_series(tmp_path, monkeypatch):
    monkeypatch.setattr(fred, "download", lambda series_id: SAMPLE)
    fred.update_fred(str(tmp_path), ["DGS10"])
    summaries = fred.status(str(tmp_path), ["DGS10", "DGS2"])
    assert list(summaries) == ["DGS10"]
    assert summaries["DGS10"].value == 4.05


def test_api_key_prefers_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(config.FRED_API_KEY_ENV, "  env-key  ")
    monkeypatch.setattr(config, "FRED_API_KEY_FILE", str(tmp_path / "missing"))
    assert fred_feed.api_key() == "env-key"


def test_api_key_reads_the_secret_file(monkeypatch, tmp_path):
    path = tmp_path / "fred_api_key"
    path.write_text("file-key\n", encoding="utf-8")
    monkeypatch.delenv(config.FRED_API_KEY_ENV, raising=False)
    monkeypatch.setattr(config, "FRED_API_KEY_FILE", str(path))
    assert fred_feed.api_key() == "file-key"


def test_api_key_is_none_without_a_key(monkeypatch, tmp_path):
    monkeypatch.delenv(config.FRED_API_KEY_ENV, raising=False)
    monkeypatch.setattr(config, "FRED_API_KEY_FILE", str(tmp_path / "missing"))
    assert fred_feed.api_key() is None


def test_download_uses_the_api_when_a_key_exists(monkeypatch):
    urls = []
    monkeypatch.setattr(fred_feed, "api_key", lambda: "secret-key")
    monkeypatch.setattr(fred_feed, "_fetch",
                        lambda url, series_id: urls.append(url) or "")
    fred_feed.download("DGS10")
    assert urls[0].startswith(config.FRED_API_URL)
    assert "api_key=secret-key" in urls[0]


def test_download_falls_back_to_the_keyless_endpoint(monkeypatch):
    urls = []
    monkeypatch.setattr(fred_feed, "api_key", lambda: None)
    monkeypatch.setattr(fred_feed, "_fetch",
                        lambda url, series_id: urls.append(url) or "")
    fred_feed.download("DGS10")
    assert urls[0] == config.FRED_BASE_URL.format(series="DGS10")


def test_parse_rows_reads_an_api_payload():
    payload = ('{"observations": [{"date": "2026-11-04", "value": "."},'
               ' {"date": "2026-11-05", "value": "4.05"}]}')
    assert fred_feed.parse_rows(payload) == [
        {"date": "2026-11-04", "value": ""},
        {"date": "2026-11-05", "value": "4.05"}]


def test_error_text_redacts_the_api_key(monkeypatch):
    monkeypatch.setattr(fred_feed, "api_key", lambda: "secret-key")
    text = fred_feed._describe(OSError("failed for secret-key"))
    assert "secret-key" not in text
    assert "***" in text


def test_status_ignores_a_missing_series(tmp_path):
    assert fred.status(str(tmp_path), ["DGS2"]) == {}
