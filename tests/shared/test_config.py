"""Tests for the shared constants and path helpers."""

import datetime as dt
import glob
import os
import pathlib

import pytest

from src.shared import config

_DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"


def test_month_path_keeps_the_plain_name_for_the_bid_side(tmp_path):
    when = dt.datetime(2026, 11, 6, tzinfo=dt.timezone.utc)
    path = config.month_path(str(tmp_path), when, config.SIDE_BID)
    assert os.path.basename(path) == "xauusd_1m_2026-11.csv"


def test_month_path_marks_ask_files_separately(tmp_path):
    when = dt.datetime(2026, 11, 6, tzinfo=dt.timezone.utc)
    path = config.month_path(str(tmp_path), when, config.SIDE_ASK)
    assert os.path.basename(path) == "xauusd_1m_ask_2026-11.csv"


def test_data_file_pattern_never_matches_the_other_side(tmp_path):
    for name in ("xauusd_1m_2026-11.csv", "xauusd_1m_ask_2026-11.csv"):
        (tmp_path / name).write_text("", encoding=config.ENCODING)
    bid = [os.path.basename(path) for path in
           glob.glob(config.data_file_pattern(str(tmp_path), config.SIDE_BID))]
    ask = [os.path.basename(path) for path in
           glob.glob(config.data_file_pattern(str(tmp_path), config.SIDE_ASK))]
    assert bid == ["xauusd_1m_2026-11.csv"]
    assert ask == ["xauusd_1m_ask_2026-11.csv"]


def test_series_registry_maps_keys_to_instruments_and_prefixes():
    assert config.resolve_series("xauusd").instrument == "XAU/USD"
    assert config.resolve_series("DXY").instrument == "DOLLAR.IDX/USD"
    assert config.resolve_series(None).key == config.DEFAULT_SERIES
    assert config.resolve_series("dxy").prefix == "dxy_1m"


def test_every_series_owns_its_files_and_symbol():
    for key, series in config.SERIES.items():
        assert series.key == key
        assert series.instrument
        assert series.prefix == f"{key}_1m"
    prefixes = [series.prefix for series in config.SERIES.values()]
    assert len(prefixes) == len(set(prefixes))


def test_the_gold_complex_is_registered():
    expected = {"xauusd", "xagusd", "xaueur", "xaugbp", "xauchf", "xauaud",
                "xaujpy", "dxy"}
    assert expected <= set(config.SERIES)


def test_resolve_series_rejects_unknown_keys():
    with pytest.raises(ValueError):
        config.resolve_series("spx")


def test_month_path_uses_the_series_prefix(tmp_path):
    when = dt.datetime(2026, 11, 6, tzinfo=dt.timezone.utc)
    path = config.month_path(str(tmp_path), when, config.SIDE_BID, "dxy_1m")
    assert os.path.basename(path) == "dxy_1m_2026-11.csv"


def test_data_file_pattern_keeps_series_apart(tmp_path):
    for name in ("xauusd_1m_2026-11.csv", "dxy_1m_2026-11.csv",
                 "dxy_1m_ask_2026-11.csv"):
        (tmp_path / name).write_text("", encoding=config.ENCODING)
    dxy = [os.path.basename(path) for path in
           glob.glob(config.data_file_pattern(str(tmp_path), config.SIDE_BID,
                                              "dxy_1m"))]
    assert dxy == ["dxy_1m_2026-11.csv"]


def test_normalize_side_accepts_aliases():
    assert config.normalize_side("b") == config.SIDE_BID
    assert config.normalize_side("BID") == config.SIDE_BID
    assert config.normalize_side(" ask ") == config.SIDE_ASK


def test_normalize_side_rejects_unknown_values():
    with pytest.raises(ValueError):
        config.normalize_side("mid")


def test_resolve_data_dir_prefers_the_explicit_value(monkeypatch, tmp_path):
    monkeypatch.setenv(config.DATA_DIR_ENV, str(tmp_path / "from-env"))
    assert config.resolve_data_dir("/explicit") == "/explicit"


def test_resolve_data_dir_falls_back_to_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(config.DATA_DIR_ENV, str(tmp_path / "from-env"))
    assert config.resolve_data_dir(None) == str(tmp_path / "from-env")


def test_resolve_data_dir_falls_back_to_the_project_default(monkeypatch):
    monkeypatch.delenv(config.DATA_DIR_ENV, raising=False)
    assert config.resolve_data_dir(None) == config.DEFAULT_DATA_DIR


def test_lock_path_uses_the_data_dir_unless_overridden(monkeypatch, tmp_path):
    monkeypatch.delenv(config.LOCK_DIR_ENV, raising=False)
    expected = os.path.join(str(tmp_path), config.LOCK_NAME)
    assert config.lock_path(str(tmp_path)) == expected
    override = os.path.join(str(tmp_path), "locks")
    assert config.lock_path(str(tmp_path), override) == os.path.join(
        override, config.LOCK_NAME)


def test_every_price_series_is_listed_in_the_data_guide():
    """`FLOW-10`: a new data type also reaches the documentation."""
    text = (_DOCS / "data.md").read_text(encoding="utf-8")
    for key in config.SERIES:
        assert key in text, key


def test_every_macro_series_is_listed_in_the_macro_guide():
    """`FLOW-10`: a new macro series also reaches its guide."""
    text = (_DOCS / "macro.md").read_text(encoding="utf-8")
    for series_id in config.FRED_SERIES:
        assert series_id in text, series_id


def test_the_fred_detail_registry_covers_every_series():
    """The report reads unit and frequency from this registry, so it must match."""
    assert set(config.FRED_SERIES_DETAIL) == set(config.FRED_SERIES)


def test_every_etf_fund_is_listed_in_the_alternative_guide():
    """`FLOW-10`: a new fund also reaches its guide."""
    text = (_DOCS / "alternative.md").read_text(encoding="utf-8")
    for key, entry in config.ETF_SERIES.items():
        assert key in text, key
        assert entry["label"] in text, key


def test_every_volatility_series_is_listed_in_the_alternative_guide():
    text = (_DOCS / "alternative.md").read_text(encoding="utf-8")
    for key, entry in config.VOLATILITY_SERIES.items():
        assert key in text, key
        assert entry["url"] in text, key


def test_every_fed_feed_is_listed_in_the_alternative_guide():
    text = (_DOCS / "alternative.md").read_text(encoding="utf-8")
    for name, url in config.FED_FEEDS.items():
        assert url in text, name


def test_every_rate_country_is_listed_in_the_rates_guide():
    """`FLOW-10`: a new country also reaches its guide."""
    text = (_DOCS / "rates.md").read_text(encoding="utf-8")
    for code, entry in config.RATES_COUNTRIES.items():
        assert code in text, code
        assert entry["yield"] in text, code
        inflation = entry.get("cpi") or entry["cpi_index"]
        assert inflation in text, code


def test_the_alternative_files_are_named_once():
    """Every stored series owns its file, so two sources cannot collide."""
    files = [entry["file"] for entry in config.ETF_SERIES.values()]
    files += [entry["file"] for entry in config.VOLATILITY_SERIES.values()]
    assert len(files) == len(set(files))
