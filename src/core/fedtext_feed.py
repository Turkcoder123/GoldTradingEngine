"""Federal Reserve documents: the RSS feeds and the text of one page.

The Board publishes its speeches and monetary policy releases as RSS, so the
list of documents needs no scraping; only the body text is read from the page,
paragraph by paragraph, with the standard library parser.
"""

from __future__ import annotations

import email.utils
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from ..shared import config
from .altfeed import AltError, download

_MINUTES_LINK = re.compile(r"/monetarypolicy/fomcminutes\d+\.htm")
# Site chrome that appears on every Board page and belongs in no document.
_CHROME = (
    "An official website of the United States Government",
    "Secure .gov websites use HTTPS",
    "The Federal Reserve, the central bank of the United States",
    "A .gov website belongs to an official government organization",
    "Last Update:",
    "20th Street and Constitution Avenue N.W.",
)


class _Article(HTMLParser):
    """Paragraphs inside the page's <div id="article">, chrome excluded."""

    def __init__(self, whole_page: bool = False):
        super().__init__(convert_charrefs=True)
        self._depth = 1 if whole_page else 0
        self._inside = whole_page
        self._in_paragraph = False
        self._current = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "div":
            if self._inside:
                self._depth += 1
            elif attributes.get("id") == "article":
                self._inside = True
                self._depth = 1
        elif tag == "p" and self._inside:
            self._in_paragraph = True
            self._current = []

    def handle_endtag(self, tag):
        if tag == "div" and self._inside:
            self._depth -= 1
            if self._depth <= 0:
                self._inside = False
        elif tag == "p" and self._in_paragraph:
            self._in_paragraph = False
            text = re.sub(r"\s+", " ", "".join(self._current)).strip()
            if text:
                self.blocks.append(text)

    def handle_data(self, data):
        if self._in_paragraph:
            self._current.append(data)


def feed_items(payload: bytes, feed: str) -> list:
    """Documents of one RSS feed, newest first, without their text."""
    try:
        root = ET.fromstring(payload.decode("utf-8-sig"))
    except ET.ParseError as exc:
        raise AltError(f"unreadable feed {feed}: {exc}") from exc
    documents = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        date = _iso_date(item.findtext("pubDate") or "")
        if not (title and url and date):
            continue
        documents.append({
            "date": date,
            "kind": _kind(feed, title),
            "title": title,
            "speaker": _speaker(title, feed),
            "url": url,
        })
    return documents


def article_text(payload: bytes) -> str:
    """Body text of one Board page, one paragraph per line.

    Pages carry their content in `<div id="article">`; a page without that block
    falls back to every paragraph, minus the site chrome.
    """
    parser = _Article()
    parser.feed(payload.decode("utf-8", "replace"))
    blocks = parser.blocks
    if not blocks:
        blocks = [block for block in _all_paragraphs(payload)
                  if not block.startswith(_CHROME)]
    return "\n\n".join(block for block in blocks
                       if not block.startswith(_CHROME))


def _all_paragraphs(payload: bytes) -> list:
    """Every paragraph of a page, ignoring where it sits."""
    parser = _Article(whole_page=True)
    parser.feed(payload.decode("utf-8", "replace"))
    return parser.blocks


def minutes_link(payload: bytes) -> str:
    """Absolute URL of the minutes document a release points at, or empty."""
    match = _MINUTES_LINK.search(payload.decode("utf-8", "replace"))
    return "https://www.federalreserve.gov" + match.group(0) if match else ""


def fetch_feed(feed: str) -> list:
    """Documents of one configured feed."""
    return feed_items(download(config.FED_FEEDS[feed]), feed)


def fetch_text(url: str) -> str:
    """Body text of one document URL."""
    return article_text(download(url))


def fetch_minutes_link(url: str) -> str:
    """Minutes document linked from a release page, or empty."""
    return minutes_link(download(url))


def _iso_date(text: str) -> str:
    """RFC 822 feed date -> ISO date; empty when unparsable."""
    try:
        return email.utils.parsedate_to_datetime(text.strip()).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _kind(feed: str, title: str) -> str:
    """Document kind: minutes release, statement or speech."""
    if feed == "speeches":
        return "speech"
    if "minutes" in title.lower():
        return "minutes_release"
    return "statement"


def _speaker(title: str, feed: str) -> str:
    """Speaker of a speech ('Bowman, Supervisory ...' -> 'Bowman')."""
    if feed != "speeches" or "," not in title:
        return ""
    return title.split(",", 1)[0].strip()
