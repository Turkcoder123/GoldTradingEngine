"""Tests for the SiftingIO frame parsing (offline, no socket)."""

import json

import pytest

from src.core import live_params, live_ticks
from src.shared import config

TICK = {"f": "tick", "class": "spot", "s": "XAUUSD", "p": 4086.3,
        "P": 10812, "b": 4085.99, "B": 28061, "a": 4086.62, "A": 35094,
        "t": 1794211181154}


def test_decode_answers_a_dict_only_for_a_json_object():
    assert live_ticks.decode('{"f": "tick"}') == {"f": "tick"}
    assert live_ticks.decode("not json") is None
    assert live_ticks.decode("[1, 2]") is None


def test_the_bid_side_is_preferred_for_a_bid_run():
    tick = live_ticks.tick_frame(TICK, config.SIDE_BID, "xauusd", "XAUUSD")
    assert tick.price == 4085.99
    assert tick.series == "xauusd"
    assert tick.symbol == "XAUUSD"
    assert tick.timestamp_ms == 1794211181154


def test_the_ask_side_is_preferred_for_an_ask_run():
    tick = live_ticks.tick_frame(TICK, config.SIDE_ASK, "xauusd", "XAUUSD")
    assert tick.price == 4086.62


def test_the_trade_price_is_the_fallback():
    frame = {"f": "tick", "s": "EURUSD", "p": "1.11717", "t": 1794211183254}
    tick = live_ticks.tick_frame(frame, config.SIDE_ASK, "eurusd", "EURUSD")
    assert tick.price == 1.11717


def test_another_symbol_and_another_frame_are_not_ticks():
    other = dict(TICK, s="EURUSD")
    assert live_ticks.tick_frame(other, config.SIDE_BID, "xauusd", "XAUUSD") is None
    ack = {"f": "ack", "op": "subscribe", "product": "com"}
    assert live_ticks.tick_frame(ack, config.SIDE_BID, "xauusd", "XAUUSD") is None


@pytest.mark.parametrize("field,value", [("t", None), ("t", "later"),
                                         ("t", 0), ("p", "x")])
def test_a_frame_without_a_usable_time_or_price_is_not_a_tick(field, value):
    frame = dict(TICK, **{field: value})
    if field == "p":                      # no side field may rescue it
        frame.pop("b", None)
        frame.pop("a", None)
    assert live_ticks.tick_frame(
        frame, config.SIDE_BID, "xauusd", "XAUUSD") is None


def test_the_subscribe_frame_groups_symbols_of_one_product():
    payload = json.loads(live_ticks.subscribe_payload("com", ["XAUUSD"]))
    assert payload == {"op": "subscribe", "product": "com",
                       "symbols": ["XAUUSD"]}


def test_the_unsubscribe_frame_repeats_the_subscribe_shape():
    payload = json.loads(live_ticks.unsubscribe_payload("fx", ["EURUSD"]))
    assert payload["op"] == "unsubscribe"
    assert payload["symbols"] == ["EURUSD"]


def test_the_ping_frame_matches_the_protocol():
    assert json.loads(live_ticks.ping_payload()) == {"op": "ping"}


def test_the_auth_acknowledgement_carries_the_limits():
    ack = {"f": "ack", "op": "auth", "tier": "free", "max_conn": 1,
           "max_subs": 5, "active_conn": 1}
    assert live_ticks.auth_limits(ack) == {"tier": "free", "max_conn": 1,
                                           "max_subs": 5}
    assert live_ticks.auth_limits({"f": "ack", "op": "subscribe"}) == {}


def test_an_error_frame_becomes_readable_text():
    frame = {"f": "error", "code": "max_subscriptions", "message": "cap"}
    assert live_ticks.error_text(frame) == "max_subscriptions: cap"
    assert live_ticks.error_text({"f": "error"}) == "error"


def test_the_registry_maps_the_streamed_series_to_products():
    assert live_params.LIVE_SERIES["xauusd"] == {"symbol": "XAUUSD",
                                                 "product": "com"}
    assert live_params.LIVE_SERIES["eurusd"] == {"symbol": "EURUSD",
                                                 "product": "fx"}
