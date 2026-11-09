"""Twelve Data WebSocket transport: subscribe, heartbeat, reconnect, counting.

`websocket-client` is the one approved third-party runtime dependency (OPEN-6)
and is imported lazily, so every other command and the whole test suite keep
running with the standard library only. The API key travels in the
`X-TD-APIKEY` header, never in the URL, and it is redacted from every message
this module reports.
"""

from __future__ import annotations

import os
import socket
import time
from typing import NamedTuple

from ..shared import config, envfile
from . import live_params, live_ticks


class LiveFeedError(RuntimeError):
    """Raised when the stream cannot start (missing dependency or key)."""


class Connection(NamedTuple):
    """One open socket plus the exceptions that mean 'no frame yet'."""

    handle: object
    timeouts: tuple


def api_key() -> str | None:
    """$TWELVE_DATA_API_KEY, else the key in the project `.env`, else None."""
    from_env = os.environ.get(live_params.API_KEY_ENV, "").strip()
    if from_env:
        return from_env
    values = envfile.read(live_params.ENV_FILE)
    return (values.get(live_params.API_KEY_ENV) or "").strip() or None


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
    """Opens one authenticated socket; the key never enters the URL or a log."""
    websocket = _import_websocket()
    handle = websocket.create_connection(
        live_params.WEBSOCKET_URL,
        header=[f"{live_params.AUTH_HEADER}: {key}"],
        timeout=live_params.CONNECT_TIMEOUT_SECONDS)
    return Connection(handle, (websocket.WebSocketTimeoutException,
                               socket.timeout))


class LiveFeed:
    """One reconnecting session that turns raw frames into ticks."""

    def __init__(self, on_tick, key: str, symbol: str = live_params.SYMBOL,
                 side: str = None, connect=None, clock=time.monotonic,
                 sleeper=time.sleep, report=print):
        self._on_tick = on_tick
        self._key = key
        self._symbol = symbol
        self._side = side or config.DEFAULT_SIDE
        self._connect = connect or default_connect
        self._clock = clock
        self._sleeper = sleeper
        self._report = report
        self.stopped = False
        self.accepted = 0
        self.ignored = 0
        self.status_events = 0
        self.reconnects = 0

    def stop(self) -> None:
        """Asks both loops to finish after the frame that is being handled."""
        self.stopped = True

    def _redact(self, text) -> str:
        """Removes the API key from anything that is about to be printed."""
        text = str(text)
        return text.replace(self._key, "***") if self._key else text

    def backoff(self, attempt: int) -> float:
        """Bounded exponential pause before the next reconnect attempt."""
        step = max(int(attempt), 1) - 1
        pause = live_params.RECONNECT_BASE_SECONDS * (2 ** step)
        return min(pause, live_params.RECONNECT_MAX_SECONDS)

    def _expired(self, deadline) -> bool:
        """True once the requested run duration is over."""
        return deadline is not None and self._clock() >= deadline

    def run(self, max_seconds=None) -> dict:
        """Streams until the duration ends or `stop()` is called."""
        deadline = (None if max_seconds is None
                    else self._clock() + float(max_seconds))
        attempt = 0
        while not self.stopped and not self._expired(deadline):
            try:
                connection = self._connect(self._key)
            except LiveFeedError:
                raise
            except Exception as exc:          # network errors are expected
                self._report(f" ! live connect failed: {self._redact(exc)}")
                attempt += 1
                self._sleeper(self.backoff(attempt))
                continue
            attempt = 0
            self._session(connection, deadline)
        return self.summary()

    def _session(self, connection, deadline) -> None:
        """One socket: subscribe, pump frames, then close and back off."""
        try:
            connection.handle.send(live_ticks.subscribe_payload(self._symbol))
            self._pump(connection, deadline)
        except Exception as exc:              # a dropped socket is normal
            if not self.stopped:
                self._report(f" ! live stream interrupted: {self._redact(exc)}")
        finally:
            try:
                connection.handle.close()
            except Exception as exc:          # an already closed socket
                self._report(f" ! live close failed: {self._redact(exc)}")
        if not self.stopped and not self._expired(deadline):
            self.reconnects += 1
            self._sleeper(self.backoff(self.reconnects))

    def _pump(self, connection, deadline) -> None:
        """Reads frames and sends the heartbeat whenever ten seconds passed."""
        beat = self._clock()
        while not self.stopped and not self._expired(deadline):
            try:
                frame = connection.handle.recv()
            except connection.timeouts:       # idle socket, not an error
                frame = ""
            if frame:
                self.consume(frame)
            if self._clock() - beat >= live_params.HEARTBEAT_SECONDS:
                connection.handle.send(live_ticks.heartbeat_payload())
                beat = self._clock()

    def consume(self, frame: str) -> None:
        """Handles one raw frame: a tick, a status event or an ignored frame."""
        message = live_ticks.decode(frame)
        if message is None:
            self.ignored += 1
            return
        if message.get("event") == live_params.SUBSCRIBE_STATUS:
            self.status_events += 1
            self._report_status(message)
            return
        tick = live_ticks.tick(message, self._side, self._symbol)
        if tick is None:
            self.ignored += 1
            return
        self.accepted += 1
        self._on_tick(tick)

    def _report_status(self, message: dict) -> None:
        """Reports a rejected subscription instead of streaming nothing."""
        if str(message.get("status") or "").lower() == "ok":
            return
        fails = self._redact(message.get("fails") or message.get("status"))
        self._report(f" ! live subscription rejected: {fails}")

    def summary(self) -> dict:
        """Counters of the run, for the CLI summary and the tests."""
        return {
            "accepted": self.accepted,
            "ignored": self.ignored,
            "status_events": self.status_events,
            "reconnects": self.reconnects,
            "stopped": self.stopped,
        }

