"""Tests for the SiftingIO transport: a fake socket, never the network."""

import json
import sys

import pytest

from src.core import live_client, live_params, live_transport
from src.shared import config

KEY = "sft_test-key-123"


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


def _tick_frame(symbol="XAUUSD", stamp=1794211181154, bid=4085.99, ask=4086.62):
    return json.dumps({"f": "tick", "class": "spot", "s": symbol,
                       "p": bid, "b": bid, "a": ask, "t": stamp})


def _feed(socket, reports, series=None, **kwargs):
    ticks = kwargs.pop("ticks", [])
    feed = live_client.LiveFeed(
        ticks.append, KEY, series=series, side=config.SIDE_BID,
        clock=kwargs.pop("clock", Clock(1.0)), sleeper=[].append,
        report=reports.append,
        connect=lambda key: live_client.Connection(socket, (Timeout,)),
        **kwargs)
    feed.ticks = ticks
    return feed


def test_one_subscribe_frame_is_sent_per_product_channel():
    socket = FakeSocket()
    _feed(socket, []).run(max_seconds=10)
    frames = [json.loads(payload) for payload in socket.sent]
    products = {frame["product"] for frame in frames if frame.get("op") == "subscribe"}
    assert products == {"com", "fx"}
    assert socket.closed is True


def test_a_tick_frame_reaches_its_series_buffer():
    ticks = []
    feed = _feed(FakeSocket([_tick_frame()]), [], ticks=ticks)
    feed.run(max_seconds=10)
    assert [(tick.series, tick.price) for tick in ticks] == [("xauusd", 4085.99)]


def test_a_tick_of_an_unsubscribed_symbol_is_counted_not_raised():
    feed = _feed(FakeSocket([_tick_frame(symbol="XAGUSD")]), [])
    feed.run(max_seconds=10)
    assert feed.summary()["ignored"] == 1
    assert feed.summary()["accepted"] == 0


def test_the_auth_acknowledgement_reports_the_plan_limits():
    ack = json.dumps({"f": "ack", "op": "auth", "tier": "free",
                      "max_conn": 1, "max_subs": 5})
    reports = []
    feed = _feed(FakeSocket([ack]), reports)
    feed.run(max_seconds=10)
    assert feed.limits == {"tier": "free", "max_conn": 1, "max_subs": 5}
    assert any("free" in text for text in reports)


def test_an_error_frame_is_reported_with_the_key_redacted():
    frame = json.dumps({"f": "error", "code": "auth_failed",
                        "message": f"bad key {KEY}"})
    reports = []
    feed = _feed(FakeSocket([frame]), reports)
    feed.run(max_seconds=10)
    joined = " ".join(reports)
    assert feed.summary()["errors"] == 1
    assert KEY not in joined and "***" in joined


def test_a_pong_is_counted_and_the_ping_follows_the_keepalive():
    socket = FakeSocket([json.dumps({"f": "pong"})])
    feed = _feed(socket, [], clock=Clock(live_params.PING_SECONDS))
    feed.run(max_seconds=live_params.PING_SECONDS * 6)
    actions = [json.loads(payload).get("op") for payload in socket.sent]
    assert feed.summary()["pongs"] == 1
    assert "ping" in actions


def test_the_idle_hook_runs_even_while_frames_arrive():
    calls = []
    socket = FakeSocket([_tick_frame(), _tick_frame()])
    feed = _feed(socket, [], on_idle=lambda: calls.append(1))
    feed.run(max_seconds=10)
    assert calls


def test_a_dropped_socket_is_reconnected_after_a_pause():
    socket = FakeSocket(error=ConnectionError("dropped"))
    feed = _feed(socket, [])
    feed.run(max_seconds=30)
    assert feed.summary()["reconnects"] >= 1
    assert socket.closed is True


def test_a_connect_failure_is_reported_redacted():
    reports = []

    def refuse(key):
        raise OSError(f"cannot connect with {key}")

    feed = live_client.LiveFeed(
        [].append, KEY, side=config.SIDE_BID, clock=Clock(1.0),
        sleeper=[].append, report=reports.append, connect=refuse)
    feed.run(max_seconds=6)
    joined = " ".join(reports)
    assert KEY not in joined and "***" in joined


def test_the_reconnect_pause_grows_and_stays_bounded():
    feed = _feed(FakeSocket(), [])
    assert feed.backoff(1) == live_params.RECONNECT_BASE_SECONDS
    assert feed.backoff(50) == live_params.RECONNECT_MAX_SECONDS


def test_the_missing_dependency_answers_a_readable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "websocket", None)
    with pytest.raises(live_transport.LiveFeedError) as error:
        live_transport._import_websocket()
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
