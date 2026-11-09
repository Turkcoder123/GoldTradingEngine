"""Constants of the temporary live layer (`docs/live.md`).

Two providers, one precedence rule: SiftingIO streams the ticks of the
instruments it publishes over one WebSocket, and the Dukascopy feed is polled
once a minute for the dollar index, which no tick provider offers. Dukascopy
stays the authoritative source of the stored history either way, and nothing
here writes to a CSV file.
"""

from __future__ import annotations

import os

from ..shared import config

# SiftingIO live stream (docs/live.md). The key travels in the query string:
# the provider documents no header authentication for the WebSocket.
WEBSOCKET_URL = "wss://stream.sifting.io/ws/v1"
API_KEY_ENV = "SIFTING_API_KEY"
KEY_PARAM = "key"
ENV_FILE = os.path.join(os.path.dirname(config.VERSION_FILE), ".env")

# SiftingIO channels: `com` carries spot commodities, `fx` the currency pairs.
LIVE_SERIES = {
    "xauusd": {"symbol": "XAUUSD", "product": "com"},
    "eurusd": {"symbol": "EURUSD", "product": "fx"},
}
# Which field carries the price of the configured quote side, in try order.
SIDE_FIELDS = {
    config.SIDE_BID: ("b", "p"),
    config.SIDE_ASK: ("a", "p"),
}

# Frames of the stream: every server frame carries the `f` discriminator.
FRAME_ACK = "ack"
FRAME_TICK = "tick"
FRAME_PONG = "pong"
FRAME_ERROR = "error"
SUBSCRIBE_ACTION = "subscribe"
UNSUBSCRIBE_ACTION = "unsubscribe"
PING_ACTION = "ping"

# The provider asks for an application-level keepalive; twenty seconds keeps the
# connection well inside the idle window without chattering.
PING_SECONDS = 20.0
RECV_TIMEOUT_SECONDS = 1.0
CONNECT_TIMEOUT_SECONDS = 10.0
RECONNECT_BASE_SECONDS = 1.0
RECONNECT_MAX_SECONDS = 60.0

# The dollar index has no tick provider: its 1-minute bars come from the
# Dukascopy feed, polled at this interval (one request per poll).
DXY_SERIES = "dxy"
DXY_POLL_SECONDS = 60.0

# Buffer and precedence defaults: a few hours of live bars cover the fifteen
# minute Dukascopy refresh many times over.
BUFFER_MINUTES = 180
BOUNDARY_REFRESH_SECONDS = 60.0
DEFAULT_LIVE_SERIES = ("xauusd", "eurusd", "dxy")
