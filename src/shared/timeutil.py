"""UTC time helpers: every timestamp in this project is UTC (data and logs)."""

from __future__ import annotations

import datetime as dt

from . import config

_CLI_DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d")


def utc_now() -> dt.datetime:
    """Current time as an aware UTC datetime."""
    return dt.datetime.now(dt.timezone.utc)


def minute_floor(when: dt.datetime) -> dt.datetime:
    """Same instant in UTC with seconds and microseconds dropped."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return when.astimezone(dt.timezone.utc).replace(second=0, microsecond=0)


def utc_now_minute() -> dt.datetime:
    """Current minute, used as the exclusive end of a catch-up run."""
    return minute_floor(utc_now())


def epoch_to_minute(ms: int) -> dt.datetime:
    """unix milliseconds -> aware UTC datetime on a minute boundary."""
    return minute_floor(
        dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc))


def ts_to_text(ms: int) -> str:
    """unix milliseconds -> 'YYYY-MM-DD HH:MM:SS' (UTC)."""
    return epoch_to_minute(ms).strftime(config.TIMESTAMP_FORMAT)


def text_to_ms(raw: str) -> int:
    """'YYYY-MM-DD HH:MM:SS' (UTC) -> unix milliseconds; 0 when unparsable."""
    text = raw.strip()
    if len(text) < config.TIMESTAMP_WIDTH:
        return 0
    try:
        when = dt.datetime.strptime(text[:config.TIMESTAMP_WIDTH],
                                   config.TIMESTAMP_FORMAT)
    except ValueError:
        return 0
    return int(when.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def parse_cli_date(value: str) -> dt.datetime:
    """'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' -> aware UTC datetime.

    Raises ValueError for anything else; the CLI turns that into a usage error.
    """
    text = value.strip()
    for date_format in _CLI_DATE_FORMATS:
        try:
            parsed = dt.datetime.strptime(text, date_format)
        except ValueError:
            continue
        return parsed.replace(tzinfo=dt.timezone.utc)
    raise ValueError(f"invalid date {value!r}, expected YYYY-MM-DD [HH:MM]")
