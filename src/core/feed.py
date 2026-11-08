"""Dukascopy 1-minute bar client: the only module that uses the network."""

from __future__ import annotations

import json
import random
import string
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from typing import Iterator

from ..shared import config


class FeedError(RuntimeError):
    """Raised when the feed keeps failing; the caller reports it."""


@dataclass(frozen=True)
class FeedSettings:
    """How the feed is asked: instrument, side, page size, retries, timeout."""

    side: str = config.DEFAULT_SIDE
    limit: int = config.PAGE_LIMIT
    retries: int = config.DEFAULT_RETRIES
    timeout: float = config.DEFAULT_TIMEOUT_SECONDS
    instrument: str = config.INSTRUMENT


def _random_jsonp() -> str:
    """Random JSONP callback name, as the web service expects."""
    alphabet = string.ascii_letters + string.digits
    return config.JSONP_PREFIX + "".join(
        random.choices(alphabet, k=config.JSONP_LENGTH))


def unwrap_jsonp(text: str) -> str:
    """'callback([...]);' -> '[...]'; plain JSON is returned unchanged."""
    body = text.strip()
    start = body.find("(")
    end = body.rfind(")")
    if start == -1 or end < start:
        return body
    return body[start + 1:end].strip()


def parse_payload(text: str) -> list:
    """Decode a response body into the list of bars the service sent."""
    try:
        data = json.loads(unwrap_jsonp(text))
    except ValueError as exc:
        raise FeedError(f"unreadable feed payload: {exc}") from exc
    if isinstance(data, dict):
        data = data.get("updated") or data.get("data") or []
    if not isinstance(data, list):
        raise FeedError("unexpected feed payload: not a list of bars")
    return data


def request_url(start_ms: int, settings: FeedSettings) -> str:
    """Full URL of one page request starting at `start_ms` (inclusive)."""
    params = {
        "path": "chart/json3",
        "splits": "true",
        "stocks": "true",
        "time_direction": "N",
        "jsonp": _random_jsonp(),
        "last_update": str(int(start_ms)),
        "offer_side": settings.side,
        "instrument": settings.instrument,
        "interval": config.INTERVAL,
        "limit": str(int(settings.limit)),
    }
    return config.BASE_URL + "?" + urllib.parse.urlencode(params)


def usable_rows(rows: list, settings: FeedSettings) -> list:
    """Keeps bars with real prices; a symbol without quotes is an error."""
    kept = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        try:
            [float(value) for value in row[1:5]]
        except (TypeError, ValueError):
            continue
        kept.append(row)
    if rows and not kept:
        raise FeedError(
            f"instrument {settings.instrument!r} returned no prices"
            " (check the Dukascopy symbol)")
    return kept


def fetch_page(start_ms: int, settings: FeedSettings) -> list:
    """One page of bars from `start_ms`; raises FeedError on failure."""
    url = request_url(start_ms, settings)
    attempts = max(int(settings.retries), 1)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url, headers=config.REQUEST_HEADERS)
            with urllib.request.urlopen(
                    request, timeout=settings.timeout) as response:
                return usable_rows(parse_payload(
                    response.read().decode("utf-8", "replace")), settings)
        except (OSError, FeedError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                delay = min(config.RETRY_BACKOFF_SECONDS ** attempt,
                            config.RETRY_BACKOFF_CAP_SECONDS)
                time.sleep(delay)
    raise FeedError(
        f"dukascopy request failed after {attempts} attempt(s): {last_error}")


def fetch_range(start, end, settings: FeedSettings) -> Iterator[list]:
    """Yields every 1m bar in [start, end), paging through the feed."""
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    window = replace(settings, limit=min(
        settings.limit, max(2, (end_ms - start_ms) // config.MINUTE_MS + 1)))
    cursor = start_ms
    seen: set = set()
    while cursor < end_ms:
        rows = fetch_page(cursor, window)
        if not rows:
            return
        highest = cursor
        for row in rows:
            stamp = int(row[0])
            if stamp < start_ms or stamp >= end_ms:
                continue
            highest = max(highest, stamp)
            if stamp in seen:
                continue
            seen.add(stamp)
            yield row
        if highest <= cursor:            # the page held nothing new
            return
        cursor = highest
        if end_ms - highest <= config.MINUTE_MS:
            return               # the window is covered, ask for nothing more
        if len(rows) < 2:                # the feed has reached the end
            return
        time.sleep(config.PAGE_PAUSE_SECONDS)
