"""Tests for the Federal Reserve document source (no network)."""

from __future__ import annotations

import pytest

from src.core import fedtext, fedtext_feed
from src.core.altfeed import AltError

SPEECH_FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>FRB: Speeches</title>
<item><title>Bowman, Test Speech</title>
<link>https://www.federalreserve.gov/newsevents/speech/bowman20261014a.htm</link>
<pubDate>Thu, 15 Oct 2026 02:55:00 GMT</pubDate></item>
</channel></rss>"""
PRESS_FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>FRB: Monetary Policy</title>
<item><title>Minutes of the Federal Open Market Committee, September 15-16, 2026</title>
<link>https://www.federalreserve.gov/newsevents/pressreleases/monetary20261007a.htm</link>
<pubDate>Wed, 7 Oct 2026 18:00:00 GMT</pubDate></item>
</channel></rss>"""
PAGE = (b'<html><body><p>chrome</p><div id="article"><h4>Title</h4>'
        b"<p>Body one.</p><div><p>Body two.</p></div></div>"
        b"<p>footer chrome</p></body></html>")
RELEASE = (b'<html><body><div id="article"><p>See the '
           b'<a href="/monetarypolicy/fomcminutes20260916.htm">minutes</a>'
           b"</p></div></body></html>")


def test_feed_items_read_titles_dates_and_kinds():
    speech = fedtext_feed.feed_items(SPEECH_FEED, "speeches")[0]
    assert speech["date"] == "2026-10-15"
    assert speech["kind"] == "speech"
    assert speech["speaker"] == "Bowman"
    assert speech["url"].endswith("bowman20261014a.htm")
    minutes = fedtext_feed.feed_items(PRESS_FEED, "press_monetary")[0]
    assert minutes["date"] == "2026-10-07"
    assert minutes["kind"] == "minutes_release"
    assert minutes["speaker"] == ""


def test_feed_items_rejects_a_broken_feed():
    with pytest.raises(AltError):
        fedtext_feed.feed_items(b"not xml", "speeches")


def test_feed_items_skips_incomplete_items():
    payload = (b'<rss version="2.0"><channel><item><title>Only a title'
               b"</title></item></channel></rss>")
    assert fedtext_feed.feed_items(payload, "speeches") == []


def test_article_text_keeps_only_the_article_paragraphs():
    assert fedtext_feed.article_text(PAGE) == "Body one.\n\nBody two."


def test_article_text_falls_back_to_the_whole_page():
    text = fedtext_feed.article_text(b"<html><p>Only body</p></html>")
    assert text == "Only body"


def test_minutes_link_builds_an_absolute_url():
    assert fedtext_feed.minutes_link(RELEASE) == (
        "https://www.federalreserve.gov/monetarypolicy/fomcminutes20260916.htm")
    assert fedtext_feed.minutes_link(b"<html></html>") == ""


def test_update_stores_the_index_and_the_texts(tmp_path, monkeypatch):
    pages = {
        "https://www.federalreserve.gov/newsevents/speech/bowman20261014a.htm":
            "Speech body",
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261007a.htm":
            "Release body",
    }
    monkeypatch.setattr(
        fedtext_feed, "fetch_feed",
        lambda feed: fedtext_feed.feed_items(
            SPEECH_FEED if feed == "speeches" else PRESS_FEED, feed))
    monkeypatch.setattr(fedtext_feed, "fetch_text", lambda url: pages[url])
    monkeypatch.setattr(
        fedtext_feed, "fetch_minutes_link",
        lambda url: "https://www.federalreserve.gov/monetarypolicy/fomcminutes20260916.htm")
    monkeypatch.setitem(pages,
                        "https://www.federalreserve.gov/monetarypolicy/fomcminutes20260916.htm",
                        "Minutes body")
    result = fedtext.update_fed(str(tmp_path), limit=10)
    assert result.ok is True
    assert result.added == 3
    assert result.total == 3
    stored = fedtext.status(str(tmp_path))
    assert stored["rows"] == 3
    assert stored["texts"] == 3
    kinds = sorted(row["kind"] for row in
                   fedtext.altstore.read_rows(fedtext.index_path(str(tmp_path))))
    assert kinds == ["minutes", "minutes_release", "speech"]


def test_update_does_not_fetch_a_known_url_twice(tmp_path, monkeypatch):
    calls = []

    def fetch_text(url):
        calls.append(url)
        return "text"

    monkeypatch.setattr(
        fedtext_feed, "fetch_feed",
        lambda feed: fedtext_feed.feed_items(
            SPEECH_FEED if feed == "speeches" else PRESS_FEED, feed))
    monkeypatch.setattr(fedtext_feed, "fetch_text", fetch_text)
    monkeypatch.setattr(fedtext_feed, "fetch_minutes_link", lambda url: "")
    fedtext.update_fed(str(tmp_path), limit=10)
    second = fedtext.update_fed(str(tmp_path), limit=10)
    assert second.added == 0
    assert len(calls) == 2


def test_the_limit_keeps_the_newest_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fedtext_feed, "fetch_feed",
        lambda feed: fedtext_feed.feed_items(
            SPEECH_FEED if feed == "speeches" else PRESS_FEED, feed))
    monkeypatch.setattr(fedtext_feed, "fetch_text", lambda url: "text")
    monkeypatch.setattr(fedtext_feed, "fetch_minutes_link", lambda url: "")
    result = fedtext.update_fed(str(tmp_path), limit=1)
    assert result.added == 1
    rows = fedtext.altstore.read_rows(fedtext.index_path(str(tmp_path)))
    assert rows[0]["date"] == "2026-10-15"


def test_a_feed_failure_is_reported(tmp_path, monkeypatch):
    def explode(feed):
        raise AltError("feed down")

    monkeypatch.setattr(fedtext_feed, "fetch_feed", explode)
    result = fedtext.update_fed(str(tmp_path), limit=1)
    assert result.ok is False
    assert "feed down" in result.error


def test_status_of_an_empty_directory(tmp_path):
    described = fedtext.status(str(tmp_path))
    assert described == {"rows": 0, "first_date": None, "last_date": None,
                         "latest_title": None, "texts": 0}
