"""Federal Reserve documents: an index CSV plus one text file per document.

The feed gives the list; every new document is fetched once, its body text is
written next to the index and the index row records the URL and the text size,
so a later NLP pass never downloads the same page twice.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from ..shared import config
from . import altstore, fedtext_feed
from .altfeed import AltError

_INDEX = "fed_documents"
_TEXT_SUBDIR = "fed_text"
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class FedResult:
    """What one update stored, so the CLI can report it (CODE-3)."""

    file: str = ""
    added: int = 0
    total: int = 0
    latest: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when the index was written without an error."""
        return self.error is None


def index_path(data_dir: str) -> str:
    """Index of the stored documents."""
    return altstore.series_path(data_dir, _INDEX)


def text_dir(data_dir: str) -> str:
    """Folder of the stored document texts."""
    return os.path.join(config.alt_dir(data_dir), _TEXT_SUBDIR)


def _slug(url: str) -> str:
    """File name of one document: the page name, stripped to safe characters."""
    stem = os.path.basename(url).rsplit(".", 1)[0].lower()
    return _SLUG.sub("_", stem).strip("_") or "document"


def _write_text(data_dir: str, url: str, text: str) -> None:
    """Stores one document text; OSError reaches the caller."""
    folder = text_dir(data_dir)
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, _slug(url) + ".txt")
    with open(target, "w", encoding=config.ENCODING, newline="\n") as handle:
        handle.write(text.rstrip("\n") + "\n")


def _documents(data_dir: str, limit: int) -> list:
    """Newest documents that are not stored yet, at most `limit` of them."""
    known = {row.get("url") for row in altstore.read_rows(index_path(data_dir))}
    seen, fresh = set(), []
    for feed in config.FED_FEEDS:
        for document in fedtext_feed.fetch_feed(feed):
            if document["url"] in known or document["url"] in seen:
                continue
            seen.add(document["url"])
            fresh.append(document)
    fresh.sort(key=lambda document: (document["date"], document["url"]),
               reverse=True)
    return fresh[:limit]


def update_fed(data_dir: str,
               limit: int = config.ALT_LIMIT_DOCUMENTS) -> FedResult:
    """Fetches the newest documents and merges them into the stored index."""
    target = index_path(data_dir)
    stored = altstore.read_rows(target)
    try:
        documents = _documents(data_dir, max(0, int(limit)))
    except AltError as exc:
        return FedResult(file=os.path.basename(target), total=len(stored),
                         error=str(exc))
    fresh = []
    try:
        for document in documents:
            fresh.append(_store(data_dir, document))
            extra = _minutes_document(data_dir, document)
            if extra:
                fresh.append(extra)
        merged = altstore.merge_documents(stored, fresh, config.FED_FIELDS)
        altstore.write_rows(target, merged, config.FED_FIELDS)
    except AltError as exc:
        return FedResult(file=os.path.basename(target), total=len(stored),
                         error=str(exc))
    except OSError as exc:
        return FedResult(file=os.path.basename(target), total=len(stored),
                         error=f"cannot write {target}: {exc}")
    return FedResult(file=os.path.basename(target), added=len(fresh),
                     total=len(merged),
                     latest=merged[-1]["date"] if merged else None)


def _store(data_dir: str, document: dict) -> dict:
    """Fetches one document, stores its text and returns the index row."""
    text = fedtext_feed.fetch_text(document["url"])
    _write_text(data_dir, document["url"], text)
    return dict(document, chars=str(len(text)))


def _minutes_document(data_dir: str, document: dict):
    """The minutes text a release links to, stored as its own document."""
    if document["kind"] != "minutes_release":
        return None
    link = fedtext_feed.fetch_minutes_link(document["url"])
    if not link:
        return None
    return _store(data_dir, {"date": document["date"], "kind": "minutes",
                             "title": document["title"], "speaker": "",
                             "url": link})


def status(data_dir: str) -> dict:
    """Stored documents: count, coverage and the latest entry, offline."""
    rows = altstore.read_rows(index_path(data_dir))
    if not rows:
        return {"rows": 0, "first_date": None, "last_date": None,
                "latest_title": None, "texts": 0}
    folder = text_dir(data_dir)
    texts = len(os.listdir(folder)) if os.path.isdir(folder) else 0
    return {
        "rows": len(rows),
        "first_date": rows[0].get("date"),
        "last_date": rows[-1].get("date"),
        "latest_title": rows[-1].get("title"),
        "texts": texts,
    }
