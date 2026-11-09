"""Constants of the temporary Twelve Data live layer (`docs/live.md`).

The live layer is an overlay only: Dukascopy stays the authoritative source of
the stored 1-minute history, and nothing here writes to a CSV file. Keeping the
constants in their own module follows MOD-7 and leaves the protocol modules
readable.
"""

from __future__ import annotations

import os

from ..shared import config

# Twelve Data real-time price stream (wss://ws.twelvedata.com/v1/quotes/price).
WEBSOCKET_URL = "wss://ws.twelvedata.com/v1/quotes/price"
SYMBOL = "XAU/USD"
API_KEY_ENV = "TWELVE_DATA_API_KEY"
AUTH_HEADER = "X-TD-APIKEY"
ENV_FILE = os.path.join(os.path.dirname(config.VERSION_FILE), ".env")

# The provider expects these exact action names on the same socket.
SUBSCRIBE_ACTION = "subscribe"
UNSUBSCRIBE_ACTION = "unsubscribe"
HEARTBEAT_ACTION = "heartbeat"
SUBSCRIBE_STATUS = "subscribe-status"
PRICE_EVENT = "price"

# The provider asks for a heartbeat every ten seconds to keep the socket open.
HEARTBEAT_SECONDS = 10.0
RECV_TIMEOUT_SECONDS = 1.0
CONNECT_TIMEOUT_SECONDS = 10.0
RECONNECT_BASE_SECONDS = 1.0
RECONNECT_MAX_SECONDS = 60.0

# Buffer and precedence defaults: a few hours of live bars are enough to cover
# the fifteen minute Dukascopy refresh many times over.
BUFFER_MINUTES = 180
BOUNDARY_REFRESH_SECONDS = 60.0

# Provider timestamps are UNIX seconds; a millisecond value is far above this.
SECONDS_LIMIT = 100_000_000_000
MS_PER_SECOND = 1000

# Which event field carries the price of the configured quote side, in the
# order they are tried; `price` is the documented fallback.
SIDE_FIELDS = {
    config.SIDE_BID: ("bid", "price"),
    config.SIDE_ASK: ("ask", "price"),
}
