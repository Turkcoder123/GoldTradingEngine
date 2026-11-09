"""Tests for the Twelve Data frame parsing (offline, no socket)."""

import json

import pytest

from src.core import live_params, live_ticks
from src.shared import config

PRICE_FRAME = {
    "event": "price",
    "symbol": "XAU/USD",
    "currency": "USD",
    "currency_base": "Gold Spot",
    "timestamp": 1647950462,
    "price": 1925.18,
    "bid": 1925.05,
    "ask": 1925.32,
}


def test_decode_answers_a_dict_only_for_a_json_object():
    assert live_ticks.decode('{"event": "price"}') == {"event": "price"}
    assert live_ticks.decode("not json") is None
    assert live_ticks.decode("[1, 2]") is None


def test_provider_seconds_become_epoch_milliseconds():
    assert live_ticks.timestamp_ms(1647950462) == 1647950462000


def test_a_millisecond_timestamp_passes_through():
    assert live_ticks.timestamp_ms(1647950462123) == 1647950462123


@pytest.mark.parametrize("value", [None, "", "later", 0, -5])
def test_an_unusable_timestamp_is_rejected(value):
    with pytest.raises(ValueError):
        live_ticks.timestamp_ms(value)


def test_the_bid_side_is_preferred_for_a_bid_run():
    tick = live_ticks.tick(PRICE_FRAME, config.SIDE_BID)
    assert tick.price == 1925.05
    assert tick.timestamp_ms == 1647950462000
    assert tick.symbol == "XAU/USD"


def test_the_ask_side_is_preferred_for_an_ask_run():
    assert live_ticks.tick(PRICE_FRAME, config.SIDE_ASK).price == 1925.32


def test_the_price_field_is_the_documented_fallback():
    frame = {"event": "price", "symbol": "XAU/USD", "timestamp": 1647950462,
             "price": 1925.18}
    assert live_ticks.tick(frame, config.SIDE_ASK).price == 1925.18


def test_a_status_event_is_not_a_tick():
    frame = {"event": "subscribe-status", "status": "ok", "success": []}
    assert live_ticks.tick(frame, config.SIDE_BID) is None


def test_another_symbol_is_not_a_tick():
    frame = dict(PRICE_FRAME, symbol="EUR/USD")
    assert live_ticks.tick(frame, config.SIDE_BID) is None


def test_a_price_event_without_timestamp_is_not_a_tick():
    frame = dict(PRICE_FRAME, timestamp=None)
    assert live_ticks.tick(frame, config.SIDE_BID) is None


def test_unusable_prices_are_not_ticks():
    frame = dict(PRICE_FRAME, bid="", ask=None, price=0)
    assert live_ticks.tick(frame, config.SIDE_BID) is None


def test_the_subscribe_payload_matches_the_provider_format():
    payload = json.loads(live_ticks.subscribe_payload())
    assert payload == {"action": "subscribe",
                       "params": {"symbols": live_params.SYMBOL}}


def test_the_heartbeat_payload_matches_the_provider_format():
    assert json.loads(live_ticks.heartbeat_payload()) == {
        "action": "heartbeat"}
