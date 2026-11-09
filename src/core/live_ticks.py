"""Parsing of the SiftingIO stream: one text frame to one usable tick.

Every server frame carries an `f` discriminator: `tick` frames carry prices,
`ack` and `pong` answer control operations, and `error` reports a rejected one.
Only a tick of a configured symbol with a usable price becomes a Tick; anything
else is reported so the client can count it instead of failing (CODE-3).
"""

from __future__ import annotations

import json
from typing import NamedTuple

from . import live_params


class Tick(NamedTuple):
    """One accepted tick: the series it belongs to, its symbol, time and price."""

    series: str
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


def _number(raw):
    """A positive price, or None when the field is missing or unusable."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _timestamp(raw):
    """Provider epoch milliseconds; the provider already uses milliseconds."""
    try:
        stamp = int(float(raw))
    except (TypeError, ValueError):
        return None
    return stamp if stamp > 0 else None


def tick_frame(message, side: str, series: str, symbol: str):
    """One tick of a tick frame, or None for another frame or symbol."""
    if not isinstance(message, dict):
        return None
    if message.get("f") != live_params.FRAME_TICK:
        return None
    if str(message.get("s") or "").strip().upper() != symbol.upper():
        return None
    stamp = _timestamp(message.get("t"))
    if stamp is None:
        return None
    for field in live_params.SIDE_FIELDS[side]:
        price = _number(message.get(field))
        if price is not None:
            return Tick(series, symbol.upper(), stamp, price)
    return None


def subscribe_payload(product: str, symbols) -> str:
    """The subscribe frame of one product channel, as JSON."""
    return json.dumps({"op": live_params.SUBSCRIBE_ACTION, "product": product,
                       "symbols": list(symbols)})


def unsubscribe_payload(product: str, symbols) -> str:
    """The unsubscribe frame of one product channel, as JSON."""
    return json.dumps({"op": live_params.UNSUBSCRIBE_ACTION,
                       "product": product, "symbols": list(symbols)})


def ping_payload() -> str:
    """The application-level keepalive frame."""
    return json.dumps({"op": live_params.PING_ACTION})


def auth_limits(message) -> dict:
    """Tier and connection limits carried by the `auth` acknowledgement."""
    if not isinstance(message, dict) or message.get("op") != "auth":
        return {}
    return {key: message.get(key)
            for key in ("tier", "max_conn", "max_subs") if message.get(key)}


def error_text(message) -> str:
    """Readable text of an error frame, without assuming a field exists."""
    if not isinstance(message, dict):
        return "unreadable error frame"
    code = str(message.get("code") or "error")
    detail = str(message.get("message") or "").strip()
    return f"{code}: {detail}" if detail else code
