"""Tests for the Twelve Data transport: a fake socket, never the network."""

import json
import sys

import pytest

from src.core import live_client, live_params, live_ticks
from src.shared import config

KEY = "test-key-123"
BASE = 1647950462


class Timeout(Exception):
    """Stands in for the websocket timeout exception (idle socket)."""


class FakeSocket:
    """Minimal stand-in for one websocket connection."""

    def __init__(self, frames=(), error=None):
        self.sent = []
        self.closed = False
        self._frames = list(frames)
        self._error = error

    def send(self, payload):
        self.sent.append(payload)

    def recv(self):
        if self._frames:
            return self._frames.pop(0)
        if self._error:
            raise self._error
        raise Timeout()

    def close(self):
        self.closed = True


class Clock:
    """Monotonic clock that advances a fixed step on every call."""

    def __init__(self, step=1.0):
        self.value = 0.0
        self.step = step

    def __call__(self):
        self.value += self.step
        return self.value


def _feed(socket, reports, ticks=None, clock=None, **kwargs):
    """A feed wired to a fake socket, collecting reports and ticks."""
    ticks = ticks if ticks is not None else []
    delivered = []
    feed = live_client.LiveFeed(
        ticks.append, KEY, side=config.SIDE_BID, clock=clock or Clock(1.0),
        sleeper=delivered.append, report=reports.append,
        connect=lambda key: live_client.Connection(socket, (Timeout,)),
        **kwargs)
    feed.delivered_pauses = delivered
    return feed


def test_the_subscribe_frame_is_sent_before_any_frame_is_read():
    socket = FakeSocket()
    feed = _feed(socket, [])
    feed.run(max_seconds=10)
    assert json.loads(socket.sent[0]) == {
        "action": "subscribe", "params": {"symbols": live_params.SYMBOL}}
    assert socket.closed is True


def test_a_price_frame_reaches_the_callback_once():
    frame = json.dumps({"event": "price", "symbol": "XAU/USD",
                        "timestamp": BASE, "bid": 1925.05, "ask": 1925.32})
    ticks = []
    feed = _feed(FakeSocket([frame]), [], ticks=ticks)
    feed.run(max_seconds=5)
    assert [tick.price for tick in ticks] == [1925.05]
    assert ticks[0].timestamp_ms == BASE * 1000
    assert feed.summary()["accepted"] == 1


def test_malformed_and_foreign_frames_are_counted_not_raised():
    frames = ["not json",
              json.dumps({"event": "price", "symbol": "EUR/USD",
                          "timestamp": BASE, "price": 1.1})]
    feed = _feed(FakeSocket(frames), [])
    feed.run(max_seconds=10)
    assert feed.summary()["ignored"] == 2
    assert feed.summary()["accepted"] == 0


def test_the_heartbeat_is_sent_while_the_socket_is_idle():
    socket = FakeSocket()
    feed = _feed(socket, [], clock=Clock(live_params.HEARTBEAT_SECONDS))
    feed.run(max_seconds=live_params.HEARTBEAT_SECONDS * 6)
    actions = [json.loads(frame)["action"] for frame in socket.sent]
    assert actions[0] == "subscribe"
    assert actions.count("heartbeat") >= 1


def test_a_rejected_subscription_is_reported_with_the_key_redacted():
    frame = json.dumps({"event": "subscribe-status", "status": "error",
                        "fails": [{"symbol": "XAU/USD", "message": KEY}]})
    reports = []
    feed = _feed(FakeSocket([frame]), reports)
    feed.run(max_seconds=5)
    assert feed.summary()["status_events"] == 1
    assert reports and KEY not in " ".join(reports)
    assert "***" in reports[0]


def test_a_successful_subscription_is_not_reported_as_a_failure():
    frame = json.dumps({"event": "subscribe-status", "status": "ok",
                        "success": [{"symbol": "XAU/USD"}]})
    reports = []
    feed = _feed(FakeSocket([frame]), reports)
    feed.run(max_seconds=5)
    assert reports == []


def test_a_connect_failure_is_reported_redacted_and_retried():
    reports = []

    def refuse(key):
        raise OSError(f"cannot connect with {key}")

    feed = live_client.LiveFeed(
        [].append, KEY, side=config.SIDE_BID, clock=Clock(1.0),
        sleeper=[].append, report=reports.append, connect=refuse)
    feed.run(max_seconds=6)
    joined = " ".join(reports)
    assert KEY not in joined
    assert "***" in joined
    assert feed.summary()["reconnects"] == 0


def test_the_reconnect_pause_grows_and_stays_bounded():
    feed = _feed(FakeSocket(), [])
    assert feed.backoff(1) == live_params.RECONNECT_BASE_SECONDS
    assert feed.backoff(2) == live_params.RECONNECT_BASE_SECONDS * 2
    assert feed.backoff(50) == live_params.RECONNECT_MAX_SECONDS


def test_a_dropped_socket_is_reconnected_after_a_pause():
    socket = FakeSocket(error=ConnectionError("dropped"))
    feed = _feed(socket, [])
    feed.run(max_seconds=30)
    assert feed.summary()["reconnects"] >= 1
    assert feed.delivered_pauses and socket.closed is True


def test_the_missing_dependency_answers_a_readable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "websocket", None)
    with pytest.raises(live_client.LiveFeedError) as error:
        live_client._import_websocket()
    assert "websocket-client" in str(error.value)


def test_the_key_comes_from_the_environment_first(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"{live_params.API_KEY_ENV}=from-file\n",
                        encoding="utf-8")
    monkeypatch.setattr(live_params, "ENV_FILE", str(env_file))
    monkeypatch.delenv(live_params.API_KEY_ENV, raising=False)
    assert live_client.api_key() == "from-file"
    monkeypatch.setenv(live_params.API_KEY_ENV, "from-shell")
    assert live_client.api_key() == "from-shell"
