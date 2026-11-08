"""FRED download and parsing: the only macro module that uses the network.

Two transports, one payload shape:
  * official API (`api.stlouisfed.org`) when a key is configured, JSON;
  * keyless plot endpoint (`fredgraph.csv`) otherwise, CSV.
The key is read from `$FRED_API_KEY` or `secrets/fred_api_key` and never
appears in a message: error text is redacted (`_describe`). FRED marks a
missing observation with a single dot, which is normalised to an empty value.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request

from ..shared import config


class FredError(RuntimeError):
    """Raised when a series cannot be downloaded or does not parse."""


def api_key() -> str | None:
    """Key from $FRED_API_KEY, else from secrets/fred_api_key, else None."""
    from_env = os.environ.get(config.FRED_API_KEY_ENV, "").strip()
    if from_env:
        return from_env
    try:
        with open(config.FRED_API_KEY_FILE, "r",
                  encoding=config.ENCODING) as handle:
            from_file = handle.read().strip()
    except OSError:                       # no key file is a normal state
        return None
    return from_file or None


def _describe(exc: OSError) -> str:
    """Error text with the api key removed, so a log never leaks it."""
    text = f"{type(exc).__name__}: {exc}"
    key = api_key()
    return text.replace(key, "***") if key else text


def _fetch(url: str, series_id: str) -> str:
    """GET with retries; a stalled request is retried with a growing pause."""
    attempts = max(int(config.FRED_RETRIES), 1)
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(
                    url, timeout=config.FRED_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", "replace")
        except OSError as exc:
            last_error = _describe(exc)
            if attempt < attempts:
                time.sleep(config.FRED_RETRY_BACKOFF_SECONDS * attempt)
    raise FredError(f"cannot download {series_id} after {attempts} "
                    f"attempt(s): {last_error}")


def download(series_id: str) -> str:
    """Observations of one series, through the API when a key is available.

    The keyless host stalls for minutes when a request pretends to be a
    browser, hence no browser user agent is sent on that path.
    """
    key = api_key()
    if not key:
        return _fetch(config.FRED_BASE_URL.format(series=series_id), series_id)
    query = urllib.parse.urlencode(
        {"series_id": series_id, "api_key": key, "file_type": "json"})
    return _fetch(f"{config.FRED_API_URL}?{query}", series_id)


def _csv_rows(text: str) -> list:
    """Rows of the keyless endpoint: observation_date,<series id>."""
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 2 or "date" not in header[0].lower():
        raise FredError("unexpected download: no observation header")
    rows = []
    for record in reader:
        if len(record) < 2 or not record[0].strip():
            continue
        raw = record[1].strip()
        rows.append({"date": record[0].strip(),
                     "value": "" if raw in (".", "") else raw})
    return rows


def _json_rows(text: str) -> list:
    """Rows of the API payload: {'observations': [{'date', 'value'}, ...]}."""
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise FredError(f"unreadable API payload: {exc}") from exc
    observations = (payload.get("observations")
                    if isinstance(payload, dict) else None)
    if not isinstance(observations, list):
        raise FredError("the API returned no observations")
    rows = []
    for item in observations:
        date = str(item.get("date") or "").strip()
        raw = item.get("value")
        if not date:
            continue
        rows.append({"date": date,
                     "value": "" if raw in (".", "", None) else str(raw)})
    return rows


def parse_rows(text: str) -> list:
    """Rows as {'date': 'YYYY-MM-DD', 'value': '4.06' or ''}, oldest first."""
    is_json = text.lstrip().startswith("{")
    rows = _json_rows(text) if is_json else _csv_rows(text)
    if not rows:
        raise FredError("the series returned no observations")
    rows.sort(key=lambda item: item["date"])
    return rows


def numeric_points(rows: list) -> list:
    """(date, value) pairs of the rows that carry a number, oldest first."""
    points = []
    for row in rows:
        try:
            points.append((row["date"], float(row["value"])))
        except (KeyError, TypeError, ValueError):
            continue
    return points
