"""SiftingIO session: subscribe, ping, reconnect, counting, routing.

The socket factory lives in `live_transport` (the module that owns the approved
dependency, OPEN-6). The provider authenticates the socket with the key in the
query string, so the key is redacted from every message this module reports.
"""

from __future__ import annotations

import os
import time

from ..shared import config, envfile
from . import live_params, live_ticks
from .live_transport import Connection, LiveFeedError, default_connect


def api_key() -> str | None:
    """$SIFTING_API_KEY, else the key in the project `.env`, else None."""
    from_env = os.environ.get(live_params.API_KEY_ENV, "").strip()
    if from_env:
        return from_env
    values = envfile.read(live_params.ENV_FILE)
    return (values.get(live_params.API_KEY_ENV) or "").strip() or None


class LiveFeed:
    """One reconnecting session that turns raw frames into ticks."""

    def __init__(self, on_tick, key: str, series=None, side: str = None,
                 connect=None, clock=time.monotonic, sleeper=time.sleep,
                 report=print, on_idle=None):
        self._on_tick = on_tick
        self._key = key
        self._series = dict(series or live_params.LIVE_SERIES)
        self._by_symbol = {entry["symbol"].upper(): series_key
                           for series_key, entry in self._series.items()}
        self._side = side or config.DEFAULT_SIDE
        self._connect = connect or default_connect
        self._clock = clock
        self._sleeper = sleeper
        self._report = report
        self._on_idle = on_idle or (lambda: None)
        self.stopped = False
        self.limits: dict = {}
        self.accepted = 0
        self.ignored = 0
        self.status_events = 0
        self.errors = 0
        self.pongs = 0
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

    def products(self) -> dict:
        """Symbols grouped by product channel: {'com': ['XAUUSD'], ...}."""
        grouped: dict = {}
        for entry in self._series.values():
            grouped.setdefault(entry["product"], []).append(entry["symbol"])
        return grouped

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
            for product, symbols in self.products().items():
                connection.handle.send(
                    live_ticks.subscribe_payload(product, symbols))
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
        """Reads frames, pings the server and lets the caller poll the index.

        The idle hook runs after every frame and every timeout: a busy stream
        never times out, so a hook bound to timeouts alone would never poll.
        The poller throttles itself, so calling it here costs one comparison.
        """
        beat = self._clock()
        while not self.stopped and not self._expired(deadline):
            try:
                frame = connection.handle.recv()
            except connection.timeouts:       # idle socket, not an error
                frame = ""
            if frame:
                self.consume(frame)
            self._on_idle()
            if self._clock() - beat >= live_params.PING_SECONDS:
                connection.handle.send(live_ticks.ping_payload())
                beat = self._clock()

    def consume(self, frame: str) -> None:
        """Handles one raw frame: a tick, an ack, a pong or an error."""
        message = live_ticks.decode(frame)
        if message is None:
            self.ignored += 1
            return
        kind = message.get("f")
        if kind == live_params.FRAME_TICK:
            self._consume_tick(message)
        elif kind == live_params.FRAME_ACK:
            self._consume_ack(message)
        elif kind == live_params.FRAME_PONG:
            self.pongs += 1
        elif kind == live_params.FRAME_ERROR:
            self.errors += 1
            self._report(" ! live error: "
                         f"{self._redact(live_ticks.error_text(message))}")
        else:
            self.ignored += 1

    def _consume_ack(self, message: dict) -> None:
        """Counts an acknowledgement and reports the tier limits once."""
        self.status_events += 1
        limits = live_ticks.auth_limits(message)
        if not limits:
            return
        self.limits = limits
        self._report(" live limits: tier %s, %s connection(s), "
                     "%s subscription(s)" % (limits.get("tier"),
                                             limits.get("max_conn"),
                                             limits.get("max_subs")))

    def _consume_tick(self, message: dict) -> None:
        """Routes one tick frame to the series it belongs to."""
        symbol = str(message.get("s") or "").strip().upper()
        series = self._by_symbol.get(symbol)
        tick = (live_ticks.tick_frame(message, self._side, series, symbol)
                if series else None)
        if tick is None:
            self.ignored += 1
            return
        self.accepted += 1
        self._on_tick(tick)

    def summary(self) -> dict:
        """Counters of the run, for the CLI summary and the tests."""
        return {
            "accepted": self.accepted,
            "ignored": self.ignored,
            "status_events": self.status_events,
            "errors": self.errors,
            "pongs": self.pongs,
            "reconnects": self.reconnects,
            "stopped": self.stopped,
        }

