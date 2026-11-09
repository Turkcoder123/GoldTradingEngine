"""Parsing of the Twelve Data price stream: one text frame to one usable tick.

Two event types share the socket: `status` events about the subscription itself
and `price` events with the tick. Only a price event of the configured symbol
that carries a usable number becomes a tick; anything else answers None so the
client can count it instead of failing (CODE-3 keeps the count visible).
"""

from __future__ import annotations

import json
from typing import NamedTuple

from . import live_params


class Tick(NamedTuple):
    """One accepted live tick: the symbol, its UTC epoch and the quote side."""

    symbol: str
    timestamp_ms: int
    price: float


def decode(text):
    """The frame as a dict, or None when it is not a JSON object."""
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def timestamp_ms(value) -> int:
    """Provider timestamp in epoch milliseconds; seconds are scaled up.

    Raises ValueError for anything that is not a number, so the caller can
    treat it as an unusable frame instead of guessing a time.
    """
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("unusable timestamp") from exc
    if number <= 0:
        raise ValueError("unusable timestamp")
    if number > live_params.SECONDS_LIMIT:
        return int(number)
    return int(number * live_params.MS_PER_SECOND)


def _price(raw):
    """A positive price, or None when the field is missing or unusable."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def tick(message, side: str, symbol: str = live_params.SYMBOL):
    """One tick of a price event, or None for a status event or a bad frame."""
    if not isinstance(message, dict):
        return None
    if message.get("event") != live_params.PRICE_EVENT:
        return None
    received = str(message.get("symbol") or "").strip().upper()
    if received != symbol.upper():
        return None
    try:
        stamp = timestamp_ms(message.get("timestamp"))
    except ValueError:
        return None
    for field in live_params.SIDE_FIELDS[side]:
        price = _price(message.get(field))
        if price is not None:
            return Tick(received, stamp, price)
    return None


def subscribe_payload(symbol: str = live_params.SYMBOL,
                      action: str = live_params.SUBSCRIBE_ACTION) -> str:
    """The subscribe (or unsubscribe) frame the provider expects, as JSON."""
    return json.dumps({"action": action, "params": {"symbols": symbol}})


def heartbeat_payload() -> str:
    """The heartbeat frame that keeps the socket open."""
    return json.dumps({"action": live_params.HEARTBEAT_ACTION})
