"""Tests for the Dukascopy client. No test touches the real network."""

import datetime as dt

import pytest

from src.core import feed
from src.shared import config

START = dt.datetime(2026, 11, 6, 21, 55, tzinfo=dt.timezone.utc)
START_MS = int(START.timestamp() * 1000)


class FakeResponse:
    """Minimal stand-in for the object urlopen() returns."""

    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self.body.encode("utf-8")


def test_unwrap_jsonp_extracts_the_payload():
    assert feed.unwrap_jsonp('cb123([1,2]);') == "[1,2]"


def test_unwrap_jsonp_keeps_plain_json():
    assert feed.unwrap_jsonp(' [{"a": 1}] ') == '[{"a": 1}]'


def test_unwrap_jsonp_tolerates_whitespace_after_the_wrapper():
    assert feed.unwrap_jsonp('cb([1]);\n') == "[1]"


def test_parse_payload_reads_a_bar_list():
    assert feed.parse_payload('cb([[1,2,3,4,5,6]]);') == [[1, 2, 3, 4, 5, 6]]


def test_parse_payload_reads_the_updated_key():
    payload = '{"updated": [[1,2,3,4,5,6]]}'
    assert feed.parse_payload(payload) == [[1, 2, 3, 4, 5, 6]]


def test_parse_payload_rejects_broken_json():
    with pytest.raises(feed.FeedError):
        feed.parse_payload("not json at all")


def test_parse_payload_rejects_a_non_list_payload():
    with pytest.raises(feed.FeedError):
        feed.parse_payload('{"updated": "nope"}')


def test_request_url_carries_every_documented_parameter():
    settings = feed.FeedSettings(side=config.SIDE_ASK, limit=5)
    url = feed.request_url(START_MS, settings)
    assert "instrument=XAU%2FUSD" in url
    assert "interval=1MIN" in url
    assert "offer_side=A" in url
    assert "limit=5" in url
    assert f"last_update={START_MS}" in url


def test_fetch_page_returns_parsed_rows(monkeypatch):
    body = f'cb([[{START_MS},1,2,0.5,1.5,7]]);'
    monkeypatch.setattr(
        feed.urllib.request, "urlopen",
        lambda request, timeout=None: FakeResponse(body))
    rows = feed.fetch_page(START_MS, feed.FeedSettings(retries=1))
    assert rows == [[START_MS, 1, 2, 0.5, 1.5, 7]]


def test_fetch_page_raises_feed_error_after_the_last_attempt(monkeypatch):
    def explode(request, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(feed.urllib.request, "urlopen", explode)
    with pytest.raises(feed.FeedError):
        feed.fetch_page(START_MS, feed.FeedSettings(retries=1))


def test_fetch_range_pages_until_the_end_of_the_window(monkeypatch):
    end = START + dt.timedelta(minutes=5)

    def fake_fetch_page(cursor, settings):
        offset = (cursor - START_MS) // config.MINUTE_MS
        if offset >= 5:
            return []
        return [[START_MS + (offset + step) * config.MINUTE_MS, 1, 1, 1, 1, 1]
                for step in range(2)]

    monkeypatch.setattr(feed, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(feed.time, "sleep", lambda seconds: None)
    rows = feed.fetch_range(START, end, feed.FeedSettings())
    stamps = [int(row[0]) for row in rows]
    assert stamps == sorted(set(stamps))
    assert len(stamps) == 5
    assert stamps[0] == START_MS
    assert stamps[-1] == START_MS + 4 * config.MINUTE_MS


def test_fetch_range_covers_a_window_in_one_request(monkeypatch):
    end = START + dt.timedelta(minutes=5)
    calls = []

    def fake_fetch_page(cursor, settings):
        calls.append((cursor, settings.limit))
        offset = (cursor - START_MS) // config.MINUTE_MS
        return [[START_MS + (offset + step) * config.MINUTE_MS, 1, 1, 1, 1, 1]
                for step in range(5 - offset)]

    monkeypatch.setattr(feed, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(feed.time, "sleep", lambda seconds: None)
    rows = list(feed.fetch_range(START, end, feed.FeedSettings()))
    assert len(rows) == 5
    assert len(calls) == 1
    assert calls[0][1] == 6


def test_fetch_range_returns_when_the_page_is_empty(monkeypatch):
    monkeypatch.setattr(feed, "fetch_page", lambda cursor, settings: [])
    rows = list(feed.fetch_range(START, START + dt.timedelta(hours=1),
                                 feed.FeedSettings()))
    assert rows == []


def test_usable_rows_drops_null_bars():
    rows = [[1, 1, 2, 0.5, 1.5, 7], [None], [2, None, None, None, None, 1]]
    settings = feed.FeedSettings(instrument="XAU/USD")
    assert feed.usable_rows(rows, settings) == [[1, 1, 2, 0.5, 1.5, 7]]


def test_usable_rows_rejects_a_symbol_without_prices():
    settings = feed.FeedSettings(instrument="NOT_A_SYMBOL")
    with pytest.raises(feed.FeedError) as error:
        feed.usable_rows([None], settings)
    assert "NOT_A_SYMBOL" in str(error.value)


def test_request_url_uses_the_configured_instrument():
    settings = feed.FeedSettings(instrument="DOLLAR.IDX/USD")
    url = feed.request_url(START_MS, settings)
    assert "instrument=DOLLAR.IDX%2FUSD" in url
