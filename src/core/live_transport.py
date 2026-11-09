"""SiftingIO transport: the socket factory and the approved dependency.

`websocket-client` is the one approved third-party runtime dependency (OPEN-6)
and is imported lazily, so every other command and the whole test suite keep
running with the standard library only. Keeping the factory here leaves
`live_client` with the session logic alone (MOD-1, MOD-2).
"""

from __future__ import annotations

import socket
from typing import NamedTuple

from . import live_params


class LiveFeedError(RuntimeError):
    """Raised when the stream cannot start (missing dependency or key)."""


class Connection(NamedTuple):
    """One open socket plus the exceptions that mean 'no frame yet'."""

    handle: object
    timeouts: tuple


def _import_websocket():
    """The approved dependency, imported only when a stream actually starts."""
    try:
        import websocket                      # noqa: F401 (lazy on purpose)
    except ImportError as exc:
        raise LiveFeedError(
            "websocket-client is not installed; run "
            "`python -m pip install websocket-client` (docs/live.md)") from exc
    return websocket


def default_connect(key: str) -> Connection:
    """Opens one authenticated socket; the key travels in the query string."""
    websocket = _import_websocket()
    url = f"{live_params.WEBSOCKET_URL}?{live_params.KEY_PARAM}={key}"
    handle = websocket.create_connection(
        url, timeout=live_params.CONNECT_TIMEOUT_SECONDS)
    return Connection(handle, (websocket.WebSocketTimeoutException,
                               socket.timeout))
